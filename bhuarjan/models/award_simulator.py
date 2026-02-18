# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AwardSimulator(models.Model):
    _name = 'bhu.award.simulator'
    _description = 'Award Simulator / अवार्ड सिमुलेटर'
    _order = 'id desc'

    name = fields.Char(string='Reference Name', default='New Simulation')
    user_id = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user)

    # ─── Survey Type ───────────────────────────────────────────────────────────
    survey_type = fields.Selection([
        ('rural', 'Rural / ग्रामीण'),
        ('urban', 'Urban / शहरी'),
    ], string='Survey Type / सर्वे प्रकार', required=True, default='rural')

    # ─── Land Section ──────────────────────────────────────────────────────────
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम')
    district_id = fields.Many2one('bhu.district', string='District / जिला')

    base_rate = fields.Float(
        string='Base Rate per Hectare (₹) / आधार दर प्रति हेक्टेयर',
        digits=(16, 2),
        help='Enter the base land rate per hectare manually, or it will be auto-filled from the Land Rate Master if a village is selected.'
    )

    distance_from_road = fields.Float(
        string='Distance from Main Road (M) / मुख्य मार्ग से दूरी (मीटर)',
        digits=(10, 2), default=0.0,
        help='Rural: <= 20m is MR, Urban: <= 50m is MR'
    )

    road_type = fields.Selection([
        ('mr', 'MR – Main Road / मुख्यमार्ग'),
        ('mbr', 'MBR – Beyond Main Road / मुख्यमार्ग से परे'),
    ], string='Road Type / सड़क प्रकार', compute='_compute_road_type', store=True, readonly=False)

    @api.depends('distance_from_road', 'survey_type')
    def _compute_road_type(self):
        for rec in self:
            dist = rec.distance_from_road
            if rec.survey_type == 'rural':
                rec.road_type = 'mr' if dist <= 20 else 'mbr'
            else: # urban
                rec.road_type = 'mr' if dist <= 50 else 'mbr'

    is_diverted = fields.Boolean(string='Diverted Land / विचलित भूमि', default=False)
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

    @api.depends('base_rate', 'road_type', 'is_diverted', 'irrigation_type', 'acquired_area', 'village_id', 
                 'section4_date', 'award_date', 'interest_rate_percent')
    def _compute_land_award(self):
        for rec in self:
            base = rec.base_rate or 0.0

            # Auto-fetch from rate master if village is set and base_rate is 0
            if not base and rec.village_id:
                rate_master = rec.env['bhu.rate.master'].search([
                    ('village_id', '=', rec.village_id.id),
                    ('state', '=', 'active'),
                ], limit=1)
                if rate_master:
                    base = rate_master.main_road_rate_hectare if rec.road_type == 'mr' else rate_master.other_road_rate_hectare

            # Road type adjustment
            rate = base

            # Diverted: -20%
            if rec.is_diverted:
                rate = rate * 0.80

            # Irrigation adjustment
            if rec.irrigation_type == 'irrigated':
                rate = rate * 1.20
            else:
                rate = rate * 0.80

            land_award = rate * (rec.acquired_area or 0.0)
            solatium = land_award * 1.0  # 100% solatium
            
            # Interest Calculation (12% per annum on Market Value)
            interest = 0.0
            days = 0
            if rec.section4_date and rec.award_date and rec.section4_date < rec.award_date:
                delta = rec.award_date - rec.section4_date
                days = delta.days
                # Interest = Market Value * (12/100) * (Days / 365)
                interest = land_award * (rec.interest_rate_percent / 100.0) * (days / 365.25)

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

    # ─── Tree Section ──────────────────────────────────────────────────────────
    tree_line_ids = fields.One2many(
        'bhu.award.simulator.tree.line', 'simulator_id',
        string='Trees / वृक्ष'
    )
    tree_total = fields.Float(
        string='Tree Total (₹) / वृक्ष कुल',
        digits=(16, 2), compute='_compute_tree_total', store=True
    )

    @api.depends('tree_line_ids', 'tree_line_ids.line_total')
    def _compute_tree_total(self):
        for rec in self:
            rec.tree_total = sum(rec.tree_line_ids.mapped('line_total'))

    # ─── Structure Section ─────────────────────────────────────────────────────
    structure_line_ids = fields.One2many(
        'bhu.award.simulator.structure.line', 'simulator_id',
        string='Structures / संरचनाएं'
    )
    structure_total = fields.Float(
        string='Structure Total (₹) / संरचना कुल',
        digits=(16, 2), compute='_compute_structure_total', store=True
    )

    @api.depends('structure_line_ids', 'structure_line_ids.line_total')
    def _compute_structure_total(self):
        for rec in self:
            rec.structure_total = sum(rec.structure_line_ids.mapped('line_total'))

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

    def action_calculate(self):
        """Trigger recompute (now that store=True, this might be needed for forced refresh)"""
        self._compute_land_award()
        self._compute_tree_total()
        self._compute_structure_total()
        self._compute_grand_total()
        return True


class AwardSimulatorTreeLine(models.Model):
    _name = 'bhu.award.simulator.tree.line'
    _description = 'Award Simulator – Tree Line'

    simulator_id = fields.Many2one('bhu.award.simulator', string='Simulator', ondelete='cascade')

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
            rate = 0.0
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
                            rate = matched[0].rate
                        else:
                            # Use highest girth range if girth exceeds all ranges
                            rate = rate_variants[-1].rate
                    else:
                        # No girth specified – use first variant
                        rate = rate_variants[0].rate

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

    structure_type = fields.Selection([
        ('well_kaccha', 'Well – Kaccha / कुआं (कच्चा)'),
        ('well_pakka', 'Well – Pakka / कुआं (पक्का)'),
        ('tubewell', 'Tubewell / ट्यूबवेल'),
        ('pond', 'Pond / तालाब'),
        ('house_kaccha', 'House – Kaccha / घर (कच्चा)'),
        ('house_pakka', 'House – Pakka / घर (पक्का)'),
        ('shed_kaccha', 'Shed – Kaccha / शेड (कच्चा)'),
        ('shed_pakka', 'Shed – Pakka / शेड (पक्का)'),
        ('other', 'Other / अन्य'),
    ], string='Structure Type / संरचना प्रकार', required=True)

    description = fields.Char(string='Description / विवरण')
    quantity = fields.Integer(string='Quantity / संख्या', default=1)
    area_sqft = fields.Float(string='Area (Sq. Ft.) / क्षेत्रफल (वर्ग फुट)', digits=(10, 2))
    unit_rate = fields.Float(string='Rate per Unit/Sq.Ft. (₹) / दर', digits=(16, 2))

    line_total = fields.Float(
        string='Line Total (₹) / पंक्ति कुल',
        digits=(16, 2), compute='_compute_line_total', store=True
    )

    @api.depends('quantity', 'area_sqft', 'unit_rate')
    def _compute_line_total(self):
        for line in self:
            if line.area_sqft:
                line.line_total = line.area_sqft * line.unit_rate * (line.quantity or 1)
            else:
                line.line_total = line.unit_rate * (line.quantity or 1)
