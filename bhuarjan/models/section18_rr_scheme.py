# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json

class Section18RRScheme(models.Model):
    _name = 'bhu.section18.rr.scheme'
    _description = 'Section 18 R and R Scheme'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Scheme Reference / योजना संदर्भ', required=True, tracking=True, default='New')
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True, tracking=True, ondelete='cascade')
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम', required=True, tracking=True)
    
    # Scheme file upload
    scheme_file = fields.Binary(string='R and R Scheme File / पुनर्वास और पुनर्स्थापना योजना फ़ाइल', required=True, tracking=True)
    scheme_filename = fields.Char(string='Scheme Filename / योजना फ़ाइल नाम', tracking=True)
    
    # Notes
    notes = fields.Text(string='Notes / नोट्स', tracking=True)
    
    # No state field - free from validation as per requirements
    
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
        """Generate scheme reference if not provided"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                # Try to use sequence settings from settings master
                project_id = vals.get('project_id')
                village_id = vals.get('village_id')
                if project_id:
                    sequence_number = self.env['bhuarjan.settings.master'].get_sequence_number(
                        'section18_rr_scheme', project_id, village_id=village_id
                    )
                    if sequence_number:
                        vals['name'] = sequence_number
                    else:
                        # Fallback to ir.sequence
                        sequence = self.env['ir.sequence'].next_by_code('bhu.section18.rr.scheme') or 'New'
                        vals['name'] = f'RR-{sequence}'
                else:
                    # No project_id, use fallback
                    sequence = self.env['ir.sequence'].next_by_code('bhu.section18.rr.scheme') or 'New'
                    vals['name'] = f'RR-{sequence}'
        return super().create(vals_list)
    
    def action_download_scheme(self):
        """Download scheme file"""
        self.ensure_one()
        if not self.scheme_file:
            raise ValidationError(_('No scheme file available to download.'))
        filename = self.scheme_filename or f'scheme_{self.name}.pdf'
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/scheme_file/{filename}?download=true',
            'target': 'self',
        }

