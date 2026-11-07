/* ===================== HWH STATION JSON (INLINE) ===================== */
const HWH_STATIONS = new Set([
  "ABGM","ABKA","ACLE","ADST","AGAE","AJLE","ALPD","AMBG","AMP","ARNB","AZ",
  "BAA","BAHW","BBAE","BCF","BCGM","BDC","BDH","BEQ","BESY","BFZ","BGAE",
  "BGF","BGNA","BGRA","BHLA","BHP","BHR","BLAE","BLY","BMAE","BOI","BPAE",
  "BPS","BQY","BRIP","BRMA","BRMH","BRPA","BSAE","BSBR","BSLE","BSMH",
  "BTNG","BTRH","BWN","BZL","BZLE","CCRL","CDAE","CGR","CHC","CMDG","CNS",
  "CRAE","CTR","CWLE","CWT","DBP","DEA","DHAE","DHPD","DKAE","DLM","DMLE",
  "DNHL","DTAE","GBRA","GFAE","GGLE","GHLE","GKH","GMAN","GNJP","GNND",
  "GOGT","GPAE","GLPG","GRAE","GRP","GSGB","HGY","HIH","HMZ","HPL","HRNS",
  "HWH","HWHG","HYG","IPRA","JHBN","JIT","JOX","JPQ","JRAE","JRBI","JTL",
  "JVT","KAN","KCY","KGLE","KHN","KJRA","KJRM","KJU","KKAE","KLNT","KLP",
  "KMAE","KMDC","KMPR","KMRA","KNHR","KNSN","KOG","KPLE","KQLF","KQU",
  "KSHT","KTLR","KURV","KWAE","KZPE","LILUAH","LAP","LBP","LCAE","LKX",
  "LLH","LOK","MAYP","MBE","MDSE","MGAE","MYPR","MHTR","MIAN","MLV","MLYA",
  "MRR","MSAE","MTF","MUG","MUU","MYM","NBAE","NBKH","NDAE","NDIM","NGF",
  "NGX","NHT","NKL","NLSE","NMF","NRX","NSF","NXL","PBZ","PCQ","PDA","PKR",
  "PLAE","PNDI","PNE","PRAE","PRGR","PSAE","PTAE","RCD","RIS","RJG","RPH",
  "RSLR","SALE","SDI","SDLE","SHBA","SHBC","SHBL","SHE","SIU","SIZ","SKG",
  "SKIP","SLG","SMAE","SNT","SOAE","SOF","SPS","SRP","SYAE","TAK","TBAE",
  "TBB","TTT","TKP","TKPH","TLO","TLPH","TPF","TYAE","UPA","VSPR"
]);

/* ===== CREW REPORT TIME HELPERS ===== */
function tmin(t){
 t = T(t);
 if(!t) return null;
 let [h,m]=t.split(":").map(Number);
 return h*60+m;
}

function thhmm(m){
 if(m==null) return "";
 m=(m+1440)%1440;
 return String(Math.floor(m/60)).padStart(2,'0')+":"+String(m%60).padStart(2,'0');
}

function tdiff(a,b){
 if(!a||!b) return "";
 return thhmm(tmin(b)-tmin(a));
}

/* ===================== CONFIG ===================== */
const TEMPLATE_HEADERS = [
  "Sl","Crew ID","Crew Name","Train No","Loco",
  "Date","ON Time","ON Stn",
  "AS Pass\nDep Time(Before working)",
  "As Pass\nDep Stn\n(Before working)",
  "As Pass\nArr Time(Before working)",
  "As Pass\nArr Stn(Before working)",
  "CTO","Dep","CTO/DEP Stn",
  "INT STN ARR","INT STN DEP","INT Stn",
  "Arr","CMO","MOC Stn",
  "AS Pass\nDep Time(After working)",
  "As Pass\nDep Stn\n(After working)",
  "As Pass\nArr Time(After working)",
  "As Pass\nArr Stn(After working)",
  "OFF Time","Off Stn"
];

let resultData = [];
let dataTableInstance = null;

/* ===================== RENDER HEADERS ===================== */
const EXTRA_HEADERS = ["Sign Off Date","Working KM","Section","Working Section","Remarks","WORKING","ALL POSTED ROUTES (AFTER WORKING)"];

const headerRow = document.getElementById("headerRow");
[...TEMPLATE_HEADERS, ...EXTRA_HEADERS].forEach(h => {
  const th = document.createElement("th");
  th.innerText = h;
  headerRow.appendChild(th);
});

