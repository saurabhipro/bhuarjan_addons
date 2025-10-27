# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

{
    "name": "Global Search",

    "version": "0.0.1",

    "author": "Softhealer Technologies",

    "website": "https://www.softhealer.com",

    "license": "OPL-1",

    "support": "support@softhealer.com",

    "category": "Extra Tools",

    "summary": "any data search Easy Object Search Quick Object Find Module advance search Object"
               " Using Attributes Overall Odoo Object Search Global Model Search advance records "
               "search google search Feeds search all in one search option Odoo Advanced Search "
               "List view search List View Manager Quick Search Listview search rename column "
               "reorder Column search expand powerfull search list view search search range search"
               " by range search by date easy search fast search dynamic search speed up micro "
               "search Odoo Smart Search Elastic search dynamic filter product search auto search "
               "automatic search quick product search optimize search better search Linear search"
               "Binary search Sequential Search Interval Search Interpolation search Global Search"
               "Menu Global Menu Search Quick Menu Search Quick Search Menu Quick Menu Access "
               "Global Menu Access Global Search Odoo Quick Search Odoo Global Search Odoo Quick "
               "Search"
               "Multi-Model Search"
               "Configurable Search"
               "One2many Field Search"
               "Open Record in New Tab"
               "Minimum Character Search Trigger"
               "Search InterfaceS",

    "description": """
Global Search feaure allows Odoo users to search across all configured objects and fields, including one-to-many relationships. It supports multi-company environments, respects user access rights, and opens results in a new tab. You can define a minimum number of characters required to trigger the search. Models and fields are fully configurable, with access managed through security groups. The interface clearly displays object types and company names for easy identification. All internal users can use this feature. Cheers!""",

    "depends": ['base_setup'],

    "data": [
        "security/base_security.xml",
        "security/ir.model.access.csv",
        "views/global_search_view.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'sh_global_search/static/src/scss/GlobalSearch.scss',
            'sh_global_search/static/src/scss/systray_customization.scss',
            'sh_global_search/static/src/xml/*.xml',
            'sh_global_search/static/src/js/*',
        ]
    },

    "images": ["static/description/background.png", ],
    "installable": True,
    "auto_install": False,
    "application": True,
    "price": 40,
    "currency": "EUR"
}
