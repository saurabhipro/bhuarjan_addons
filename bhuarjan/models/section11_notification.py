# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Section11Notification(models.Model):
    _name = 'bhu.section11.notification'
    _description = 'Section 11 Notification / धारा 11 सूचना'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'notification_date desc, name'

    name = fields.Char(string='Notification Number / सूचना संख्या', required=True, tracking=True)
    notification_date = fields.Date(string='Notification Date / सूचना दिनाँक', required=True, 
                                   default=fields.Date.today, tracking=True)
    
    # Company/Organization Information
    company_id = fields.Many2one('res.company', string='Company / कंपनी', required=True, 
                                 default=lambda self: self.env.company, tracking=True)
    
    # Survey Information
    survey_id = fields.Many2one('bhu.survey', string='Survey / सर्वे', required=True, tracking=True)
    landowner_ids = fields.Many2many('bhu.landowner', string='Affected Landowners / प्रभावित भूमिस्वामी', 
                                    tracking=True)
    
    # Notification Details
    notification_type = fields.Selection([
        ('public_notice', 'Public Notice / सार्वजनिक सूचना'),
        ('individual_notice', 'Individual Notice / व्यक्तिगत सूचना'),
        ('newspaper_notice', 'Newspaper Notice / समाचार पत्र सूचना'),
        ('radio_notice', 'Radio Notice / रेडियो सूचना'),
        ('tv_notice', 'TV Notice / टीवी सूचना')
    ], string='Notification Type / सूचना प्रकार', required=True, tracking=True)
    
    # Publication Details
    publication_date = fields.Date(string='Publication Date / प्रकाशन दिनाँक', tracking=True)
    newspaper_name = fields.Char(string='Newspaper Name / समाचार पत्र का नाम', tracking=True)
    radio_station = fields.Char(string='Radio Station / रेडियो स्टेशन', tracking=True)
    tv_channel = fields.Char(string='TV Channel / टीवी चैनल', tracking=True)
    
    # Content
    notification_content = fields.Text(string='Notification Content / सूचना सामग्री', required=True, tracking=True)
    hindi_content = fields.Text(string='Hindi Content / हिंदी सामग्री', tracking=True)
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft / मसौदा'),
        ('published', 'Published / प्रकाशित'),
        ('acknowledged', 'Acknowledged / स्वीकृत'),
        ('completed', 'Completed / पूर्ण')
    ], string='Status / स्थिति', default='draft', tracking=True)
    
    # Response Details
    response_deadline = fields.Date(string='Response Deadline / प्रतिक्रिया की अंतिम तिथि', tracking=True)
    total_responses = fields.Integer(string='Total Responses / कुल प्रतिक्रियाएं', compute='_compute_responses', store=True)
    objection_count = fields.Integer(string='Objections Count / आपत्तियों की संख्या', compute='_compute_responses', store=True)
    
    # Attachments
    attachment_ids = fields.One2many('ir.attachment', 'res_id', string='Attachments / अनुलग्नक', 
                                   domain=[('res_model', '=', 'bhu.section11.notification')])
    
    @api.depends('landowner_ids')
    def _compute_responses(self):
        """Compute total responses and objections"""
        for record in self:
            record.total_responses = len(record.landowner_ids)
            # Count objections from related section 15 objections
            objections = self.env['bhu.section15.objection'].search([
                ('section11_notification_id', '=', record.id)
            ])
            record.objection_count = len(objections)
    
    @api.constrains('notification_date', 'publication_date')
    def _check_dates(self):
        """Validate notification and publication dates"""
        for record in self:
            if record.publication_date and record.notification_date:
                if record.publication_date < record.notification_date:
                    raise ValidationError(_('Publication date cannot be before notification date.'))
    
    def action_publish(self):
        """Publish the notification"""
        for record in self:
            if record.state == 'draft':
                record.write({'state': 'published'})
                record.message_post(
                    body=_('Notification published on %s') % record.publication_date or fields.Date.today(),
                    message_type='notification'
                )
    
    def action_acknowledge(self):
        """Acknowledge the notification"""
        for record in self:
            if record.state == 'published':
                record.write({'state': 'acknowledged'})
                record.message_post(
                    body=_('Notification acknowledged'),
                    message_type='notification'
                )
    
    def action_complete(self):
        """Mark notification as completed"""
        for record in self:
            if record.state == 'acknowledged':
                record.write({'state': 'completed'})
                record.message_post(
                    body=_('Notification process completed'),
                    message_type='notification'
                )
    
    def action_view_objections(self):
        """View related objections"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Objections for %s') % self.name,
            'res_model': 'bhu.section15.objection',
            'view_mode': 'list,form',
            'domain': [('section11_notification_id', '=', self.id)],
            'context': {'default_section11_notification_id': self.id}
        }
