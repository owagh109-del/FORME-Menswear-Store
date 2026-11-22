from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(app.root_path, "store.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(60), nullable=False)
    description = db.Column(db.Text, default="")
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(500), default="")
    sizes = db.Column(db.String(100), default="S,M,L,XL")
    stock = db.Column(db.Integer, default=10)
    featured = db.Column(db.Boolean, default=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(120), default="")
    address = db.Column(db.Text, nullable=False)
    delivery_method = db.Column(db.String(30), default="Courier")
    payment_method = db.Column(db.String(40), default="Cash on Delivery")
    total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(30), default="Received")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan")

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    product_name = db.Column(db.String(120), nullable=False)
    size = db.Column(db.String(20), default="")
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class AdminAccess(db.Model):
    """Separate access table so existing store.db files remain compatible."""
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("admin.id"), unique=True, nullable=False)
    role = db.Column(db.String(30), default="staff", nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    admin = db.relationship("Admin", backref=db.backref("access", uselist=False, cascade="all, delete-orphan"))

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)
    return wrapper

def cart_items():
    cart = session.get("cart", {})
    items, total = [], 0
    for key, value in cart.items():
        product = db.session.get(Product, int(key))
        if product:
            qty = int(value.get("qty", 1))
            size = value.get("size", "")
            subtotal = product.price * qty
            items.append({"product": product, "qty": qty, "size": size, "subtotal": subtotal})
            total += subtotal
    return items, total

@app.context_processor
def inject_globals():
    return {"cart_count": sum(int(v.get("qty", 1)) for v in session.get("cart", {}).values())}

@app.route("/")
def home():
    featured = Product.query.filter_by(featured=True).limit(4).all()
    if not featured:
        featured = Product.query.order_by(Product.id.desc()).limit(4).all()
    return render_template("home.html", featured=featured)

@app.route("/shop")
def shop():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    query = Product.query
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))
    if category:
        query = query.filter_by(category=category)
    products = query.order_by(Product.id.desc()).all()
    categories = [x[0] for x in db.session.query(Product.category).distinct().all()]
    return render_template("shop.html", products=products, categories=categories, q=q, selected=category)

