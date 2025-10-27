# -*- coding: utf-8 -*-
##############################################################################
#
#    In2IT Technologies Pvt. Ltd
#    Copyright (C) 2025 (https://www.in2ittech.com)
#
##############################################################################
{
    'name': "Odoo Dynamic Dashboard",
    'version': '18.0.2.0.1',
    'category': 'Productivity',
    'summary': """Create Configurable Dashboards Easily""",
    'description': """Odoo Dynamic Dashboard, Dynamic Dashboard, Odoo Dashboard, Web Dynamic Dashboard, Dashboard with AI, Analytic Dashboard, AI Dashboard, Odoo17 Dashboard, Responsive Dashboard, Odoo17, Dashboard""",
    'author': 'odoo Odoo Team',
    'depends': ['web'],
    'data': [
        'security/dashboard_security.xml',
        'security/ir.model.access.csv',
        'data/dashboard_theme_data.xml',
        'data/kpi_functions.xml',
        'views/dashboard_views.xml',
        'data/dashboard_block_data.xml',
        'views/dynamic_block_views.xml',
        'views/dashboard_menu_views.xml',
        'views/dashboard_theme_views.xml',
        'wizard/dashboard_mail_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'https://cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js',
            'odoo_dynamic_dashboard/static/src/css/**/*.css',
            'odoo_dynamic_dashboard/static/src/scss/**/*.scss',
            'odoo_dynamic_dashboard/static/src/js/**/*.js',
            'odoo_dynamic_dashboard/static/src/xml/**/*.xml',
            'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css',
            'odoo_dynamic_dashboard/static/lib/js/interactjs.js',

            'odoo_dynamic_dashboard/static/src/js/list_controller.xml'
        ],
    },
    'images': ['static/description/banner.gif'],
    'license': "AGPL-3",
    'uninstall_hook': "uninstall_hook",
    'installable': True,
    'auto_install': False,
    'application': True,
}



