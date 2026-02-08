{
    'name': 'Bhuarjan Website',
    'version': '18.0.1.0.0',
    'summary': 'Landing page and website integration for the BHUARJAN platform.',
    'category': 'Website/Website',
    'description': 'This module provides a premium, responsive landing page for the BHUARJAN platform, featuring real-time insights and a modern design system.',
    'depends': ['website', 'bhuarjan'],
    'data': [
        'views/website_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'bhuarjan_website/static/src/css/website_styles.css',
            'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Outfit:wght@300;400;600;700&display=swap',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
