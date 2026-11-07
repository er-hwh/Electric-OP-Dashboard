/* ===========================
   GLOBAL VARIABLES
=========================== */

let originalData = [];
let filteredData = [];

let overallData = [];
let zeroWheelData = [];
let runningKmData = [];

let activeAnalyzer = "overall";

let currentResultData = [];

const RUNNING_DUTY_TYPES = [
    "WR"
];

/* ===========================
   RULE CONFIG
=========================== */

const EXCLUDED_DUTY_TYPES = [

    "WR",
    "LR",
    "SH",
    "BNKD",
    "DEAD",
    "COCH",
    "DEPT",
    "BD",
    "GHAT",
    "MINIMUM GURANTEED",
    "CP"

];

let resultTable = null;

/* ===========================
   INIT DATATABLE
=========================== */

$(document).ready(function(){

    $('#resultTable thead tr.filter-row th').each(function(){

        $(this).html(
            '<input type="text" placeholder="🔍" />'
        );

    });

    resultTable = new DataTable('#resultTable',{

        pageLength:50,

        scrollX:true,

        scrollY:"65vh",

        fixedHeader:true,

        order:[[0,'asc']]

    });

    resultTable.columns().every(function(index){

        const column = this;

        $('input', $('.filter-row th')[index])

        .on('keyup change', function(){

            if(column.search() !== this.value){

                column
                    .search(this.value)
                    .draw();

            }

        });

    });

    // Check URL query parameters to auto-select the proper tab
    const urlParams = new URLSearchParams(window.location.search);
    const activeTab = urlParams.get('tab');
    if (activeTab === 'runningKm') {
        $("#runningKmTabBtn").click();
    } else {
        $("#zeroWheelTabBtn").click();
    }

});

function getReportHeading(){

    if(activeAnalyzer === "overall"){

        return "CMS OVERALL DUTIES REPORT";

    }

    if(activeAnalyzer === "runningKm"){

        return "CMS RUNNING KM ANALYZER REPORT";

    }

    return "CMS ZERO WHEEL MOVEMENT REPORT";

}

$("#btnApplyKmFilter").on(
    "click",
    function(){

        if(activeAnalyzer === "zeroWheel"){
            activeAnalyzer = "overall";
        }

        $("#resultTitle").text(
            activeAnalyzer === "runningKm"
                ? "Running KM Analysis Result"
                : "Overall Analysis Result"
        );

        applyRunningKmFilter();

    }
);

$("#btnResetKmFilter").on(
    "click",
    function(){

        $("#kmFrom").val(0);

        $("#kmTo").val(30);

        $("#dutyFrom").val("00:00");

        $("#dutyTo").val("23:59");

        $("#speedSlabFilter").val("ALL");

        $("#speedFrom").val("");

        $("#speedTo").val("");

        const baseData =
            activeAnalyzer === "runningKm"
                ? runningKmData
                : overallData;

        filteredData =
            baseData.filter(
                row => true
            );

        $("#includedGroups").text(
            getUniqueGroups(filteredData)
        );

        $("#returnedRows").text(
            filteredData.length
        );

        loadResultTable();
        updateSummary();
    }
);

$("#speedSlabFilter").on("change", function() {
    $("#speedFrom").val("");
    $("#speedTo").val("");
    applyRunningKmFilter();
});

$("#speedFrom, #speedTo").on("input", function() {
    if ($(this).val() !== "") {
        $("#speedSlabFilter").val("ALL");
    }
});

$("#overallTabBtn").on(
    "click",
    function(){

        activeAnalyzer =
            "overall";

        $("#runningKmFilterPanel")
            .show();

        $("#overallTabBtn")
            .addClass("active");

        $("#zeroWheelTabBtn")
            .removeClass("active");

        $("#runningKmTabBtn")
            .removeClass("active");

        if (overallData.length > 0) {
            renderDailySummary();
            $("#dailySummarySection").show();
        }

        $("#resultTitle").text(
            "Overall Analysis Result"
        );

        filteredData =
            [...overallData];

        $("#includedGroups").text(
            getUniqueGroups(
                filteredData
            )
        );

        $("#returnedRows").text(
            filteredData.length
        );

        loadResultTable();
        updateSummary();

    }
);

$("#zeroWheelTabBtn").on(
    "click",
    function(){

        activeAnalyzer =
            "zeroWheel";

        $("#dailySummarySection")
            .hide();

        $("#runningKmFilterPanel")
            .hide();

        $("#zeroWheelTabBtn")
            .addClass("active");

        $("#overallTabBtn")
            .removeClass("active");

        $("#runningKmTabBtn")
            .removeClass("active");

        $("#resultTitle").text(
            "Zero Wheel Movement Result"
        );

        filteredData =
            [...zeroWheelData];

        $("#includedGroups").text(
            getUniqueGroups(filteredData)
        );

        $("#returnedRows").text(
            filteredData.length
        );

        loadResultTable();

        updateSummary();

    }
);

$("#runningKmTabBtn").on(
    "click",
    function(){

        activeAnalyzer =
            "runningKm";

        $("#dailySummarySection")
            .hide();

        $("#runningKmFilterPanel")
            .show();

        $("#runningKmTabBtn")
            .addClass("active");

        $("#overallTabBtn")
            .removeClass("active");

        $("#zeroWheelTabBtn")
            .removeClass("active");

        $("#resultTitle").text(
            "Running KM Analysis Result"
        );

        filteredData =
            [...runningKmData];

        $("#includedGroups").text(
            getUniqueGroups(
                filteredData
            )
        );

        $("#returnedRows").text(
            filteredData.length
        );

        loadResultTable();
        updateSummary();

    }
);

/* ===========================
   EXCEL READER
=========================== */

function findHeaderRow(sheetData){

    for(let i=0;i<sheetData.length;i++){

        const row = sheetData[i];

        if(!row) continue;

        const values = row.map(x =>
            String(x || "")
            .trim()
            .toUpperCase()
        );

        if(
            values.includes("S.NO.") &&
            values.includes("CREW ID")
        ){
            return i;
        }
    }

    return -1;
}

function readExcelFile(file){

    return new Promise((resolve,reject)=>{

        const reader = new FileReader();

        reader.onload = function(e){

            try{

                const data = new Uint8Array(e.target.result);

                const workbook = XLSX.read(data,{
                    type:'array'
                });

                const firstSheet =
                    workbook.Sheets[
                        workbook.SheetNames[0]
                    ];

                const rawData =
                    XLSX.utils.sheet_to_json(
                        firstSheet,
                        {
                            header:1,
                            defval:""
                        }
                    );

                const headerIndex =
                    findHeaderRow(rawData);

                if(headerIndex === -1){

                    reject(
                        "Header row not found."
                    );

                    return;
                }

                const headers =
                    rawData[headerIndex];

                const rows =
                    rawData.slice(headerIndex + 1);

                const jsonData =
                    rows.map(row=>{

                        let obj = {};

                        headers.forEach(
                            (header,index)=>{

                            obj[
                                String(header).trim()
                            ] =
                                row[index] || "";

                        });

                        return obj;

                    });

                resolve(jsonData);

            }
            catch(err){

                reject(err);

            }

        };

        reader.readAsArrayBuffer(file);

    });

}

