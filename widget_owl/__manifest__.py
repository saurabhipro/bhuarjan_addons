# -*- coding: utf-8 -*-
{
    'name': "widget_owl",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'license': 'LGPL-3',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        'views/res_partner.xml',
    ],


    # ✅ Assets
    'assets': {
        'web.assets_backend': [
            'widget_owl/static/src/js/components/one2many_dialoge/list_renderer.js',
            'widget_owl/static/src/js/components/one2many_dialoge/one2many_field_dialoge.js',
            'widget_owl/static/src/js/components/one2many_dialoge/popup.js',
        ],
    },

}

