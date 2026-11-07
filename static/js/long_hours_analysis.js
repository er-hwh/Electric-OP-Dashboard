$(document).ready(function() {
    // Default dates (last one week)
    const today = new Date();
    const past7 = new Date(today.getTime() - (7 * 24 * 60 * 60 * 1000));
    
    const formatDate = (d) => {
        const yyyy = d.getFullYear();
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const dd = String(d.getDate()).padStart(2, '0');
        return `${yyyy}-${mm}-${dd}`;
    };
    
    // Set default dates
    $("#fromDate").val(formatDate(past7));
    $("#toDate").val(formatDate(today));
    
    // Init DataTable
    let recordsTable = null;
    let overallSlotsDoughnutChart = null;
    let sectionSlotsBarChart = null;
    
    // Load summary and sections list on startup
    loadSummary();
    loadDetailedAnalysis();
    initRecordsTable();
    loadSectionDropdowns();
    
    // Event listeners for filters
    $("#applyFiltersBtn").click(function() {
        loadSummary();
        loadDetailedAnalysis();
        initRecordsTable();
    });
    
    $("#resetFiltersBtn").click(function() {
        $("#fromDate").val(formatDate(past7));
        $("#toDate").val(formatDate(today));
        $("#filterCategory").val("");
        $("#filterSection").val("");
        $("#filterTrain").val("");
        $("#filterLoco").val("");
        $("#filterCrew").val("");
        $("#filterDenominator").val("4665");
        
        loadSummary();
        loadDetailedAnalysis();
        initRecordsTable();
    });
    
    $("#syncDutyHoursBtn").click(function() {
        const btn = $(this);
        const originalHtml = btn.html();
        btn.prop("disabled", true).html('<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>Syncing...');
        
        $.ajax({
            url: "/tools/long-hours-analysis/sync-duty-hours",
            type: "POST",
            success: function(response) {
                alert("Successfully synced " + response.synced_count + " records with Duty Hours database.");
                loadSummary();
                loadDetailedAnalysis();
                initRecordsTable();
            },
            error: function(xhr) {
                alert("Error during sync: " + (xhr.responseJSON?.detail || xhr.responseText));
            },
            complete: function() {
                btn.prop("disabled", false).html(originalHtml);
            }
        });
    });

    // Daily Total Duties Upload Handler
    $("#totalDutiesUploadForm").on("submit", function(e) {
        e.preventDefault();
        const fileInput = document.getElementById("totalDutiesFile");
        if (fileInput.files.length === 0) {
            alert("Please select the total duties Excel file first.");
            return;
        }

        const formData = new FormData();
        formData.append("file", fileInput.files[0]);

        $("#totalDutiesUploadStatus")
            .removeClass("d-none alert-danger alert-success")
            .addClass("alert-info")
            .html('<i class="bi bi-hourglass-split me-1"></i> Updating total duties. Please wait...');
        $("#totalDutiesUploadBtn").prop("disabled", true);

        $.ajax({
            url: "/tools/long-hours-analysis/total-duties/upload",
            type: "POST",
            data: formData,
            processData: false,
            contentType: false,
            success: function(response) {
                $("#totalDutiesUploadBtn").prop("disabled", false);
                if (response.success) {
                    $("#totalDutiesUploadStatus").removeClass("alert-info").addClass("alert-success").html(`
                        <strong><i class="bi bi-check-circle-fill me-1"></i> Total Duties Updated!</strong><br>
                        Dates: ${response.dates_updated} | Total Duties: ${Number(response.total_duties || 0).toLocaleString()}<br>
                        Range: ${response.from_date} to ${response.to_date}
                    `);
                    fileInput.value = "";
                    loadSummary();
                } else {
                    $("#totalDutiesUploadStatus").removeClass("alert-info").addClass("alert-danger").html(`<i class="bi bi-exclamation-triangle-fill me-1"></i> Error: ${response.detail || "Upload failed"}`);
                }
            },
            error: function(xhr) {
                $("#totalDutiesUploadBtn").prop("disabled", false);
                const err = xhr.responseJSON ? xhr.responseJSON.detail : "An error occurred during total duties upload.";
                $("#totalDutiesUploadStatus").removeClass("alert-info").addClass("alert-danger").html(`<i class="bi bi-exclamation-triangle-fill me-1"></i> Error: ${err}`);
            }
        });
    });
    
    // Trigger summaries when category filter is changed directly
    $("#filterCategory").change(function() {
        // Reload sections dropdown to match category
        loadSectionDropdowns();
    });

    // File Upload Handler
    $("#uploadForm").on("submit", function(e) {
        e.preventDefault();
        const fileInput = document.getElementById("excelFile");
        if (fileInput.files.length === 0) {
            alert("Please select an Excel file first.");
            return;
        }
        
        const formData = new FormData();
        formData.append("file", fileInput.files[0]);
        
        $("#uploadStatus").removeClass("d-none alert-danger alert-success").addClass("alert-info").html('<i class="bi bi-hourglass-split me-1"></i> Processing file. Please wait...');
        $("#uploadBtn").prop("disabled", true);
        
        $.ajax({
            url: "/tools/long-hours-analysis/upload",
            type: "POST",
            data: formData,
            processData: false,
            contentType: false,
            success: function(response) {
                $("#uploadBtn").prop("disabled", false);
                if (response.success) {
                    $("#uploadStatus").removeClass("alert-info").addClass("alert-success").html(`
                        <strong><i class="bi bi-check-circle-fill me-1"></i> Import Successful!</strong><br>
                        File: ${response.filename}<br>
                        Total Rows Processed: ${response.total_rows}<br>
                        Inserted: ${response.inserted} | Updated: ${response.updated}
                    `);
                    
                    // Reload data
                    loadSummary();
                    loadDetailedAnalysis();
                    loadSectionDropdowns();
                    initRecordsTable();
                } else {
                    $("#uploadStatus").removeClass("alert-info").addClass("alert-danger").html(`<i class="bi bi-exclamation-triangle-fill me-1"></i> Error: ${response.detail || "Upload failed"}`);
                }
            },
            error: function(xhr) {
                $("#uploadBtn").prop("disabled", false);
                const err = xhr.responseJSON ? xhr.responseJSON.detail : "An error occurred during upload.";
                $("#uploadStatus").removeClass("alert-info").addClass("alert-danger").html(`<i class="bi bi-exclamation-triangle-fill me-1"></i> Error: ${err}`);
            }
        });
    });

    // Toggle all columns check
    $("#selectAllCols").change(function() {
        $(".col-checkbox").prop("checked", $(this).prop("checked"));
    });

    // Export Summary Excel
    function triggerSummaryExport(bracket) {
        const fromDate = $("#fromDate").val();
        const toDate = $("#toDate").val();
        const category = $("#filterCategory").val();
        const section = $("#filterSection").val();
        const denomVal = $("#filterDenominator").val();
        const denominator = parseInt(denomVal) || 4665;
        
        let url = `/tools/long-hours-analysis/export-summary?denominator=${denominator}`;
        if (fromDate) url += `&from_date=${fromDate}`;
        if (toDate) url += `&to_date=${toDate}`;
        if (category) url += `&category=${encodeURIComponent(category)}`;
        if (section) url += `&section=${encodeURIComponent(section)}`;
        if (bracket) url += `&bracket=${bracket}`;
        
        window.location.href = url;
    }

    $("#exportSummaryGt14Btn").click(function() {
        triggerSummaryExport("gt14");
    });

    $("#exportSummary12to14Btn").click(function() {
        triggerSummaryExport("12to14");
    });

    // Column Selector Modal open
    $("#btnOpenDownloadModal").click(function() {
        // Reset checkbox to checked for main columns
        $("#colModal").modal("show");
    });

    // Execute custom column download
    $("#btnConfirmDownload").click(function() {
        const selectedCols = [];
        $(".col-checkbox:checked").each(function() {
            selectedCols.push($(this).val());
        });
        
        if (selectedCols.length === 0) {
            alert("Please select at least one column to download.");
            return;
        }
        
        const scope = $("input[name='downloadScope']:checked").val();
        const filters = {
            from_date: $("#fromDate").val(),
            to_date: $("#toDate").val(),
            category: $("#filterCategory").val(),
            section: $("#filterSection").val(),
            train: $("#filterTrain").val(),
            loco: $("#filterLoco").val(),
            crew: $("#filterCrew").val()
        };
        
        $("#btnConfirmDownload").prop("disabled", true).html('<span class="spinner-border spinner-border-sm me-1"></span> Exporting...');
        
        fetch('/tools/long-hours-analysis/export-records', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                columns: selectedCols,
                filters: filters,
                scope: scope
            })
        })
        .then(response => {
            if (!response.ok) throw new Error("Export failed");
            return response.blob();
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Long_Hours_Data_Export_${new Date().toISOString().split('T')[0]}.xlsx`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
            
            $("#colModal").modal("hide");
            $("#btnConfirmDownload").prop("disabled", false).html('<i class="bi bi-download me-1"></i> Download Excel');
        })
        .catch(err => {
            alert("Error exporting data: " + err.message);
            $("#btnConfirmDownload").prop("disabled", false).html('<i class="bi bi-download me-1"></i> Download Excel');
        });
    });

    // Load section list for dropdowns
    function loadSectionDropdowns() {
        const category = $("#filterCategory").val();
        let url = "/tools/long-hours-analysis/summary";
        if (category) {
            url += `?category=${encodeURIComponent(category)}`;
        }
        
        $.get(url, function(res) {
            if (res.success) {
                const select = $("#filterSection");
                const currentVal = select.val();
                select.empty().append('<option value="">All Sections</option>');
                
                // Combine unique sections from both brackets
                const sectionsSet = new Set();
                if (res.gt14 && res.gt14.rows) {
                    res.gt14.rows.forEach(item => sectionsSet.add(item.section));
                }
                if (res["12to14"] && res["12to14"].rows) {
                    res["12to14"].rows.forEach(item => sectionsSet.add(item.section));
                }
                
                // Add unique sections sorted alphabetically
                Array.from(sectionsSet).sort().forEach(sec => {
                    select.append(`<option value="${sec}">${sec}</option>`);
                });
                
                if (currentVal) {
                    select.val(currentVal);
                }
            }
        });
    }

    // Load Section-Wise Summary Table
    function loadSummary() {
        const fromDate = $("#fromDate").val();
        const toDate = $("#toDate").val();
        const category = $("#filterCategory").val();
        const section = $("#filterSection").val();
        const denomVal = $("#filterDenominator").val();
        const denominator = parseInt(denomVal) || 4665;
        
        let url = `/tools/long-hours-analysis/summary?denominator=${denominator}`;
        if (fromDate) url += `&from_date=${fromDate}`;
        if (toDate) url += `&to_date=${toDate}`;
        if (category) url += `&category=${encodeURIComponent(category)}`;
        if (section) url += `&section=${encodeURIComponent(section)}`;
        
        $("#summaryTableBodyGt14").html('<tr><td colspan="7" class="text-center py-4"><div class="spinner-border text-primary spinner-border-sm me-2"></div>Loading Summaries...</td></tr>');
        $("#summaryTableBody12to14").html('<tr><td colspan="7" class="text-center py-4"><div class="spinner-border text-primary spinner-border-sm me-2"></div>Loading Summaries...</td></tr>');
        $("#slotsTableBody").html('<tr><td colspan="6" class="text-center py-4"><div class="spinner-border text-primary spinner-border-sm me-2"></div>Loading Time Slot Analysis...</td></tr>');
        
        $.get(url, function(res) {
            if (res.success) {
                // Render Gt14 Summary
                renderSummaryTable(res.gt14, "summaryTableBodyGt14", "gt14");
                // Render 12to14 Summary
                renderSummaryTable(res["12to14"], "summaryTableBody12to14", "12to14");
                // Render Slots Breakdown Table
                renderSlotsTable(res.slots_breakdown);
                // Update Slots Charts
                updateSlotsCharts(res.slots_breakdown);
                
                // Update Metrics Row
                $("#metricTotalDuties").text(res.total_duties_count.toLocaleString());
                
                const gt14Count = res.gt14.total.count || 0;
                const gt14Pct = res.gt14.total.pct_age || 0;
                const ct12to14Count = res["12to14"].total.count || 0;
                const ct12to14Pct = res["12to14"].total.pct_age || 0;
                
                $("#metricGt14Cases").html(`${gt14Count.toLocaleString()} <span style="font-size: 0.95rem; font-weight: 500;">(${gt14Pct.toFixed(2)}%)</span>`);
                $("#metric12to14Cases").html(`${ct12to14Count.toLocaleString()} <span style="font-size: 0.95rem; font-weight: 500;">(${ct12to14Pct.toFixed(2)}%)</span>`);
                
                const lhCountVal = res.long_hours_duties_count || 0;
                const denominatorVal = res.total_duties_count || 1;
                const lhPct = (lhCountVal / denominatorVal) * 100;
                $("#metricTotalLH").html(`${lhCountVal.toLocaleString()} <span style="font-size: 0.95rem; font-weight: 500;">(${lhPct.toFixed(2)}%)</span>`);
                
                $("#pct12to14Text").text("Percentage of total duties");
                $("#pctGt14Text").text("Percentage of total duties");
                
                $("#filterDenominator").val(res.denominator);
                if (res.denominator_source === "daily_upload") {
                    $("#totalDutySourceText").text("From uploaded total-duty sheet");
                } else {
                    $("#totalDutySourceText").text("Manual fallback denominator");
                }
                
                // Bind click event to toggle details
                $(".summary-row").off("click").click(function() {
                    const sec = $(this).data("section");
                    const tableId = $(this).data("table");
                    toggleSectionDetails(sec, $(this), tableId);
                });
            }
        });
    }

    function escapeHtml(value) {
        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function badgeClassFor(category) {
        if (category === "HWH-OTH") return "badge-hwh-oth";
        if (category === "OTH-HWH") return "badge-oth-hwh";
        if (category === "OTH DIV") return "badge-oth-div";
        return "badge-divisional";
    }

    function buildFilteredUrl(baseUrl) {
        const params = [];
        const fromDate = $("#fromDate").val();
        const toDate = $("#toDate").val();
        const category = $("#filterCategory").val();
        const section = $("#filterSection").val();
        if (fromDate) params.push(`from_date=${encodeURIComponent(fromDate)}`);
        if (toDate) params.push(`to_date=${encodeURIComponent(toDate)}`);
        if (category) params.push(`category=${encodeURIComponent(category)}`);
        if (section) params.push(`section=${encodeURIComponent(section)}`);
        return params.length ? `${baseUrl}?${params.join("&")}` : baseUrl;
    }

    function loadDetailedAnalysis() {
        $("#detailedOverviewBody").html('<tr><td colspan="10" class="text-center py-4"><div class="spinner-border text-info spinner-border-sm me-2"></div>Loading detailed analysis...</td></tr>');
        $("#detailedSectionCards").html('<div class="text-center py-4"><div class="spinner-border text-info spinner-border-sm me-2"></div>Loading scenario analysis...</div>');

        $.get(buildFilteredUrl("/tools/long-hours-analysis/detailed-analysis"), function(res) {
            if (!res.success) return;
            renderDetailedOverview(res.overview);
            renderDetailedSections(res.sections || []);
            // Populate the detailed visualization charts tab with data
            renderDetailedCharts(res);
        }).fail(function(xhr) {
            const err = xhr.responseJSON ? xhr.responseJSON.detail : "Unable to load detailed analysis.";
            $("#detailedOverviewBody").html(`<tr><td colspan="10" class="text-center py-4 text-danger">${escapeHtml(err)}</td></tr>`);
            $("#detailedSectionCards").html(`<div class="text-center py-4 text-danger">${escapeHtml(err)}</div>`);
        });
    }

    function renderDetailedOverview(overview) {
        const rows = overview.rows || [];
        const total = overview.total || {};
        let html = "";

        if (rows.length === 0) {
            html = '<tr><td colspan="10" class="text-center py-4 text-muted">No detailed records found for the selected filters.</td></tr>';
        } else {
            rows.forEach(row => {
                const category = row.category || "DIVISIONAL";
                html += `
                    <tr class="lh-section-clickable detailed-section-row" data-section="${escapeHtml(row.section)}" title="Click to view individual records">
                        <td><span class="badge ${badgeClassFor(category)}">${escapeHtml(category)}</span></td>
                        <td class="fw-bold text-primary">${escapeHtml(row.section)}</td>
                        <td class="text-center fw-bold">${row.count}</td>
                        <td class="text-center fw-bold text-success">${row.avg_total}</td>
                        <td class="text-center">${row.avg_hwh}</td>
                        <td class="text-center">${row.avg_oth}</td>
                        <td class="text-center">${row.avg_sign_on_dep}</td>
                        <td class="text-center">${row.avg_wheel}</td>
                        <td class="text-center">${row.avg_arr_sign_off}</td>
                        <td class="text-center">${row.avg_detn}</td>
                    </tr>
                `;
            });
            html += `
                <tr class="table-light fw-bold border-top border-dark">
                    <td>TOTAL</td>
                    <td></td>
                    <td class="text-center text-primary">${total.count || 0}</td>
                    <td class="text-center text-success">${total.avg_total || "00:00"}</td>
                    <td class="text-center">${total.avg_hwh || "00:00"}</td>
                    <td class="text-center">${total.avg_oth || "00:00"}</td>
                    <td class="text-center">${total.avg_sign_on_dep || "00:00"}</td>
                    <td class="text-center">${total.avg_wheel || "00:00"}</td>
                    <td class="text-center">${total.avg_arr_sign_off || "00:00"}</td>
                    <td class="text-center">${total.avg_detn || "00:00"}</td>
                </tr>
            `;
        }
        $("#detailedOverviewBody").html(html);
        $(".detailed-section-row").off("click").on("click", function() {
            const sectionName = $(this).data("section");
            openSectionRecordsModal(sectionName);
        });
    }

    function formatModalDateTime(obj) {
        if (!obj) return "";
        const first = [obj.date, obj.time].filter(Boolean).join(" ");
        const stn = obj.stn ? `<div class="text-primary fw-bold">${escapeHtml(obj.stn)}</div>` : "";
        return `<div>${escapeHtml(first)}</div>${stn}`;
    }

    function formatStationPair(obj, firstKey, secondKey, firstLabel, secondLabel) {
        if (!obj) return "";
        const first = obj[firstKey] ? `<div><span class="text-muted">${firstLabel}</span> <strong>${escapeHtml(obj[firstKey])}</strong></div>` : "";
        const second = obj[secondKey] ? `<div><span class="text-muted">${secondLabel}</span> <strong>${escapeHtml(obj[secondKey])}</strong></div>` : "";
        return first + second || "-";
    }

    function openSectionRecordsModal(sectionName) {
        const modalEl = document.getElementById("sectionRecordsModal");
        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        $("#sectionRecordsModalLabel").html(`<i class="bi bi-list-ul me-2"></i>${escapeHtml(sectionName)} Individual Records`);
        $("#sectionRecordsSummary").text("Loading records...");
        $("#sectionRecordsTableBody").html('<tr><td colspan="13" class="text-center py-4"><div class="spinner-border text-info spinner-border-sm me-2"></div>Loading individual records...</td></tr>');
        modal.show();

        let url = buildFilteredUrl("/tools/long-hours-analysis/section-records");
        url += (url.includes("?") ? "&" : "?") + `section=${encodeURIComponent(sectionName)}`;

        $.get(url, function(res) {
            if (!res.success) return;
            const records = res.records || [];
            $("#sectionRecordsSummary").text(`${res.section} | ${records.length.toLocaleString()} individual record(s) in current filter range`);

            if (records.length === 0) {
                $("#sectionRecordsTableBody").html('<tr><td colspan="13" class="text-center py-4 text-muted">No individual records found for this section and filter range.</td></tr>');
                return;
            }

            const html = records.map(row => `
                <tr>
                    <td class="text-center">${row.sl_no}</td>
                    <td>
                        <div class="fw-bold">${escapeHtml(row.crew_id)}</div>
                        <div class="text-muted small">${escapeHtml(row.lp_name)}</div>
                    </td>
                    <td class="text-center">
                        <div class="fw-bold">${escapeHtml(row.train_no)}</div>
                        <div class="text-muted small">${escapeHtml(row.loco_no)}</div>
                    </td>
                    <td class="text-center">${formatModalDateTime(row.sign_on)}</td>
                    <td class="text-center">${formatStationPair(row.toc_dep, "cto_stn", "dep_stn", "CTO", "DEP")}</td>
                    <td class="text-center fw-bold">${escapeHtml(row.pdd)}</td>
                    <td class="text-center fw-bold">${escapeHtml(row.wheel_movement)}</td>
                    <td class="text-center">${escapeHtml(row.detn_ic_point || "-")}</td>
                    <td class="text-center">${formatStationPair(row.arr_cmo, "arr_stn", "cmo_stn", "ARR", "CMO")}</td>
                    <td class="text-center fw-bold">${escapeHtml(row.pad)}</td>
                    <td class="text-center">${formatModalDateTime(row.sign_off)}</td>
                    <td class="text-center">
                        <div class="fw-bold text-success">${escapeHtml(row.total_duty)}</div>
                        <div class="small text-primary">HWH ${escapeHtml(row.hwh_div)}</div>
                        <div class="small text-warning">OTH ${escapeHtml(row.oth_div)}</div>
                    </td>
                    <td class="remarks-cell">${escapeHtml(row.remarks || "-")}</td>
                </tr>
            `).join("");
            $("#sectionRecordsTableBody").html(html);
        }).fail(function(xhr) {
            const err = xhr.responseJSON ? xhr.responseJSON.detail : "Unable to load individual records.";
            $("#sectionRecordsSummary").text("Error");
            $("#sectionRecordsTableBody").html(`<tr><td colspan="13" class="text-center py-4 text-danger">${escapeHtml(err)}</td></tr>`);
        });
    }

    function detailLine(label, value) {
        return `<div class="lh-scenario-line"><span>${escapeHtml(label)}</span><span>${escapeHtml(value)}</span></div>`;
    }

    function scenarioPanel(title, lines, className = "", dutyCount = 0) {
        if (parseInt(dutyCount) === 0) {
            return `
                <div class="lh-scenario-panel border-dashed bg-light text-muted d-flex flex-column justify-content-center align-items-center opacity-75" style="min-height: 172px;">
                    <h6 class="text-secondary small fw-bold text-center mb-1 text-uppercase">${escapeHtml(title)}</h6>
                    <div class="badge bg-secondary-subtle text-secondary border border-secondary px-3 py-1.5 rounded fs-6 fw-bold">NIL</div>
                </div>
            `;
        }
        return `
            <div class="lh-scenario-panel ${className}">
                <h6>${escapeHtml(title)}</h6>
                ${lines.join("")}
            </div>
        `;
    }

    function renderDetailedSections(sections) {
        if (!sections.length) {
            $("#detailedSectionCards").html('<div class="text-center py-4 text-muted">No section scenario records found for the selected filters.</div>');
            return;
        }

        let html = `
        <div class="accordion accordion-flush shadow-sm rounded-3 overflow-hidden border" id="scenarioAccordion">
        `;
        
        sections.forEach((section, index) => {
            const category = section.category || "DIVISIONAL";
            const source = section.source || "SRC";
            const destination = section.destination || "DEST";
            const scenarioCount = section.overall ? (section.overall.count || 0) : 0;
            const scenarios = section.scenarios || {};
            const sourceCto = scenarios.source_cto || {};
            const enrouteCto = scenarios.enroute_cto || {};
            const enrouteCmo = scenarios.enroute_cmo_dest_off || {};
            const destinationPad = scenarios.destination_pad || {};
            const offOther = scenarios.off_other || {};

            const accordionId = `collapseScenario_${index}`;
            const headerId = `headingScenario_${index}`;
            const badgeClass = badgeClassFor(category);

            html += `
                <div class="accordion-item border-bottom">
                    <h2 class="accordion-header" id="${headerId}">
                        <button class="accordion-button collapsed px-4 py-3 d-flex align-items-center gap-3" type="button" data-bs-toggle="collapse" data-bs-target="#${accordionId}" aria-expanded="false" aria-controls="${accordionId}">
                            <div class="d-flex align-items-center flex-grow-1 flex-wrap gap-2">
                                <span class="badge ${badgeClass} px-2.5 py-1.5 fs-7" style="font-size: 0.72rem; letter-spacing: 0.3px;">${escapeHtml(category)}</span>
                                <strong class="fs-6 text-dark me-2" style="font-size: 0.95rem;">${escapeHtml(section.section)}</strong>
                                <span class="text-muted small d-none d-sm-inline">| Route: ${escapeHtml(source)} ➔ ${escapeHtml(destination)}</span>
                            </div>
                            <span class="badge bg-danger-subtle text-danger border border-danger-subtle px-3 py-1.5 rounded-pill fw-bold text-end me-3" style="font-size: 0.75rem;">
                                <i class="bi bi-exclamation-octagon me-1"></i>${scenarioCount} Cases
                            </span>
                        </button>
                    </h2>
                    <div id="${accordionId}" class="accordion-collapse collapse" aria-labelledby="${headerId}" data-bs-parent="#scenarioAccordion">
                        <div class="accordion-body bg-light-subtle p-4">
                            <div class="lh-scenario-grid">
                                ${scenarioPanel(`Sign ON & CTO at ${source}`, [
                                    detailLine("Total Nos of Duty", sourceCto.count || 0),
                                    detailLine("AVG Duty Hours", sourceCto.avg_total || "00:00"),
                                    detailLine("AVG HWH Div", sourceCto.avg_hwh || "00:00"),
                                    detailLine("AVG OTH Div", sourceCto.avg_oth || "00:00"),
                                    detailLine("AVG Wheel Movement", sourceCto.avg_wheel || "00:00"),
                                    detailLine("PDD > 4 Hrs", sourceCto.pdd_gt_4hrs || 0),
                                    detailLine("PDD 3-4 Hrs", sourceCto.pdd_3to4hrs || 0),
                                    detailLine("PDD 2-3 Hrs", sourceCto.pdd_2to3hrs || 0),
                                    detailLine("PDD 1-2 Hrs", sourceCto.pdd_1to2hrs || 0),
                                    detailLine("PDD < 1 Hr", sourceCto.pdd_lt_1hr || 0)
                                ], "scenario-panel-blue", sourceCto.count || 0)}
                                ${scenarioPanel(`Sign ON at ${source}, CTO enroute`, [
                                    detailLine("Total Nos of Duty", enrouteCto.count || 0),
                                    detailLine("AVG Duty Hours", enrouteCto.avg_total || "00:00"),
                                    detailLine("AVG HWH Div", enrouteCto.avg_hwh || "00:00"),
                                    detailLine("AVG OTH Div", enrouteCto.avg_oth || "00:00"),
                                    detailLine("AVG Wheel Movement", enrouteCto.avg_wheel || "00:00"),
                                    detailLine("AVG Sign ON - CTO", enrouteCto.avg_on_to_cto || "00:00"),
                                    detailLine("AVG CTO - DEP", enrouteCto.avg_cto_to_dep || "00:00"),
                                    detailLine("Enroute CTO Stations", enrouteCto.stations || "NA")
                                ], "scenario-panel-teal", enrouteCto.count || 0)}
                                ${scenarioPanel(`CMO enroute, OFF at ${destination}`, [
                                    detailLine("Total Nos of Duty", enrouteCmo.count || 0),
                                    detailLine("AVG ARR - CMO", enrouteCmo.avg_arr_to_cmo || "00:00"),
                                    detailLine("AVG CMO - Sign Off", enrouteCmo.avg_cmo_to_off || "00:00"),
                                    detailLine("Enroute CMO Stations", enrouteCmo.stations || "NA")
                                ], "scenario-panel-amber", enrouteCmo.count || 0)}
                                ${scenarioPanel(`CMO & Sign OFF at ${destination}`, [
                                    detailLine("Total Nos of Duty", destinationPad.count || 0),
                                    detailLine("AVG PAD", destinationPad.avg_pad || "00:00")
                                ], "scenario-panel-green", destinationPad.count || 0)}
                                ${scenarioPanel("OFF at HQ / other CBL", [
                                    detailLine("Total Nos of Duty", offOther.count || 0),
                                    detailLine("AVG ARR - CMO", offOther.avg_arr_to_cmo || "00:00"),
                                    detailLine("AVG CMO - Sign Off", offOther.avg_cmo_to_off || "00:00"),
                                    detailLine("CMO Stations", offOther.stations || "NA")
                                ], "scenario-panel-purple", offOther.count || 0)}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });

        html += `</div>`;
        $("#detailedSectionCards").html(html);
    }

    function renderSummaryTable(dataObj, tableBodyId, tableId) {
        let html = "";
        const rows = dataObj.rows;
        const total = dataObj.total;
        const pctText = (value) => Number(value || 0).toFixed(2);
        
        if (rows.length === 0) {
            html = '<tr><td colspan="7" class="text-center py-4 text-muted">No records found for the selected filters.</td></tr>';
        } else {
            rows.forEach((row) => {
                let badgeClass = "badge-divisional";
                if (row.category === "HWH-OTH") badgeClass = "badge-hwh-oth";
                else if (row.category === "OTH-HWH") badgeClass = "badge-oth-hwh";
                else if (row.category === "OTH DIV") badgeClass = "badge-oth-div";
                
                const idSafe = row.section.replace(/\s+/g, '_') + "_" + tableId;
                
                html += `
                    <tr class="summary-row" data-section="${row.section}" data-table="${tableId}">
                        <td><span class="badge ${badgeClass}">${row.category}</span></td>
                        <td class="fw-bold text-primary">${row.section}</td>
                        <td class="text-center fw-bold">${row.count}</td>
                        <td class="text-center fw-bold text-secondary">${pctText(row.pct_age)}%</td>
                        <td class="text-center">${row.avg_hwh}</td>
                        <td class="text-center">${row.avg_oth}</td>
                        <td class="text-center fw-bold text-success">${row.avg_total}</td>
                    </tr>
                    <tr class="detail-row d-none" id="detail-${idSafe}">
                        <td colspan="7" class="p-0">
                            <div class="lh-detail-box" id="detail-box-${idSafe}">
                                <!-- Details loaded dynamically -->
                            </div>
                        </td>
                    </tr>
                `;
            });
            
            // Add total row at bottom
            html += `
                <tr class="table-light fw-bold border-top border-dark">
                    <td>TOTAL</td>
                    <td></td>
                    <td class="text-center text-primary">${total.count}</td>
                    <td class="text-center text-secondary">${pctText(total.pct_age)}%</td>
                    <td class="text-center">${total.avg_hwh}</td>
                    <td class="text-center">${total.avg_oth}</td>
                    <td class="text-center text-success">${total.avg_total}</td>
                </tr>
            `;
        }
        $(`#${tableBodyId}`).html(html);
    }

    // Toggle Section Scenario breakdown
    function toggleSectionDetails(section, rowElement, tableId) {
        const idSafe = section.replace(/\s+/g, '_') + "_" + tableId;
        const detailRow = $(`#detail-${idSafe}`);
        const detailBox = $(`#detail-box-${idSafe}`);
        
        if (!detailRow.hasClass("d-none")) {
            // Collapse
            detailRow.addClass("d-none");
            rowElement.removeClass("table-active");
            return;
        }
        
        // Collapse other open detail rows
        $(".detail-row").addClass("d-none");
        $(".summary-row").removeClass("table-active");
        
        // Show loading spinner
        detailRow.removeClass("d-none");
        rowElement.addClass("table-active");
        detailBox.html('<div class="text-center py-4"><div class="spinner-border text-primary spinner-border-sm me-2"></div>Loading Section Details...</td></tr>');
        
        const fromDate = $("#fromDate").val();
        const toDate = $("#toDate").val();
        
        let url = `/tools/long-hours-analysis/scenario-details?section=${encodeURIComponent(section)}`;
        if (fromDate) url += `&from_date=${fromDate}`;
        if (toDate) url += `&to_date=${toDate}`;
        
        $.get(url, function(res) {
            if (res.success) {
                const s = res.snapshot;
                
                let html = `
                    <div class="d-flex justify-content-between align-items-center mb-4 border-bottom pb-2">
                        <h5 class="mb-0 text-dark fw-bold"><i class="bi bi-info-circle-fill text-primary me-2"></i>Analysis Snapshot: ${section}</h5>
                    </div>
                    
                    <div class="row g-3">
                        <div class="col-md-2 col-6">
                            <div class="lh-detail-metric">
                                <div class="lh-detail-metric-val">${s.total_cases}</div>
                                <div class="lh-detail-metric-lbl">Total Cases</div>
                            </div>
                        </div>
                        <div class="col-md-2 col-6">
                            <div class="lh-detail-metric">
                                <div class="lh-detail-metric-val text-success">${s.avg_total}</div>
                                <div class="lh-detail-metric-lbl">Avg Total Duty</div>
                            </div>
                        </div>
                        <div class="col-md-2 col-6">
                            <div class="lh-detail-metric">
                                <div class="lh-detail-metric-val text-primary">${s.avg_hwh}</div>
                                <div class="lh-detail-metric-lbl">Avg HWH Div</div>
                            </div>
                        </div>
                        <div class="col-md-2 col-6">
                            <div class="lh-detail-metric">
                                <div class="lh-detail-metric-val text-warning">${s.avg_oth}</div>
                                <div class="lh-detail-metric-lbl">Avg Oth Div</div>
                            </div>
                        </div>
                        <div class="col-md-4 col-12">
                            <div class="lh-detail-metric">
                                <div class="lh-detail-metric-val text-info">${s.avg_wheel}</div>
                                <div class="lh-detail-metric-lbl">Avg Wheel Movement</div>
                            </div>
                        </div>
                    </div>
                `;
                
                detailBox.html(html);
            }
        });
    }

    // Helper function to extract cell value from row_data dynamically using column mapping
    function getVal(row, cleanKey) {
        if (!row || !row.row_data || !window.colMap) return "";
        let idx = window.colMap[cleanKey];
        if (idx !== undefined && idx < row.row_data.length) {
            return row.row_data[idx] !== null ? row.row_data[idx] : "";
        }
        return "";
    }

    // Helper function to format date from YYYY-MM-DD to DD-MM-YYYY
    function formatDateStr(val) {
        if (!val) return "";
        let str = String(val).trim();
        if (str.includes(" ")) str = str.split(" ")[0];
        if (str.includes("T")) str = str.split("T")[0];
        // Match YYYY-MM-DD
        let m = str.match(/^(\d{4})-(\d{2})-(\d{2})$/);
        if (m) {
            return `${m[3]}-${m[2]}-${m[1]}`;
        }
        // Match DD-MM-YYYY
        let m2 = str.match(/^(\d{2})-(\d{2})-(\d{4})$/);
        if (m2) return str;
        // Match DD/MM/YYYY
        let m3 = str.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
        if (m3) return `${m3[1]}-${m3[2]}-${m3[3]}`;
        return str;
    }

    // Helper function to format time (e.g. truncate HH:MM:SS to HH:MM)
    function formatTimeStr(val) {
        if (!val) return "";
        let str = String(val).trim();
        let parts = str.split(":");
        if (parts.length >= 2) {
            return `${parts[0].padStart(2, '0')}:${parts[1].padStart(2, '0')}`;
        }
        return str;
    }

    // Initialize Server-Side DataTable for Individual Long Hours Register
    function initRecordsTable() {
        if (recordsTable) {
            recordsTable.destroy();
            $('#recordsTable tbody').empty();
        }
        
        recordsTable = $('#recordsTable').DataTable({
            processing: true,
            serverSide: true,
            lengthMenu: [10, 25, 50, 100],
            pageLength: 10,
            ajax: {
                url: "/tools/long-hours-analysis/records",
                type: "GET",
                data: function(d) {
                    d.from_date = $("#fromDate").val();
                    d.to_date = $("#toDate").val();
                    d.category = $("#filterCategory").val();
                    d.section = $("#filterSection").val();
                    d.train = $("#filterTrain").val();
                    d.loco = $("#filterLoco").val();
                    d.crew = $("#filterCrew").val();
                },
                dataSrc: function(json) {
                    // Populate window.colMap dynamically
                    window.colMap = {};
                    if (json.headers) {
                        json.headers.forEach((h, idx) => {
                            let clean = h.toLowerCase().replace(/\s+/g, '').replace(/_/g, '').replace(/-/g, '').replace(/\//g, '').replace(/\\/g, '');
                            window.colMap[clean] = idx;
                        });
                    }
                    return json.data;
                }
            },
            columns: [
                // 1. Sl No
                {
                    data: null,
                    className: "text-center",
                    render: function(data, type, row, meta) {
                        return meta.row + meta.settings._iDisplayStart + 1;
                    }
                },
                // 2. CREW
                {
                    data: function(row) {
                        let id = getVal(row, 'crewid') || getVal(row, 'crewcode') || '';
                        let name = getVal(row, 'crewname') || getVal(row, 'lpname') || '';
                        return `<div class="fw-bold">${id}</div><div class="text-muted small" style="max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${name}</div>`;
                    }
                },
                // 3. TRAIN NO & LOCO NO
                {
                    data: function(row) {
                        let loco = getVal(row, 'loco') || getVal(row, 'locono') || '';
                        let train = getVal(row, 'trainno') || '';
                        return `<div class="fw-bold text-dark">${loco}</div><div class="text-muted small">${train}</div>`;
                    },
                    className: "text-center"
                },
                // 4. SIGN ON
                {
                    data: function(row) {
                        let dt = formatDateStr(getVal(row, 'date') || getVal(row, 'signondate') || '');
                        let tm = formatTimeStr(getVal(row, 'ontime') || getVal(row, 'signontime') || '');
                        let plc = getVal(row, 'onstn') || getVal(row, 'signonstn') || '';
                        return `<div class="fw-bold">${dt}</div><div>${tm}</div><div class="text-primary small fw-bold">${plc}</div>`;
                    },
                    className: "text-center"
                },
                // 5. TOC & DEP
                {
                    data: function(row) {
                        let plc = getVal(row, 'ctodepstn') || getVal(row, 'ctostn') || '';
                        let cto = formatTimeStr(getVal(row, 'cto') || '');
                        let dep = formatTimeStr(getVal(row, 'dep') || '');
                        return `<div class="fw-bold">${plc}</div><div class="small text-muted">CTO = ${cto}</div><div class="small text-muted">DEP = ${dep}</div>`;
                    },
                    className: "text-center"
                },
                // 6. PDD or SIGN ON-DEP (SUB PRE CTO & POST CTO)
                {
                    data: function(row) {
                        let pdd = formatTimeStr(getVal(row, 'pddtotal') || getVal(row, 'pdd') || '');
                        let pre = formatTimeStr(getVal(row, 'precto') || '');
                        let post = formatTimeStr(getVal(row, 'postcto') || '');
                        if (pdd === "00:00" || !pdd) {
                            let sign_on_dep = formatTimeStr(getVal(row, 'ontodep') || getVal(row, 'signontodep') || getVal(row, 'signontodepseconds') || '');
                            return `<div class="small fw-bold">Total (S/ON-DEP) = ${sign_on_dep}</div><div class="small text-muted">Pre = ${pre} | Post = ${post}</div>`;
                        } else {
                            return `<div class="small fw-bold">Total (PDD) = ${pdd}</div><div class="small text-muted">Pre = ${pre} | Post = ${post}</div>`;
                        }
                    }
                },
                // 7. WHEEL MOVEMENT
                {
                    data: function(row) {
                        let val = getVal(row, 'wheelmovement') || getVal(row, 'wheelmovementseconds') || '';
                        return formatTimeStr(val);
                    },
                    className: "text-center fw-bold"
                },
                // 8. INTERCHANGE
                {
                    data: function(row) {
                        if (row.section_category === "DIVISIONAL") {
                            return `<div class="text-center">NA</div>`;
                        }
                        let val = getVal(row, 'detnaticpoint') || '';
                        if (val === "" || val.toUpperCase() === "NA") {
                            return `<div class="text-center">NA</div>`;
                        }
                        return `<div class="text-center">${formatTimeStr(val)}</div>`;
                    }
                },
                // 9. ARR & CMO
                {
                    data: function(row) {
                        let plc = getVal(row, 'mocstn') || getVal(row, 'arrstn') || '';
                        let arr = formatTimeStr(getVal(row, 'arr') || '');
                        let cmo = formatTimeStr(getVal(row, 'cmo') || getVal(row, 'cmostn') || '');
                        return `<div class="fw-bold">${plc}</div><div class="small text-muted">ARR = ${arr}</div><div class="small text-muted">CMO = ${cmo}</div>`;
                    },
                    className: "text-center"
                },
                // 10. PAD OR ARR - SIGN OFF (SUB PRE CMO & POST CMO)
                {
                    data: function(row) {
                        let pad = formatTimeStr(getVal(row, 'padtotal') || getVal(row, 'pad') || '');
                        let pre = formatTimeStr(getVal(row, 'precmo') || '');
                        let post = formatTimeStr(getVal(row, 'postcmo') || '');
                        if (pad === "00:00" || !pad) {
                            let arr_to_off = formatTimeStr(getVal(row, 'arrtooff') || getVal(row, 'cmotooff') || getVal(row, 'wheelstoptooffseconds') || '');
                            return `<div class="small fw-bold">Total (ARR-S/OFF) = ${arr_to_off}</div><div class="small text-muted">Pre = ${pre} | Post = ${post}</div>`;
                        } else {
                            return `<div class="small fw-bold">Total (PAD) = ${pad}</div><div class="small text-muted">Pre = ${pre} | Post = ${post}</div>`;
                        }
                    }
                },
                // 11. SIGN OFF
                {
                    data: function(row) {
                        let dt = formatDateStr(getVal(row, 'signoffdate') || '');
                        let tm = formatTimeStr(getVal(row, 'offtime') || getVal(row, 'signofftime') || '');
                        let plc = getVal(row, 'offstn') || getVal(row, 'signoffstn') || '';
                        return `<div class="fw-bold">${dt}</div><div>${tm}</div><div class="text-primary small fw-bold">${plc}</div>`;
                    },
                    className: "text-center"
                },
                // 12. TOTAL DUTY
                {
                    data: function(row) {
                        let tot = formatTimeStr(getVal(row, 'total') || '');
                        let hwh = formatTimeStr(getVal(row, 'hwhdiv') || '');
                        let Oth = formatTimeStr(getVal(row, 'otherdiv') || '');
                        return `<div class="small fw-bold text-success">Total = ${tot}</div><div class="small text-primary">HWH = ${hwh}</div><div class="small text-warning">OTH = ${Oth}</div>`;
                    }
                },
                // 13. LH SECTION
                {
                    data: function(row) {
                        let val = getVal(row, 'longhourssection') || getVal(row, 'section') || '';
                        return `<div class="text-center fw-bold text-primary">${val}</div>`;
                    }
                },
                // 14. REMARKS
                {
                    data: function(row) {
                        let val = getVal(row, 'remarks') || getVal(row, 'remark') || '';
                        if (!val.trim()) {
                            return `<div class="text-center text-muted">-</div>`;
                        }
                        return `
                            <div class="text-center">
                                <button type="button" class="btn btn-sm btn-outline-primary show-remarks-btn" data-bs-toggle="modal" data-bs-target="#remarksModal" title="Click to view detailed remarks">
                                    <i class="bi bi-eye-fill"></i>
                                </button>
                            </div>
                        `;
                    }
                }
            ],
            order: [[3, "desc"]], // Sort by Sign-ON Date by default
            language: {
                processing: '<div class="spinner-border text-primary spinner-border-sm me-2"></div>Processing...'
            }
        });
    }

    // Event listener for populating remarks modal content when shown
    $('#remarksModal').on('show.bs.modal', function(event) {
        let button = $(event.relatedTarget);
        let tr = button.closest('tr');
        let row = recordsTable.row(tr).data();
        let remarks = getVal(row, 'remarks') || getVal(row, 'remark') || '';
        $('#remarksModalContent').text(remarks);
    });

    function renderSlotsTable(slotsData) {
        let html = "";
        const rows = slotsData.rows;
        const total = slotsData.total;
        
        if (!rows || rows.length === 0) {
            html = '<tr><td colspan="6" class="text-center py-4 text-muted">No records found for the selected filters.</td></tr>';
        } else {
            rows.forEach((row) => {
                let badgeClass = "badge-divisional";
                if (row.category === "HWH-OTH") badgeClass = "badge-hwh-oth";
                else if (row.category === "OTH-HWH") badgeClass = "badge-oth-hwh";
                else if (row.category === "OTH DIV") badgeClass = "badge-oth-div";
                
                html += `
                    <tr>
                        <td><span class="badge ${badgeClass}">${row.category}</span></td>
                        <td class="fw-bold text-primary">${row.section}</td>
                        <td class="text-center fw-bold">${row.total_cases}</td>
                        <td class="text-center">
                            <span class="fw-bold text-dark">${row.slot_1_count}</span>
                            <span class="text-muted small">(${row.slot_1_pct}%)</span>
                        </td>
                        <td class="text-center">
                            <span class="fw-bold text-dark">${row.slot_2_count}</span>
                            <span class="text-muted small">(${row.slot_2_pct}%)</span>
                        </td>
                        <td class="text-center">
                            <span class="fw-bold text-dark">${row.slot_3_count}</span>
                            <span class="text-muted small">(${row.slot_3_pct}%)</span>
                        </td>
                    </tr>
                `;
            });
            
            // Add total row at bottom
            html += `
                <tr class="table-light fw-bold border-top border-dark">
                    <td>TOTAL</td>
                    <td></td>
                    <td class="text-center text-primary">${total.total_cases}</td>
                    <td class="text-center">
                        <span class="text-dark">${total.slot_1_count}</span>
                        <span class="text-secondary small">(${total.slot_1_pct}%)</span>
                    </td>
                    <td class="text-center">
                        <span class="text-dark">${total.slot_2_count}</span>
                        <span class="text-secondary small">(${total.slot_2_pct}%)</span>
                    </td>
                    <td class="text-center">
                        <span class="text-dark">${total.slot_3_count}</span>
                        <span class="text-secondary small">(${total.slot_3_pct}%)</span>
                    </td>
                </tr>
            `;
        }
        $("#slotsTableBody").html(html);
    }

    function updateSlotsCharts(slotsData) {
        if (typeof Chart === "undefined") {
            $("#overallSlotsDoughnutChart").parent().html('<div class="text-center text-muted small py-5">Chart library unavailable. Slot table is shown on the left.</div>');
            $("#sectionSlotsBarChart").parent().html('<div class="text-center text-muted small py-5">Chart library unavailable. Slot comparison table is shown on the left.</div>');
            return;
        }

        const totalObj = slotsData.total;
        const rows = slotsData.rows || [];
        
        // 1. Overall Doughnut Chart
        const doughnutCtx = document.getElementById('overallSlotsDoughnutChart').getContext('2d');
        if (overallSlotsDoughnutChart) {
            overallSlotsDoughnutChart.destroy();
        }
        
        overallSlotsDoughnutChart = new Chart(doughnutCtx, {
            type: 'doughnut',
            data: {
                labels: ['00:00 - 08:00 (Slot 1)', '08:00 - 16:00 (Slot 2)', '16:00 - 24:00 (Slot 3)'],
                datasets: [{
                    data: [totalObj.slot_1_count, totalObj.slot_2_count, totalObj.slot_3_count],
                    backgroundColor: ['#6366f1', '#f59e0b', '#10b981'],
                    hoverBackgroundColor: ['#4f46e5', '#d97706', '#059669'],
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            boxWidth: 12,
                            font: { size: 10 }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const val = context.raw || 0;
                                const total = totalObj.total_cases || 1;
                                const pct = ((val / total) * 100).toFixed(1);
                                return `${context.label}: ${val.toLocaleString()} (${pct}%)`;
                            }
                        }
                    }
                },
                cutout: '65%'
            }
        });
        
        // 2. Section Stacked Bar Chart
        const barCtx = document.getElementById('sectionSlotsBarChart').getContext('2d');
        if (sectionSlotsBarChart) {
            sectionSlotsBarChart.destroy();
        }
        
        // Take top 8 sections by total cases for better visualization
        const sortedRows = [...rows].sort((a, b) => b.total_cases - a.total_cases).slice(0, 8);
        
        const labels = sortedRows.map(r => r.section);
        const slot1Data = sortedRows.map(r => r.slot_1_count);
        const slot2Data = sortedRows.map(r => r.slot_2_count);
        const slot3Data = sortedRows.map(r => r.slot_3_count);
        
        sectionSlotsBarChart = new Chart(barCtx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: '00:00 - 08:00',
                        data: slot1Data,
                        backgroundColor: '#6366f1'
                    },
                    {
                        label: '08:00 - 16:00',
                        data: slot2Data,
                        backgroundColor: '#f59e0b'
                    },
                    {
                        label: '16:00 - 24:00',
                        data: slot3Data,
                        backgroundColor: '#10b981'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        stacked: true,
                        grid: { display: false },
                        ticks: { font: { size: 9 } }
                    },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        ticks: { font: { size: 9 } }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            boxWidth: 10,
                            font: { size: 9 }
                        }
                    }
                }
            }
        });
    }

    // Custom Charts instantiation logic
    let topSectionsChartInstance = null;
    let categoryChartInstance = null;
    let avgHoursChartInstance = null;

    function renderDetailedCharts(res) {
        // Destroy existing chart instances if they exist
        if (topSectionsChartInstance) topSectionsChartInstance.destroy();
        if (categoryChartInstance) categoryChartInstance.destroy();
        if (avgHoursChartInstance) avgHoursChartInstance.destroy();

        // 1. Top Sections Cases Chart (> 12 hours)
        const sectionCasesMap = {};
        const sectionsData = res.overview.rows || [];
        
        sectionsData.forEach(row => {
            const sec = row.section;
            const cases = parseInt(row.count) || 0;
            sectionCasesMap[sec] = (sectionCasesMap[sec] || 0) + cases;
        });

        // Sort sections and take top 8
        const sortedSections = Object.keys(sectionCasesMap)
            .map(sec => ({ section: sec, count: sectionCasesMap[sec] }))
            .sort((a, b) => b.count - a.count)
            .slice(0, 8);

        const ctxTop = document.getElementById("topSectionsLhChart").getContext("2d");
        topSectionsChartInstance = new Chart(ctxTop, {
            type: 'bar',
            data: {
                labels: sortedSections.map(s => s.section),
                datasets: [{
                    label: 'Long Hours Cases (>12h)',
                    data: sortedSections.map(s => s.count),
                    backgroundColor: 'rgba(59, 130, 246, 0.75)',
                    borderColor: 'rgb(59, 130, 246)',
                    borderWidth: 1.5,
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: { beginAtZero: true, ticks: { font: { size: 10 } } },
                    x: { ticks: { font: { size: 9 }, maxRotation: 45, minRotation: 0 } }
                }
            }
        });

        // 2. Category Share Chart
        // Group by category (Divisional / Other Div / etc.)
        const categoryMap = {};
        sectionsData.forEach(row => {
            const cat = row.category || "DIVISIONAL";
            const cases = parseInt(row.count) || 0;
            categoryMap[cat] = (categoryMap[cat] || 0) + cases;
        });

        const catLabels = Object.keys(categoryMap);
        const catData = Object.values(categoryMap);

        const ctxCat = document.getElementById("categoryLhChart").getContext("2d");
        categoryChartInstance = new Chart(ctxCat, {
            type: 'doughnut',
            data: {
                labels: catLabels,
                datasets: [{
                    data: catData,
                    backgroundColor: [
                        '#3b82f6', // Blue
                        '#10b981', // Teal/Green
                        '#f59e0b', // Yellow/Amber
                        '#8b5cf6', // Purple
                        '#ef4444'  // Red
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { boxWidth: 12, font: { size: 10 } }
                    }
                }
            }
        });

        // 3. Avg Hours Breakdown by Section (Line chart showing Average duty, Wheel movement, Detn)
        const avgRows = (res.overview.rows || []).slice(0, 6); // Top 6 sections
        const parseTimeToFloat = (tStr) => {
            if (!tStr || tStr === "00:00") return 0;
            const parts = tStr.split(":");
            return parseFloat(parts[0]) + (parseFloat(parts[1] || 0) / 60);
        };

        const sectionLabels = avgRows.map(r => r.section);
        
        // Let's draw average timings
        const avgTotalData = avgRows.map(r => parseTimeToFloat(r.avg_total));
        const avgWheelData = avgRows.map(r => parseTimeToFloat(r.avg_wheel));
        const avgDetnData = avgRows.map(r => parseTimeToFloat(r.avg_detn));

        const ctxAvg = document.getElementById("sectionAvgHoursChart").getContext("2d");
        avgHoursChartInstance = new Chart(ctxAvg, {
            type: 'line',
            data: {
                labels: sectionLabels,
                datasets: [
                    {
                        label: 'Avg Total Duty',
                        data: avgTotalData,
                        borderColor: '#ef4444',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        borderWidth: 2,
                        tension: 0.25,
                        fill: false
                    },
                    {
                        label: 'Avg Wheel Movt',
                        data: avgWheelData,
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        borderWidth: 2,
                        tension: 0.25,
                        fill: false
                    },
                    {
                        label: 'Avg Detn I/C',
                        data: avgDetnData,
                        borderColor: '#f59e0b',
                        backgroundColor: 'rgba(245, 158, 11, 0.1)',
                        borderWidth: 2,
                        tension: 0.25,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: { boxWidth: 12, font: { size: 10 } }
                    }
                },
                scales: {
                    y: {
                        title: { display: true, text: 'Hours', font: { size: 10 } },
                        ticks: { font: { size: 9 } }
                    },
                    x: { ticks: { font: { size: 9 } } }
                }
            }
        });

        // 4. Sign On - Departure & Arr - Sign Off Chart (Double Group Bar or Line)
        const avgSignOnDepData = avgRows.map(r => parseTimeToFloat(r.avg_sign_on_dep));
        const avgArrSignOffData = avgRows.map(r => parseTimeToFloat(r.avg_arr_sign_off));

        const ctxDetn = document.getElementById("sectionDetnBreakdownChart").getContext("2d");
        if (window.detnChartInstance) window.detnChartInstance.destroy();
        window.detnChartInstance = new Chart(ctxDetn, {
            type: 'bar',
            data: {
                labels: sectionLabels,
                datasets: [
                    {
                        label: 'Sign On - Departure',
                        data: avgSignOnDepData,
                        backgroundColor: '#6366f1',
                        borderRadius: 4
                    },
                    {
                        label: 'Arrival - Sign Off',
                        data: avgArrSignOffData,
                        backgroundColor: '#ec4899',
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: { boxWidth: 12, font: { size: 10 } }
                    }
                },
                scales: {
                    y: {
                        title: { display: true, text: 'Hours', font: { size: 10 } },
                        ticks: { font: { size: 9 } }
                    },
                    x: { ticks: { font: { size: 9 } } }
                }
            }
        });
    }

});
