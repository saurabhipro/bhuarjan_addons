# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


# Stub models for Process menu items - to be implemented later
# These are minimal models to allow the module to load

class Section4NotificationWizard(models.TransientModel):
    _name = 'bhu.section4.notification.wizard'
    _description = 'Section 4 Notification Wizard'

    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True)
    village_ids = fields.Many2many('bhu.village', string='Villages / ग्राम', required=True)
    public_purpose = fields.Text(string='Public Purpose / लोक प्रयोजन का विवरण', 
                                 help='Description of public purpose for land acquisition')
    
    # Public Hearing Details
    public_hearing_date = fields.Date(string='Public Hearing Date / जन सुनवाई दिनांक')
    public_hearing_time = fields.Char(string='Public Hearing Time / जन सुनवाई समय', 
                                      help='e.g., 10:00 AM')
    public_hearing_place = fields.Char(string='Public Hearing Place / जन सुनवाई स्थान')
    
    # 11 Questions from the template
    q1_brief_description = fields.Text(string='(एक) लोक प्रयोजन का संक्षिप्त विवरण / Brief description of public purpose')
    q2_directly_affected = fields.Char(string='(दो) प्रत्यक्ष रूप से प्रभावित परिवारों की संख्या / Number of directly affected families')
    q3_indirectly_affected = fields.Char(string='(तीन) अप्रत्यक्ष रूप से प्रभावित परिवारों की संख्या / Number of indirectly affected families')
    q4_private_assets = fields.Char(string='(चार) प्रभावित क्षेत्र में निजी मकानों तथा अन्य परिसंपत्तियों की अनुमानित संख्या / Estimated number of private houses and other assets')
    q5_government_assets = fields.Char(string='(पाँच) प्रभावित क्षेत्र में शासकीय मकान तथा अन्य परिसंपत्तियों की अनुमानित संख्या / Estimated number of government houses and other assets')
    q6_minimal_acquisition = fields.Char(string='(छः) क्या प्रस्तावित अर्जन न्यूनतम है? / Is the proposed acquisition minimal?')
    q7_alternatives_considered = fields.Text(string='(सात) क्या संभव विकल्पों और इसकी साध्यता पर विचार कर लिया गया है? / Have possible alternatives and their feasibility been considered?')
    q8_total_cost = fields.Char(string='(आठ) परियोजना की कुल लागत / Total cost of the project')
    q9_project_benefits = fields.Text(string='(नौ) परियोजना से होने वाला लाभ / Benefits from the project')
    q10_compensation_measures = fields.Text(string='(दस) प्रस्तावित सामाजिक समाघात की प्रतिपूर्ति के लिये उपाय तथा उस पर होने वाला संभावित व्यय / Measures for compensation and likely expenditure')
    q11_other_components = fields.Text(string='(ग्यारह) परियोजना द्वारा प्रभावित होने वाले अन्य घटक / Other components affected by the project')

    @api.onchange('project_id')
    def _onchange_project_id(self):
        """Reset villages when project changes and set domain"""
        self.village_ids = False
        if self.project_id and self.project_id.village_ids:
            return {'domain': {'village_ids': [('id', 'in', self.project_id.village_ids.ids)]}}
        return {'domain': {'village_ids': []}}

    def _get_consolidated_village_data(self):
        """Get consolidated survey data grouped by village"""
        self.ensure_one()
        
        # Get all approved surveys for selected villages in the project
        surveys = self.env['bhu.survey'].search([
            ('project_id', '=', self.project_id.id),
            ('village_id', 'in', self.village_ids.ids),
            ('state', '=', 'approved')
        ])
        
        # Group surveys by village and calculate totals
        village_data = {}
        for survey in surveys:
            village = survey.village_id
            if village.id not in village_data:
                # Get district and tehsil from village or survey
                district_name = village.district_id.name if village.district_id else (survey.district_name or 'Raigarh (Chhattisgarh)')
                tehsil_name = village.tehsil_id.name if village.tehsil_id else (survey.tehsil_id.name or '')
                
                village_data[village.id] = {
                    'village_id': village.id,
                    'village_name': village.name,
                    'district': district_name,
                    'tehsil': tehsil_name,
                    'total_area': 0.0,
                    'surveys': []
                }
            # Sum up acquired area for all khasras in this village
            village_data[village.id]['total_area'] += survey.acquired_area or 0.0
            village_data[village.id]['surveys'].append(survey.id)
        
        # Convert to list sorted by village name
        consolidated_list = []
        for village_id in sorted(village_data.keys(), key=lambda x: village_data[x]['village_name']):
            consolidated_list.append(village_data[village_id])
        
        return consolidated_list

    def get_formatted_hearing_date(self):
        """Format public hearing date for display"""
        self.ensure_one()
        if self.public_hearing_date:
            return self.public_hearing_date.strftime('%d/%m/%Y')
        return '........................'
    
    def action_generate_pdf(self):
        """Generate Section 4 Notification PDF with consolidated village data"""
        self.ensure_one()
        
        if not self.village_ids:
            raise ValidationError(_('Please select at least one village.'))
        
        # Get consolidated data
        consolidated_data = self._get_consolidated_village_data()
        
        if not consolidated_data:
            raise ValidationError(_('No approved surveys found for the selected villages.'))
        
        # Generate PDF report - pass the wizard recordset
        report_action = self.env.ref('bhuarjan.action_report_section4_notification')
        return report_action.report_action(self)


