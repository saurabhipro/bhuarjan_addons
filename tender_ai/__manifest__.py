{
    'name': 'Tender AI - Gemini Tender Processing',
    'version': '18.0.1.0.0',
    'summary': 'AI-powered tender processing using Gemini API',
    'description': """
        Tender AI Module
        ================
        This module processes tender ZIP files using Google Gemini API to extract:
        - Tender information from tender.pdf
        - Bidder/company details from company folders
        - Payment records
        - Work experience records
        - Eligibility criteria
        
        Features:
        - Secure ZIP file upload and extraction
        - Background processing with job tracking
        - Gemini API integration for PDF extraction
        - Excel export of processed data
    """,
    'category': 'Tools',
    'author': 'Bhuarjan',
    'website': 'bhuarjan.com',
    'depends': ['base', 'mail', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/system_parameter_data.xml',
        'views/tender_dashboard_views.xml',
        'views/tender_job_views.xml',
        'views/tender_views.xml',
        'views/bidder_views.xml',
        'views/payment_views.xml',
        'views/work_experience_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tender_ai/static/src/css/tender_dashboard.css',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
