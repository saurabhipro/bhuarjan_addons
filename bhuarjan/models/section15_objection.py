# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Section15Objection(models.Model):
    _name = 'bhu.section15.objection'
    _description = 'Section 15 Objections'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Objection Reference / आपत्ति संदर्भ', required=True, tracking=True, default='New')
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True, tracking=True)
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम', required=True, tracking=True)
    landowner_id = fields.Many2one('bhu.landowner', string='Landowner / भूमिस्वामी', required=True, tracking=True)
    survey_id = fields.Many2one('bhu.survey', string='Survey / सर्वे', tracking=True)
    
    objection_date = fields.Date(string='Objection Date / आपत्ति दिनांक', required=True, tracking=True, default=fields.Date.today)
    objection_details = fields.Text(string='Objection Details / आपत्ति विवरण', required=True, tracking=True)
    status = fields.Selection([
        ('draft', 'Draft / प्रारूप'),
        ('received', 'Received / प्राप्त'),
        ('under_review', 'Under Review / समीक्षा के अधीन'),
        ('resolved', 'Resolved / हल'),
        ('rejected', 'Rejected / अस्वीकृत'),
    ], string='Status / स्थिति', default='draft', tracking=True)
    
    resolution_details = fields.Text(string='Resolution Details / समाधान विवरण', tracking=True)
    resolved_date = fields.Date(string='Resolved Date / समाधान दिनांक', tracking=True)
    
    @api.model
    def create(self, vals):
        """Generate objection reference if not provided"""
        if vals.get('name', 'New') == 'New':
            sequence = self.env['ir.sequence'].next_by_code('bhu.section15.objection') or 'New'
            vals['name'] = f'OBJ-{sequence}'
        return super(Section15Objection, self).create(vals)

    @api.onchange('project_id')
    def _onchange_project_id(self):
        """Reset village when project changes and set domain"""
        self.village_id = False
        if self.project_id and self.project_id.village_ids:
            return {'domain': {'village_id': [('id', 'in', self.project_id.village_ids.ids)]}}
        return {'domain': {'village_id': []}}

    def action_resolve(self):
        """Mark objection as resolved"""
        for record in self:
            if not record.resolution_details:
                raise ValidationError(_('Please enter resolution details before resolving.'))
            record.status = 'resolved'
            record.resolved_date = fields.Date.today()
            record.message_post(
                body=_('Objection resolved by %s') % self.env.user.name,
                message_type='notification'
            )

