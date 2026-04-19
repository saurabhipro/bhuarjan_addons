# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from .award_header_constants import get_award_header_constants


class AwardSimulator(models.Model):
    _name = 'bhu.award.simulator'
    _description = 'Award Simulator / अवार्ड सिमुलेटर'
    _order = 'id desc'

    user_id = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    # ─── Survey Type ───────────────────────────────────────────────────────────
    survey_type = fields.Selection([
        ('rural', 'Rural / ग्रामीण'),
        ('urban', 'Urban / शहरी'),
    ], string='Survey Type / सर्वे प्रकार', required=True, default='rural')

    # ─── Land Section ──────────────────────────────────────────────────────────
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम')
    district_id = fields.Many2one('bhu.district', string='District / जिला')
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना')

    base_rate = fields.Float(
        string='Base Rate per Hectare (₹) / आधार दर प्रति हेक्टेयर',
        digits=(16, 2),
        help='Enter the base land rate per hectare manually, or it will be auto-filled from the Land Rate Master if a village is selected.'
    )

    distance_from_road = fields.Float(
        string='Distance from Main Road (M) / मुख्य मार्ग से दूरी (मीटर)',
        digits=(10, 2), default=0.0,
        help='Rural: <= 50m is MR, Urban: <= 20m is MR'
    )

    road_type = fields.Selection([
        ('mr', 'MR – Main Road / मुख्यमार्ग'),
        ('mbr', 'BMR – Beyond Main Road / मुख्यमार्ग से परे'),
    ], string='Road Type / सड़क प्रकार', compute='_compute_road_type', store=True, readonly=False)

    @api.depends('distance_from_road', 'survey_type')
    def _compute_road_type(self):
        for rec in self:
            dist = rec.distance_from_road
            if rec.survey_type == 'rural':
                rec.road_type = 'mr' if dist <= 50 else 'mbr'
            else: # urban
                rec.road_type = 'mr' if dist <= 20 else 'mbr'

    has_traded_land = fields.Boolean(string='Diverted (Traded) Land / विचलित (व्यापारित) भूमि', default=False)
    irrigation_type = fields.Selection([
        ('irrigated', 'Irrigated / सिंचित'),
        ('unirrigated', 'Unirrigated / असिंचित'),
    ], string='Irrigation Type / सिंचाई प्रकार', required=True, default='irrigated')

    acquired_area = fields.Float(
        string='Acquired Area (Hectares) / अर्जित क्षेत्रफल (हेक्टेयर)',
        digits=(10, 4), default=1.0
    )

    # ─── Dates & Interest Section ──────────────────────────────────────────────
    section4_date = fields.Date(string='Section 4 Publication Date / धारा 4 प्रकाशन तिथि')
    award_date = fields.Date(string='Award Date / अवार्ड तिथि', default=fields.Date.context_today)
    interest_rate_percent = fields.Float(string='Interest Rate (%)', default=12.0)

    # ─── Computed Land Rate ────────────────────────────────────────────────────
    effective_land_rate = fields.Float(
        string='Effective Land Rate (₹/Ha) / प्रभावी भूमि दर',
        digits=(16, 2), compute='_compute_land_award', store=True
    )
    land_award_amount = fields.Float(
        string='Land Award Amount (₹) / भूमि अवार्ड राशि',
        digits=(16, 2), compute='_compute_land_award', store=True
    )
    solatium_amount = fields.Float(
        string='Solatium 100% (₹) / सॉलेशियम 100%',
        digits=(16, 2), compute='_compute_land_award', store=True
    )
    land_total = fields.Float(
        string='Land Total (₹) / भूमि कुल',
        digits=(16, 2), compute='_compute_land_award', store=True
    )

    # ─── Computed Interest ─────────────────────────────────────────────────────
    interest_days = fields.Integer(string='Interest Days', compute='_compute_land_award', store=True)
    interest_amount = fields.Float(
        string='Interest 12% (₹/Sec 30(2)) / ब्याज 12%',
        digits=(16, 2), compute='_compute_land_award', store=True
    )

    @api.depends('base_rate', 'road_type', 'has_traded_land', 'irrigation_type', 'acquired_area', 'village_id',
                 'section4_date', 'award_date', 'interest_rate_percent',
                 'land_line_ids', 'land_line_ids.land_award_amount',
                 'land_line_ids.solatium_amount', 'land_line_ids.interest_amount',
                 'land_line_ids.line_total')
    def _compute_land_award(self):
        for rec in self:
            # Prefer per-khasra land lines if present (survey-driven)
            if rec.land_line_ids:
                land_award = sum(rec.land_line_ids.mapped('land_award_amount'))
                solatium = sum(rec.land_line_ids.mapped('solatium_amount'))
                interest = sum(rec.land_line_ids.mapped('interest_amount'))
                # Effective rate = weighted average if needed; show first line as preview
                rec.effective_land_rate = rec.land_line_ids[:1].effective_rate or 0.0
                rec.land_award_amount = land_award
                rec.solatium_amount = solatium
                rec.interest_days = rec.land_line_ids[:1].interest_days or 0
                rec.interest_amount = interest
                rec.land_total = land_award + solatium + interest
                continue

            # Fallback: legacy single-input computation
            base = rec.base_rate or 0.0
            if not base and rec.village_id:
                rate_master = rec.env['bhu.rate.master'].search([
                    ('village_id', '=', rec.village_id.id),
                    ('state', '=', 'active'),
                ], limit=1)
                if rate_master:
                    base = rate_master.main_road_rate_hectare if rec.road_type == 'mr' else rate_master.other_road_rate_hectare

            rate = base
            if rec.has_traded_land:
                rate = rate * 0.80
            if rec.irrigation_type == 'irrigated':
                rate = rate * 1.20
            else:
                rate = rate * 0.80

            land_award = rate * (rec.acquired_area or 0.0)
            solatium = land_award * 1.0
            interest, days = rec._calculate_interest_on_basic(land_award)

            rec.effective_land_rate = rate
            rec.land_award_amount = land_award
            rec.solatium_amount = solatium
            rec.interest_days = days
            rec.interest_amount = interest
            rec.land_total = land_award + solatium + interest

    # ─── Reference Rates (For testing) ─────────────────────────────────────────
    reference_land_rate_ids = fields.Many2many(
        'bhu.rate.master', string='Land Rates for Testing',
        compute='_compute_reference_rates'
    )
    reference_tree_rate_ids = fields.Many2many(
        'bhu.tree.rate.master', string='Tree Rates for Testing',
        compute='_compute_reference_rates'
    )

    @api.depends('village_id', 'tree_line_ids.tree_master_id')
    def _compute_reference_rates(self):
        for rec in self:
            # Land rates for current village
            if rec.village_id:
                rec.reference_land_rate_ids = self.env['bhu.rate.master'].search([
                    ('village_id', '=', rec.village_id.id)
                ])
            else:
                rec.reference_land_rate_ids = False

            # Tree rates for trees in current lines
            if rec.tree_line_ids:
                tree_master_ids = rec.tree_line_ids.mapped('tree_master_id').ids
                rec.reference_tree_rate_ids = self.env['bhu.tree.rate.master'].search([
                    ('tree_master_id', 'in', tree_master_ids)
                ])
            else:
                rec.reference_tree_rate_ids = False

    # ─── Land Lines (per-khasra survey-driven) ────────────────────────────────
    land_line_ids = fields.One2many(
        'bhu.award.simulator.land.line', 'simulator_id',
        string='Land Lines / भूमि लाइनें'
    )
    land_search = fields.Char(
        string='Search Khasra / खसरा खोजें',
        help='Type any part of a khasra number to filter the Land Component grid.',
    )
    land_count = fields.Integer(
        string='Khasra Count / खसरा संख्या',
        compute='_compute_land_lines_total', store=True
    )

    @api.depends('land_line_ids', 'land_line_ids.line_total',
                 'land_line_ids.land_award_amount', 'land_line_ids.solatium_amount',
                 'land_line_ids.interest_amount')
    def _compute_land_lines_total(self):
        for rec in self:
            rec.land_count = len(rec.land_line_ids)

    # ─── Tree Section ──────────────────────────────────────────────────────────
    tree_line_ids = fields.One2many(
        'bhu.award.simulator.tree.line', 'simulator_id',
        string='Trees / वृक्ष'
    )
    tree_basic_amount = fields.Float(
        string='Tree Basic (₹) / वृक्ष मूल',
        digits=(16, 2), compute='_compute_tree_total', store=True
    )
    tree_solatium_amount = fields.Float(
        string='Tree Solatium 100% (₹) / वृक्ष सॉलेशियम',
        digits=(16, 2), compute='_compute_tree_total', store=True
    )
    tree_interest_amount = fields.Float(
        string='Tree Interest 12% (₹) / वृक्ष ब्याज',
        digits=(16, 2), compute='_compute_tree_total', store=True
    )
    tree_total = fields.Float(
        string='Tree Total (₹) / वृक्ष कुल',
        digits=(16, 2), compute='_compute_tree_total', store=True
    )
    tree_count = fields.Integer(
        string='Tree Count / वृक्षों की संख्या',
        compute='_compute_tree_total', store=True
    )

    @api.depends('tree_line_ids', 'tree_line_ids.line_total', 'tree_line_ids.quantity', 'section4_date', 'award_date', 'interest_rate_percent')
    def _compute_tree_total(self):
        for rec in self:
            basic = sum(rec.tree_line_ids.mapped('line_total'))
            solatium = basic * 1.0
            interest, _days = rec._calculate_interest_on_basic(basic)
            
            rec.tree_basic_amount = basic
            rec.tree_solatium_amount = solatium
            rec.tree_interest_amount = interest
            rec.tree_total = basic + solatium + interest
            rec.tree_count = int(sum(rec.tree_line_ids.mapped('quantity')))

    # ─── Structure Section ─────────────────────────────────────────────────────
    structure_line_ids = fields.One2many(
        'bhu.award.structure.details', 'simulator_id',
        string='Structures / संरचनाएं'
    )
    structure_basic_amount = fields.Float(
        string='Structure Basic (₹) / संरचना मूल',
        digits=(16, 2), compute='_compute_structure_total', store=True
    )
    structure_solatium_amount = fields.Float(
        string='Structure Solatium 100% (₹) / संरचना सॉलेशियम',
        digits=(16, 2), compute='_compute_structure_total', store=True
    )
    structure_interest_amount = fields.Float(
        string='Structure Interest 12% (₹) / संरचना ब्याज',
        digits=(16, 2), compute='_compute_structure_total', store=True
    )
    structure_total = fields.Float(
        string='Structure Total (₹) / संरचना कुल',
        digits=(16, 2), compute='_compute_structure_total', store=True
    )
    structure_count = fields.Integer(
        string='Structure Count / संरचना गिनती',
        compute='_compute_structure_total', store=True
    )

    @api.depends('structure_line_ids', 'structure_line_ids.line_total', 'section4_date', 'award_date', 'interest_rate_percent')
    def _compute_structure_total(self):
        for rec in self:
            basic = sum(rec.structure_line_ids.mapped('line_total'))
            solatium = basic * 1.0
            interest, _days = rec._calculate_interest_on_basic(basic)
            
            rec.structure_basic_amount = basic
            rec.structure_solatium_amount = solatium
            rec.structure_interest_amount = interest
            rec.structure_total = basic + solatium + interest
            rec.structure_count = len(rec.structure_line_ids)

    # ─── Grand Total ───────────────────────────────────────────────────────────
    grand_total = fields.Float(
        string='Grand Total Award (₹) / कुल अवार्ड',
        digits=(16, 2), compute='_compute_grand_total', store=True
    )

    @api.depends('land_total', 'tree_total', 'structure_total')
    def _compute_grand_total(self):
        for rec in self:
            rec.grand_total = rec.land_total + rec.tree_total + rec.structure_total

    # ─── Auto-fill base rate from village ─────────────────────────────────────
    @api.onchange('village_id', 'road_type', 'distance_from_road')
    def _onchange_village_id(self):
        if self.village_id:
            if self.village_id.district_id:
                self.district_id = self.village_id.district_id

            rate_master = self.env['bhu.rate.master'].search([
                ('village_id', '=', self.village_id.id),
                ('state', '=', 'active'),
            ], limit=1)
            if rate_master:
                if self.road_type == 'mr':
                    self.base_rate = rate_master.main_road_rate_hectare
                else:
                    self.base_rate = rate_master.other_road_rate_hectare

    @api.onchange('project_id')
    def _onchange_project_id(self):
        domain = {'village_id': []}
        for rec in self:
            if rec.project_id and rec.village_id and rec.village_id not in rec.project_id.village_ids:
                rec.village_id = False
            rec._auto_populate_tree_lines_from_surveys()
            rec._auto_populate_land_lines_from_surveys()
            if rec.project_id:
                domain = {'village_id': [('id', 'in', rec.project_id.village_ids.ids)]}
        return {'domain': domain}

    @api.onchange('project_id', 'village_id')
    def _onchange_project_village_tree_lines(self):
        self._auto_populate_tree_lines_from_surveys()
        self._auto_populate_land_lines_from_surveys()

    def _auto_populate_land_lines_from_surveys(self):
        """Populate per-khasra land lines from surveys for selected project/village."""
        for rec in self:
            if not rec.village_id or not rec.project_id:
                rec.land_line_ids = [(5, 0, 0)]
                continue
            surveys = rec.env['bhu.survey'].search([
                ('project_id', '=', rec.project_id.id),
                ('village_id', '=', rec.village_id.id),
                ('khasra_number', '!=', False),
            ])
            commands = [(5, 0, 0)]
            for survey in surveys:
                commands.append((0, 0, {
                    'survey_id': survey.id,
                }))
            rec.land_line_ids = commands

    def _auto_populate_tree_lines_from_surveys(self):
        """Populate simulator tree lines from survey tree data for selected project/village."""
        for rec in self:
            if not rec.village_id or not rec.project_id:
                rec.tree_line_ids = [(5, 0, 0)]
                continue
            surveys = rec.env['bhu.survey'].search([
                ('project_id', '=', rec.project_id.id),
                ('village_id', '=', rec.village_id.id),
                ('khasra_number', '!=', False),
            ])
            commands = [(5, 0, 0)]
            for survey in surveys:
                for tline in (survey.tree_line_ids or []):
                    condition_value = 'sound'
                    if 'condition' in tline._fields:
                        condition_value = tline.condition or 'sound'
                    commands.append((0, 0, {
                        'survey_id': survey.id,
                        'tree_master_id': tline.tree_master_id.id if tline.tree_master_id else False,
                        'development_stage': tline.development_stage or 'fully_developed',
                        'girth_cm': tline.girth_cm or 0.0,
                        'condition': condition_value,
                        'quantity': tline.quantity or 1,
                    }))
            rec.tree_line_ids = commands

    def format_indian_number(self, value, decimals=2):
        if value is None:
            value = 0.0
        if decimals == 2:
            return f"{value:,.2f}"
        elif decimals == 4:
            return f"{value:,.4f}"
        else:
            return f"{value:,.{decimals}f}"

    def get_award_header_constants(self):
        """Shared award header labels used by Excel/PDF outputs."""
        self.ensure_one()
        return get_award_header_constants()

    def _get_village_surveys_for_simulator(self):
        """Return all village surveys with khasra for simulator reports."""
        self.ensure_one()
        if not self.village_id:
            return self.env['bhu.survey']
        domain = [
            ('village_id', '=', self.village_id.id),
            ('khasra_number', '!=', False),
        ]
        if self.project_id:
            domain.append(('project_id', '=', self.project_id.id))
        return self.env['bhu.survey'].search(domain)

    def _get_section4_approval_date(self):
        """Return Section 4 date for simulator interest start."""
        self.ensure_one()
        # Simulator should prefer the date entered in UI.
        if self.section4_date:
            return fields.Date.to_date(self.section4_date)

        # Fallback to Section 4 records only if UI date is not entered.
        if self.village_id:
            domain = [('village_id', '=', self.village_id.id)]
            if self.project_id:
                domain.append(('project_id', '=', self.project_id.id))
            section4_records = self.env['bhu.section4.notification'].search(
                domain, order='approved_date desc, signed_date desc, id desc', limit=10
            )
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

    def _get_award_calculation_date(self):
        """Return award end date for simulator interest."""
        self.ensure_one()
        # Simulator should prefer UI award date.
        if self.award_date:
            return fields.Date.to_date(self.award_date)

        # Fallback only when UI award date is empty.
        if self.create_date:
            return fields.Datetime.to_datetime(self.create_date).date()
        return fields.Date.context_today(self)

    def _calculate_interest_on_basic(self, basic_value):
        """Calculate interest as 12% p.a. on basic value."""
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

    def get_interest_period_note(self):
        """Text for interest date range in PDF/Excel headers."""
        self.ensure_one()
        start_date = self._get_section4_approval_date()
        end_date = self._get_award_calculation_date()
        if start_date and end_date:
            if end_date < start_date:
                start_date, end_date = end_date, start_date
            return f"{start_date.strftime('%d/%m/%Y')} से {end_date.strftime('%d/%m/%Y')} तक"
        return "धारा 4 स्वीकृति दिनांक से अवार्ड दिनांक तक"

    def get_land_compensation_data(self):
        self.ensure_one()
        # In Simulator, we want to see all surveys in the selected village.
        surveys = self._get_village_surveys_for_simulator()
            
        if not surveys:
            # Fallback to manual simulator data if no surveys found
            return [{
                'landowner_name': 'Manual Simulation / मैनुअल सिमुलेशन',
                'father_name': '',
                'address': '',
                'khasra': 'N/A',
                'original_area': 0.0,
                'acquired_area': self.acquired_area,
                'lagan': 'N/A',
                'is_within_distance': False,
                'distance_from_main_road': 0.0,
                'unirrigated': self.irrigation_type == 'unirrigated',
                'irrigated': self.irrigation_type == 'irrigated',
                'is_diverted': False,
                'guide_line_rate': self.effective_land_rate,
                'basic_value': self.land_award_amount, # basic is same as factored/2?
                'market_value': self.land_award_amount * 2.0,
                'solatium': self.solatium_amount,
                'interest': self.interest_amount,
                'total_compensation': self.land_total,
                'paid_compensation': self.land_total,
                'remark': 'Simulation Only',
            }]
            
        rate_master = False
        if self.village_id:
            rate_master = self.env['bhu.rate.master'].search([('village_id', '=', self.village_id.id), ('state', '=', 'active')], limit=1)

        compensation_data = {}
        for survey in surveys:
            khasra = survey.khasra_number or ''
            acquired_area = survey.acquired_area or 0.0
            irrigation_type = survey.irrigation_type or 'unirrigated'
            is_irrigated = irrigation_type == 'irrigated'
            
            # Use has_traded_land as the indicator for diverted land as requested
            is_diverted = survey.has_traded_land == 'yes'
            
            # Using is_within_distance_for_award (True=Main Road, False=Other Road/BMR)
            road_type = 'mr' if survey.is_within_distance_for_award else 'mbr'
                
            guide_line_rate = getattr(self, 'base_rate', 0.0)
            if rate_master and not guide_line_rate:
                guide_line_rate = rate_master.main_road_rate_hectare if road_type == 'mr' else rate_master.other_road_rate_hectare
                 
            rate = guide_line_rate
            if is_diverted: rate = rate * 0.80
            if is_irrigated: rate = rate * 1.20
            else: rate = rate * 0.80
            
            market_value_basic = rate * acquired_area
            market_value_factored = market_value_basic * 2.0
            solatium = market_value_factored * 1.0 # 100%
            
            interest, _days = self._calculate_interest_on_basic(market_value_basic)
                    
            total_compensation = market_value_factored + solatium + interest

            landowners = survey.landowner_ids if survey.landowner_ids else []
            if not landowners:
                key = (False, khasra)
                if key not in compensation_data:
                    compensation_data[key] = {
                        'landowner': None,
                        'landowner_name': '',
                        'father_name': '',
                        'address': '',
                        'khasra': khasra,
                        'original_area': survey.total_area or 0.0,
                        'acquired_area': 0.0,
                        'lagan': getattr(survey, 'lagan', khasra) or khasra,
                        'is_within_distance': survey.is_within_distance_for_award,
                        'distance_from_main_road': survey.distance_from_main_road or 0.0,
                        'unirrigated': not is_irrigated,
                        'irrigated': is_irrigated,
                        'is_diverted': is_diverted,
                        'guide_line_rate': guide_line_rate,
                        'basic_value': 0.0,
                        'market_value': 0.0,
                        'solatium': 0.0,
                        'interest': 0.0,
                        'total_compensation': 0.0,
                        'paid_compensation': 0.0,
                        'remark': '',
                    }
                compensation_data[key]['acquired_area'] += acquired_area
                compensation_data[key]['basic_value'] += market_value_basic
                compensation_data[key]['market_value'] += market_value_factored
                compensation_data[key]['solatium'] += solatium
                compensation_data[key]['interest'] += interest
                compensation_data[key]['total_compensation'] += total_compensation
                # Logic for Column 18: Minimum 5/5/10 lakh check (Placeholder or logic)
                compensation_data[key]['paid_compensation'] = max(compensation_data[key]['total_compensation'], 0.0)
            else:
                for landowner in landowners:
                    key = (landowner.id, khasra)
                    if key not in compensation_data:
                        compensation_data[key] = {
                            'landowner': landowner,
                            'landowner_name': landowner.name or '',
                            'father_name': landowner.father_name or landowner.spouse_name or '',
                            'address': landowner.owner_address or '',
                            'khasra': khasra,
                            'original_area': survey.total_area or 0.0,
                            'acquired_area': 0.0,
                            'lagan': getattr(survey, 'lagan', khasra) or khasra,
                            'is_within_distance': survey.is_within_distance_for_award,
                            'distance_from_main_road': survey.distance_from_main_road or 0.0,
                            'unirrigated': not is_irrigated,
                            'irrigated': is_irrigated,
                            'is_diverted': is_diverted,
                            'guide_line_rate': guide_line_rate,
                            'basic_value': 0.0,
                            'market_value': 0.0,
                            'solatium': 0.0,
                            'interest': 0.0,
                            'total_compensation': 0.0,
                            'paid_compensation': 0.0,
                            'remark': '',
                        }
                    share = 1.0 / len(landowners)
                    compensation_data[key]['acquired_area'] += acquired_area * share
                    compensation_data[key]['basic_value'] += market_value_basic * share
                    compensation_data[key]['market_value'] += market_value_factored * share
                    compensation_data[key]['solatium'] += solatium * share
                    compensation_data[key]['interest'] += interest * share
                    compensation_data[key]['total_compensation'] += total_compensation * share
                    compensation_data[key]['paid_compensation'] = max(compensation_data[key]['total_compensation'], 0.0)

        result = list(compensation_data.values())
        result.sort(key=lambda x: (x['landowner_name'] or '', x['khasra'] or ''))
        return result

    def get_land_compensation_grouped_data(self):
        """Group land rows by owner so multiple khasras appear together."""
        self.ensure_one()
        land_data = self.get_land_compensation_data()
        grouped = {}
        ordered_keys = []
        numeric_totals = (
            'original_area', 'acquired_area', 'basic_value', 'market_value',
            'solatium', 'interest', 'total_compensation', 'paid_compensation',
        )
        for row in land_data:
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
            group.pop('khasra_seen', None)
            result.append(group)
        return result

    def get_tree_compensation_data(self):
        self.ensure_one()
        surveys = self._get_village_surveys_for_simulator()
        manual_tree_data = []
        for t_line in self.tree_line_ids:
            manual_tree_data.append({
                'landowner': None, 'landowner_name': 'Manual / मैनुअल', 'father_name': '',
                'khasra': 'N/A', 'total_khasra': 'N/A', 'total_area': 0.0,
                'tree_type': t_line.tree_master_id.name if t_line.tree_master_id else 'Other',
                'tree_type_code': t_line.tree_type or 'other',
                'tree_count': t_line.quantity or 0,
                'girth_cm': t_line.girth_cm or 0.0,
                'rate': t_line.unit_rate or 0.0,
                'value': t_line.line_total or 0.0,
                'determined_value': t_line.line_total or 0.0,
                'solatium': t_line.line_total or 0.0,
                'interest': 0.0,
                'total': (t_line.line_total or 0.0) * 2.0,
                'remark': 'Manual Simulation',
            })
        if not surveys:
            # Fallback to manual simulator tree data
            if not manual_tree_data:
                return []
            return manual_tree_data
            
        tree_data = {}
        for survey in surveys:
            khasra = survey.khasra_number or ''
            landowners = survey.landowner_ids if survey.landowner_ids else []
            tree_lines = survey.tree_line_ids if hasattr(survey, 'tree_line_ids') else []
            
            if not tree_lines:
                continue
                
            if not landowners:
                for tree_line in tree_lines:
                    tree_type_name = tree_line.tree_master_id.name if tree_line.tree_master_id else 'other'
                    key = (False, khasra, tree_type_name)
                    if key not in tree_data:
                        tree_data[key] = {
                            'landowner': None, 'landowner_name': '', 'father_name': '',
                            'khasra': khasra, 'total_khasra': '', 'total_area': survey.total_area or 0.0,
                            'tree_type': tree_type_name, 'tree_type_code': tree_line.tree_type or 'other',
                            'tree_count': 0, 'girth_cm': 0.0, 'rate': 0.0, 'value': 0.0,
                            'determined_value': 0.0, 'solatium': 0.0, 'interest': 0.0, 'total': 0.0, 'remark': '',
                        }
                    rate_per_tree = tree_line.get_applicable_rate()
                    tree_data[key]['tree_count'] += tree_line.quantity or 0
                    tree_data[key]['girth_cm'] = tree_line.girth_cm or 0.0
                    tree_data[key]['rate'] = rate_per_tree
                    tree_data[key]['value'] += (tree_line.quantity or 0) * rate_per_tree
            else:
                for landowner in landowners:
                    for tree_line in tree_lines:
                        tree_type_name = tree_line.tree_master_id.name if tree_line.tree_master_id else 'other'
                        key = (landowner.id, khasra, tree_type_name)
                        if key not in tree_data:
                            tree_data[key] = {
                                'landowner': landowner, 'landowner_name': landowner.name or '', 
                                'father_name': landowner.father_name or landowner.spouse_name or '',
                                'khasra': khasra, 'total_khasra': '', 'total_area': survey.total_area or 0.0,
                                'tree_type': tree_type_name, 'tree_type_code': tree_line.tree_type or 'other',
                                'tree_count': 0, 'girth_cm': 0.0, 'rate': 0.0, 'value': 0.0,
                                'determined_value': 0.0, 'solatium': 0.0, 'interest': 0.0, 'total': 0.0, 'remark': '',
                            }
                        rate_per_tree = tree_line.get_applicable_rate()
                        share = 1.0 / len(landowners)
                        tree_data[key]['tree_count'] += (tree_line.quantity or 0) * share
                        tree_data[key]['girth_cm'] = tree_line.girth_cm or 0.0
                        tree_data[key]['rate'] = rate_per_tree
                        tree_data[key]['value'] += (tree_line.quantity or 0) * rate_per_tree * share
                        
        for key, data in tree_data.items():
            value = data['value']
            data['determined_value'] = value
            data['solatium'] = value * 1.0  # 100%
            interest = 0.0
            if self.section4_date and self.award_date:
                days = (self.award_date - self.section4_date).days
                if days > 0:
                    interest = value * (self.interest_rate_percent / 100.0) * (days / 365.25)
            data['interest'] = interest
            data['total'] = value + data['solatium'] + interest
            
        result = list(tree_data.values())
        result.sort(key=lambda x: (x['landowner_name'] or '', x['khasra'] or ''))
        return result or manual_tree_data

    def get_structure_compensation_data(self):
        """Get structure compensation data only from manual simulator structure lines."""
        self.ensure_one()
        structure_data = []
        for s_line in self.structure_line_ids:
            survey = s_line.survey_id
            total_value = s_line.line_total or 0.0
            base_row = {
                'total_khasra': survey.khasra_number if survey else (s_line.khasra_number or 'N/A'),
                'total_area': survey.total_area if survey else 0.0,
                'asset_khasra': survey.khasra_number if survey else (s_line.khasra_number or 'N/A'),
                'asset_land_area': survey.acquired_area if survey else 0.0,
                'asset_type': s_line.get_structure_type_label(),
                'asset_code': 4,
                'asset_dimension': (s_line.asset_count or 0.0) if s_line.structure_type == 'well' else (s_line.area_sqm or 0.0),
                'remark': s_line.description or 'Manual Structure Entry',
            }
            if survey and survey.landowner_ids:
                owners = survey.landowner_ids
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

    def action_calculate(self):
        """Repopulate survey-driven land/tree lines and recompute totals."""
        for rec in self:
            rec._auto_populate_land_lines_from_surveys()
            rec._auto_populate_tree_lines_from_surveys()
        self.env.add_to_compute(self._fields['effective_land_rate'], self)
        self.env.add_to_compute(self._fields['land_award_amount'], self)
        self.env.add_to_compute(self._fields['solatium_amount'], self)
        self.env.add_to_compute(self._fields['interest_amount'], self)
        self.env.add_to_compute(self._fields['land_total'], self)
        self.env.add_to_compute(self._fields['tree_total'], self)
        self.env.add_to_compute(self._fields['structure_total'], self)
        self.env.add_to_compute(self._fields['grand_total'], self)
        return True

    def action_download(self):
        """Unified download method that opens the format selection wizard"""
        self.ensure_one()
        return {
            'name': _('Download Award Summary / अवार्ड सारांश डाउनलोड करें'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'bhu.award.download.wizard',
            'target': 'new',
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
                'default_report_xml_id': 'bhuarjan.action_report_award_simulator',
                'default_filename': f"Award_Simulator_{self.village_id.name or 'Manual'}_{fields.Date.today()}"
            }
        }

    def action_download_pdf(self):
        """Open the download wizard for PDF"""
        self.ensure_one()
        return {
            'name': _('Download Award Summary (PDF)'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'bhu.award.download.wizard',
            'target': 'new',
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
                'default_report_xml_id': 'bhuarjan.action_report_award_simulator',
                'default_format': 'pdf',
                'default_filename': f"Award_Simulator_{self.village_id.name or 'Manual'}_{fields.Date.today()}"
            }
        }

    def action_download_word(self):
        """Open the download wizard for Word"""
        self.ensure_one()
        raise ValidationError(_('Word download is disabled for Award Simulator. Please use PDF or Excel.'))

    def action_download_excel(self):
        """Generate and download Excel report in long-table landscape format"""
        self.ensure_one()
        import io
        import base64
        try:
            import xlsxwriter
        except ImportError:
            raise ValidationError(_("Python library 'xlsxwriter' is not installed."))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        award_headers = self.get_award_header_constants()
        land_sheet = workbook.add_worksheet('Land')
        asset_sheet = workbook.add_worksheet('Assets')
        tree_sheet = workbook.add_worksheet('Trees')

        # Formats
        title_fmt = workbook.add_format({
            'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter',
            'border': 1
        })
        subtitle_fmt = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter',
            'border': 1
        })
        header_group_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#d9e1f2', 'align': 'center', 'valign': 'vcenter',
            'border': 1, 'text_wrap': True
        })
        header_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#f2f2f2', 'align': 'center', 'valign': 'vcenter',
            'border': 1, 'text_wrap': True
        })
        cell_fmt = workbook.add_format({'border': 1, 'valign': 'top'})
        cell_center_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
        yes_fmt = workbook.add_format({
            'border': 1, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#2e7d32', 'color': 'white', 'bold': True
        })
        no_fmt = workbook.add_format({
            'border': 1, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#c62828', 'color': 'white', 'bold': True
        })
        number_fmt = workbook.add_format({'border': 1, 'align': 'right', 'num_format': '#,##0.000'})
        money_fmt = workbook.add_format({'border': 1, 'align': 'right', 'num_format': '#,##0'})
        total_label_fmt = workbook.add_format({
            'bold': True, 'border': 1, 'bg_color': '#e2e8f0', 'align': 'center', 'valign': 'vcenter'
        })
        total_money_fmt = workbook.add_format({
            'bold': True, 'border': 1, 'bg_color': '#e2e8f0', 'align': 'right', 'num_format': '#,##0'
        })
        blank_msg_fmt = workbook.add_format({
            'italic': True, 'border': 1, 'align': 'center', 'valign': 'vcenter'
        })

        def _setup_sheet(sheet, col_widths, repeat_to_row):
            sheet.set_landscape()
            sheet.set_paper(9)  # A4
            sheet.fit_to_pages(1, 0)
            sheet.repeat_rows(0, repeat_to_row)
            for idx, width in enumerate(col_widths):
                sheet.set_column(idx, idx, width)

        def _yes_no_format(flag):
            return yes_fmt if flag else no_fmt

        # Land tab
        land_col_widths = [4, 24, 10, 10, 10, 10, 8, 8, 8, 13, 10, 10, 11, 11, 10, 10, 11, 8, 11, 10]
        _setup_sheet(land_sheet, land_col_widths, 8)
        row = 0
        land_sheet.merge_range(row, 0, row, 19, 'AWARD SIMULATOR / अवार्ड सिमुलेटर', title_fmt)
        row += 1
        subtitle = (
            f"Village / ग्राम: {self.village_id.name or '-'} | "
            f"Project / परियोजना: {self.project_id.name or '-'} | "
            f"Date / तिथि: {fields.Date.today()}"
        )
        land_sheet.merge_range(row, 0, row, 19, subtitle, subtitle_fmt)
        row += 2

        # LAND TABLE
        land_sheet.merge_range(
            row, 0, row, 19,
            f"{award_headers['sections']['land_sheet_label']} - {award_headers['sections']['land_title']}",
            header_group_fmt
        )
        row += 1

        sim_land_headers = award_headers['excel']['sim_land_headers']
        land_sheet.merge_range(row, 0, row + 1, 0, sim_land_headers['rowspan_headers'][0], header_fmt)
        land_sheet.merge_range(row, 1, row + 1, 1, sim_land_headers['rowspan_headers'][1], header_fmt)
        land_sheet.merge_range(row, 2, row, 3, sim_land_headers['group_held'], header_group_fmt)
        land_sheet.merge_range(row, 4, row, 5, sim_land_headers['group_acquired'], header_group_fmt)
        land_sheet.merge_range(row, 6, row, 9, sim_land_headers['group_main_road'], header_group_fmt)
        for col_offset, label in enumerate(sim_land_headers['tail_headers'], start=10):
            land_sheet.merge_range(row, col_offset, row + 1, col_offset, label, header_fmt)
        row += 1
        for col_offset, label in enumerate(sim_land_headers['sub_headers'], start=2):
            land_sheet.write(row, col_offset, label, header_fmt)
        land_sheet.set_row(row - 1, 36)
        land_sheet.set_row(row, 36)
        row += 1

        land_groups = self.get_land_compensation_grouped_data()
        if not land_groups:
            land_sheet.merge_range(row, 0, row, 19, 'No land data available / भूमि डेटा उपलब्ध नहीं है (Blank)', blank_msg_fmt)
            row += 1
        else:
            total_basic = total_market = total_solatium = 0.0
            total_interest = total_comp = total_paid = total_acq = 0.0
            for i, group in enumerate(land_groups, 1):
                lines = group.get('lines', [])
                details = group.get('landowner_name', '')
                father = group.get('father_name')
                if father:
                    details = f"{details}\nपिता/पति: {father}"
                for idx, land in enumerate(lines):
                    land_sheet.write(row, 0, i if idx == 0 else '', cell_center_fmt)
                    land_sheet.write(row, 1, details if idx == 0 else '', cell_fmt)
                    land_sheet.write(row, 2, land.get('khasra', ''), cell_center_fmt)
                    land_sheet.write_number(row, 3, float(land.get('original_area', 0.0) or 0.0), number_fmt)
                    land_sheet.write(row, 4, land.get('khasra', ''), cell_center_fmt)
                    land_sheet.write_number(row, 5, float(land.get('acquired_area', 0.0) or 0.0), number_fmt)
                    is_within_distance = bool(land.get('is_within_distance'))
                    is_irrigated = bool(land.get('irrigated'))
                    is_unirrigated = bool(land.get('unirrigated'))
                    is_diverted = bool(land.get('is_diverted'))
                    distance_value = land.get('distance_from_main_road') or 0.0
                    if distance_value:
                        land_sheet.write(row, 6, f"{distance_value:.2f} m",
                                          _yes_no_format(is_within_distance))
                    else:
                        land_sheet.write(row, 6, 'हाँ' if is_within_distance else 'नहीं',
                                          _yes_no_format(is_within_distance))
                    land_sheet.write(row, 7, 'हाँ' if is_irrigated else 'नहीं', _yes_no_format(is_irrigated))
                    land_sheet.write(row, 8, 'हाँ' if is_unirrigated else 'नहीं', _yes_no_format(is_unirrigated))
                    land_sheet.write(row, 9, 'हाँ' if is_diverted else 'नहीं', _yes_no_format(is_diverted))
                    land_sheet.write(row, 10, '-', cell_center_fmt)
                    land_sheet.write_number(row, 11, float(land.get('guide_line_rate', 0.0) or 0.0), money_fmt)
                    land_sheet.write_number(row, 12, float(land.get('basic_value', 0.0) or 0.0), money_fmt)
                    land_sheet.write_number(row, 13, float(land.get('market_value', 0.0) or 0.0), money_fmt)
                    land_sheet.write_number(row, 14, float(land.get('solatium', 0.0) or 0.0), money_fmt)
                    land_sheet.write_number(row, 15, float(land.get('interest', 0.0) or 0.0), money_fmt)
                    land_sheet.write_number(row, 16, float(land.get('total_compensation', 0.0) or 0.0), money_fmt)
                    land_sheet.write_number(row, 17, float(land.get('rehab_policy_amount', 0.0) or 0.0), money_fmt)
                    land_sheet.write_number(row, 18, float(land.get('paid_compensation', 0.0) or 0.0), money_fmt)
                    land_sheet.write(row, 19, land.get('remark', ''), cell_fmt)
                    row += 1

                land_sheet.merge_range(row, 0, row, 1, 'कुल', total_label_fmt)
                land_sheet.write_number(row, 2, float(group.get('khasra_count', 0) or 0), total_money_fmt)
                land_sheet.write_number(row, 3, float(group.get('original_area', 0.0) or 0.0), total_money_fmt)
                land_sheet.write_number(row, 4, float(group.get('khasra_count', 0) or 0), total_money_fmt)
                land_sheet.write_number(row, 5, float(group.get('acquired_area', 0.0) or 0.0), total_money_fmt)
                land_sheet.write_blank(row, 6, None, total_label_fmt)
                land_sheet.write_blank(row, 7, None, total_label_fmt)
                land_sheet.write_blank(row, 8, None, total_label_fmt)
                land_sheet.write_blank(row, 9, None, total_label_fmt)
                land_sheet.write_blank(row, 10, None, total_label_fmt)
                land_sheet.write_blank(row, 11, None, total_label_fmt)
                land_sheet.write_number(row, 12, float(group.get('basic_value', 0.0) or 0.0), total_money_fmt)
                land_sheet.write_number(row, 13, float(group.get('market_value', 0.0) or 0.0), total_money_fmt)
                land_sheet.write_number(row, 14, float(group.get('solatium', 0.0) or 0.0), total_money_fmt)
                land_sheet.write_number(row, 15, float(group.get('interest', 0.0) or 0.0), total_money_fmt)
                land_sheet.write_number(row, 16, float(group.get('total_compensation', 0.0) or 0.0), total_money_fmt)
                land_sheet.write_number(row, 17, float(group.get('rehab_policy_amount', 0.0) or 0.0), total_money_fmt)
                land_sheet.write_number(row, 18, float(group.get('paid_compensation', 0.0) or 0.0), total_money_fmt)
                land_sheet.write_blank(row, 19, None, total_label_fmt)
                total_acq += float(group.get('acquired_area', 0.0) or 0.0)
                total_basic += float(group.get('basic_value', 0.0) or 0.0)
                total_market += float(group.get('market_value', 0.0) or 0.0)
                total_solatium += float(group.get('solatium', 0.0) or 0.0)
                total_interest += float(group.get('interest', 0.0) or 0.0)
                total_comp += float(group.get('total_compensation', 0.0) or 0.0)
                total_paid += float(group.get('paid_compensation', 0.0) or 0.0)
                row += 1

            land_sheet.merge_range(row, 0, row, 3, 'MAHAYOG (TOTAL) / महायोग', total_label_fmt)
            land_sheet.write_blank(row, 4, None, total_label_fmt)
            land_sheet.write_number(row, 5, total_acq, total_money_fmt)
            land_sheet.write_blank(row, 6, None, total_label_fmt)
            land_sheet.write_blank(row, 7, None, total_label_fmt)
            land_sheet.write_blank(row, 8, None, total_label_fmt)
            land_sheet.write_blank(row, 9, None, total_label_fmt)
            land_sheet.write_blank(row, 10, None, total_label_fmt)
            land_sheet.write_blank(row, 11, None, total_label_fmt)
            land_sheet.write_number(row, 12, total_basic, total_money_fmt)
            land_sheet.write_number(row, 13, total_market, total_money_fmt)
            land_sheet.write_number(row, 14, total_solatium, total_money_fmt)
            land_sheet.write_number(row, 15, total_interest, total_money_fmt)
            land_sheet.write_number(row, 16, total_comp, total_money_fmt)
            land_sheet.write_number(row, 17, sum(float(g.get('rehab_policy_amount', 0.0) or 0.0) for g in land_groups), total_money_fmt)
            land_sheet.write_number(row, 18, total_paid, total_money_fmt)
            land_sheet.write_blank(row, 19, None, total_label_fmt)

        # ASSET TAB
        asset_col_widths = [4, 24, 10, 10, 10, 10, 22, 10, 12, 12, 12, 12, 12]
        _setup_sheet(asset_sheet, asset_col_widths, 4)
        asset_row = 0
        asset_sheet.merge_range(asset_row, 0, asset_row, 12, 'AWARD SIMULATOR / अवार्ड सिमुलेटर', title_fmt)
        asset_row += 1
        asset_sheet.merge_range(asset_row, 0, asset_row, 12, subtitle, subtitle_fmt)
        asset_row += 2
        asset_sheet.merge_range(
            asset_row, 0, asset_row, 12,
            f"{award_headers['sections']['asset_sheet_label']} - {award_headers['sections']['asset_title']}",
            header_group_fmt
        )
        asset_row += 1
        asset_headers = award_headers['excel']['sim_asset_headers']
        for col, title in enumerate(asset_headers):
            asset_sheet.write(asset_row, col, title, header_fmt)
        asset_row += 1
        asset_groups = self.get_structure_compensation_grouped_data()
        if not asset_groups:
            asset_sheet.merge_range(asset_row, 0, asset_row, 12, 'No asset/structure data available / परिसम्पत्ति डेटा उपलब्ध नहीं है (Blank)', blank_msg_fmt)
            asset_row += 1
        else:
            for i, group in enumerate(asset_groups, 1):
                lines = group.get('lines', [])
                details = group.get('landowner_name', '')
                father = group.get('father_name')
                if father:
                    details = f"{details}\nपिता/पति: {father}"
                for idx, asset in enumerate(lines):
                    asset_sheet.write(asset_row, 0, i if idx == 0 else '', cell_center_fmt)
                    asset_sheet.write(asset_row, 1, details if idx == 0 else '', cell_fmt)
                    asset_sheet.write(asset_row, 2, asset.get('total_khasra', ''), cell_center_fmt)
                    asset_sheet.write_number(asset_row, 3, float(asset.get('total_area', 0.0) or 0.0), number_fmt)
                    asset_sheet.write(asset_row, 4, asset.get('asset_khasra', ''), cell_center_fmt)
                    asset_sheet.write_number(asset_row, 5, float(asset.get('asset_land_area', 0.0) or 0.0), number_fmt)
                    asset_sheet.write(asset_row, 6, f"({asset.get('asset_code', '4')}) {asset.get('asset_type', '')}", cell_fmt)
                    asset_sheet.write_number(asset_row, 7, float(asset.get('asset_dimension', 0.0) or 0.0), number_fmt)
                    asset_sheet.write_number(asset_row, 8, float(asset.get('market_value', 0.0) or 0.0), money_fmt)
                    asset_sheet.write_number(asset_row, 9, float(asset.get('solatium', 0.0) or 0.0), money_fmt)
                    asset_sheet.write_number(asset_row, 10, float(asset.get('interest', 0.0) or 0.0), money_fmt)
                    asset_sheet.write_number(asset_row, 11, float(asset.get('total', 0.0) or 0.0), money_fmt)
                    asset_sheet.write(asset_row, 12, asset.get('remark', ''), cell_fmt)
                    asset_row += 1

                asset_sheet.merge_range(asset_row, 0, asset_row, 1, 'कुल', total_label_fmt)
                asset_sheet.write_number(asset_row, 2, float(group.get('khasra_count', 0) or 0), total_money_fmt)
                asset_sheet.write_number(asset_row, 3, float(group.get('total_area', 0.0) or 0.0), total_money_fmt)
                asset_sheet.write_number(asset_row, 4, float(group.get('khasra_count', 0) or 0), total_money_fmt)
                asset_sheet.write_number(asset_row, 5, float(group.get('asset_land_area', 0.0) or 0.0), total_money_fmt)
                asset_sheet.write_blank(asset_row, 6, None, total_label_fmt)
                asset_sheet.write_number(asset_row, 7, float(group.get('asset_dimension', 0.0) or 0.0), total_money_fmt)
                asset_sheet.write_number(asset_row, 8, float(group.get('market_value', 0.0) or 0.0), total_money_fmt)
                asset_sheet.write_number(asset_row, 9, float(group.get('solatium', 0.0) or 0.0), total_money_fmt)
                asset_sheet.write_number(asset_row, 10, float(group.get('interest', 0.0) or 0.0), total_money_fmt)
                asset_sheet.write_number(asset_row, 11, float(group.get('total', 0.0) or 0.0), total_money_fmt)
                asset_sheet.write_blank(asset_row, 12, None, total_label_fmt)
                asset_row += 1

        # TREE TAB
        tree_col_widths = [4, 24, 10, 10, 10, 20, 10, 10, 10, 12, 12, 12, 12, 12]
        _setup_sheet(tree_sheet, tree_col_widths, 4)
        tree_row = 0
        tree_sheet.merge_range(tree_row, 0, tree_row, 13, 'AWARD SIMULATOR / अवार्ड सिमुलेटर', title_fmt)
        tree_row += 1
        tree_sheet.merge_range(tree_row, 0, tree_row, 13, subtitle, subtitle_fmt)
        tree_row += 2
        tree_sheet.merge_range(
            tree_row, 0, tree_row, 13,
            f"{award_headers['sections']['tree_sheet_label']} - {award_headers['sections']['tree_title']}",
            header_group_fmt
        )
        tree_row += 1
        tree_headers = award_headers['excel']['sim_tree_headers']
        for col, title in enumerate(tree_headers):
            tree_sheet.write(tree_row, col, title, header_fmt)
        tree_row += 1
        tree_groups = self.get_tree_compensation_grouped_data()
        if not tree_groups:
            tree_sheet.merge_range(tree_row, 0, tree_row, 13, 'No tree data available / वृक्ष डेटा उपलब्ध नहीं है (Blank)', blank_msg_fmt)
            tree_row += 1
        else:
            for i, group in enumerate(tree_groups, 1):
                lines = group.get('lines', [])
                details = group.get('landowner_name', '')
                father = group.get('father_name')
                if father:
                    details = f"{details}\nपिता/पति: {father}"
                for idx, tree in enumerate(lines):
                    tree_sheet.write(tree_row, 0, i if idx == 0 else '', cell_center_fmt)
                    tree_sheet.write(tree_row, 1, details if idx == 0 else '', cell_fmt)
                    tree_sheet.write(tree_row, 2, tree.get('total_khasra', ''), cell_center_fmt)
                    tree_sheet.write_number(tree_row, 3, float(tree.get('total_area', 0.0) or 0.0), number_fmt)
                    tree_sheet.write(tree_row, 4, tree.get('khasra', ''), cell_center_fmt)
                    tree_sheet.write(tree_row, 5, tree.get('tree_type', ''), cell_fmt)
                    tree_sheet.write_number(tree_row, 6, float(tree.get('tree_count', 0.0) or 0.0), number_fmt)
                    tree_sheet.write_number(tree_row, 7, float(tree.get('girth_cm', 0.0) or 0.0), number_fmt)
                    tree_sheet.write_number(tree_row, 8, float(tree.get('rate', 0.0) or 0.0), money_fmt)
                    tree_sheet.write_number(tree_row, 9, float(tree.get('value', 0.0) or 0.0), money_fmt)
                    tree_sheet.write_number(tree_row, 10, float(tree.get('solatium', 0.0) or 0.0), money_fmt)
                    tree_sheet.write_number(tree_row, 11, float(tree.get('interest', 0.0) or 0.0), money_fmt)
                    tree_sheet.write_number(tree_row, 12, float(tree.get('total', 0.0) or 0.0), money_fmt)
                    tree_sheet.write(tree_row, 13, tree.get('remark', ''), cell_fmt)
                    tree_row += 1

                tree_sheet.merge_range(tree_row, 0, tree_row, 1, 'कुल', total_label_fmt)
                tree_sheet.write_number(tree_row, 2, float(group.get('khasra_count', 0) or 0), total_money_fmt)
                tree_sheet.write_number(tree_row, 3, float(group.get('total_area', 0.0) or 0.0), total_money_fmt)
                tree_sheet.write_number(tree_row, 4, float(group.get('khasra_count', 0) or 0), total_money_fmt)
                tree_sheet.write_blank(tree_row, 5, None, total_label_fmt)
                tree_sheet.write_number(tree_row, 6, float(group.get('tree_count', 0.0) or 0.0), total_money_fmt)
                tree_sheet.write_blank(tree_row, 7, None, total_label_fmt)
                tree_sheet.write_blank(tree_row, 8, None, total_label_fmt)
                tree_sheet.write_number(tree_row, 9, float(group.get('value', 0.0) or 0.0), total_money_fmt)
                tree_sheet.write_number(tree_row, 10, float(group.get('solatium', 0.0) or 0.0), total_money_fmt)
                tree_sheet.write_number(tree_row, 11, float(group.get('interest', 0.0) or 0.0), total_money_fmt)
                tree_sheet.write_number(tree_row, 12, float(group.get('total', 0.0) or 0.0), total_money_fmt)
                tree_sheet.write_blank(tree_row, 13, None, total_label_fmt)
                tree_row += 1

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())
        output.close()

        attachment = self.env['ir.attachment'].create({
            'name': f"Award_Simulator_{self.village_id.name or 'Manual'}.xlsx",
            'type': 'binary',
            'datas': file_data,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }


class AwardSimulatorLandLine(models.Model):
    _name = 'bhu.award.simulator.land.line'
    _description = 'Award Simulator – Land Line (per khasra)'
    _order = 'khasra_number'

    simulator_id = fields.Many2one('bhu.award.simulator', string='Simulator', ondelete='cascade')
    survey_id = fields.Many2one('bhu.survey', string='Survey / सर्वे', required=True)

    # Read-only data pulled directly from the linked survey
    khasra_number = fields.Char(
        string='Khasra Number', related='survey_id.khasra_number',
        store=True, readonly=True,
    )
    village_id = fields.Many2one(
        'bhu.village', string='Village', related='survey_id.village_id',
        store=True, readonly=True,
    )
    is_within_distance_for_award = fields.Boolean(
        string='Within Main Road', related='survey_id.is_within_distance_for_award',
        readonly=True,
    )
    distance_from_main_road = fields.Float(
        string='Distance (m)', related='survey_id.distance_from_main_road',
        store=True, readonly=True, digits=(10, 2),
    )
    irrigation_type = fields.Selection(
        related='survey_id.irrigation_type', string='Irrigation Type',
        readonly=True,
    )
    has_traded_land = fields.Selection(
        related='survey_id.has_traded_land', string='Diverted (Traded)',
        readonly=True,
    )
    acquired_area = fields.Float(
        string='Acquired Area (Ha)', related='survey_id.acquired_area',
        store=True, readonly=True, digits=(10, 4),
    )
    total_area = fields.Float(
        string='Total Area (Ha)', related='survey_id.total_area',
        readonly=True, digits=(10, 4),
    )

    road_type = fields.Selection([
        ('mr', 'MR'),
        ('mbr', 'BMR'),
    ], string='Road Type', compute='_compute_amounts', store=True)

    diverted_display = fields.Char(
        string='Diverted', compute='_compute_diverted_display',
    )

    irrigation_display = fields.Char(
        string='Irrigation', compute='_compute_irrigation_display',
    )

    @api.depends('has_traded_land')
    def _compute_diverted_display(self):
        for line in self:
            if line.has_traded_land == 'yes':
                line.diverted_display = '✓'
            elif line.has_traded_land == 'no':
                line.diverted_display = '✗'
            else:
                line.diverted_display = ''

    @api.depends('irrigation_type')
    def _compute_irrigation_display(self):
        for line in self:
            if line.irrigation_type == 'irrigated':
                line.irrigation_display = 'Irrigated'
            elif line.irrigation_type == 'unirrigated':
                line.irrigation_display = 'Unirrigated'
            else:
                line.irrigation_display = ''

    base_rate = fields.Float(
        string='Base Rate (₹/Ha)', digits=(16, 2),
        compute='_compute_amounts', store=True,
    )
    effective_rate = fields.Float(
        string='Effective Rate (₹/Ha)', digits=(16, 2),
        compute='_compute_amounts', store=True,
    )
    land_award_amount = fields.Float(
        string='Land Award (₹)', digits=(16, 2),
        compute='_compute_amounts', store=True,
    )
    solatium_amount = fields.Float(
        string='Solatium 100% (₹)', digits=(16, 2),
        compute='_compute_amounts', store=True,
    )
    interest_days = fields.Integer(
        string='Interest Days', compute='_compute_amounts', store=True,
    )
    interest_amount = fields.Float(
        string='Interest 12% (₹)', digits=(16, 2),
        compute='_compute_amounts', store=True,
    )
    line_total = fields.Float(
        string='Line Total (₹)', digits=(16, 2),
        compute='_compute_amounts', store=True,
    )

    @api.depends(
        'survey_id', 'survey_id.is_within_distance_for_award',
        'survey_id.distance_from_main_road', 'survey_id.survey_type',
        'survey_id.irrigation_type', 'survey_id.has_traded_land',
        'survey_id.acquired_area', 'survey_id.village_id',
        'simulator_id.base_rate', 'simulator_id.section4_date',
        'simulator_id.award_date', 'simulator_id.interest_rate_percent',
    )
    def _compute_amounts(self):
        for line in self:
            survey = line.survey_id
            simulator = line.simulator_id

            # Derive road type directly from measured distance when available.
            # This avoids stale UI cases where boolean may not yet be refreshed.
            if survey:
                distance = survey.distance_from_main_road or 0.0
                threshold = 50.0 if survey.survey_type == 'rural' else 20.0
                road_type = 'mr' if distance <= threshold else 'mbr'
            else:
                road_type = 'mbr'

            base = simulator.base_rate if simulator else 0.0
            village = survey.village_id if survey else False
            if (not base) and village:
                rate_master = line.env['bhu.rate.master'].search([
                    ('village_id', '=', village.id),
                    ('state', '=', 'active'),
                ], limit=1)
                if rate_master:
                    base = (
                        rate_master.main_road_rate_hectare
                        if road_type == 'mr'
                        else rate_master.other_road_rate_hectare
                    )

            rate = base or 0.0
            if survey and survey.has_traded_land == 'yes':
                rate = rate * 0.80
            if survey and survey.irrigation_type == 'irrigated':
                rate = rate * 1.20
            else:
                rate = rate * 0.80

            acquired = (survey.acquired_area or 0.0) if survey else 0.0
            land_award = rate * acquired
            solatium = land_award * 1.0

            interest, days = 0.0, 0
            if simulator:
                interest, days = simulator._calculate_interest_on_basic(land_award)

            line.road_type = road_type
            line.base_rate = base or 0.0
            line.effective_rate = rate
            line.land_award_amount = land_award
            line.solatium_amount = solatium
            line.interest_days = days
            line.interest_amount = interest
            line.line_total = land_award + solatium + interest


class AwardSimulatorTreeLine(models.Model):
    _name = 'bhu.award.simulator.tree.line'
    _description = 'Award Simulator – Tree Line'

    simulator_id = fields.Many2one('bhu.award.simulator', string='Simulator', ondelete='cascade')
    survey_id = fields.Many2one('bhu.survey', string='Survey / सर्वे')
    khasra_number = fields.Char(
        string='Khasra Number',
        related='survey_id.khasra_number',
        store=True,
        readonly=True,
    )

    tree_master_id = fields.Many2one('bhu.tree.master', string='Tree / वृक्ष', required=True)
    tree_type = fields.Selection(related='tree_master_id.tree_type', string='Tree Type', readonly=True)

    development_stage = fields.Selection([
        ('undeveloped', 'Undeveloped / अविकसित'),
        ('semi_developed', 'Semi-developed / अर्ध-विकसित'),
        ('fully_developed', 'Fully Developed / पूर्ण विकसित'),
    ], string='Development Stage / विकास स्तर', required=True, default='fully_developed')

    girth_cm = fields.Float(string='Girth (cm) / छाती (से.मी.)', digits=(10, 2))

    condition = fields.Selection([
        ('sound', 'Sound / स्वस्थ'),
        ('unsound', 'Unsound / अस्वस्थ'),
    ], string='Condition / स्थिति', default='sound')

    quantity = fields.Integer(string='Quantity / संख्या', default=1)

    unit_rate = fields.Float(
        string='Unit Rate (₹) / इकाई दर',
        digits=(16, 2), compute='_compute_unit_rate', store=True
    )
    line_total = fields.Float(
        string='Line Total (₹) / पंक्ति कुल',
        digits=(16, 2), compute='_compute_unit_rate', store=True
    )

    @api.depends('tree_master_id', 'development_stage', 'girth_cm', 'condition', 'quantity')
    def _compute_unit_rate(self):
        for line in self:
            # Keep simulator totals usable even when exact tree-rate master rows are missing.
            fallback_rate = 6000.0 if line.tree_type == 'fruit_bearing' else 177.0
            rate = fallback_rate
            if line.tree_master_id and line.development_stage:
                # Find matching rate variant
                domain = [
                    ('tree_master_id', '=', line.tree_master_id.id),
                    ('development_stage', '=', line.development_stage),
                    ('active', '=', True),
                ]
                rate_variants = line.env['bhu.tree.rate.master'].search(domain, order='girth_range_min')

                if rate_variants:
                    if line.girth_cm:
                        # Match by girth range
                        matched = rate_variants.filtered(
                            lambda r: r.girth_range_min <= line.girth_cm and
                                      (not r.girth_range_max or r.girth_range_max >= line.girth_cm)
                        )
                        if matched:
                            rate = matched[0].rate or fallback_rate
                        else:
                            # Use highest girth range if girth exceeds all ranges
                            rate = rate_variants[-1].rate or fallback_rate
                    else:
                        # No girth specified – use first variant
                        rate = rate_variants[0].rate or fallback_rate

            # Unsound trees get 50% of rate
            if line.condition == 'unsound':
                rate = rate * 0.5

            line.unit_rate = rate
            line.line_total = rate * (line.quantity or 0)

    @api.onchange('tree_master_id')
    def _onchange_tree_master_id(self):
        """Reset stage when tree changes"""
        self.development_stage = 'fully_developed'
        self.girth_cm = 0.0


class AwardSimulatorStructureLine(models.Model):
    _name = 'bhu.award.simulator.structure.line'
    _description = 'Award Simulator – Structure Line'

    simulator_id = fields.Many2one('bhu.award.simulator', string='Simulator', ondelete='cascade')
    survey_id = fields.Many2one(
        'bhu.survey',
        string='Khasra / खसरा',
        required=True,
        help='Select khasra first, then add manual structure details for this award simulation.'
    )
    khasra_number = fields.Char(
        string='Khasra Number / खसरा नंबर',
        related='survey_id.khasra_number',
        store=True,
        readonly=True
    )

    structure_type = fields.Selection([
        ('makan', 'Makan / मकान'),
        ('well', 'Well / कुआं'),
        ('maveshi_kotha', 'Maveshi Kotha / मवेशी कोठा'),
        ('poultry_farm_shed', 'Poultry Farm Shed / पोल्ट्री फार्म शेड'),
        ('other', 'Others / अन्य'),
    ], string='Structure Type / परिसम्पत्ति विवरण', required=True)

    construction_type = fields.Selection([
        ('kaccha', 'Kaccha / कच्चा'),
        ('pukka', 'Pukka / पक्का'),
    ], string='Construction Type / निर्माण प्रकार')

    description = fields.Char(string='Description / विवरण')
    well_count = fields.Integer(string='Well Count / कुओं की संख्या', default=1)
    area_sqm = fields.Float(string='Area (Sq. Meter) / क्षेत्रफल (वर्ग मीटर)', digits=(10, 2))
    market_rate_per_sqm = fields.Float(string='Market Rate per Sq. Meter (₹) / बाजार मूल्य दर (प्रति वर्ग मीटर)', digits=(16, 2))
    well_fixed_rate = fields.Float(string='Well Fixed Rate (₹) / कुआं स्थिर दर', default=90000.0, digits=(16, 2))
    asset_value = fields.Float(
        string='Asset Value (₹) / परिसम्पत्ति की कीमत',
        digits=(16, 2),
        compute='_compute_line_total',
        store=True
    )

    line_total = fields.Float(
        string='Line Total (₹) / पंक्ति कुल',
        digits=(16, 2), compute='_compute_line_total', store=True
    )

    @api.depends('structure_type', 'well_count', 'well_fixed_rate', 'area_sqm', 'market_rate_per_sqm')
    def _compute_line_total(self):
        for line in self:
            if line.structure_type == 'well':
                computed_value = (line.well_count or 0) * (line.well_fixed_rate or 0.0)
            else:
                computed_value = (line.area_sqm or 0.0) * (line.market_rate_per_sqm or 0.0)
            line.asset_value = computed_value
            line.line_total = computed_value

    def get_structure_type_label(self):
        """Return display label for structure type selection."""
        self.ensure_one()
        base = dict(self._fields['structure_type'].selection).get(self.structure_type, self.structure_type or 'Other')
        if self.construction_type:
            construction = dict(self._fields['construction_type'].selection).get(self.construction_type, self.construction_type)
            return f"{base} ({construction})"
        return base
