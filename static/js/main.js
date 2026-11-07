// Live Indian Railways Standard Time Clock
function updateRailwayClock() {
    const clockEl = document.getElementById('railway-clock');
    if (!clockEl) return;
    
    const now = new Date();
    // Options for Indian Standard Time
    const dateOptions = { day: '2-digit', month: 'short', year: 'numeric' };
    const dateStr = now.toLocaleDateString('en-GB', dateOptions).replace(/ /g, '-');
    
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    
    clockEl.textContent = `IST: ${dateStr} | ${hours}:${minutes}:${seconds}`;
}

document.addEventListener('DOMContentLoaded', function() {
    updateRailwayClock();
    setInterval(updateRailwayClock, 1000);

    // Auto-dismiss standard alerts after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert-dismissible');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 6000);
});
