# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools.translate import _


class Stage9Section21(models.Model):
    _name = 'bhu.stage9.section21'
    _description = 'Stage 9: Section 21 Notice to Owner for Award'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    # Basic Information
    notice_date = fields.Date(string='Notice Date', required=True, tracking=True)
    public_purpose = fields.Text(string='Public Purpose', required=True)
    
    # Location Information
    district_id = fields.Many2one('bhu.district', string='District', required=True)
    tehsil_id = fields.Many2one('bhu.tehsil', string='Tehsil', required=True)
    village_id = fields.Many2one('bhu.village', string='Village', required=True)
    total_area = fields.Float(string='Total Area (Acres)', readonly=True)
    
    # Notice Details
    notice_type = fields.Selection([
        ('personal', 'Personal Notice'),
        ('public', 'Public Notice'),
        ('newspaper', 'Newspaper Notice')
    ], string='Notice Type', required=True, default='personal')
    
    notice_delivery_date = fields.Date(string='Notice Delivery Date')
    notice_delivery_method = fields.Char(string='Delivery Method')
    notice_recipient = fields.Char(string='Notice Recipient')
    
    # Award Details
    award_amount = fields.Monetary(string='Award Amount', currency_field='currency_id', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    
    # Landowner Details
    landowner_ids = fields.Many2many('bhu.landowner', string='Affected Landowners')
    total_affected_families = fields.Integer(string='Total Affected Families', default=0)
    
    # Company Information
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    company_name = fields.Char(related='company_id.name', string='Company Name', store=True)
    
    # Related Records
    survey_ids = fields.Many2many('bhu.survey', string='Related Surveys')
    stage8_ids = fields.Many2many('bhu.stage8.section19', string='Related Stage 8 Records')
    
    # Signature Details
    signature_place = fields.Char(string='Signature Place')
    signature_date = fields.Date(string='Signature Date')
    signed_by = fields.Char(string='Signed By')
    designation = fields.Char(string='Designation')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('bhu.stage9.section21') or _('New')
        return super(Stage9Section21, self).create(vals_list)

    def action_confirm(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset(self):
        self.write({'state': 'draft'})
