# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json

class Section23Award(models.Model):
    _name = 'bhu.section23.award'
    _description = 'Section 23 Award'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Award Reference / अवार्ड संदर्भ', required=True, tracking=True, default='New')
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True, tracking=True, ondelete='cascade')
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम', required=True, tracking=True)
    
    # Department - computed from project (for filtering purposes)
    department_id = fields.Many2one('bhu.department', string='Department / विभाग', 
                                   related='project_id.department_id', store=True, readonly=True)
    
    # Award details
    award_date = fields.Date(string='Award Date / अवार्ड दिनांक', default=fields.Date.today, tracking=True)
    award_number = fields.Char(string='Award Number / अवार्ड संख्या', tracking=True)
    
    # Award document
    award_document = fields.Binary(string='Award Document / अवार्ड दस्तावेज़', tracking=True)
    award_document_filename = fields.Char(string='Document Filename / दस्तावेज़ फ़ाइल नाम', tracking=True)
    
    # Notes
    notes = fields.Text(string='Notes / नोट्स', tracking=True)
    
    village_domain = fields.Char()
    
    @api.onchange('project_id')
    def _onchange_project_id(self):
        """Reset village when project changes and set domain"""
        for rec in self:
            if rec.project_id and rec.project_id.village_ids:
                rec.village_domain = json.dumps([('id', 'in', rec.project_id.village_ids.ids)])
            else:
                rec.village_domain = json.dumps([])
                rec.village_id = False
    
    @api.model_create_multi
    def create(self, vals_list):
        """Generate award reference if not provided"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                # Try to use sequence settings from settings master
                project_id = vals.get('project_id')
                village_id = vals.get('village_id')
                if project_id:
                    sequence_number = self.env['bhuarjan.settings.master'].get_sequence_number(
                        'section23_award', project_id, village_id=village_id
                    )
                    if sequence_number:
                        vals['name'] = sequence_number
                    else:
                        # Fallback to ir.sequence
                        sequence = self.env['ir.sequence'].next_by_code('bhu.section23.award') or 'New'
                        vals['name'] = f'SEC23-{sequence}'
                else:
                    # No project_id, use fallback
                    sequence = self.env['ir.sequence'].next_by_code('bhu.section23.award') or 'New'
                    vals['name'] = f'SEC23-{sequence}'
        return super().create(vals_list)
    
    def action_download_award(self):
        """Download award document"""
        self.ensure_one()
        if not self.award_document:
            raise ValidationError(_('No award document available to download.'))
        filename = self.award_document_filename or f'award_{self.name}.pdf'
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/award_document/{filename}?download=true',
            'target': 'self',
        }

