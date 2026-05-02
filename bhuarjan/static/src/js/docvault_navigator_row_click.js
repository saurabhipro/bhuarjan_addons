/** @odoo-module **/

// Lightweight bridge: when a user clicks anywhere on a Doc Vault Navigator
// section row (other than form-action buttons), the row's primary "View"
// button is triggered so the PDF renders in the right panel without any
// popup.  This avoids overriding the list view but still provides the
// "click anywhere = render PDF" UX the user requested.

document.addEventListener("click", (ev) => {
    const target = ev.target;
    if (!target || !(target instanceof Element)) {
        return;
    }
    const row = target.closest(".o_docvault_left_panel .o_list_view .o_data_row");
    if (!row) {
        return;
    }
    // Don't double-trigger when the explicit View button itself was clicked.
    if (target.closest("button")) {
        return;
    }
    const viewBtn = row.querySelector("button.btn-primary");
    if (viewBtn) {
        ev.preventDefault();
        ev.stopPropagation();
        viewBtn.click();
    }
}, true);
