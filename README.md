# Men's Wear Store — Flask starter project

A responsive starter e-commerce website for a home-based men's clothing business. It includes a product catalogue, category/search filters, product details, session cart, checkout, COD/manual payment selection, local delivery/courier choice, order confirmation, and an admin dashboard.

## Run on Windows

1. Install Python 3.10 or newer.
2. Extract this ZIP.
3. Open PowerShell in the `menswear_store` folder.
4. Create and activate a virtual environment:

```powershell
py -m venv venv
.\venv\Scripts\activate
```

5. Install dependencies:

```powershell
pip install -r requirements.txt
```

6. Start the website:

```powershell
python app.py
```

7. Open `http://127.0.0.1:5000` in your browser.

## Admin login

- URL: `http://127.0.0.1:5000/admin/login`
- Username: `admin`
- Password: `ChangeMe123!`

**Immediately change the starter admin password before using this on a public server.** This demo uses a simple starter login and is not production hardened.

## Add your real products

Sign in to the admin panel → Add product. Add the product name, category, price, sizes, stock, description and an image URL. For a first demo, use public image URLs. For a real store, implement secure image uploads and store product images in managed storage.

## Important before taking real orders

This is a working starter/MVP, not a fully production-ready commerce system:
- Checkout currently records orders in the local SQLite database.
- Payment choices are Cash on Delivery or payment arranged directly with the seller. No card/UPI payment gateway is connected.
- Courier charges, GST/tax invoices, shipping labels, email/SMS/WhatsApp notifications, returns/refunds and customer accounts are not implemented.
- The sample product photos are remote demo images; replace them with photos you own or have permission to use.
- Before public launch, add CSRF protection, rate limiting, secure admin password management, HTTPS, backups, privacy/terms/returns pages, input validation, and a production database.
- Never collect or store card numbers, UPI PINs, OTPs or banking passwords on this website.

## Suggested next phase

1. Add your brand name, logo, real product photos and contact details.
2. Add customer accounts, order history and saved addresses.
3. Integrate a trusted payment provider using its official hosted checkout.
4. Add courier/shipping integration and delivery charge rules.
5. Add multi-vendor onboarding only after your own store is stable.


## Extended admin features
- Owner-only staff account management at `/admin/accounts` (create, disable, and enable staff logins).
- Roles: owner, manager, orders, and inventory.
- Customer directory at `/admin/customers`, grouped by checkout phone number.
- Sales and stock summary at `/admin/analytics`.
- Low-stock alerts and best-selling product summary.

The customer directory is based on guest checkout records; customer self-service login/accounts are not included yet. Sales summaries are operational estimates, not accounting reports. This is still a development starter: before public launch add CSRF protection, secure production secrets, HTTPS, backups, audit logs, privacy notices, and proper deployment configuration.
