# -*- coding: utf-8 -*-

import json
import logging
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
    ], string='Status', default='draft', tracking=True, index=True)
    
    is_generated = fields.Boolean(string='Is Generated', default=False, tracking=True)
    
    village_domain = fields.Char()
    
    # Survey lines for award generation
    award_survey_line_ids = fields.One2many('bhu.section23.award.survey.line', 'award_id', 
                                            string='Approved Surveys / स्वीकृत सर्वेक्षण',
                                            help='Select type and distance for each approved survey')
    # Khasra search filter — stored so value persists across reloads
    khasra_filter = fields.Char(string='Search Khasra', default='')
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
            threshold = 50.0 if survey.survey_type == 'rural' else 30.0
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
        for rec in self:
            old_p, old_v = pre_scope.get(rec.id, (False, False))
            new_p = rec.project_id.id if rec.project_id else False
            new_v = rec.village_id.id if rec.village_id else False
            if new_p != old_p or new_v != old_v:
                rec._populate_award_survey_lines(reset_if_empty=True)
                if rec.project_id and rec.village_id:
                    rec._sync_award_structure_lines()
        return result

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
            threshold = 50.0 if survey.survey_type == 'rural' else 30.0
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

    def action_refresh_land_rates(self):
        """Force-recompute rate_per_hectare and display amounts for all land survey lines."""
        self.ensure_one()
        lines = self.award_survey_line_ids
        if lines:
            lines._compute_rate_per_hectare()
            lines._compute_line_display_amounts()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Rates Refreshed',
                'message': f'Recomputed rates for {len(lines)} land survey line(s) from the active rate master.',
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
        # Same columns as Award Simulator land grid (Khasra → Interest).
        headers = [
            'Khasra / खसरा', 'Village / ग्राम', 'Distance (m) / दूरी', 'Road / सड़क', 'Irrigation / सिंचाई', 'Diverted / विचलित',
            'Acquired (Ha) / अधि.', f'Base ({cur_sym}/Ha)', f'Effective ({cur_sym}/Ha)', f'Land award ({cur_sym})',
            f'Solatium ({cur_sym})', f'Interest ({cur_sym})',
        ]
        parts = [
            '<div class="table-responsive s23-preview-wrap s23-land-sim-table-wrap">',
            '<table class="table table-sm s23-sim-table s23-sim-table-land">',
            '<thead><tr>',
        ]
        for col in headers:
            parts.append(f'<th class="s23-sim-th" scope="col">{escape(col)}</th>')
        parts.append('</tr></thead><tbody>')
        for r in rows:
            parts.append('<tr>')
            parts.append(f'<td class="text-nowrap">{escape(r.get("khasra") or "")}</td>')
            parts.append(f'<td class="text-nowrap">{escape(r.get("village_name") or "")}</td>')
            parts.append(f'<td class="text-end tabular-nums">{self._html_s23_num(r.get("distance_from_main_road"), 2)}</td>')
            road = (r.get("road_type_label") or ("MR" if r.get("is_within_distance") else "BMR"))
            parts.append(f'<td class="text-nowrap text-center"><span class="s23-sim-badge">{escape(road)}</span></td>')
            parts.append(f'<td class="text-nowrap small">{escape(r.get("irrigation_label") or "")}</td>')
            div_lbl = (r.get("diverted_label") or ("Yes" if r.get("is_diverted") else "No"))
            parts.append(f'<td class="text-center text-nowrap">{escape(div_lbl)}</td>')
            parts.append(f'<td class="text-end tabular-nums">{self._html_s23_num(r.get("acquired_area"), 4)}</td>')
            parts.append(f'<td class="text-end tabular-nums">{self._html_s23_num(r.get("base_rate_hectare") or 0, 0)}</td>')
            eff = r.get("effective_rate_hectare")
            if eff is None:
                eff = r.get("guide_line_rate")
            parts.append(f'<td class="text-end tabular-nums fw-semibold">{self._html_s23_num(eff, 0)}</td>')
            parts.append(f'<td class="text-end tabular-nums">{self._html_s23_num(r.get("basic_value"), 0)}</td>')
            parts.append(f'<td class="text-end tabular-nums">{self._html_s23_num(r.get("solatium"), 0)}</td>')
            parts.append(f'<td class="text-end tabular-nums">{self._html_s23_num(r.get("interest"), 0)}</td>')
            parts.append('</tr>')
        parts.append(
            '</tbody></table><p class="s23-sim-hint text-muted small mb-0">'
            'Values follow the same rules as the Section 23 PDF / पीडीऐफ़ के समान नियम'
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
            'Owner', 'Khasra', 'Tree', 'Tree Type', 'Dev. Stage',
            'Girth (cm)', 'Qty',
            f'Unit Rate ({cur_sym})', f'Value ({cur_sym})',
            f'Solatium ({cur_sym})', f'Interest ({cur_sym})', f'Total ({cur_sym})',
        ]
        parts = [
            '<div class="table-responsive s23-preview-wrap s23-land-sim-table-wrap">',
            '<table class="table table-sm s23-sim-table s23-sim-table-land">',
            '<thead><tr>',
        ]
        for col in headers:
            parts.append(f'<th class="s23-sim-th" scope="col">{escape(col)}</th>')
        parts.append('</tr></thead><tbody>')
        for r in rows:
            parts.append('<tr>')
            parts.append(f'<td class="text-nowrap">{escape(r.get("landowner_name") or "")}</td>')
            parts.append(f'<td class="text-nowrap">{escape(r.get("tree_khasra") or r.get("khasra") or "")}</td>')
            parts.append(f'<td class="text-nowrap">{escape(str(r.get("tree_type") or ""))}</td>')
            # Tree type code label
            tc = r.get("tree_type_code") or ""
            tc_label = "Fruit Bearing" if tc == "fruit_bearing" else ("Timber" if tc == "timber" else tc.replace("_", " ").title())
            parts.append(f'<td class="text-nowrap small">{escape(tc_label)}</td>')
            _ds_map = {'undeveloped': 'Undeveloped', 'semi_developed': 'Semi-Developed', 'fully_developed': 'Fully Developed'}
            ds_label = _ds_map.get(r.get('development_stage') or '', r.get('development_stage') or '—')
            parts.append(f'<td class="text-nowrap small">{escape(ds_label)}</td>')
            parts.append(f'<td class="text-end tabular-nums">{self._html_s23_num(r.get("girth_cm"), 1)}</td>')
            parts.append(f'<td class="text-end tabular-nums">{self._html_s23_num(r.get("tree_count"), 0)}</td>')
            unit_rate = r.get("unit_rate") or r.get("rate") or 0
            parts.append(f'<td class="text-end tabular-nums">{self._html_s23_num(unit_rate, 0)}</td>')
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
        report_action = self._get_section23_report_action()
        return {
            'name': _('Download Section 23 Award / धारा 23 अवार्ड डाउनलोड करें'),
            'type': 'ir.actions.act_window',
            'res_model': 'bhu.award.download.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
                'default_report_xml_id': report_action.get_external_id().get(report_action.id, 'bhuarjan.action_report_section23_award'),
                'default_filename': f'Section23_Award_{self.name}.doc',
                'default_export_scope': 'all',
                'default_add_cover_letter': True,
            }
        }

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
        scope = export_scope or self.env.context.get('bhu_export_scope') or 'all'
        if scope not in ('all', 'land', 'asset', 'tree'):
            scope = 'all'
        report_action = self._get_section23_report_action()
        return report_action.with_context(
            s23_pdf_scope=scope,
            s23_include_cover=bool(include_cover_letter),
        ).report_action(self)
    
    def _validate_for_generate(self, require_sales_sort_rate=True):
        """Pre-checks for opening/running generate flow.

        ``require_sales_sort_rate`` should be False when only opening the popup,
        because the value is entered in that wizard.
        """
        self.ensure_one()
        # Ensure O2M is flushed so we do not call _populate with a false "empty" after edits.
        self.flush_recordset()
        if self.is_generated:
            raise ValidationError(_(
                'Award already generated for this Project and Village. '
                'Use Download instead of generating again.'
            ))
        if not self.project_id:
            raise ValidationError(_('Please select a project first.'))
        if not self.village_id:
            raise ValidationError(_('Please select a village first.'))
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

    def action_generate_award(self):
        """Open the same download wizard as Award Simulator; confirm runs generate (PDF/Excel)."""
        self.ensure_one()
        self._validate_for_generate(require_sales_sort_rate=False)
        report_action = self._get_section23_report_action()
        xmlid = report_action.get_external_id().get(
            report_action.id, 'bhuarjan.action_report_section23_award'
        )
        return {
            'name': _('Generate Section 23 Award / अवार्ड जेनरेट करें'),
            'type': 'ir.actions.act_window',
            'res_model': 'bhu.award.download.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
                'default_report_xml_id': xmlid,
                'default_filename': f'Section23_Award_{self.name}.pdf',
                'default_export_scope': 'all',
                'default_section23_generate': True,
                'default_add_cover_letter': True,
            },
        }

    def apply_generate_from_download_wizard(self, file_format, export_scope='all', include_cover_letter=False):
        """Called from bhu.award.download.wizard when Section 23 generate is confirmed."""
        self.ensure_one()
        import base64
        from datetime import datetime

        self._validate_for_generate(require_sales_sort_rate=True)
        self._sync_award_structure_lines()
        self._refresh_award_line_items()

        if file_format == 'excel':
            self.write({'is_generated': True})
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
                    'is_generated': True,
                })
                return {
                    'type': 'ir.actions.act_url',
                    'url': f'/web/content/{self._name}/{self.id}/award_document/{filename}?download=true',
                    'target': 'self',
                }

        self.write({'is_generated': True})
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

    def _refresh_award_line_items(self):
        """Persist generated line-items so users can review rows from DB later."""
        self.ensure_one()
        self.award_line_item_ids.unlink()

        line_vals = []
        for row in self.get_land_compensation_data():
            line_vals.append((0, 0, {
                'line_type': 'land',
                'landowner_name': row.get('landowner_name', ''),
                'khasra_number': row.get('khasra', ''),
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

        for row in self.get_tree_compensation_data():
            line_vals.append((0, 0, {
                'line_type': 'tree',
                'landowner_name': row.get('landowner_name', ''),
                'khasra_number': row.get('khasra', ''),
                'total_compensation': row.get('total', 0.0) or 0.0,
                'remark': row.get('tree_type', '') or '',
            }))

        for row in self.get_structure_compensation_data():
            line_vals.append((0, 0, {
                'line_type': 'structure',
                'landowner_name': row.get('landowner_name', ''),
                'khasra_number': row.get('asset_khasra', ''),
                'acquired_area': row.get('total_area', 0.0) or 0.0,
                'guide_line_rate': row.get('market_value', 0.0) or 0.0,
                'solatium': row.get('solatium', 0.0) or 0.0,
                'interest': row.get('interest', 0.0) or 0.0,
                'total_compensation': row.get('total', 0.0) or 0.0,
                'remark': row.get('asset_type', '') or '',
            }))

        if line_vals:
            self.write({'award_line_item_ids': line_vals})
    
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
        if self.create_date:
            return fields.Datetime.to_datetime(self.create_date).date()
        if self.award_date:
            return fields.Date.to_date(self.award_date)
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
        """MR/BMR line from the active land rate master (before irrigation and diverted %), for display."""
        self.ensure_one()
        if not self.village_id or not survey:
            return 0.0
        rm = self.env['bhu.rate.master'].search([
            ('village_id', '=', self.village_id.id),
            ('state', 'in', ['active', 'draft']),
        ], limit=1, order='state ASC, effective_from DESC')
        if not rm:
            return 0.0
        land_type = (award_line.land_type if award_line else (survey.land_type_for_award or 'village'))
        is_within = award_line.is_within_distance if award_line else derived_within
        if land_type not in ('village', 'residential'):
            land_type = 'village'
        if is_within:
            return rm.main_road_rate_hectare or 0.0
        return rm.other_road_rate_hectare or 0.0

