# -*- coding: utf-8 -*-
{
    'name': 'Password Eyes Icon Widget',
    'version': '1.0',
    'summary': 'Adds an eye icon to toggle visibility for password-like fields.',
    'description': """
Adds a custom field widget for backend forms and also adds visibility toggle icons 
to password fields on public Login, Signup, and Reset Password pages.

Features:
- Backend widget for password fields via 'password_eyes_icon' widget attribute
- Login page password visibility toggle 
- Optional support for signup and reset password pages (requires auth_signup module)
- Fully reusable password toggle functionality
    """,
    'category': 'Extra Tools',
    'author': 'Gout',
    'license': 'LGPL-3',
    'depends': [
        'web', 
        # 'auth_signup' 
        # Uncomment this code if you want to show the icon on signup and reset password pages
    ],
    'data': [
        'views/web_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'password_eyes_icon/static/src/scss/password_eyes_icon.scss',
            'password_eyes_icon/static/src/js/password_eyes_icon.js',
            'password_eyes_icon/static/src/js/password_eyes_icon_field.js',
            'password_eyes_icon/static/src/xml/password_eyes_icon.xml',
        ],
        'web.assets_frontend': [
            'password_eyes_icon/static/src/scss/password_eyes_icon.scss',
            'password_eyes_icon/static/src/js/password_toggle_public.js',
        ],
        'web.assets_public': [
            'password_eyes_icon/static/src/scss/password_eyes_icon.scss',
            'password_eyes_icon/static/src/js/password_toggle_public.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': [
        'static/description/thumbnail.png',
    ],
} 