{
    "name": "Remove Odoo in URL | Remove Odoo URL | Remove Odoo",
    "summary": "Remove Odoo in URL",
    "version": "0.1.1",
    "category": "Extra Tools",
    'author': "Mountain Tran",
    'support': "mountaintran2021@gmail.com",
    'license': 'OPL-1',
    'price': 15,
    'currency': 'EUR',
    "depends": ["web",'base'],
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    "data": [
          'data/ir_config_parameter.xml',
          'views/ir_config_parameter_views.xml'
      ],
    "assets": {
        "web.assets_backend": [
            "ta_remove_odoo_url/static/src/**/*",
        ],
    },
    'uninstall_hook': '_uninstall_cleanup',
}