@app.route("/product/<int:product_id>")
def product_detail(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    return render_template("product.html", product=product)

@app.post("/cart/add/<int:product_id>")
def add_to_cart(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    if product.stock < 1:
        flash("This item is currently out of stock.", "error")
        return redirect(url_for("product_detail", product_id=product.id))
    size = request.form.get("size", "")
    qty = max(1, min(int(request.form.get("quantity", 1)), product.stock))
    cart = session.get("cart", {})
    key = str(product.id)
    if key in cart and cart[key].get("size") == size:
        cart[key]["qty"] = min(product.stock, int(cart[key]["qty"]) + qty)
    else:
        cart[key] = {"qty": qty, "size": size}
    session["cart"] = cart
    flash("Added to your bag.", "success")
    return redirect(request.referrer or url_for("shop"))

@app.route("/cart")
def cart():
    items, total = cart_items()
    return render_template("cart.html", items=items, total=total)

@app.post("/cart/update")
def update_cart():
    cart = session.get("cart", {})
    for key in list(cart.keys()):
        try:
            qty = int(request.form.get(f"qty_{key}", cart[key]["qty"]))
            product = db.session.get(Product, int(key))
            if qty <= 0:
                cart.pop(key, None)
            elif product:
                cart[key]["qty"] = min(qty, product.stock)
        except (ValueError, TypeError):
            pass
    session["cart"] = cart
    return redirect(url_for("cart"))

@app.post("/cart/remove/<int:product_id>")
def remove_from_cart(product_id):
    cart = session.get("cart", {})
    cart.pop(str(product_id), None)
    session["cart"] = cart
    return redirect(url_for("cart"))

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    items, total = cart_items()
    if not items:
        flash("Your bag is empty.", "error")
        return redirect(url_for("shop"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        if not name or not phone or not address:
            flash("Please complete your name, phone and delivery address.", "error")
            return render_template("checkout.html", items=items, total=total)
        delivery = request.form.get("delivery", "Courier")
        payment = request.form.get("payment", "Cash on Delivery")
        order = Order(customer_name=name, phone=phone, email=request.form.get("email", ""),
                      address=address, delivery_method=delivery, payment_method=payment, total=total)
        db.session.add(order)
        for item in items:
            product = item["product"]
            if product.stock < item["qty"]:
                flash(f"Only {product.stock} left for {product.name}. Please update your bag.", "error")
                db.session.rollback()
                return redirect(url_for("cart"))
            product.stock -= item["qty"]
            db.session.add(OrderItem(order=order, product_name=product.name, size=item["size"],
                                     quantity=item["qty"], price=product.price))
        db.session.commit()
        session["cart"] = {}
        return render_template("order_success.html", order=order)
    return render_template("checkout.html", items=items, total=total)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        admin = Admin.query.filter_by(username=request.form.get("username", "")).first()
        access = AdminAccess.query.filter_by(admin_id=admin.id).first() if admin else None
        if admin and access and access.active and check_password_hash(admin.password_hash, request.form.get("password", "")):
            session["admin_id"] = admin.id
            session["admin_role"] = access.role
            return redirect(url_for("admin_dashboard"))
        flash("Incorrect username or password.", "error")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_id", None)
    session.pop("admin_role", None)
    return redirect(url_for("home"))

def owner_required(fn):
    @wraps(fn)
    @admin_required
    def wrapper(*args, **kwargs):
        if session.get("admin_role") != "owner":
            abort(403)
        return fn(*args, **kwargs)
    return wrapper

def role_required(*allowed_roles):
    def decorate(fn):
        @wraps(fn)
        @admin_required
        def wrapper(*args, **kwargs):
            role = session.get("admin_role", "staff")
            if role not in set(allowed_roles) | {"owner", "manager"}:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorate


@app.route("/admin")
@admin_required
def admin_dashboard():
    products = Product.query.order_by(Product.id.desc()).all()
    orders = Order.query.order_by(Order.created_at.desc()).all()
    total_sales = sum(o.total for o in orders if o.status != "Cancelled")
    low_stock = Product.query.filter(Product.stock <= 5).count()
    return render_template("admin.html", products=products, orders=orders,
                           total_sales=total_sales, low_stock=low_stock,
                           admin_role=session.get("admin_role", "staff"))

@app.route("/admin/accounts", methods=["GET", "POST"])
@owner_required
def admin_accounts():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "staff")
        if not username or len(password) < 10 or role not in {"manager", "orders", "inventory"}:
            flash("Enter a username, a password of at least 10 characters, and a valid role.", "error")
        elif Admin.query.filter_by(username=username).first():
            flash("That username is already in use.", "error")
        else:
            user = Admin(username=username, password_hash=generate_password_hash(password))
            db.session.add(user)
            db.session.flush()
            db.session.add(AdminAccess(admin_id=user.id, role=role, active=True))
            db.session.commit()
            flash("Staff account created.", "success")
            return redirect(url_for("admin_accounts"))
    staff = db.session.query(Admin, AdminAccess).join(AdminAccess, Admin.id == AdminAccess.admin_id).order_by(Admin.id).all()
    return render_template("admin_accounts.html", staff=staff)

@app.post("/admin/accounts/<int:admin_id>/toggle")
@owner_required
def toggle_admin_account(admin_id):
    user = db.session.get(Admin, admin_id) or abort(404)
    access = AdminAccess.query.filter_by(admin_id=user.id).first() or abort(404)
    if access.role == "owner":
        flash("The owner account cannot be disabled here.", "error")
    elif user.id == session.get("admin_id"):
        flash("You cannot disable your own account.", "error")
    else:
        access.active = not access.active
        db.session.commit()
    return redirect(url_for("admin_accounts"))

@app.route("/admin/customers")
@admin_required
def admin_customers():
    # The starter checkout stores guest customer details on orders; this is a customer directory,
    # not customer login accounts. Multiple orders are grouped by phone number.
    grouped = {}
    for order in Order.query.order_by(Order.created_at.desc()).all():
        key = order.phone.strip()
        if key not in grouped:
            grouped[key] = {"name": order.customer_name, "phone": order.phone, "email": order.email,
                            "orders": 0, "spent": 0.0, "last_order": order.created_at}
        grouped[key]["orders"] += 1
        if order.status != "Cancelled":
            grouped[key]["spent"] += order.total
    return render_template("admin_customers.html", customers=list(grouped.values()))

@app.route("/admin/analytics")
@admin_required
def admin_analytics():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    completed_sales = sum(o.total for o in orders if o.status not in {"Cancelled"})
    status_counts = {}
    for order in orders:
        status_counts[order.status] = status_counts.get(order.status, 0) + 1
    best_sellers = db.session.query(OrderItem.product_name, db.func.sum(OrderItem.quantity).label("units")).group_by(OrderItem.product_name).order_by(db.func.sum(OrderItem.quantity).desc()).limit(5).all()
    low_stock_products = Product.query.filter(Product.stock <= 5).order_by(Product.stock).all()
    return render_template("admin_analytics.html", orders=orders, completed_sales=completed_sales,
                           status_counts=status_counts, best_sellers=best_sellers,
                           low_stock_products=low_stock_products)

@app.route("/admin/product/new", methods=["GET", "POST"])
@app.route("/admin/product/<int:product_id>/edit", methods=["GET", "POST"])
@role_required("inventory")
def admin_product(product_id=None):
    product = db.session.get(Product, product_id) if product_id else Product()
    if request.method == "POST":
        product.name = request.form.get("name", "").strip()
        product.category = request.form.get("category", "Men")
        product.description = request.form.get("description", "")
        product.price = float(request.form.get("price", 0))
        product.image = request.form.get("image", "")
        product.sizes = request.form.get("sizes", "S,M,L,XL")
        product.stock = max(0, int(request.form.get("stock", 0)))
        product.featured = request.form.get("featured") == "on"
        if not product.name or product.price < 0:
            flash("Enter a product name and valid price.", "error")
            return render_template("product_form.html", product=product)
        db.session.add(product)
        db.session.commit()
        return redirect(url_for("admin_dashboard"))
    return render_template("product_form.html", product=product)

@app.post("/admin/order/<int:order_id>/status")
@role_required("orders")
def update_order_status(order_id):
    order = db.session.get(Order, order_id) or abort(404)
    order.status = request.form.get("status", order.status)
    db.session.commit()
    return redirect(url_for("admin_dashboard"))

@app.post("/admin/product/<int:product_id>/delete")
@role_required("inventory")
def delete_product(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for("admin_dashboard"))

def seed():
    db.create_all()
    owner = Admin.query.filter_by(username="admin").first()
    if not owner:
        owner = Admin(username="admin", password_hash=generate_password_hash("ChangeMe123!"))
        db.session.add(owner)
        db.session.flush()
    if not AdminAccess.query.filter_by(admin_id=owner.id).first():
        db.session.add(AdminAccess(admin_id=owner.id, role="owner", active=True))
    # Give any pre-existing non-owner admin records a limited staff role.
    db.session.flush()
    for existing_admin in Admin.query.all():
        if not AdminAccess.query.filter_by(admin_id=existing_admin.id).first():
            db.session.add(AdminAccess(admin_id=existing_admin.id, role="staff", active=True))
    if Product.query.count() == 0:
        samples = [
            Product(name="Classic Oxford Shirt", category="Shirts", description="A versatile everyday shirt with a clean, smart finish.", price=899, image="https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=900", sizes="S,M,L,XL,XXL", stock=15, featured=True),
            Product(name="Everyday Cotton T-Shirt", category="T-Shirts", description="Soft cotton comfort for daily wear.", price=499, image="https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=900", sizes="S,M,L,XL,XXL", stock=20, featured=True),
            Product(name="Smart Casual Jacket", category="Jackets", description="A light layer for a sharp casual look.", price=1599, image="https://images.unsplash.com/photo-1551028719-00167b16eac5?w=900", sizes="M,L,XL,XXL", stock=8, featured=True),
            Product(name="Slim Fit Denim", category="Jeans", description="A modern everyday denim fit.", price=1299, image="https://images.unsplash.com/photo-1542272604-787c3835535d?w=900", sizes="30,32,34,36,38", stock=12, featured=True),
        ]
        db.session.add_all(samples)
    db.session.commit()

with app.app_context():
    seed()

if __name__ == "__main__":
    app.run(debug=True)