$("#btnAnalyze").on("click",async function(){

    const file =
        $("#excelFile")[0].files[0];

    if(!file){

        alert(
            "Please select an Excel file."
        );

        return;
    }

    try{

        $("#loadingBox").show();

        $("#fileStatus")
            .text("Reading");

        originalData =
            await readExcelFile(file);

        const dutyGroups =
            new Set();

        originalData.forEach(row=>{

            const sno =
                String(
                    row["S.No."] ||
                    row["S.NO."] ||
                    ""
                ).trim();

            if(sno){

                dutyGroups.add(sno);

            }

        });

        $("#totalRows")
            .text(originalData.length);

        $("#totalGroups")
            .text(dutyGroups.size);

        $("#fileStatus")
            .text("Loaded");

        $("#loadingBox").hide();

        alert(
            `Excel Loaded Successfully\n\nRows : ${originalData.length}\nGroups : ${dutyGroups.size}`
        );

        analyzeZeroWheel();

        analyzeRunningKm();

        analyzeOverall();

        renderDailySummary();

        if(activeAnalyzer === "runningKm"){

            $("#dailySummarySection")
                .hide();

            filteredData =
                [...runningKmData];

            $("#runningKmFilterPanel")
                .show();

            $("#resultTitle").text(
                "Running KM Analysis Result"
            );

            $("#runningKmTabBtn")
                .addClass("active");

            $("#overallTabBtn")
                .removeClass("active");

            $("#zeroWheelTabBtn")
                .removeClass("active");

        }
        else if(activeAnalyzer === "zeroWheel"){

            $("#dailySummarySection")
                .hide();

            filteredData =
                [...zeroWheelData];

            $("#runningKmFilterPanel")
                .hide();

            $("#resultTitle").text(
                "Zero Wheel Movement Result"
            );

            $("#zeroWheelTabBtn")
                .addClass("active");

            $("#overallTabBtn")
                .removeClass("active");

            $("#runningKmTabBtn")
                .removeClass("active");

        }
        else{

            activeAnalyzer =
                "overall";

            $("#dailySummarySection")
                .show();

            filteredData =
                [...overallData];

            $("#runningKmFilterPanel")
                .show();

            $("#resultTitle").text(
                "Overall Analysis Result"
            );

            $("#overallTabBtn")
                .addClass("active");

            $("#zeroWheelTabBtn")
                .removeClass("active");

            $("#runningKmTabBtn")
                .removeClass("active");

        }

        $("#includedGroups").text(
            getUniqueGroups(filteredData)
        );

        $("#returnedRows").text(
            filteredData.length
        );

        loadResultTable();

        updateSummary();

    }
    catch(error){

        $("#loadingBox").hide();

        $("#fileStatus")
            .text("Error");

        console.error(error);

        alert(
            "Error reading Excel.\n\n" +
            error
        );

    }

});

/* ===========================
   GROUP BY S.NO
=========================== */

function groupBySNo(data){

    const groups = {};

    data.forEach(row=>{

        const sno =
            String(
                row["S.No."] ||
                row["S.NO."] ||
                ""
            ).trim();

        if(!sno) return;

        if(!groups[sno]){

            groups[sno] = [];

        }

        groups[sno].push(row);

    });

    return groups;

}

/* ===========================
   DUTY TYPE EXTRACTOR
=========================== */

function getDutyTypes(group){

    return group.map(row=>{

        return String(
            row["DUTY TYPE"] || ""
        )
        .trim()
        .toUpperCase();

    });

}

/* ===========================
   VALIDATE DUTY GROUP
=========================== */

function isValidDutyGroup(group){

    const dutyTypes =
        getDutyTypes(group);

    const hasYR =
        dutyTypes.includes("YR");

    const hasWT =
        dutyTypes.includes("WT");

    const hasRequired =
        hasYR || hasWT;

    const hasExcludedDutyType =
        dutyTypes.some(type =>
            EXCLUDED_DUTY_TYPES.includes(type)
        );

    const hasExcludedRemarks =
        hasExcludedText(group);

    return (

        hasRequired &&

        !hasExcludedDutyType &&

        !hasExcludedRemarks

    );

}

/* ===========================
   GROUP COUNTER
=========================== */

function getUniqueGroups(data){

    const groups =
        new Set();

    data.forEach(row=>{

        const sno =
            String(
                row["S.No."] ||
                row["S.NO."] ||
                ""
            ).trim();

        if(sno){

            groups.add(sno);

        }

    });

    return groups.size;

}

/* ===========================
   MAIN ANALYZER
=========================== */

function analyzeZeroWheel(){

    filteredData = [];

    zeroWheelData = [];

    const groupedData =
        groupBySNo(originalData);

    const groups =
        Object.values(groupedData);

    groups.sort((a,b)=>{

        const dateA =
            parseDateValue(a[0]["SIGNON DATE"]) || new Date(0);

        const dateB =
            parseDateValue(b[0]["SIGNON DATE"]) || new Date(0);

        return dateA - dateB;

    });

    let includedCount = 0;
    let excludedCount = 0;

    let newSno = 1;

    groups.forEach(group=>{

        const valid =
            isValidDutyGroup(group);

        if(valid){

            includedCount++;

            group.forEach(row=>{

                row["NEW_SNO"] =
                    newSno;

                zeroWheelData.push(row);

            });

            newSno++;

        }
        else{

            excludedCount++;

        }

    });

    filteredData =
        [...zeroWheelData];

    $("#includedGroups").text(
        includedCount
    );

    $("#excludedGroups").text(
        excludedCount
    );

    $("#returnedRows").text(
        filteredData.length
    );

    $("#btnExport").prop(
        "disabled",
        false
    );

    $("#btnExportPdf").prop(
        "disabled",
        false
    );

    $("#btnCopy").prop(
        "disabled",
        false
    );
    updateSummary();

}


function extractRowSpeed(row) {
    if (!row) return null;
    let val = row["AVG. SPEED (KM/Hrs)"];
    if (val === undefined || val === null || val === "" || val === "-") {
        for (const k of Object.keys(row)) {
            const cleanKey = k.trim().toUpperCase();
            if (cleanKey.includes("AVG") && cleanKey.includes("SPEED")) {
                val = row[k];
                break;
            }
        }
    }
    if (val !== undefined && val !== null && val !== "" && val !== "-") {
        const num = parseFloat(String(val).replace(/[^0-9.-]/g, ""));
        if (!isNaN(num) && num > 0) return num;
    }
    return null;
}

function extractRouteKm(row) {
    if (!row) return 0;
    let val = row["Route KM"];
    if (val === undefined || val === null || val === "" || val === "-") {
        for (const k of Object.keys(row)) {
            const cleanKey = k.trim().toUpperCase();
            if (cleanKey === "ROUTE KM" || cleanKey === "ROUTE_KM" || cleanKey === "ROUTEKM") {
                val = row[k];
                break;
            }
        }
    }
    if (val !== undefined && val !== null && val !== "" && val !== "-") {
        const num = parseFloat(String(val).replace(/[^0-9.-]/g, ""));
        if (!isNaN(num) && num > 0) return num;
    }
    return 0;
}

function calculateGroupDutySpeed(group) {
    if (!group || group.length === 0) return 0.0;

    // 1. Priority 1: WR rows with recorded speed
    let wrRows = group.filter(row => {
        const dutyType = String(row["DUTY TYPE"] || row["Duty Type"] || "").trim().toUpperCase();
        return dutyType === "WR";
    });

    let totalWrKm = 0;
    let weightedWrSpeedSum = 0;
    let validWrSpeeds = [];

    wrRows.forEach(row => {
        const sp = extractRowSpeed(row);
        const km = extractRouteKm(row);
        if (sp !== null && sp > 0) {
            validWrSpeeds.push(sp);
            if (km > 0) {
                totalWrKm += km;
                weightedWrSpeedSum += (sp * km);
            }
        }
    });

    if (totalWrKm > 0 && weightedWrSpeedSum > 0) {
        return Number((weightedWrSpeedSum / totalWrKm).toFixed(2));
    }
    if (validWrSpeeds.length > 0) {
        return Number(Math.max(...validWrSpeeds).toFixed(2));
    }

    // 2. Priority 2: Any other row in the duty group with recorded speed (e.g. LR, SH, etc.)
    let totalOtherKm = 0;
    let weightedOtherSpeedSum = 0;
    let validOtherSpeeds = [];

    group.forEach(row => {
        const sp = extractRowSpeed(row);
        const km = extractRouteKm(row);
        if (sp !== null && sp > 0) {
            validOtherSpeeds.push(sp);
            if (km > 0) {
                totalOtherKm += km;
                weightedOtherSpeedSum += (sp * km);
            }
        }
    });

    if (totalOtherKm > 0 && weightedOtherSpeedSum > 0) {
        return Number((weightedOtherSpeedSum / totalOtherKm).toFixed(2));
    }
    if (validOtherSpeeds.length > 0) {
        return Number(Math.max(...validOtherSpeeds).toFixed(2));
    }

    // 3. Priority 3: Derive from Route KM and Duty Hours if Route KM > 0
    let groupKm = 0;
    let groupMinutes = 0;
    group.forEach(row => {
        groupKm += extractRouteKm(row);
        const rawDuty = row["DUTY HRS"] || row["Duty Hrs"] || row["TOTAL DUTY"] || row["Total Duty"] || "";
        const m = timeToMinutes(rawDuty);
        if (m > groupMinutes) groupMinutes = m;
    });

    if (groupKm > 0 && groupMinutes > 0) {
        const derivedSpeed = groupKm / (groupMinutes / 60);
        return Number(derivedSpeed.toFixed(2));
    }

    // 4. Priority 4: Zero Wheel Movement / 0 KM / Standby / No recorded movement
    return 0.0;
}

