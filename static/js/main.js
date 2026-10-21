document.addEventListener("DOMContentLoaded", () => {
  const flashes = document.querySelectorAll(".flash");
  flashes.forEach((item) => {
    window.setTimeout(() => {
      item.style.transition = "opacity .35s ease";
      item.style.opacity = "0";
      window.setTimeout(() => item.remove(), 400);
    }, 4500);
  });
});
