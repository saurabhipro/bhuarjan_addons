# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools.translate import _


class Stage3Jansunwai(models.Model):
    _name = 'bhu.stage3.jansunwai'
    _description = 'Stage 3: Section 4(1) Jansunwai & Social Impact Assessment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    # Basic Information
    notification_date = fields.Date(string='Notification Date', required=True, tracking=True)
    public_purpose = fields.Text(string='Public Purpose', required=True)
    
    # Location Information
    district_id = fields.Many2one('bhu.district', string='District', required=True)
    tehsil_id = fields.Many2one('bhu.tehsil', string='Tehsil', required=True)
    village_id = fields.Many2one('bhu.village', string='Village', required=True)
    total_area = fields.Float(string='Total Area (Acres)', readonly=True)
    
    # Jansunwai Details
    jansunwai_date = fields.Date(string='Jansunwai Date', required=True)
    jansunwai_time = fields.Char(string='Jansunwai Time', placeholder='e.g., 10:00 AM')
    jansunwai_location = fields.Char(string='Jansunwai Location', required=True)
    jansunwai_purpose = fields.Text(string='Purpose of Jansunwai', required=True)
    
    # Social Impact Assessment
    sia_conducted = fields.Boolean(string='SIA Conducted', default=False)
    sia_date = fields.Date(string='SIA Date')
    sia_agency = fields.Char(string='SIA Agency')
    sia_report = fields.Binary(string='SIA Report')
    sia_report_filename = fields.Char(string='SIA Report Filename')
    
    # Affected Population
    total_affected_families = fields.Integer(string='Total Affected Families', default=0)
    total_affected_individuals = fields.Integer(string='Total Affected Individuals', default=0)
    scheduled_caste_families = fields.Integer(string='Scheduled Caste Families', default=0)
    scheduled_tribe_families = fields.Integer(string='Scheduled Tribe Families', default=0)
    other_backward_class_families = fields.Integer(string='OBC Families', default=0)
    
    # Land Details
    total_land_area = fields.Float(string='Total Land Area (Acres)')
    agricultural_land = fields.Float(string='Agricultural Land (Acres)')
    non_agricultural_land = fields.Float(string='Non-Agricultural Land (Acres)')
    forest_land = fields.Float(string='Forest Land (Acres)')
    
    # Compensation Details
    estimated_compensation = fields.Monetary(string='Estimated Compensation', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    
    # Company Information
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    company_name = fields.Char(related='company_id.name', string='Company Name', store=True)
    
    # Related Records
    survey_ids = fields.Many2many('bhu.survey', string='Related Surveys')
    notification4_ids = fields.Many2many('bhu.notification4', string='Related Notification 4')
    
    # Signature Details
    signature_place = fields.Char(string='Signature Place')
    signature_date = fields.Date(string='Signature Date')
    signed_by = fields.Char(string='Signed By')
    designation = fields.Char(string='Designation')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('bhu.stage3.jansunwai') or _('New')
        return super(Stage3Jansunwai, self).create(vals)

    def action_confirm(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset(self):
        self.write({'state': 'draft'})