function analyzeRunningKm(){

    runningKmData = [];

    const groupedData =
        groupBySNo(originalData);

    const groups =
        Object.values(groupedData);

    let runningGroupCount = 0;

    let newSno = 1;

    groups.forEach(group=>{

        let runningKm = 0;

        let hasRunningDuty = false;

        group.forEach(row=>{

            const dutyType =
                String(
                    row["DUTY TYPE"] || row["Duty Type"] || ""
                )
                .trim()
                .toUpperCase();

            // Only consider rows where duty type = "WR" and consider "Route KM" column
            if(dutyType === "WR"){

                hasRunningDuty = true;

                const km = extractRouteKm(row);

                runningKm += km;

            }

        });

        if(hasRunningDuty){

            runningGroupCount++;

            const dutySpeed = calculateGroupDutySpeed(group);

            group.forEach(row=>{
                row["RUNNING_KM"] = Number(runningKm.toFixed(2));
                row["RUNNING_NEW_SNO"] =
                    newSno;
                row["DUTY_SPEED"] = dutySpeed;
                runningKmData.push(row);

            });

            newSno++;

        }

    });

    console.log(
        "Running Groups:",
        runningGroupCount
    );

}

function analyzeOverall(){

    overallData = [];

    const groupedData =
        groupBySNo(originalData);

    const groups =
        Object.values(groupedData);

    let overallGroupCount = 0;

    let newSno = 1;

    groups.forEach(group=>{

        let runningKm = 0;

        group.forEach(row=>{

            const dutyType =
                String(
                    row["DUTY TYPE"] || row["Duty Type"] || ""
                )
                .trim()
                .toUpperCase();

            // Only consider rows where duty type = "WR" and consider "Route KM" column
            if(dutyType === "WR"){

                const km = extractRouteKm(row);

                runningKm += km;

            }

        });

        overallGroupCount++;

        const dutySpeed = calculateGroupDutySpeed(group);

        group.forEach(row=>{
            row["RUNNING_KM"] = Number(runningKm.toFixed(2));
            row["RUNNING_NEW_SNO"] =
                newSno;
            row["DUTY_SPEED"] = dutySpeed;
            overallData.push(row);

        });

        newSno++;

    });

    console.log(
        "Overall Groups:",
        overallGroupCount
    );

}

function applyRunningKmFilter(){

    const fromKm =
        Number($("#kmFrom").val()) || 0;

    const toKm =
        Number($("#kmTo").val()) || 999999;

    const dutyFrom =
        timeToMinutes(
            $("#dutyFrom").val()
        );

    const dutyTo =
        timeToMinutes(
            $("#dutyTo").val()
        );

    const speedSlab = $("#speedSlabFilter").val() || "ALL";
    const speedFromVal = $("#speedFrom").val();
    const speedToVal = $("#speedTo").val();
    const hasSpeedFrom = speedFromVal !== "" && speedFromVal !== undefined && !isNaN(Number(speedFromVal));
    const hasSpeedTo = speedToVal !== "" && speedToVal !== undefined && !isNaN(Number(speedToVal));
    const speedFrom = hasSpeedFrom ? Number(speedFromVal) : null;
    const speedTo = hasSpeedTo ? Number(speedToVal) : null;

    const baseData =
        activeAnalyzer === "runningKm"
            ? runningKmData
            : overallData;

    filteredData =
        baseData.filter(row=>{

            const km =
                Number(
                    row["RUNNING_KM"] || 0
                );

            const dutyMinutes =
                timeToMinutes(
                    row["TOTAL DUTY"]
                );

            const speed = row["DUTY_SPEED"];

            // KM Check
            if (km < fromKm || km > toKm) return false;

            // Duty Hrs Check
            if (dutyMinutes < dutyFrom || dutyMinutes > dutyTo) return false;

            // Speed Slab Check (Default is ALL)
            if (speedSlab !== "ALL") {
                if (speed === null || speed === undefined) return false;
                if (speedSlab === "<= 5" && !(speed <= 5)) return false;
                if (speedSlab === "05-08" && !(speed > 5 && speed <= 8)) return false;
                if (speedSlab === "<= 8" && !(speed <= 8)) return false;
                if (speedSlab === "08-10" && !(speed > 8 && speed <= 10)) return false;
                if (speedSlab === "10-12" && !(speed > 10 && speed <= 12)) return false;
                if (speedSlab === "12-15" && !(speed > 12 && speed <= 15)) return false;
                if (speedSlab === "> 15" && !(speed > 15)) return false;
            }

            // Custom Speed Range Check (if user entered Min/Max)
            if (hasSpeedFrom) {
                if (speed === null || speed === undefined || speed < speedFrom) return false;
            }
            if (hasSpeedTo) {
                if (speed === null || speed === undefined || speed > speedTo) return false;
            }

            return true;

        });

    $("#includedGroups").text(
        getUniqueGroups(filteredData)
    );

    $("#returnedRows").text(
        filteredData.length
    );

    loadResultTable();
    updateSummary();

}

/* ===========================
   LOAD RESULT TABLE
=========================== */

function loadResultTable(){

    resultTable.clear();

    const snoMap = {};

    let currentSno = 1;

    filteredData.forEach(row=>{

        const originalSno =
            String(
                row["S.No."] ||
                row["S.NO."] ||
                ""
            ).trim();

        if(!snoMap[originalSno]){

            snoMap[originalSno] =
                currentSno++;

        }

        resultTable.row.add([

            snoMap[originalSno],

            row["CREW ID"] || "",
            row["NAME"] || "",
            row["DESIG"] || "",
            row["TOTAL DUTY"] || "",
            row["SIGNON DATE"] || "",
            row["SIGNON STTN"] || "",
            row["DEPARTURE"] || "",
            row["PDD"] || "",
            row["ARRIVAL"] || "",
            row["SIGNOFF DATE"] || "",
            row["SIGNOFF STTN"] || "",
            row["DUTY HRS"] || "",
            row["DUTY TYPE"] || "",
            row["TRAIN NO"] || "",
            row["LOCO NO"] || "",
            row["WHEEL MOVEMENT"] || "",
            row["AVG. SPEED (KM/Hrs)"] || "",
            row["Route KM"] || "",
            row["TOTAL KM"] || "",
            row["M/K"] || "",
            row["CTO"] || "",
            row["CMO"] || "",
            row["Section"] || "",
            row["Route Name"] || "",
            row["RUNNING_KM"] || ""

        ]);

    });

    resultTable.draw(false);

}

/* ===========================
   DATE PARSING & RANGE HELPERS
=========================== */

function parseDateValue(val) {
    if (!val) return null;
    if (val instanceof Date && !isNaN(val.getTime())) {
        return val;
    }
    if (typeof val === 'number') {
        if (val > 0) {
            const date = new Date(Math.round((val - 25569) * 86400 * 1000));
            return isNaN(date.getTime()) ? null : date;
        }
        return null;
    }
    const str = String(val).trim();
    if (!str || str === '-' || str.toUpperCase() === 'NA' || str.toUpperCase() === 'NULL') return null;

    const datePart = str.split(/[ T]/)[0].trim();

    // DD-MM-YYYY, DD/MM/YYYY, DD.MM.YYYY
    const dmyMatch = datePart.match(/^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})$/);
    if (dmyMatch) {
        let day = parseInt(dmyMatch[1], 10);
        let month = parseInt(dmyMatch[2], 10) - 1;
        let year = parseInt(dmyMatch[3], 10);
        if (year < 100) year += 2000;
        const d = new Date(year, month, day);
        return isNaN(d.getTime()) ? null : d;
    }

    // YYYY-MM-DD, YYYY/MM/DD
    const ymdMatch = datePart.match(/^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$/);
    if (ymdMatch) {
        let year = parseInt(ymdMatch[1], 10);
        let month = parseInt(ymdMatch[2], 10) - 1;
        let day = parseInt(ymdMatch[3], 10);
        const d = new Date(year, month, day);
        return isNaN(d.getTime()) ? null : d;
    }

    const fallback = new Date(str);
    return isNaN(fallback.getTime()) ? null : fallback;
}