class ExpertCommitteeReport(models.Model):
    _name = 'bhu.expert.committee.report'
    _description = 'Expert Committee Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Report Name', required=True, default='New')
    project_id = fields.Many2one('bhu.project', string='Project', required=True)
    village_id = fields.Many2one('bhu.village', string='Village', required=True)
    report_file = fields.Binary(string='Report File')
    report_filename = fields.Char(string='File Name')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft')


class ExpertCommitteeOrderWizard(models.TransientModel):
    _name = 'bhu.expert.committee.order.wizard'
    _description = 'Expert Committee Order Wizard'

    project_id = fields.Many2one('bhu.project', string='Project', required=True)
    village_ids = fields.Many2many('bhu.village', string='Villages', required=True)

    def action_generate_order(self):
        """Generate Order - To be implemented"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Info'),
                'message': _('Order generation will be implemented soon.'),
                'type': 'info',
            }
        }


class Section11PreliminaryWizard(models.TransientModel):
    _name = 'bhu.section11.preliminary.wizard'
    _description = 'Section 11 Preliminary Report Wizard'

    project_id = fields.Many2one('bhu.project', string='Project', required=True)
    village_ids = fields.Many2many('bhu.village', string='Villages', required=True)

    def action_generate_report(self):
        """Generate Report - To be implemented"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Info'),
                'message': _('Report generation will be implemented soon.'),
                'type': 'info',
            }
        }


class Section19NotificationWizard(models.TransientModel):
    _name = 'bhu.section19.notification.wizard'
    _description = 'Section 19 Notification Wizard'

    project_id = fields.Many2one('bhu.project', string='Project', required=True)
    village_ids = fields.Many2many('bhu.village', string='Villages', required=True)

    def action_generate_notification(self):
        """Generate Notification - To be implemented"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Info'),
                'message': _('Notification generation will be implemented soon.'),
                'type': 'info',
            }
        }


class DraftAwardWizard(models.TransientModel):
    _name = 'bhu.draft.award.wizard'
    _description = 'Draft Award Wizard'

    project_id = fields.Many2one('bhu.project', string='Project', required=True)
    village_ids = fields.Many2many('bhu.village', string='Villages', required=True)

    def action_generate_draft_award(self):
        """Generate Draft Award - To be implemented"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Info'),
                'message': _('Draft award generation will be implemented soon.'),
                'type': 'info',
            }
        }


class GenerateNoticesWizard(models.TransientModel):
    _name = 'bhu.generate.notices.wizard'
    _description = 'Generate Notices Wizard'

    project_id = fields.Many2one('bhu.project', string='Project', required=True)
    village_ids = fields.Many2many('bhu.village', string='Villages')

    def action_generate_notices(self):
        """Generate Notices - To be implemented"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Info'),
                'message': _('Notice generation will be implemented soon.'),
                'type': 'info',
            }
        }


class DownloadNoticesWizard(models.TransientModel):
    _name = 'bhu.download.notices.wizard'
    _description = 'Download Notices Wizard'

    project_id = fields.Many2one('bhu.project', string='Project')
    village_id = fields.Many2one('bhu.village', string='Village')
    landowner_id = fields.Many2one('bhu.landowner', string='Landowner')

    def action_download_notices(self):
        """Download Notices - To be implemented"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Info'),
                'message': _('Notice download will be implemented soon.'),
                'type': 'info',
            }
        }


class AwardNotificationWizard(models.TransientModel):
    _name = 'bhu.award.notification.wizard'
    _description = 'Award Notification Wizard'

    project_id = fields.Many2one('bhu.project', string='Project', required=True)
    village_ids = fields.Many2many('bhu.village', string='Villages', required=True)

    def action_generate_award_notification(self):
        """Generate Award Notification - To be implemented"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Info'),
                'message': _('Award notification generation will be implemented soon.'),
                'type': 'info',
            }
        }


class DownloadAwardNotificationWizard(models.TransientModel):
    _name = 'bhu.download.award.notification.wizard'
    _description = 'Download Award Notification Wizard'

    project_id = fields.Many2one('bhu.project', string='Project')
    village_id = fields.Many2one('bhu.village', string='Village')
    landowner_id = fields.Many2one('bhu.landowner', string='Landowner')

    def action_download_award_notification(self):
        """Download Award Notification - To be implemented"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Info'),
                'message': _('Award notification download will be implemented soon.'),
                'type': 'info',
            }
        }


class GeneratePaymentFileWizard(models.TransientModel):
    _name = 'bhu.generate.payment.file.wizard'
    _description = 'Generate Payment File Wizard'

    project_id = fields.Many2one('bhu.project', string='Project', required=True)
    village_ids = fields.Many2many('bhu.village', string='Villages', required=True)

    def action_generate_payment_file(self):
        """Generate Payment File - To be implemented"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Info'),
                'message': _('Payment file generation will be implemented soon.'),
                'type': 'info',
            }
        }

