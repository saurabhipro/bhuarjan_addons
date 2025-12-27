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
    award_document = fields.Binary(string='Award Document / अवार्ड दस्तावेज़', tracking=False)
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
    
    def action_generate_award(self):
        """Generate Section 23 Award Report (Land + Tree Compensation merged)"""
        self.ensure_one()
        
        if not self.project_id:
            raise ValidationError(_('Please select a project first.'))
        
        if not self.village_id:
            raise ValidationError(_('Please select a village first.'))
        
        # Get the report action and generate PDF
        report_action = self.env.ref('bhuarjan.action_report_section23_award')
        
        # Generate PDF directly (downloads instead of opening in new tab)
        pdf_result = report_action.sudo()._render_qweb_pdf(
            report_action.report_name,
            [self.id],
            data={}
        )
        
        if pdf_result:
            pdf_data = pdf_result[0] if isinstance(pdf_result, (tuple, list)) else pdf_result
            if isinstance(pdf_data, bytes):
                # Save to award_document field
                import base64
                from datetime import datetime
                
                filename = f'Section23_Award_{self.village_id.name.replace(" ", "_") if self.village_id else ""}_{datetime.now().strftime("%Y%m%d")}.pdf'
                
                self.write({
                    'award_document': base64.b64encode(pdf_data),
                    'award_document_filename': filename
                })
                
                # Return download action
                return {
                    'type': 'ir.actions.act_url',
                    'url': f'/web/content/{self._name}/{self.id}/award_document/{filename}?download=true',
                    'target': 'self',
                }
        
        # Fallback to standard report action if PDF generation fails
        return report_action.report_action(self)
    
    def get_land_compensation_data(self):
        """Get land compensation data grouped by landowner and khasra"""
        self.ensure_one()
        
        # Get approved surveys for this village and project
        surveys = self.env['bhu.survey'].search([
            ('project_id', '=', self.project_id.id),
            ('village_id', '=', self.village_id.id),
            ('state', 'in', ['approved', 'locked']),
            ('khasra_number', '!=', False),
        ])
        
        if not surveys:
            return []
        
        # Group by landowner and khasra
        compensation_data = {}
        
        for survey in surveys:
            khasra = survey.khasra_number or ''
            acquired_area = survey.acquired_area or 0.0
            
            # Get land type from survey
            irrigation_type = survey.irrigation_type or 'unirrigated'
            is_irrigated = irrigation_type == 'irrigated'
            is_unirrigated = irrigation_type == 'unirrigated'
            
            # Get landowners for this survey
            landowners = survey.landowner_ids if survey.landowner_ids else []
            
            if not landowners:
                # If no landowners, create entry with empty landowner
                key = (False, khasra)
                if key not in compensation_data:
                    compensation_data[key] = {
                        'landowner': None,
                        'landowner_name': '',
                        'father_name': '',
                        'caste': '',
                        'address': '',
                        'khasra': khasra,
                        'original_area': 0.0,
                        'acquired_area': 0.0,
                        'lagan': khasra,  # Using khasra as lagan
                        'fallow': False,
                        'unirrigated': False,
                        'irrigated': False,
                        'guide_line_rate': 0.0,
                        'market_value': 0.0,
                        'solatium': 0.0,
                        'interest': 0.0,
                        'total_compensation': 0.0,
                        'rehab_policy_per_acre_1': 0.0,
                        'rehab_policy_per_acre_2': 0.0,
                        'rehab_policy_amount': 0.0,
                        'dev_compensation': 0.0,
                    }
                compensation_data[key]['acquired_area'] += acquired_area
            else:
                # Process each landowner
                for landowner in landowners:
                    key = (landowner.id, khasra)
                    if key not in compensation_data:
                        compensation_data[key] = {
                            'landowner': landowner,
                            'landowner_name': landowner.name or '',
                            'father_name': landowner.father_name or landowner.spouse_name or '',
                            'caste': '',  # Caste not stored in model
                            'address': landowner.owner_address or '',
                            'khasra': khasra,
                            'original_area': 0.0,
                            'acquired_area': 0.0,
                            'lagan': khasra,
                            'fallow': False,
                            'unirrigated': is_unirrigated,
                            'irrigated': is_irrigated,
                            'guide_line_rate': 0.0,  # Will be calculated
                            'market_value': 0.0,
                            'solatium': 0.0,
                            'interest': 0.0,
                            'total_compensation': 0.0,
                            'rehab_policy_per_acre_1': 0.0,
                            'rehab_policy_per_acre_2': 0.0,
                            'rehab_policy_amount': 0.0,
                            'dev_compensation': 0.0,
                        }
                    compensation_data[key]['acquired_area'] += acquired_area
        
        # Convert to list and calculate totals
        result = []
        for key, data in compensation_data.items():
            # Calculate compensation amounts (placeholder - adjust based on actual rates)
            guide_line_rate = 2112000.0  # Default rate from screenshot
            market_value = data['acquired_area'] * guide_line_rate * 2  # Factor = 2
            solatium = market_value  # 100% solatium
            interest = market_value  # Interest calculation
            total_compensation = market_value + solatium + interest
            
            data['guide_line_rate'] = guide_line_rate
            data['market_value'] = market_value
            data['solatium'] = solatium
            data['interest'] = interest
            data['total_compensation'] = total_compensation
            
            result.append(data)
        
        # Sort by landowner name, then khasra
        result.sort(key=lambda x: (x['landowner_name'] or '', x['khasra'] or ''))
        
        return result
    
    def get_tree_compensation_data(self):
        """Get tree compensation data grouped by landowner and khasra"""
        self.ensure_one()
        
        # Get approved surveys with trees for this village and project
        surveys = self.env['bhu.survey'].search([
            ('project_id', '=', self.project_id.id),
            ('village_id', '=', self.village_id.id),
            ('state', 'in', ['approved', 'locked']),
            ('khasra_number', '!=', False),
        ])
        
        if not surveys:
            return []
        
        # Get all tree lines from surveys
        tree_data = {}
        
        for survey in surveys:
            khasra = survey.khasra_number or ''
            landowners = survey.landowner_ids if survey.landowner_ids else []
            
            # Get tree lines for this survey
            tree_lines = survey.tree_line_ids if hasattr(survey, 'tree_line_ids') else []
            
            if not tree_lines:
                continue
            
            if not landowners:
                # If no landowners, create entry with empty landowner
                for tree_line in tree_lines:
                    tree_type_name = tree_line.tree_master_id.name if tree_line.tree_master_id else 'other'
                    key = (False, khasra, tree_type_name)
                    if key not in tree_data:
                        tree_data[key] = {
                            'landowner': None,
                            'landowner_name': '',
                            'father_name': '',
                            'caste': '',
                            'khasra': khasra,
                            'total_khasra': '',
                            'total_area': 0.0,
                                'tree_type': tree_type_name,
                                'tree_type_code': tree_line.tree_type or 'other',
                            'tree_count': 0,
                            'girth_cm': 0.0,
                            'rate': 0.0,
                            'value': 0.0,
                            'determined_value': 0.0,
                            'solatium': 0.0,
                            'interest': 0.0,
                            'total': 0.0,
                            'remark': '',
                        }
                    tree_data[key]['tree_count'] += tree_line.quantity or 0
                    tree_data[key]['girth_cm'] = tree_line.girth_cm or 0.0
                    tree_data[key]['rate'] = tree_line.rate_per_tree or 0.0
                    tree_data[key]['value'] += (tree_line.quantity or 0) * (tree_line.rate_per_tree or 0.0)
            else:
                # Process each landowner
                for landowner in landowners:
                    for tree_line in tree_lines:
                        tree_type_name = tree_line.tree_master_id.name if tree_line.tree_master_id else 'other'
                        key = (landowner.id, khasra, tree_type_name)
                        if key not in tree_data:
                            tree_data[key] = {
                                'landowner': landowner,
                                'landowner_name': landowner.name or '',
                                'father_name': landowner.father_name or landowner.spouse_name or '',
                                'caste': '',
                                'khasra': khasra,
                                'total_khasra': khasra,
                                'total_area': survey.acquired_area or 0.0,
                                'tree_type': tree_line.tree_master_id.name if tree_line.tree_master_id else 'other',
                                'tree_type_code': tree_line.tree_type or 'other',
                                'tree_count': 0,
                                'girth_cm': 0.0,
                                'rate': 0.0,
                                'value': 0.0,
                                'determined_value': 0.0,
                                'solatium': 0.0,
                                'interest': 0.0,
                                'total': 0.0,
                                'remark': '',
                            }
                        tree_data[key]['tree_count'] += tree_line.quantity or 0
                        tree_data[key]['girth_cm'] = tree_line.girth_cm or 0.0
                        # Calculate rate based on tree type and girth (placeholder - adjust based on actual rates)
                        rate = 6000.0 if tree_line.tree_type == 'fruit_bearing' else 177.0
                        tree_data[key]['rate'] = rate
                        tree_data[key]['value'] += (tree_line.quantity or 0) * rate
        
        # Calculate compensation amounts
        result = []
        for key, data in tree_data.items():
            determined_value = data['value']
            solatium = determined_value * 0.1  # 10% solatium
            interest = determined_value * 2.1  # Interest calculation (210%)
            total = determined_value + solatium + interest
            
            data['determined_value'] = determined_value
            data['solatium'] = solatium
            data['interest'] = interest
            data['total'] = total
            
            result.append(data)
        
        # Sort by landowner name, then khasra, then tree type
        result.sort(key=lambda x: (x['landowner_name'] or '', x['khasra'] or '', x.get('tree_type', '') or ''))
        
        return result