function formatDateToDDMMYYYY(d) {
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    return `${day}-${month}-${year}`;
}

function getSignOffDateFromRow(row) {
    if (!row) return null;
    let raw = row["SIGNOFF DATE"] || row["Signoff Date"] || row["SIGN OFF DATE"] || row["Sign Off Date"] || row["SIGNOFF_DATE"] || "";
    if (!raw) {
        for (const k of Object.keys(row)) {
            const cleanKey = k.trim().toUpperCase();
            if ((cleanKey.includes("SIGNOFF") || cleanKey.includes("SIGN OFF") || cleanKey.includes("SIGN-OFF")) && cleanKey.includes("DATE")) {
                raw = row[k];
                break;
            }
        }
    }
    return parseDateValue(raw);
}

function getSignOnDateFromRow(row) {
    if (!row) return null;
    let raw = row["SIGNON DATE"] || row["Signon Date"] || row["SIGN ON DATE"] || row["Sign On Date"] || row["SIGNON_DATE"] || "";
    if (!raw) {
        for (const k of Object.keys(row)) {
            const cleanKey = k.trim().toUpperCase();
            if ((cleanKey.includes("SIGNON") || cleanKey.includes("SIGN ON") || cleanKey.includes("SIGN-ON")) && cleanKey.includes("DATE")) {
                raw = row[k];
                break;
            }
        }
    }
    return parseDateValue(raw);
}

function getDateRangeFromData(data) {
    if (!data || data.length === 0) {
        return formatDateToDDMMYYYY(new Date());
    }

    const timestamps = [];
    const grouped = groupBySNo(data);

    if (Object.keys(grouped).length > 0) {
        Object.values(grouped).forEach(group => {
            let dateVal = null;
            // Prioritize SIGNOFF DATE (duties in CMS daily reports are classified by sign-off date)
            for (let i = group.length - 1; i >= 0; i--) {
                const d = getSignOffDateFromRow(group[i]);
                if (d) {
                    dateVal = d;
                    break;
                }
            }
            if (!dateVal) {
                for (let row of group) {
                    const d = getSignOffDateFromRow(row);
                    if (d) {
                        dateVal = d;
                        break;
                    }
                }
            }
            // Fallback to SIGNON DATE only if no signoff date found
            if (!dateVal) {
                for (let row of group) {
                    const d = getSignOnDateFromRow(row);
                    if (d) {
                        dateVal = d;
                        break;
                    }
                }
            }
            if (dateVal) {
                timestamps.push(dateVal.getTime());
            }
        });
    } else {
        data.forEach(row => {
            const d = getSignOffDateFromRow(row) || getSignOnDateFromRow(row);
            if (d) timestamps.push(d.getTime());
        });
    }

    if (timestamps.length === 0) {
        return formatDateToDDMMYYYY(new Date());
    }

    const minDate = new Date(Math.min(...timestamps));
    const maxDate = new Date(Math.max(...timestamps));

    const minStr = formatDateToDDMMYYYY(minDate);
    const maxStr = formatDateToDDMMYYYY(maxDate);

    if (minStr === maxStr) {
        return minStr;
    }
    return `${minStr}_to_${maxStr}`;
}

/* ===========================
   EXPORT TO EXCEL
=========================== */

function exportToExcel(){

    if(filteredData.length === 0){

        alert("No data available for export.");

        return;
    }

    try{

        const snoMap = {};

        let currentSno = 1;

        const exportData =
            filteredData.map(row=>{

                const originalSno =
                    String(
                        row["S.No."] ||
                        row["S.NO."] ||
                        ""
                    ).trim();

                if(!snoMap[originalSno]){

                    snoMap[originalSno] =
                        currentSno++;

                }

                return {

                    "S.No.": snoMap[originalSno],

                    "CREW ID": row["CREW ID"] || "",
                    "NAME": row["NAME"] || "",
                    "DESIG": row["DESIG"] || "",
                    "TOTAL DUTY": row["TOTAL DUTY"] || "",
                    "SIGNON DATE": row["SIGNON DATE"] || "",
                    "SIGNON STTN": row["SIGNON STTN"] || "",
                    "DEPARTURE": row["DEPARTURE"] || "",
                    "PDD": row["PDD"] || "",
                    "ARRIVAL": row["ARRIVAL"] || "",
                    "SIGNOFF DATE": row["SIGNOFF DATE"] || "",
                    "SIGNOFF STTN": row["SIGNOFF STTN"] || "",
                    "DUTY HRS": row["DUTY HRS"] || "",
                    "DUTY TYPE": row["DUTY TYPE"] || "",
                    "TRAIN NO": row["TRAIN NO"] || "",
                    "LOCO NO": row["LOCO NO"] || "",
                    "WHEEL MOVEMENT": row["WHEEL MOVEMENT"] || "",
                    "AVG SPEED": row["AVG. SPEED (KM/Hrs)"] || "",
                    "ROUTE KM": row["Route KM"] || "",
                    "TOTAL KM": row["TOTAL KM"] || "",
                    "M/K": row["M/K"] || "",
                    "CTO": row["CTO"] || "",
                    "CMO": row["CMO"] || "",
                    "SECTION": row["Section"] || "",
                    "ROUTE NAME": row["Route Name"] || "",
                    "RUNNING KM": row["RUNNING_KM"] || ""

                };

            });

        const wb =
            XLSX.utils.book_new();

        const dateRangeStr = getDateRangeFromData(filteredData);

        const heading = `${getReportHeading()} | Date: ${dateRangeStr.replace(/_/g, " ")} | Generated: ${new Date().toLocaleString()} | Total Duty: ${$("#totalGroups").text()} (Rows: ${$("#totalRows").text()}) | Matches Found: ${$("#includedGroups").text()} (Rows: ${$("#returnedRows").text()})`;

        const ws =
            XLSX.utils.aoa_to_sheet([
                [heading]
            ]);

        XLSX.utils.sheet_add_json(
            ws,
            exportData,
            {
                origin:"A3"
            }
        );

        ws["!merges"] = [{
            s:{r:0,c:0},
            e:{r:0,c:26}
        }];

        ws["!cols"] = [

            {wch:8},
            {wch:12},
            {wch:30},
            {wch:15},
            {wch:12},
            {wch:18},
            {wch:15},
            {wch:15},
            {wch:12},
            {wch:15},
            {wch:18},
            {wch:15},
            {wch:12},
            {wch:12},
            {wch:12},
            {wch:12},
            {wch:18},
            {wch:12},
            {wch:10},
            {wch:10},
            {wch:8},
            {wch:12},
            {wch:12},
            {wch:20},
            {wch:30},
            {wch:15}

        ];

        let sheetName = "Overall";
        let prefix = "Overall_Duties";
        if(activeAnalyzer === "runningKm"){
            sheetName = "Running KM";
            prefix = "Running_KM_Analyzer";
        } else if(activeAnalyzer === "zeroWheel"){
            sheetName = "Zero Wheel";
            prefix = "Zero_Wheel_Movement";
        }

        XLSX.utils.book_append_sheet(
            wb,
            ws,
            sheetName
        );

        const fileName = `${prefix}_${dateRangeStr}.xlsx`;

        XLSX.writeFile(
            wb,
            fileName
        );

    }
    catch(error){

        console.error(error);

        alert("Export failed.");

    }

}

/* ===========================
   EXPORT PDF
=========================== */

