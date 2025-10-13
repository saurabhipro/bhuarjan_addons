{
    'name' : 'Bhuarjan',
    'version': '18.0',

    'summary': 'BhoomiArjan — Land Acquisition Management System.',
    'sequence':'-1',
    'description':'To digitize and streamline the end-to-end workflow for land acquisition under RFCTLARR Act, 2013, from Form-10 initiation to Section 19 declaration, ensuring transparency, traceability, and accountability at each level.',
    'category':'Bhumuarjan',
    'website': 'bhuarjan.com',
    'depends':['mail'],
    'data':[
        'security/ir.model.access.csv',
        'security/secrurity.xml',
        'views/district_views.xml',
        'views/project_views.xml',
        'views/res_users.xml',
        'views/menuitem.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',

}