const WORKING_SECTION_RULES = [

  { name:"RPH-BWN",
    on:["RPH","PKR"],
    moc:["TPF","MLV","GHLE","SNT","BSLE","AMP","KPLE","PNE","BHP","BDH","PCQ","GKH","NRX","BPS","JTL","KAN","TIT","BWN"],
    off:["BWN","RPH","BHP","SNT"]
  },

  { name:"BWN-RPH",
    on:["BWN","BHP"],
    moc:["RPH","TPF","MLV","GHLE","SNT","BSLE","AMP","KPLE","PNE","BHP","BDH","PCQ","GKH","NRX","BPS","JTL","KAN","TIT","BWN"],
    off:["BWN","RPH","BHP","SNT"]
  },

  { name:"RPH-PKR",
    on:["RPH"],
    moc:["SDLE","NHT","CTR","MRR","BSBR","RJG","NGF","PKR","TBB","KLP","GMAN"],
    off:["PKR","RPH"]
  },

  { name:"PKR-RPH",
    on:["PKR"],
    moc:["RPH","SDLE","NHT","CTR","MRR","BSBR","RJG","NGF","PKR","TBB","KLP","GMAN"],
    off:["PKR","RPH"]
  },

  // ---- DIVISION RULE ----
  { name:"MLDT DIVISION",
    on:["GALE","MCCS","MGLE","MLDT","SBG","BHW","TDLE"],
    moc:null,
    off:["GALE","MCCS","MGLE","MLDT","SBG","BHW","TDLE"]
  },

  { name:"ASN DIVISION",
    on:["UDL","PAW"],
    moc:["MWZ","KNRI","SURI","KOX","CPLE","DUJ","PCR","DMGA","PAW","UKA","KJME","UDL"],
    off:["UDL","PAW"]
  },

  { name:"KGP DIVISION",
    on:["ADL"],
    moc:["BALT","BKNM","BKNC","MRGM","ADL"],
    off:["ADL"]
  },

  { name:"RPH-AZ",
  on:["RPH","BWN","BHP"],
  moc:["TKP","LAP","MGAE","SDI","BAA","GSGB"],
  off:["AZ","RPH","PKR"]
  },

  { name:"AZ-RPH",
  on:["RPH","BWN","BHP","AZ"],
  moc:["TKP","LAP","MGAE","SDI","BAA","GSGB"],
  off:["RPH"]
  },

  { name:"RPH-KURV",
  on:["RPH"],
  moc:["ALPD","PRGR","HRNS","SKIP","BRMA","KURV"],
  off:["RPH","KURV"]
  },

  { name:"KURV-RPH",
  on:["KURV"],
  moc:["ALPD","PRGR","HRNS","SKIP","BRMA","KURV"],
  off:["RPH"]
  },

  { name:"RPH-ADL",
  on:["RPH","BWN","BHP"],
  moc:["BALT","BKNM","BKNC","MRGM","ADL"],
  off:["ADL","DKAE","HWH","BWN","RPH"]
  },

  { name:"ADL-BWN",
  on:["ADL"],
  moc:["BALT","BKNM","BKNC","MRGM","ADL"],
  off:["DKAE","HWH","BWN","RPH"]
  },

  { name:"DKAE-ADL",
  on:["DKAE"],
  moc:["BALT","BKNM","BKNC","MRGM","ADL"],
  off:["ADL","DKAE","HWH","BWN","RPH"]
  },

  { name:"RPH-MLDT",
  on:["RPH","BWN","PKR"],
  moc:["BDLC","BHW","BKLE","NFK","CMX","KTJ","JMQ","GZM","MLDT","JRLE","AHN","SPLE","NILE","BDBP","DGLE","SXP","BPBS"],
  off:["MLDT","RPH","PKR"]
  },
  { name:"MLDT-RPH",
  on:["MLDT"],
  moc:["RPH","SDLE","NHT","CTR","MRR","BSBR","RJG","NGF","PKR","TBB","KLP","GMAN","BDLC","BDAG","TDLE","NFK","CMX","KTJ","JMQ","GZM","MLDT"],
  off:["RPH","PKR","BWN","BHP","SNT","NHT"]
  },

  { name:"RPH-TDLE",
  on:["RPH","BWN","BHP","PKR"],
  moc:["BDLC","BDAG","TDLE"],
  off:["TDLE","RPH","PKR"]
  },

  { name:"TDLE-RPH",
  on:["TDLE"],
  moc:["RPH","SDLE","NHT","CTR","MRR","BSBR","RJG","NGF","PKR","TBB","KLP","GMAN","BDLC","BDAG","TDLE"],
  off:["RPH","PKR","BWN","BHP","SNT","NHT"]
  },

  { name:"RPH-DUMK",
  on:["RPH","BWN","BHP","PKR"],
  moc:["RPH","ALPD","PRGR","HRNS","SKIP","BRMA","KURV","DUMK"],
  off:["DUMK"]
  },

  { name:"DUMK-RPH",
  on:["DUMK"],
  moc:["RPH","ALPD","PRGR","HRNS","SKIP","BRMA","KURV"],
  off:["KURV","RPH","PKR","BWN","DUMK"]
  },

  { name:"RPH-UDL",
  on:["RPH","BHP","PKR"],
  moc:["MWZ","KNRI","SURI","KOX","CPLE","DUJ","PCR","DMGA","PAW","UKA","KJME","UDL"],
  off:["UDL","PAW","RPH","BWN"]
  },

  { name:"RPH-SBG",
  on:["RPH","BWN","BHP","PKR"],
  moc:["BDLC","BHW","BKLE","DDX","TPH","KXE","TLJ","KPTO","MJP","SLJ","SBG"],
  off:["SBG","RPH","PKR"]
  },

  { name:"SBG-RPH",
  on:["SBG","BHW"],
  moc:["RPH","SDLE","NHT","CTR","MRR","BSBR","RJG","NGF","PKR","TBB","KLP","GMAN","BDLC","BHW","BKLE","DDX","TPH","KXE","TLJ","KPTO","MJP","SLJ","SBG"],
  off:["RPH","PKR","BWN"]
  },

  { name:"RPH-BGP",
  on:["RPH","BWN","BHP","PKR"],
  moc:["MPUR","BRPS","NNHT","KUMT","HSDA","KADL","DANE","PETA","MDLE","MDVB","PJLE","BHLE","PNSA","PADH","DWLE","BGP"],
  off:["BGP"]
  },

  { name:"BGP-RPH",
  on:["BGP"],
  moc:["RPH","ALPD","PRGR","HRNS","SKIP","BRMA","KURV","DUMK","MPUR","BRPS","NNHT","KUMT","HSDA","KADL","DANE","PETA","MDLE","MDVB","PJLE","BHLE","PNSA","PADH","DWLE","BGP"],
  off:["KURV","RPH","PKR"]
  },

  { name:"RPH-MCCS",
  on:["RPH","BWN","PKR"],
  moc:["PRDG","MPLR","MPLE","NWMS","MGLE","GALE"],
  off:["GALE","MCCS"]
  },

  { name:"MCCS-RPH",
  on:["GALE","MCCS"],
  moc:["RPH","SDLE","NHT","TKP","LAP","MGAE","SDI","BAA","GSGB","PRDG","MPLR","MPLE","NWMS","MGLE"],
  off:["AZ","RPH","PKR","BWN","NHT"]
  },

  { name:"RPH-MGLE",
  on:["RPH","BWN","PKR"],
  moc:["PRDG","MPLR","MPLE","NWMS","MGLE"],
  off:["MGLE"]
  },

  { name:"MGLE-RPH",
  on:["MGLE"],
  moc:["RPH","SDLE","NHT","TKP","LAP","MGAE","SDI","BAA","GSGB","PRDG","MPLR","MPLE","NWMS","MGLE"],
  off:["AZ","RPH","PKR","BWN","NHT"]
  }

];