function exportToPdf(){

    if(filteredData.length === 0){

        alert("No data available.");

        return;
    }

    const { jsPDF } = window.jspdf;

    const doc = new jsPDF(
        'landscape',
        'mm',
        'a4'
    );

    const dateRangeStr = getDateRangeFromData(filteredData);

    const heading = `${getReportHeading()} | Date: ${dateRangeStr.replace(/_/g, " ")} | Generated: ${new Date().toLocaleString()} | Total Duty: ${$("#totalGroups").text()} (Rows: ${$("#totalRows").text()}) | Matches Found: ${$("#includedGroups").text()} (Rows: ${$("#returnedRows").text()})`;

    doc.setFontSize(8);

    doc.setFont(undefined,"bold");

    doc.text(
        heading,
        8,
        8
    );

    const tableData = [];

    const snoMap = {};

    let currentSno = 1;

    filteredData.forEach(row=>{

        const originalSno =
            String(
                row["S.No."] ||
                row["S.NO."] ||
                ""
            ).trim();

        if(!snoMap[originalSno]){

            snoMap[originalSno] =
                currentSno++;

        }

        tableData.push([

            snoMap[originalSno],

            row["CREW ID"] || "",
            row["NAME"] || "",
            row["DESIG"] || "",
            row["TOTAL DUTY"] || "",
            row["SIGNON DATE"] || "",
            row["SIGNON STTN"] || "",
            row["DEPARTURE"] || "",
            row["PDD"] || "",
            row["ARRIVAL"] || "",
            row["SIGNOFF DATE"] || "",
            row["SIGNOFF STTN"] || "",
            row["DUTY HRS"] || "",
            row["DUTY TYPE"] || "",
            row["TRAIN NO"] || "",
            row["LOCO NO"] || "",
            row["WHEEL MOVEMENT"] || "",
            row["AVG. SPEED (KM/Hrs)"] || "",
            row["Route KM"] || "",
            row["TOTAL KM"] || "",
            row["M/K"] || "",
            row["CTO"] || "",
            row["CMO"] || "",
            row["Section"] || "",
            row["Route Name"] || "",
            row["RUNNING_KM"] || ""

        ]);

    });

    doc.autoTable({

        startY:12,

        head:[[
            "S.No",
            "Crew ID",
            "Name",
            "Desig",
            "Total Duty",
            "SignOn Date",
            "SignOn Stn",
            "Departure",
            "PDD",
            "Arrival",
            "SignOff Date",
            "SignOff Stn",
            "Duty Hrs",
            "Duty Type",
            "Train No",
            "Loco No",
            "Wheel Mov",
            "Avg Speed",
            "Route KM",
            "Total KM",
            "M/K",
            "CTO",
            "CMO",
            "Section",
            "Route Name",
            "Running KM"
        ]],

        body:tableData,

        theme:"grid",

        styles:{
            fontSize:4,
            cellPadding:0.5,
            overflow:'linebreak',
            valign:'middle'
        },

        headStyles:{
            fillColor:[52,73,94],
            textColor:[255,255,255],
            fontSize:4,
            halign:'center'
        },

        alternateRowStyles:{
            fillColor:[245,245,245]
        },

        tableWidth:'auto',

        rowPageBreak:'auto',

        showHead:'everyPage',

        margin:{
            top:12,
            left:2,
            right:2
        }

    });

    let prefix = "Overall_Duties";
    if(activeAnalyzer === "runningKm"){
        prefix = "Running_KM_Analyzer";
    } else if(activeAnalyzer === "zeroWheel"){
        prefix = "Zero_Wheel_Movement";
    }

    const fileName = `${prefix}_${dateRangeStr}.pdf`;

    doc.save(fileName);

}

/* ===========================
   BUTTON PLACEHOLDERS
=========================== */

$("#btnExport").on("click",function(){

    exportToExcel();

});

$("#btnExportPdf").on("click",function(){

    exportToPdf();

});

$("#btnCopy").on("click",function(){
    var el = document.getElementById("resultTable");
    if(!el) return;
    
    var body = document.body, range, sel;
    if (document.createRange && window.getSelection) {
        range = document.createRange();
        sel = window.getSelection();
        sel.removeAllRanges();
        try {
            range.selectNodeContents(el);
            sel.addRange(range);
        } catch (e) {
            range.selectNode(el);
            sel.addRange(range);
        }
    } else if (body.createTextRange) {
        range = body.createTextRange();
        range.moveToElementText(el);
        range.select();
    }
    
    try {
        document.execCommand("copy");
        alert("Table copied to clipboard!");
    } catch(err) {
        alert("Failed to copy table.");
    }
    if(window.getSelection) {
        window.getSelection().removeAllRanges();
    }
});

$("#btnClear").on("click",function(){

    location.reload();

});

function parseCmsDate(dateStr){
    return parseDateValue(dateStr) || new Date(0);
}

function timeToMinutes(timeStr){

    if(!timeStr)
        return 0;

    const parts =
        String(timeStr).split(":");

    const hh =
        Number(parts[0]) || 0;

    const mm =
        Number(parts[1]) || 0;

    return (hh * 60) + mm;
}

function getCurrentData(){
    return filteredData;
}

function hasExcludedText(group){

    return group.some(row=>{

        // Gather train number column values
        const trainVals = [];
        for (const k of Object.keys(row)) {
            const cleanKey = k.trim().toUpperCase();
            if (
                cleanKey === "TRAIN NO" ||
                cleanKey === "TRAIN NO." ||
                cleanKey === "TRAIN_NO" ||
                cleanKey === "TRAIN NUMBER" ||
                cleanKey === "TRAIN" ||
                cleanKey.includes("TRAIN NO")
            ) {
                if (row[k] !== undefined && row[k] !== null && String(row[k]).trim() !== "") {
                    trainVals.push(String(row[k]));
                }
            }
        }

        if (trainVals.length === 0) {
            const fallback =
                row["TRAIN NO"] ||
                row["Train No"] ||
                row["TRAIN NO."] ||
                row["Train No."] ||
                "";
            trainVals.push(String(fallback));
        }

        // Excluded exact phrases requested for Zero Wheel Movement
        const excludedExactPhrases = [
            "RPH T/YD",
            "RPH TRAFFIC/YD",
            "RPH T-YD",
            "RPH T YD",
            "STAND BY",
            "STAND/BY"
        ];

        return trainVals.some(rawTrainNo => {
            const text =
                String(rawTrainNo)
                .toUpperCase()
                .trim();

            if (!text) return false;

            // Basic keywords
            const hasKeyword =
                text.includes("ART") ||
                text.includes("PT") ||
                text.includes("PILOT") ||
                text.includes("SHUNT") ||
                text.includes("ENQ");

            // RJG + Q/QRY combinations
            const hasRJGQ =
                text.includes("RJG") &&
                (
                    text.includes("QRY") ||
                    text.includes("/Q") ||
                    text.includes("-Q") ||
                    text.includes(" Q ")
                );

            // Excluded RPH / Yard patterns
            const normalized = text.replace(/\s+/g, " ");

            const hasExcludedTrainPatterns =
                normalized.includes("RPH ET") ||
                normalized.includes("RPH/ET") ||
                normalized.includes("T/YARD RPH") ||
                /RPH\s*\/\s*ET/.test(text) ||
                /T\s*\/\s*YARD\s+RPH/.test(text);

            // Check if train no contains specified exact phrases
            const hasExcludedExactPhrase =
                excludedExactPhrases.some(phrase =>
                    text.includes(phrase) || normalized.includes(phrase)
                ) ||
                /RPH\s+T\s*\/\s*YD/.test(text) ||
                /RPH\s+TRAFFIC\s*\/\s*YD/.test(text) ||
                /RPH\s+T\s*-\s*YD/.test(text) ||
                /RPH\s+T\s+YD/.test(text) ||
                /STAND\s+BY/.test(text) ||
                /STAND\s*\/\s*BY/.test(text);

            return (
                hasKeyword ||
                hasRJGQ ||
                hasExcludedTrainPatterns ||
                hasExcludedExactPhrase
            );
        });

    });

}

function calculateTotalKm(data){
    if(!data || data.length === 0) return 0;
    let totalKm = 0;
    data.forEach(row => {
        const dutyType = String(row["DUTY TYPE"] || row["Duty Type"] || "").trim().toUpperCase();
        if(dutyType === "WR"){
            totalKm += extractRouteKm(row);
        }
    });
    return Number(totalKm.toFixed(1));
}

function calculateAverageSpeed(data){
    if(!data || data.length === 0) return null;
    let totalWrKm = 0;
    let totalWeightedSpeedKm = 0;
    let validSpeeds = [];

    data.forEach(row => {
        const dutyType = String(row["DUTY TYPE"] || row["Duty Type"] || "").trim().toUpperCase();
        if(dutyType === "WR"){
            const sp = extractRowSpeed(row);
            const km = extractRouteKm(row);
            if(sp !== null && sp > 0){
                validSpeeds.push(sp);
                if(km > 0){
                    totalWrKm += km;
                    totalWeightedSpeedKm += (sp * km);
                }
            }
        }
    });

    if(totalWrKm > 0 && totalWeightedSpeedKm > 0){
        return Number((totalWeightedSpeedKm / totalWrKm).toFixed(1));
    }
    if(validSpeeds.length > 0){
        const sum = validSpeeds.reduce((a, b) => a + b, 0);
        return Number((sum / validSpeeds.length).toFixed(1));
    }
    return null;
}

