/* Bhuarjan Menu Icons JavaScript */

odoo.define('bhuarjan.menu_icons', function (require) {
    'use strict';

    var Menu = require('web.Menu');

    Menu.include({
        _updateMenuIcons: function() {
            // Add icons to menu items based on their IDs
            var iconMap = {
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
            var self = this;
            _.each(iconMap, function(iconClass, menuId) {
                var $menuItem = self.$('.o_menu_item[data-menu-xmlid*="' + menuId + '"]');
                if ($menuItem.length && !$menuItem.find('.fa').length) {
                    $menuItem.prepend('<i class="fa ' + iconClass + ' menu-icon"></i>');
                }
            });
        },

        start: function() {
            var result = this._super.apply(this, arguments);
            this._updateMenuIcons();
            return result;
        }
    });
});
