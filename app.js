document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".product-image img, .detail-image img").forEach(img => {
    img.addEventListener("error", () => { img.style.display = "none"; });
  });
});