/* ===================== HELPERS ===================== */
function clean(k){ return k.toLowerCase().replace(/[^a-z0-9]/g,""); }

function findValue(row, aliases){
  const keys = Object.keys(row||{});
  for (let a of aliases){
    const f = keys.find(k => clean(k) === clean(a));
    if (f && row[f] !== "") return row[f];
  }
  return "";
}

function getVal(obj, label){
  const key = Object.keys(obj).find(k => clean(k) === clean(label));
  return key ? obj[key] : "";
}

function extractTime(v){
  if(!v) return "";
  const m = v.toString().match(/(\d{1,2}):(\d{1,2})/);
  return m ? m[1].padStart(2,"0")+":"+m[2].padStart(2,"0") : "";
}

function parseSignOnDate(v){
  if(!v) return {date:"",time:""};
  const s=v.toString().trim().replace(/\//g,"-").replace(/\./g,"-");
  const p=s.split(" ");
  const d=p[0].split("-");
  const t=p[1]||"";
  let date="";
  if(d.length===3){
    const yy=d[2].length===4?d[2].slice(-2):d[2];
    date=`${d[0].padStart(2,"0")}-${d[1].padStart(2,"0")}-${yy}`;
  }
  return {date,time:extractTime(t)};
}

function inHWH(stn){
  return HWH_STATIONS.has((stn||"").toUpperCase().trim());
}

function mapINTByRules(out){

  const onStn  = S(out["ON Stn"]);
  const ctoStn = S(out["CTO/DEP Stn"]);
  const mocStn = S(out["MOC Stn"]);
  const offStn = S(out["Off Stn"]);
  const train  = S(out["Train No"]);

  const stations = [onStn, ctoStn, mocStn, offStn];

  const AZ_EXCEPTION_LIST = ["MLDT", "GALE", "MGLE", "SBG"];

  // ===== EXCEPTION RULE =====
  if (
    ctoStn === "AZ" &&
    (AZ_EXCEPTION_LIST.includes(mocStn) ||
     AZ_EXCEPTION_LIST.includes(offStn))
  ) {
    return "PRDG";
  }

  // ===== NORMAL RULES =====
  for (let s of stations) {

    if (["MGLE","GALE"].includes(s)) return "GSGB";
    if (s==="ADL") return "BTNG";
    if (["TDLE","SBG","CLG"].includes(s)) return "GMAN";
    if (["UDL","PAW"].includes(s)) return "SNT";
    if (["DUMK","BGP"].includes(s)) return "DUMK";

    if (s==="MLDT"){
      return train.includes("GSGB") ? "GSGB" : "GMAN";
    }
  }

  return "";
}
/* ===== ULTRA SAFE VALUE HANDLER ===== */
function S(v){
  if(v === null || v === undefined) return "";
  return String(v).trim().toUpperCase();
}

function T(v){
  if(!v) return "";
  const s = String(v);
  const m = s.match(/(\d{1,2}):(\d{1,2})/);
  return m ? m[1].padStart(2,"0")+":"+m[2].padStart(2,"0") : "";
}

/* ===================== SUBMIT ===================== */
function submitSource(){
  resultData=[];
  document.querySelector("#resultTable tbody").innerHTML="";

  if(dataTableInstance){
    dataTableInstance.destroy();
    dataTableInstance = null;
  }

  const f=document.getElementById("sourceFile").files[0];
  if(!f){ alert("Upload file"); return; }

  const r=new FileReader();
  r.onload=e=>{
    const wb=XLSX.read(new Uint8Array(e.target.result),{type:"array"});
    const sh=wb.Sheets[wb.SheetNames[0]];
    const aoa=XLSX.utils.sheet_to_json(sh,{header:1,defval:""});

    let hi=-1;
    for(let i=0;i<aoa.length;i++){
      if(clean(aoa[i][0]||"")==="sno"){ hi=i; break; }
    }
    if(hi===-1){ alert("S.No header not found"); return; }

    const headers=aoa[hi];
    const rows=aoa.slice(hi+1).map(r=>{
      const o={};
      headers.forEach((h,i)=>{ if(h) o[h]=r[i]; });
      return o;
    });

    generateResult(rows);
    
    // Extract unique routes
    let allRoutes = new Set();
    resultData.forEach(out => {
        let routesStr = out["ALL POSTED ROUTES (AFTER WORKING)"];
        if (routesStr) {
            routesStr.split("\n").forEach(r => {
                let rc = r.replace(/,$/, "").trim();
                if(rc) allRoutes.add(rc);
            });
        }
    });
    
    if (allRoutes.size > 0) {
        fetch("/tools/long-hours-analysis/save-routes", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({routes: Array.from(allRoutes)})
        })
        .then(res => res.json())
        .then(data => {
            let map = data.route_map || {};
            resultData.forEach(out => {
               let routesStr = out["ALL POSTED ROUTES (AFTER WORKING)"];
               if (routesStr) {
                   let updated = routesStr.split("\n").map(r => {
                       let rc = r.replace(/,$/, "").trim();
                       let c = r.endsWith(",") ? "," : "";
                       if (map[rc]) {
                           return `${rc}(${map[rc]})${c}`;
                       }
                       return r;
                   });
                   out["ALL POSTED ROUTES (AFTER WORKING)"] = updated.join("\n");
               }
            });
            renderTable();
            initDataTable();
        })
        .catch(err => {
            console.error(err);
            renderTable();
            initDataTable();
        });
    } else {
        renderTable();
        initDataTable();
    }
  };
  r.readAsArrayBuffer(f);
}

