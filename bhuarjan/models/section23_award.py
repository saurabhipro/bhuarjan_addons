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
    
    # Award document
    award_document = fields.Binary(string='Award Document / अवार्ड दस्तावेज़', tracking=False)
    award_document_filename = fields.Char(string='Document Filename / दस्तावेज़ फ़ाइल नाम', tracking=True)
    
    # Notes
    notes = fields.Text(string='Notes / नोट्स', tracking=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('sent_back', 'Sent Back')
    ], string='Status', default='draft', tracking=True)
    
    is_generated = fields.Boolean(string='Is Generated', default=False, tracking=True)
    
    village_domain = fields.Char()
    
    # Survey lines for award generation
    award_survey_line_ids = fields.One2many('bhu.section23.award.survey.line', 'award_id', 
                                            string='Approved Surveys / स्वीकृत सर्वेक्षण',
                                            help='Select type and distance for each approved survey')
    
    # Rate Permutations for Village (read-only, computed)
    rate_permutation_ids = fields.One2many('bhu.rate.master.permutation.line', 'award_id', 
                                           string='Rate Permutations', readonly=True, 
                                           compute='_compute_rate_permutations', store=False)
    
    # Computed field to check if all surveys have type and distance selected
    all_surveys_configured = fields.Boolean(string='All Surveys Configured', 
                                           compute='_compute_all_surveys_configured',
                                           help='True when all surveys have type and distance selected')
    
    # User Role Fields for UI Logic
    is_sdm = fields.Boolean(compute='_compute_user_roles')
    is_section_officer = fields.Boolean(compute='_compute_user_roles')
    is_admin = fields.Boolean(compute='_compute_user_roles')

    def _compute_user_roles(self):
        for rec in self:
            rec.is_sdm = self.env.user.has_group('bhuarjan.group_bhuarjan_sdm')
            rec.is_section_officer = self.env.user.has_group('bhuarjan.group_bhu_section_officer')
            rec.is_admin = self.env.user.has_group('bhuarjan.group_bhuarjan_admin')
    
    @api.depends('village_id')
    def _compute_rate_permutations(self):
        """Compute rate permutations for the selected village"""
        for award in self:
            # Clear existing
            award.rate_permutation_ids = [(5, 0, 0)]
            if award.village_id:
                # Get active rate master for this village
                rate_master = self.env['bhu.rate.master'].get_all_rates_for_village(award.village_id.id)
                if rate_master:
                    permutations = rate_master.get_all_permutations()
                    # Create transient records to display
                    lines = []
                    for perm in permutations:
                        line = self.env['bhu.rate.master.permutation.line'].create({
                            'award_id': award.id,
                            'road_proximity': perm['road_proximity'],
                            'irrigation_status': perm['irrigation_status'],
                            'is_diverted': perm['is_diverted'],
                            'calculated_rate': perm['rate'],
                        })
                        lines.append(line.id)
                    award.rate_permutation_ids = [(6, 0, lines)]
    
    @api.depends('award_survey_line_ids.land_type', 'award_survey_line_ids.is_within_distance')
    def _compute_all_surveys_configured(self):
        """Check if all survey lines have type and distance configured"""
        for record in self:
            if not record.award_survey_line_ids:
                record.all_surveys_configured = False
            else:
                # land_type must be set (Village or Residential)
                # is_within_distance can be True or False (both are valid - checked or unchecked)
                # We just need to ensure land_type is set
                record.all_surveys_configured = all(
                    line.land_type for line in record.award_survey_line_ids
                )
    
    @api.onchange('village_id', 'project_id')
    def _onchange_village_populate_surveys(self):
        """Auto-populate approved surveys when village is selected"""
        if self.project_id and self.village_id:
            # Get approved surveys for this village and project
            surveys = self.env['bhu.survey'].search([
                ('project_id', '=', self.project_id.id),
                ('village_id', '=', self.village_id.id),
                ('state', 'in', ['approved', 'locked']),
            ])
            
            # Create or update survey lines
            existing_survey_ids = self.award_survey_line_ids.mapped('survey_id').ids
            new_lines = []
            
            for survey in surveys:
                if survey.id not in existing_survey_ids:
                    # Create new line - sync existing values from survey if available
                    new_lines.append((0, 0, {
                        'survey_id': survey.id,
                        'khasra_number': survey.khasra_number or '',
                        'land_type': survey.land_type_for_award or False,
                        'is_within_distance': survey.is_within_distance_for_award or False,
                    }))
            
            if new_lines:
                self.award_survey_line_ids = new_lines
        else:
            self.award_survey_line_ids = [(5, 0, 0)]
    
    @api.onchange('project_id')
    def _onchange_project_id(self):
        """Reset village when project changes and set domain"""
        for rec in self:
            if rec.project_id and rec.project_id.village_ids:
                rec.village_domain = json.dumps([('id', 'in', rec.project_id.village_ids.ids)])
            else:
                rec.village_domain = json.dumps([])
                rec.village_id = False
            # Trigger survey population if village is already set
            if rec.village_id:
                rec._onchange_village_populate_surveys()
    
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
            
        if not self.award_survey_line_ids:
            raise ValidationError(_('No approved surveys found for this village. Cannot generate award.\n इस गाँव के लिए कोई स्वीकृत सर्वेक्षण नहीं मिला। अवार्ड उत्पन्न नहीं किया जा सकता।'))
        
        # Validate that all surveys have type configured
        # is_within_distance can be True or False (both are valid - checked or unchecked means user has made a choice)
        missing_lines = self.award_survey_line_ids.filtered(lambda l: not l.land_type)
        
        if missing_lines:
            survey_names = ', '.join([line.survey_id.name for line in missing_lines if line.survey_id][:5])
            if len(missing_lines) > 5:
                survey_names += '...'
            raise ValidationError(_(
                'Please select type (Village/Residential) for all surveys before generating award.\n'
                'Missing type selection for surveys: %s'
            ) % survey_names)
        
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
                    'award_document_filename': filename,
                    'is_generated': True
                })
                
                # Return download action
                return {
                    'type': 'ir.actions.act_url',
                    'url': f'/web/content/{self._name}/{self.id}/award_document/{filename}?download=true',
                    'target': 'self',
                }
        
        # Fallback to standard report action if PDF generation fails
        self.write({'is_generated': True})
        return report_action.report_action(self)
    
    def action_submit_award(self):
        """Submit the award after document upload"""
        self.ensure_one()
        if not self.award_document:
            raise ValidationError(_('Please upload the signed award document before submitting.\nकृपया जमा करने से पहले हस्ताक्षरित अवार्ड दस्तावेज़ अपलोड करें।'))
        
        self.write({
            'state': 'submitted'
        })
        
        # Log activity
        self.message_post(body=_("Award submitted with signed document."))

    def action_approve_award(self):
        """Approve the award"""
        self.ensure_one()
        self.write({'state': 'approved'})
        self.message_post(body=_("Award approved."))

    def action_send_back_award(self):
        """Send back the award for correction"""
        self.ensure_one()
        self.write({'state': 'sent_back'})
        self.message_post(body=_("Award sent back for correction."))
    
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
    
    def format_indian_number(self, value, decimals=2):
        """Format number with Indian numbering system (commas for thousands)"""
        if value is None:
            value = 0.0
        
        # Format the number with commas (Indian numbering system)
        if decimals == 2:
            formatted = f"{value:,.2f}"
        elif decimals == 4:
            formatted = f"{value:,.4f}"
        else:
            formatted = f"{value:,.{decimals}f}"
        
        return formatted
    
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


