// Gradient Register Management JS

let currentPage = 1;
const pageSize = 50;

let chartInstance = null;
let currentChartData = null; // Caches profile and distribution data
let currentChartType = 'profile'; // 'profile' or 'distribution'

let activeStallingFromKM = null;
let activeStallingToKM = null;
let activeLabelText = "";
let activeTextKM = null;
let activeTextElev = null;

let customMarkers = [];
let chartTextAnnotations = [];
let draggingAnnotation = null; // annotation currently being dragged

const RPH_DUMK_UP_SIGNALS = [
    { type: 'signal', km: 98.450, label: 'RPH S/S' },
    { type: 'signal', km: 100.150, label: 'RPH E/S' },
    { type: 'signal', km: 100.270, label: 'RPH A/S' },
    { type: 'neutral_section', km: 101.100, label: 'N/S' },
    { type: 'signal', km: 110.090, label: 'ALPD H/S' },
    { type: 'signal', km: 116.010, label: 'D/S' },
    { type: 'signal', km: 117.010, label: 'PRGR H/S' },
    { type: 'signal', km: 118.030, label: 'PRGR S/S' },
    { type: 'signal', km: 118.130, label: 'PRGR A/S' },
    { type: 'signal', km: 123.100, label: 'D/S' },
    { type: 'signal', km: 124.100, label: 'HRNS H/S' },
    { type: 'signal', km: 125.130, label: 'HRNS S/S' },
    { type: 'signal', km: 126.030, label: 'HRNS A/S' },
    { type: 'neutral_section', km: 126.090, label: 'N/S' },
    { type: 'signal', km: 136.130, label: 'D/S' },
    { type: 'signal', km: 137.140, label: 'SKIP H/S' },
    { type: 'signal', km: 138.200, label: 'SKIP S/S' },
    { type: 'signal', km: 139.040, label: 'SKIP A/S' },
    { type: 'signal', km: 146.060, label: 'BRMA H/S' },
    { type: 'signal', km: 154.120, label: 'D/S' },
    { type: 'signal', km: 155.170, label: 'KURV H/S' },
    { type: 'signal', km: 157.050, label: 'KURV S/S' },
    { type: 'signal', km: 157.090, label: 'KURV A/S' },
    { type: 'signal', km: 160.180, label: 'D/S' },
    { type: 'signal', km: 161.190, label: 'DUMK H/S' }
];

const RPH_DUMK_DN_SIGNALS = [
    { type: 'signal', km: 161.070, label: 'DUMK S/S' },
    { type: 'signal', km: 161.210, label: 'DUMK A/S' },
    { type: 'signal', km: 158.140, label: 'D/S' },
    { type: 'signal', km: 157.140, label: 'KURV H/S' },
    { type: 'signal', km: 156.060, label: 'KURV S/S' },
    { type: 'signal', km: 155.090, label: 'KURV A/S' },
    { type: 'signal', km: 146.130, label: 'BRMA H/S' },
    { type: 'signal', km: 140.080, label: 'D/S' },
    { type: 'signal', km: 139.090, label: 'SKIP H/S' },
    { type: 'signal', km: 138.050, label: 'SKIP S/S' },
    { type: 'signal', km: 137.180, label: 'SKIP A/S' },
    { type: 'signal', km: 127.070, label: 'D/S' },
    { type: 'neutral_section', km: 126.110, label: 'N/S' },
    { type: 'signal', km: 126.070, label: 'HRNS H/S' },
    { type: 'signal', km: 125.050, label: 'HRNS S/S' },
    { type: 'signal', km: 124.140, label: 'HRNS A/S' },
    { type: 'signal', km: 119.140, label: 'D/S' },
    { type: 'signal', km: 118.180, label: 'PRGR H/S' },
    { type: 'signal', km: 117.160, label: 'PRGR S/S' },
    { type: 'signal', km: 117.060, label: 'PRGR A/S' },
    { type: 'signal', km: 110.090, label: 'ALPD H/S' },
    { type: 'signal', km: 102.040, label: 'D/S' },
    { type: 'neutral_section', km: 101.120, label: 'N/S' },
    { type: 'signal', km: 101.020, label: 'RPH H/S' }
];

document.addEventListener("DOMContentLoaded", () => {
    // Initial load of sections dropdown
    loadSections();
    
    // Load initial table list
    fetchGradients();
    
    // Listeners for filters
    document.getElementById("filterSection").addEventListener("change", (e) => {
        currentPage = 1;
        const section = e.target.value;
        
        // Clear active stalling marker when changing section
        clearStallingEvent();
        
        // Reload dependent line and direction filters
        loadDependentFilters(section);
        
        // Update table list
        fetchGradients();
        
        // Load and show/hide chart
        if (section) {
            fetchChartData(section);
        } else {
            document.getElementById("chartCard").style.display = "none";
        }
    });
    
    document.getElementById("filterLine").addEventListener("change", () => {
        currentPage = 1;
        fetchGradients();
        
        // If section is selected, update chart with selected line
        const section = document.getElementById("filterSection").value;
        if (section) {
            const line = document.getElementById("filterLine").value;
            fetchChartData(section, line);
        }
    });
    
    document.getElementById("filterDirection").addEventListener("change", () => {
        currentPage = 1;
        fetchGradients();
    });
    
    document.getElementById("textSearch").addEventListener("input", debounce(() => {
        currentPage = 1;
        fetchGradients();
    }, 300));
    
    // Predefined signals selection listener
    const selectPred = document.getElementById("selectPredefinedSignals");
    if (selectPred) {
        selectPred.addEventListener("change", (e) => {
            const val = e.target.value;
            customMarkers = [];
            
            if (val === "up") {
                RPH_DUMK_UP_SIGNALS.forEach(s => {
                    customMarkers.push({
                        id: Date.now() + Math.random(),
                        type: s.type,
                        km: s.km,
                        label: s.label
                    });
                });
            } else if (val === "dn") {
                RPH_DUMK_DN_SIGNALS.forEach(s => {
                    customMarkers.push({
                        id: Date.now() + Math.random(),
                        type: s.type,
                        km: s.km,
                        label: s.label
                    });
                });
            }
            
            updateMarkersListUI();
            
            if (customMarkers.length > 0) {
                document.getElementById("btnClearStalling").style.display = "inline-block";
            } else {
                if (activeStallingFromKM === null) {
                    document.getElementById("btnClearStalling").style.display = "none";
                }
            }
            
            renderChart();
        });
    }
    
    // Show/hide markerEndKMContainer dynamically based on markerType selection
    const markerTypeSelect = document.getElementById("markerType");
    if (markerTypeSelect) {
        markerTypeSelect.addEventListener("change", (e) => {
            const container = document.getElementById("markerEndKMContainer");
            const kmInput = document.getElementById("markerKM");
            if (e.target.value === "speed") {
                if (container) container.style.display = "block";
                if (kmInput) kmInput.placeholder = "From KM (e.g. 125.100)";
            } else {
                if (container) container.style.display = "none";
                if (kmInput) kmInput.placeholder = "KM Position (e.g. 11.200)";
            }
        });
    }

    // Reset filters button
    document.getElementById("btnResetFilters").addEventListener("click", resetFilters);
    
    // Pagination buttons
    document.getElementById("btnPrevPage").addEventListener("click", (e) => {
        e.preventDefault();
        if (currentPage > 1) {
            currentPage--;
            fetchGradients();
        }
    });
    
    document.getElementById("btnNextPage").addEventListener("click", (e) => {
        e.preventDefault();
        currentPage++;
        fetchGradients();
    });
    
    // Chart view buttons
    document.getElementById("btnViewProfile").addEventListener("click", () => {
        toggleChartView('profile');
    });
    document.getElementById("btnViewDistribution").addEventListener("click", () => {
        toggleChartView('distribution');
    });
    
    // Chart download (opens modal options)
    document.getElementById("btnDownloadChart").addEventListener("click", showSaveChartModal);
    
    // Save Chart Modal actions
    document.getElementById("btnCloseSaveChartModal").addEventListener("click", hideSaveChartModal);
    document.getElementById("btnCancelSaveChart").addEventListener("click", hideSaveChartModal);
    document.getElementById("btnConfirmDownloadChart").addEventListener("click", executeChartDownload);
    document.getElementById("saveScope").addEventListener("change", (e) => {
        const fields = document.getElementById("saveCustomRangeFields");
        fields.style.display = e.target.value === "custom" ? "block" : "none";
    });

    // Excel and PDF downloads
    document.getElementById("btnDownloadExcel").addEventListener("click", downloadTableAsExcel);
    document.getElementById("btnDownloadPDF").addEventListener("click", downloadTableAsPDF);

    // Stalling buttons
    document.getElementById("btnPlotStalling").addEventListener("click", plotStallingEvent);
    document.getElementById("btnClearStalling").addEventListener("click", clearStallingEvent);
    document.getElementById("btnAddMarker").addEventListener("click", addCustomMarker);
    
    // Toggle distance calculations checkbox listener
    const chkShowDistances = document.getElementById("chkShowDistances");
    if (chkShowDistances) {
        chkShowDistances.addEventListener("change", () => {
            updateMarkersListUI();
            if (currentChartData) {
                renderChart();
            }
        });
    }

    // Chart scale adjustable range/number listeners
    const chartScaleRange = document.getElementById("chartScaleRange");
    const chartScaleNum = document.getElementById("chartScaleNum");
    const chartScaleVal = document.getElementById("chartScaleVal");

    function updateChartScaleValue(val) {
        const intVal = parseInt(val) || 200;
        const boundedVal = Math.max(10, Math.min(1000, intVal));
        
        if (chartScaleRange && chartScaleRange.value != boundedVal) chartScaleRange.value = boundedVal;
        if (chartScaleNum && chartScaleNum.value != boundedVal) chartScaleNum.value = boundedVal;
        if (chartScaleVal) chartScaleVal.innerText = `${boundedVal} px`;
        
        if (currentChartData) {
            renderChart();
        }
    }

    if (chartScaleRange) {
        chartScaleRange.addEventListener("input", (e) => updateChartScaleValue(e.target.value));
    }
    if (chartScaleNum) {
        chartScaleNum.addEventListener("change", (e) => updateChartScaleValue(e.target.value));
        chartScaleNum.addEventListener("keyup", (e) => updateChartScaleValue(e.target.value));
    }

    // Search markers list listener
    const searchMarkersInput = document.getElementById("searchMarkersInput");
    if (searchMarkersInput) {
        searchMarkersInput.addEventListener("input", () => {
            updateMarkersListUI();
        });
    }

    // Toggle Upload panel button click
    const btnToggle = document.getElementById("btnToggleUpload");
    if (btnToggle) {
        btnToggle.addEventListener("click", () => {
            const uploadCard = document.getElementById("adminUploadCard");
            uploadCard.style.display = uploadCard.style.display === "none" ? "block" : "none";
        });
    }
    
    // Upload Excel Form submission
    const uploadForm = document.getElementById("gradientUploadForm");
    if (uploadForm) {
        uploadForm.addEventListener("submit", handleExcelUpload);
    }
    
    // Sync UI with global admin login status
    syncAdminUI(window.isAdmin);
    window.addEventListener("adminAuthChanged", (e) => {
        syncAdminUI(e.detail.isAdmin);
    });

    // Resize listener for scrollable container width calculations
    window.addEventListener("resize", () => {
        if (currentChartData && currentChartType === 'profile') {
            renderChart();
        }
    });
    
    // Text Annotation add button
    const btnAddAnnotation = document.getElementById("btnAddAnnotation");
    if (btnAddAnnotation) {
        btnAddAnnotation.addEventListener("click", addTextAnnotation);
    }
    
    // Canvas drag support for text annotations
    const canvas = document.getElementById("gradientChart");
    if (canvas) {
        canvas.addEventListener("mousedown", (e) => {
            if (!chartInstance || chartTextAnnotations.length === 0) return;
            const rect = canvas.getBoundingClientRect();
            const mx = e.clientX - rect.left;
            const my = e.clientY - rect.top;
            
            const ctx = canvas.getContext("2d");
            for (let i = chartTextAnnotations.length - 1; i >= 0; i--) {
                const ann = chartTextAnnotations[i];
                ctx.font = `bold ${ann.fontSize}px Arial`;
                const tw = ctx.measureText(ann.text).width;
                const th = ann.fontSize;
                
                // Get pixel coordinates from chart instance directly
                const xAxis = chartInstance.scales.x;
                const yAxis = chartInstance.scales.y;
                const ax = xAxis.getPixelForValue(ann.km.toFixed(3));
                const ay = yAxis.getPixelForValue(ann.elevation);
                
                if (mx >= ax - 8 && mx <= ax + tw + 8 &&
                    my >= ay - th - 8 && my <= ay + 8) {
                    draggingAnnotation = ann;
                    ann._dragOffsetX = mx - ax;
                    ann._dragOffsetY = my - ay;
                    canvas.style.cursor = "grabbing";
                    e.preventDefault();
                    return;
                }
            }
        });
        
        canvas.addEventListener("mousemove", (e) => {
            if (!chartInstance) return;
            const rect = canvas.getBoundingClientRect();
            const mx = e.clientX - rect.left;
            const my = e.clientY - rect.top;
            
            if (draggingAnnotation) {
                const xAxis = chartInstance.scales.x;
                const yAxis = chartInstance.scales.y;
                
                const targetX = mx - (draggingAnnotation._dragOffsetX || 0);
                const targetY = my - (draggingAnnotation._dragOffsetY || 0);
                
                // Convert pixel back to data coords using Chart.js scales
                const targetKM = xAxis.getValueForPixel(targetX);
                const targetElev = yAxis.getValueForPixel(targetY);
                
                const profile = currentChartData.elevation_profile;
                const minKM = profile[0].km;
                const maxKM = profile[profile.length - 1].km;
                
                draggingAnnotation.km = Math.max(minKM, Math.min(maxKM, targetKM));
                draggingAnnotation.elevation = targetElev;
                
                renderChart(true);
                e.preventDefault();
            } else {
                // Change cursor to pointer if hovering over an annotation text box
                let hoverFound = false;
                const ctx = canvas.getContext("2d");
                for (let i = chartTextAnnotations.length - 1; i >= 0; i--) {
                    const ann = chartTextAnnotations[i];
                    ctx.font = `bold ${ann.fontSize}px Arial`;
                    const tw = ctx.measureText(ann.text).width;
                    const th = ann.fontSize;
                    
                    const xAxis = chartInstance.scales.x;
                    const yAxis = chartInstance.scales.y;
                    const ax = xAxis.getPixelForValue(ann.km.toFixed(3));
                    const ay = yAxis.getPixelForValue(ann.elevation);
                    
                    if (mx >= ax - 8 && mx <= ax + tw + 8 &&
                        my >= ay - th - 8 && my <= ay + 8) {
                        hoverFound = true;
                        break;
                    }
                }
                canvas.style.cursor = hoverFound ? "pointer" : "default";
            }
        });
        
        canvas.addEventListener("mouseup", (e) => {
            if (draggingAnnotation) {
                draggingAnnotation = null;
                canvas.style.cursor = "default";
            }
        });
        
        canvas.addEventListener("mouseleave", (e) => {
            if (draggingAnnotation) {
                draggingAnnotation = null;
                canvas.style.cursor = "default";
            }
        });
    }
});

