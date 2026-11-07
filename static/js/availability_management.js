let availabilityRows = [];
let statusOptions = [];
let lastSummaryRows = [];
let activeSlotFilter = null;

const editableFields = [
    "crew_id",
    "name",
    "origdesig",
    "remarks",
    "sign_off",
    "available",
    "rest_hours",
    "mobile_no_reg"
];

const columns = [
    { field:"s_no", label:"S.No" },
    { field:"crew_id", label:"CREW ID" },
    { field:"name", label:"NAME" },
    { field:"origdesig", label:"ORIGDESIG" },
    { field:"status", label:"Status" },
    { field:"remarks", label:"Remarks" },
    { field:"sign_off", label:"SIGN OFF" },
    { field:"available", label:"AVAILABLE" },
    { field:"rest_hours", label:"REST HOURS" },
    { field:"mobile_no_reg", label:"MOBILE NOReg" }
];

const prefixTypes = [
    { symbol:"@", label:"Non Run" },
    { symbol:"*", label:"Under Rest" },
    { symbol:"%", label:"LR" },
    { symbol:"$", label:"Advance Nonrun" },
    { symbol:"#", label:"Coaching Link" }
];

const slotColors = [
    "#FCD5B4", // Peach
    "#EAF2DD", // Green
    "#F2DDDC", // Rose
    "#DBE5F1", // Blue
    "#DED9C3", // Beige
    "#F5EEF8", // Lavender
    "#E8F8F5", // Mint
    "#FEF9E7", // Light yellow
    "#FDF2E9", // Light orange
    "#EAECEE", // Light gray
    "#E8F6F3", // Light teal
    "#FADBD8"  // Light coral
];

function getSlotIndex(availableAt, activeStart) {
    if (!availableAt) return -1;
    if (availableAt < activeStart) {
        return 0; // "On Hand"
    }
    const diffMs = availableAt - activeStart;
    const diffHours = diffMs / (1000 * 60 * 60);
    return Math.floor(diffHours / 2) + 1; // slots start at 1
}

function resetFilterInputs(){
    const toEl = document.getElementById("slotToDate");
    const toTimeEl = document.getElementById("slotTo");

    if (toEl) toEl.value = toDateInput(new Date());
    if (toTimeEl) toTimeEl.value = "";
}

document.addEventListener("DOMContentLoaded", async () => {
    buildTimeOptions();
    await loadStatusOptions();
    await loadAvailability();
    resetFilterInputs();

    document.getElementById("btnUploadAvailability").addEventListener("click", uploadAvailability);
    document.getElementById("availabilitySearch").addEventListener("input", () => {
        renderTable();
        buildSummary();
    });
    document.getElementById("btnCopySummary").addEventListener("click", () => copyTableSummary("summaryBody", "Availability summary copied."));
    document.getElementById("btnCopyPrefixSummary").addEventListener("click", () => copyTableSummary("prefixSummaryBody", "Crew type summary copied."));
    document.getElementById("btnImageSummary").addEventListener("click", () => exportSummaryImage("summaryBody", "Availability_Summary.png"));
    document.getElementById("btnImagePrefixSummary").addEventListener("click", () => exportSummaryImage("prefixSummaryBody", "Crew_Type_Summary.png"));
    document.getElementById("btnExportPrint").addEventListener("click", exportPdf);
    document.getElementById("btnExportExcel").addEventListener("click", exportExcel);
    document.getElementById("btnExportPdf").addEventListener("click", exportPdf);
    document.getElementById("btnExportImage").addEventListener("click", exportImage);
    document.getElementById("btnExportImage").addEventListener("click", exportImage);
    
    // Database Truncate Button
    const btnTruncateDB = document.getElementById("btnTruncateDB");
    if(btnTruncateDB) {
        btnTruncateDB.addEventListener("click", clearAvailability);
    }

    // Filter Buttons
    const btnApplyFilter = document.getElementById("btnApplyFilter");
    if(btnApplyFilter) {
        btnApplyFilter.addEventListener("click", () => {
            renderTable();
            buildSummary({ applyTableFilter: true });
        });
    }

    const btnClearFilter = document.getElementById("btnClearFilter");
    if(btnClearFilter) {
        btnClearFilter.addEventListener("click", () => {
            resetFilterInputs();
            activeSlotFilter = null;
            renderTable();
            buildSummary();
        });
    }
});

