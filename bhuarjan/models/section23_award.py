# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json
from .award_header_constants import get_award_header_constants

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
    award_structure_line_ids = fields.One2many(
        'bhu.award.structure.details',
        'award_id',
        string='Award Structure Entries / अवार्ड परिसम्पत्ति प्रविष्टियां'
    )
    
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

    _sql_constraints = [
        ('project_village_unique', 'unique(project_id, village_id)', 
         'Only one award per project and village is allowed! / प्रत्येक परियोजना और गाँव के लिए केवल एक अवार्ड की अनुमति है!')
    ]

    @api.constrains('project_id', 'village_id')
    def _check_unique_award(self):
        """Python constraint to prevent duplicates during creation/write"""
        for record in self:
            if record.project_id and record.village_id:
                existing = self.search([
                    ('project_id', '=', record.project_id.id),
                    ('village_id', '=', record.village_id.id),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(_('An award already exists for this Project and Village. / इस परियोजना और गाँव के लिए एक अवार्ड पहले से ही मौजूद है।'))

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
                    distance = survey.distance_from_main_road or 0.0
                    threshold = 50.0 if survey.survey_type == 'rural' else 20.0
                    new_lines.append((0, 0, {
                        'survey_id': survey.id,
                        'khasra_number': survey.khasra_number or '',
                        'land_type': survey.land_type_for_award or False,
                        'is_within_distance': distance <= threshold,
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
        """Download award document - Open wizard for PDF/Word"""
        self.ensure_one()
        return {
            'name': _('Download Section 23 Award / धारा 23 अवार्ड डाउनलोड करें'),
            'type': 'ir.actions.act_window',
            'res_model': 'bhu.award.download.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
                'default_report_xml_id': 'bhuarjan.action_report_section23_award',
                'default_filename': f'Section23_Award_{self.name}.doc'
            }
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

        self._sync_award_structure_lines()
        
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

    def _sync_award_structure_lines(self):
        """Link survey-level structure entries to this award."""
        self.ensure_one()
        survey_ids = self.award_survey_line_ids.mapped('survey_id').ids
        if not survey_ids:
            return
        structure_lines = self.env['bhu.award.structure.details'].search([
            ('survey_id', 'in', survey_ids),
        ])
        if structure_lines:
            structure_lines.write({'award_id': self.id})
    
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

    def _get_section4_approval_date(self):
        """Return section 4 approval date for this project/village."""
        self.ensure_one()
        if not self.project_id or not self.village_id:
            return False
        section4_records = self.env['bhu.section4.notification'].search([
            ('project_id', '=', self.project_id.id),
            ('village_id', '=', self.village_id.id),
        ], order='approved_date desc, signed_date desc, id desc', limit=10)
        for section4 in section4_records:
            for candidate in (
                section4.approved_date,
                section4.signed_date,
                section4.public_hearing_date,
                section4.public_hearing_datetime,
                section4.create_date,
            ):
                if candidate:
                    if isinstance(candidate, str):
                        return fields.Date.to_date(candidate)
                    if hasattr(candidate, 'date'):
                        return candidate.date()
                    return candidate
        return False

    def get_award_header_constants(self):
        """Shared award header labels used by Excel and PDF outputs."""
        self.ensure_one()
        return get_award_header_constants()

    def _get_award_calculation_date(self):
        """Return award creation date used for interest end date."""
        self.ensure_one()
        if self.create_date:
            return fields.Datetime.to_datetime(self.create_date).date()
        if self.award_date:
            return fields.Date.to_date(self.award_date)
        return fields.Date.context_today(self)

    def _calculate_interest_on_basic(self, basic_value):
        """Calculate 12% annual interest on basic value."""
        self.ensure_one()
        start_date = self._get_section4_approval_date()
        end_date = self._get_award_calculation_date()
        if not start_date or not end_date or not basic_value:
            return 0.0, 0
        if end_date < start_date:
            start_date, end_date = end_date, start_date
        days = (end_date - start_date).days
        if days <= 0:
            return 0.0, 0
        interest = basic_value * 0.12 * (days / 365.25)
        return interest, days

    @api.model
    def _is_fallow_survey(self, survey):
        """Return True when survey is fallow (पड़ती) land."""
        if not survey or not survey.crop_type_id:
            return False
        crop_code = (survey.crop_type_id.code or '').upper()
        crop_name = (survey.crop_type_id.name or '')
        return crop_code == 'FALLOW' or 'पड़ती' in crop_name

    @api.model
    def _get_min_rehab_rate_per_acre(self, is_fallow, is_irrigated, is_unirrigated):
        """
        Minimum rehab policy rates (per acre):
        - Fallow (पड़ती): 6,00,000
        - Unirrigated (असिंचित): 8,00,000
        - Irrigated (सिंचित): 10,00,000
        """
        if is_fallow:
            return 600000.0
        if is_irrigated:
            return 1000000.0
        if is_unirrigated:
            return 800000.0
        # Safe default when irrigation type is missing
        return 800000.0

    def get_interest_period_note(self):
        """Text note for report header interest period."""
        self.ensure_one()
        start_date = self._get_section4_approval_date()
        end_date = self._get_award_calculation_date()
        if start_date and end_date:
            if end_date < start_date:
                start_date, end_date = end_date, start_date
            return f"{start_date.strftime('%d/%m/%Y')} से {end_date.strftime('%d/%m/%Y')} तक"
        return "धारा 4 स्वीकृति दिनांक से अवार्ड दिनांक तक"
    
    def get_land_compensation_data(self):
        """Get land compensation data grouped by landowner and khasra"""
        self.ensure_one()
        acre_per_hectare = 2.47105381
        
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
            is_fallow = self._is_fallow_survey(survey)
            is_diverted = survey.has_traded_land == 'yes'
            
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
                        'address': '',
                        'khasra': khasra,
                        'original_area': 0.0,
                        'acquired_area': 0.0,
                        'lagan': khasra,  # Using khasra as lagan
                        'fallow': is_fallow,
                        'unirrigated': False,
                        'irrigated': False,
                        'is_diverted': is_diverted,
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
                            'address': landowner.owner_address or '',
                            'khasra': khasra,
                            'original_area': 0.0,
                            'acquired_area': 0.0,
                            'lagan': khasra,
                            'fallow': is_fallow,
                            'unirrigated': is_unirrigated,
                            'irrigated': is_irrigated,
                            'is_diverted': is_diverted,
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
        # Convert to list and calculate totals matching the 19 columns
        result = []
        for key, data in compensation_data.items():
            # Get survey to access proper rates if possible
            survey = self.env['bhu.survey'].search([
                ('project_id', '=', self.project_id.id),
                ('village_id', '=', self.village_id.id),
                ('khasra_number', '=', data['khasra'])
            ], limit=1)
            
            # Derive main-road status from measured distance.
            # Rule: rural <= 50m is MR, urban <= 20m is MR; 0/blank counts as MR.
            distance_from_main_road = (survey.distance_from_main_road or 0.0) if survey else 0.0
            if survey:
                threshold = 50.0 if survey.survey_type == 'rural' else 20.0
                derived_is_within_distance = distance_from_main_road <= threshold
            else:
                derived_is_within_distance = False

            # Use computed rate from award line if available
            award_line = self.award_survey_line_ids.filtered(lambda l: l.survey_id.id == survey.id)
            has_award_line = bool(award_line)
            guide_line_rate = award_line[0].rate_per_hectare if has_award_line else 2112000.0
            is_within_distance = derived_is_within_distance
            is_diverted = survey.has_traded_land == 'yes'

            # Business rule: +25% on guideline rate for diverted land within main road range.
            # Avoid double-application when survey line already computed this uplift.
            if (not has_award_line) and is_diverted and is_within_distance:
                guide_line_rate *= 1.25
            
            # Logic matching 19-column image:
            # 13: basic_value = rate * area
            # 14: market_value = basic_value * factor (2)
            # 15: solatium = market_value * 1.0
            # 16: interest = basic value * 12% from section 4 approval to award date
            
            market_value_basic = data['acquired_area'] * guide_line_rate
            market_value_factored = market_value_basic * 2.0
            solatium = market_value_factored * 1.0 # 100%
            
            interest, _days = self._calculate_interest_on_basic(market_value_basic)
            
            total_compensation = market_value_factored + solatium + interest
            acquired_area_acre = data['acquired_area'] * acre_per_hectare
            rehab_rate_per_acre = self._get_min_rehab_rate_per_acre(
                data.get('fallow'),
                data.get('irrigated'),
                data.get('unirrigated'),
            )
            rehab_policy_amount = acquired_area_acre * rehab_rate_per_acre
            payable_compensation = max(total_compensation, rehab_policy_amount)
            
            data.update({
                'guide_line_rate': guide_line_rate,
                'basic_value': market_value_basic,
                'market_value': market_value_factored,
                'solatium': solatium,
                'interest': interest,
                'total_compensation': total_compensation,
                'rehab_policy_rate_per_acre': rehab_rate_per_acre,
                'rehab_policy_amount': rehab_policy_amount,
                'paid_compensation': payable_compensation,
                'remark': '',
                'original_area': survey.total_area if survey else 0.0,
                'lagan': survey.lagan if (survey and hasattr(survey, 'lagan')) else data['khasra'],
                'is_within_distance': is_within_distance,
                'distance_from_main_road': distance_from_main_road,
                'is_diverted': is_diverted,
            })
            
            result.append(data)
        
        # Sort by landowner name, then khasra
        result.sort(key=lambda x: (x['landowner_name'] or '', x['khasra'] or ''))
        
        return result

    def get_land_compensation_grouped_data(self):
        """Group land rows by owner so multiple khasras appear together."""
        self.ensure_one()
        land_data = self.get_land_compensation_data()
        grouped = {}
        ordered_keys = []
        def _khasra_sort_key(line):
            khasra = (line.get('khasra') or '').strip()
            if not khasra:
                return (1, 10**12, 10**12, '')
            parts = khasra.split('/', 1)
            main = int(parts[0]) if parts[0].isdigit() else 10**12
            sub = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10**12
            return (0, main, sub, khasra)
        numeric_totals = (
            'original_area', 'acquired_area', 'basic_value', 'market_value',
            'solatium', 'interest', 'total_compensation', 'rehab_policy_amount', 'paid_compensation',
        )
        for row in land_data:
            if row.get('landowner_name'):
                # Group by beneficiary identity (name + father/spouse) so duplicate
                # landowner master IDs with same beneficiary still merge in one block.
                beneficiary_name = (row.get('landowner_name') or '').strip().lower()
                father_name = (row.get('father_name') or '').strip().lower()
                key = ('beneficiary', beneficiary_name, father_name)
            else:
                key = ('khasra', row.get('khasra') or '')
            if key not in grouped:
                grouped[key] = {
                    'landowner_name': row.get('landowner_name', ''),
                    'father_name': row.get('father_name', ''),
                    'address': row.get('address', ''),
                    'lines': [],
                    'khasra_count': 0,
                    'khasra_seen': set(),
                }
                for field_name in numeric_totals:
                    grouped[key][field_name] = 0.0
                ordered_keys.append(key)
            group = grouped[key]
            group['lines'].append(row)
            khasra = row.get('khasra') or ''
            if khasra and khasra not in group['khasra_seen']:
                group['khasra_seen'].add(khasra)
                group['khasra_count'] += 1
            for field_name in numeric_totals:
                group[field_name] += row.get(field_name, 0.0) or 0.0

        result = []
        for key in ordered_keys:
            group = grouped[key]
            group['lines'] = sorted(group.get('lines', []), key=_khasra_sort_key)
            group.pop('khasra_seen', None)
            result.append(group)
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
                    rate_per_tree = tree_line.get_applicable_rate()
                    tree_data[key]['tree_count'] += tree_line.quantity or 0
                    tree_data[key]['girth_cm'] = tree_line.girth_cm or 0.0
                    tree_data[key]['rate'] = rate_per_tree
                    tree_data[key]['value'] += (tree_line.quantity or 0) * rate_per_tree
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

    def get_structure_compensation_data(self):
        """Get structure compensation data from shared award structure entries."""
        self.ensure_one()
        surveys = self.env['bhu.survey'].search([
            ('project_id', '=', self.project_id.id),
            ('village_id', '=', self.village_id.id),
            ('state', 'in', ['approved', 'locked']),
            ('khasra_number', '!=', False),
        ])
        if not surveys:
            return []

        structure_lines = self.env['bhu.award.structure.details'].search([
            ('survey_id', 'in', surveys.ids),
        ])
        if not structure_lines:
            return []

        structure_data = []
        for line in structure_lines:
            survey = line.survey_id
            total_value = line.line_total or 0.0
            base_row = {
                'total_khasra': survey.khasra_number or '',
                'total_area': survey.total_area or 0.0,
                'asset_khasra': survey.khasra_number or '',
                'asset_land_area': survey.acquired_area or 0.0,
                'asset_type': line.get_structure_type_label(),
                'asset_code': 4,
                'asset_dimension': (line.asset_count or 0.0) if line.structure_type == 'well' else (line.area_sqm or 0.0),
                'remark': line.description or '',
            }
            owners = survey.landowner_ids
            if owners:
                owner_count = len(owners)
                share = total_value / owner_count if owner_count else total_value
                for owner in owners:
                    structure_data.append({
                        **base_row,
                        'landowner_name': owner.name or '',
                        'father_name': owner.father_name or owner.spouse_name or '',
                        'market_value': share,
                        'solatium': share,
                        'interest': 0.0,
                        'total': share * 2.0,
                    })
            else:
                structure_data.append({
                    **base_row,
                    'landowner_name': '',
                    'father_name': '',
                    'market_value': total_value,
                    'solatium': total_value,
                    'interest': 0.0,
                    'total': total_value * 2.0,
                })
        return structure_data

    def get_tree_compensation_grouped_data(self):
        """Group tree rows by owner for report rowspans/subtotals."""
        self.ensure_one()
        tree_data = self.get_tree_compensation_data()
        grouped = {}
        ordered_keys = []
        numeric_totals = ('total_area', 'tree_count', 'value', 'solatium', 'interest', 'total')
        for row in tree_data:
            owner = row.get('landowner')
            if owner:
                key = ('owner', owner.id)
            elif row.get('landowner_name'):
                key = ('name', row.get('landowner_name'), row.get('father_name') or '')
            else:
                key = ('khasra', row.get('khasra') or '')
            if key not in grouped:
                grouped[key] = {
                    'landowner_name': row.get('landowner_name', ''),
                    'father_name': row.get('father_name', ''),
                    'lines': [],
                    'khasra_count': 0,
                    'khasra_seen': set(),
                }
                for field_name in numeric_totals:
                    grouped[key][field_name] = 0.0
                ordered_keys.append(key)
            group = grouped[key]
            group['lines'].append(row)
            khasra = row.get('khasra') or ''
            if khasra and khasra not in group['khasra_seen']:
                group['khasra_seen'].add(khasra)
                group['khasra_count'] += 1
            for field_name in numeric_totals:
                group[field_name] += row.get(field_name, 0.0) or 0.0

        result = []
        for key in ordered_keys:
            group = grouped[key]
            group.pop('khasra_seen', None)
            result.append(group)
        return result

    def get_structure_compensation_grouped_data(self):
        """Group structure rows by owner for report rowspans/subtotals."""
        self.ensure_one()
        structure_data = self.get_structure_compensation_data()
        grouped = {}
        ordered_keys = []
        numeric_totals = ('total_area', 'asset_land_area', 'asset_dimension', 'market_value', 'solatium', 'interest', 'total')
        for row in structure_data:
            if row.get('landowner_name'):
                key = ('name', row.get('landowner_name'), row.get('father_name') or '')
            else:
                key = ('khasra', row.get('asset_khasra') or '')
            if key not in grouped:
                grouped[key] = {
                    'landowner_name': row.get('landowner_name', ''),
                    'father_name': row.get('father_name', ''),
                    'lines': [],
                    'khasra_count': 0,
                    'khasra_seen': set(),
                }
                for field_name in numeric_totals:
                    grouped[key][field_name] = 0.0
                ordered_keys.append(key)
            group = grouped[key]
            group['lines'].append(row)
            khasra = row.get('asset_khasra') or row.get('total_khasra') or ''
            if khasra and khasra not in group['khasra_seen']:
                group['khasra_seen'].add(khasra)
                group['khasra_count'] += 1
            for field_name in numeric_totals:
                group[field_name] += row.get(field_name, 0.0) or 0.0

        result = []
        for key in ordered_keys:
            group = grouped[key]
            group.pop('khasra_seen', None)
            result.append(group)
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
    
    @api.depends('land_type', 'is_within_distance', 'award_id.village_id', 'survey_id.irrigation_type', 'survey_id.has_traded_land')
    def _compute_rate_per_hectare(self):
        """Compute rate per hectare from rate master based on type and distance"""
        for line in self:
            rate = 0.0
            if line.award_id and line.award_id.village_id and line.land_type:
                # Get rate master for this village (prioritize active, but allow draft)
                rate_master = self.env['bhu.rate.master'].search([
                    ('village_id', '=', line.award_id.village_id.id),
                    ('state', 'in', ['active', 'draft']),
                ], limit=1, order='state ASC, effective_from DESC')
                
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
                    elif irrigation_type in ['non_irrigated', 'unirrigated']:
                        rate = base_rate * 0.8
                    else:
                        rate = base_rate

                    # Business rule: +25% for diverted land within main-road distance.
                    if line.survey_id.has_traded_land == 'yes' and line.is_within_distance:
                        rate = rate * 1.25
            
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
                distance = line.survey_id.distance_from_main_road or 0.0
                threshold = 50.0 if line.survey_id.survey_type == 'rural' else 20.0
                line.is_within_distance = distance <= threshold
    
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
                        distance = survey.distance_from_main_road or 0.0
                        threshold = 50.0 if survey.survey_type == 'rural' else 20.0
                        vals['is_within_distance'] = distance <= threshold
        
        lines = super().create(vals_list)
        
        # Sync type and distance to survey after creation
        for line in lines:
            if line.survey_id and (line.land_type or line.is_within_distance is not False):
                line.survey_id.write({
                    'land_type_for_award': line.land_type,
                    'is_within_distance_for_award': line.is_within_distance,
                })
        
        return lines

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

    def action_download_excel(self):
        """Generate and download Excel report directly using xlsxwriter"""
        self.ensure_one()
        import io
        import base64
        try:
            import xlsxwriter
        except ImportError:
            raise ValidationError(_("Python library 'xlsxwriter' is not installed."))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        sheet = workbook.add_worksheet('Section 23 Award Summary')

        # Formats
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#8B4513', 'color': 'white', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter'})
        label_fmt = workbook.add_format({
            'bold': True,
            'border': 1,
            'bg_color': '#f8fafc',
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
        })
        value_fmt = workbook.add_format({'border': 1})
        yes_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#2e7d32', 'color': 'white', 'bold': True})
        no_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#c62828', 'color': 'white', 'bold': True})
        money_fmt = workbook.add_format({'border': 1, 'num_format': '₹#,##0.00'})
        total_fmt = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#e2e8f0', 'num_format': '₹#,##0.00'})

        sheet.set_column('A:A', 10)
        sheet.set_column('B:B', 40)
        sheet.set_column('C:K', 15)

        # Header
        sheet.merge_range('A1:K1', 'SECTION 23 AWARD SUMMARY / धारा 23 अवार्ड सारांश', title_fmt)
        sheet.write(2, 0, 'Village / ग्राम', label_fmt); sheet.write(2, 1, self.village_id.name or '', value_fmt)
        sheet.write(3, 0, 'Project / परियोजना', label_fmt); sheet.write(3, 1, self.project_id.name or '', value_fmt)
        sheet.write(4, 0, 'Award Date', label_fmt); sheet.write(4, 1, str(self.award_date or ''), value_fmt)

        row = 6
        # Land Section
        award_headers = self.get_award_header_constants()
        sheet.merge_range(row, 0, row, 19, award_headers['excel']['section23_land_title'], header_fmt)
        row += 1
        headers = award_headers['excel']['section23_land_headers']
        sheet.set_row(row, 90)
        for col, h in enumerate(headers):
            sheet.write(row, col, h, label_fmt)
        row += 1

        land_data = self.get_land_compensation_data()
        total_acquired = 0.0
        total_basic = 0.0
        total_market = 0.0
        total_solatium = 0.0
        total_interest = 0.0
        total_comp = 0.0
        total_rehab = 0.0
        total_paid = 0.0
        
        for i, land in enumerate(land_data, 1):
            details = f"{land.get('landowner_name', '')} {land.get('father_name', '')} {land.get('address', '')}"
            sheet.write(row, 0, i, value_fmt)
            sheet.write(row, 1, details, value_fmt)
            sheet.write(row, 2, land.get('khasra', ''), value_fmt)
            sheet.write(row, 3, land.get('original_area', 0.0), value_fmt)
            sheet.write(row, 4, land.get('khasra', ''), value_fmt) # Acquired Khasra
            sheet.write(row, 5, land.get('acquired_area', 0.0), value_fmt)
            is_within_distance = bool(land.get('is_within_distance'))
            is_irrigated = bool(land.get('irrigated'))
            is_unirrigated = bool(land.get('unirrigated'))
            is_diverted = bool(land.get('is_diverted'))
            distance_value = land.get('distance_from_main_road') or 0.0
            if distance_value and is_within_distance:
                sheet.write(row, 6, f"{distance_value:.2f} m",
                            yes_fmt if is_within_distance else no_fmt)
            else:
                sheet.write(row, 6, 'Yes' if is_within_distance else 'No',
                            yes_fmt if is_within_distance else no_fmt)
            if is_within_distance:
                # Main-road khasra: irrigated/unirrigated/diverted split is not applicable.
                sheet.write(row, 7, 'NA', value_fmt)
                sheet.write(row, 8, 'NA', value_fmt)
                sheet.write(row, 9, 'NA', value_fmt)
            else:
                sheet.write(row, 7, 'Yes' if is_irrigated else 'No', yes_fmt if is_irrigated else no_fmt)
                sheet.write(row, 8, 'Yes' if is_unirrigated else 'No', yes_fmt if is_unirrigated else no_fmt)
                sheet.write(row, 9, 'Yes' if is_diverted else 'No', yes_fmt if is_diverted else no_fmt)
            sheet.write(row, 10, '', value_fmt) # 3 years avg sale rate
            sheet.write(row, 11, land.get('guide_line_rate', 0.0), money_fmt)
            sheet.write(row, 12, land.get('basic_value', 0.0), money_fmt)
            sheet.write(row, 13, land.get('market_value', 0.0), money_fmt)
            sheet.write(row, 14, land.get('solatium', 0.0), money_fmt)
            sheet.write(row, 15, land.get('interest', 0.0), money_fmt)
            sheet.write(row, 16, land.get('total_compensation', 0.0), money_fmt)
            sheet.write(row, 17, land.get('rehab_policy_amount', 0.0), money_fmt)
            sheet.write(row, 18, land.get('paid_compensation', 0.0), money_fmt)
            sheet.write(row, 19, land.get('remark', ''), value_fmt)
            
            total_acquired += land.get('acquired_area', 0.0)
            total_basic += land.get('basic_value', 0.0)
            total_market += land.get('market_value', 0.0)
            total_solatium += land.get('solatium', 0.0)
            total_interest += land.get('interest', 0.0)
            total_comp += land.get('total_compensation', 0.0)
            total_rehab += land.get('rehab_policy_amount', 0.0)
            total_paid += land.get('paid_compensation', 0.0)
            row += 1

        # Land Total row
        sheet.merge_range(row, 0, row, 4, 'MAHAYOG (TOTAL) / महायोग', label_fmt)
        sheet.write(row, 5, total_acquired, total_fmt)
        sheet.write(row, 12, total_basic, total_fmt)
        sheet.write(row, 13, total_market, total_fmt)
        sheet.write(row, 14, total_solatium, total_fmt)
        sheet.write(row, 15, total_interest, total_fmt)
        sheet.write(row, 16, total_comp, total_fmt)
        sheet.write(row, 17, total_rehab, total_fmt)
        sheet.write(row, 18, total_paid, total_fmt)
        
        row += 2
        # Tree Section (Brief)
        sheet.merge_range(row, 0, row, 10, 'TREE COMPENSATION / वृक्ष मुआवजा', header_fmt)
        row += 1
        tree_data = self.get_tree_compensation_data()
        if tree_data:
            headers = award_headers['excel']['section23_tree_brief_headers']
            for col, h in enumerate(headers):
                sheet.write(row, col, h, label_fmt)
            row += 1
            
            total_tree_comp = 0.0
            for i, tree in enumerate(tree_data, 1):
                sheet.write(row, 0, i, value_fmt)
                sheet.write(row, 1, tree.get('landowner_name', ''), value_fmt)
                sheet.write(row, 2, tree.get('khasra', ''), value_fmt)
                sheet.write(row, 3, tree.get('tree_type', ''), value_fmt)
                sheet.write(row, 4, tree.get('tree_count', 0), value_fmt)
                sheet.write(row, 5, tree.get('determined_value', 0.0), money_fmt)
                sheet.write(row, 6, tree.get('solatium', 0.0), money_fmt)
                sheet.write(row, 7, tree.get('interest', 0.0), money_fmt)
                sheet.write(row, 8, tree.get('total', 0.0), money_fmt)
                total_tree_comp += tree.get('total', 0.0)
                row += 1
            
            sheet.merge_range(row, 0, row, 7, 'TOTAL TREE COMPENSATION', label_fmt)
            sheet.write(row, 8, total_tree_comp, total_fmt)

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())
        output.close()

        attachment = self.env['ir.attachment'].create({
            'name': f"Section23_Award_{self.village_id.name or 'Export'}.xlsx",
            'type': 'binary',
            'datas': file_data,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