/* ================= FILTER DROP DOWN LOADS ================= */
function loadSections() {
    fetch("/api/gradient/sections")
        .then(res => res.json())
        .then(sections => {
            const select = document.getElementById("filterSection");
            select.innerHTML = '<option value="">All Sections</option>';
            sections.forEach(sec => {
                select.innerHTML += `<option value="${sec}">${sec}</option>`;
            });
            // Also load dependent filters initially for all sections
            loadDependentFilters("");
        });
}

function loadDependentFilters(section) {
    const lineSelect = document.getElementById("filterLine");
    const dirSelect = document.getElementById("filterDirection");
    
    const prevLineVal = lineSelect.value;
    const prevDirVal = dirSelect.value;
    
    let lineUrl = "/api/gradient/lines";
    let dirUrl = "/api/gradient/directions";
    
    if (section) {
        lineUrl += `?section=${encodeURIComponent(section)}`;
        dirUrl += `?section=${encodeURIComponent(section)}`;
    }
    
    fetch(lineUrl)
        .then(res => res.json())
        .then(lines => {
            lineSelect.innerHTML = '<option value="">All Lines</option>';
            lines.forEach(l => {
                const selected = l === prevLineVal ? 'selected' : '';
                lineSelect.innerHTML += `<option value="${l}" ${selected}>${l}</option>`;
            });
        });

    fetch(dirUrl)
        .then(res => res.json())
        .then(directions => {
            dirSelect.innerHTML = '<option value="">All Directions</option>';
            directions.forEach(dir => {
                const selected = dir === prevDirVal ? 'selected' : '';
                dirSelect.innerHTML += `<option value="${dir}" ${selected}>${dir}</option>`;
            });
        });
}