function updateSummary(){

    const totalDuty =
        $("#totalGroups").text();

    const totalRows =
        $("#totalRows").text();

    const matchedDuty =
        $("#includedGroups").text();

    const returnedRows =
        $("#returnedRows").text();

    const avgSpeed = calculateAverageSpeed(filteredData);
    const avgSpeedText = avgSpeed !== null ? ` &nbsp; | &nbsp; Avg Speed : <span>${avgSpeed} KMPH</span>` : "";

    $("#summaryText").html(

        `Total Duty : <span>${totalDuty}</span> (Rows : ${totalRows})
         &nbsp; | &nbsp;
         Matches Found : <span>${matchedDuty}</span> (Rows : ${returnedRows})${avgSpeedText}`

    );

}

/* ===========================
   SUMMARY PREVIEW MODAL
=========================== */

function calculateSummary(type) {
    let summary = {};
    let totalDuty = 0;
    
    // We want the summary of the currently active/filtered dataset
    // We will group the filteredData by S.No. to count unique duties
    const groupedData = groupBySNo(filteredData);
    const groups = Object.values(groupedData);
    
    groups.forEach(group => {
        let runningKm = 0;
        let dutyMinutes = 0;
        
        // Sum route KM for this group to get distance run (only WR rows)
        group.forEach(row => {
            const dutyType = String(row["DUTY TYPE"] || row["Duty Type"] || "").trim().toUpperCase();
            if (dutyType === "WR") {
                runningKm += extractRouteKm(row);
            }
        });
        
        // Total duty should be same across the group
        if (group.length > 0) {
             dutyMinutes = timeToMinutes(group[0]["TOTAL DUTY"]);
        }
        
        if (type === 'hrs') {
            let slab = '';
            const hours = dutyMinutes / 60;
            if (hours <= 4) slab = '<= 04:00';
            else if (hours > 4 && hours < 9) slab = '> 04:00 & < 09:00';
            else if (hours >= 9 && hours < 11) slab = '>= 09:00 & < 11:00';
            else if (hours >= 11 && hours < 12) slab = '>= 11:00 & < 12:00';
            else if (hours >= 12 && hours < 14) slab = '>= 12:00 & < 14:00';
            else slab = '>= 14:00';
            
            summary[slab] = (summary[slab] || 0) + 1;
        } else if (type === 'distance') {
            let slab = '';
            if (runningKm <= 10) slab = '<= 10';
            else if (runningKm > 10 && runningKm <= 20) slab = '> 10 & <= 20';
            else if (runningKm > 20 && runningKm <= 30) slab = '> 20 & <= 30';
            else if (runningKm > 30 && runningKm <= 40) slab = '> 30 & <= 40';
            else if (runningKm > 40 && runningKm <= 50) slab = '> 40 & <= 50';
            else if (runningKm > 50 && runningKm <= 60) slab = '> 50 & <= 60';
            else if (runningKm > 60 && runningKm <= 90) slab = '> 60 & <= 90';
            else slab = '> 90';
            
            summary[slab] = (summary[slab] || 0) + 1;
        } else if (type === 'speed') {
            const dutySpeed = (group.length > 0 && group[0]["DUTY_SPEED"] !== undefined && group[0]["DUTY_SPEED"] !== null)
                ? group[0]["DUTY_SPEED"]
                : calculateGroupDutySpeed(group);

            if (dutySpeed !== null) {
                let slab = '';
                if (dutySpeed <= 5) slab = '<= 5 KMPH';
                else if (dutySpeed > 5 && dutySpeed <= 8) slab = '05 - 08 KMPH';
                else if (dutySpeed > 8 && dutySpeed <= 10) slab = '08 - 10 KMPH';
                else if (dutySpeed > 10 && dutySpeed <= 12) slab = '10 - 12 KMPH';
                else if (dutySpeed > 12 && dutySpeed <= 15) slab = '12 - 15 KMPH';
                else slab = '> 15 KMPH';

                summary[slab] = (summary[slab] || 0) + 1;
                if (dutySpeed <= 8) {
                    summary['<= 8 (ALL)'] = (summary['<= 8 (ALL)'] || 0) + 1;
                }
            } else {
                summary['N/A'] = (summary['N/A'] || 0) + 1;
            }
        }
        totalDuty++;
    });
    
    return { summary, totalDuty };
}

function renderSummaryTable(type) {
    const data = calculateSummary(type);
    let title = 'Hours';
    if (type === 'distance') title = 'Distance in KM';
    else if (type === 'speed') title = 'Speed in KMPH';

    let htmlHead = '<tr><th class="text-center">Slab (' + title + ')</th><th class="text-center">Total Duties</th><th class="text-center">Percentage</th></tr>';
    let htmlBody = '';
    
    const slabsHrs = [
        '<= 04:00',
        '> 04:00 & < 09:00',
        '>= 09:00 & < 11:00',
        '>= 11:00 & < 12:00',
        '>= 12:00 & < 14:00',
        '>= 14:00'
    ];
    const slabsDist = [
        '<= 10',
        '> 10 & <= 20',
        '> 20 & <= 30',
        '> 30 & <= 40',
        '> 40 & <= 50',
        '> 50 & <= 60',
        '> 60 & <= 90',
        '> 90'
    ];
    const slabsSpeed = [
        '<= 5 KMPH',
        '05 - 08 KMPH',
        '<= 8 (ALL)',
        '08 - 10 KMPH',
        '10 - 12 KMPH',
        '12 - 15 KMPH',
        '> 15 KMPH'
    ];
    if (data.summary['N/A']) {
        slabsSpeed.push('N/A');
    }
    
    const slabs = type === 'hrs' ? slabsHrs : (type === 'distance' ? slabsDist : slabsSpeed);
    
    slabs.forEach(slab => {
        const count = data.summary[slab] || 0;
        const pct = data.totalDuty > 0 ? ((count / data.totalDuty) * 100).toFixed(1) : "0.0";
        const isSubtotal = (slab === '<= 8 (ALL)');
        const rowClass = isSubtotal ? 'table-warning fw-bold' : '';
        htmlBody += `<tr class="${rowClass}"><td class="text-center">${slab}</td><td class="text-center fw-semibold">${count}</td><td class="text-center text-muted">${pct}%</td></tr>`;
    });
    htmlBody += `<tr class="table-info fw-bold"><td class="text-center">Total</td><td class="text-center">${data.totalDuty}</td><td class="text-center">100.0%</td></tr>`;
    
    $("#summaryTableHead").html(htmlHead);
    $("#summaryTableBody").html(htmlBody);
    
    // Store current type for export
    $("#summaryModal").data("exportType", type);
}

$("#btnPreviewKm").on("click", function() {
    $("#btnShowHrsSummary").removeClass("btn-secondary").addClass("btn-primary");
    $("#btnShowDistanceSummary").removeClass("btn-primary").addClass("btn-secondary");
    $("#btnShowSpeedSummary").removeClass("btn-primary").addClass("btn-secondary");
    renderSummaryTable('hrs'); // Default to Hrs
    // Try BS5 first, fallback to jQuery modal
    if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
        const modalEl = document.getElementById('summaryModal');
        let summaryModal = bootstrap.Modal.getInstance(modalEl);
        if (!summaryModal) {
            summaryModal = new bootstrap.Modal(modalEl);
        }
        summaryModal.show();
    } else {
        $('#summaryModal').modal('show');
    }
});

$("#btnShowHrsSummary").on("click", function() {
    $("#btnShowHrsSummary").removeClass("btn-secondary").addClass("btn-primary");
    $("#btnShowDistanceSummary").removeClass("btn-primary").addClass("btn-secondary");
    $("#btnShowSpeedSummary").removeClass("btn-primary").addClass("btn-secondary");
    renderSummaryTable('hrs');
});

$("#btnShowDistanceSummary").on("click", function() {
    $("#btnShowDistanceSummary").removeClass("btn-secondary").addClass("btn-primary");
    $("#btnShowHrsSummary").removeClass("btn-primary").addClass("btn-secondary");
    $("#btnShowSpeedSummary").removeClass("btn-primary").addClass("btn-secondary");
    renderSummaryTable('distance');
});

