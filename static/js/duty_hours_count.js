// Duty Hours Count Module JS

let uploadedFileId = null;
let downloadFileId = null;

document.addEventListener("DOMContentLoaded", () => {
    const fileInput = document.getElementById("excelFile");
    const uploadZone = document.getElementById("uploadZone");
    const fromSelect = document.getElementById("fromSignOffDateSelect");
    const toSelect = document.getElementById("toSignOffDateSelect");
    const datesSummaryRow = document.getElementById("datesSummaryRow");
    const datesSummaryTableBody = document.getElementById("datesSummaryTableBody");
    const datesSummaryTableFoot = document.getElementById("datesSummaryTableFoot");
    const filterCard = document.getElementById("filterCard");
    const summaryRow = document.getElementById("summaryRow");
    const previewContainer = document.getElementById("previewContainer");
    const tableViewport = document.getElementById("tableViewport");
    const totalGroupsEl = document.getElementById("totalGroups");
    const totalRowsEl = document.getElementById("totalRows");
    const btnDownload = document.getElementById("btnDownloadExcel");
    const btnDownloadRouteExcel = document.getElementById("btnDownloadRouteExcel");
    const btnDownloadRouteImage = document.getElementById("btnDownloadRouteImage");
    const btnDownloadDatesExcel = document.getElementById("btnDownloadDatesExcel");
    const selectDateTitle = document.getElementById("selectDateTitle");
    
    // Toast container
    const toastContainer = document.getElementById("dutyHoursToastContainer");

    function showToast(message, type = "primary") {
        const toast = document.createElement("div");
        toast.className = `toast align-items-center text-bg-${type} border-0`;
        toast.role = "alert";
        toast.ariaLive = "assertive";
        toast.ariaAtomic = "true";
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${escapeHtml(message)}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        toastContainer.appendChild(toast);
        const instance = new bootstrap.Toast(toast, { delay: 4000 });
        toast.addEventListener("hidden.bs.toast", () => toast.remove());
        instance.show();
    }

    function escapeHtml(value) {
        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function parseDate(dateStr) {
        if (!dateStr) return null;
        const parts = dateStr.split('-');
        if (parts.length === 3) {
            return new Date(parts[2], parts[1] - 1, parts[0]);
        }
        return null;
    }

    // Drag and Drop
    ["dragenter", "dragover"].forEach(eventName => {
        uploadZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            uploadZone.classList.add("dragover");
        }, false);
    });

    ["dragleave", "drop"].forEach(eventName => {
        uploadZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            uploadZone.classList.remove("dragover");
        }, false);
    });

    uploadZone.addEventListener("drop", (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            fileInput.files = files;
            handleFileUpload(files[0]);
        }
    });

    uploadZone.addEventListener("click", () => {
        fileInput.click();
    });

    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            handleFileUpload(fileInput.files[0]);
        }
    });

    // Upload File
    async function handleFileUpload(file) {
        const lowerName = (file && file.name) ? file.name.toLowerCase() : ""; if (!lowerName.endsWith(".xlsx") && !lowerName.endsWith(".xls")) {
            showToast("Invalid file format. Please select an Excel file (.xlsx/.xls).", "danger");
            return;
        }

        // Show uploading state
        uploadZone.innerHTML = `
            <div class="spinner-border text-primary mb-2" role="status"></div>
            <div>Uploading and processing file...</div>
        `;

        const formData = new FormData();
        formData.append("file", file);

        try {
            const response = await fetch("/api/duty-hours/upload", {
                method: "POST",
                body: formData
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Upload failed.");
            }

            uploadedFileId = data.file_id;
            
            // Populate From/To Date dropdowns
            fromSelect.innerHTML = '<option value="">-- From Date --</option>';
            toSelect.innerHTML = '<option value="">-- To Date --</option>';
            const datesList = Array.isArray(data.unique_dates) ? data.unique_dates : (Array.isArray(data.dates) ? data.dates : []); datesList.forEach(date => {
                const optFrom = document.createElement("option");
                optFrom.value = date;
                optFrom.textContent = date;
                fromSelect.appendChild(optFrom);

                const optTo = document.createElement("option");
                optTo.value = date;
                optTo.textContent = date;
                toSelect.appendChild(optTo);
            });

            // Populate dates summary table
            if (datesSummaryTableFoot) datesSummaryTableFoot.innerHTML = "";
            if (data.dates_summary_data && data.dates_summary_data.length > 0) {
                datesSummaryTableBody.innerHTML = "";
                data.dates_summary_data.forEach(item => {
                    const tr = document.createElement("tr");
                    tr.innerHTML = `
                        <td class="ps-3 text-start fw-medium">${item.date}</td>
                        <td class="text-end fw-semibold text-primary total-col">${item.total}</td>
                        <td class="text-end slab-nos">${item.le_4 ?? 0}</td>
                        <td class="text-end slab-pct">${item.le_4_pct ?? "0.0%"}</td>
                        <td class="text-end slab-nos">${item.slab_4_9 ?? 0}</td>
                        <td class="text-end slab-pct">${item.slab_4_9_pct ?? "0.0%"}</td>
                        <td class="text-end slab-nos">${item.slab_9_12 ?? 0}</td>
                        <td class="text-end slab-pct">${item.slab_9_12_pct ?? "0.0%"}</td>
                        <td class="text-end slab-nos">${item["12_14"] ?? 0}</td>
                        <td class="text-end slab-pct">${item["12_14_pct"] ?? "0.0%"}</td>
                        <td class="text-end slab-nos">${item.over_14 ?? 0}</td>
                        <td class="text-end pe-3 slab-pct">${item.over_14_pct ?? "0.0%"}</td>
                    `;
                    datesSummaryTableBody.appendChild(tr);
                });

                // Populate total row if multiple dates or summary_totals available
                if (data.summary_totals && datesSummaryTableFoot) {
                    const tot = data.summary_totals;
                    const footTr = document.createElement("tr");
                    footTr.innerHTML = `
                        <td class="ps-3 text-start fw-bold">Total</td>
                        <td class="text-end fw-bold text-primary total-col">${tot.total}</td>
                        <td class="text-end slab-nos">${tot.le_4}</td>
                        <td class="text-end slab-pct">${tot.le_4_pct}</td>
                        <td class="text-end slab-nos">${tot.slab_4_9}</td>
                        <td class="text-end slab-pct">${tot.slab_4_9_pct}</td>
                        <td class="text-end slab-nos">${tot.slab_9_12}</td>
                        <td class="text-end slab-pct">${tot.slab_9_12_pct}</td>
                        <td class="text-end slab-nos">${tot["12_14"]}</td>
                        <td class="text-end slab-pct">${tot["12_14_pct"]}</td>
                        <td class="text-end slab-nos">${tot.over_14}</td>
                        <td class="text-end pe-3 slab-pct">${tot.over_14_pct}</td>
                    `;
                    datesSummaryTableFoot.appendChild(footTr);
                }

                datesSummaryRow.classList.remove("d-none");
            } else if (data.dates_summary) {
                datesSummaryTableBody.innerHTML = `<tr><td colspan="12" class="text-center text-muted py-3">${data.dates_summary}</td></tr>`;
                datesSummaryRow.classList.remove("d-none");
            } else {
                datesSummaryRow.classList.add("d-none");
            }

            // Reveal controls
            filterCard.classList.remove("d-none");
            previewContainer.classList.add("d-none");
            summaryRow.classList.add("d-none");
            btnDownload.disabled = true;
            if (btnDownloadRouteExcel) btnDownloadRouteExcel.disabled = true;
            if (btnDownloadRouteImage) btnDownloadRouteImage.disabled = true;

            showToast("Excel workbook loaded successfully!", "success");

        } catch (error) {
            showToast(error.message, "danger");
        } finally {
            // Restore upload zone text
            uploadZone.innerHTML = `
                <i class="bi bi-file-earmark-excel"></i>
                <h5>Drag & drop your Excel report here</h5>
                <p class="text-muted small">or click to browse files</p>
            `;
        }
    }

    const dutySlabSelect = document.getElementById("dutySlabSelect");

    // Both dropdowns trigger filter
    async function triggerFilter() {
        const fromDate = fromSelect.value;
        const toDate = toSelect.value;
        const selectedSlab = dutySlabSelect ? dutySlabSelect.value : "all";
        
        if (!fromDate || !toDate) {
            previewContainer.classList.add("d-none");
            summaryRow.classList.add("d-none");
            btnDownload.disabled = true;
            if (btnDownloadRouteExcel) btnDownloadRouteExcel.disabled = true;
            if (btnDownloadRouteImage) btnDownloadRouteImage.disabled = true;
            return;
        }

        tableViewport.innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border text-primary mb-2" role="status"></div>
                <div>Filtering duties and rendering preview...</div>
            </div>
        `;
        previewContainer.classList.remove("d-none");
        summaryRow.classList.add("d-none");
        btnDownload.disabled = true;
        if (btnDownloadRouteExcel) btnDownloadRouteExcel.disabled = true;
        if (btnDownloadRouteImage) btnDownloadRouteImage.disabled = true;

        try {
            const response = await fetch("/api/duty-hours/filter", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    file_id: uploadedFileId,
                    from_date: fromDate,
                    to_date: toDate,
                    duty_slab: selectedSlab
                })
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Filtering failed.");
            }

            // Update summary
            let titleText = fromDate === toDate ? fromDate : `${fromDate} to ${toDate}`;
            if (selectedSlab !== "all" && dutySlabSelect) {
                titleText += ` (${dutySlabSelect.options[dutySlabSelect.selectedIndex].text})`;
            }
            selectDateTitle.textContent = titleText;
            totalGroupsEl.textContent = data.total_groups;
            totalRowsEl.textContent = data.total_rows;

            // Track ChartJS instances globally/module scope in js
            if (!window.routeDutiesChartInst) window.routeDutiesChartInst = null;
            if (!window.routeAvgDutyChartInst) window.routeAvgDutyChartInst = null;
            if (!window.routeAvgWheelChartInst) window.routeAvgWheelChartInst = null;

            // Populate Route-wise Summary Table
            const routeSummaryBody = document.querySelector("#routeSummaryTable tbody");
            if (routeSummaryBody) {
                routeSummaryBody.innerHTML = "";
                if (data.route_summary && data.route_summary.length > 0) {
                    data.route_summary.forEach(item => {
                        const tr = document.createElement("tr");
                        tr.innerHTML = `
                            <td class="text-dark fw-medium border-0">${escapeHtml(item.route)}</td>
                            <td class="text-end border-0">${item.duty_count}</td>
                            <td class="text-end border-0 fw-semibold text-primary">${item.avg_duty_hours}</td>
                            <td class="text-end border-0 fw-semibold text-success">${item.avg_wheel_movement || "00:00"}</td>
                        `;
                        routeSummaryBody.appendChild(tr);
                    });
                } else {
                    routeSummaryBody.innerHTML = '<tr><td colspan="4" class="text-center text-muted border-0 py-3">No route data available</td></tr>';
                }
            }

            // Render Route-wise Charts
            if (data.route_summary && data.route_summary.length > 0) {
                // Keep top 8 routes for readability
                const sortedRoutes = [...data.route_summary].sort((a, b) => b.duty_count - a.duty_count).slice(0, 8);
                const labels = sortedRoutes.map(x => x.route);
                const counts = sortedRoutes.map(x => x.duty_count);
                
                const parseTimeToHoursFloat = (timeStr) => {
                    if (!timeStr) return 0;
                    const parts = timeStr.split(':');
                    if (parts.length >= 2) {
                        return parseFloat(parts[0]) + parseFloat(parts[1]) / 60.0;
                    }
                    return parseFloat(timeStr) || 0;
                };

                const avgDutyHrs = sortedRoutes.map(x => parseTimeToHoursFloat(x.avg_duty_hours));
                const avgWheelHrs = sortedRoutes.map(x => parseTimeToHoursFloat(x.avg_wheel_movement));

                // 1. Duties Count Chart
                if (window.routeDutiesChartInst) window.routeDutiesChartInst.destroy();
                const ctx1 = document.getElementById("routeDutiesChart").getContext("2d");
                window.routeDutiesChartInst = new Chart(ctx1, {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Duties Count',
                            data: counts,
                            backgroundColor: 'rgba(30, 58, 138, 0.75)',
                            borderColor: 'rgba(30, 58, 138, 1)',
                            borderWidth: 1.5,
                            borderRadius: 4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: { y: { beginAtZero: true } }
                    }
                });

                // 2. Avg Duty Hours Chart
                if (window.routeAvgDutyChartInst) window.routeAvgDutyChartInst.destroy();
                const ctx2 = document.getElementById("routeAvgDutyChart").getContext("2d");
                window.routeAvgDutyChartInst = new Chart(ctx2, {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Avg Duty Hours (hrs)',
                            data: avgDutyHrs,
                            backgroundColor: 'rgba(13, 148, 136, 0.75)',
                            borderColor: 'rgba(13, 148, 136, 1)',
                            borderWidth: 1.5,
                            borderRadius: 4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: { y: { beginAtZero: true } }
                    }
                });

                // 3. Avg Wheel Movement Chart
                if (window.routeAvgWheelChartInst) window.routeAvgWheelChartInst.destroy();
                const ctx3 = document.getElementById("routeAvgWheelChart").getContext("2d");
                window.routeAvgWheelChartInst = new Chart(ctx3, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Avg Wheel Movement (hrs)',
                            data: avgWheelHrs,
                            backgroundColor: 'rgba(217, 119, 6, 0.2)',
                            borderColor: 'rgba(217, 119, 6, 1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.3
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: { y: { beginAtZero: true } }
                    }
                });
            }

            summaryRow.classList.remove("d-none");

            // Update preview
            tableViewport.innerHTML = data.html_preview;

            // Enable downloads
            downloadFileId = data.download_id;
            btnDownload.disabled = false;
            if (btnDownloadRouteExcel) btnDownloadRouteExcel.disabled = false;
            if (btnDownloadRouteImage) btnDownloadRouteImage.disabled = false;

            showToast("Duties filtered successfully!", "success");

        } catch (error) {
            tableViewport.innerHTML = `
                <div class="alert alert-danger m-3">
                    <i class="bi bi-exclamation-triangle-fill"></i> ${escapeHtml(error.message)}
                </div>
            `;
            if (btnDownloadRouteExcel) btnDownloadRouteExcel.disabled = true;
            if (btnDownloadRouteImage) btnDownloadRouteImage.disabled = true;
            showToast(error.message, "danger");
        }
    }

    // Sync From/To selectors
    fromSelect.addEventListener("change", () => {
        const fromVal = fromSelect.value;
        const toVal = toSelect.value;
        if (fromVal) {
            if (!toVal) {
                toSelect.value = fromVal;
            } else {
                const fromD = parseDate(fromVal);
                const toD = parseDate(toVal);
                if (fromD && toD && fromD > toD) {
                    toSelect.value = fromVal;
                }
            }
        }
        triggerFilter();
    });

    toSelect.addEventListener("change", () => {
        const fromVal = fromSelect.value;
        const toVal = toSelect.value;
        if (toVal) {
            if (!fromVal) {
                fromSelect.value = toVal;
            } else {
                const fromD = parseDate(fromVal);
                const toD = parseDate(toVal);
                if (fromD && toD && fromD > toD) {
                    fromSelect.value = toVal;
                }
            }
        }
        triggerFilter();
    });

    if (dutySlabSelect) {
        dutySlabSelect.addEventListener("change", triggerFilter);
    }

    // Download Button Click
    btnDownload.addEventListener("click", () => {
        if (!downloadFileId) return;
        window.location.href = `/api/duty-hours/download/${downloadFileId}`;
    });

    // Download Route-wise Summary as Excel
    if (btnDownloadRouteExcel) {
        btnDownloadRouteExcel.addEventListener("click", () => {
            if (!uploadedFileId) return;
            const fromDate = fromSelect.value;
            const toDate = toSelect.value;
            const selectedSlab = dutySlabSelect ? dutySlabSelect.value : "all";
            window.location.href = `/api/duty-hours/download-route-summary?file_id=${uploadedFileId}&from_date=${fromDate}&to_date=${toDate}&duty_slab=${selectedSlab}`;
        });
    }

    // Download Route-wise Summary as Image (html2canvas)
    if (btnDownloadRouteImage) {
        btnDownloadRouteImage.addEventListener("click", () => {
            const card = document.getElementById("routeSummaryCard");
            if (!card) return;
            
            const actions = document.getElementById("routeSummaryActions");
            if (actions) actions.style.display = 'none'; // hide buttons in captured image
            
            html2canvas(card, {
                backgroundColor: "#ffffff",
                scale: 2
            }).then(canvas => {
                if (actions) actions.style.display = 'flex'; // restore buttons
                
                const link = document.createElement("a");
                const fromVal = fromSelect.value;
                const toVal = toSelect.value;
                const date_str = fromVal === toVal ? fromVal : `${fromVal}_to_${toVal}`;
                link.download = `Route_Wise_Summary_${date_str}.png`;
                link.href = canvas.toDataURL("image/png");
                link.click();
            }).catch(err => {
                if (actions) actions.style.display = 'flex';
                showToast("Failed to generate image: " + err.message, "danger");
            });
        });
    }

    // Download Available Sign Off Dates Summary as Excel
    if (btnDownloadDatesExcel) {
        btnDownloadDatesExcel.addEventListener("click", () => {
            if (!uploadedFileId) return;
            window.location.href = `/api/duty-hours/download-dates-summary?file_id=${uploadedFileId}`;
        });
    }
});

// String endswith Polyfill
if (!String.prototype.endswith) {
    String.prototype.endswith = function(suffix) {
        return this.indexOf(suffix, this.length - suffix.length) !== -1;
    };
}