/* ===================== CORE LOGIC ===================== */
function generateResult(sourceRows){
  const groups={};
  sourceRows.forEach(r=>{
    const sn=r[Object.keys(r)[0]];
    if(!sn) return;
    if(!groups[sn]) groups[sn]=[];
    groups[sn].push(r);
  });

  Object.keys(groups).forEach(sn=>{
    const rows=groups[sn];
    const first=rows[0];
    const out={};
    TEMPLATE_HEADERS.forEach(h=>out[h]="");

    const WR_TYPES=["WR","LR","KH","YR","WT"];
    const isWR=r=>WR_TYPES.includes(findValue(r,["DUTY TYPE"]));
    const isSP=r=>findValue(r,["DUTY TYPE"])==="SP";
    const noCTO=r=>["YR","WT"].includes(findValue(r,["DUTY TYPE"]));

    // PART 1
    out["Sl"]=sn;
    out["Crew ID"]=findValue(first,["CREW ID"]);
    out["Crew Name"]=findValue(first,["NAME"]);
    const tr=rows.find(r=>isWR(r))||rows.find(r=>findValue(r,["TRAIN NO"]));
    out["Train No"]=tr?findValue(tr,["TRAIN NO"]):"";
    const lr=rows.find(r=>findValue(r,["LOCO NO"]));
    out["Loco"]=lr?findValue(lr,["LOCO NO"]):"";

    // PART 2
    const p=parseSignOnDate(findValue(first,["SIGNON DATE"]));
    out["Date"]=p.date;
    out["ON Time"]=p.time;
    out["ON Stn"]=findValue(first,["SIGNON STTN"]);

    // PART 3
    const wrIdx=rows.findIndex(r=>isWR(r));
    const spBefore=rows.slice(0,wrIdx===-1?rows.length:wrIdx).filter(isSP);
    if(findValue(first,["DUTY TYPE"])!=="WR" && spBefore.length){
      out["AS Pass\nDep Time(Before working)"]=extractTime(findValue(spBefore[0],["DEPARTURE"]));
      out["As Pass\nDep Stn\n(Before working)"]=findValue(spBefore[0],["SIGNON STTN"]);
      out["As Pass\nArr Time(Before working)"]=extractTime(findValue(spBefore.at(-1),["ARRIVAL"]));
      out["As Pass\nArr Stn(Before working)"]=findValue(spBefore.at(-1),["SIGNOFF STTN"]);
    }

    // PART 4
    const wrs = rows.filter(isWR);

    if (wrs.length) {
      const fw = wrs[0];              // first WR/LR/KH/YR/WT
      const lw = wrs[wrs.length-1]; // last WR/LR/KH/YR/WT

      // Start working
      if (!noCTO(fw)) {
        out["CTO"] = extractTime(findValue(fw, ["CTO"]));
      }

      out["Dep"] = extractTime(findValue(fw, ["DEPARTURE"]));
      out["CTO/DEP Stn"] = findValue(fw, ["SIGNON STTN"]);

      // End working (even if same row)
      out["Arr"] = extractTime(findValue(lw, ["ARRIVAL"]));

      if (!noCTO(lw)) {
        out["CMO"] = extractTime(findValue(lw, ["CMO"]));
      }

      out["MOC Stn"] = findValue(lw, ["SIGNOFF STTN"]);
    }

    // PART 5
    const lastWR=rows.map(r=>isWR(r)).lastIndexOf(true);
    const spAfter=lastWR!==-1?rows.slice(lastWR+1).filter(isSP):[];
    if(spAfter.length && rows.length>1){
      out["AS Pass\nDep Time(After working)"]=extractTime(findValue(spAfter[0],["DEPARTURE"]));
      out["As Pass\nDep Stn\n(After working)"]=findValue(spAfter[0],["SIGNON STTN"]);
      out["As Pass\nArr Time(After working)"]=extractTime(findValue(spAfter.at(-1),["ARRIVAL"]));
      out["As Pass\nArr Stn(After working)"]=findValue(spAfter.at(-1),["SIGNOFF STTN"]);
    }

    // PART 6
    const last=rows.at(-1);
    out["OFF Time"]=extractTime(findValue(last,["SIGNOFF DATE"]));
    out["Off Stn"]=findValue(last,["SIGNOFF STTN"]);

    // ===================== NEW INT STN LOGIC =====================

    // RULE 1: If BOTH source stations are in HWH division
    const signOnSrc = findValue(first, ["SIGNON STTN"]);
    const signOffSrc = findValue(rows.at(-1), ["SIGNOFF STTN"]);

    if (inHWH(signOnSrc) && inHWH(signOffSrc)) {
      out["INT STN ARR"] = "00:00";
      out["INT STN DEP"] = "00:00";
      out["INT Stn"] = "NA";
    } else {
      // RULE 2: Special station mapping
      const mapped = mapINTByRules(out);
      if (mapped) {
        out["INT Stn"] = mapped;
      }
    }

    out.__noWR = !wrs.length;
    out.__rows = rows;
    resultData.push(out);
  });
}