$("#btnShowSpeedSummary").on("click", function() {
    $("#btnShowSpeedSummary").removeClass("btn-secondary").addClass("btn-primary");
    $("#btnShowHrsSummary").removeClass("btn-primary").addClass("btn-secondary");
    $("#btnShowDistanceSummary").removeClass("btn-primary").addClass("btn-secondary");
    renderSummaryTable('speed');
});

$("#btnExportSummaryExcel").on("click", function() {
    const type = $("#summaryModal").data("exportType") || 'hrs';
    const data = calculateSummary(type);
    
    const slabsHrs = [
        '<= 04:00',
        '> 04:00 & < 09:00',
        '>= 09:00 & < 11:00',
        '>= 11:00 & < 12:00',
        '>= 12:00 & < 14:00',
        '>= 14:00'
    ];
    const slabsDist = [
        '<= 10',
        '> 10 & <= 20',
        '> 20 & <= 30',
        '> 30 & <= 40',
        '> 40 & <= 50',
        '> 50 & <= 60',
        '> 60 & <= 90',
        '> 90'
    ];
    const slabsSpeed = [
        '<= 5 KMPH',
        '05 - 08 KMPH',
        '<= 8 (ALL)',
        '08 - 10 KMPH',
        '10 - 12 KMPH',
        '12 - 15 KMPH',
        '> 15 KMPH'
    ];
    if (data.summary['N/A']) {
        slabsSpeed.push('N/A');
    }
    const slabs = type === 'hrs' ? slabsHrs : (type === 'distance' ? slabsDist : slabsSpeed);
    
    let exportData = [];
    slabs.forEach(slab => {
        const count = data.summary[slab] || 0;
        const pct = data.totalDuty > 0 ? ((count / data.totalDuty) * 100).toFixed(1) : "0.0";
        exportData.push({
            "Slab": slab,
            "Total Duties": count,
            "Percentage": pct + "%"
        });
    });
    exportData.push({
        "Slab": "Total",
        "Total Duties": data.totalDuty,
        "Percentage": "100.0%"
    });
    
    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(exportData);
    
    XLSX.utils.book_append_sheet(wb, ws, "Summary");
    
    const dateRangeStr = getDateRangeFromData(filteredData);
    let typeName = 'Hours';
    if (type === 'distance') typeName = 'Distance';
    else if (type === 'speed') typeName = 'Speed';
    const fileName = "Summary_" + typeName + "_" + dateRangeStr + ".xlsx";
    XLSX.writeFile(wb, fileName);
});

/* ===========================
   DAILY SUMMARY SECTION LOGIC
=========================== */

function renderDailySummary() {
    if (!overallData || overallData.length === 0) {
        $("#dailySummarySection").hide();
        return;
    }

    const dateStr = getDateRangeFromData(overallData);
    $("#dsDateBadge").text(`Date: ${dateStr.replace(/_/g, " ")}`);

    const groupedData = groupBySNo(overallData);
    const groups = Object.values(groupedData);
    const totalDuties = groups.length;
    const totalRows = overallData.length;

    $("#dsTotalBadge").text(`Total Duties: ${totalDuties}`);
    $("#kpiTotalDuties").text(totalDuties);
    $("#kpiTotalRows").text(`(${totalRows} Rows)`);

    // Identify Zero Wheel Movement duty groups from zeroWheelData
    const zwmGroupSnoSet = new Set();
    zeroWheelData.forEach(row => {
        const sno = String(row["S.No."] || row["S.NO."] || "").trim();
        if (sno) zwmGroupSnoSet.add(sno);
    });
    const zwmCount = zwmGroupSnoSet.size;
    const nonZwmCount = totalDuties - zwmCount;
    const zwmPct = totalDuties > 0 ? ((zwmCount / totalDuties) * 100).toFixed(1) : "0.0";
    const nonZwmPct = totalDuties > 0 ? ((nonZwmCount / totalDuties) * 100).toFixed(1) : "0.0";

    $("#kpiZwmCount").text(zwmCount);
    $("#kpiZwmPct").text(`${zwmPct}% of Total`);
    $("#dsZwmSubBadge").text(`ZWM: ${zwmCount} (${zwmPct}%)`);

    // 1. Duty Hours breakdown
    const dutyHrsCounts = {
        "<= 04:00": 0,
        "> 04:00 & < 09:00": 0,
        ">= 09:00 & < 11:00": 0,
        ">= 11:00 & < 12:00": 0,
        ">= 12:00 & < 14:00": 0,
        ">= 14:00": 0
    };

    // 2. KM Run breakdown
    const kmRunCounts = {
        "<= 10 KM": 0,
        "> 10 & <= 20 KM": 0,
        "> 20 & <= 30 KM": 0,
        "> 30 & <= 40 KM": 0,
        "> 40 & <= 50 KM": 0,
        "> 50 & <= 60 KM": 0,
        "> 60 & <= 90 KM": 0,
        "> 90 KM": 0
    };

    // 4. Speed breakdown
    const speedCounts = {
        "<= 5 KMPH": 0,
        "05 - 08 KMPH": 0,
        "<= 8 KMPH (ALL)": 0,
        "08 - 10 KMPH": 0,
        "10 - 12 KMPH": 0,
        "12 - 15 KMPH": 0,
        "> 15 KMPH": 0,
        "N/A": 0
    };

    let totalDutyMinutes = 0;
    let maxDutyMinutes = 0;
    let totalKmSum = 0;
    let validSpeeds = [];

    groups.forEach(group => {
        // Duty hours calculation
        let minutes = 0;
        for (let row of group) {
            const rawDuty = row["TOTAL DUTY"] || row["Total Duty"] || row["DUTY HRS"] || "";
            if (rawDuty) {
                minutes = timeToMinutes(rawDuty);
                if (minutes > 0) break;
            }
        }
        totalDutyMinutes += minutes;
        if (minutes > maxDutyMinutes) maxDutyMinutes = minutes;
        const hrs = minutes / 60;

        if (hrs <= 4) dutyHrsCounts["<= 04:00"]++;
        else if (hrs > 4 && hrs < 9) dutyHrsCounts["> 04:00 & < 09:00"]++;
        else if (hrs >= 9 && hrs < 11) dutyHrsCounts[">= 09:00 & < 11:00"]++;
        else if (hrs >= 11 && hrs < 12) dutyHrsCounts[">= 11:00 & < 12:00"]++;
        else if (hrs >= 12 && hrs < 14) dutyHrsCounts[">= 12:00 & < 14:00"]++;
        else dutyHrsCounts[">= 14:00"]++;

        // KM Run calculation
        const km = (group.length > 0 && group[0]["RUNNING_KM"] !== undefined) ? group[0]["RUNNING_KM"] : 0;
        totalKmSum += km;

        if (km <= 10) kmRunCounts["<= 10 KM"]++;
        else if (km > 10 && km <= 20) kmRunCounts["> 10 & <= 20 KM"]++;
        else if (km > 20 && km <= 30) kmRunCounts["> 20 & <= 30 KM"]++;
        else if (km > 30 && km <= 40) kmRunCounts["> 30 & <= 40 KM"]++;
        else if (km > 40 && km <= 50) kmRunCounts["> 40 & <= 50 KM"]++;
        else if (km > 50 && km <= 60) kmRunCounts["> 50 & <= 60 KM"]++;
        else if (km > 60 && km <= 90) kmRunCounts["> 60 & <= 90 KM"]++;
        else kmRunCounts["> 90 KM"]++;

        // Speed calculation
        let sp = (group.length > 0 && group[0]["DUTY_SPEED"] !== undefined && group[0]["DUTY_SPEED"] !== null)
            ? Number(group[0]["DUTY_SPEED"])
            : calculateGroupDutySpeed(group);

        if (isNaN(sp) || sp === null) sp = 0.0;

        validSpeeds.push(sp);
        if (sp <= 5) speedCounts["<= 5 KMPH"]++;
        else if (sp > 5 && sp <= 8) speedCounts["05 - 08 KMPH"]++;
        else if (sp > 8 && sp <= 10) speedCounts["08 - 10 KMPH"]++;
        else if (sp > 10 && sp <= 12) speedCounts["10 - 12 KMPH"]++;
        else if (sp > 12 && sp <= 15) speedCounts["12 - 15 KMPH"]++;
        else speedCounts["> 15 KMPH"]++;

        if (sp <= 8) speedCounts["<= 8 KMPH (ALL)"]++;
    });

    // KPI values
    const avgMinutes = totalDuties > 0 ? Math.round(totalDutyMinutes / totalDuties) : 0;
    const avgDutyHrsStr = `${String(Math.floor(avgMinutes / 60)).padStart(2, '0')}:${String(avgMinutes % 60).padStart(2, '0')}`;
    const maxDutyHrsStr = `${String(Math.floor(maxDutyMinutes / 60)).padStart(2, '0')}:${String(maxDutyMinutes % 60).padStart(2, '0')}`;
    $("#kpiAvgDutyHrs").text(avgDutyHrsStr);
    $("#kpiMaxDutyHrs").text(`Max: ${maxDutyHrsStr}`);

    totalKmSum = calculateTotalKm(overallData);
    $("#kpiTotalKm").text(`${totalKmSum.toFixed(1)} KM`);
    $("#kpiRunningDutiesCount").text(`${nonZwmCount} Running Duties (${zwmCount} ZWM Excluded)`);

    const avgSpeedVal = calculateAverageSpeed(overallData) || "0.0";
    $("#dsAvgSpeedBadgeTop").text(`Avg Speed: ${avgSpeedVal} KMPH`);
    $("#kpiAvgSpeedBig").text(`${avgSpeedVal} KMPH`);
    $("#kpiAvgSpeedDuties").text(`All ${totalDuties} Duties Considered`);

    // Render Table 1: Duty Hours Slabs
    $("#dsHrsSubBadge").text(`Total: ${totalDuties}`);
    let tbodyHrs = "";
    Object.keys(dutyHrsCounts).forEach(slab => {
        const count = dutyHrsCounts[slab];
        const pct = totalDuties > 0 ? ((count / totalDuties) * 100).toFixed(1) : "0.0";
        tbodyHrs += `<tr>
            <td class="text-start ps-3 fw-medium">${slab}</td>
            <td class="fw-semibold">${count}</td>
            <td class="text-muted">${pct}%</td>
        </tr>`;
    });
    tbodyHrs += `<tr class="table-secondary fw-bold">
        <td class="text-start ps-3">Total</td>
        <td>${totalDuties}</td>
        <td>100.0%</td>
    </tr>`;
    $("#dsDutyHoursTbody").html(tbodyHrs);

    // Render Table 2: KM Run Slabs
    $("#dsKmSubBadge").text(`Total: ${totalDuties}`);
    let tbodyKm = "";
    Object.keys(kmRunCounts).forEach(slab => {
        const count = kmRunCounts[slab];
        const pct = totalDuties > 0 ? ((count / totalDuties) * 100).toFixed(1) : "0.0";
        tbodyKm += `<tr>
            <td class="text-start ps-3 fw-medium">${slab}</td>
            <td class="fw-semibold">${count}</td>
            <td class="text-muted">${pct}%</td>
        </tr>`;
    });
    tbodyKm += `<tr class="table-secondary fw-bold">
        <td class="text-start ps-3">Total</td>
        <td>${totalDuties}</td>
        <td>100.0%</td>
    </tr>`;
    $("#dsKmRunTbody").html(tbodyKm);

    // Render Table 3: Zero Wheel Movement
    let tbodyZwm = `
        <tr class="table-danger-subtle">
            <td class="text-start ps-3 fw-semibold text-danger">Zero Wheel Movement (ZWM)</td>
            <td class="fw-bold text-danger">${zwmCount}</td>
            <td class="fw-bold text-danger">${zwmPct}%</td>
        </tr>
        <tr>
            <td class="text-start ps-3 fw-medium text-success">Running Duties (Non-ZWM)</td>
            <td class="fw-semibold text-success">${nonZwmCount}</td>
            <td class="text-muted">${nonZwmPct}%</td>
        </tr>
        <tr class="table-secondary fw-bold">
            <td class="text-start ps-3">Total Overall Duties</td>
            <td>${totalDuties}</td>
            <td>100.0%</td>
        </tr>
    `;
    $("#dsZwmTbody").html(tbodyZwm);

    // Render Table 4: Speed Slabs
    $("#dsSpeedSubBadge").text(`Total: ${totalDuties}`);
    let tbodySpeed = "";
    const speedSlabKeys = [
        "<= 5 KMPH",
        "05 - 08 KMPH",
        "<= 8 KMPH (ALL)",
        "08 - 10 KMPH",
        "10 - 12 KMPH",
        "12 - 15 KMPH",
        "> 15 KMPH"
    ];
    if (speedCounts["N/A"] > 0) {
        speedSlabKeys.push("N/A");
    }
    speedSlabKeys.forEach(slab => {
        const count = speedCounts[slab];
        const pct = totalDuties > 0 ? ((count / totalDuties) * 100).toFixed(1) : "0.0";
        const isSubtotal = (slab === "<= 8 KMPH (ALL)");
        const rowClass = isSubtotal ? 'table-warning fw-bold' : '';
        tbodySpeed += `<tr class="${rowClass}">
            <td class="text-start ps-3 ${isSubtotal ? 'fw-bold' : 'fw-medium'}">${slab}</td>
            <td class="fw-semibold">${count}</td>
            <td class="${isSubtotal ? 'fw-bold text-dark' : 'text-muted'}">${pct}%</td>
        </tr>`;
    });
    tbodySpeed += `<tr class="table-secondary fw-bold">
        <td class="text-start ps-3">Total</td>
        <td>${totalDuties}</td>
        <td>100.0%</td>
    </tr>`;
    $("#dsSpeedTbody").html(tbodySpeed);

    // Show section if overall analyzer is active
    if (activeAnalyzer === "overall") {
        $("#dailySummarySection").show();
    }
}

