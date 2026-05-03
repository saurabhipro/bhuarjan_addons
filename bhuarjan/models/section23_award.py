# -*- coding: utf-8 -*-

import json
import logging
import base64
import re
import time
from markupsafe import Markup, escape

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from .award_header_constants import get_award_header_constants

_logger = logging.getLogger(__name__)

class Section23Award(models.Model):
    _name = 'bhu.section23.award'
    _description = 'Section 23 Award'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Award Reference / अवार्ड संदर्भ', required=True, tracking=True, default='New')
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True, tracking=True, index=True, ondelete='cascade')
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम', required=True, tracking=True, index=True)
    
    # Department - computed from project (for filtering purposes)
    department_id = fields.Many2one('bhu.department', string='Department / विभाग', 
                                   related='project_id.department_id', store=True, readonly=True)
    
    # Award details
    award_date = fields.Date(string='Award Date / अवार्ड दिनांक', default=fields.Date.today, tracking=True)
    case_number = fields.Char(
        string='Case Number / प्रकरण क्रमांक',
        tracking=True,
        help='Land acquisition case/proceeding number (e.g., SEC23-New, SEC23-2024-001)'
    )
    section4_hearing_date = fields.Date(
        string='Section 4 Public Hearing Date / धारा 4 सार्वजनिक सुनवाई दिनांक',
        compute='_compute_section4_hearing_date',
        store=False,
        readonly=True,
        help='Automatically fetched from Section 4 notification public hearing date'
    )
    avg_three_year_sales_sort_rate = fields.Float(
        string='Avg. sales sort rate (3 years) / विगत तीन वर्षों का औसत बिक्री छांट दर',
        digits=(16, 4),
        required=True,
        default=0.0,
        tracking=True,
        help='Mandatory before generating the award; shown on land schedule (Excel/PDF).',
    )

    # Award rate inputs (defaulted from active rate master; editable on the award)
    rate_master_main_road_ha = fields.Monetary(
        string='MR Rate (₹/Ha)', currency_field='currency_id',
        default=0.0,
        tracking=True,
        help='Main Road rate per hectare from the active land rate master for this village.',
    )
    rate_master_other_road_ha = fields.Monetary(
        string='BMR Rate (₹/Ha)', currency_field='currency_id',
        default=0.0,
        tracking=True,
        help='Beyond Main Road rate per hectare from the active land rate master for this village.',
    )
    rate_master_main_road_sqm = fields.Float(
        string='MR Plot Rate (₹/sqm)',
        digits=(16, 2),
        default=0.0,
        tracking=True,
    )
    rate_master_other_road_sqm = fields.Float(
        string='BMR Plot Rate (₹/sqm)',
        digits=(16, 2),
        default=0.0,
        tracking=True,
    )

    # Village profile for this award (defaulted from village master; editable on award)
    village_type = fields.Selection([
        ('rural', 'Rural / ग्रामीण'),
        ('urban', 'Urban / नगरीय'),
    ], string='Village Type / ग्राम प्रकार',
       default='rural', tracking=True)

    # Urban award settings
    urban_body_type = fields.Selection([
        ('nagar_nigam',     'Nagar Nigam / नगर निगम'),
        ('nagar_palika',    'Nagar Palika / नगर पालिका'),
        ('nagar_panchayat', 'Nagar Panchayat / नगर पंचायत'),
    ], string='Urban Body Type / नगरीय निकाय प्रकार',
       tracking=True,
       help='Pulled from village; override here if needed. Controls urban area-slab calculation.')

    is_urban = fields.Boolean(
        string='Is Urban / नगरीय है',
        compute='_compute_is_urban',
        store=False,
        help='True when selected village is Urban in village master.',
    )
    
    # Award document
    award_document = fields.Binary(string='Award Document / अवार्ड दस्तावेज़', tracking=False)
    award_document_filename = fields.Char(string='Document Filename / दस्तावेज़ फ़ाइल नाम', tracking=True)
    signed_land_award_document = fields.Binary(string='Signed Land Award PDF', tracking=False)
    signed_land_award_filename = fields.Char(string='Signed Land Award Filename', tracking=True)
    signed_tree_award_document = fields.Binary(string='Signed Tree Award PDF', tracking=False)
    signed_tree_award_filename = fields.Char(string='Signed Tree Award Filename', tracking=True)
    signed_asset_award_document = fields.Binary(string='Signed Asset Award PDF', tracking=False)
    signed_asset_award_filename = fields.Char(string='Signed Asset Award Filename', tracking=True)
    signed_consolidated_award_document = fields.Binary(string='Signed Consolidated Award PDF', tracking=False)
    signed_consolidated_award_filename = fields.Char(string='Signed Consolidated Award Filename', tracking=True)
    signed_rr_award_document = fields.Binary(string='Signed R&R Award PDF', tracking=False)
    signed_rr_award_filename = fields.Char(string='Signed R&R Award Filename', tracking=True)
    
    # Notes
    notes = fields.Text(string='Notes / नोट्स', tracking=True)
    
    state = fields.Selection([
        ('draft', 'Draft / प्रारूप'),
        ('approved', 'Generated / उत्पन्न'),
        ('submitted', 'Submitted'),   # legacy — no longer used in new flow
        ('sent_back', 'Sent Back'),   # legacy — no longer used in new flow
    ], string='Status', default='draft', tracking=True, index=True)
    
    is_generated = fields.Boolean(string='Is Generated', default=False, tracking=True)
    land_generated = fields.Boolean(string='Land Generated', default=False, tracking=True)
    tree_generated = fields.Boolean(string='Tree Generated', default=False, tracking=True)
    asset_generated = fields.Boolean(string='Asset Generated', default=False, tracking=True)
    consolidated_generated = fields.Boolean(string='Consolidated Generated', default=False, tracking=True)
    rr_generated = fields.Boolean(string='R&R Generated', default=False, tracking=True)
    loader_progress_active = fields.Boolean(string='Loader Progress Active', default=False, tracking=False)
    loader_progress_done = fields.Integer(string='Loader Progress Done', default=0, tracking=False)
    loader_progress_total = fields.Integer(string='Loader Progress Total', default=0, tracking=False)
    loader_progress_pct = fields.Float(string='Loader Progress %', digits=(6, 2), default=0.0, tracking=False)
    loader_progress_label = fields.Char(string='Loader Progress Label', tracking=False)
    all_components_generated = fields.Boolean(
        string='All Components Generated',
        compute='_compute_all_components_generated',
        store=False,
    )
    s23_generation_stage = fields.Selection(
        [
            ('draft', 'Draft'),
            ('land_generated', 'Land Generated'),
            ('tree_generated', 'Tree Generated'),
            ('asset_generated', 'Asset Generated'),
            ('all_generated', 'All Generated'),
            ('consolidated_generated', 'Consolidated Generated'),
            ('rr_generated', 'R&R Generated'),
        ],
        string='Generation Progress',
        compute='_compute_s23_generation_stage',
        store=False,
    )
    
    village_domain = fields.Char()
    
    # Survey lines for award generation
    award_survey_line_ids = fields.One2many('bhu.section23.award.survey.line', 'award_id', 
                                            string='Approved Surveys / स्वीकृत सर्वेक्षण',
                                            help='Select type and distance for each approved survey')
    # Khasra search filter — stored so value persists across reloads
    khasra_filter = fields.Char(string='Search Khasra', default='')
    tree_khasra_filter = fields.Char(string='Search Tree Khasra', default='')
    award_line_item_ids = fields.One2many(
        'bhu.section23.award.line.item',
        'award_id',
        string='Award Line Items',
        readonly=True,
    )
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

    # Premium form (simulator-style dashboard totals – non-stored)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', compute='_compute_s23_premium_currency', readonly=True,
    )
    land_total = fields.Float(
        string='Land Total', digits=(16, 2), compute='_compute_land_total', store=False,
    )
    tree_total = fields.Float(
        string='Tree Total', digits=(16, 2), compute='_compute_tree_total', store=False,
    )
    structure_total = fields.Float(
        string='Structure Total', digits=(16, 2), compute='_compute_structure_total', store=False,
    )
    grand_total = fields.Float(
        string='Grand Total', digits=(16, 2), compute='_compute_grand_total', store=False,
    )
    s23_survey_count = fields.Integer(
        string='Survey Count', compute='_compute_s23_survey_count', store=False,
    )
    s23_land_khasra_count = fields.Integer(
        string='Land Khasra Count', compute='_compute_s23_land_khasra_count', store=False,
    )
    s23_tree_count = fields.Integer(
        string='Tree Count', compute='_compute_s23_tree_count', store=False,
    )
    s23_asset_count = fields.Integer(
        string='Asset Count', compute='_compute_s23_asset_count', store=False,
    )
    s23_land_preview_html = fields.Html(
        string='Land preview', compute='_compute_s23_section_previews', sanitize=False, store=False,
    )
    s23_tree_preview_html = fields.Html(
        string='Tree preview', compute='_compute_s23_section_previews', sanitize=False, store=False,
    )

    _sql_constraints = [
        ('project_village_unique', 'unique(project_id, village_id)', 
         'Only one award per project and village is allowed! / प्रत्येक परियोजना और गाँव के लिए केवल एक अवार्ड की अनुमति है!')
    ]

    @api.model
    def _auto_init(self):
        res = super()._auto_init()
        self._cr.execute(
            """
            CREATE INDEX IF NOT EXISTS bhu_s23_award_state_proj_vill_idx
            ON bhu_section23_award (state, project_id, village_id)
            """
        )
        return res

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

    @api.depends('project_id', 'village_id')
    def _compute_section4_hearing_date(self):
        for rec in self:
            if rec.project_id and rec.village_id:
                hearing_date = rec._get_section4_public_hearing_date()
                rec.section4_hearing_date = hearing_date
            else:
                rec.section4_hearing_date = False

    def _compute_user_roles(self):
        for rec in self:
            rec.is_sdm = self.env.user.has_group('bhuarjan.group_bhuarjan_sdm')
            rec.is_section_officer = self.env.user.has_group('bhuarjan.group_bhu_section_officer')
            rec.is_admin = self.env.user.has_group('bhuarjan.group_bhuarjan_admin')

    def _sync_village_profile_from_master(self, force=False):
        for rec in self:
            if not rec.village_id:
                continue
            master_vtype = rec.village_id.village_type or 'rural'
            master_ubody = rec.village_id.urban_body_type or False
            if force or not rec.village_type:
                rec.village_type = master_vtype
            if force or not rec.urban_body_type:
                rec.urban_body_type = master_ubody

    def _sync_village_profile_to_master(self):
        for rec in self:
            if not rec.village_id:
                continue
            rec.village_id.sudo().write({
                'village_type': rec.village_type or 'rural',
                'urban_body_type': rec.urban_body_type if rec.village_type == 'urban' else False,
            })

    @api.onchange('village_type')
    def _onchange_village_type_clear_urban_body(self):
        for rec in self:
            if rec.village_type != 'urban':
                rec.urban_body_type = False

    @api.depends('village_type', 'village_id', 'village_id.village_type')
    def _compute_is_urban(self):
        for rec in self:
            vtype = rec.village_type or (rec.village_id.village_type if rec.village_id else 'rural')
            rec.is_urban = (vtype == 'urban')

    def _get_active_rate_master_for_village(self):
        self.ensure_one()
        if not self.village_id:
            return False
        return self.env['bhu.rate.master'].search([
            ('village_id', '=', self.village_id.id),
            ('state', 'in', ['active', 'draft']),
        ], limit=1, order='state ASC, effective_from DESC')

    def _s23_distance_threshold(self):
        """MR/BMR threshold in meters from effective village type."""
        self.ensure_one()
        vtype = self.village_type or (self.village_id.village_type if self.village_id else 'rural')
        return 20.0 if vtype == 'urban' else 50.0

    def _sync_rate_fields_from_master(self, force=False):
        for rec in self:
            rm = rec._get_active_rate_master_for_village()
            mr_rate = float(rm.main_road_rate_hectare or 0.0) if rm else 0.0
            bmr_rate = float(rm.other_road_rate_hectare or 0.0) if rm else 0.0
            mr_plot_rate = float(rm.main_road_rate_sqm or 0.0) if rm else 0.0
            bmr_plot_rate = float(rm.other_road_rate_sqm or 0.0) if rm else 0.0
            if force or not rec.rate_master_main_road_ha:
                rec.rate_master_main_road_ha = mr_rate
            if force or not rec.rate_master_other_road_ha:
                rec.rate_master_other_road_ha = bmr_rate
            if force or not rec.rate_master_main_road_sqm:
                rec.rate_master_main_road_sqm = mr_plot_rate
            if force or not rec.rate_master_other_road_sqm:
                rec.rate_master_other_road_sqm = bmr_plot_rate

    @api.depends('project_id', 'project_id.company_id', 'project_id.company_id.currency_id')
    def _compute_s23_premium_currency(self):
        for rec in self:
            # Section 23 award UI must always show INR amounts.
            try:
                inr = rec.env.ref('base.INR')
            except Exception:
                inr = False
            cur = rec.project_id.company_id.currency_id if rec.project_id and rec.project_id.company_id else False
            rec.currency_id = inr or cur or rec.env.company.currency_id

    @api.depends(
        'award_survey_line_ids',
        'award_survey_line_ids.land_award_amount',
        'award_survey_line_ids.solatium_display',
        'award_survey_line_ids.interest_display',
    )
    def _compute_land_total(self):
        for rec in self:
            rec.land_total = sum(
                (line.land_award_amount or 0.0) +
                (line.solatium_display or 0.0) +
                (line.interest_display or 0.0)
                for line in rec.award_survey_line_ids
            )

    @api.depends(
        'award_structure_line_ids',
        'award_structure_line_ids.line_total',
    )
    def _compute_structure_total(self):
        for rec in self:
            rec.structure_total = sum((line.line_total or 0.0) * 2.0 for line in rec.award_structure_line_ids)

    @api.depends('project_id', 'village_id')
    def _compute_tree_total(self):
        for rec in self:
            tree_total = 0.0
            if rec.project_id and rec.village_id:
                surveys = rec.env['bhu.survey'].search([
                    ('project_id', '=', rec.project_id.id),
                    ('village_id', '=', rec.village_id.id),
                    ('state', 'in', ['draft', 'submitted', 'approved', 'locked']),
                ])
                for survey in surveys:
                    for tree_line in survey.tree_line_ids:
                        qty = float(getattr(tree_line, 'quantity', 0) or 0.0)
                        rate = float(tree_line.get_applicable_rate() if hasattr(tree_line, 'get_applicable_rate') else 0.0)
                        base_value = qty * rate
                        tree_total += base_value + (base_value * 0.1) + (base_value * 2.1)
            rec.tree_total = tree_total

    @api.depends('land_total', 'tree_total', 'structure_total')
    def _compute_grand_total(self):
        for rec in self:
            rec.grand_total = (rec.land_total or 0.0) + (rec.tree_total or 0.0) + (rec.structure_total or 0.0)

    @api.depends(
        'award_survey_line_ids', 'award_survey_line_ids.land_type', 'award_survey_line_ids.is_within_distance',
        'award_survey_line_ids.survey_id', 'award_survey_line_ids.rate_per_hectare',
        'village_id', 'project_id', 'award_date',
    )
    def _compute_s23_section_previews(self):
        for rec in self:
            rec.s23_land_preview_html = rec._html_s23_land_preview()
            rec.s23_tree_preview_html = rec._html_s23_tree_preview()

    @api.depends('award_survey_line_ids')
    def _compute_s23_survey_count(self):
        for rec in self:
            rec.s23_survey_count = len(rec.award_survey_line_ids)

    @api.depends('award_survey_line_ids', 'award_survey_line_ids.khasra_number')
    def _compute_s23_land_khasra_count(self):
        for rec in self:
            rec.s23_land_khasra_count = len(set(filter(None, rec.award_survey_line_ids.mapped('khasra_number'))))

    @api.depends('project_id', 'village_id')
    def _compute_s23_tree_count(self):
        for rec in self:
            tree_count = 0
            if rec.project_id and rec.village_id:
                surveys = rec.env['bhu.survey'].search([
                    ('project_id', '=', rec.project_id.id),
                    ('village_id', '=', rec.village_id.id),
                    ('state', 'in', ['draft', 'submitted', 'approved', 'locked', 'rejected']),
                ])
                if surveys.ids:
                    # Sum quantities directly — read_group aggregate keys differ across Odoo
                    # versions (e.g. quantity_sum vs quantity:sum), which caused badge to show 0.
                    lines = rec.env['bhu.survey.tree.line'].search([
                        ('survey_id', 'in', surveys.ids),
                    ])
                    tree_count = int(sum(lines.mapped('quantity')) or 0)
            rec.s23_tree_count = tree_count

    @api.depends('award_structure_line_ids', 'award_structure_line_ids.asset_count')
    def _compute_s23_asset_count(self):
        for rec in self:
            rec.s23_asset_count = sum(int(al.asset_count or 1) for al in rec.award_structure_line_ids)
    
    @api.depends('village_id')
    def _compute_rate_permutations(self):
        """Keep relation empty; do not create/link persisted lines here.

        Creating real ``bhu.rate.master.permutation.line`` rows and assigning
        ``(6, 0, [db_ids...])`` on this computed One2many during web onchange
        leaves x2many snapshot keys as plain ints; ``web``'s
        ``RecordSnapshot.diff`` then fails with ``AttributeError: 'int' object
        has no attribute 'origin'``. Permutations are not shown on award views;
        use the rate master / wizard flows for matrix display.
        """
        for award in self:
            award.rate_permutation_ids = [(5, 0, 0)]

    @api.depends('land_generated', 'tree_generated', 'asset_generated', 'is_generated')
    def _compute_all_components_generated(self):
        for rec in self:
            rec.all_components_generated = bool(
                (rec.land_generated and rec.tree_generated and rec.asset_generated) or rec.is_generated
            )

    @api.depends(
        'land_generated',
        'tree_generated',
        'asset_generated',
        'all_components_generated',
        'consolidated_generated',
        'rr_generated',
    )
    def _compute_s23_generation_stage(self):
        for rec in self:
            if rec.rr_generated:
                rec.s23_generation_stage = 'rr_generated'
            elif rec.consolidated_generated:
                rec.s23_generation_stage = 'consolidated_generated'
            elif rec.all_components_generated:
                rec.s23_generation_stage = 'all_generated'
            elif rec.asset_generated:
                rec.s23_generation_stage = 'asset_generated'
            elif rec.tree_generated:
                rec.s23_generation_stage = 'tree_generated'
            elif rec.land_generated:
                rec.s23_generation_stage = 'land_generated'
            else:
                rec.s23_generation_stage = 'draft'
    
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
    
    def _onchange_add_award_survey_lines_if_empty(self):
        """Pre-create land lines only when the O2M is still empty (no 5,0,0 in onchange).

        A full O2M replace with (5,0,0) + (0,0,...) during @api.onchange makes the web
        client snapshot diff crash (int ids vs NewId.origin). Full rebuild is done in
        create() / write() only.
        """
        self.ensure_one()
        if not (self.project_id and self.village_id):
            return
        if self.award_survey_line_ids:
            return
        surveys = self.env['bhu.survey'].search([
            ('project_id', '=', self.project_id.id),
            ('village_id', '=', self.village_id.id),
            ('state', 'in', ['draft', 'submitted', 'approved', 'locked', 'rejected']),
        ])
        if not surveys:
            return
        commands = []
        for survey in surveys:
            distance = survey.distance_from_main_road or 0.0
            threshold = self._s23_distance_threshold()
            commands.append((0, 0, {
                'survey_id': survey.id,
                'land_type': survey.land_type_for_award or 'village',
                'is_within_distance': distance <= threshold,
            }))
        if commands:
            self.award_survey_line_ids = commands
            self.award_survey_line_ids._compute_rate_per_hectare()
            self.award_survey_line_ids._compute_line_display_amounts()
        if self.project_id and self.village_id:
            self._sync_award_structure_lines()

    @api.onchange('village_id', 'project_id')
    def _onchange_village_populate_surveys(self):
        """Pre-fill land lines on first project+village (empty list only; save refreshes the rest)."""
        for rec in self:
            rec._sync_village_profile_from_master(force=bool(rec.village_id))
            rec._sync_rate_fields_from_master(force=bool(rec.village_id))
            rec._onchange_add_award_survey_lines_if_empty()

    @api.onchange('project_id')
    def _onchange_project_id(self):
        """Reset village when project changes and set domain"""
        for rec in self:
            if rec.project_id and rec.project_id.village_ids:
                rec.village_domain = json.dumps([('id', 'in', rec.project_id.village_ids.ids)])
            else:
                rec.village_domain = json.dumps([])
                rec.village_id = False
            if rec.village_id:
                rec._onchange_add_award_survey_lines_if_empty()
    
    @api.model_create_multi
    def create(self, vals_list):
        """Generate award reference and reuse existing project+village award when present."""
        to_create = []
        existing_records = self.browse()
        for vals in vals_list:
            vals = dict(vals)
            # Never apply O2M from the web client: it can send CREATE rows without
            # survey_id (required), causing SQL errors. Lines are built by _populate_award_survey_lines.
            vals.pop('award_survey_line_ids', None)
            project_id = vals.get('project_id')
            village_id = vals.get('village_id')
            if project_id and village_id:
                existing = self.search([
                    ('project_id', '=', project_id),
                    ('village_id', '=', village_id),
                ], limit=1)
                if existing:
                    existing_records |= existing
                    continue
            if vals.get('name', 'New') == 'New':
                # Try to use sequence settings from settings master
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
            to_create.append(vals)
        records = super().create(to_create) if to_create else self.browse()
        records |= existing_records
        # Onchange does not run for backend create() calls; ensure lines are populated/synced.
        for record in records:
            record._sync_village_profile_from_master(force=False)
            record._sync_rate_fields_from_master(force=False)
            record._populate_award_survey_lines(reset_if_empty=False)
        return records

    def write(self, vals):
        vals = dict(vals)
        # Ignore direct O2M payloads from web client by default, but allow
        # trusted server-side flows (populate/debug) to write survey lines.
        if not self.env.context.get('allow_award_survey_line_write'):
            vals.pop('award_survey_line_ids', None)
        # Only compare scope after write. Do not repopulate land lines whenever
        # project_id/village_id *appear* in vals — the web client often re-sends
        # the same M2O on any save, which would (5,0,0) rebuild every time and
        # make land award rows or amounts "vanish" after Save.
        pre_scope = {
            rec.id: (
                rec.project_id.id if rec.project_id else False,
                rec.village_id.id if rec.village_id else False,
            )
            for rec in self
        }
        result = super().write(vals)
        village_profile_changed = any(k in vals for k in ('village_type', 'urban_body_type'))
        for rec in self:
            old_p, old_v = pre_scope.get(rec.id, (False, False))
            new_p = rec.project_id.id if rec.project_id else False
            new_v = rec.village_id.id if rec.village_id else False
            if new_p != old_p or new_v != old_v:
                rec._sync_village_profile_from_master(force=True)
                rec._sync_rate_fields_from_master(force=True)
                rec._populate_award_survey_lines(reset_if_empty=True)
                if rec.project_id and rec.village_id:
                    rec._sync_award_structure_lines()
            if village_profile_changed and rec.village_id:
                rec._sync_village_profile_to_master()
        return result

    def unlink(self):
        """Explicitly remove O2M children before deletion.

        Cascade would handle it eventually, but stored computed fields on
        bhu.section23.award.survey.line depend on award_id fields.  When the
        ORM cascade fires those recomputes mid-transaction they try to read the
        (already-deleted) award record and raise MissingError in the browser.
        Unlinking the children first keeps the recompute queue clean.
        """
        for rec in self:
            rec.award_survey_line_ids.unlink()
            rec.award_line_item_ids.unlink()
        return super().unlink()

    def _populate_award_survey_lines(self, reset_if_empty=False):
        """Populate survey lines from draft/submitted/approved surveys.

        Rebuilds lines deterministically for the selected project+village.
        """
        self.ensure_one()
        _logger.info(f"[DEBUG] _populate_award_survey_lines called for award {self.name} (ID {self.id})")
        _logger.info(f"[DEBUG]   project_id={self.project_id.id if self.project_id else None}, village_id={self.village_id.id if self.village_id else None}")
        
        if not (self.project_id and self.village_id):
            _logger.warning(f"[DEBUG] Missing project_id or village_id. Returning early.")
            if reset_if_empty:
                self.award_survey_line_ids = [(5, 0, 0)]
            return

        surveys = self.env['bhu.survey'].search([
            ('project_id', '=', self.project_id.id),
            ('village_id', '=', self.village_id.id),
            # Include rejected as fallback; standard states are draft/submitted/approved/locked
            ('state', 'in', ['draft', 'submitted', 'approved', 'locked', 'rejected']),
        ])
        _logger.info(f"[DEBUG] Found {len(surveys)} surveys matching project {self.project_id.id} and village {self.village_id.id}")
        for i, s in enumerate(surveys):
            _logger.info(f"[DEBUG]   Survey {i+1}: ID={s.id}, name={s.name}, khasra={s.khasra_number}, state={s.state}")
        
        if not surveys:
            _logger.warning(f"[DEBUG] No surveys found. reset_if_empty={reset_if_empty}, current award_survey_line_ids={len(self.award_survey_line_ids)}")
            # Never wipe existing land lines on a "soft" repopulate: if the search returns
            # no rows (workflow timing, or state not matching yet), a full clear would
            # remove khasra from the form — e.g. on Generate when _validate repopulates.
            if self.award_survey_line_ids and not reset_if_empty:
                _logger.info(f"[DEBUG] Keeping existing {len(self.award_survey_line_ids)} award_survey_line_ids (soft repopulate with no surveys)")
                return
            self.award_survey_line_ids = [(5, 0, 0)]
            _logger.info(f"[DEBUG] Cleared award_survey_line_ids")
            return
        # Rebuild commands from current surveys to avoid stale/empty UI rows.
        commands = [(5, 0, 0)]
        for survey in surveys:
            distance = survey.distance_from_main_road or 0.0
            threshold = self._s23_distance_threshold()
            commands.append((0, 0, {
                'survey_id': survey.id,
                'land_type': survey.land_type_for_award or 'village',
                'is_within_distance': distance <= threshold,
            }))
        _logger.info(f"[DEBUG] Creating {len(commands)-1} award_survey_line records from {len(surveys)} surveys")
        self.with_context(allow_award_survey_line_write=True).write({
            'award_survey_line_ids': commands,
        })
        # Force rate recompute now that award_id is fully linked on each line
        if self.award_survey_line_ids:
            self.award_survey_line_ids._compute_rate_per_hectare()
            self.award_survey_line_ids._compute_line_display_amounts()
        if self.project_id and self.village_id:
            self._sync_award_structure_lines()
        _logger.info(f"[DEBUG] _populate_award_survey_lines complete. Final count: {len(self.award_survey_line_ids)}")

    def action_clear_khasra_filter(self):
        """Clear the khasra filter and reload."""
        self.ensure_one()
        self.khasra_filter = ''
        if self.project_id and self.village_id and not self.award_survey_line_ids:
            self._populate_award_survey_lines(reset_if_empty=False)
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_clear_tree_khasra_filter(self):
        """Clear the tree khasra filter and reload."""
        self.ensure_one()
        self.tree_khasra_filter = ''
        if self.project_id and self.village_id and not self.award_survey_line_ids:
            self._populate_award_survey_lines(reset_if_empty=False)
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_tree_add_popup(self):
        """Open tree edit wizard directly for typed khasra."""
        self.ensure_one()
        if self.project_id and self.village_id and not self.award_survey_line_ids:
            self._populate_award_survey_lines(reset_if_empty=False)
        if not self.award_survey_line_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Add Tree',
                    'message': 'No khasra lines found. Select project and village first.',
                    'type': 'warning',
                    'sticky': False,
                },
            }

        term = (self.tree_khasra_filter or '').strip()
        if not term:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Add Tree',
                    'message': 'Please enter Khasra number first, then click Add Tree.',
                    'type': 'warning',
                    'sticky': False,
                },
            }

        matches = self.award_survey_line_ids.filtered(
            lambda l, t=term.lower(): t in (l.khasra_number or '').lower()
        )
        if not matches:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Add Tree',
                    'message': f'No khasra matched "{term}".',
                    'type': 'warning',
                    'sticky': False,
                },
            }

        exact = matches.filtered(
            lambda l, t=term.lower(): (l.khasra_number or '').strip().lower() == t
        )
        if not exact and len(matches) > 1:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Add Tree',
                    'message': f'Multiple khasra matched "{term}". Please type full khasra number.',
                    'type': 'warning',
                    'sticky': False,
                },
            }

        target_line = (exact[:1] or matches[:1])
        return target_line.action_open_survey_for_tree_edit()

    def action_refresh_land_lines_debug(self):
        """[DEBUG] Manually refresh land lines from surveys. Logs details to server console."""
        self.ensure_one()
        _logger.info(f"\n{'='*80}")
        _logger.info(f"[MANUAL DEBUG] User clicked 'Refresh Land Lines'")
        _logger.info(f"Award: {self.name} (ID {self.id})")
        _logger.info(f"Project: {self.project_id.name if self.project_id else 'None'} (ID {self.project_id.id if self.project_id else None})")
        _logger.info(f"Village: {self.village_id.name if self.village_id else 'None'} (ID {self.village_id.id if self.village_id else None})")
        _logger.info(f"Current award_survey_line_ids count: {len(self.award_survey_line_ids)}")
        _logger.info(f"{'='*80}\n")
        self._populate_award_survey_lines(reset_if_empty=True)
        _logger.info(f"\n[MANUAL DEBUG] After populate: award_survey_line_ids count = {len(self.award_survey_line_ids)}\n")
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_apply_khasra_search(self):
        """Search khasra and open edit popup(s) for matching land line(s)."""
        self.ensure_one()
        if self.project_id and self.village_id and not self.award_survey_line_ids:
            self._populate_award_survey_lines(reset_if_empty=False)
        term = (self.khasra_filter or '').strip()
        if not term:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Search',
                    'message': 'Enter a khasra value before searching.',
                    'type': 'warning',
                    'sticky': False,
                },
            }

        matches = self.award_survey_line_ids.filtered(
            lambda l, t=term.lower(): t in (l.khasra_number or '').lower()
        )
        if not matches:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Search',
                    'message': f'No khasra matched "{term}".',
                    'type': 'warning',
                    'sticky': False,
                },
            }

        # If exactly one match, open the same 4-field edit wizard directly.
        if len(matches) == 1:
            return matches.action_open_survey_for_land_edit()

        # If multiple matches, open popup list with Edit button on each row.
        tree_view = False
        try:
            tree_view = self.env.ref('bhuarjan.view_section23_award_survey_line_tree').id
        except Exception:
            tree_view = False

        return {
            'type': 'ir.actions.act_window',
            'name': f'Khasra Search: {term}',
            'res_model': 'bhu.section23.award.survey.line',
            'view_mode': 'list',
            'views': [(tree_view, 'list')],
            'domain': [('id', 'in', matches.ids)],
            'target': 'new',
            'context': {
                'default_award_id': self.id,
                'create': False,
                'edit': False,
            },
        }

    def action_apply_tree_khasra_search(self):
        """Search khasra and open popup tree editor for matching survey line(s)."""
        self.ensure_one()
        if self.project_id and self.village_id and not self.award_survey_line_ids:
            self._populate_award_survey_lines(reset_if_empty=False)
        term = (self.tree_khasra_filter or '').strip()
        if not term:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Search',
                    'message': 'Enter a khasra value before searching tree lines.',
                    'type': 'warning',
                    'sticky': False,
                },
            }

        matches = self.award_survey_line_ids.filtered(
            lambda l, t=term.lower(): t in (l.khasra_number or '').lower()
        )
        if not matches:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Search',
                    'message': f'No khasra matched "{term}".',
                    'type': 'warning',
                    'sticky': False,
                },
            }

        if len(matches) == 1:
            return matches.action_open_survey_for_tree_edit()

        tree_view = False
        try:
            tree_view = self.env.ref('bhuarjan.view_section23_award_survey_line_tree').id
        except Exception:
            tree_view = False

        return {
            'type': 'ir.actions.act_window',
            'name': f'Tree Khasra Search: {term}',
            'res_model': 'bhu.section23.award.survey.line',
            'view_mode': 'list',
            'views': [(tree_view, 'list')],
            'domain': [('id', 'in', matches.ids)],
            'target': 'new',
            'context': {
                'default_award_id': self.id,
                'create': False,
                'edit': False,
            },
        }

    def _s23_recompute_award_survey_lines_for_export(self):
        """Recompute and persist land survey line rates before PDF/Excel (current survey + master)."""
        self.ensure_one()
        lines = self.award_survey_line_ids
        if not lines:
            return
        lines._compute_rate_per_hectare()
        lines._compute_line_display_amounts()
        lines.flush_recordset()

    def action_refresh_land_rates(self):
        """Force-recompute rate_per_hectare and display amounts for all land survey lines."""
        self.ensure_one()
        self._s23_recompute_award_survey_lines_for_export()
        lines = self.award_survey_line_ids
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Rates Refreshed',
                'message': _('Recomputed rates for %s land survey line(s) from the active rate master.') % len(lines),
                'type': 'success',
                'sticky': False,
            },
        }

    def _html_s23_num(self, value, decimals=2):
        return escape(self.format_indian_number(float(value or 0.0), decimals))

    def _html_s23_land_preview(self):
        self.ensure_one()
        if not (self.project_id and self.village_id):
            return Markup(
                '<p class="text-muted s23_note mb-0">'
                'Select project and village to see land lines (same engine as the award / अवार्ड).'
                '</p>'
            )
        rows = self.get_land_compensation_data()
        if not rows:
            return Markup(
                '<p class="text-muted s23_note mb-0">'
                'No land rows found for this village/project. Check surveys and khasra data.'
                '</p>'
            )
        try:
            _cur = self.currency_id or self.env.company.currency_id
            cur_sym = _cur.symbol or '₹'
        except Exception:
            cur_sym = '₹'
        # Soft alternating palette for khasra groups
        _SLAB_COLORS = [
            '#e3f2fd',  # light blue
            '#f3e5f5',  # light purple
            '#e8f5e9',  # light green
            '#fff3e0',  # light amber
            '#fce4ec',  # light pink
            '#e0f7fa',  # light cyan
            '#f9fbe7',  # light lime
            '#ede7f6',  # light violet
        ]

        # Build a khasra→color mapping so every slab row of the same khasra
        # shares one color; rural (non-slab) rows get a plain white background.
        khasra_color = {}
        color_idx = 0
        for r in rows:
            if r.get('is_urban_slab'):
                k = (r.get('khasra') or '', r.get('landowner_name') or '')
                if k not in khasra_color:
                    khasra_color[k] = _SLAB_COLORS[color_idx % len(_SLAB_COLORS)]
                    color_idx += 1

        headers = [
            ('Sr. No. / क्र.', 'num'),
            ('Owner / भूमि स्वामी', 'text'),
            ('Khasra / खसरा', 'text'),
            ('Village / ग्राम', 'text'),
            ('Distance (m) / दूरी', 'num'),
            ('Road / सड़क', 'text'),
            ('Irrigation / सिंचाई', 'text'),
            ('Diverted / विचलित', 'text'),
            ('Acquired (Ha) / अधि.', 'num'),
            ('Slab / Remark', 'text'),
        ]
        parts = [
            '<div class="table-responsive s23-preview-wrap s23-land-sim-table-wrap">',
            '<table class="table table-sm s23-sim-table s23-sim-table-land">',
            '<thead><tr>',
        ]
        for col_label, col_type in headers:
            parts.append(
                f'<th class="s23-sim-th s23-sortable-th" scope="col" '
                f'data-sort-type="{escape(col_type)}" title="Click to sort">'
                f'{escape(col_label)}'
                f'<span class="s23-sort-indicator" aria-hidden="true"></span>'
                f'</th>'
            )
        parts.append('</tr></thead><tbody>')

        rows_sorted = sorted(
            rows,
            key=lambda x: (
                x.get('khasra') or '',
                x.get('landowner_name') or '',
                float(x.get('distance_from_main_road') or 0.0),
            ),
        )
        merged_by_khasra = {}
        for r in rows_sorted:
            khasra_val = (r.get("khasra") or "").strip()
            if not khasra_val:
                continue
            if khasra_val not in merged_by_khasra:
                merged_by_khasra[khasra_val] = {
                    'khasra': khasra_val,
                    'owners': [],
                    'village_name': r.get("village_name") or "",
                    'distance_from_main_road': r.get("distance_from_main_road") or 0.0,
                    'road_type_label': r.get("road_type_label") or ("MR" if r.get("is_within_distance") else "BMR"),
                    'irrigation_label': r.get("irrigation_label") or "",
                    'irrigation_type': r.get("irrigation_type") or "",
                    'is_diverted': r.get("is_diverted"),
                    'diverted_label': r.get("diverted_label") or ("Yes" if r.get("is_diverted") else "No"),
                    'acquired_area': r.get("acquired_area") or 0.0,
                    'remark': r.get("remark") or "",
                }
            bucket = merged_by_khasra[khasra_val]
            owner = (r.get("landowner_name") or "").strip()
            if owner and owner not in bucket['owners']:
                bucket['owners'].append(owner)
            # same khasra rows often duplicate acquired area per owner; keep logical single-khasra value
            bucket['acquired_area'] = max(bucket['acquired_area'], r.get("acquired_area") or 0.0)
            remark = (r.get("remark") or "").strip()
            if remark and remark not in (bucket['remark'] or ""):
                bucket['remark'] = (bucket['remark'] + ", " + remark).strip(", ")

        for sr_no, row in enumerate(merged_by_khasra.values(), start=1):
            parts.append('<tr>')
            parts.append(f'<td class="text-center tabular-nums">{sr_no}</td>')
            owner_display = ", ".join(row['owners'])
            parts.append(f'<td class="text-nowrap">{escape(owner_display)}</td>')
            parts.append(f'<td class="text-nowrap fw-semibold">{escape(row["khasra"])}</td>')
            parts.append(f'<td class="text-nowrap">{escape(row.get("village_name") or "")}</td>')
            parts.append(f'<td class="text-end tabular-nums">{self._html_s23_num(row.get("distance_from_main_road"), 2)}</td>')
            road = row.get("road_type_label") or ("MR" if row.get("is_within_distance") else "BMR")
            road_key = road.strip().upper()
            road_style = (
                'color:#1b8f4f;font-weight:700;'
                if road_key == "MR" else
                'color:#c0392b;font-weight:700;'
            )
            parts.append(
                f'<td class="text-nowrap text-center"><span class="s23-sim-badge" style="{road_style}">{escape(road)}</span></td>'
            )
            irrigation_label = (row.get("irrigation_label") or "").strip()
            irrigation_key = (row.get("irrigation_type") or "").strip().lower()
            label_key = irrigation_label.lower()
            irrigated_yes = irrigation_key == "irrigated" or (
                "irrigated" in label_key and "unirrigated" not in label_key
            )
            irrigation_style = (
                'color:#1b8f4f;font-weight:600;'
                if irrigated_yes else
                'color:#d66a6a;font-weight:600;'
            )
            parts.append(
                f'<td class="text-nowrap small text-center" style="{irrigation_style}">{escape(irrigation_label)}</td>'
            )
            div_lbl = (row.get("diverted_label") or ("Yes" if row.get("is_diverted") else "No"))
            diverted_flag = row.get("is_diverted")
            diverted_yes = bool(diverted_flag) if diverted_flag is not None else (
                div_lbl.strip().lower() in {"yes", "y", "true", "1", "हाँ", "ha", "haan"}
            )
            diverted_style = (
                'color:#1b8f4f;font-weight:700;'
                if diverted_yes else
                'color:#c0392b;font-weight:700;'
            )
            parts.append(f'<td class="text-center text-nowrap" style="{diverted_style}">{escape(div_lbl)}</td>')
            parts.append(f'<td class="text-end tabular-nums">{self._html_s23_num(row.get("acquired_area"), 4)}</td>')
            parts.append(f'<td class="text-nowrap small" style="font-style:italic;">{escape((row.get("remark") or ""))}</td>')
            parts.append('</tr>')

        parts.append(
            '</tbody></table>'
            '<p class="s23-sim-hint text-muted small mb-0">'
            'Each colour group = one khasra split into urban slabs / एक रंग = एक खसरा के स्लैब'
            '</p></div>'
        )
        return Markup(''.join(parts))

    def _html_s23_tree_preview(self):
        self.ensure_one()
        if not (self.project_id and self.village_id):
            return Markup(
                '<p class="text-muted s23_note mb-0">'
                'Select project and village to see tree lines.'
                '</p>'
            )
        rows = self.get_tree_compensation_data()
        if not rows:
            return Markup(
                '<p class="text-muted s23_note mb-0">'
                'No tree compensation rows (no tree lines on surveys or zero quantities).'
                '</p>'
            )
        try:
            _cur = self.currency_id or self.env.company.currency_id
            cur_sym = _cur.symbol or '₹'
        except Exception:
            cur_sym = '₹'
        headers = [
            'Khasra', 'Owner', 'Tree', 'Tree Type', 'Dev. Stage',
            'Girth (cm)', 'Qty',
            f'Unit Rate ({cur_sym})', f'Value ({cur_sym})',
            f'Solatium ({cur_sym})', f'Interest ({cur_sym})', f'Total ({cur_sym})',
        ]
        merged_by_khasra = {}

        def _fnum(val):
            try:
                return float(val or 0.0)
            except Exception:
                return 0.0

        for r in rows:
            khasra = (r.get("tree_khasra") or r.get("khasra") or "").strip()
            if not khasra:
                continue
            bucket = merged_by_khasra.setdefault(khasra, {
                'khasra': khasra,
                'owners': [],
                'tree_names': [],
                'tree_type_labels': [],
                'dev_stage_labels': [],
                'girth_labels': [],
                'unit_rates': [],
                'qty': 0.0,
                'value': 0.0,
                'solatium': 0.0,
                'interest': 0.0,
                'total': 0.0,
            })

            owner = (r.get("landowner_name") or "").strip()
            if owner and owner not in bucket['owners']:
                bucket['owners'].append(owner)

            tree_name = str(r.get("tree_type") or "").strip()
            if tree_name and tree_name not in bucket['tree_names']:
                bucket['tree_names'].append(tree_name)

            tc = r.get("tree_type_code") or ""
            tc_label = "Fruit Bearing" if tc == "fruit_bearing" else ("Timber" if tc == "timber" else tc.replace("_", " ").title())
            if tc_label and tc_label not in bucket['tree_type_labels']:
                bucket['tree_type_labels'].append(tc_label)

            _ds_map = {'undeveloped': 'Undeveloped', 'semi_developed': 'Semi-Developed', 'fully_developed': 'Fully Developed'}
            ds_label = _ds_map.get(r.get('development_stage') or '', r.get('development_stage') or '—')
            if ds_label and ds_label not in bucket['dev_stage_labels']:
                bucket['dev_stage_labels'].append(ds_label)

            girth_val = _fnum(r.get("girth_cm"))
            girth_lbl = self._html_s23_num(girth_val, 1)
            if girth_lbl and girth_lbl not in bucket['girth_labels']:
                bucket['girth_labels'].append(girth_lbl)

            unit_rate = _fnum(r.get("unit_rate") or r.get("rate") or 0.0)
            if unit_rate > 0 and unit_rate not in bucket['unit_rates']:
                bucket['unit_rates'].append(unit_rate)

            bucket['qty'] += _fnum(r.get("tree_count"))
            bucket['value'] += _fnum(r.get("value"))
            bucket['solatium'] += _fnum(r.get("solatium"))
            bucket['interest'] += _fnum(r.get("interest"))
            bucket['total'] += _fnum(r.get("total"))

        parts = [
            '<div class="table-responsive s23-preview-wrap s23-land-sim-table-wrap">',
            '<table class="table table-sm s23-sim-table s23-sim-table-land">',
            '<thead><tr>',
        ]
        for col in headers:
            parts.append(f'<th class="s23-sim-th" scope="col">{escape(col)}</th>')
        parts.append('</tr></thead><tbody>')
        for khasra, r in merged_by_khasra.items():
            parts.append('<tr>')
            parts.append(f'<td class="text-nowrap fw-semibold">{escape(khasra)}</td>')
            parts.append(f'<td class="text-nowrap">{escape(", ".join(r.get("owners") or []))}</td>')
            parts.append(f'<td class="text-nowrap">{escape(", ".join(r.get("tree_names") or []))}</td>')
            parts.append(f'<td class="text-nowrap small">{escape(", ".join(r.get("tree_type_labels") or []))}</td>')
            parts.append(f'<td class="text-nowrap small">{escape(", ".join(r.get("dev_stage_labels") or []))}</td>')
            parts.append(f'<td class="text-end tabular-nums">{escape(", ".join(r.get("girth_labels") or []))}</td>')
            parts.append(f'<td class="text-end tabular-nums">{self._html_s23_num(r.get("qty"), 0)}</td>')
            unit_rates = r.get("unit_rates") or []
            if len(unit_rates) == 1:
                unit_rate_display = self._html_s23_num(unit_rates[0], 0)
            elif len(unit_rates) > 1:
                unit_rate_display = "Mixed"
            else:
                unit_rate_display = self._html_s23_num(0, 0)
            parts.append(f'<td class="text-end tabular-nums">{escape(unit_rate_display)}</td>')
            parts.append(f'<td class="text-end tabular-nums">{self._html_s23_num(r.get("value"), 0)}</td>')
            parts.append(f'<td class="text-end tabular-nums">{self._html_s23_num(r.get("solatium"), 0)}</td>')
            parts.append(f'<td class="text-end tabular-nums">{self._html_s23_num(r.get("interest"), 0)}</td>')
            parts.append(f'<td class="text-end tabular-nums fw-bold">{self._html_s23_num(r.get("total"), 0)}</td>')
            parts.append('</tr>')
        parts.append('</tbody></table></div>')
        return Markup(''.join(parts))

    def action_open_land_surveys_for_edit(self):
        """Open village surveys so users can edit distance/irrigation/diverted quickly."""
        self.ensure_one()
        if not (self.project_id and self.village_id):
            raise ValidationError(_('Select project and village first.'))
        return {
            'name': _('Edit land inputs / भूमि इनपुट संपादित करें'),
            'type': 'ir.actions.act_window',
            'res_model': 'bhu.survey',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [
                ('project_id', '=', self.project_id.id),
                ('village_id', '=', self.village_id.id),
                ('state', 'in', ['draft', 'submitted', 'approved', 'locked', 'rejected']),
                ('khasra_number', '!=', False),
            ],
            'context': {
                'search_default_project_id': self.project_id.id,
                'search_default_village_id': self.village_id.id,
            },
        }

    def action_download_award(self):
        """Download award document - Open wizard for PDF/Word"""
        self.ensure_one()
        return self._open_award_download_wizard(
            generate=False,
            export_scope='all',
            variant='standard',
            title=_('Download Section 23 Award / धारा 23 अवार्ड डाउनलोड करें'),
        )

    def _open_award_download_wizard(
        self,
        generate=False,
        export_scope='all',
        variant='standard',
        default_format='pdf',
        title=None,
        simple_download_dialog=False,
    ):
        self.ensure_one()
        report_action = self._get_section23_report_action()
        scope = export_scope or 'all'
        if scope not in ('all', 'land', 'asset', 'tree'):
            scope = 'all'
        sheet_variant = variant or 'standard'
        if sheet_variant not in ('standard', 'consolidated', 'rr'):
            sheet_variant = 'standard'
        return {
            'name': title or _('Download Award / अवार्ड डाउनलोड करें'),
            'type': 'ir.actions.act_window',
            'res_model': 'bhu.award.download.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
                'default_report_xml_id': report_action.get_external_id().get(
                    report_action.id, 'bhuarjan.action_report_section23_award'
                ),
                'default_filename': f'Section23_Award_{self.name}.pdf',
                'default_export_scope': scope,
                'default_add_cover_letter': True,
                'default_section23_generate': bool(generate),
                'default_section23_sheet_variant': sheet_variant,
                'default_format': default_format if default_format in ('pdf', 'excel') else 'pdf',
                'default_simple_download_dialog': bool(simple_download_dialog),
            }
        }

    def _s23_cache_attachment_name(self, export_scope='all', variant='standard', file_format='pdf'):
        self.ensure_one()
        scope = (export_scope or 'all').lower()
        var = (variant or 'standard').lower()
        fmt = 'pdf' if (file_format or 'pdf').lower() == 'pdf' else 'excel'
        return f"s23_cache::{var}::{scope}::{fmt}"

    def _s23_filename_token(self, value, fallback):
        raw = (value or '').strip()
        if not raw:
            return fallback
        token = re.sub(r'\s+', ' ', raw).strip()
        # Keep Hindi/Unicode text readable; only remove filesystem-unsafe chars.
        token = (token
                 .replace('/', '-')
                 .replace('\\', '-')
                 .replace(':', '-')
                 .replace('*', '')
                 .replace('?', '')
                 .replace('"', '')
                 .replace('<', '')
                 .replace('>', '')
                 .replace('|', ''))
        token = token.replace(' ', '_')
        return token or fallback

    def _s23_location_type_suffix(self):
        """Return location type token with readable urban-body name."""
        self.ensure_one()
        village_type = (self.village_type or (self.village_id.village_type if self.village_id else '') or 'rural').lower()
        if village_type != 'urban':
            return 'R_Rural'
        body_type = (self.urban_body_type or (self.village_id.urban_body_type if self.village_id else '') or '').lower()
        body_map = {
            'nagar_nigam': 'Nagar_Nigam',
            'nagar_palika': 'Nagar_Palika',
            'nagar_panchayat': 'Nagar_Panchayat',
        }
        body_code = body_map.get(body_type, 'Urban')
        return f"U_{body_code}"

    def get_urban_body_label(self):
        """Return urban body label only when award location is urban."""
        self.ensure_one()
        village_type = (self.village_type or (self.village_id.village_type if self.village_id else '') or 'rural').lower()
        if village_type != 'urban':
            return ''
        body_type = (self.urban_body_type or (self.village_id.urban_body_type if self.village_id else '') or '').lower()
        if not body_type:
            return ''
        body_map = {
            'nagar_nigam': 'Nagar Nigam / नगर निगम',
            'nagar_palika': 'Nagar Palika / नगर पालिका',
            'nagar_panchayat': 'Nagar Panchayat / नगर पंचायत',
        }
        return body_map.get(body_type, body_type)

    def _s23_cache_filename_for_user(self, export_scope='all', variant='standard', file_format='pdf'):
        self.ensure_one()
        village_tok = self._s23_filename_token(
            self.village_id.name if self.village_id else '',
            f'village_{self.village_id.id if self.village_id else self.id}',
        )
        loc_tok = self._s23_location_type_suffix()
        scope_key = (export_scope or 'all').lower()
        variant_key = (variant or 'standard').lower()
        if variant_key == 'consolidated':
            award_type_tok = 'Consolidated'
        elif variant_key == 'rr':
            award_type_tok = 'RR'
        else:
            scope_map = {
                'land': 'Land',
                'tree': 'Tree',
                'asset': 'Asset',
                'all': 'All',
            }
            award_type_tok = scope_map.get(scope_key, 'All')
        ext = 'pdf' if (file_format or 'pdf').lower() == 'pdf' else 'xlsx'
        return f"Sec23_Award_{award_type_tok}_{village_tok}_{loc_tok}.{ext}"

    def _s23_get_cached_attachment(self, export_scope='all', variant='standard', file_format='pdf'):
        self.ensure_one()
        cache_key = self._s23_cache_attachment_name(export_scope, variant, file_format)
        att = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('description', 'ilike', cache_key),
        ], order='create_date desc, id desc', limit=1)
        if att:
            return att
        # Backward-compatibility with older cache naming.
        legacy_name = "S23_CACHE__%s__%s__%s__%s.%s" % (
            (variant or 'standard').lower(),
            (export_scope or 'all').lower(),
            'pdf' if (file_format or 'pdf').lower() == 'pdf' else 'excel',
            self.id,
            'pdf' if (file_format or 'pdf').lower() == 'pdf' else 'xlsx',
        )
        return self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('name', '=', legacy_name),
        ], limit=1)

    def _s23_store_cached_attachment(self, binary_data, export_scope='all', variant='standard', file_format='pdf'):
        self.ensure_one()
        if not binary_data:
            return False
        cache_key = self._s23_cache_attachment_name(export_scope, variant, file_format)
        user_name = self._s23_cache_filename_for_user(export_scope, variant, file_format)
        mimetype = 'application/pdf' if (file_format or 'pdf') == 'pdf' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        old = self._s23_get_cached_attachment(export_scope, variant, file_format)
        if old:
            old.unlink()
        return self.env['ir.attachment'].create({
            'name': user_name,
            'type': 'binary',
            'datas': base64.b64encode(binary_data),
            'mimetype': mimetype,
            'res_model': self._name,
            'res_id': self.id,
            'description': f'S23 cached export ({variant}/{export_scope}/{file_format}) [{cache_key}]',
        })

    def _s23_clear_variant_cache(self, variants=None):
        """Delete cached files for selected variant(s) from DB."""
        self.ensure_one()
        variants = variants or ('consolidated', 'rr')
        vars_clean = tuple(v for v in variants if v in ('standard', 'consolidated', 'rr'))
        if not vars_clean:
            return 0
        atts = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
        ])
        to_remove = atts.filtered(
            lambda att: any(
                (f"s23_cache::{var}::" in ((att.description or '').lower())) or
                (f"S23_CACHE__{var}__" in (att.name or ''))
                for var in vars_clean
            )
        )
        count = len(to_remove)
        if to_remove:
            to_remove.unlink()
        return count

    @api.model
    def _extract_attachment_id_from_action(self, action):
        if not isinstance(action, dict):
            return False
        if action.get('type') != 'ir.actions.act_url':
            return False
        url = action.get('url') or ''
        if not url:
            return False
        match = re.search(r'/web/content/(\d+)', url)
        return int(match.group(1)) if match else False

    def _s23_render_pdf_bytes(self, export_scope='all'):
        self.ensure_one()
        scope = export_scope or 'all'
        if scope not in ('all', 'land', 'asset', 'tree'):
            scope = 'all'
        report_action = self._get_section23_report_action()
        pdf_result = report_action.sudo().with_context(
            s23_pdf_scope=scope,
            s23_include_cover=False,
        )._render_qweb_pdf(report_action.id, [self.id], data={})
        if not pdf_result:
            return b''
        return pdf_result[0] if isinstance(pdf_result, (tuple, list)) else pdf_result

    def _s23_render_variant_pdf_bytes(self, variant='standard', export_scope='all'):
        self.ensure_one()
        var = (variant or 'standard').lower()
        if var == 'standard':
            return self._s23_render_pdf_bytes(export_scope=export_scope)
        if var == 'consolidated':
            report_action = self.env.ref('bhuarjan.action_report_consolidated_award_sheet')
            pdf_result = report_action.sudo()._render_qweb_pdf(report_action.id, [self.id], data={})
            if not pdf_result:
                return b''
            return pdf_result[0] if isinstance(pdf_result, (tuple, list)) else pdf_result
        if var == 'rr':
            report_action = self.env.ref('bhuarjan.action_report_rr_award_sheet')
            pdf_result = report_action.sudo()._render_qweb_pdf(report_action.id, [self.id], data={})
            if not pdf_result:
                return b''
            return pdf_result[0] if isinstance(pdf_result, (tuple, list)) else pdf_result
        return b''

    def _s23_prepare_variant_cache(self, variant='standard', export_scope='all'):
        """Generate and cache BOTH PDF and Excel for a variant."""
        self.ensure_one()
        var = (variant or 'standard').lower()
        scope = export_scope or 'all'
        if scope not in ('all', 'land', 'asset', 'tree'):
            scope = 'all'
        if var not in ('standard', 'consolidated', 'rr'):
            var = 'standard'

        # Guard: if row phase already reached 100%, reserve post-processing units
        # so loader does not stay at 100% during PDF/Excel cache work.
        cur = self.get_loader_progress_current() or {}
        cur_done = int(cur.get('done') or 0)
        cur_total = int(cur.get('total') or 0)
        if cur_total <= cur_done:
            self._s23_set_loader_progress(
                done=cur_done,
                total=cur_done + 8,
                label=_('Starting document cache phase...'),
                active=True,
                flush=True,
            )

        self._s23_increment_loader_progress(
            step=1, label=_('Rendering PDF report...'), flush=True, active=True
        )
        pdf_bytes = self._s23_render_variant_pdf_bytes(variant=var, export_scope=scope)
        if pdf_bytes:
            self._s23_store_cached_attachment(
                pdf_bytes, export_scope=scope, variant=var, file_format='pdf'
            )
            self._s23_increment_loader_progress(
                step=1, label=_('Uploading PDF to DB cache...'), flush=True, active=True
            )

        excel_action = False
        self._s23_increment_loader_progress(
            step=1, label=_('Rendering Excel report...'), flush=True, active=True
        )
        if var == 'standard':
            excel_action = self.action_download_excel_components(export_scope=scope)
        elif var == 'consolidated':
            excel_action = self.action_download_consolidated_excel()
        elif var == 'rr':
            excel_action = self.action_download_rr_excel()

        excel_attachment_id = self._extract_attachment_id_from_action(excel_action)
        if excel_attachment_id:
            tmp_att = self.env['ir.attachment'].browse(excel_attachment_id)
            if tmp_att.exists() and tmp_att.datas:
                excel_bytes = base64.b64decode(tmp_att.datas)
                self._s23_store_cached_attachment(
                    excel_bytes, export_scope=scope, variant=var, file_format='excel'
                )
                self._s23_increment_loader_progress(
                    step=1, label=_('Uploading Excel to DB cache...'), flush=True, active=True
                )
                # Keep DB clean: remove temporary one created by exporter.
                tmp_att.unlink()
        self._s23_increment_loader_progress(
            step=1, label=_('Cache ready. Updating status...'), flush=True, active=True
        )

    def _s23_prepare_standard_scope_cache(self, export_scope='all'):
        """Generate and cache BOTH PDF and Excel for a standard scope."""
        self.ensure_one()
        self._s23_prepare_variant_cache(variant='standard', export_scope=export_scope)

    def action_download_cached_award_file(self, export_scope='all', file_format='pdf', variant='standard'):
        """Download pre-generated file from DB cache (no regeneration)."""
        self.ensure_one()
        scope = export_scope or 'all'
        fmt = (file_format or 'pdf').lower()
        var = (variant or 'standard').lower()
        if fmt not in ('pdf', 'excel'):
            fmt = 'pdf'
        if var not in ('standard', 'consolidated', 'rr'):
            var = 'standard'
        att = self._s23_get_cached_attachment(scope, var, fmt)
        if not att:
            raise ValidationError(_(
                'No cached %s file found for %s/%s. '
                'Please generate first and then download.'
            ) % (fmt.upper(), var.title(), scope.title()))
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{att.id}?download=true',
            'target': 'self',
        }

    def _s23_signed_field_map(self, export_scope='all', variant='standard'):
        self.ensure_one()
        scope = (export_scope or 'all').lower()
        var = (variant or 'standard').lower()
        if var == 'consolidated':
            return ('signed_consolidated_award_document', 'signed_consolidated_award_filename', 'Consolidated')
        if var == 'rr':
            return ('signed_rr_award_document', 'signed_rr_award_filename', 'R&R')
        if scope == 'land':
            return ('signed_land_award_document', 'signed_land_award_filename', 'Land')
        if scope == 'tree':
            return ('signed_tree_award_document', 'signed_tree_award_filename', 'Tree')
        if scope == 'asset':
            return ('signed_asset_award_document', 'signed_asset_award_filename', 'Asset')
        return (False, False, False)

    def action_download_signed_award_file(self, export_scope='all', variant='standard', file_format='pdf'):
        """Download uploaded signed award PDF for selected section/variant."""
        self.ensure_one()
        fmt = (file_format or 'pdf').lower()
        if fmt != 'pdf':
            raise ValidationError(_(
                'Signed award is supported only for PDF downloads.'
            ))
        file_field, name_field, label = self._s23_signed_field_map(export_scope, variant)
        if not file_field:
            raise ValidationError(_(
                'Signed download is available only for Land, Tree, Asset, Consolidated, and R&R award sections.'
            ))
        binary_data = self[file_field]
        filename = (self[name_field] or f"Signed_{label}_Award.pdf") if name_field else f"Signed_{label}_Award.pdf"
        if not binary_data:
            raise ValidationError(_(
                'No signed %s award PDF is uploaded yet. Please upload it first.'
            ) % label)
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/{file_field}/{filename}?download=true',
            'target': 'self',
        }

    def _mark_generated_scope(self, export_scope='all'):
        self.ensure_one()
        scope = export_scope or 'all'
        vals = {}
        if scope in ('all', 'land'):
            vals['land_generated'] = True
        if scope in ('all', 'asset'):
            vals['asset_generated'] = True
        if scope in ('all', 'tree'):
            vals['tree_generated'] = True
        if vals:
            self.write(vals)
        all_done = bool(self.land_generated and self.asset_generated and self.tree_generated)
        self.write({
            'is_generated': all_done,
            'state': 'approved' if all_done else 'draft',
        })

    def _mark_variant_generated(self, variant='standard'):
        self.ensure_one()
        var = (variant or 'standard').lower()
        if var == 'consolidated':
            self.write({'consolidated_generated': True})
        elif var == 'rr':
            self.write({'rr_generated': True})

    def _s23_set_loader_progress(self, done=None, total=None, label=None, active=None, flush=False):
        self.ensure_one()
        key = 'bhuarjan.s23.loader.progress.%s' % self.id
        user_key = 'bhuarjan.s23.loader.progress.user.%s' % self.env.uid
        vtype_raw = (self.village_type or (self.village_id.village_type if self.village_id else '') or '').lower()
        village_type_label = 'Urban / नगरीय' if vtype_raw == 'urban' else 'Rural / ग्रामीण'
        urban_body_label = self.get_urban_body_label() or '-'
        current = {}
        raw = self.env['ir.config_parameter'].sudo().get_param(key, default='') or ''
        if raw:
            try:
                current = json.loads(raw) if isinstance(raw, str) else {}
                if not isinstance(current, dict):
                    current = {}
            except Exception:
                current = {}
        done_val = max(0, int(done if done is not None else current.get('done') or 0))
        total_val = max(0, int(total if total is not None else current.get('total') or 0))
        pct_val = (100.0 * done_val / total_val) if total_val > 0 else float(current.get('pct') or 0.0)
        payload = {
            'active': bool(active) if active is not None else bool(current.get('active', True)),
            'done': done_val,
            'total': total_val,
            'pct': pct_val,
            'label': label if label is not None else (current.get('label') or ''),
            'project': self.project_id.name if self.project_id else '',
            'village': self.village_id.name if self.village_id else '',
            'village_type': village_type_label,
            'urban_body': urban_body_label,
        }
        try:
            if flush:
                # Write progress in an isolated transaction to avoid concurrent
                # updates on the same award row.
                from odoo.modules.registry import Registry
                with Registry(self.env.cr.dbname).cursor() as cr2:
                    env2 = api.Environment(cr2, self.env.uid, dict(self.env.context))
                    env2['ir.config_parameter'].sudo().set_param(key, json.dumps(payload))
                    env2['ir.config_parameter'].sudo().set_param(user_key, json.dumps(payload))
                    cr2.commit()
            else:
                self.env['ir.config_parameter'].sudo().set_param(key, json.dumps(payload))
                self.env['ir.config_parameter'].sudo().set_param(user_key, json.dumps(payload))
        except Exception:
            _logger.exception("Failed loader progress write for award %s", self.id)

    @api.model
    def get_loader_progress(self, award_id):
        rec = self.browse(int(award_id or 0))
        if not rec or not rec.exists():
            return {}
        key = 'bhuarjan.s23.loader.progress.%s' % rec.id
        raw = self.env['ir.config_parameter'].sudo().get_param(key, default='') or ''
        if raw:
            try:
                payload = json.loads(raw)
                if isinstance(payload, dict):
                    payload.setdefault('project', rec.project_id.name if rec.project_id else '')
                    payload.setdefault('village', rec.village_id.name if rec.village_id else '')
                    vtype_raw = (rec.village_type or (rec.village_id.village_type if rec.village_id else '') or '').lower()
                    payload.setdefault('village_type', 'Urban / नगरीय' if vtype_raw == 'urban' else 'Rural / ग्रामीण')
                    payload.setdefault('urban_body', rec.get_urban_body_label() or '-')
                    return payload
            except Exception:
                pass
        vtype_raw = (rec.village_type or (rec.village_id.village_type if rec.village_id else '') or '').lower()
        return {
            'active': False,
            'done': 0,
            'total': 0,
            'pct': 0.0,
            'label': '',
            'project': rec.project_id.name if rec.project_id else '',
            'village': rec.village_id.name if rec.village_id else '',
            'village_type': 'Urban / नगरीय' if vtype_raw == 'urban' else 'Rural / ग्रामीण',
            'urban_body': rec.get_urban_body_label() or '-',
        }

    @api.model
    def get_loader_progress_current(self):
        key = 'bhuarjan.s23.loader.progress.user.%s' % self.env.uid
        raw = self.env['ir.config_parameter'].sudo().get_param(key, default='') or ''
        if raw:
            try:
                payload = json.loads(raw)
                if isinstance(payload, dict):
                    return payload
            except Exception:
                pass
        return {
            'active': False,
            'done': 0,
            'total': 0,
            'pct': 0.0,
            'label': '',
            'project': '',
            'village': '',
            'village_type': '',
            'urban_body': '',
        }

    def _s23_increment_loader_progress(self, step=1, label=None, flush=False, active=True):
        self.ensure_one()
        current = self.get_loader_progress_current() or {}
        cur_done = int(current.get('done') or 0)
        cur_total = int(current.get('total') or 0)
        next_done = cur_done + max(0, int(step or 0))
        if cur_total > 0 and next_done > cur_total:
            next_done = cur_total
        self._s23_set_loader_progress(
            done=next_done,
            total=cur_total,
            label=label,
            active=active,
            flush=flush,
        )

    def _ensure_all_components_generated(self):
        self.ensure_one()
        all_generated = bool(
            (self.land_generated and self.asset_generated and self.tree_generated) or self.is_generated
        )
        if not all_generated:
            raise ValidationError(_(
                'All section awards must be generated first (Land + Asset + Tree), '
                'then you can download Standard/Consolidated/R&R full sheets.'
            ))

    def _generate_scope_without_download(self, export_scope='all', label=None, allow_regenerate=False):
        """Generate requested scope and update status without opening download UI."""
        self.ensure_one()
        self._s23_set_loader_progress(
            done=0,
            total=0,
            label=_('Preparing generation...'),
            active=True,
            flush=True,
        )
        gen_t0 = time.perf_counter()
        _logger.warning(
            "[S23 GENERATE START] award=%s id=%s scope=%s project=%s village=%s",
            self.name,
            self.id,
            export_scope,
            self.project_id.id if self.project_id else None,
            self.village_id.id if self.village_id else None,
        )
        had_consolidated = bool(self.consolidated_generated)
        had_rr = bool(self.rr_generated)
        self._validate_for_generate(
            require_sales_sort_rate=True,
            allow_when_fully_generated=bool(allow_regenerate),
        )
        t0 = time.perf_counter()
        self._sync_award_structure_lines()
        t_sync = time.perf_counter() - t0
        t1 = time.perf_counter()
        self._refresh_award_line_items(export_scope=export_scope, log_khasra=True)
        t_refresh = time.perf_counter() - t1
        t2 = time.perf_counter()
        self._s23_prepare_standard_scope_cache(export_scope=export_scope)
        t_cache = time.perf_counter() - t2
        # Base section change invalidates consolidated/R&R snapshots.
        self._s23_increment_loader_progress(
            step=1, label=_('Resetting dependent caches...'), flush=True, active=True
        )
        removed_count = self._s23_clear_variant_cache(variants=('consolidated', 'rr'))
        self.write({
            'consolidated_generated': False,
            'rr_generated': False,
        })
        self._s23_increment_loader_progress(
            step=1, label=_('Updating generation status...'), flush=True, active=True
        )
        self._mark_generated_scope(export_scope=export_scope)
        self._s23_set_loader_progress(
            label=_('Finalizing files...'),
            active=True,
            flush=True,
        )
        total_sec = time.perf_counter() - gen_t0
        _logger.warning(
            "[S23 GENERATE] award=%s id=%s scope=%s timings: sync=%.3fs refresh=%.3fs cache=%.3fs total=%.3fs",
            self.name, self.id, export_scope, t_sync, t_refresh, t_cache, total_sec
        )
        reset_note = ''
        if had_consolidated or had_rr:
            reset_note = _(
                ' Consolidated and R&R caches were reset. Please regenerate both before download.'
            )
        self.message_post(
            body=_("Section generated successfully. / पत्रक सफलतापूर्वक जेनरेट किया गया।") + reset_note
        )
        message = label or _('Section generated. Now use Download button for PDF/Excel.')
        if had_consolidated or had_rr:
            message = _(
                '%s Consolidated and R&R were reset and their cached files were deleted from DB (%s file(s)). '
                'Please regenerate Consolidated and R&R.'
            ) % (message, removed_count)
        current = self.get_loader_progress_current() or {}
        final_total = int(current.get('total') or 0)
        self._s23_set_loader_progress(
            done=final_total,
            total=final_total,
            label=_('Completed'),
            active=False,
            flush=True,
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Generated'),
                'message': message,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }

    def action_generate_land_award(self):
        self.ensure_one()
        return self._generate_scope_without_download(
            export_scope='land',
            label=_('Land award generated. Use Download Land Award for PDF/Excel.'),
        )

    def action_generate_tree_award(self):
        self.ensure_one()
        return self._generate_scope_without_download(
            export_scope='tree',
            label=_('Tree award generated. Use Download Tree Award for PDF/Excel.'),
        )

    def action_generate_asset_award(self):
        self.ensure_one()
        return self._generate_scope_without_download(
            export_scope='asset',
            label=_('Asset award generated. Use Download Asset Award for PDF/Excel.'),
        )

    def action_regenerate_land_award(self):
        self.ensure_one()
        return self._generate_scope_without_download(
            export_scope='land',
            label=_('Land award regenerated. Latest PDF/Excel cached and ready to download.'),
            allow_regenerate=True,
        )

    def action_regenerate_tree_award(self):
        self.ensure_one()
        return self._generate_scope_without_download(
            export_scope='tree',
            label=_('Tree award regenerated. Latest PDF/Excel cached and ready to download.'),
            allow_regenerate=True,
        )

    def action_regenerate_asset_award(self):
        self.ensure_one()
        return self._generate_scope_without_download(
            export_scope='asset',
            label=_('Asset award regenerated. Latest PDF/Excel cached and ready to download.'),
            allow_regenerate=True,
        )

    def _generate_variant_without_download(self, variant='consolidated'):
        self.ensure_one()
        self._ensure_all_components_generated()
        var = (variant or 'consolidated').lower()
        if var not in ('consolidated', 'rr'):
            var = 'consolidated'
        self._s23_prepare_variant_cache(variant=var, export_scope='all')
        self._mark_variant_generated(variant=var)
        lbl = _('Consolidated award generated. Download is ready from DB cache.')
        if var == 'rr':
            lbl = _('R&R award generated. Download is ready from DB cache.')
        self.message_post(body=lbl)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Generated'),
                'message': lbl,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }

    def action_generate_consolidated_award(self):
        self.ensure_one()
        return self._generate_variant_without_download(variant='consolidated')

    def action_generate_rr_award(self):
        self.ensure_one()
        return self._generate_variant_without_download(variant='rr')

    def action_download_land_award(self):
        self.ensure_one()
        if not self.land_generated:
            raise ValidationError(_('Generate Land Award first, then download.'))
        return self._open_award_download_wizard(
            generate=False,
            export_scope='land',
            variant='standard',
            title=_('Download Land Award / भूमि अवार्ड डाउनलोड करें'),
            simple_download_dialog=True,
        )

    def action_download_tree_award(self):
        self.ensure_one()
        if not self.tree_generated:
            raise ValidationError(_('Generate Tree Award first, then download.'))
        return self._open_award_download_wizard(
            generate=False,
            export_scope='tree',
            variant='standard',
            title=_('Download Tree Award / वृक्ष अवार्ड डाउनलोड करें'),
            simple_download_dialog=True,
        )

    def action_download_asset_award(self):
        self.ensure_one()
        if not self.asset_generated:
            raise ValidationError(_('Generate Asset Award first, then download.'))
        return self._open_award_download_wizard(
            generate=False,
            export_scope='asset',
            variant='standard',
            title=_('Download Asset Award / परिसम्पत्ति अवार्ड डाउनलोड करें'),
            simple_download_dialog=True,
        )

    def action_download_standard_full_award(self):
        self.ensure_one()
        self._ensure_all_components_generated()
        return self._open_award_download_wizard(
            generate=False,
            export_scope='all',
            variant='standard',
            title=_('Download Standard Award (Full) / मानक अवार्ड (पूर्ण) डाउनलोड करें'),
            simple_download_dialog=True,
        )

    def action_download_consolidated_full_award(self):
        self.ensure_one()
        self._ensure_all_components_generated()
        if not self.consolidated_generated:
            raise ValidationError(_('Generate Consolidated Award first, then download.'))
        return self._open_award_download_wizard(
            generate=False,
            export_scope='all',
            variant='consolidated',
            title=_('Download Consolidated Award (Full) / समेकित अवार्ड (पूर्ण) डाउनलोड करें'),
            simple_download_dialog=True,
        )

    def action_download_rr_full_award(self):
        self.ensure_one()
        self._ensure_all_components_generated()
        if not self.rr_generated:
            raise ValidationError(_('Generate R&R Award first, then download.'))
        return self._open_award_download_wizard(
            generate=False,
            export_scope='all',
            variant='rr',
            title=_('Download R&R Award (Full) / पुनर्वास अवार्ड (पूर्ण) डाउनलोड करें'),
            simple_download_dialog=True,
        )

    def get_award_village_scope_summary(self):
        """Village + component totals (Section 23, for summary export)."""
        self.ensure_one()
        land_sum = sum(
            float(g.get('paid_compensation', 0) or g.get('total_compensation', 0) or 0)
            for g in self.get_land_compensation_grouped_data()
        )
        tree_sum = sum(float(g.get('total', 0) or 0) for g in self.get_tree_compensation_grouped_data())
        struct_sum = sum(float(g.get('total', 0) or 0) for g in self.get_structure_compensation_grouped_data())
        v = self.village_id
        return {
            'village': v.name if v else '',
            'project': self.project_id.name if self.project_id else '',
            'tehsil': v.tehsil_id.name if v and v.tehsil_id else '',
            'district': v.district_id.name if v and v.district_id else '',
            'land_total': land_sum,
            'tree_total': tree_sum,
            'structure_total': struct_sum,
            'grand_total': land_sum + tree_sum + struct_sum,
        }

    def _action_download_excel_village_only(self):
        self.ensure_one()
        self._s23_recompute_award_survey_lines_for_export()
        import io
        import base64
        try:
            import xlsxwriter
        except ImportError:
            raise ValidationError(_("Python library 'xlsxwriter' is not installed."))
        s = self.get_award_village_scope_summary()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Village')
        title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'border': 1})
        label_fmt = workbook.add_format({'border': 1, 'bold': True})
        cell_fmt = workbook.add_format({'border': 1})
        money_fmt = workbook.add_format({'border': 1, 'num_format': '#,##0', 'align': 'right'})
        row = 0
        sheet.merge_range(row, 0, row, 2, 'SECTION 23 VILLAGE SUMMARY / धारा 23 ग्राम सारांश', title_fmt)
        row += 2
        rows = [
            ('Village / ग्राम', s['village'], False),
            ('Project / परियोजना', s['project'], False),
            ('Tehsil / तहसील', s['tehsil'], False),
            ('District / जिला', s['district'], False),
            ('Land total (₹) / भूमि कुल', s['land_total'], True),
            ('Trees total (₹) / वृक्ष कुल', s['tree_total'], True),
            ('Structure total (₹) / परिसम्पत्ति कुल', s['structure_total'], True),
            ('Grand total (₹) / कुल', s['grand_total'], True),
        ]
        for label, val, is_money in rows:
            sheet.write(row, 0, label, label_fmt)
            if is_money:
                sheet.write_number(row, 1, float(val or 0.0), money_fmt)
            else:
                sheet.write(row, 1, val or '', cell_fmt)
            row += 1
        sheet.set_column(0, 0, 38)
        sheet.set_column(1, 1, 28)
        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())
        output.close()
        attachment = self.env['ir.attachment'].create({
            'name': f"Section23_Village_Summary_{self.village_id.name or self.name or 'Export'}.xlsx",
            'type': 'binary',
            'datas': file_data,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_download_excel(self, export_scope='all'):
        """Alias to keep wizard and buttons on the same simulator-format excel."""
        self.ensure_one()
        return self.action_download_excel_components(export_scope=export_scope)


    def action_download_pdf_components(self, export_scope='all', include_cover_letter=False):
        """Download Section 23 PDF with selected section scope."""
        self.ensure_one()
        self._s23_recompute_award_survey_lines_for_export()
        scope = export_scope or self.env.context.get('bhu_export_scope') or 'all'
        if scope not in ('all', 'land', 'asset', 'tree'):
            scope = 'all'
        report_action = self._get_section23_report_action()
        return report_action.with_context(
            s23_pdf_scope=scope,
            s23_include_cover=bool(include_cover_letter),
        ).report_action(self)
    
    def _validate_for_generate(self, require_sales_sort_rate=True, allow_when_fully_generated=False):
        """Pre-checks for opening/running generate flow.

        ``require_sales_sort_rate`` keeps the generator strict on rate entry.
        """
        self.ensure_one()
        # Ensure missing rate fields are auto-filled from village master first.
        # User-edited non-zero values are preserved (force=False).
        self._sync_rate_fields_from_master(force=False)
        # Avoid flushing parent award row here (can cause concurrent update retries
        # during regenerate). Flush only child line buffers if present.
        if self.award_survey_line_ids:
            self.award_survey_line_ids.flush_recordset()
        if self.award_structure_line_ids:
            self.award_structure_line_ids.flush_recordset()
        if (not allow_when_fully_generated) and self.land_generated and self.tree_generated and self.asset_generated:
            raise ValidationError(_(
                'All section awards are already generated for this Project and Village. '
                'Use Download options instead of generating again.'
            ))
        if not self.project_id:
            raise ValidationError(_('Please select a project first.'))
        if not self.village_id:
            raise ValidationError(_('Please select a village first.'))
        if not (self.case_number or '').strip():
            raise ValidationError(_(
                'Please enter the Case Number / प्रकरण क्रमांक before generating the award.'
            ))
        if not self._get_section4_approval_date():
            raise ValidationError(_(
                'Section 4 notification is not approved yet for this project and village.\n'
                'Please get the Section 4 approved before creating the award.\n\n'
                'इस प्रोजेक्ट और गाँव के लिए धारा 4 की अधिसूचना अभी स्वीकृत नहीं हुई है।\n'
                'अवार्ड बनाने से पहले कृपया धारा 4 की स्वीकृति प्राप्त करें।'
            ))
        if not self.award_survey_line_ids:
            self._populate_award_survey_lines(reset_if_empty=False)
        if not self.award_survey_line_ids:
            raise ValidationError(_(
                'No surveys found for this village. Cannot generate award.\n'
                'इस गाँव के लिए कोई स्वीकृत सर्वेक्षण नहीं मिला। अवार्ड उत्पन्न नहीं किया जा सकता।'
            ))
        missing_lines = self.award_survey_line_ids.filtered(lambda l: not l.land_type)
        if missing_lines:
            survey_names = ', '.join([line.survey_id.name for line in missing_lines if line.survey_id][:5])
            if len(missing_lines) > 5:
                survey_names += '...'
            raise ValidationError(_(
                'Please select type (Village/Residential) for all surveys before generating award.\n'
                'Missing type selection for surveys: %s'
            ) % survey_names)
        bad_struct = self.award_structure_line_ids.filtered(lambda l: not l.survey_id)
        if bad_struct:
            raise ValidationError(_(
                'Select a khasra for every structure line before generating the award, or remove empty lines.\n'
                'अवार्ड जेनरेट करने से पहले हर संरचना पंक्ति के लिए खसरा चुनें, या खाली पंक्तियाँ हटा दें।'
            ))
        if require_sales_sort_rate:
            rate = float(self.avg_three_year_sales_sort_rate or 0.0)
            if rate <= 0.0:
                raise ValidationError(_(
                    'Please enter विगत तीन वर्षों का औसत बिक्री छांट दर (must be greater than zero) '
                    'before generating the award.\n'
                    'अवार्ड जेनरेट करने से पहले यह दर दर्ज करें।'
                ))
        mr_rate = float(self.rate_master_main_road_ha or 0.0)
        bmr_rate = float(self.rate_master_other_road_ha or 0.0)
        if mr_rate <= 0.0 or bmr_rate <= 0.0:
            raise ValidationError(_(
                'Please enter both MR Rate and BMR Rate (greater than zero) before generating the award.\n'
                'अवार्ड जेनरेट करने से पहले MR Rate और BMR Rate दोनों दर्ज करें।'
            ))
        if self.is_urban:
            if not (self.urban_body_type or '').strip():
                raise ValidationError(_(
                    'For Urban awards, please select Urban Body Type before generating the award.\n'
                    'नगरीय अवार्ड के लिए जेनरेट करने से पहले Urban Body Type चुनना आवश्यक है।'
                ))
            mr_sqm = float(self.rate_master_main_road_sqm or 0.0)
            bmr_sqm = float(self.rate_master_other_road_sqm or 0.0)
            if mr_sqm <= 0.0 or bmr_sqm <= 0.0:
                raise ValidationError(_(
                    'For Urban awards, please enter both MR and BMR rates in square meter (greater than zero).\n'
                    'नगरीय अवार्ड के लिए MR और BMR दोनों वर्गमीटर दरें दर्ज करना आवश्यक है।'
                ))

    def action_generate_award(self):
        """Generate all section scopes without download prompt."""
        self.ensure_one()
        return self._generate_scope_without_download(
            export_scope='all',
            label=_('All sections generated. Full Standard/Consolidated/R&R downloads are now enabled.'),
        )

    def apply_generate_from_download_wizard(self, file_format, export_scope='all', include_cover_letter=False, generate_variant='standard'):
        """Called from bhu.award.download.wizard when Section 23 generate is confirmed."""
        self.ensure_one()
        import base64
        from datetime import datetime
        _logger.warning(
            "[S23 GENERATE WIZARD START] award=%s id=%s scope=%s variant=%s format=%s",
            self.name, self.id, export_scope, generate_variant, file_format
        )

        self._validate_for_generate(require_sales_sort_rate=True)
        self._sync_award_structure_lines()
        self._refresh_award_line_items(export_scope=export_scope or 'all', log_khasra=True)

        variant = generate_variant or 'standard'
        if variant not in ('standard', 'consolidated', 'rr'):
            variant = 'standard'

        if variant == 'consolidated':
            self._ensure_all_components_generated()
            self.write({'is_generated': True, 'state': 'approved'})
            self.message_post(body=_("Consolidated award generated and auto-approved. / समेकित अवार्ड जेनरेट किया गया और स्वतः अनुमोदित हुआ।"))
            if file_format == 'excel':
                return self.action_download_consolidated_excel()
            return self.action_download_consolidated_pdf()

        if variant == 'rr':
            self._ensure_all_components_generated()
            self.write({'is_generated': True, 'state': 'approved'})
            self.message_post(body=_("R&R award generated and auto-approved. / पुनर्वास अवार्ड जेनरेट किया गया और स्वतः अनुमोदित हुआ।"))
            if file_format == 'excel':
                return self.action_download_rr_excel()
            return self.action_download_rr_pdf()

        if file_format == 'excel':
            self._mark_generated_scope(export_scope=export_scope or 'all')
            self.message_post(body=_("Section award generated. / संबंधित पत्रक जेनरेट किया गया।"))
            return self.action_download_excel_components(export_scope=export_scope or 'all')

        if file_format != 'pdf':
            raise ValidationError(_('Unsupported format for generate.'))

        scope = export_scope or 'all'
        if scope not in ('all', 'land', 'asset', 'tree'):
            scope = 'all'

        report_action = self._get_section23_report_action()
        pdf_result = report_action.sudo().with_context(
            s23_pdf_scope=scope,
            s23_include_cover=bool(include_cover_letter),
        )._render_qweb_pdf(
            report_action.id,
            [self.id],
            data={},
        )
        if pdf_result:
            pdf_data = pdf_result[0] if isinstance(pdf_result, (tuple, list)) else pdf_result
            if isinstance(pdf_data, bytes):
                filename = (
                    f"Section23_Award_"
                    f"{(self.village_id.name or '').replace(' ', '_')}_"
                    f"{datetime.now().strftime('%Y%m%d')}.pdf"
                )
                self.write({
                    'award_document': base64.b64encode(pdf_data),
                    'award_document_filename': filename,
                })
                self._mark_generated_scope(export_scope=scope)
                self.message_post(body=_("Section award generated. / संबंधित पत्रक जेनरेट किया गया।"))
                return {
                    'type': 'ir.actions.act_url',
                    'url': f'/web/content/{self._name}/{self.id}/award_document/{filename}?download=true',
                    'target': 'self',
                }

        self._mark_generated_scope(export_scope=scope)
        self.message_post(body=_("Section award generated. / संबंधित पत्रक जेनरेट किया गया।"))
        return report_action.with_context(
            s23_pdf_scope=scope,
            s23_include_cover=bool(include_cover_letter),
        ).report_action(self)
    
    def _get_section23_report_action(self):
        """Get Section 23 report action with safe fallback when xmlid is missing."""
        self.ensure_one()
        try:
            return self.env.ref('bhuarjan.action_report_section23_award')
        except Exception:
            report_action = self.env['ir.actions.report'].search([
                ('model', '=', 'bhu.section23.award'),
                ('report_name', '=', 'bhuarjan.section23_award_report'),
                ('report_type', '=', 'qweb-pdf'),
            ], limit=1)
            if report_action:
                return report_action
            raise ValidationError(_(
                'Section 23 report action is missing. Please upgrade module "bhuarjan" '
                'to load report xml id: bhuarjan.action_report_section23_award'
            ))

    def _sync_award_structure_lines(self):
        """Link survey-level structure entries to this award."""
        self.ensure_one()
        survey_ids = self.award_survey_line_ids.mapped('survey_id').ids
        if not survey_ids:
            return
        structure_lines = self.env['bhu.award.structure.details'].search([
            ('survey_id', 'in', survey_ids),
            ('award_id', '!=', self.id),
        ])
        if structure_lines:
            structure_lines.write({'award_id': self.id})

    def _refresh_award_line_items(self, export_scope='all', log_khasra=False):
        """Persist generated line-items so users can review rows from DB later.

        Optimized: for section-wise generation, only refresh requested scope.
        """
        self.ensure_one()
        self.award_line_item_ids.unlink()
        scope = (export_scope or 'all').lower()
        if scope not in ('all', 'land', 'tree', 'asset'):
            scope = 'all'
        def _safe_amount(val):
            try:
                if val in (None, False, ''):
                    return 0.0
                if isinstance(val, str):
                    val = val.replace(',', '').replace('₹', '').strip()
                return float(val)
            except Exception:
                return 0.0

        line_vals = []
        land_rows = self.get_land_compensation_data() if scope in ('all', 'land') else []
        tree_rows = self.get_tree_compensation_data() if scope in ('all', 'tree') else []
        asset_rows = self.get_structure_compensation_data() if scope in ('all', 'asset') else []
        # Progress row count should reflect visible/logical rows for land (khasra-level),
        # not internal owner-split calculation entries.
        land_khasra_from_lines = set(
            filter(None, (self.award_survey_line_ids.mapped('khasra_number') if self.award_survey_line_ids else []))
        )
        if land_khasra_from_lines:
            land_progress_rows = len(land_khasra_from_lines)
        else:
            land_progress_rows = len({
                (r.get('khasra') or '').strip()
                for r in land_rows
                if (r.get('khasra') or '').strip()
            }) if land_rows else 0
        tree_progress_rows = len(tree_rows)
        asset_progress_rows = len(asset_rows)
        total_rows = land_progress_rows + tree_progress_rows + asset_progress_rows
        # Keep final progress room for cache/upload/status phases after rows are processed.
        tail_steps = 6
        total_units = (total_rows + tail_steps) if total_rows > 0 else tail_steps
        processed_rows = 0
        self._s23_set_loader_progress(
            done=0,
            total=total_units,
            label=_('Processing award rows...'),
            active=True,
            flush=True,
        )

        def _bump_progress(label_text):
            nonlocal processed_rows
            processed_rows += 1
            if processed_rows == total_rows or processed_rows % 5 == 0:
                self._s23_set_loader_progress(
                    done=processed_rows,
                    total=total_units,
                    label=label_text,
                    active=True,
                    flush=True,
                )

        if scope in ('all', 'land'):
            seen_land_khasra = set()
            for row in land_rows:
                khasra = row.get('khasra', '')
                line_vals.append((0, 0, {
                    'line_type': 'land',
                    'landowner_name': row.get('landowner_name', ''),
                    'khasra_number': khasra,
                    'original_area': row.get('original_area', 0.0) or 0.0,
                    'acquired_area': row.get('acquired_area', 0.0) or 0.0,
                    'is_within_distance': bool(row.get('is_within_distance')),
                    'irrigated': bool(row.get('irrigated')),
                    'unirrigated': bool(row.get('unirrigated')),
                    'is_diverted': bool(row.get('is_diverted')),
                    'guide_line_rate': row.get('guide_line_rate', 0.0) or 0.0,
                    'basic_value': row.get('basic_value', 0.0) or 0.0,
                    'market_value': row.get('market_value', 0.0) or 0.0,
                    'solatium': row.get('solatium', 0.0) or 0.0,
                    'interest': row.get('interest', 0.0) or 0.0,
                    'total_compensation': row.get('total_compensation', 0.0) or 0.0,
                    'rehab_policy_amount': row.get('rehab_policy_amount', 0.0) or 0.0,
                    'paid_compensation': row.get('paid_compensation', 0.0) or 0.0,
                    'remark': row.get('remark', '') or '',
                }))
                k_key = (khasra or '').strip()
                if k_key and k_key not in seen_land_khasra:
                    seen_land_khasra.add(k_key)
                    _bump_progress(_('Processing land rows...'))
            if log_khasra:
                _logger.warning(
                    "[S23 GENERATE][LAND] award=%s id=%s rows=%s calc_entries=%s total_amount=%.2f",
                    self.name,
                    self.id,
                    land_progress_rows,
                    len(land_rows),
                    sum(_safe_amount(r.get('total_compensation', 0.0)) for r in land_rows),
                )

        if scope in ('all', 'tree'):
            for row in tree_rows:
                khasra = row.get('khasra', '')
                line_vals.append((0, 0, {
                    'line_type': 'tree',
                    'landowner_name': row.get('landowner_name', ''),
                    'khasra_number': khasra,
                    'total_compensation': row.get('total', 0.0) or 0.0,
                    'remark': row.get('tree_type', '') or '',
                }))
                _bump_progress(_('Processing tree rows...'))
            if log_khasra:
                _logger.warning(
                    "[S23 GENERATE][TREE] award=%s id=%s rows=%s total_amount=%.2f",
                    self.name,
                    self.id,
                    len(tree_rows),
                    sum(_safe_amount(r.get('total', 0.0)) for r in tree_rows),
                )

        if scope in ('all', 'asset'):
            for row in asset_rows:
                khasra = row.get('asset_khasra', '')
                line_vals.append((0, 0, {
                    'line_type': 'structure',
                    'landowner_name': row.get('landowner_name', ''),
                    'khasra_number': khasra,
                    'acquired_area': row.get('total_area', 0.0) or 0.0,
                    'guide_line_rate': row.get('market_value', 0.0) or 0.0,
                    'solatium': row.get('solatium', 0.0) or 0.0,
                    'interest': row.get('interest', 0.0) or 0.0,
                    'total_compensation': row.get('total', 0.0) or 0.0,
                    'remark': row.get('asset_type', '') or '',
                }))
                _bump_progress(_('Processing asset rows...'))
            if log_khasra:
                _logger.warning(
                    "[S23 GENERATE][ASSET] award=%s id=%s rows=%s total_amount=%.2f",
                    self.name,
                    self.id,
                    len(asset_rows),
                    sum(_safe_amount(r.get('total', 0.0)) for r in asset_rows),
                )

        if line_vals:
            self.write({'award_line_item_ids': line_vals})
        self._s23_set_loader_progress(
            done=total_rows,
            total=total_units,
            label=_('Rows processed. Preparing documents...'),
            active=True,
            flush=True,
        )
    
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
        """Mark award as Generated/Approved (used for legacy records generated before auto-approve)."""
        self.ensure_one()
        self.write({'state': 'approved', 'is_generated': True})
        self.message_post(body=_("Award marked as Generated / अवार्ड उत्पन्न के रूप में चिह्नित किया गया।"))

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

    def _get_section4_public_hearing_date(self):
        """Return section 4 public hearing date for this project/village."""
        self.ensure_one()
        if not self.project_id or not self.village_id:
            return False
        section4_records = self.env['bhu.section4.notification'].search([
            ('project_id', '=', self.project_id.id),
            ('village_id', '=', self.village_id.id),
        ], order='public_hearing_date desc, public_hearing_datetime desc, id desc', limit=10)
        for section4 in section4_records:
            if section4.public_hearing_date:
                return fields.Date.to_date(section4.public_hearing_date)
            if section4.public_hearing_datetime:
                dt = fields.Datetime.to_datetime(section4.public_hearing_datetime)
                return dt.date() if dt else False
        return False

    def get_award_header_constants(self):
        """Shared award header labels used by Excel and PDF outputs."""
        self.ensure_one()
        return get_award_header_constants()

    def _get_award_calculation_date(self):
        """Return award creation date used for interest end date."""
        self.ensure_one()
        if self.award_date:
            return fields.Date.to_date(self.award_date)
        if self.create_date:
            return fields.Datetime.to_datetime(self.create_date).date()
        return fields.Date.context_today(self)

    def _calculate_interest_on_basic(self, basic_value):
        """Calculate interest at 1% per month (or part thereof)."""
        self.ensure_one()
        start_date = self._get_section4_public_hearing_date()
        end_date = self._get_award_calculation_date()
        if not start_date or not end_date or not basic_value:
            return 0.0, 0
        if end_date < start_date:
            start_date, end_date = end_date, start_date
        days = (end_date - start_date).days
        if days <= 0:
            return 0.0, 0
        # Count partial month as full month:
        # 01/01 to 26/04 => 4 months => 4%
        months = (days + 29) // 30
        interest = basic_value * 0.01 * months
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
        """Minimum rehab policy rate per acre for Col 17 floor.

        Policy mapping used:
        - Irrigated: 10,00,000 per acre
        - Unirrigated (default): 8,00,000 per acre
        - Fallow: 6,00,000 per acre
        """
        if is_irrigated:
            return 1000000.0
        if is_fallow:
            return 600000.0
        return 800000.0

    @api.model
    def _s23_bmr_rate_multiplier(self, is_mr_lane, is_diverted, is_irrigated):
        """Guideline land-rate factors apply only on the BMR lane (off main-road master rate).

        MR lane (``is_mr_lane``): multiplier **1.0**.

        BMR lane:
        - **Diverted + irrigated**: **×1.25** on the BMR master rate.
        - **Diverted + unirrigated**: **×1.0** on the BMR master rate.
        - **Not diverted + irrigated**: **×1.0** on the BMR master rate.
        - **Not diverted + unirrigated**: **×0.8** on the BMR master rate.
        """
        if is_mr_lane:
            return 1.0
        if is_diverted and is_irrigated:
            return 1.25
        return 1.0 if is_irrigated else 0.8

    def get_interest_period_note(self):
        """Text note for report header interest period from Section 4 public hearing to award date."""
        self.ensure_one()
        start_date = self._get_section4_public_hearing_date()
        end_date = self._get_award_calculation_date()
        if start_date and end_date:
            if end_date < start_date:
                start_date, end_date = end_date, start_date
            return f"{start_date.strftime('%d/%m/%Y')} से {end_date.strftime('%d/%m/%Y')} तक"
        return "धारा 4 सार्वजनिक सुनवाई दिनांक से अवार्ड दिनांक तक"

    def _s23_land_base_rate_per_hectare(self, survey, award_line, derived_within):
        """MR/BMR rate from award values; fallback to active land rate master."""
        self.ensure_one()
        if not self.village_id or not survey:
            return 0.0
        mr_rate = float(self.rate_master_main_road_ha or 0.0)
        bmr_rate = float(self.rate_master_other_road_ha or 0.0)
        if mr_rate <= 0.0 or bmr_rate <= 0.0:
            rm = self._get_active_rate_master_for_village()
            if rm:
                if mr_rate <= 0.0:
                    mr_rate = float(rm.main_road_rate_hectare or 0.0)
                if bmr_rate <= 0.0:
                    bmr_rate = float(rm.other_road_rate_hectare or 0.0)
        land_type = (award_line.land_type if award_line else (survey.land_type_for_award or 'village'))
        is_within = award_line.is_within_distance if award_line else derived_within
        if land_type not in ('village', 'residential'):
            land_type = 'village'
        if is_within:
            return mr_rate
        return bmr_rate

