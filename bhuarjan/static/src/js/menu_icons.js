/** @odoo-module **/

import { registry } from "@odoo/web";
import { Menu } from "@web/webclient/menu/menu";
import { patch } from "@web/core/utils/patch";

patch(Menu.prototype, "bhuarjan.menu_icons", {
    _updateMenuIcons() {
        // Add icons to menu items based on their IDs
        const iconMap = {
            'menu_bhu_surveys': 'fa-bar-chart',
            'menu_bhu_survey': 'fa-file-text',
            'menu_bhu_master': 'fa-database',
            'menu_bhu_department': 'fa-building',
            'menu_bhu_project': 'fa-folder',
            'menu_bhu_district': 'fa-map',
            'menu_bhu_sub_division': 'fa-map-marker',
            'menu_bhu_tehsil': 'fa-building',
            'menu_bhu_circle': 'fa-circle',
            'menu_bhu_village': 'fa-building',
            'menu_bhu_landowner': 'fa-user',
            'menu_bhu_process': 'fa-cogs',
            'menu_bhu_stage2_section4': 'fa-bullhorn',
            'menu_bhu_stage3_section4_1': 'fa-users',
            'menu_bhu_stage4_section7': 'fa-users',
            'menu_bhu_stage5_section8': 'fa-check-circle',
            'menu_bhu_stage6_section11': 'fa-bell',
            'menu_bhu_stage7_section15': 'fa-exclamation-triangle',
            'menu_bhu_stage8_section19': 'fa-trophy',
            'menu_bhu_stage9_section21': 'fa-file-text',
            'menu_bhu_stage9_section23': 'fa-file-text',
            'menu_bhu_users': 'fa-users'
        };

        // Add icons to menu items
        Object.entries(iconMap).forEach(([menuId, iconClass]) => {
            const menuItem = this.el.querySelector(`.o_menu_item[data-menu-xmlid*="${menuId}"]`);
            if (menuItem && !menuItem.querySelector('.fa')) {
                const icon = document.createElement('i');
                icon.className = `fa ${iconClass} menu-icon`;
                menuItem.prepend(icon);
            }
        });
    },

    async start() {
        await super.start();
        this._updateMenuIcons();
    }
});
