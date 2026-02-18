# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AwardSimulator(models.TransientModel):
    _name = 'bhu.award.simulator'
    _description = 'Award Simulator / अवार्ड सिमुलेटर'

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

    road_type = fields.Selection([
        ('mr', 'MR – Main Road / मुख्यमार्ग'),
        ('mbr', 'MBR – Beyond Main Road / मुख्यमार्ग से परे'),
    ], string='Road Type / सड़क प्रकार', required=True, default='mr')

    is_diverted = fields.Boolean(string='Diverted Land / विचलित भूमि', default=False)
    irrigation_type = fields.Selection([
        ('irrigated', 'Irrigated / सिंचित'),
        ('unirrigated', 'Unirrigated / असिंचित'),
    ], string='Irrigation Type / सिंचाई प्रकार', required=True, default='irrigated')

    acquired_area = fields.Float(
        string='Acquired Area (Hectares) / अर्जित क्षेत्रफल (हेक्टेयर)',
        digits=(10, 4), default=1.0
    )

    # ─── Computed Land Rate ────────────────────────────────────────────────────
    effective_land_rate = fields.Float(
        string='Effective Land Rate (₹/Ha) / प्रभावी भूमि दर',
        digits=(16, 2), compute='_compute_land_award', store=False
    )
    land_award_amount = fields.Float(
        string='Land Award Amount (₹) / भूमि अवार्ड राशि',
        digits=(16, 2), compute='_compute_land_award', store=False
    )
    solatium_amount = fields.Float(
        string='Solatium 100% (₹) / सॉलेशियम 100%',
        digits=(16, 2), compute='_compute_land_award', store=False
    )
    land_total = fields.Float(
        string='Land Total (₹) / भूमि कुल',
        digits=(16, 2), compute='_compute_land_award', store=False
    )

    @api.depends('base_rate', 'road_type', 'is_diverted', 'irrigation_type', 'acquired_area', 'village_id')
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

            # Road type adjustment: MBR uses other_road rate (already selected via base)
            # If base was manually entered, MBR = base (no further road adjustment needed)
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

            rec.effective_land_rate = rate
            rec.land_award_amount = land_award
            rec.solatium_amount = solatium
            rec.land_total = land_award + solatium

    # ─── Tree Section ──────────────────────────────────────────────────────────
    tree_line_ids = fields.One2many(
        'bhu.award.simulator.tree.line', 'simulator_id',
        string='Trees / वृक्ष'
    )
    tree_total = fields.Float(
        string='Tree Total (₹) / वृक्ष कुल',
        digits=(16, 2), compute='_compute_tree_total', store=False
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
        digits=(16, 2), compute='_compute_structure_total', store=False
    )

    @api.depends('structure_line_ids', 'structure_line_ids.line_total')
    def _compute_structure_total(self):
        for rec in self:
            rec.structure_total = sum(rec.structure_line_ids.mapped('line_total'))

    # ─── Grand Total ───────────────────────────────────────────────────────────
    grand_total = fields.Float(
        string='Grand Total Award (₹) / कुल अवार्ड',
        digits=(16, 2), compute='_compute_grand_total', store=False
    )

    @api.depends('land_total', 'tree_total', 'structure_total')
    def _compute_grand_total(self):
        for rec in self:
            rec.grand_total = rec.land_total + rec.tree_total + rec.structure_total

    # ─── Auto-fill base rate from village ─────────────────────────────────────
    @api.onchange('village_id', 'road_type')
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
        """Trigger recompute (no-op, computed fields auto-update)"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'bhu.award.simulator',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self.env.context,
        }


class AwardSimulatorTreeLine(models.TransientModel):
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
        digits=(16, 2), compute='_compute_unit_rate', store=False
    )
    line_total = fields.Float(
        string='Line Total (₹) / पंक्ति कुल',
        digits=(16, 2), compute='_compute_unit_rate', store=False
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


class AwardSimulatorStructureLine(models.TransientModel):
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
        digits=(16, 2), compute='_compute_line_total', store=False
    )

    @api.depends('quantity', 'area_sqft', 'unit_rate')
    def _compute_line_total(self):
        for line in self:
            if line.area_sqft:
                line.line_total = line.area_sqft * line.unit_rate * (line.quantity or 1)
            else:
                line.line_total = line.unit_rate * (line.quantity or 1)
