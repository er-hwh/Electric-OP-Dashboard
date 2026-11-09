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

    // Prevent Bootstrap modal blinking / focus loops by ensuring all modals are direct children of body
    function relocateModalsToBody() {
        document.querySelectorAll('.modal').forEach(function(modalEl) {
            if (modalEl.parentElement !== document.body) {
                document.body.appendChild(modalEl);
            }
        });
    }
    relocateModalsToBody();
    document.addEventListener('show.bs.modal', function(e) {
        if (e.target && e.target.parentElement !== document.body) {
            document.body.appendChild(e.target);
        }
    });

    // Initialize DataTables with 10 records default and clean pagination
    function initDataTables() {
        if (typeof $ !== 'undefined' && $.fn.DataTable) {
            $('.datatable, .table-paginated').each(function() {
                if (!$.fn.DataTable.isDataTable(this)) {
                    $(this).DataTable({
                        pageLength: 10,
                        lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "All"]],
                        language: {
                            search: "_INPUT_",
                            searchPlaceholder: "Search table records...",
                            lengthMenu: "Show _MENU_ records",
                            info: "Showing _START_ to _END_ of _TOTAL_ entries",
                            paginate: {
                                previous: '<i class="fa-solid fa-chevron-left"></i>',
                                next: '<i class="fa-solid fa-chevron-right"></i>'
                            }
                        },
                        responsive: false,
                        autoWidth: false,
                        order: []
                    });
                }
            });
        }
    }
    initDataTables();

});