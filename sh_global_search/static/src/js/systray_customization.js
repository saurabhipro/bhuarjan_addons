/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

// Hide unwanted systray items
const HIDDEN_SYSTRAY_ITEMS = [
    "web.debug_mode_menu",      // Debug mode
    "note.systray",             // Notes taker
    "mail.systray",             // Mail notifications (if you want to hide)
    "web_enterprise.systray",   // Enterprise features
    "web_enterprise.enterprise_systray", // Enterprise systray
];

// Remove hidden systray items
HIDDEN_SYSTRAY_ITEMS.forEach(itemKey => {
    try {
        registry.category("systray").remove(itemKey);
    } catch (e) {
        // Item might not exist, ignore error
        console.debug(`Systray item ${itemKey} not found to remove`);
    }
});

// Patch the systray to reorder items
patch(registry.category("systray"), {
    add(key, item, options = {}) {
        // Set higher sequence for GlobalSearch to appear after user menu
        if (key === "GlobalSearch") {
            options.sequence = 50; // Higher than default but lower than user menu
        }
        return this._super(key, item, options);
    }
});

// Additional CSS to hide specific elements if they still appear
const style = document.createElement('style');
style.textContent = `
    /* Hide debug mode button */
    .o_debug_manager,
    .o_debug_mode,
    [data-key="web.debug_mode_menu"] {
        display: none !important;
    }
    
    /* Hide notes taker */
    .o_note_systray,
    [data-key="note.systray"] {
        display: none !important;
    }
    
    /* Hide enterprise systray items */
    .o_enterprise_systray,
    [data-key*="enterprise"] {
        display: none !important;
    }
    
    /* Ensure search menu appears in correct position */
    .o_menu_systray .o_systray_item[data-key="GlobalSearch"] {
        order: 1;
    }
`;
document.head.appendChild(style);
