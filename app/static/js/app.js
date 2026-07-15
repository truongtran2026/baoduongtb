function togglePanel(id) {
  const el = document.getElementById(id);
  if (el) el.classList.toggle("open");
}

document.addEventListener("submit", (e) => {
  const form = e.target;
  if (form.dataset.confirm) {
    if (!confirm(form.dataset.confirm)) {
      e.preventDefault();
    }
  }
});