function buildTimeOptions(){
    const toSelect = document.getElementById("slotTo");
    
    [toSelect].forEach(select => {
        if (!select) return;
        select.innerHTML = "";
        select.add(new Option("-", ""));

        for(let hour = 0; hour <= 24; hour += 2){
            const value = String(hour).padStart(2, "0") + ":00";
            select.add(new Option(value, value));
        }
    });
}

function setDefaultSlotTarget(){
    const now = new Date();
    const activeStart = getActiveSlotStart(now);
    const target = new Date(activeStart);

    if(activeStart.getHours() < 18){
        target.setHours(20, 0, 0, 0);
    }
    else if(activeStart.getHours() < 20){
        target.setHours(20, 0, 0, 0);
    }
    else{
        target.setHours(activeStart.getHours(), 0, 0, 0);
    }

    document.getElementById("slotToDate").value = toDateInput(target);
    document.getElementById("slotTo").value = `${String(target.getHours()).padStart(2, "0")}:00`;
}

async function loadStatusOptions(){
    const response = await fetch("/api/availability/status-options");
    statusOptions = (await response.json()).map(option => (
        String(option).trim().toLowerCase() === "others" ? "Other" : option
    ));
    statusOptions = [...new Set(statusOptions)];
    if(!statusOptions.includes("-")) statusOptions.unshift("-");
    if(!statusOptions.some(option => option.toLowerCase() === "other")) statusOptions.push("Other");
}

async function loadAvailability(){
    const response = await fetch("/api/availability");
    availabilityRows = await response.json();
    activeSlotFilter = null;
    renderTable();
    buildSummary();
}