function exportDailySummaryExcel() {
    if (!overallData || overallData.length === 0) {
        alert("No data available to export summary.");
        return;
    }
    const dateStr = getDateRangeFromData(overallData);
    const wb = XLSX.utils.book_new();

    const wsData = [
        ["CMS DAILY SUMMARY REPORT"],
        [`Date: ${dateStr.replace(/_/g, " ")}`, `Generated: ${new Date().toLocaleString()}`],
        [],
        ["1. TOTAL DUTY COUNTS & DUTY HOURS WISE SLAB"],
        ["Duty Hours Slab", "Duty Count", "Percentage"]
    ];

    $("#dsDutyHoursTbody tr").each(function() {
        const cols = [];
        $(this).find("td").each(function() { cols.push($(this).text().trim()); });
        if (cols.length === 3) wsData.push(cols);
    });

    wsData.push([]);
    wsData.push(["2. KM RUN TABLE (SLAB WISE)"]);
    wsData.push(["KM Run Slab", "Duty Count", "Percentage"]);
    $("#dsKmRunTbody tr").each(function() {
        const cols = [];
        $(this).find("td").each(function() { cols.push($(this).text().trim()); });
        if (cols.length === 3) wsData.push(cols);
    });

    wsData.push([]);
    wsData.push(["3. ZERO WHEEL MOVEMENT (ZWM)"]);
    wsData.push(["Movement Category", "Duty Count", "Percentage"]);
    $("#dsZwmTbody tr").each(function() {
        const cols = [];
        $(this).find("td").each(function() { cols.push($(this).text().trim()); });
        if (cols.length === 3) wsData.push(cols);
    });

    wsData.push([]);
    wsData.push(["4. SPEED WISE SUMMARY"]);
    wsData.push(["Speed Slab", "Duty Count", "Percentage"]);
    $("#dsSpeedTbody tr").each(function() {
        const cols = [];
        $(this).find("td").each(function() { cols.push($(this).text().trim()); });
        if (cols.length === 3) wsData.push(cols);
    });

    const ws = XLSX.utils.aoa_to_sheet(wsData);
    ws['!cols'] = [{ wch: 35 }, { wch: 15 }, { wch: 15 }];
    XLSX.utils.book_append_sheet(wb, ws, "Daily Summary");

    const fileName = `Daily_Summary_${dateStr}.xlsx`;
    XLSX.writeFile(wb, fileName);
}

$("#btnExportDailySummary").on("click", exportDailySummaryExcel);

$("#btnToggleDailySummary").on("click", function() {
    $("#dailySummaryBody").slideToggle(200, function() {
        if ($("#dailySummaryBody").is(":visible")) {
            $("#iconToggleDailySummary").removeClass("bi-chevron-down").addClass("bi-chevron-up");
        } else {
            $("#iconToggleDailySummary").removeClass("bi-chevron-up").addClass("bi-chevron-down");
        }
    });
});
