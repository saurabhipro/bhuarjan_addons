/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onMounted, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class RoleBasedDashboard extends Component {
    static template = xml`<div class="o_loading" style="text-align: center; padding: 50px;"><div class="spinner-border" role="status"><span class="sr-only">Loading...</span></div></div>`;
    
    setup() {
        this.action = useService("action");
        
        // Redirect immediately without blocking - default to SDM dashboard
        // Admin users will see admin dashboard via menu visibility rules
        onMounted(async () => {
            // Default to SDM dashboard for all users
            // Admin users have a separate menu item that shows admin dashboard
            await this.action.doAction({
                type: "ir.actions.client",
                tag: "bhuarjan.sdm_dashboard_tag",
            });
        });
    }
}

// Register the action
registry.category("actions").add(
    "bhuarjan.role_based_dashboard",
    RoleBasedDashboard
);

