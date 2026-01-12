/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { WebClient } from "@web/webclient/webclient";
import { onMounted } from "@odoo/owl";

patch(WebClient.prototype, {
    setup() {
        super.setup();
        
        onMounted(() => {
            // Make logo clickable to load dashboard
            this.makeLogoClickable();
        });
    },

    makeLogoClickable() {
        // Wait for DOM to be ready
        setTimeout(() => {
            // Find the logo/brand element in the menu
            const logoElements = document.querySelectorAll('.o_main_navbar .navbar-brand, .o_main_navbar .o_menu_brand, .o_main_navbar [data-menu="root"]');
            
            logoElements.forEach(logo => {
                if (!logo.hasAttribute('data-dashboard-click')) {
                    logo.setAttribute('data-dashboard-click', 'true');
                    logo.style.cursor = 'pointer';
                    logo.addEventListener('click', (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        // Use role-based dashboard action that checks user role on server
                        // The server will route to the correct dashboard based on user's role and groups
                        if (this.env.services.action) {
                            this.env.services.action.doAction('bhuarjan.action_role_based_dashboard', {
                                clearBreadcrumbs: true,
                            });
                        } else {
                            // Fallback to hash if service not found
                            window.location.href = '/web#action=bhuarjan.action_role_based_dashboard';
                        }
                    });
                }
            });
        }, 1500);
    },
});
