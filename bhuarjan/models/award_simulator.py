# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


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
            if rec.has_traded_land:
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
            
            # Attempt to map project_id automatically if village is selected
            if not self.project_id and hasattr(self.village_id, 'project_ids') and self.village_id.project_ids:
                self.project_id = self.village_id.project_ids[0]

            rate_master = self.env['bhu.rate.master'].search([
                ('village_id', '=', self.village_id.id),
                ('state', '=', 'active'),
            ], limit=1)
            if rate_master:
                if self.road_type == 'mr':
                    self.base_rate = rate_master.main_road_rate_hectare
                else:
                    self.base_rate = rate_master.other_road_rate_hectare

    def format_indian_number(self, value, decimals=2):
        if value is None:
            value = 0.0
        if decimals == 2:
            return f"{value:,.2f}"
        elif decimals == 4:
            return f"{value:,.4f}"
        else:
            return f"{value:,.{decimals}f}"

    def get_land_compensation_data(self):
        self.ensure_one()
        # In Simulator, we want to see the effect on ALL surveys in the village regardless of state
        surveys = self.env['bhu.survey'].search([
            ('village_id', '=', self.village_id.id),
            ('khasra_number', '!=', False),
        ])
        if self.project_id:
            surveys = surveys.filtered(lambda x: x.project_id == self.project_id)
            
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
                'unirrigated': self.irrigation_type == 'unirrigated',
                'irrigated': self.irrigation_type == 'irrigated',
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
            
            # Using is_within_distance_for_award (True=Main Road, False=Other Road/MBR)
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
            
            interest = 0.0
            if self.section4_date and self.award_date:
                days = (self.award_date - self.section4_date).days
                if days > 0:
                    # Column 16: Interest (12% per annum)
                    interest = market_value_factored * (self.interest_rate_percent / 100.0) * (days / 365.25)
                    
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
                        'unirrigated': not is_irrigated,
                        'irrigated': is_irrigated,
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
                            'unirrigated': not is_irrigated,
                            'irrigated': is_irrigated,
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

    def get_tree_compensation_data(self):
        self.ensure_one()
        surveys = self.env['bhu.survey'].search([
            ('village_id', '=', self.village_id.id),
            ('khasra_number', '!=', False),
        ])
        if not surveys:
            # Fallback to manual simulator tree data
            if not self.tree_line_ids:
                return []
            
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
                    'solatium': t_line.line_total or 0.0, # Simulator uses 100%
                    'interest': 0.0, 
                    'total': (t_line.line_total or 0.0) * 2.0, # basic + solatium
                    'remark': 'Manual Simulation',
                })
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
                    tree_data[key]['tree_count'] += tree_line.quantity or 0
                    tree_data[key]['girth_cm'] = tree_line.girth_cm or 0.0
                    tree_data[key]['rate'] = tree_line.rate_per_tree or 0.0
                    tree_data[key]['value'] += (tree_line.quantity or 0) * (tree_line.rate_per_tree or 0.0)
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
                        share = 1.0 / len(landowners)
                        tree_data[key]['tree_count'] += (tree_line.quantity or 0) * share
                        tree_data[key]['girth_cm'] = tree_line.girth_cm or 0.0
                        tree_data[key]['rate'] = tree_line.rate_per_tree or 0.0
                        tree_data[key]['value'] += (tree_line.quantity or 0) * (tree_line.rate_per_tree or 0.0) * share
                        
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
        return result

    def get_structure_compensation_data(self):
        """Get structure compensation data (house, well, pond, shed) for simulator report"""
        self.ensure_one()
        surveys = self.env['bhu.survey'].search([
            ('village_id', '=', self.village_id.id) if self.village_id else ('id', '=', 0),
            ('khasra_number', '!=', False),
            ('state', 'in', ['approved', 'locked']),
        ])
        
        if not surveys:
            # Fallback to manual simulator structure data
            if not self.structure_line_ids:
                return []
            
            manual_data = []
            for s_line in self.structure_line_ids:
                val = s_line.line_total or 0.0
                manual_data.append({
                    'landowner_name': 'Manual / मैनुअल', 'father_name': '',
                    'total_khasra': 'N/A', 'total_area': 0.0,
                    'asset_khasra': 'N/A', 'asset_land_area': 0.0,
                    'asset_type': s_line.structure_type or 'Other', 'asset_code': 4,
                    'asset_dimension': s_line.quantity or s_line.area_sqft or 0.0,
                    'market_value': val, 'solatium': val, 'interest': 0.0, 'total': val * 2.0,
                    'remark': 'Manual Simulation',
                })
            return manual_data
            
        structure_data = []
        for survey in surveys:
            assets = []
            if survey.has_house == 'yes':
                assets.append({'type': 'House / मकान', 'area': survey.house_area, 'code': 1})
            if survey.has_well == 'yes':
                assets.append({'type': 'Well / कुआं', 'area': survey.well_count, 'code': 2})
            if getattr(survey, 'has_shed', 'no') == 'yes':
                assets.append({'type': 'Shed / शेड', 'area': getattr(survey, 'shed_area', 0.0), 'code': 3})
            if survey.has_pond == 'yes':
                assets.append({'type': 'Pond / तालाब', 'area': 0.0, 'code': 4})

            if not assets:
                continue

            khasra = survey.khasra_number or ''
            landowners = survey.landowner_ids
            
            for asset in assets:
                if not landowners:
                    structure_data.append({
                        'landowner_name': '', 'father_name': '',
                        'total_khasra': khasra, 'total_area': survey.total_area or 0.0,
                        'asset_khasra': khasra, 'asset_land_area': 0.0,
                        'asset_type': asset['type'], 'asset_code': asset['code'],
                        'asset_dimension': asset['area'],
                        'market_value': 0.0, 'solatium': 0.0, 'interest': 0.0, 'total': 0.0, 'remark': '',
                    })
                else:
                    for landowner in landowners:
                        structure_data.append({
                            'landowner_name': landowner.name or '', 
                            'father_name': landowner.father_name or landowner.spouse_name or '',
                            'total_khasra': khasra, 'total_area': survey.total_area or 0.0,
                            'asset_khasra': khasra, 'asset_land_area': 0.0,
                            'asset_type': asset['type'], 'asset_code': asset['code'],
                            'asset_dimension': asset['area'],
                            'market_value': 0.0, 'solatium': 0.0, 'interest': 0.0, 'total': 0.0, 'remark': '',
                        })
        return structure_data

    def action_calculate(self):
        """Force recompute all stored depends fields"""
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
            'res_model': 'sia.download.wizard',
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
            'res_model': 'sia.download.wizard',
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
        return {
            'name': _('Download Award Summary (Word)'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sia.download.wizard',
            'target': 'new',
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
                'default_report_xml_id': 'bhuarjan.action_report_award_simulator',
                'default_format': 'word',
                'default_filename': f"Award_Simulator_{self.village_id.name or 'Manual'}_{fields.Date.today()}"
            }
        }

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
        sheet = workbook.add_worksheet('Award Simulator')

        # Print setup for long table layout
        sheet.set_landscape()
        sheet.set_paper(9)  # A4
        sheet.fit_to_pages(1, 0)
        sheet.repeat_rows(0, 8)

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

        # Column widths for 20-column long table (A:T)
        col_widths = [4, 24, 10, 10, 8, 10, 10, 8, 8, 8, 8, 10, 10, 11, 11, 10, 10, 11, 11, 10]
        for idx, width in enumerate(col_widths):
            sheet.set_column(idx, idx, width)

        row = 0
        sheet.merge_range(row, 0, row, 19, 'AWARD SIMULATOR / अवार्ड सिमुलेटर', title_fmt)
        row += 1
        subtitle = (
            f"Village / ग्राम: {self.village_id.name or '-'} | "
            f"Project / परियोजना: {self.project_id.name or '-'} | "
            f"Date / तिथि: {fields.Date.today()}"
        )
        sheet.merge_range(row, 0, row, 19, subtitle, subtitle_fmt)
        row += 2

        # LAND TABLE (same long structure as PDF)
        sheet.merge_range(row, 0, row, 19, 'पत्रक (भाग-1 क) - अर्जित भूमि का मुआवजा पत्रक', header_group_fmt)
        row += 1

        sheet.merge_range(row, 0, row + 1, 0, '1.\nक्र.', header_fmt)
        sheet.merge_range(row, 1, row + 1, 1, '2.\nभूमिस्वामी विवरण', header_fmt)
        sheet.merge_range(row, 2, row, 4, 'अर्जित भूमि का विवरण', header_group_fmt)
        sheet.merge_range(row, 5, row, 7, 'अर्जित भूमि का विवरण', header_group_fmt)
        sheet.merge_range(row, 8, row + 1, 8, '9.\nमुख्य मार्ग?', header_fmt)
        sheet.merge_range(row, 9, row + 1, 9, '10.\nअसिंचित?', header_fmt)
        sheet.merge_range(row, 10, row + 1, 10, '11.\nसिंचित?', header_fmt)
        sheet.merge_range(row, 11, row + 1, 11, 'विगत तीन वर्षों का औसत बिक्री छांट दर', header_fmt)
        sheet.merge_range(row, 12, row + 1, 12, '12.\nगाइड लाइन दर', header_fmt)
        sheet.merge_range(row, 13, row + 1, 13, '13.\nमूल्य (Basic)', header_fmt)
        sheet.merge_range(row, 14, row + 1, 14, '14.\nबाजार मूल्य (Factor=2)', header_fmt)
        sheet.merge_range(row, 15, row + 1, 15, '15.\nसोलेशियम (100%)', header_fmt)
        sheet.merge_range(row, 16, row + 1, 16, '16.\nब्याज (12%)', header_fmt)
        sheet.merge_range(row, 17, row + 1, 17, '17.\nकुल निर्धारित', header_fmt)
        sheet.merge_range(row, 18, row + 1, 18, '18.\nदेय मुआवजा', header_fmt)
        sheet.merge_range(row, 19, row + 1, 19, '19.\nरिमार्क', header_fmt)
        row += 1
        sheet.write(row, 2, '3.\nकुल खसरा', header_fmt)
        sheet.write(row, 3, '4.\nकुल रकबा', header_fmt)
        sheet.write(row, 4, '5.\nलगान', header_fmt)
        sheet.write(row, 5, '6.\nअर्जित खसरा', header_fmt)
        sheet.write(row, 6, '7.\nअर्जित रकबा', header_fmt)
        sheet.write(row, 7, '8.\nलगान', header_fmt)
        sheet.set_row(row - 1, 36)
        sheet.set_row(row, 36)
        row += 1

        land_data = self.get_land_compensation_data()
        if not land_data:
            sheet.merge_range(row, 0, row, 19, 'No land data available / भूमि डेटा उपलब्ध नहीं है (Blank)', blank_msg_fmt)
            row += 1
        else:
            total_basic = total_market = total_solatium = 0.0
            total_interest = total_comp = total_paid = total_acq = 0.0
            for i, land in enumerate(land_data, 1):
                details = land.get('landowner_name', '')
                father = land.get('father_name')
                if father:
                    details = f"{details}\nपिता/पति: {father}"
                sheet.write(row, 0, i, cell_center_fmt)
                sheet.write(row, 1, details, cell_fmt)
                sheet.write(row, 2, land.get('khasra', ''), cell_center_fmt)
                sheet.write_number(row, 3, float(land.get('original_area', 0.0) or 0.0), number_fmt)
                sheet.write(row, 4, land.get('lagan', ''), cell_center_fmt)
                sheet.write(row, 5, land.get('khasra', ''), cell_center_fmt)
                sheet.write_number(row, 6, float(land.get('acquired_area', 0.0) or 0.0), number_fmt)
                sheet.write(row, 7, land.get('lagan', ''), cell_center_fmt)
                sheet.write(row, 8, 'हाँ' if land.get('is_within_distance') else 'नहीं', cell_center_fmt)
                sheet.write(row, 9, 'हाँ' if land.get('unirrigated') else 'नहीं', cell_center_fmt)
                sheet.write(row, 10, 'हाँ' if land.get('irrigated') else 'नहीं', cell_center_fmt)
                sheet.write(row, 11, '-', cell_center_fmt)
                sheet.write_number(row, 12, float(land.get('guide_line_rate', 0.0) or 0.0), money_fmt)
                sheet.write_number(row, 13, float(land.get('basic_value', 0.0) or 0.0), money_fmt)
                sheet.write_number(row, 14, float(land.get('market_value', 0.0) or 0.0), money_fmt)
                sheet.write_number(row, 15, float(land.get('solatium', 0.0) or 0.0), money_fmt)
                sheet.write_number(row, 16, float(land.get('interest', 0.0) or 0.0), money_fmt)
                sheet.write_number(row, 17, float(land.get('total_compensation', 0.0) or 0.0), money_fmt)
                sheet.write_number(row, 18, float(land.get('paid_compensation', 0.0) or 0.0), money_fmt)
                sheet.write(row, 19, land.get('remark', ''), cell_fmt)
                total_acq += float(land.get('acquired_area', 0.0) or 0.0)
                total_basic += float(land.get('basic_value', 0.0) or 0.0)
                total_market += float(land.get('market_value', 0.0) or 0.0)
                total_solatium += float(land.get('solatium', 0.0) or 0.0)
                total_interest += float(land.get('interest', 0.0) or 0.0)
                total_comp += float(land.get('total_compensation', 0.0) or 0.0)
                total_paid += float(land.get('paid_compensation', 0.0) or 0.0)
                row += 1

            sheet.merge_range(row, 0, row, 5, 'MAHAYOG (TOTAL) / महायोग', total_label_fmt)
            sheet.write_number(row, 6, total_acq, total_money_fmt)
            sheet.write_blank(row, 7, None, total_label_fmt)
            sheet.write_blank(row, 8, None, total_label_fmt)
            sheet.write_blank(row, 9, None, total_label_fmt)
            sheet.write_blank(row, 10, None, total_label_fmt)
            sheet.write_blank(row, 11, None, total_label_fmt)
            sheet.write_blank(row, 12, None, total_label_fmt)
            sheet.write_number(row, 13, total_basic, total_money_fmt)
            sheet.write_number(row, 14, total_market, total_money_fmt)
            sheet.write_number(row, 15, total_solatium, total_money_fmt)
            sheet.write_number(row, 16, total_interest, total_money_fmt)
            sheet.write_number(row, 17, total_comp, total_money_fmt)
            sheet.write_number(row, 18, total_paid, total_money_fmt)
            sheet.write_blank(row, 19, None, total_label_fmt)
            row += 2

        # ASSET / STRUCTURE TABLE
        sheet.merge_range(row, 0, row, 19, 'पत्रक (भाग-1 ख) - परिसम्पत्तियों का मुआवजा पत्रक', header_group_fmt)
        row += 1
        asset_headers = [
            '1. क्र.', '2. भूमिस्वामी विवरण', '3. कुल खसरा', '4. रकबा (हे.)', '5. खसरा',
            '6. रकबा', '7. परिसम्पत्ति विवरण', '8. क्षेत्रफल', '9. बाजार मूल्य', '10. 100% सोलेशियम',
            '11. 12% ब्याज', '12. योग', '13. रिमार्क'
        ]
        for col, title in enumerate(asset_headers):
            sheet.write(row, col, title, header_fmt)
        row += 1
        asset_data = self.get_structure_compensation_data()
        if not asset_data:
            sheet.merge_range(row, 0, row, 12, 'No asset/structure data available / परिसम्पत्ति डेटा उपलब्ध नहीं है (Blank)', blank_msg_fmt)
            row += 1
        else:
            for i, asset in enumerate(asset_data, 1):
                details = asset.get('landowner_name', '')
                father = asset.get('father_name')
                if father:
                    details = f"{details}\nपिता/पति: {father}"
                sheet.write(row, 0, i, cell_center_fmt)
                sheet.write(row, 1, details, cell_fmt)
                sheet.write(row, 2, asset.get('total_khasra', ''), cell_center_fmt)
                sheet.write_number(row, 3, float(asset.get('total_area', 0.0) or 0.0), number_fmt)
                sheet.write(row, 4, asset.get('asset_khasra', ''), cell_center_fmt)
                sheet.write_number(row, 5, float(asset.get('asset_land_area', 0.0) or 0.0), number_fmt)
                sheet.write(row, 6, f"({asset.get('asset_code', '4')}) {asset.get('asset_type', '')}", cell_fmt)
                sheet.write_number(row, 7, float(asset.get('asset_dimension', 0.0) or 0.0), number_fmt)
                sheet.write_number(row, 8, float(asset.get('market_value', 0.0) or 0.0), money_fmt)
                sheet.write_number(row, 9, float(asset.get('solatium', 0.0) or 0.0), money_fmt)
                sheet.write_number(row, 10, float(asset.get('interest', 0.0) or 0.0), money_fmt)
                sheet.write_number(row, 11, float(asset.get('total', 0.0) or 0.0), money_fmt)
                sheet.write(row, 12, asset.get('remark', ''), cell_fmt)
                row += 1
        row += 1

        # TREE TABLE
        sheet.merge_range(row, 0, row, 19, 'पत्रक (भाग-1 ग) - वृक्षों का मुआवजा पत्रक', header_group_fmt)
        row += 1
        tree_headers = [
            '1. क्र.', '2. भूमिस्वामी विवरण', '3. कुल खसरा', '4. रकबा (हे.)', '5. खसरा',
            '6. वृक्ष प्रकार', '7. गोलाई', '8. Misc', '8. Rate', '8. Value',
            '9. 100% सोलेशियम', '10. 12% ब्याज', '11. योग', '12. रिमार्क'
        ]
        for col, title in enumerate(tree_headers):
            sheet.write(row, col, title, header_fmt)
        row += 1
        tree_data = self.get_tree_compensation_data()
        if not tree_data:
            sheet.merge_range(row, 0, row, 13, 'No tree data available / वृक्ष डेटा उपलब्ध नहीं है (Blank)', blank_msg_fmt)
            row += 1
        else:
            for i, tree in enumerate(tree_data, 1):
                details = tree.get('landowner_name', '')
                father = tree.get('father_name')
                if father:
                    details = f"{details}\nपिता/पति: {father}"
                tree_desc = f"{tree.get('tree_type', '')}\nनग: {tree.get('tree_count', 0)}"
                sheet.write(row, 0, i, cell_center_fmt)
                sheet.write(row, 1, details, cell_fmt)
                sheet.write(row, 2, tree.get('total_khasra', ''), cell_center_fmt)
                sheet.write_number(row, 3, float(tree.get('total_area', 0.0) or 0.0), number_fmt)
                sheet.write(row, 4, tree.get('khasra', ''), cell_center_fmt)
                sheet.write(row, 5, tree_desc, cell_fmt)
                sheet.write_number(row, 6, float(tree.get('girth_cm', 0.0) or 0.0), number_fmt)
                sheet.write(row, 7, '-', cell_center_fmt)
                sheet.write_number(row, 8, float(tree.get('rate', 0.0) or 0.0), money_fmt)
                sheet.write_number(row, 9, float(tree.get('value', 0.0) or 0.0), money_fmt)
                sheet.write_number(row, 10, float(tree.get('solatium', 0.0) or 0.0), money_fmt)
                sheet.write_number(row, 11, float(tree.get('interest', 0.0) or 0.0), money_fmt)
                sheet.write_number(row, 12, float(tree.get('total', 0.0) or 0.0), money_fmt)
                sheet.write(row, 13, tree.get('remark', ''), cell_fmt)
                row += 1

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