/* ===================== RENDER ===================== */
function renderTable(){
  const tb=document.querySelector("#resultTable tbody");
  tb.innerHTML="";
  resultData.forEach(r=>{
    const tr=document.createElement("tr");
    if(r.__noWR){
      tr.classList.add("no-wr-row");
      tr.title="No WR/LR/KH/YR/WT duty found";
    }
    applyExtraColumns(r);   // <---- add calculation before showing

  [...TEMPLATE_HEADERS, ...EXTRA_HEADERS].forEach(h=>{
    const td=document.createElement("td");
    td.contentEditable=true;
    td.className="editable";
    td.innerText=r[h]||"";
    td.oninput=()=>r[h]=td.innerText.trim();
    tr.appendChild(td);
  });
    tb.appendChild(tr);
  });
}

/* ===================== DATATABLE ===================== */
function initDataTable(){

  if ($.fn.DataTable.isDataTable('#resultTable')) {
      $('#resultTable').DataTable().destroy();
  }

  dataTableInstance = $('#resultTable').DataTable({
      pageLength:10,
      lengthMenu:[10,25,50,100,500],
      scrollX:true,
      order:[],
      language:{
          search:"🔍 Search:",
          lengthMenu:"Show _MENU_ rows",
          info:"Showing _START_ to _END_ of _TOTAL_ rows"
      }
  });
}

