{
    'name': 'Bhuarjan Web',
    'version': '18.0.1.0.0',
    'summary': 'Public website for Bhuarjan — Land Acquisition Management System.',
    'description': 'A beautiful public-facing website for the Bhuarjan LAMS platform, '
                   'showcasing features, benefits, and how the system works.',
    'category': 'Website',
    'website': 'bhuarjan.com',
    'depends': ['website', 'bhuarjan'],
    'data': [
        'views/website_templates.xml',
        'views/acts_templates.xml',
        'views/login_templates.xml',
        'views/mobile_app_templates.xml',
        'views/website_menu.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'bhuarjan_web/static/src/css/bhuarjan_website.css',
            'bhuarjan_web/static/src/js/bhuarjan_website.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
