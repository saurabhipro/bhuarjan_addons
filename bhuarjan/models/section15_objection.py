# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Section15Objection(models.Model):
    _name = 'bhu.section15.objection'
    _description = 'Section 15 Objection / धारा 15 आपत्ति'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'objection_date desc, name'

    name = fields.Char(string='Objection Number / आपत्ति संख्या', required=True, tracking=True)
    objection_date = fields.Date(string='Objection Date / आपत्ति दिनाँक', required=True, 
                                default=fields.Date.today, tracking=True)
    
    # Company/Organization Information
    company_id = fields.Many2one('res.company', string='Company / कंपनी', required=True, 
                                 default=lambda self: self.env.company, tracking=True)
    
    # Related Records
    section11_notification_id = fields.Many2one('bhu.section11.notification', 
                                               string='Section 11 Notification / धारा 11 सूचना', 
                                               required=True, tracking=True)
    survey_id = fields.Many2one('bhu.survey', string='Survey / सर्वे', 
                               related='section11_notification_id.survey_id', store=True)
    landowner_id = fields.Many2one('bhu.landowner', string='Objector / आपत्तिकर्ता', 
                                  required=True, tracking=True)
    
    # Objection Details
    objection_type = fields.Selection([
        ('compensation', 'Compensation / मुआवजा'),
        ('land_measurement', 'Land Measurement / भूमि माप'),
        ('ownership', 'Ownership / स्वामित्व'),
        ('procedure', 'Procedure / प्रक्रिया'),
        ('other', 'Other / अन्य')
    ], string='Objection Type / आपत्ति प्रकार', required=True, tracking=True)
    
    objection_reason = fields.Text(string='Objection Reason / आपत्ति का कारण', required=True, tracking=True)
    supporting_documents = fields.Text(string='Supporting Documents / समर्थन दस्तावेज', tracking=True)
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft / मसौदा'),
        ('submitted', 'Submitted / प्रस्तुत'),
        ('under_review', 'Under Review / समीक्षा में'),
        ('accepted', 'Accepted / स्वीकृत'),
        ('rejected', 'Rejected / अस्वीकृत'),
        ('resolved', 'Resolved / हल')
    ], string='Status / स्थिति', default='draft', tracking=True)
    
    # Review Details
    review_date = fields.Date(string='Review Date / समीक्षा दिनाँक', tracking=True)
    reviewer_id = fields.Many2one('res.users', string='Reviewer / समीक्षक', tracking=True)
    review_notes = fields.Text(string='Review Notes / समीक्षा नोट्स', tracking=True)
    decision_date = fields.Date(string='Decision Date / निर्णय दिनाँक', tracking=True)
    decision_notes = fields.Text(string='Decision Notes / निर्णय नोट्स', tracking=True)
    
    # Resolution
    resolution_type = fields.Selection([
        ('compensation_adjustment', 'Compensation Adjustment / मुआवजा समायोजन'),
        ('re_survey', 'Re-survey / पुनः सर्वेक्षण'),
        ('legal_proceedings', 'Legal Proceedings / कानूनी कार्यवाही'),
        ('withdrawn', 'Withdrawn / वापस लिया गया'),
        ('other', 'Other / अन्य')
    ], string='Resolution Type / समाधान प्रकार', tracking=True)
    
    resolution_notes = fields.Text(string='Resolution Notes / समाधान नोट्स', tracking=True)
    resolution_date = fields.Date(string='Resolution Date / समाधान दिनाँक', tracking=True)
    
    # Attachments
    attachment_ids = fields.One2many('ir.attachment', 'res_id', string='Attachments / अनुलग्नक', 
                                   domain=[('res_model', '=', 'bhu.section15.objection')])
    
    @api.constrains('objection_date', 'review_date', 'decision_date', 'resolution_date')
    def _check_dates(self):
        """Validate objection dates"""
        for record in self:
            if record.review_date and record.objection_date:
                if record.review_date < record.objection_date:
                    raise ValidationError(_('Review date cannot be before objection date.'))
            if record.decision_date and record.review_date:
                if record.decision_date < record.review_date:
                    raise ValidationError(_('Decision date cannot be before review date.'))
            if record.resolution_date and record.decision_date:
                if record.resolution_date < record.decision_date:
                    raise ValidationError(_('Resolution date cannot be before decision date.'))
    
    def action_submit(self):
        """Submit the objection"""
        for record in self:
            if record.state == 'draft':
                record.write({'state': 'submitted'})
                record.message_post(
                    body=_('Objection submitted for review'),
                    message_type='notification'
                )
    
    def action_under_review(self):
        """Mark objection as under review"""
        for record in self:
            if record.state == 'submitted':
                record.write({
                    'state': 'under_review',
                    'review_date': fields.Date.today()
                })
                record.message_post(
                    body=_('Objection is now under review'),
                    message_type='notification'
                )
    
    def action_accept(self):
        """Accept the objection"""
        for record in self:
            if record.state == 'under_review':
                record.write({
                    'state': 'accepted',
                    'decision_date': fields.Date.today()
                })
                record.message_post(
                    body=_('Objection accepted'),
                    message_type='notification'
                )
    
    def action_reject(self):
        """Reject the objection"""
        for record in self:
            if record.state == 'under_review':
                record.write({
                    'state': 'rejected',
                    'decision_date': fields.Date.today()
                })
                record.message_post(
                    body=_('Objection rejected'),
                    message_type='notification'
                )
    
    def action_resolve(self):
        """Resolve the objection"""
        for record in self:
            if record.state in ['accepted', 'rejected']:
                record.write({
                    'state': 'resolved',
                    'resolution_date': fields.Date.today()
                })
                record.message_post(
                    body=_('Objection resolved'),
                    message_type='notification'
                )
