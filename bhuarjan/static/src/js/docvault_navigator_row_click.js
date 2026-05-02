/** @odoo-module **/

// Doc Vault Navigator: clicking anywhere on a section row triggers the
// hidden eye-icon button (action_select_document), which lets Odoo's own
// button/action framework handle the form refresh — ensuring the PDF viewer
// re-renders with the selected document.

document.addEventListener("click", (ev) => {
    const target = ev.target;
    if (!target || !(target instanceof Element)) return;

    const row = target.closest(
        ".o_docvault_left_panel .o_list_view .o_data_row"
    );
    if (!row) return;

    // If the eye-button itself was clicked, let it propagate naturally.
    if (target.closest(".o_docvault_row_view_btn")) return;

    const viewBtn = row.querySelector(".o_docvault_row_view_btn");
    if (viewBtn) {
        ev.preventDefault();
        ev.stopPropagation();
        viewBtn.click();
    }
}, true);
