{
    'name': 'JWT Mobile Authentication',
    'version': '1.0',
    'summary': 'JWT Authentication for Mobile App using mobile number and OTP',
    'category': 'Authentication',
    'author': 'Your Name',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'security/res_groups.xml',
        'views/mobile_otp_views.xml',
        'views/res_users_views.xml',
        'views/jwt_token_views.xml'
    ],
    'installable': True,
    'application': True,
}

#library need to install
#pip install PyJWT
