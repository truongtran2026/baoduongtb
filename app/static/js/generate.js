(() => {
  const stationSelect = document.getElementById("stationSelect");
  if (!stationSelect) return;

  const categoryWrap = document.getElementById("categoryWrap");
  const categoryPicker = document.getElementById("categoryPicker");
  const categoryEmptyHint = document.getElementById("categoryEmptyHint");
  const step2 = document.getElementById("step2");
  const step3 = document.getElementById("step3");
  const step4 = document.getElementById("step4");
  const performedBy = document.getElementById("performedBy");
  const coworker = document.getElementById("coworker");
  const peopleWarning = document.getElementById("peopleWarning");
  const maintenanceDate = document.getElementById("maintenanceDate");
  const deviceSearch = document.getElementById("deviceSearch");
  const deviceList = document.getElementById("deviceList");
  const deviceSelectedCount = document.getElementById("deviceSelectedCount");
  const deviceTotalCount = document.getElementById("deviceTotalCount");
  const selectAllBtn = document.getElementById("selectAllBtn");
  const selectNoneBtn = document.getElementById("selectNoneBtn");
  const generateBtn = document.getElementById("generateBtn");
  const generateBtnLabel = document.getElementById("generateBtnLabel");
  const generateHint = document.getElementById("generateHint");
  const resultCard = document.getElementById("resultCard");

  let selectedCategoryId = null;
  let devices = [];

  function escapeHtml(str) {
    return String(str ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  function setEnabled(el, enabled) {
    el.classList.toggle("enabled", enabled);
  }

  async function fetchJson(url, options) {
    const res = await fetch(url, options);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const err = new Error(data.detail || "Có lỗi xảy ra");
      err.data = data;
      throw err;
    }
    return data;
  }

  stationSelect.addEventListener("change", async () => {
    const stationId = stationSelect.value;
    selectedCategoryId = null;
    categoryPicker.innerHTML = "";
    resultCard.innerHTML = "";
    setEnabled(step2, false);
    setEnabled(step3, false);
    setEnabled(step4, false);
    resetDeviceList("Hãy chọn trạm và mục bảo dưỡng ở bước 1.");
    updateGenerateState();

    if (!stationId) {
      categoryWrap.style.display = "none";
      return;
    }
    categoryWrap.style.display = "block";

    const [categories, employees] = await Promise.all([
      fetchJson(`/api/generate/categories?station_id=${stationId}`),
      fetchJson(`/api/generate/employees?station_id=${stationId}`),
    ]);

    categoryEmptyHint.style.display = categories.length ? "none" : "block";
    categoryPicker.innerHTML = categories.map((c) => `
      <div class="category-option ${c.has_template ? "" : "no-template"}" data-id="${c.id}">
        <div class="cat-name">${escapeHtml(c.name)}</div>
        <div class="cat-meta">${c.device_count} thiết bị${c.has_template ? "" : " · chưa có file mẫu"}</div>
      </div>
    `).join("");
    categoryPicker.querySelectorAll(".category-option").forEach((el) => {
      el.addEventListener("click", () => selectCategory(parseInt(el.dataset.id, 10)));
    });

    performedBy.innerHTML = '<option value="">-- Chọn người thực hiện --</option>' +
      employees.map((e) => `<option value="${escapeHtml(e.name)}">${escapeHtml(e.name)}</option>`).join("");
    coworker.innerHTML = '<option value="">-- Không có --</option>' +
      employees.map((e) => `<option value="${escapeHtml(e.name)}">${escapeHtml(e.name)}</option>`).join("");

    setEnabled(step2, true);
  });

  function selectCategory(categoryId) {
    selectedCategoryId = categoryId;
    categoryPicker.querySelectorAll(".category-option").forEach((el) => {
      el.classList.toggle("selected", parseInt(el.dataset.id, 10) === categoryId);
    });
    loadDevices();
    setEnabled(step3, true);
  }

  async function loadDevices() {
    const stationId = stationSelect.value;
    if (!stationId || !selectedCategoryId) return;
    resetDeviceList("Đang tải...");
    devices = await fetchJson(`/api/generate/devices?station_id=${stationId}&category_id=${selectedCategoryId}`);
    devices = devices.map((d) => ({ ...d, selected: true }));
    renderDeviceList();
  }

  function resetDeviceList(message) {
    deviceList.innerHTML = `<div class="device-empty">${escapeHtml(message)}</div>`;
    deviceTotalCount.textContent = "0";
    deviceSelectedCount.textContent = "0";
  }

  function renderDeviceList() {
    if (!devices.length) {
      resetDeviceList("Không có thiết bị nào cho lựa chọn này.");
      updateGenerateState();
      return;
    }
    deviceList.innerHTML = devices.map((d) => `
      <label class="device-row" data-name="${escapeHtml(d.name.toLowerCase())}">
        <input type="checkbox" data-id="${d.id}" ${d.selected ? "checked" : ""}>
        <div>
          <div class="device-name">${escapeHtml(d.name)}</div>
          <div class="device-meta">${escapeHtml(d.record_no || "")}${d.configuration ? " · " + escapeHtml(d.configuration) : ""}</div>
        </div>
      </label>
    `).join("");
    deviceList.querySelectorAll('input[type=checkbox]').forEach((cb) => {
      cb.addEventListener("change", () => {
        const id = parseInt(cb.dataset.id, 10);
        const d = devices.find((x) => x.id === id);
        if (d) d.selected = cb.checked;
        updateCounts();
      });
    });
    updateCounts();
  }

  function updateCounts() {
    const total = devices.length;
    const selected = devices.filter((d) => d.selected).length;
    deviceTotalCount.textContent = total;
    deviceSelectedCount.textContent = selected;
    updateGenerateState();
  }

  deviceSearch.addEventListener("input", () => {
    const q = deviceSearch.value.trim().toLowerCase();
    deviceList.querySelectorAll(".device-row").forEach((row) => {
      row.style.display = row.dataset.name.includes(q) ? "" : "none";
    });
  });

  selectAllBtn.addEventListener("click", () => {
    devices.forEach((d) => (d.selected = true));
    renderDeviceList();
  });
  selectNoneBtn.addEventListener("click", () => {
    devices.forEach((d) => (d.selected = false));
    renderDeviceList();
  });

  [maintenanceDate, performedBy, coworker].forEach((el) => el.addEventListener("change", updateGenerateState));

  function updateGenerateState() {
    const hasStation = !!stationSelect.value;
    const hasCategory = !!selectedCategoryId;
    const hasDate = !!maintenanceDate.value;
    const hasPerformer = !!performedBy.value;
    const samePerson = coworker.value && coworker.value === performedBy.value;
    const selectedDevices = devices.filter((d) => d.selected).length;

    peopleWarning.style.display = samePerson ? "block" : "none";
    setEnabled(step4, hasStation && hasCategory);

    const ready = hasStation && hasCategory && hasDate && hasPerformer && !samePerson && selectedDevices > 0;
    generateBtn.disabled = !ready;
    generateHint.textContent = ready
      ? `Sẵn sàng tạo ${selectedDevices} hồ sơ bảo dưỡng.`
      : "Hoàn tất các bước trên để tiếp tục.";
  }

  generateBtn.addEventListener("click", async () => {
    const deviceIds = devices.filter((d) => d.selected).map((d) => d.id);
    generateBtn.disabled = true;
    generateBtnLabel.innerHTML = '<span class="spinner"></span> Đang tạo file...';
    resultCard.innerHTML = "";

    try {
      const payload = {
        station_id: parseInt(stationSelect.value, 10),
        category_id: selectedCategoryId,
        maintenance_date: maintenanceDate.value,
        performed_by: performedBy.value,
        coworker: coworker.value,
        device_ids: deviceIds,
      };
      const result = await fetchJson("/api/generate/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      renderResult(result);
    } catch (err) {
      resultCard.innerHTML = `<div class="card"><div class="flash flash-error" style="margin:0;">⚠ ${escapeHtml(err.message)}</div></div>`;
    } finally {
      generateBtnLabel.textContent = "Tạo hồ sơ bảo dưỡng";
      updateGenerateState();
    }
  });

  function statusBadge(status) {
    if (status === "success") return '<span class="badge badge-success">✓ Thành công</span>';
    if (status === "warning") return '<span class="badge badge-warning">⚠ Cảnh báo</span>';
    return '<span class="badge badge-danger">✗ Lỗi</span>';
  }

  function renderResult(result) {
    const rows = result.files.map((f) => `
      <tr>
        <td>${escapeHtml(f.device_name)}</td>
        <td>${escapeHtml(f.filename)}</td>
        <td>${statusBadge(f.status)}</td>
        <td class="text-muted">${escapeHtml(f.message || "")}</td>
      </tr>
    `).join("");

    resultCard.innerHTML = `
      <div class="card" style="margin-top:20px;">
        <div class="card-title">Kết quả tạo hồ sơ</div>
        <div class="card-subtitle">Thư mục lưu: ${escapeHtml(result.output_folder)}</div>
        <div class="result-summary">
          <div class="stat-card"><div class="stat-value">${result.requested_count}</div><div class="stat-label">Yêu cầu</div></div>
          <div class="stat-card"><div class="stat-value" style="color:var(--green-600)">${result.success_count}</div><div class="stat-label">Thành công</div></div>
          <div class="stat-card"><div class="stat-value" style="color:var(--amber-600)">${result.warning_count}</div><div class="stat-label">Cảnh báo</div></div>
          <div class="stat-card"><div class="stat-value" style="color:var(--red-600)">${result.error_count}</div><div class="stat-label">Lỗi</div></div>
        </div>
        <div class="header-actions" style="margin-bottom:16px;">
          <a class="btn btn-primary" href="/history/${result.run_id}/download">⬇ Tải về (ZIP)</a>
          ${result.can_open_locally ? `<button type="button" class="btn btn-secondary" id="openFolderBtn">📂 Mở thư mục</button>` : ""}
          <a class="btn btn-secondary" href="/history/${result.run_id}">Xem chi tiết trong Lịch sử</a>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>Thiết bị</th><th>Tên file</th><th>Trạng thái</th><th>Ghi chú</th></tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </div>
    `;

    const openBtn = document.getElementById("openFolderBtn");
    if (openBtn) {
      openBtn.addEventListener("click", () => {
        fetch(`/history/${result.run_id}/open-folder`, { method: "POST" });
      });
    }
    resultCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
})();