class Section23AwardSurveyLine(models.Model):
    """Survey lines for Section 23 Award - allows selection of type and distance for each survey"""
    _name = 'bhu.section23.award.survey.line'
    _description = 'Section 23 Award Survey Line'
    _order = 'survey_id'
    
    award_id = fields.Many2one('bhu.section23.award', string='Award', required=True, ondelete='cascade')
    survey_id = fields.Many2one('bhu.survey', string='Survey / सर्वेक्षण', required=True, ondelete='cascade')
    
    # Survey information (readonly, from survey)
    khasra_number = fields.Char(string='Khasra Number / खसरा संख्या', readonly=True)
    acquired_area = fields.Float(string='Acquired Area (Hectare) / अधिग्रहित क्षेत्र (हेक्टेयर)', 
                                 related='survey_id.acquired_area', readonly=True, store=True)
    survey_name = fields.Char(string='Survey Number', related='survey_id.name', readonly=True, store=True)
    survey_date = fields.Date(string='Survey Date', related='survey_id.survey_date', readonly=True, store=True)
    
    # Type selection (Village or Residential) - radio button
    # These fields sync with survey model
    land_type = fields.Selection([
        ('village', 'Village / ग्राम'),
        ('residential', 'Residential / आवासीय')
    ], string='Type / प्रकार', required=True, default='village',
       help='Select whether this is village land or residential land')
    
    # Distance checkbox
    # For village: 20 meters from main road
    # For residential: 05 meters from main road
    is_within_distance = fields.Boolean(string='Within Distance / दूरी के भीतर', 
                                       default=False,
                                       help='Check if khasra is within distance from main road (20m for village, 5m for residential)')
    
    @api.onchange('land_type', 'is_within_distance')
    def _onchange_type_distance(self):
        """Sync type and distance to survey model and trigger rate recompute"""
        for line in self:
            if line.survey_id:
                line.survey_id.write({
                    'land_type_for_award': line.land_type,
                    'is_within_distance_for_award': line.is_within_distance,
                })
            # Force recompute for immediate UI feedback
            line._compute_rate_per_hectare()
    
    def write(self, vals):
        """Sync type and distance to survey when updating"""
        result = super().write(vals)
        for line in self:
            if line.survey_id and ('land_type' in vals or 'is_within_distance' in vals):
                line.survey_id.write({
                    'land_type_for_award': line.land_type,
                    'is_within_distance_for_award': line.is_within_distance,
                })
        return result
    
    # Computed rate per hectare from rate master
    rate_per_hectare = fields.Monetary(string='Rate per Hectare / हेक्टेयर दर', 
                                      currency_field='currency_id',
                                      compute='_compute_rate_per_hectare', store=True,
                                      help='Rate per hectare fetched from rate master based on type and distance')
    
    currency_id = fields.Many2one('res.currency', string='Currency', 
                                  default=lambda self: self.env.ref('base.INR'))
    
    @api.depends('land_type', 'is_within_distance', 'award_id.village_id', 'survey_id.irrigation_type')
    def _compute_rate_per_hectare(self):
        """Compute rate per hectare from rate master based on type and distance"""
        for line in self:
            rate = 0.0
            if line.award_id and line.award_id.village_id and line.land_type:
                # Get active rate master for this village
                rate_master = self.env['bhu.rate.master'].search([
                    ('village_id', '=', line.award_id.village_id.id),
                    ('state', '=', 'active'),
                ], limit=1, order='effective_from desc')
                
                if rate_master:
                    # Determine which rate to use based on type and distance
                    # Default to village rules if not set
                    land_type = line.land_type or 'village'
                    
                    if land_type == 'village':
                        # Village: 20 meters
                        if line.is_within_distance:
                            base_rate = rate_master.main_road_rate_hectare
                        else:
                            base_rate = rate_master.other_road_rate_hectare
                    else:
                        # Residential: 5 meters
                        if line.is_within_distance:
                            base_rate = rate_master.main_road_rate_hectare
                        else:
                            base_rate = rate_master.other_road_rate_hectare
                    
                    # Apply irrigation adjustment from survey
                    # Rules from Land Rate Master get_rate_for_land:
                    # Irrigated: +20% (1.2), Non-Irrigated: -20% (0.8)
                    irrigation_type = line.survey_id.irrigation_type if line.survey_id else False
                    
                    if irrigation_type == 'irrigated':
                        rate = base_rate * 1.2
                    elif irrigation_type in ['unirrigated', 'non_irrigated']:
                        rate = base_rate * 0.8
                    else:
                        rate = base_rate
            
            line.rate_per_hectare = rate
    
    @api.onchange('survey_id')
    def _onchange_survey_id(self):
        """Update khasra number and sync values when survey is selected"""
        for line in self:
            if line.survey_id:
                line.khasra_number = line.survey_id.khasra_number or ''
                # Load existing values from survey if available
                if not line.land_type and line.survey_id.land_type_for_award:
                    line.land_type = line.survey_id.land_type_for_award
                if line.is_within_distance is False and line.survey_id.is_within_distance_for_award:
                    line.is_within_distance = line.survey_id.is_within_distance_for_award
    
    @api.model_create_multi
    def create(self, vals_list):
        """Auto-populate khasra number and sync to survey when creating"""
        for vals in vals_list:
            # Auto-populate khasra number from survey
            if 'survey_id' in vals and 'khasra_number' not in vals:
                survey = self.env['bhu.survey'].browse(vals['survey_id'])
                if survey:
                    vals['khasra_number'] = survey.khasra_number or ''
                    # Also sync existing values from survey if not provided
                    if 'land_type' not in vals and survey.land_type_for_award:
                        vals['land_type'] = survey.land_type_for_award
                    if 'is_within_distance' not in vals:
                        vals['is_within_distance'] = survey.is_within_distance_for_award or False
        
        lines = super().create(vals_list)
        
        # Sync type and distance to survey after creation
        for line in lines:
            if line.survey_id and (line.land_type or line.is_within_distance is not False):
                line.survey_id.write({
                    'land_type_for_award': line.land_type,
                    'is_within_distance_for_award': line.is_within_distance,
                })
        
        return lines