async function uploadAvailability(){
    const input = document.getElementById("availabilityFile");
    const file = input.files[0];

    if(!file){
        showToast("Please select Excel file.", "warning");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    const button = document.getElementById("btnUploadAvailability");
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

    try{
        const response = await fetch("/api/availability/upload", {
            method:"POST",
            body:formData
        });

        const data = await readJsonResponse(response);
        if(!response.ok){
            throw new Error(data.detail || "Upload failed.");
        }

        availabilityRows = data.rows;
        activeSlotFilter = null;
        resetFilterInputs();
        renderTable();
        buildSummary();
        showToast(`Imported ${data.inserted} rows successfully.`, "success");
    }
    catch(error){
        showToast(error.message, "danger");
    }
    finally{
        button.disabled = false;
        button.innerHTML = '<i class="bi bi-upload"></i>';
    }
}

function renderTable(){
    const tbody = document.getElementById("availabilityBody");
    const rows = getVisibleRows();

    tbody.innerHTML = "";

    const activeStart = getSlotStartPoint();
    const slotGroups = {};
    const availableRowsList = [];

    // Group available crew rows by slot index
    rows.forEach(row => {
        row.remarks_count = ""; // Reset
        if (!isUnavailable(row)) {
            availableRowsList.push(row);
            const availableAt = getAvailableDate(row);
            const slotIdx = getSlotIndex(availableAt, activeStart);
            if (slotIdx >= 0) {
                if (!slotGroups[slotIdx]) {
                    slotGroups[slotIdx] = [];
                }
                slotGroups[slotIdx].push(row);
            }
        }
    });

    // Assign dynamic count starting from 1 for each slot group
    for (const slotIdx in slotGroups) {
        const groupRows = slotGroups[slotIdx];
        groupRows.forEach((row, i) => {
            row.remarks_count = String(i + 1);
        });
    }

    // At the end of the entire list (the last available row), show the overall total
    if (availableRowsList.length > 0) {
        const lastRow = availableRowsList[availableRowsList.length - 1];
        const lastCount = lastRow.remarks_count;
        const overallTotal = availableRowsList.length;
        lastRow.remarks_count = `${lastCount} (Total: ${overallTotal})`;
    }

    rows.forEach((row, index) => {
        const tr = document.createElement("tr");
        if(isUnavailable(row)) {
            tr.classList.add("unavailable-row");
        } else {
            const availableAt = getAvailableDate(row);
            const slotIdx = getSlotIndex(availableAt, activeStart);
            if (slotIdx >= 0) {
                tr.style.backgroundColor = slotColors[slotIdx % slotColors.length];
            }
        }

        columns.forEach(col => {
            const td = document.createElement("td");

            if(col.field === "s_no"){
                td.textContent = index + 1;
            }
            else if(col.field === "status"){
                td.classList.add("status-cell");
                td.appendChild(buildStatusSelect(row));
            }
            else{
                td.textContent = getDisplayValue(row, col.field);

                if(editableFields.includes(col.field)){
                    td.contentEditable = true;
                    td.dataset.original = td.textContent;
                    td.classList.add("editable-cell");
                    if(col.field === "remarks") applyRemarksRules(row, td);
                    td.addEventListener("blur", () => saveCell(row, col.field, td));
                    td.addEventListener("keydown", event => {
                        if(event.key === "Enter" && col.field !== "remarks"){
                            event.preventDefault();
                            td.blur();
                        }
                    });
                }
            }

            tr.appendChild(td);
        });

        const actionTd = document.createElement("td");
        const deleteButton = document.createElement("button");
        deleteButton.className = "btn btn-outline-danger btn-sm delete-row";
        deleteButton.title = "Delete row";
        deleteButton.innerHTML = '<i class="bi bi-trash"></i>';
        deleteButton.addEventListener("click", () => deleteRow(row.id));
        actionTd.appendChild(deleteButton);
        tr.appendChild(actionTd);

        tbody.appendChild(tr);
    });

    document.getElementById("availabilityCount").textContent = `${rows.length} rows`;
}

function buildStatusSelect(row){
    const select = document.createElement("select");
    select.className = "form-select form-select-sm";
    select.add(new Option("", ""));

    statusOptions.forEach(option => {
        select.add(new Option(option, option));
    });

    select.value = row.status || "";
    select.addEventListener("change", async () => {
        const value = select.value;
        select.disabled = true;
        try{
            let remarks = (value === "" || value === "-") ? "" : value;
            if (value === "OUT") {
                remarks = "C/F";
            }
            await updateRow(row.id, { status:value, remarks });
            row.status = value;
            row.remarks = remarks;

            renderTable();
            buildSummary();
            showToast("Status updated.", "success");
        }
        catch(error){
            showToast(error.message, "danger");
            renderTable();
        }
        finally{
            select.disabled = false;
        }
    });

    return select;
}

function applyRemarksRules(row, td){
    td.classList.add("remarks-cell");
    const status = normalizeStatus(row.status);
    const isAvail = (status === "" || status === "-");
    td.contentEditable = !isAvail;
    if(isAvail) {
        td.classList.add("disabled");
    } else {
        td.classList.remove("disabled");
    }
}

async function saveCell(row, field, cell){
    if(field === "remarks" && cell.contentEditable !== "true") return;

    const value = cell.textContent.trim();
    if(value === cell.dataset.original) return;

    try{
        await updateField(row.id, field, value);
        row[field] = value;
        cell.dataset.original = value;

        if(field === "available"){
            applyAvailableParts(row, value);
        }

        renderTable();
        buildSummary();
    }
    catch(error){
        showToast(error.message, "danger");
        cell.textContent = cell.dataset.original;
    }
}

async function updateField(id, field, value){
    return updateRow(id, { field, value });
}

async function updateRow(id, payload){
    const response = await fetch(`/api/availability/${id}`, {
        method:"PUT",
        headers:{ "Content-Type":"application/json" },
        body:JSON.stringify(payload)
    });

    const data = await readJsonResponse(response);
    if(!response.ok){
        throw new Error(data.detail || "Update failed.");
    }
}

async function deleteRow(id){
    const confirmed = await confirmAction("Delete this row?", "This will remove the selected crew record from the availability table.");
    if(!confirmed) return;

    const response = await fetch(`/api/availability/${id}`, {
        method:"DELETE"
    });

    if(!response.ok){
        const data = await readJsonResponse(response);
        showToast(data.detail || "Delete failed.", "danger");
        return;
    }

    availabilityRows = availabilityRows.filter(row => row.id !== id);
    renderTable();
    buildSummary();
    showToast("Row deleted.", "success");
}

async function clearAvailability(){
    const confirmed = await confirmAction(
        "Clear all crew availability?",
        "This will truncate the crew availability table and remove all imported rows."
    );
    if(!confirmed) return;

    const response = await fetch("/api/availability/clear", { method:"POST" });
    if(!response.ok){
        const data = await readJsonResponse(response);
        showToast(data.detail || "Clear failed.", "danger");
        return;
    }

    availabilityRows = [];
    activeSlotFilter = null;
    renderTable();
    buildSummary();
    showToast("Crew availability table cleared.", "success");
}

function buildSummary(options = {}){
    const activeStart = getSlotStartPoint();
    const selectedTarget = selectedTargetDateTime();
    const tbody = document.getElementById("summaryBody");
    const prefixBody = document.getElementById("prefixSummaryBody");
    const applyTableFilter = options.applyTableFilter === true;
    const search = document.getElementById("availabilitySearch").value.trim().toLowerCase();

    tbody.innerHTML = "";
    lastSummaryRows = [];

    if (!selectedTarget) {
        tbody.innerHTML = '<tr><td colspan="2" class="text-muted">Select filter to view slots</td></tr>';
        if(applyTableFilter){
            activeSlotFilter = null;
            renderTable();
        }
        buildPrefixSummary(prefixBody, null);
        return;
    }

    const end = new Date(selectedTarget);
    if(end <= activeStart){
        tbody.innerHTML = '<tr><td colspan="2" class="text-danger">Up to time must be after the From time.</td></tr>';
        if(applyTableFilter){
            activeSlotFilter = null;
            renderTable();
        }
        buildPrefixSummary(prefixBody, null);
        return;
    }

    if(applyTableFilter){
        activeSlotFilter = { end };
        renderTable();
    }

    const countableRows = getRowsInSummaryWindow(activeStart, end);
    const onHand = countableRows.filter(row => {
        const availableAt = getAvailableDate(row);
        return availableAt && availableAt < activeStart;
    }).length;

    addSummaryRow(tbody, "On Hand", onHand, slotColors[0]);
    lastSummaryRows.push(["On Hand", onHand]);

    let total = onHand;
    let slotStart = new Date(activeStart);
    let slotCount = 1;

    while(slotStart < end){
        const slotEnd = new Date(slotStart);
        slotEnd.setHours(slotEnd.getHours() + 2, 0, 0, 0);

        const count = availabilityRows.filter(row => {
            if(isUnavailable(row)) return false;
            const availableAt = getAvailableDate(row);
            if(!availableAt || availableAt < slotStart || availableAt >= slotEnd) return false;
            if(search){
                const matchesSearch = columns.some(col => String(getDisplayValue(row, col.field) || "").toLowerCase().includes(search));
                if(!matchesSearch) return false;
            }
            return true;
        }).length;

        total += count;
        const label = `${formatSlot(slotStart)} - ${formatSlot(slotEnd)}`;
        lastSummaryRows.push([label, count]);
        addSummaryRow(tbody, label, count, slotColors[slotCount % slotColors.length]);

        slotStart = slotEnd;
        slotCount++;
    }

    const totalRow = document.createElement("tr");
    totalRow.className = "summary-total";
    totalRow.innerHTML = `<td>Total</td><td>${total}</td>`;
    tbody.appendChild(totalRow);

    buildPrefixSummary(prefixBody, countableRows);
}

function addSummaryRow(tbody, label, count, bgColor){
    const tr = document.createElement("tr");
    if (bgColor) {
        tr.style.backgroundColor = bgColor;
    }
    tr.innerHTML = `<td>${label}</td><td>${count}</td>`;
    tbody.appendChild(tr);
}

function buildPrefixSummary(tbody, rows = null){
    tbody.innerHTML = "";
    let countableRows = rows;
    if(!countableRows){
        const search = document.getElementById("availabilitySearch").value.trim().toLowerCase();
        countableRows = availabilityRows.filter(row => {
            if(isUnavailable(row)) return false;
            if(search){
                const matchesSearch = columns.some(col => String(getDisplayValue(row, col.field) || "").toLowerCase().includes(search));
                if(!matchesSearch) return false;
            }
            return true;
        });
    }

    const knownSymbols = prefixTypes.map(t => t.symbol);
    const onHandCount = countableRows.filter(row => !knownSymbols.includes(getCrewPrefix(row))).length;
    
    const onHandTr = document.createElement("tr");
    onHandTr.innerHTML = `<td><span class="prefix-badge" style="background: #e8f5e9; color: #2e7d32;">✓</span> On Hand</td><td>${onHandCount}</td>`;
    tbody.appendChild(onHandTr);

    prefixTypes.forEach(type => {
        const count = countableRows.filter(row => getCrewPrefix(row) === type.symbol).length;
        const tr = document.createElement("tr");
        tr.innerHTML = `<td><span class="prefix-badge">${escapeHtml(type.symbol)}</span> ${escapeHtml(type.label)}</td><td>${count}</td>`;
        tbody.appendChild(tr);
    });
}

function getRowsInSummaryWindow(activeStart, end){
    const search = document.getElementById("availabilitySearch").value.trim().toLowerCase();
    return availabilityRows.filter(row => {
        if(isUnavailable(row)) return false;
        const availableAt = getAvailableDate(row);
        if (!availableAt || availableAt >= end) return false;
        if(search){
            const matchesSearch = columns.some(col => String(getDisplayValue(row, col.field) || "").toLowerCase().includes(search));
            if(!matchesSearch) return false;
        }
        return true;
    });
}

async function copyTableSummary(tbodyId, message){
    const table = document.getElementById(tbodyId).closest("table");
    const rows = [...table.querySelectorAll("tr")].map(row => (
        [...row.children].map(cell => cell.textContent.trim()).join("\t")
    ));
    await navigator.clipboard.writeText(rows.join("\n"));
    showToast(message, "success");
}

function exportSummaryImage(tbodyId, filename){
    const originalTable = document.getElementById(tbodyId).closest("table");
    const table = originalTable.cloneNode(true);
    table.setAttribute("dir", "ltr");
    table.style.direction = "ltr";
    table.style.width = "400px";
    
    // Apply styling to table headers (th) for export
    table.querySelectorAll("th").forEach(th => {
        th.style.backgroundColor = "#1f3f66";
        th.style.color = "#ffffff";
        th.style.fontWeight = "bold";
        th.style.textAlign = "left";
        th.style.padding = "6px 10px";
        th.style.border = "1px solid #9ca3af";
    });

    // Apply styling to cells (td) for export
    table.querySelectorAll("td").forEach(td => {
        td.style.padding = "6px 10px";
        td.style.border = "1px solid #9ca3af";
        td.style.textAlign = "left";
    });

    // Create an invisible container in the viewport area to prevent layout clipping
    const container = document.createElement("div");
    container.style.position = "fixed";
    container.style.top = "0";
    container.style.left = "0";
    container.style.width = "400px";
    container.style.height = "0";
    container.style.overflow = "hidden";
    container.style.zIndex = "-9999";

    container.appendChild(table);
    document.body.appendChild(container);

    html2canvas(table, {
        backgroundColor: "#ffffff",
        logging: false,
        scale: 2
    }).then(canvas => {
        document.body.removeChild(container);
        canvas.toBlob(blob => downloadBlob(blob, filename));
    }).catch(err => {
        console.error("html2canvas exportSummaryImage failed", err);
        if (container.parentNode) {
            document.body.removeChild(container);
        }
    });
}

function exportExcel(){
    const html = buildExportTableHtml();
    const blob = new Blob([html], { type:"application/vnd.ms-excel" });
    downloadBlob(blob, "Availability_Management.xls");
}

function exportPdf(){
    const win = window.open("", "_blank");
    win.document.write(`
        <html>
            <head>
                <title>Availability Management</title>
                <style>
                    table{border-collapse:collapse;width:100%;font-family:Arial;font-size:10px}
                    th,td{border:1px solid #777;padding:4px;text-align:left}
                    th{background:#1f3f66;color:#fff}
                </style>
            </head>
            <body>${buildExportTableHtml()}<script>window.print();<\/script></body>
        </html>
    `);
    win.document.close();
}

function exportImage(){
    const table = buildExportDomTable();
    table.setAttribute("dir", "ltr");
    table.style.direction = "ltr";
    table.style.width = "1200px";
    
    // Create an invisible container in the viewport area to prevent layout clipping
    const container = document.createElement("div");
    container.style.position = "fixed";
    container.style.top = "0";
    container.style.left = "0";
    container.style.width = "1200px";
    container.style.height = "0";
    container.style.overflow = "hidden";
    container.style.zIndex = "-9999";
    
    container.appendChild(table);
    document.body.appendChild(container);

    html2canvas(table, {
        backgroundColor: "#ffffff",
        logging: false,
        scale: 2
    }).then(canvas => {
        document.body.removeChild(container);
        canvas.toBlob(blob => downloadBlob(blob, "Availability_Management.png"));
    }).catch(err => {
        console.error("html2canvas exportImage failed", err);
        if (container.parentNode) {
            document.body.removeChild(container);
        }
    });
}

function buildExportTableHtml(){
    const exportColumns = columns.filter(col => col.field !== "status");
    const headers = exportColumns.map(col => `<th style="background-color: #1f3f66; color: #ffffff; font-weight: bold; text-align: left; padding: 6px 10px; border: 1px solid #9ca3af;">${col.label}</th>`).join("");
    const visibleRows = getVisibleRows();
    
    // Group available crew rows by slot index to count them starting from 1 for each slot
    const activeStart = getSlotStartPoint();
    const slotGroups = {};
    const availableRowsList = [];

    visibleRows.forEach(row => {
        row.remarks_count = ""; // Reset
        if (!isUnavailable(row)) {
            availableRowsList.push(row);
            const availableAt = getAvailableDate(row);
            const slotIdx = getSlotIndex(availableAt, activeStart);
            if (slotIdx >= 0) {
                if (!slotGroups[slotIdx]) {
                    slotGroups[slotIdx] = [];
                }
                slotGroups[slotIdx].push(row);
            }
        }
    });

    for (const slotIdx in slotGroups) {
        const groupRows = slotGroups[slotIdx];
        groupRows.forEach((row, i) => {
            row.remarks_count = String(i + 1);
        });
    }

    if (availableRowsList.length > 0) {
        const lastRow = availableRowsList[availableRowsList.length - 1];
        const lastCount = lastRow.remarks_count;
        const overallTotal = availableRowsList.length;
        lastRow.remarks_count = `${lastCount} (Total: ${overallTotal})`;
    }

    const body = visibleRows.map((row, index) => {
        let rowStyle = "";
        if (isUnavailable(row)) {
            rowStyle = 'style="background-color: #fde8e8;"'; // soft shade of red
        } else {
            const availableAt = getAvailableDate(row);
            const slotIdx = getSlotIndex(availableAt, activeStart);
            if (slotIdx >= 0) {
                rowStyle = `style="background-color: ${slotColors[slotIdx % slotColors.length]};"`;
            }
        }

        return `
        <tr ${rowStyle}>
            ${exportColumns.map(col => {
                const value = col.field === "s_no" ? index + 1 : getDisplayValue(row, col.field);
                return `<td style="padding: 6px 10px; border: 1px solid #9ca3af; text-align: left;">${escapeHtml(value)}</td>`;
            }).join("")}
        </tr>
        `;
    }).join("");

    return `<table dir="ltr" style="direction: ltr !important; text-align: left !important; border-collapse: collapse; width: 100%; border: 1px solid #9ca3af;"><thead><tr>${headers}</tr></thead><tbody>${body}</tbody></table>`;
}

function buildExportDomTable(){
    const div = document.createElement("div");
    div.innerHTML = buildExportTableHtml();
    return div.querySelector("table");
}

function getVisibleRows(){
    const search = document.getElementById("availabilitySearch").value.trim().toLowerCase();

    return availabilityRows.filter(row => {
        if(activeSlotFilter){
            const availableAt = getAvailableDate(row);
            if(!availableAt || availableAt >= activeSlotFilter.end){
                return false;
            }
        }

        if(!search) return true;
        return columns.some(col => String(getDisplayValue(row, col.field) || "").toLowerCase().includes(search));
    });
}

function getDisplayValue(row, field){
    if(field === "available"){
        return formatDateTime(getAvailableDate(row)) || row.available || "";
    }
    if(field === "remarks"){
        const status = normalizeStatus(row.status);
        if (status === "" || status === "-") {
            return row.remarks_count || "";
        }
        return row.remarks || "";
    }
    if(field === "rest_hours"){
        const val = String(row.rest_hours || "").trim();
        const match = val.match(/^(\d{1,2}):(\d{2}):\d{2}$/);
        if (match) {
            return `${match[1]}:${match[2]}`;
        }
        return val;
    }
    return row[field] || "";
}

function selectedTargetDateTime(){
    const dateValue = document.getElementById("slotToDate").value;
    const timeValue = document.getElementById("slotTo").value;
    if (!dateValue || !timeValue) return null;
    const [hour] = timeValue.split(":").map(Number);
    const date = new Date(`${dateValue}T00:00:00`);
    date.setHours(hour, 0, 0, 0);
    return date;
}

function getActiveSlotStart(date){
    const start = new Date(date);
    start.setMinutes(0, 0, 0);
    start.setHours(Math.floor(start.getHours() / 2) * 2);
    return start;
}

function getAvailableDate(row){
    if(row.available_iso) return new Date(row.available_iso);
    if(row.available_date && row.available_time) return new Date(`${row.available_date}T${row.available_time}`);
    const parsed = parseDisplayDateTime(row.available);
    if(parsed) return parsed;
    return null;
}

function applyAvailableParts(row, value){
    const parsed = parseDisplayDateTime(value);
    if(parsed){
        row.available = formatDateTime(parsed);
        row.available_iso = toLocalIsoMinute(parsed);
        row.available_date = toDateInput(parsed);
        row.available_time = formatTime(parsed);
        return;
    }

    const time = extractTime(value);
    if(time){
        const currentDate = row.available_date || toDateInput(new Date());
        const parsedTime = new Date(`${currentDate}T${time}`);
        row.available = formatDateTime(parsedTime);
        row.available_iso = toLocalIsoMinute(parsedTime);
        row.available_date = currentDate;
        row.available_time = time;
    }
}

function getCrewPrefix(row){
    const crewId = String(row.crew_id || "").trim();
    return crewId ? crewId[0] : "";
}

function isUnavailable(row){
    const status = normalizeStatus(row.status);
    return status !== "" && status !== "-";
}

function isFixedUnavailableStatus(status){
    const normalized = normalizeStatus(status);
    return normalized !== "" && normalized !== "-" && normalized !== "other";
}

function normalizeStatus(status){
    return String(status || "").trim().toLowerCase();
}

function extractTime(value){
    const match = String(value || "").match(/(\d{1,2}):(\d{2})/);
    return match ? `${match[1].padStart(2, "0")}:${match[2]}` : "";
}

function formatSlot(date){
    return formatTime(date);
}

function formatTime(date){
    return `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}

function formatDateTime(date){
    if(!date || Number.isNaN(date.getTime())) return "";
    return [
        String(date.getDate()).padStart(2, "0"),
        String(date.getMonth() + 1).padStart(2, "0"),
        String(date.getFullYear()).slice(-2)
    ].join("-") + ` ${formatTime(date)}`;
}

function parseDisplayDateTime(value){
    const text = String(value || "").trim();
    const match = text.match(/^(\d{1,2})[-/](\d{1,2})[-/](\d{2}|\d{4})\s+(\d{1,2}):(\d{2})$/);
    if(!match) return null;

    let year = Number(match[3]);
    if(year < 100) year += 2000;

    const date = new Date(year, Number(match[2]) - 1, Number(match[1]), Number(match[4]), Number(match[5]), 0, 0);
    return Number.isNaN(date.getTime()) ? null : date;
}

function toLocalIsoMinute(date){
    return `${toDateInput(date)}T${formatTime(date)}`;
}

function toDateInput(date){
    return [
        date.getFullYear(),
        String(date.getMonth() + 1).padStart(2, "0"),
        String(date.getDate()).padStart(2, "0")
    ].join("-");
}

function showToast(message, type = "primary"){
    const container = document.getElementById("availabilityToastContainer");
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
    container.appendChild(toast);
    const instance = new bootstrap.Toast(toast, { delay:3000 });
    toast.addEventListener("hidden.bs.toast", () => toast.remove());
    instance.show();
}

function confirmAction(title, message){
    return new Promise(resolve => {
        const modal = document.getElementById("availabilityConfirmModal");
        const titleEl = document.getElementById("availabilityConfirmTitle");
        const messageEl = document.getElementById("availabilityConfirmMessage");
        const confirmButton = document.getElementById("availabilityConfirmOk");
        const instance = bootstrap.Modal.getOrCreateInstance(modal);

        titleEl.textContent = title;
        messageEl.textContent = message;

        const cleanup = () => {
            confirmButton.removeEventListener("click", onConfirm);
            modal.removeEventListener("hidden.bs.modal", onHidden);
        };
        const onConfirm = () => {
            cleanup();
            instance.hide();
            resolve(true);
        };
        const onHidden = () => {
            cleanup();
            resolve(false);
        };

        confirmButton.addEventListener("click", onConfirm, { once:true });
        modal.addEventListener("hidden.bs.modal", onHidden, { once:true });
        instance.show();
    });
}

function downloadBlob(blob, filename){
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
}

function escapeHtml(value){
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function getOldestAvailableDate() {
    let oldest = null;
    availabilityRows.forEach(row => {
        if (isUnavailable(row)) return;
        const dt = getAvailableDate(row);
        if (dt && !Number.isNaN(dt.getTime())) {
            if (!oldest || dt < oldest) {
                oldest = dt;
            }
        }
    });
    return oldest || new Date();
}

function getSlotStartPoint() {
    return getActiveSlotStart(new Date());
}

async function readJsonResponse(response){
    const text = await response.text();
    if(!text){
        return {};
    }

    try{
        return JSON.parse(text);
    }
    catch(error){
        return {
            detail: text.slice(0, 200)
        };
    }
}