/* ================= FETCH DATA & POPULATE TABLE ================= */
function fetchGradients() {
    const section = document.getElementById("filterSection").value;
    const line = document.getElementById("filterLine").value;
    const direction = document.getElementById("filterDirection").value;
    const search = document.getElementById("textSearch").value;
    
    let url = `/api/gradient/search?page=${currentPage}&limit=${pageSize}`;
    if (section) url += `&section=${encodeURIComponent(section)}`;
    if (line) url += `&line=${encodeURIComponent(line)}`;
    if (direction) url += `&direction=${encodeURIComponent(direction)}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    
    const tbody = document.getElementById("gradientTableBody");
    tbody.innerHTML = '<tr><td colspan="11" class="text-muted py-4"><div class="spinner-border spinner-border-sm text-primary me-2"></div>Loading data...</td></tr>';
    
    fetch(url)
        .then(res => res.json())
        .then(data => {
            document.getElementById("val-total").innerText = data.total;
            renderTable(data.records);
            updatePaginationControls(data.total);
        })
        .catch(err => {
            tbody.innerHTML = '<tr><td colspan="11" class="text-danger py-4">Failed to fetch gradient data.</td></tr>';
        });
}

function renderTable(records) {
    const tbody = document.getElementById("gradientTableBody");
    tbody.innerHTML = "";
    
    if (records.length === 0) {
        tbody.innerHTML = '<tr><td colspan="11" class="text-muted py-5 text-center">No gradient records found matching active filters.</td></tr>';
        return;
    }
    
    records.forEach(r => {
        const tr = document.createElement("tr");
        
        let badgeClass = "badge bg-secondary";
        const dir = (r.direction || "").toUpperCase();
        if (dir.includes("RISE")) badgeClass = "badge badge-rise";
        else if (dir.includes("FALL")) badgeClass = "badge badge-fall";
        else if (dir.includes("LEVEL")) badgeClass = "badge badge-level";
        
        tr.innerHTML = `
            <td>${r.div_rly}</td>
            <td class="fw-bold">${r.section}</td>
            <td>${r.line}</td>
            <td>${r.km_from}</td>
            <td>${r.met_from}</td>
            <td>${r.km_to}</td>
            <td>${r.met_to}</td>
            <td>${r.gauge}</td>
            <td>${r.length_m}</td>
            <td><span class="${badgeClass}">${r.direction}</span></td>
            <td class="fw-bold text-dark">${r.grade === "0" ? "-" : r.grade}</td>
        `;
        tbody.appendChild(tr);
    });
}

function updatePaginationControls(total) {
    const info = document.getElementById("paginationInfo");
    const prev = document.getElementById("btnPrevPage");
    const next = document.getElementById("btnNextPage");
    const pageNum = document.getElementById("currentPageNum");
    
    const start = total === 0 ? 0 : (currentPage - 1) * pageSize + 1;
    const end = Math.min(currentPage * pageSize, total);
    
    info.innerText = `Showing ${start} to ${end} of ${total} records`;
    pageNum.innerText = `Page ${currentPage}`;
    
    if (currentPage <= 1) {
        prev.classList.add("disabled");
    } else {
        prev.classList.remove("disabled");
    }
    
    if (end >= total) {
        next.classList.add("disabled");
    } else {
        next.classList.remove("disabled");
    }
}

function resetFilters() {
    document.getElementById("filterSection").value = "";
    document.getElementById("filterLine").value = "";
    document.getElementById("filterDirection").value = "";
    document.getElementById("textSearch").value = "";
    currentPage = 1;
    loadDependentFilters("");
    fetchGradients();
    document.getElementById("chartCard").style.display = "none";
    
    // Hide predefined signals container
    const predContainer = document.getElementById("predefinedSignalsContainer");
    if (predContainer) predContainer.style.display = "none";
}

/* ================= CHART LOGIC ================= */
function fetchChartData(section, line = "") {
    let url = `/api/gradient/chart-data?section=${encodeURIComponent(section)}`;
    if (line) {
        url += `&line=${encodeURIComponent(line)}`;
    }
    
    fetch(url)
        .then(res => res.json())
        .then(data => {
            currentChartData = data;
            document.getElementById("chartSectionTitle").innerText = `${data.section} (Line: ${data.line || 'All'})`;
            document.getElementById("chartCard").style.display = "block";
            
            // Show/Hide predefined signals select dropdown based on section
            const predContainer = document.getElementById("predefinedSignalsContainer");
            const selectPred = document.getElementById("selectPredefinedSignals");
            if (predContainer && selectPred) {
                if (data.section === "RPH - DUMK") {
                    predContainer.style.display = "block";
                    selectPred.value = ""; // Reset value on reload
                } else {
                    predContainer.style.display = "none";
                }
            }
            
            renderChart();
        })
        .catch(err => {
            console.error("Error fetching chart data:", err);
        });
}

function toggleChartView(type) {
    currentChartType = type;
    
    const btnProfile = document.getElementById("btnViewProfile");
    const btnDist = document.getElementById("btnViewDistribution");
    
    if (type === 'profile') {
        btnProfile.className = "btn btn-primary active";
        btnDist.className = "btn btn-outline-primary";
    } else {
        btnProfile.className = "btn btn-outline-primary";
        btnDist.className = "btn btn-primary active";
    }
    
    renderChart();
}

function renderChart(disableAnimation = false) {
    if (!currentChartData) return;
    
    const ctx = document.getElementById("gradientChart").getContext("2d");
    if (chartInstance) {
        chartInstance.destroy();
    }
    
    const container = document.getElementById("gradientChartContainer");
    
    if (currentChartType === 'profile') {
        // Deep copy the cached elevation profile points
        let profile = JSON.parse(JSON.stringify(currentChartData.elevation_profile));
        
        const profileMinKM = profile.length > 0 ? profile[0].km : 0;
        const profileMaxKM = profile.length > 0 ? profile[profile.length - 1].km : 0;
        
        // If stalling from/to is active, insert them into labels coordinates
        if (activeStallingFromKM !== null && activeStallingFromKM >= profileMinKM && activeStallingFromKM <= profileMaxKM) {
            if (!profile.some(p => Math.abs(p.km - activeStallingFromKM) < 0.0001)) {
                profile.push({
                    km: activeStallingFromKM,
                    elevation: getInterpolatedElevation(activeStallingFromKM, profile),
                    grade: "Marker Start",
                    direction: "MARKER"
                });
            }
        }
        if (activeStallingToKM !== null && activeStallingToKM >= profileMinKM && activeStallingToKM <= profileMaxKM) {
            if (!profile.some(p => Math.abs(p.km - activeStallingToKM) < 0.0001)) {
                profile.push({
                    km: activeStallingToKM,
                    elevation: getInterpolatedElevation(activeStallingToKM, profile),
                    grade: "Marker End",
                    direction: "MARKER"
                });
            }
        }
        
        // Insert custom text location if active
        if (activeLabelText && activeTextKM !== null && activeTextKM >= profileMinKM && activeTextKM <= profileMaxKM) {
            if (!profile.some(p => Math.abs(p.km - activeTextKM) < 0.0001)) {
                profile.push({
                    km: activeTextKM,
                    elevation: getInterpolatedElevation(activeTextKM, profile),
                    grade: activeLabelText,
                    direction: "TEXT_POINT"
                });
            }
        }
        
        // Insert custom markers if active and within visible bounds
        customMarkers.forEach(m => {
            if (m.km >= profileMinKM && m.km <= profileMaxKM) {
                let existing = profile.find(p => Math.abs(p.km - m.km) < 0.0001);
                if (existing) {
                    existing.direction = `CUSTOM_POINT_${m.type}`;
                    if (m.label) existing.grade = m.label;
                } else {
                    profile.push({
                        km: m.km,
                        elevation: getInterpolatedElevation(m.km, profile),
                        grade: m.label || m.type,
                        direction: `CUSTOM_POINT_${m.type}`
                    });
                }
            }
        });
        
        profile.sort((a, b) => a.km - b.km);
        
        // Calculate the physical distance range of the profile
        const kmDistance = profileMaxKM - profileMinKM;
        // Apply the chosen dynamic scale value (pixels per Kilometer)
        const scaleSelector = document.getElementById("chartScaleRange");
        const pxPerKM = scaleSelector ? parseInt(scaleSelector.value) : 200;
        // Plus 150px safety margins for chart titles/layout.
        const dynamicWidth = Math.round(kmDistance * pxPerKM) + 150;
        container.style.width = `${dynamicWidth}px`;
        
        const labels = profile.map(p => p.km.toFixed(3));
        const elevationData = profile.map(p => p.elevation);
        const tooltipDetails = profile.map(p => p.grade);
        const directions = profile.map(p => p.direction);
        
        // Style arrays for individual points
        const pointBackgroundColors = [];
        const pointRadii = [];
        const pointHoverRadii = [];
        const pointStyles = [];
        
        profile.forEach(p => {
            if (p.direction === "MARKER") {
                pointBackgroundColors.push("#dc2626"); // Red boundary marker
                pointRadii.push(6);
                pointHoverRadii.push(9);
                pointStyles.push("circle");
            } else if (p.direction.startsWith("CUSTOM_POINT_")) {
                const type = p.direction.replace("CUSTOM_POINT_", "");
                let color = "#4b5563";
                let style = "circle";
                if (type === 'stalled') { color = "#dc2626"; style = "triangle"; }
                else if (type === 'signal') { color = "#ea580c"; style = "rectRot"; }
                else if (type === 'station') { color = "#1e40af"; style = "rect"; }
                else if (type === 'neutral_section') { color = "#7c3aed"; style = "star"; }
                else if (type === 'lc_gate') { color = "#0891b2"; style = "rect"; }
                else if (type === 'speed') { color = "#16a34a"; style = "rectRounded"; }
                
                // Override with custom marker color if selected by user
                const m = customMarkers.find(cm => Math.abs(cm.km - p.km) < 0.0001 && cm.type === type);
                if (m && m.color) {
                    color = m.color;
                }
                
                pointBackgroundColors.push(color);
                pointRadii.push(8);
                pointHoverRadii.push(11);
                pointStyles.push(style);
            } else if (p.direction === "TEXT_POINT") {
                pointBackgroundColors.push("rgba(0,0,0,0)"); // Hidden anchor point
                pointRadii.push(0);
                pointHoverRadii.push(0);
                pointStyles.push("circle");
            } else {
                pointBackgroundColors.push("#2563eb"); // Blue standard
                pointRadii.push(3);
                pointHoverRadii.push(6);
                pointStyles.push("circle");
            }
        });
        
        // Build datasets array
        const datasets = [{
            label: 'Relative Elevation (meters)',
            data: elevationData,
            borderColor: '#2563eb',
            backgroundColor: 'rgba(37, 99, 235, 0.1)',
            borderWidth: 2,
            fill: true,
            tension: 0.1,
            pointBackgroundColor: pointBackgroundColors,
            pointRadius: pointRadii,
            pointHoverRadius: pointHoverRadii,
            pointStyle: pointStyles
        }];
        
        chartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: disableAnimation ? false : undefined,
                layout: {
                    padding: {
                        top: 65, // top space for horizontal gradient labels and N/S labels
                        bottom: 110 // bottom space for slanted signal names, direction, and help text
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            afterBody: function(context) {
                                const idx = context[0].dataIndex;
                                const dir = directions[idx];
                                if (dir === "MARKER") {
                                     return `Boundary KM`;
                                } else if (dir.startsWith("CUSTOM_POINT_")) {
                                     const type = dir.replace("CUSTOM_POINT_", "");
                                     const typeName = type.toUpperCase().replace("_", " ");
                                     let detail = `${typeName}: ${tooltipDetails[idx]}`;
                                     
                                     // Find matching custom marker in profile
                                     const p = profile[idx];
                                     const m = customMarkers.find(cm => Math.abs(cm.km - p.km) < 0.0001 && cm.type === type);
                                     
                                     if (m && m.speed !== undefined && m.speed !== null && m.speed !== '') {
                                         detail += `\nTrain Speed: ${m.speed} km/h`;
                                     }
                                     
                                     const stalled = customMarkers.find(cm => cm.type === 'stalled');
                                     let speedMarker = null;
                                     if (stalled) {
                                         const markersWithSpeed = customMarkers.filter(cm => cm.type !== 'stalled' && cm.speed !== undefined && cm.speed !== null && cm.speed !== '' && cm.speed > 0);
                                         if (markersWithSpeed.length > 0) {
                                             speedMarker = markersWithSpeed.reduce((prev, curr) => 
                                                 Math.abs(curr.km - stalled.km) < Math.abs(prev.km - stalled.km) ? curr : prev
                                             );
                                         }
                                     }
                                     
                                     if (stalled && speedMarker) {
                                         const distM = Math.round(Math.abs(stalled.km - speedMarker.km) * 1000);
                                         const u = speedMarker.speed * (5/18); // m/s
                                         const timeSec = Math.round(2 * distM / u);
                                         const decel = (u * u) / (2 * distM); // m/s^2
                                         
                                         if (type === 'stalled') {
                                             detail += `\n\nSpeed Reduction Analysis:\n• Initial Speed: ${speedMarker.speed} km/h (at KM ${speedMarker.km.toFixed(3)})\n• Stalled Speed: 0 km/h\n• Distance: ${distM} m\n• Time Taken: ${timeSec} seconds\n• Deceleration Rate: ${decel.toFixed(3)} m/s²`;
                                         } else if (m && m.id === speedMarker.id) {
                                             detail += `\n\nStalling Analysis:\n• Running Speed: ${speedMarker.speed} km/h\n• Stalled at KM: ${stalled.km.toFixed(3)}\n• Dist to Stalled: ${distM} m\n• Time to Stall: ${timeSec} seconds\n• Deceleration Rate: ${decel.toFixed(3)} m/s²`;
                                         }
                                     }
                                     return detail;
                                } else if (dir === "TEXT_POINT") {
                                     return `Label: ${tooltipDetails[idx]}`;
                                }
                                return `Slope: ${tooltipDetails[idx]}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: { display: false },
                        ticks: {
                            callback: function(val, index) {
                                const kmStr = this.getLabelForValue(val);
                                // Check if this profile point belongs to a custom marker point (excluding neutral sections drawn at the top)
                                const pt = profile[index];
                                if (pt && pt.direction && pt.direction.startsWith("CUSTOM_POINT_") && !pt.direction.includes("neutral_section")) {
                                    // Suppress tick label to prevent overwriting station/signal names
                                    return "";
                                }
                                return kmStr;
                            },
                            font: {
                                size: disableAnimation ? 13 : 11,
                                weight: 'bold'
                            }
                        }
                    },
                    y: {
                        title: { display: false },
                        min: window._tempYMin !== undefined ? window._tempYMin : undefined,
                        max: window._tempYMax !== undefined ? window._tempYMax : undefined,
                        ticks: {
                            font: {
                                size: disableAnimation ? 13 : 11,
                                weight: 'bold'
                            }
                        }
                    }
                }
            },
            plugins: [{
                id: 'customStallingGraphics',
                beforeDraw: function(chart) {
                    const ctxDraw = chart.ctx;
                    ctxDraw.save();
                    ctxDraw.fillStyle = '#ffffff'; // Paint solid white background
                    ctxDraw.fillRect(0, 0, chart.width, chart.height);
                    ctxDraw.restore();
                },
                afterDraw: function(chart) {
                    const ctxDraw = chart.ctx;
                    const xAxis = chart.scales.x;
                    const yAxis = chart.scales.y;
                    
                    const topY = yAxis.top;
                    const bottomY = yAxis.bottom;
                    
                    // Draw horizontal Y-axis title at the top-left of the chart grid
                    ctxDraw.save();
                    ctxDraw.font = disableAnimation ? 'bold 12.5px Arial' : 'bold 9.5px Arial';
                    ctxDraw.fillStyle = '#475569';
                    ctxDraw.textAlign = 'left';
                    ctxDraw.textBaseline = 'bottom';
                    ctxDraw.fillText('Relative Elevation (meters)', xAxis.left, topY - 10);
                    ctxDraw.restore();
                    
                    const activeProfile = currentChartData.elevation_profile;
                    if (!activeProfile || activeProfile.length === 0) return;
                    const profileMinKM = activeProfile[0].km;
                    const profileMaxKM = activeProfile[activeProfile.length - 1].km;
                    
                    function getXPixel(km) {
                        if (km < profileMinKM) return xAxis.left;
                        if (km > profileMaxKM) return xAxis.right;
                        return xAxis.getPixelForValue(km.toFixed(3));
                    }
                    
                    // 1. Draw Stalling Area Zone & vertical boundary lines
                    if (activeStallingFromKM !== null && activeStallingToKM !== null) {
                        if (activeStallingFromKM <= profileMaxKM && activeStallingToKM >= profileMinKM) {
                            const xFrom = getXPixel(activeStallingFromKM);
                            const xTo = getXPixel(activeStallingToKM);
                            
                            // Draw shaded zone
                            ctxDraw.fillStyle = 'rgba(239, 68, 68, 0.15)'; // transparent red
                            ctxDraw.fillRect(xFrom, topY, xTo - xFrom, bottomY - topY);
                            
                            // Draw vertical boundary lines
                            ctxDraw.strokeStyle = '#dc2626';
                            ctxDraw.lineWidth = 2;
                            ctxDraw.setLineDash([5, 5]);
                            
                            // From KM line
                            if (activeStallingFromKM >= profileMinKM && activeStallingFromKM <= profileMaxKM) {
                                ctxDraw.beginPath();
                                ctxDraw.moveTo(xFrom, topY);
                                ctxDraw.lineTo(xFrom, bottomY);
                                ctxDraw.stroke();
                                
                                ctxDraw.font = 'bold 11px Arial';
                                ctxDraw.fillStyle = '#dc2626';
                                ctxDraw.textAlign = 'center';
                                ctxDraw.fillText(activeStallingFromKM.toFixed(3), xFrom, topY - 5);
                            }
                            
                            // To KM line
                            if (activeStallingToKM >= profileMinKM && activeStallingToKM <= profileMaxKM) {
                                ctxDraw.beginPath();
                                ctxDraw.moveTo(xTo, topY);
                                ctxDraw.lineTo(xTo, bottomY);
                                ctxDraw.stroke();
                                
                                ctxDraw.font = 'bold 11px Arial';
                                ctxDraw.fillStyle = '#dc2626';
                                ctxDraw.textAlign = 'center';
                                ctxDraw.fillText(activeStallingToKM.toFixed(3), xTo, topY - 5);
                            }
                            
                            ctxDraw.setLineDash([]);
                        }
                    }
                    
                    // 2. Draw Custom adjustable Label text bubble
                    if (activeLabelText && activeTextKM !== null && activeTextElev !== null) {
                        if (activeTextKM >= profileMinKM && activeTextKM <= profileMaxKM) {
                            const xText = getXPixel(activeTextKM);
                            const yText = yAxis.getPixelForValue(activeTextElev);
                            
                            ctxDraw.font = 'bold 12px Arial';
                            ctxDraw.fillStyle = '#1e3a8a';
                            ctxDraw.textAlign = 'center';
                            
                            const textWidth = ctxDraw.measureText(activeLabelText).width;
                            
                            // Draw background text bubble
                            ctxDraw.fillStyle = '#ffffff';
                            ctxDraw.strokeStyle = '#2563eb';
                            ctxDraw.lineWidth = 1;
                            
                            const bubbleW = textWidth + 12;
                            const bubbleH = 20;
                            const bubbleX = xText - (bubbleW / 2);
                            const bubbleY = yText - 10 - bubbleH;
                            
                            ctxDraw.beginPath();
                            ctxDraw.rect(bubbleX, bubbleY, bubbleW, bubbleH);
                            ctxDraw.fill();
                            ctxDraw.stroke();
                            
                            ctxDraw.fillStyle = '#1e3a8a';
                            ctxDraw.fillText(activeLabelText, xText, bubbleY + 14);
                        }
                    }
                    
                    // 2.5 Draw Custom Speed Restriction Ranges (Arrows)
                    customMarkers.forEach(m => {
                        if (m.type === 'speed' && m.endKm !== undefined && m.endKm !== null) {
                            // Check if the range overlaps with the currently visible profile range
                            const visibleStart = Math.max(m.km, profileMinKM);
                            const visibleEnd = Math.min(m.endKm, profileMaxKM);
                            
                            if (visibleEnd > visibleStart) {
                                const xStart = getXPixel(m.km);
                                const xEnd = getXPixel(m.endKm);
                                
                                const yStartCurve = yAxis.getPixelForValue(getInterpolatedElevation(m.km, activeProfile));
                                const yEndCurve = yAxis.getPixelForValue(getInterpolatedElevation(m.endKm, activeProfile));
                                
                                // Find maximum elevation in the range
                                let maxElev = -999999;
                                activeProfile.forEach(p => {
                                    if (p.km >= m.km && p.km <= m.endKm) {
                                        if (p.elevation > maxElev) {
                                            maxElev = p.elevation;
                                        }
                                    }
                                });
                                maxElev = Math.max(maxElev, getInterpolatedElevation(m.km, activeProfile), getInterpolatedElevation(m.endKm, activeProfile));
                                
                                const yMaxCurve = yAxis.getPixelForValue(maxElev);
                                const yArrowFinal = Math.max(yMaxCurve - 35, topY + 15);
                                
                                // Draw thin vertical dotted boundary lines to the curve
                                ctxDraw.strokeStyle = m.color || "#16a34a";
                                ctxDraw.lineWidth = 1;
                                ctxDraw.setLineDash([2, 2]);
                                ctxDraw.beginPath();
                                ctxDraw.moveTo(xStart, yArrowFinal);
                                ctxDraw.lineTo(xStart, yStartCurve);
                                ctxDraw.moveTo(xEnd, yArrowFinal);
                                ctxDraw.lineTo(xEnd, yEndCurve);
                                ctxDraw.stroke();
                                ctxDraw.setLineDash([]); // reset
                                
                                // Draw horizontal arrow line
                                ctxDraw.strokeStyle = m.color || "#16a34a";
                                ctxDraw.fillStyle = m.color || "#16a34a";
                                ctxDraw.lineWidth = 2.5;
                                ctxDraw.beginPath();
                                ctxDraw.moveTo(xStart, yArrowFinal);
                                ctxDraw.lineTo(xEnd, yArrowFinal);
                                ctxDraw.stroke();
                                
                                // Draw left arrowhead
                                ctxDraw.beginPath();
                                ctxDraw.moveTo(xStart, yArrowFinal);
                                ctxDraw.lineTo(xStart + 6, yArrowFinal - 4);
                                ctxDraw.lineTo(xStart + 6, yArrowFinal + 4);
                                ctxDraw.closePath();
                                ctxDraw.fill();
                                
                                // Draw right arrowhead
                                ctxDraw.beginPath();
                                ctxDraw.moveTo(xEnd, yArrowFinal);
                                ctxDraw.lineTo(xEnd - 6, yArrowFinal - 4);
                                ctxDraw.lineTo(xEnd - 6, yArrowFinal + 4);
                                ctxDraw.closePath();
                                ctxDraw.fill();
                                
                                // Draw centered label badge
                                const rangeText = `${m.label} (${m.km.toFixed(3)} - ${m.endKm.toFixed(3)})`;
                                ctxDraw.font = disableAnimation ? 'bold 11px Arial' : 'bold 9px Arial';
                                const textW = ctxDraw.measureText(rangeText).width;
                                const badgeW = textW + 8;
                                const badgeH = 14;
                                const badgeX = ((xStart + xEnd) / 2) - badgeW / 2;
                                const badgeY = yArrowFinal - 18;
                                
                                ctxDraw.fillStyle = '#ffffff';
                                ctxDraw.fillRect(badgeX, badgeY, badgeW, badgeH);
                                ctxDraw.strokeStyle = m.color || "#16a34a";
                                ctxDraw.lineWidth = 1;
                                ctxDraw.strokeRect(badgeX, badgeY, badgeW, badgeH);
                                
                                ctxDraw.fillStyle = m.color || "#16a34a";
                                ctxDraw.textAlign = 'center';
                                ctxDraw.textBaseline = 'middle';
                                ctxDraw.fillText(rangeText, (xStart + xEnd) / 2, badgeY + badgeH / 2);
                            }
                        }
                    });

                    // 3. Draw Stacked Custom Point Markers with overlap protection
                    const lastXForTopTier = {};
                    const lastXForBottomTier = {};
                    const sortedPoints = [];
                    
                    customMarkers.forEach(m => {
                        // Skip speed range markers here (drawn as arrows instead)
                        if (m.type === 'speed' && m.endKm !== undefined && m.endKm !== null) return;
                        
                        if (m.km >= profileMinKM && m.km <= profileMaxKM) {
                            let prefix = "";
                            let color = "#4b5563";
                            let lineStyle = "dashed";
                             if (m.type === 'stalled') { prefix = "STALLED: "; color = "#dc2626"; lineStyle = "solid"; }
                             else if (m.type === 'signal') { prefix = ""; color = "#ea580c"; lineStyle = "dashed"; }
                             else if (m.type === 'station') { prefix = "STN: "; color = "#1e40af"; lineStyle = "dashed"; }
                             else if (m.type === 'neutral_section') { prefix = ""; color = "#7c3aed"; lineStyle = "dashed"; }
                             else if (m.type === 'lc_gate') { prefix = "LC: "; color = "#0891b2"; lineStyle = "dashed"; }
                             else if (m.type === 'speed') { prefix = "SPEED: "; color = "#16a34a"; lineStyle = "dashed"; }
                            
                            if (m.color) {
                                color = m.color;
                            }
                            
                            sortedPoints.push({
                                km: m.km,
                                label: `${prefix}${m.label} (${m.km.toFixed(3)})`,
                                color: color,
                                lineStyle: lineStyle,
                                type: m.type
                            });
                        }
                    });
                    
                    // Sort by X pixel coordinate (km value)
                    sortedPoints.sort((a, b) => a.km - b.km);
                    
                    sortedPoints.forEach(pt => {
                        const x = getXPixel(pt.km);
                        
                        // Draw full vertical gridline only for physical infrastructure, not for speed markers
                        if (pt.type !== 'speed') {
                            ctxDraw.strokeStyle = pt.color;
                            ctxDraw.lineWidth = pt.lineStyle === 'solid' ? 2.5 : 2;
                            if (pt.lineStyle === 'dashed') {
                                ctxDraw.setLineDash([4, 4]);
                            } else {
                                ctxDraw.setLineDash([]);
                            }
                            ctxDraw.beginPath();
                            ctxDraw.moveTo(x, topY);
                            ctxDraw.lineTo(x, bottomY);
                            ctxDraw.stroke();
                            ctxDraw.setLineDash([]); // reset
                        }
                        
                        if (pt.type === 'neutral_section') {
                            // Find the lowest top tier (for N/S at top)
                            let tier = 0;
                            while (true) {
                                const lastX = lastXForTopTier[tier];
                                if (lastX === undefined || (x - lastX) > 95) {
                                    lastXForTopTier[tier] = x;
                                    break;
                                }
                                tier++;
                            }
                            
                            const labelY = topY - 5 - (tier * 15);
                            ctxDraw.strokeStyle = pt.color;
                            ctxDraw.lineWidth = 1;
                            ctxDraw.setLineDash([2, 2]);
                            ctxDraw.beginPath();
                            ctxDraw.moveTo(x, topY);
                            ctxDraw.lineTo(x, labelY + 2);
                            ctxDraw.stroke();
                            ctxDraw.setLineDash([]); // reset
                            
                            // Draw slanted text slanted -45 degrees pointing up-right
                            ctxDraw.save();
                            ctxDraw.translate(x, labelY);
                            ctxDraw.rotate(-Math.PI / 4);
                            ctxDraw.font = disableAnimation ? 'bold 13px Arial' : 'bold 11px Arial';
                            ctxDraw.fillStyle = pt.color;
                            ctxDraw.textAlign = 'left';
                            ctxDraw.textBaseline = 'middle';
                            ctxDraw.fillText(pt.label, 4, 0);
                            ctxDraw.restore();
                        } else if (pt.type === 'speed') {
                            // Draw speed marker differently: directly on the curve as a speedometer pin
                            const yCurve = yAxis.getPixelForValue(getInterpolatedElevation(pt.km, activeProfile));
                            
                            // Draw a small vertical pin upwards from the curve line
                            ctxDraw.strokeStyle = pt.color;
                            ctxDraw.lineWidth = 1.5;
                            ctxDraw.beginPath();
                            ctxDraw.moveTo(x, yCurve);
                            ctxDraw.lineTo(x, yCurve - 20);
                            ctxDraw.stroke();
                            
                            // Draw a small horizontal speed pill badge at the top of the pin
                            ctxDraw.font = disableAnimation ? 'bold 11px Arial' : 'bold 9px Arial';
                            // Extract just the speed label, e.g. "30 km/h" or "30"
                            const speedText = pt.label.replace("SPEED: ", "").split(" (")[0];
                            const textW = ctxDraw.measureText(speedText).width;
                            const badgeW = textW + 8;
                            const badgeH = 14;
                            const badgeX = x - badgeW / 2;
                            const badgeY = yCurve - 20 - badgeH;
                            
                            // Background and border
                            ctxDraw.fillStyle = '#ffffff';
                            ctxDraw.fillRect(badgeX, badgeY, badgeW, badgeH);
                            ctxDraw.strokeStyle = pt.color;
                            ctxDraw.lineWidth = 1;
                            ctxDraw.strokeRect(badgeX, badgeY, badgeW, badgeH);
                            
                            // Draw text centered inside the pill
                            ctxDraw.fillStyle = pt.color;
                            ctxDraw.textAlign = 'center';
                            ctxDraw.textBaseline = 'middle';
                            ctxDraw.fillText(speedText, x, badgeY + badgeH / 2);
                        } else {
                            // Find the lowest bottom tier (for signals, stations, etc. at bottom)
                            let tier = 0;
                            while (true) {
                                const lastX = lastXForBottomTier[tier];
                                if (lastX === undefined || (x - lastX) > 95) {
                                    lastXForBottomTier[tier] = x;
                                    break;
                                }
                                tier++;
                            }
                            
                            const labelY = bottomY + 8 + (tier * 15);
                            ctxDraw.strokeStyle = pt.color;
                            ctxDraw.lineWidth = 1;
                            ctxDraw.setLineDash([2, 2]);
                            ctxDraw.beginPath();
                            ctxDraw.moveTo(x, bottomY);
                            ctxDraw.lineTo(x, labelY - 2);
                            ctxDraw.stroke();
                            ctxDraw.setLineDash([]); // reset
                            
                            // Draw slanted text slanted -45 degrees pointing down-left
                            ctxDraw.save();
                            ctxDraw.translate(x, labelY);
                            ctxDraw.rotate(-Math.PI / 4);
                            ctxDraw.font = disableAnimation ? 'bold 13px Arial' : 'bold 11px Arial';
                            ctxDraw.fillStyle = pt.color;
                            ctxDraw.textAlign = 'right';
                            ctxDraw.textBaseline = 'middle';
                            ctxDraw.fillText(pt.label, -4, 0);
                            ctxDraw.restore();
                        }
                    });

                    // 4. Draw Horizontal Dimension Lines for distances to Stalled location (if enabled and selected)
                    const showDistances = document.getElementById("chkShowDistances") ? document.getElementById("chkShowDistances").checked : true;
                    const stalledMarker = customMarkers.find(m => m.type === 'stalled');
                    if (showDistances && stalledMarker && stalledMarker.km >= profileMinKM && stalledMarker.km <= profileMaxKM) {
                        const xStalled = getXPixel(stalledMarker.km);
                        let dimIndex = 0;
                        
                        // Filter custom markers that have calcDistance checked and are within bounds
                        const markersToShow = customMarkers.filter(m => m.type !== 'stalled' && m.calcDistance && m.km >= profileMinKM && m.km <= profileMaxKM);
                        
                        // Sort by proximity to stalled point so closer lines sit below (keeps vertical layout clean)
                        markersToShow.sort((a, b) => Math.abs(a.km - stalledMarker.km) - Math.abs(b.km - stalledMarker.km));
                        
                        markersToShow.forEach(m => {
                            const xM = getXPixel(m.km);
                            const distMeters = Math.round(Math.abs(m.km - stalledMarker.km) * 1000);
                            
                            // Draw horizontal dimension line at the bottom of the chart (shifting up by 15px for each)
                            const dimY = bottomY - 15 - (dimIndex * 15);
                            
                            ctxDraw.strokeStyle = m.color || '#64748b'; // use custom color if available
                            ctxDraw.lineWidth = 1;
                            
                            // Draw horizontal line
                            ctxDraw.beginPath();
                            ctxDraw.moveTo(xM, dimY);
                            ctxDraw.lineTo(xStalled, dimY);
                            ctxDraw.stroke();
                            
                            // Draw small vertical ticks at the ends
                            ctxDraw.beginPath();
                            ctxDraw.moveTo(xM, dimY - 4);
                            ctxDraw.lineTo(xM, dimY + 4);
                            ctxDraw.moveTo(xStalled, dimY - 4);
                            ctxDraw.lineTo(xStalled, dimY + 4);
                            ctxDraw.stroke();
                            
                            // Draw distance text in the middle
                            ctxDraw.font = disableAnimation ? 'bold 13px Arial' : 'bold 11px Arial';
                            ctxDraw.fillStyle = m.color || '#475569';
                            ctxDraw.textAlign = 'center';
                            ctxDraw.textBaseline = 'middle';
                            
                            const text = `${distMeters.toLocaleString()} m`;
                            const textW = ctxDraw.measureText(text).width;
                            
                            // Draw white background for text to make it readable
                            ctxDraw.fillStyle = '#ffffff';
                            ctxDraw.fillRect((xM + xStalled) / 2 - textW / 2 - 4, dimY - 6, textW + 8, 12);
                            
                            ctxDraw.fillStyle = m.color || '#475569';
                            ctxDraw.fillText(text, (xM + xStalled) / 2, dimY);
                            
                            dimIndex++;
                        });
                    }

                    // 5. Draw Vertical Gradient labels along the curve
                    ctxDraw.save();
                    let lastLabelX = -999;
                    for (let i = 1; i < activeProfile.length; i++) {
                        const p1 = activeProfile[i - 1];
                        const p2 = activeProfile[i];
                        
                        const x1 = getXPixel(p1.km);
                        const x2 = getXPixel(p2.km);
                        const y1 = yAxis.getPixelForValue(p1.elevation);
                        const y2 = yAxis.getPixelForValue(p2.elevation);
                        
                        const midX = (x1 + x2) / 2;
                        const midY = (y1 + y2) / 2;
                        
                        // Draw vertical boundaries & labels at the top of the chart
                        if (Math.abs(midX - lastLabelX) > 55) {
                            const midKM = (p1.km + p2.km) / 2;
                            const labelText = getGradientAtKM(midKM);
                            
                            if (labelText && labelText !== "Start" && labelText !== "Marker Start" && labelText !== "Marker End" && labelText !== "Bound Start" && labelText !== "Bound End") {
                                // Draw white rect background for gradient label to overlay gridlines cleanly
                                ctxDraw.font = disableAnimation ? "bold 13px Arial" : "bold 11px Arial";
                                const textW = ctxDraw.measureText(labelText).width;
                                ctxDraw.fillStyle = "#ffffff";
                                ctxDraw.fillRect(midX - textW/2 - 3, topY + 4, textW + 6, 12);
                                
                                // Draw text label horizontally at the top of the chart
                                ctxDraw.fillStyle = "#334155";
                                ctxDraw.textAlign = "center";
                                ctxDraw.textBaseline = "middle";
                                ctxDraw.fillText(labelText, midX, topY + 10);
                                
                                lastLabelX = midX;
                            }
                        }
                    }
                    ctxDraw.restore();

                    // Faint vertical dashed boundary lines for each physical gradient segment
                    ctxDraw.save();
                    ctxDraw.strokeStyle = 'rgba(148, 163, 184, 0.4)'; // light grey
                    ctxDraw.lineWidth = 1;
                    ctxDraw.setLineDash([3, 3]);
                    const originalProfile = currentChartData.elevation_profile;
                    for (let i = 1; i < originalProfile.length - 1; i++) {
                        const km = originalProfile[i].km;
                        if (km > profileMinKM && km < profileMaxKM) {
                            const xBoundary = getXPixel(km);
                            const yCurve = yAxis.getPixelForValue(getInterpolatedElevation(km, originalProfile));
                            ctxDraw.beginPath();
                            ctxDraw.moveTo(xBoundary, topY);
                            ctxDraw.lineTo(xBoundary, yCurve);
                            ctxDraw.stroke();
                        }
                    }
                    ctxDraw.restore();

                    // 6. Draw Direction text at the bottom center and help text at the bottom right
                    ctxDraw.save();
                    let directionText = "";
                    if (currentChartData && currentChartData.section) {
                        if (currentChartData.section === "RPH - DUMK") {
                            const selectPred = document.getElementById("selectPredefinedSignals");
                            if (selectPred && selectPred.value === "dn") {
                                directionText = "DUMK ➔ RPH";
                            } else {
                                directionText = "RPH ➔ DUMK";
                            }
                        } else {
                            directionText = currentChartData.section.replace(/\s*-\s*/, " ➔ ");
                        }
                    }
                    
                    if (directionText) {
                        ctxDraw.font = disableAnimation ? 'bold 16px Arial' : 'bold 14px Arial';
                        ctxDraw.fillStyle = '#1e3a8a'; // dark blue
                        ctxDraw.textAlign = 'center';
                        ctxDraw.textBaseline = 'top';
                        ctxDraw.fillText(directionText, xAxis.left + xAxis.width / 2, bottomY + 80);
                    }
                    
                    // Help text
                    ctxDraw.font = disableAnimation ? 'italic 12px Arial' : 'italic 10.5px Arial';
                    ctxDraw.fillStyle = '#64748b'; // slate grey
                    ctxDraw.textAlign = 'right';
                    ctxDraw.textBaseline = 'top';
                    ctxDraw.fillText('* All location markers and distances are in KM', xAxis.right, bottomY + 82);
                    ctxDraw.restore();

                    // 7. Draw Custom Text Annotations
                    if (chartTextAnnotations && chartTextAnnotations.length > 0) {
                        ctxDraw.save();
                        chartTextAnnotations.forEach(ann => {
                            if (ann.km >= profileMinKM && ann.km <= profileMaxKM) {
                                // Calculate pixel coordinates if not set (or recalculate on chart updates)
                                const x = getXPixel(ann.km);
                                const y = yAxis.getPixelForValue(ann.elevation);

                                // If this annotation is not currently being dragged, update its pixel positions
                                if (draggingAnnotation !== ann) {
                                    ann.pixelX = x;
                                    ann.pixelY = y;
                                }

                                ctxDraw.font = `bold ${ann.fontSize}px Arial`;
                                ctxDraw.fillStyle = ann.color || "#000000";
                                ctxDraw.textAlign = 'left';
                                ctxDraw.textBaseline = 'bottom';
                                
                                // Draw a light container bubble around the text to keep it readable
                                const textW = ctxDraw.measureText(ann.text).width;
                                const textH = ann.fontSize;
                                
                                ctxDraw.fillStyle = 'rgba(255, 255, 255, 0.85)';
                                ctxDraw.strokeStyle = 'rgba(0, 0, 0, 0.15)';
                                ctxDraw.lineWidth = 1;
                                // Bubble rect
                                ctxDraw.beginPath();
                                ctxDraw.rect(ann.pixelX - 4, ann.pixelY - textH - 3, textW + 8, textH + 6);
                                ctxDraw.fill();
                                ctxDraw.stroke();

                                // Draw text inside
                                ctxDraw.fillStyle = ann.color || "#000000";
                                ctxDraw.fillText(ann.text, ann.pixelX, ann.pixelY);
                            }
                        });
                        ctxDraw.restore();
                    }
                }
            }]
        });
    } else {
        // Distribution Chart (standard full width)
        container.style.width = "100%";
        
        const dist = currentChartData.distribution;
        const total = dist.RISE + dist.FALL + dist.LEVEL;
        
        chartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['RISE', 'FALL', 'LEVEL'],
                datasets: [{
                    data: [dist.RISE, dist.FALL, dist.LEVEL],
                    backgroundColor: ['#ef4444', '#ea580c', '#10b981'],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const val = context.raw;
                                const pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
                                return ` Length: ${val}m (${pct}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
}

/* ================= TEXT ANNOTATIONS ================= */
function addTextAnnotation() {
    if (!currentChartData || !currentChartData.elevation_profile || currentChartData.elevation_profile.length === 0) {
        alert("Please load a section first.");
        return;
    }
    
    const profile = currentChartData.elevation_profile;
    const minKM = profile[0].km;
    const maxKM = profile[profile.length - 1].km;
    
    const text = document.getElementById("annotationText").value.trim();
    const kmVal = parseFloat(document.getElementById("annotationKM").value);
    const fontSize = parseInt(document.getElementById("annotationFontSize").value) || 11;
    const color = document.getElementById("annotationColor").value || "#000000";
    
    if (!text) {
        alert("Please enter the text to display.");
        return;
    }
    if (isNaN(kmVal)) {
        alert("Please enter a valid KM position.");
        return;
    }
    if (kmVal < minKM || kmVal > maxKM) {
        alert(`KM is out of bounds. Valid: ${minKM.toFixed(3)} to ${maxKM.toFixed(3)}.`);
        return;
    }
    
    const elevation = getInterpolatedElevation(kmVal, profile);
    
    chartTextAnnotations.push({
        id: Date.now() + Math.random(),
        text: text,
        km: kmVal,
        elevation: elevation + 0.3, // slightly above the curve
        fontSize: fontSize,
        color: color,
        pixelX: undefined,
        pixelY: undefined
    });
    
    // Reset inputs
    document.getElementById("annotationText").value = "";
    document.getElementById("annotationKM").value = "";
    
    updateAnnotationsListUI();
    renderChart();
}

function removeTextAnnotation(id) {
    chartTextAnnotations = chartTextAnnotations.filter(a => a.id !== id);
    updateAnnotationsListUI();
    renderChart();
}
window.removeTextAnnotation = removeTextAnnotation;

function updateAnnotationsListUI() {
    const container = document.getElementById("annotationsList");
    if (!container) return;
    
    if (chartTextAnnotations.length === 0) {
        container.style.display = "none";
        container.innerHTML = "";
        return;
    }
    
    container.style.display = "flex";
    container.innerHTML = "";
    
    chartTextAnnotations.forEach(ann => {
        const div = document.createElement("div");
        div.className = "d-flex justify-content-between align-items-center p-1 border-bottom small";
        div.innerHTML = `
            <div class="d-flex align-items-center text-truncate" style="max-width: 85%;">
                <span class="badge bg-info text-white me-1">${ann.fontSize}px</span>
                <strong style="color:${ann.color}">"${ann.text}"</strong>
                <span class="text-muted ms-1">@ KM ${ann.km.toFixed(3)}</span>
            </div>
            <button type="button" class="btn btn-link text-danger p-0 m-0 text-decoration-none fw-bold" onclick="removeTextAnnotation(${ann.id})">
                <i class="bi bi-trash-fill"></i>
            </button>
        `;
        container.appendChild(div);
    });
}

function plotStallingEvent() {
    if (!currentChartData || !currentChartData.elevation_profile || currentChartData.elevation_profile.length === 0) {
        alert("Please load a section first.");
        return;
    }
    
    const profile = currentChartData.elevation_profile;
    const minKM = profile[0].km;
    const maxKM = profile[profile.length - 1].km;
    
    const fromKMInput = document.getElementById("stallFromKM").value;
    const toKMInput = document.getElementById("stallToKM").value;
    const labelInput = document.getElementById("stallLabelText").value;
    const textKMInput = document.getElementById("stallTextKM").value;
    const textElevInput = document.getElementById("stallTextElev").value;
    
    const fromKM = parseFloat(fromKMInput);
    const toKM = parseFloat(toKMInput);
    
    if (isNaN(fromKM) || isNaN(toKM)) {
        alert("Please enter both From KM and To KM range values.");
        return;
    }
    
    if (fromKM > toKM) {
        alert("From KM cannot be greater than To KM.");
        return;
    }
    
    if (fromKM < minKM || toKM > maxKM) {
        alert(`Entered range is out of bounds. Valid section range is KM ${minKM.toFixed(3)} to KM ${maxKM.toFixed(3)}.`);
        return;
    }
    
    activeStallingFromKM = fromKM;
    activeStallingToKM = toKM;
    
    // Optional adjustable text coordinates
    activeLabelText = labelInput.trim();
    if (activeLabelText) {
        const tKM = parseFloat(textKMInput);
        const tElev = parseFloat(textElevInput);
        if (!isNaN(tKM) && !isNaN(tElev)) {
            if (tKM < minKM || tKM > maxKM) {
                alert(`Text position KM coordinate is out of bounds. Range is KM ${minKM.toFixed(3)} to KM ${maxKM.toFixed(3)}.`);
                return;
            }
            activeTextKM = tKM;
            activeTextElev = tElev;
        } else {
            activeTextKM = (fromKM + toKM) / 2;
            activeTextElev = getInterpolatedElevation(activeTextKM, profile);
        }
    } else {
        activeTextKM = null;
        activeTextElev = null;
    }
    
    document.getElementById("btnClearStalling").style.display = "inline-block";
    toggleChartView('profile');
    renderChart();
}

function clearStallingEvent() {
    activeStallingFromKM = null;
    activeStallingToKM = null;
    activeLabelText = "";
    activeTextKM = null;
    activeTextElev = null;
    
    customMarkers = [];
    
    const fKM = document.getElementById("stallFromKM");
    const tKM = document.getElementById("stallToKM");
    const lbl = document.getElementById("stallLabelText");
    const tKMPos = document.getElementById("stallTextKM");
    const tElevPos = document.getElementById("stallTextElev");
    
    const mKM = document.getElementById("markerKM");
    const mLbl = document.getElementById("markerLabel");
    
    const clearBtn = document.getElementById("btnClearStalling");
    
    if (fKM) fKM.value = "";
    if (tKM) tKM.value = "";
    if (lbl) lbl.value = "";
    if (tKMPos) tKMPos.value = "";
    if (tElevPos) tElevPos.value = "";
    if (mKM) { mKM.value = ""; mKM.placeholder = "KM Position (e.g. 11.200)"; }
    if (mLbl) mLbl.value = "";
    const mEndKM = document.getElementById("markerEndKM");
    if (mEndKM) mEndKM.value = "";
    const mEndKMC = document.getElementById("markerEndKMContainer");
    if (mEndKMC) mEndKMC.style.display = "none";
    const mSpeed = document.getElementById("markerSpeed");
    if (mSpeed) mSpeed.value = "";
    const mType = document.getElementById("markerType");
    if (mType) mType.value = "stalled";
    
    const selectPred = document.getElementById("selectPredefinedSignals");
    if (selectPred) selectPred.value = "";
    
    chartTextAnnotations = [];
    updateAnnotationsListUI();
    
    if (clearBtn) clearBtn.style.display = "none";
    
    if (currentChartData) {
        renderChart();
    }
}

function addCustomMarker() {
    if (!currentChartData || !currentChartData.elevation_profile || currentChartData.elevation_profile.length === 0) {
        alert("Please load a section first.");
        return;
    }
    
    const profile = currentChartData.elevation_profile;
    const minKM = profile[0].km;
    const maxKM = profile[profile.length - 1].km;
    
    const mType = document.getElementById("markerType").value;
    const mKMVal = document.getElementById("markerKM").value;
    const mLabelVal = document.getElementById("markerLabel").value;
    
    const km = parseFloat(mKMVal);
    const label = mLabelVal.trim();
    
    if (isNaN(km)) {
        alert("Please enter a valid KM position.");
        return;
    }
    if (!label) {
        alert("Please enter a name or label for the marker.");
        return;
    }
    if (km < minKM || km > maxKM) {
        alert(`Entered KM is out of bounds. Valid range: KM ${minKM.toFixed(3)} to KM ${maxKM.toFixed(3)}.`);
        return;
    }
    
    const colorSelect = document.getElementById("markerColor");
    const selectedColor = colorSelect ? colorSelect.value : "";
    
    const speedInput = document.getElementById("markerSpeed");
    const speedVal = speedInput && speedInput.value ? parseFloat(speedInput.value) : null;
    
    const endKMVal = document.getElementById("markerEndKM") ? document.getElementById("markerEndKM").value : "";
    const endKM = endKMVal ? parseFloat(endKMVal) : null;
    
    if (endKM !== null) {
        if (isNaN(endKM)) {
            alert("Please enter a valid End KM position.");
            return;
        }
        if (endKM < minKM || endKM > maxKM) {
            alert(`Entered End KM is out of bounds. Valid range: KM ${minKM.toFixed(3)} to KM ${maxKM.toFixed(3)}.`);
            return;
        }
        if (km > endKM) {
            alert("Start KM cannot be greater than End KM.");
            return;
        }
    }
    
    // Add marker
    const marker = {
        id: Date.now() + Math.random(),
        type: mType,
        km: km,
        endKm: endKM,
        label: label,
        color: selectedColor,
        calcDistance: undefined,
        speed: speedVal
    };
    
    customMarkers.push(marker);
    
    // Reset point marker input fields
    const markerKMEl = document.getElementById("markerKM");
    markerKMEl.value = "";
    markerKMEl.placeholder = "KM Position (e.g. 11.200)";
    document.getElementById("markerLabel").value = "";
    if (speedInput) speedInput.value = "";
    const endKMInput = document.getElementById("markerEndKM");
    if (endKMInput) endKMInput.value = "";
    const endKMContainer = document.getElementById("markerEndKMContainer");
    if (endKMContainer) endKMContainer.style.display = "none";
    if (colorSelect) colorSelect.value = "";
    document.getElementById("markerType").value = "stalled";
    
    // Update list UI
    updateMarkersListUI();
    
    // Show clear button since we have at least one marker plotted
    document.getElementById("btnClearStalling").style.display = "inline-block";
    
    // Re-render chart
    renderChart();
}

function removeCustomMarker(id) {
    customMarkers = customMarkers.filter(m => m.id !== id);
    updateMarkersListUI();
    
    // Hide clear button if no point markers are left AND no track span is active
    if (customMarkers.length === 0 && activeStallingFromKM === null) {
        document.getElementById("btnClearStalling").style.display = "none";
    }
    
    renderChart();
}

function toggleMarkerDistance(id, checked) {
    const marker = customMarkers.find(m => m.id === id);
    if (marker) {
        marker.calcDistance = checked;
        updateMarkersListUI();
        renderChart();
    }
}
window.toggleMarkerDistance = toggleMarkerDistance;

function updateMarkersListUI() {
    const container = document.getElementById("markersList");
    container.innerHTML = "";
    
    if (customMarkers.length === 0) {
        container.innerHTML = `<div class="text-muted small text-center py-4 my-auto">No point markers added yet. Add one in the middle panel.</div>`;
        const analysisBox = document.getElementById("stallingAnalysisBox");
        if (analysisBox) {
            analysisBox.style.display = "none";
            analysisBox.innerHTML = "";
        }
        return;
    }
    
    // Find stalled point to calculate distances
    const stalledMarker = customMarkers.find(m => m.type === 'stalled');
    
    // Find closest signal to the left & right of stalled point
    let leftSignal = null;
    let rightSignal = null;
    if (stalledMarker) {
        const leftSignals = customMarkers.filter(m => m.type === 'signal' && m.km < stalledMarker.km);
        if (leftSignals.length > 0) {
            leftSignal = leftSignals.reduce((prev, curr) => (curr.km > prev.km) ? curr : prev);
        }
        
        const rightSignals = customMarkers.filter(m => m.type === 'signal' && m.km > stalledMarker.km);
        if (rightSignals.length > 0) {
            rightSignal = rightSignals.reduce((prev, curr) => (curr.km < prev.km) ? curr : prev);
        }
    }
    
    // Ensure all markers have a calcDistance value set
    customMarkers.forEach(m => {
        if (m.type === 'stalled') {
            m.calcDistance = false;
            return;
        }
        if (m.calcDistance === undefined) {
            // Default to true for closest adjacent signals
            m.calcDistance = !!(stalledMarker && (m.id === leftSignal?.id || m.id === rightSignal?.id));
        }
    });
    
    const showDistances = document.getElementById("chkShowDistances") ? document.getElementById("chkShowDistances").checked : true;
    const searchInput = document.getElementById("searchMarkersInput");
    const query = searchInput ? searchInput.value.toLowerCase().trim() : "";
    
    // Filter markers based on search query
    const filteredMarkers = customMarkers.filter(m => {
        if (!query) return true;
        
        let typeText = m.type;
        if (m.type === 'stalled') typeText = "stalled";
        else if (m.type === 'signal') typeText = "signal";
        else if (m.type === 'station') typeText = "station";
        else if (m.type === 'neutral_section') typeText = "neutral section";
        else if (m.type === 'lc_gate') typeText = "l/c gate lc gate";
        else if (m.type === 'speed') typeText = "speed limit restriction";
        
        const labelText = (m.label || "").toLowerCase();
        const kmText = m.km.toFixed(3);
        const endKmText = m.endKm ? m.endKm.toFixed(3) : "";
        const speedText = m.speed ? m.speed.toString() : "";
        
        return typeText.includes(query) || 
               labelText.includes(query) || 
               kmText.includes(query) || 
               endKmText.includes(query) || 
               speedText.includes(query);
    });

    if (filteredMarkers.length === 0 && customMarkers.length > 0) {
        container.innerHTML = `<div class="text-muted small text-center py-4 my-auto">No markers match "${query}".</div>`;
        return;
    }

    filteredMarkers.forEach(m => {
        let badgeBg = "bg-secondary";
        let typeText = m.type;
        if (m.type === 'stalled') { badgeBg = "bg-danger"; typeText = "Stalled"; }
        else if (m.type === 'signal') { badgeBg = "bg-warning text-dark"; typeText = "Signal"; }
        else if (m.type === 'station') { badgeBg = "bg-primary"; typeText = "Station"; }
        else if (m.type === 'neutral_section') { badgeBg = "bg-indigo text-white"; typeText = "Neutral Sec"; }
        else if (m.type === 'lc_gate') { badgeBg = "bg-info text-dark"; typeText = "L/C Gate"; }
        else if (m.type === 'speed') { badgeBg = "bg-success"; typeText = "Speed Limit"; }
        
        const badgeStyle = m.type === 'neutral_section' ? 'style="background-color: #7c3aed !important;"' : '';
        
        // Custom badge color if user selected a custom color
        let itemBadgeStyle = badgeStyle;
        if (m.color) {
            itemBadgeStyle = `style="background-color: ${m.color} !important; color: #ffffff !important;"`;
        }
        
        // Calculate distance to stalled point ONLY if global distances are enabled and calcDistance is checked
        let distSuffix = "";
        if (showDistances && stalledMarker && m.type !== 'stalled' && m.calcDistance) {
            const distM = Math.round(Math.abs(m.km - stalledMarker.km) * 1000);
            distSuffix = ` <span class="text-danger small fw-bold">(${distM.toLocaleString()}m to Stalled)</span>`;
        }
        
        const speedText = (m.speed !== undefined && m.speed !== null && m.speed !== '') ? ` <span class="badge bg-success-subtle text-success border border-success-subtle small">${m.speed} km/h</span>` : '';
        
        // Distance checkbox shown only if stalled point exists
        const showCheckbox = !!(stalledMarker && m.type !== 'stalled');
        const checkboxHTML = showCheckbox ? `
            <input class="form-check-input me-1" type="checkbox" id="chkDist_${m.id}" ${m.calcDistance ? 'checked' : ''} onchange="toggleMarkerDistance(${m.id}, this.checked)" title="Toggle distance calculation to Stalled point">
        ` : '';
        
        let kmText = `KM ${m.km.toFixed(3)}`;
        if (m.endKm !== undefined && m.endKm !== null) {
            kmText = `KM ${m.km.toFixed(3)} - ${m.endKm.toFixed(3)}`;
        }
        
        const div = document.createElement("div");
        div.className = "d-flex justify-content-between align-items-center p-1 border-bottom small";
        div.innerHTML = `
            <div class="d-flex align-items-center text-truncate" style="max-width: 85%;">
                ${checkboxHTML}
                <span class="badge ${badgeBg} me-1" ${itemBadgeStyle}>${typeText}</span>
                <strong class="text-dark">${kmText}</strong>: ${m.label}${speedText}${distSuffix}
            </div>
            <button type="button" class="btn btn-link text-danger p-0 m-0 text-decoration-none fw-bold" onclick="removeCustomMarker(${m.id})">
                <i class="bi bi-trash-fill"></i>
            </button>
        `;
        container.appendChild(div);
    });
    
    // Stalling Speed Reduction Analysis box
    const analysisBox = document.getElementById("stallingAnalysisBox");
    if (analysisBox) {
        let speedMarker = null;
        if (stalledMarker) {
            const markersWithSpeed = customMarkers.filter(m => m.type !== 'stalled' && m.speed !== undefined && m.speed !== null && m.speed !== '' && m.speed > 0);
            if (markersWithSpeed.length > 0) {
                // Find the closest speed marker to the stalled point
                speedMarker = markersWithSpeed.reduce((prev, curr) => 
                    Math.abs(curr.km - stalledMarker.km) < Math.abs(prev.km - stalledMarker.km) ? curr : prev
                );
            }
        }
        
        if (stalledMarker && speedMarker) {
            const distM = Math.round(Math.abs(stalledMarker.km - speedMarker.km) * 1000);
            const u = speedMarker.speed * (5/18); // m/s
            const timeSec = Math.round(2 * distM / u);
            const decel = (u * u) / (2 * distM); // m/s^2
            
            analysisBox.style.display = "block";
            analysisBox.innerHTML = `
                <div class="card border-warning bg-warning-subtle text-dark-emphasis p-2 shadow-sm small">
                    <span class="d-block fw-bold text-danger mb-1" style="font-size: 11.5px;">
                        <i class="bi bi-speedometer2 me-1"></i>Stalling Speed Reduction Analysis
                    </span>
                    <div style="font-size: 11px; line-height: 1.4;">
                        <strong>Deceleration:</strong> Speed dropped from <strong>${speedMarker.speed} km/h</strong> (at KM ${speedMarker.km.toFixed(3)}) to <strong>0 km/h</strong> (at KM ${stalledMarker.km.toFixed(3)}).<br>
                        <strong>Travel distance:</strong> ${distM} meters.<br>
                        <strong>Estimated deceleration rate:</strong> ${decel.toFixed(3)} m/s².<br>
                        <strong>Estimated time taken:</strong> ${timeSec} seconds (${(timeSec/60).toFixed(1)} mins).
                    </div>
                </div>
            `;
        } else {
            analysisBox.style.display = "none";
            analysisBox.innerHTML = "";
        }
    }
}

// Attach functions globally for HTML inline access
window.removeCustomMarker = removeCustomMarker;

function getInterpolatedElevation(enteredKM, profile) {
    if (!profile || profile.length === 0) return 0;
    
    // Filter out any markers or text points so we only interpolate using raw database points
    const cleanPoints = profile.filter(p => p.direction === "RISE" || p.direction === "FALL" || p.direction === "LEVEL" || p.grade === "Start");
    
    if (cleanPoints.length === 0) return 0;
    
    // Sort cleanPoints by KM
    cleanPoints.sort((a, b) => a.km - b.km);
    
    if (enteredKM <= cleanPoints[0].km) return cleanPoints[0].elevation;
    if (enteredKM >= cleanPoints[cleanPoints.length - 1].km) return cleanPoints[cleanPoints.length - 1].elevation;
    
    for (let i = 0; i < cleanPoints.length - 1; i++) {
        const p1 = cleanPoints[i];
        const p2 = cleanPoints[i + 1];
        if (enteredKM >= p1.km && enteredKM <= p2.km) {
            const fraction = (enteredKM - p1.km) / (p2.km - p1.km);
            return p1.elevation + fraction * (p2.elevation - p1.elevation);
        }
    }
    return 0;
}

function getGradientAtKM(km) {
    if (!currentChartData || !currentChartData.elevation_profile) return "";
    const profile = currentChartData.elevation_profile;
    if (profile.length === 0) return "";
    
    for (let i = 1; i < profile.length; i++) {
        if (km <= profile[i].km + 0.0001) {
            let label = profile[i].grade;
            if (label.startsWith("1 in ")) {
                label = label.replace("1 in ", "1/");
            }
            if (profile[i].direction === "RISE") {
                label += " ↑";
            } else if (profile[i].direction === "FALL") {
                label += " ↓";
            }
            return label;
        }
    }
    const last = profile[profile.length - 1];
    let label = last.grade;
    if (label.startsWith("1 in ")) {
        label = label.replace("1 in ", "1/");
    }
    if (last.direction === "RISE") {
        label += " ↑";
    } else if (last.direction === "FALL") {
        label += " ↓";
    }
    return label;
}

/* ================= SAVE CHART OPTIONS MODAL ================= */
function showSaveChartModal() {
    if (!currentChartData) {
        alert("Please load a section first.");
        return;
    }
    
    // Set default bounds in the modal range inputs
    const profile = currentChartData.elevation_profile;
    const minKM = profile[0].km;
    const maxKM = profile[profile.length - 1].km;
    
    if (activeStallingFromKM !== null && activeStallingToKM !== null) {
        document.getElementById("saveFromKM").value = activeStallingFromKM.toFixed(3);
        document.getElementById("saveToKM").value = activeStallingToKM.toFixed(3);
        document.getElementById("saveScope").value = "custom";
        document.getElementById("saveCustomRangeFields").style.display = "block";
    } else {
        document.getElementById("saveFromKM").value = minKM.toFixed(3);
        document.getElementById("saveToKM").value = maxKM.toFixed(3);
        document.getElementById("saveScope").value = "total";
        document.getElementById("saveCustomRangeFields").style.display = "none";
    }
    document.getElementById("saveRangeHelp").innerText = `Section bounds: KM ${minKM.toFixed(3)} to KM ${maxKM.toFixed(3)}`;
    
    const modal = document.getElementById("saveChartModal");
    modal.style.display = "block";
    modal.classList.add("show");
    document.body.classList.add("modal-open");
    
    const backdrop = document.createElement("div");
    backdrop.className = "modal-backdrop fade show";
    backdrop.id = "saveChartModalBackdrop";
    document.body.appendChild(backdrop);
}

function hideSaveChartModal() {
    const modal = document.getElementById("saveChartModal");
    modal.style.display = "none";
    modal.classList.remove("show");
    document.body.classList.remove("modal-open");
    
    const backdrop = document.getElementById("saveChartModalBackdrop");
    if (backdrop) backdrop.remove();
}

function executeChartDownload() {
    const scope = document.getElementById("saveScope").value;
    if (scope === "total") {
        downloadChartAsImage();
        hideSaveChartModal();
    } else {
        const fromKMInput = document.getElementById("saveFromKM").value;
        const toKMInput = document.getElementById("saveToKM").value;
        const fromKM = parseFloat(fromKMInput);
        const toKM = parseFloat(toKMInput);
        
        if (isNaN(fromKM) || isNaN(toKM)) {
            alert("Please enter valid KM values for custom range.");
            return;
        }
        
        if (fromKM >= toKM) {
            alert("From KM must be less than To KM.");
            return;
        }
        
        const profile = currentChartData.elevation_profile;
        const minKM = profile[0].km;
        const maxKM = profile[profile.length - 1].km;
        
        if (fromKM < minKM || toKM > maxKM) {
            alert(`Selected range is outside this section bounds (KM ${minKM.toFixed(3)} - KM ${maxKM.toFixed(3)}).`);
            return;
        }
        
        downloadChartWithRange(fromKM, toKM);
        hideSaveChartModal();
    }
}

function downloadChartAsImage() {
    if (!chartInstance) return;
    const link = document.createElement("a");
    link.download = `Gradient_Chart_${currentChartData.section || 'Report'}.png`;
    link.href = chartInstance.toBase64Image();
    link.click();
}

function downloadChartWithRange(fromKM, toKM) {
    const originalProfile = JSON.parse(JSON.stringify(currentChartData.elevation_profile));
    
    // Filter coordinates to display only the requested subrange
    let tempProfile = originalProfile.filter(p => p.km >= fromKM && p.km <= toKM);
    if (tempProfile.length === 0) {
        alert("No data segments exist inside this range.");
        return;
    }
    
    // Ensure boundary points exist exactly at range limit cuts for a smooth visual path
    if (!tempProfile.some(p => Math.abs(p.km - fromKM) < 0.0001)) {
        tempProfile.unshift({
            km: fromKM,
            elevation: getInterpolatedElevation(fromKM, originalProfile),
            grade: "Bound Start",
            direction: "MARKER"
        });
    }
    if (!tempProfile.some(p => Math.abs(p.km - toKM) < 0.0001)) {
        tempProfile.push({
            km: toKM,
            elevation: getInterpolatedElevation(toKM, originalProfile),
            grade: "Bound End",
            direction: "MARKER"
        });
    }
    
    // Temporarily replace section coordinates with the filtered sub-range
    const originalData = currentChartData;
    currentChartData = {
        section: originalData.section,
        line: originalData.line,
        elevation_profile: tempProfile,
        distribution: originalData.distribution
    };
    
    // Capture the existing Y axis scale to preserve aspect ratio / slopes
    if (chartInstance && chartInstance.scales && chartInstance.scales.y) {
        window._tempYMin = chartInstance.scales.y.min;
        window._tempYMax = chartInstance.scales.y.max;
    }
    
    // Re-render chart synchronously with animation disabled
    renderChart(true);
    
    // Download image
    const link = document.createElement("a");
    link.download = `Gradient_Chart_${originalData.section}_KM_${fromKM.toFixed(3)}_to_${toKM.toFixed(3)}.png`;
    link.href = chartInstance.toBase64Image();
    link.click();
    
    // Restore full profile view
    currentChartData = originalData;
    delete window._tempYMin;
    delete window._tempYMax;
    renderChart();
}

/* ================= EXCEL EXPORTS ================= */
function downloadTableAsExcel() {
    const section = document.getElementById("filterSection").value;
    const line = document.getElementById("filterLine").value;
    const direction = document.getElementById("filterDirection").value;
    const search = document.getElementById("textSearch").value;
    
    let url = `/api/gradient/search?page=1&limit=10000`; // High limit to fetch all matching rows
    if (section) url += `&section=${encodeURIComponent(section)}`;
    if (line) url += `&line=${encodeURIComponent(line)}`;
    if (direction) url += `&direction=${encodeURIComponent(direction)}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    
    fetch(url)
        .then(res => res.json())
        .then(data => {
            if (data.records.length === 0) {
                alert("No records to export.");
                return;
            }
            
            const rows = [
                ["DIV/RLY", "Section", "Line", "KM From", "MET From", "KM To", "MET To", "Gauge", "Length (m)", "Direction", "Grade (1 in _)"]
            ];
            
            data.records.forEach(r => {
                rows.push([
                    r.div_rly, r.section, r.line, r.km_from, r.met_from, r.km_to, r.met_to, r.gauge, r.length_m, r.direction, r.grade
                ]);
            });
            
            const ws = XLSX.utils.aoa_to_sheet(rows);
            const wb = XLSX.utils.book_new();
            XLSX.utils.book_append_sheet(wb, ws, "Gradients");
            
            // Generate filename based on filters
            let filename = "Gradient_Register";
            if (section) filename += `_${section}`;
            filename += ".xlsx";
            
            XLSX.writeFile(wb, filename);
        })
        .catch(err => {
            alert("Failed to export Excel.");
        });
}

/* ================= PDF EXPORTS ================= */
function downloadTableAsPDF() {
    const element = document.getElementById("pdfExportArea");
    const section = document.getElementById("filterSection").value || "All";
    
    const opt = {
        margin:       10,
        filename:     `Gradient_Register_Report_${section}.pdf`,
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { scale: 2, useCORS: true },
        jsPDF:        { unit: 'mm', format: 'a4', orientation: 'landscape' }
    };
    
    // Execute PDF creation
    html2pdf().set(opt).from(element).save();
}

/* ================= EXCEL UPLOAD ================= */
function handleExcelUpload(e) {
    e.preventDefault();
    const fileInput = document.getElementById("gradientExcelFile");
    if (fileInput.files.length === 0) return;
    
    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    
    const statusDiv = document.getElementById("uploadStatus");
    statusDiv.style.display = "block";
    statusDiv.className = "alert alert-info py-2";
    statusDiv.innerHTML = '<div class="spinner-border spinner-border-sm text-primary me-2"></div>Uploading and parsing Excel sheet...';
    
    fetch("/api/gradient/upload", {
        method: "POST",
        body: formData
    })
    .then(res => {
        if (!res.ok) {
            return res.json().then(err => { throw new Error(err.detail || "Server error"); });
        }
        return res.json();
    })
    .then(data => {
        statusDiv.className = "alert alert-success py-2";
        statusDiv.innerText = data.message || "Upload successful!";
        
        // Reset form & reload filters + data
        document.getElementById("gradientUploadForm").reset();
        loadSections();
        currentPage = 1;
        fetchGradients();
        
        // Hide upload panel after 3 seconds
        setTimeout(() => {
            statusDiv.style.display = "none";
            document.getElementById("adminUploadCard").style.display = "none";
        }, 3000);
    })
    .catch(err => {
        statusDiv.className = "alert alert-danger py-2";
        statusDiv.innerText = err.message || "Failed to process spreadsheet.";
    });
}

/* ================= ADMIN INTERFACE SYNC ================= */
function syncAdminUI(isAdmin) {
    const adminElements = document.querySelectorAll(".admin-only");
    adminElements.forEach(el => {
        if (isAdmin) {
            el.style.setProperty("display", "block", "important");
        } else {
            el.style.setProperty("display", "none", "important");
        }
    });
}

/* ================= DEBOUNCE ================= */
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}
