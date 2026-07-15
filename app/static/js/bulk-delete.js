(() => {
  document.querySelectorAll(".bulk-form").forEach((form) => {
    const formId = form.id;
    const items = () => Array.from(document.querySelectorAll(`.bulk-item[data-form="${formId}"]`));
    const selectAll = document.querySelector(`.bulk-select-all[data-form="${formId}"]`);
    const submitBtn = document.querySelector(`.bulk-submit[form="${formId}"]`);
    const countEl = submitBtn ? submitBtn.querySelector(".bulk-count") : null;
    const itemLabel = form.dataset.itemLabel || "mục";

    function refresh() {
      const all = items();
      const checked = all.filter((i) => i.checked);
      if (countEl) countEl.textContent = checked.length;
      if (submitBtn) submitBtn.disabled = checked.length === 0;
      if (selectAll) {
        selectAll.checked = all.length > 0 && checked.length === all.length;
        selectAll.indeterminate = checked.length > 0 && checked.length < all.length;
      }
    }

    items().forEach((cb) => cb.addEventListener("change", refresh));
    if (selectAll) {
      selectAll.addEventListener("change", () => {
        items().forEach((cb) => (cb.checked = selectAll.checked));
        refresh();
      });
    }

    form.addEventListener("submit", (e) => {
      const checked = items().filter((i) => i.checked);
      if (checked.length === 0) {
        e.preventDefault();
        return;
      }
      if (!confirm(`Xoá ${checked.length} ${itemLabel} đã chọn? Không thể hoàn tác.`)) {
        e.preventDefault();
      }
    });

    refresh();
  });
})();