/* ===================== DOWNLOAD ===================== */
function downloadResultFinal(){

  if(!resultData.length){ alert("No data"); return; }

  const headers=[...TEMPLATE_HEADERS];

  if(optSignOff.checked) headers.push("Sign Off Date");
  if(optKM.checked) headers.push("Working KM");
  if(optSection.checked) headers.push("Section");
  if(optWorkingSection.checked) headers.push("Working Section");
  if(optRemarks.checked) headers.push("Remarks");
  if(document.getElementById('optWorking').checked) headers.push("WORKING");
  if(document.getElementById('optPostedRoutes').checked) headers.push("ALL POSTED ROUTES (AFTER WORKING)");

  resultData.forEach(r=>applyExtraColumns(r));

  const ws=XLSX.utils.aoa_to_sheet([
    headers,
    ...resultData.map(r=>headers.map(h=>r[h]||""))
  ]);

  const wb=XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb,ws,"RESULT");
  XLSX.writeFile(wb,"RESULT.xlsx");

}
function applyExtraColumns(out){

  const rows = out.__rows;
  if(!rows) return;

  const first = rows[0];
  const last  = rows.at(-1);

  // SIGN OFF DATE
  let raw = findValue(last,["SIGNOFF DATE"]);
  if(raw){
    const d = raw.toString().split(" ")[0]
      .replace(/\//g,"-").replace(/\./g,"-").split("-");
    if(d.length===3)
      out["Sign Off Date"] = d[0].padStart(2,"0")+"-"+d[1].padStart(2,"0")+"-"+d[2];
  }

  // WORKING KM
  let km=0;
  rows.forEach(r=>{
    const duty=findValue(r,["DUTY TYPE"]);
    if(["WR","YR","KH","LR"].includes(duty)){
      const v=parseFloat(findValue(r,["ROUTE KM","KM","DISTANCE","S"]));
      if(!isNaN(v)) km+=v;
    }
  });
  out["Working KM"]=km?km.toFixed(2):"";

  // SECTION
  const on  = findValue(first,["SIGNON STTN"]);
  const off = findValue(last,["SIGNOFF STTN"]);

  const inOn  = inHWH(on);
  const inOff = inHWH(off);

  if(inOn && inOff) out["Section"]="DIV";
  else if(inOn && !inOff) out["Section"]="HWH-OTH";
  else if(!inOn && inOff) out["Section"]="OTH-HWH";
  else out["Section"]="OTH DIV";

  // ===== REMARKS AUTO GENERATE =====
  const pdd   = out["AS Pass\nDep Time(Before working)"] ? "00:00" : tdiff(out["ON Time"],out["Dep"]);
  const wheel = tdiff(out["Dep"],out["Arr"]);
  const pad   = out["AS Pass\nDep Time(After working)"] ? "00:00" : tdiff(out["Arr"],out["OFF Time"]);

  // placeholder (logic later)
  if(!out["Working Section"])
  out["Working Section"]="";

  out["Remarks"] = buildRemarks(out,pdd,pad,wheel).replace(/<br>/g,"\n");
  out["Working Section"] = detectWorkingSection(
  out["ON Stn"],     // column H
  out["MOC Stn"],    // column U
  out["Off Stn"]     // column AA
  );
  
  let workings = [];
  let routes = [];
  rows.forEach(r => {
    let s_on = findValue(r, ["SIGNON STTN", "ON STN"]);
    let s_off = findValue(r, ["SIGNOFF STTN", "OFF STN"]);
    let dt = findValue(r, ["DUTY TYPE", "DUTY TYPE (N)"]);
    let route = findValue(r, ["ROUTE NAME", "ROUTENAME"]);
    
    let sectionStr = "";
    if (s_on && s_off) sectionStr = `${s_on}-${s_off}`;
    else if (s_on) sectionStr = s_on;
    else if (s_off) sectionStr = s_off;
    
    let workStr = "";
    if (sectionStr && dt) workStr = `${sectionStr} - ${dt}`;
    else if (sectionStr) workStr = sectionStr;
    else if (dt) workStr = dt;
    
    if (workStr) workings.push(workStr);
    
    if (route) {
        let routeStr = route.toString().replace(/,/g, ",\n");
        let routeLines = routeStr.split("\n").map(s=>s.trim()).filter(s=>s);
        routes.push(...routeLines);
    }
  });
  
  for(let i=0; i<routes.length; i++) {
      if (i < routes.length - 1 && !routes[i].endsWith(",")) routes[i] += ",";
      else if (i === routes.length - 1 && routes[i].endsWith(",")) routes[i] = routes[i].slice(0, -1);
  }
  
  out["WORKING"] = workings.join(",\n");
  // Only set ALL POSTED ROUTES if it hasn't been set yet (with IDs)
  if (!out["ALL POSTED ROUTES (AFTER WORKING)"] || !out["ALL POSTED ROUTES (AFTER WORKING)"].includes("(")) {
      out["ALL POSTED ROUTES (AFTER WORKING)"] = routes.join("\n");
  }
  
}

/* ================= CREW DUTY REPORT ================= */

function generateCrewReport(){

 if(!resultData.length){
   alert("Generate table first");
   return;
 }

 document.getElementById("crewReportContainer").style.display="block";

 const headers=[
 "SL No.","Date","Train No./Loco No.","Name of crew/HQ",
 "Sign on Time","Sign on Place","Departure (Train working)",
 "Arrival (Train working)","Sign off Time","Sign off Place",
 "PDD","Wheel movement","PAD","Total duty hours(Hrs)",
 "Interchange point & Time","Remarks"
 ];

 const thead=document.querySelector("#crewReportTable thead");
 thead.innerHTML="<tr>"+headers.map(h=>`<th>${h}</th>`).join("")+"</tr>";

 renderCrewRows();
}


function renderCrewRows(){

 const tbody=document.querySelector("#crewReportTable tbody");
 tbody.innerHTML="";

 resultData.forEach((r,i)=>{

  const pdd   = r["AS Pass\nDep Time(Before working)"] ? "00:00" : tdiff(r["ON Time"],r["Dep"]);
  const wheel = tdiff(r["Dep"],r["Arr"]);
  const pad   = r["AS Pass\nDep Time(After working)"] ? "00:00" : tdiff(r["Arr"],r["OFF Time"]);
  const total = tdiff(r["ON Time"],r["OFF Time"]);

  let interchange = "";

  if(r["Section"]==="DIV"){
  interchange="NA";
  } else {
  interchange = r["INT Stn"] ? `${r["INT Stn"]} / (${tdiff(r["INT STN ARR"],r["INT STN DEP"])})`
      : "";
  }

  const remarks = buildRemarks(r,pdd,pad,wheel).replace(/<br>/g,"\n");

  const rowData = [
    i+1,
    r["Date"]||"",
    `${r["Train No"]||""}/${r["Loco"]||""}`,
    r["Crew Name"]||"",
    r["ON Time"]||"",
    r["ON Stn"]||"",
    r["Dep"]||"",
    r["Arr"]||"",
    r["OFF Time"]||"",
    r["Off Stn"]||"",
    pdd,
    wheel,
    pad,
    total,
    interchange,
    remarks
  ];

  const tr=document.createElement("tr");

  rowData.forEach((val,ci)=>{
    const td=document.createElement("td");
    td.innerText=val;

    // SL no not editable
    if(ci!==0){
      td.contentEditable=true;
      td.classList.add("editable");

      td.oninput=()=>{
        // only remarks edit will store
        if(ci===15){
          r.__manualRemarks = td.innerText;
        }
      };
    }

    tr.appendChild(td);
  });

  tbody.appendChild(tr);
 });
}

function buildRemarks(r,pdd,pad,wheel){

  let txt="";

  const onStn  = getVal(r,"ON Stn");
  const onTime = getVal(r,"ON Time");
  const dep    = getVal(r,"Dep");
  const arr    = getVal(r,"Arr");
  const offT   = getVal(r,"OFF Time");
  const offStn = getVal(r,"Off Stn");

  const cto    = getVal(r,"CTO");
  const ctoStn = getVal(r,"CTO/DEP Stn");
  const moc    = getVal(r,"CMO");
  const mocStn = getVal(r,"MOC Stn");

  const passDepB = getVal(r,"As Pass Dep Time(Before working)");
  const passArrB = getVal(r,"As Pass Arr Time(Before working)");
  const passArrStnB = getVal(r,"As Pass Arr Stn(Before working)");

  const passDepA = getVal(r,"As Pass Dep Time(After working)");
  const passArrA = getVal(r,"As Pass Arr Time(After working)");
  const passArrStnA = getVal(r,"As Pass Arr Stn(After working)");

  txt+=`Train work ${onStn} - ${mocStn||offStn}\n\n`;

  txt+=`S/ON ${onStn} ${onTime} hrs\n`;

  if(passDepB)
  txt+=`As Pass ${onStn} Dep ${passDepB} hrs & ${passArrStnB} Arr ${passArrB} hrs\n`;

  if(cto)
  txt+=`CTO ${ctoStn} ${cto} hrs\n`;

  txt+=`DEP ${ctoStn} ${dep} hrs\n`;

  if(pdd!="00:00") txt+=`\nPDD = ${pdd} hrs\n`;

  /* ===== Wheel movement HERE ===== */
  if(wheel) txt+=`\nWheel movement = ${wheel} hrs\n`;

  txt+=`\nARR ${mocStn} ${arr} hrs\n`;

  if(moc)
  txt+=`MOC ${mocStn} ${moc} hrs\n`;

  if(passDepA)
  txt+=`As Pass ${mocStn} Dep ${passDepA} hrs ${passArrStnA} Arr ${passArrA} hrs\n`;

  if(pad!="00:00") txt+=`\nPAD = ${pad} hrs\n`;

  txt+=`\nS/OFF ${offStn} ${offT} hrs`;

  if(r.__manualRemarks) return r.__manualRemarks.replace(/\n/g,"<br>");
  return txt.replace(/\n/g,"<br>");
}

/* ================= CREW REPORT DOWNLOAD ================= */

function downloadCrewReport(){

 if(!resultData.length){
   alert("Generate Crew Report first");
   return;
 }

 const headers=[
 "SL No.","Date","Train No./Loco No.","Name of crew/HQ",
 "Sign on Time","Sign on Place","Departure (Train working)",
 "Arrival (Train working)","Sign off Time","Sign off Place",
 "PDD","Wheel movement","PAD","Total duty hours(Hrs)",
 "Interchange point & Time","Remarks"
 ];

 const data = resultData.map((r,i)=>{

  const pdd   = r["AS Pass\nDep Time(Before working)"] ? "00:00" : tdiff(r["ON Time"],r["Dep"]);
  const wheel = tdiff(r["Dep"],r["Arr"]);
  const pad   = r["AS Pass\nDep Time(After working)"] ? "00:00" : tdiff(r["Arr"],r["OFF Time"]);
  const total = tdiff(r["ON Time"],r["OFF Time"]);

  let interchange="";

  if(r["Section"]==="DIV"){
    interchange="NA";
  }else{
    interchange = r["INT Stn"] ? `${r["INT Stn"]} / (${tdiff(r["INT STN ARR"],r["INT STN DEP"])})`
    : "";
  }

  const remarks = buildRemarks(r,pdd,pad,wheel).replace(/<br>/g,"\n");

  return [
   i+1,
   r["Date"]||"",
   `${r["Train No"]||""}/${r["Loco"]||""}`,
   r["Crew Name"]||"",
   r["ON Time"]||"",
   r["ON Stn"]||"",
   r["Dep"]||"",
   r["Arr"]||"",
   r["OFF Time"]||"",
   r["Off Stn"]||"",
   pdd,
   wheel,
   pad,
   total,
   interchange,
   remarks
  ];
 });

 const ws=XLSX.utils.aoa_to_sheet([headers,...data]);

 /* column width railway style */
 ws["!cols"]=[
 {wch:6},{wch:10},{wch:18},{wch:22},
 {wch:10},{wch:12},{wch:12},{wch:12},
 {wch:12},{wch:12},{wch:10},{wch:14},
 {wch:10},{wch:16},{wch:20},{wch:80}
 ];

 const wb=XLSX.utils.book_new();
 XLSX.utils.book_append_sheet(wb,ws,"CREW REPORT");
 XLSX.writeFile(wb,"Crew_Duty_Report.xlsx");
}

function detectWorkingSection(on,moc,off){

  on = (on||"").trim().toUpperCase();
  moc = (moc||"").trim().toUpperCase();
  off = (off||"").trim().toUpperCase();

  for(const r of WORKING_SECTION_RULES){

    if(!r.on.includes(on)) continue;

    if(r.moc && !r.moc.includes(moc)) continue;

    if(!r.off.includes(off)) continue;

    return r.name;
  }

  return "";
}