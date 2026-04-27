# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Section23AwardLineItem(models.Model):
    _name = 'bhu.section23.award.line.item'
    _description = 'Section 23 Award Line Item'
    _order = 'id'

    award_id = fields.Many2one('bhu.section23.award', required=True, ondelete='cascade')
    line_type = fields.Selection([
        ('land', 'Land'),
        ('tree', 'Tree'),
        ('structure', 'Structure'),
    ], string='Component', required=True, default='land')
    landowner_name = fields.Char(string='Landowner')
    khasra_number = fields.Char(string='Khasra')
    original_area = fields.Float(string='Original Area', digits=(16, 4))
    acquired_area = fields.Float(string='Acquired Area', digits=(16, 4))
    is_within_distance = fields.Boolean(string='Main Road')
    irrigated = fields.Boolean(string='Irrigated')
    unirrigated = fields.Boolean(string='Unirrigated')
    is_diverted = fields.Boolean(string='Diverted')
    guide_line_rate = fields.Float(string='Guide Line Rate', digits=(16, 2))
    basic_value = fields.Float(string='Basic Value', digits=(16, 2))
    market_value = fields.Float(string='Market Value', digits=(16, 2))
    solatium = fields.Float(string='Solatium', digits=(16, 2))
    interest = fields.Float(string='Interest', digits=(16, 2))
    total_compensation = fields.Float(string='Total', digits=(16, 2))
    rehab_policy_amount = fields.Float(string='Rehab Policy', digits=(16, 2))
    paid_compensation = fields.Float(string='Payable', digits=(16, 2))
    remark = fields.Char(string='Remark')


class Section23AwardSurveyLine(models.Model):
    """Survey lines for Section 23 Award - allows selection of type and distance for each survey"""
    _name = 'bhu.section23.award.survey.line'
    _description = 'Section 23 Award Survey Line'
    _order = 'survey_id'

    award_id = fields.Many2one('bhu.section23.award', string='Award', required=True, index=True, ondelete='cascade')
    survey_id = fields.Many2one('bhu.survey', string='Survey / सर्वेक्षण', required=True, index=True, ondelete='cascade')

    @api.model
    def _auto_init(self):
        res = super()._auto_init()
        self._cr.execute(
            """
            CREATE INDEX IF NOT EXISTS bhu_s23_award_survey_line_award_survey_idx
            ON bhu_section23_award_survey_line (award_id, survey_id)
            """
        )
        return res

    # Survey information (readonly, from survey)
    khasra_number = fields.Char(
        string='Khasra Number / खसरा संख्या',
        related='survey_id.khasra_number', store=True, readonly=True,
    )
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
                                       help='Check if khasra is within distance from main road (50m rural, 30m urban)')
    distance_from_main_road = fields.Float(
        string='Distance (m)', related='survey_id.distance_from_main_road', readonly=True,
    )
    irrigation_type = fields.Selection(
        related='survey_id.irrigation_type', string='Irrigation', readonly=True,
    )
    has_traded_land = fields.Selection(
        related='survey_id.has_traded_land', string='Diverted', readonly=True,
    )
    village_name = fields.Char(
        string='Village', related='award_id.village_id.name', readonly=True,
    )

    # --- computed display columns (same engine as land compensation data) ----
    road_type_display = fields.Char(
        string='Road', compute='_compute_line_display_amounts', store=True,
    )
    land_award_amount = fields.Monetary(
        string='Land Award', currency_field='currency_id',
        compute='_compute_line_display_amounts', store=True,
    )
    solatium_display = fields.Monetary(
        string='Solatium', currency_field='currency_id',
        compute='_compute_line_display_amounts', store=True,
    )
    interest_display = fields.Monetary(
        string='Interest', currency_field='currency_id',
        compute='_compute_line_display_amounts', store=True,
    )
    base_rate_display = fields.Monetary(
        string='Base Rate', currency_field='currency_id',
        compute='_compute_line_display_amounts', store=True,
    )

    @api.depends(
        'rate_per_hectare', 'guide_line_master_rate', 'acquired_area',
        'distance_from_main_road', 'survey_id.survey_type',
        'award_id.award_date', 'award_id.project_id', 'award_id.village_id',
        'is_within_distance', 'land_type',
    )
    def _compute_line_display_amounts(self):
        for line in self:
            dist = line.distance_from_main_road or 0.0
            survey_type = line.survey_id.survey_type if line.survey_id else 'rural'
            threshold = 50.0 if survey_type == 'rural' else 30.0
            line.road_type_display = 'MR' if dist <= threshold else 'BMR'

            # Same as column "guide line" / rate master: main road vs other, village only
            line.base_rate_display = line.guide_line_master_rate or 0.0

            rate = line.rate_per_hectare or 0.0
            area = line.acquired_area or 0.0
            land_award = area * rate
            line.land_award_amount = land_award
            line.solatium_display = land_award  # 100%
            interest = 0.0
            if line.award_id:
                try:
                    interest, _ = line.award_id._calculate_interest_on_basic(land_award * 2.0)
                except Exception:
                    interest = 0.0
            line.interest_display = interest

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('land_type'):
                vals['land_type'] = 'village'
        return super().create(vals_list)

    def action_open_survey_for_land_edit(self):
        """Open mini popup wizard to edit 4 land inputs (distance/road/irrigation/diverted)."""
        self.ensure_one()
        if not self.survey_id:
            raise ValidationError(_('No survey linked on this line.'))
        return {
            'name': _('Edit land inputs / भूमि इनपुट संपादित करें'),
            'type': 'ir.actions.act_window',
            'res_model': 'bhu.s23.land.edit.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_survey_line_id': self.id},
        }

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
        if 'land_type' in vals and not vals.get('land_type'):
            vals = dict(vals)
            vals['land_type'] = 'village'
        result = super().write(vals)
        for line in self:
            if line.survey_id and ('land_type' in vals or 'is_within_distance' in vals):
                before_land_type = line.survey_id.land_type_for_award
                before_within = line.survey_id.is_within_distance_for_award
                line.survey_id.write({
                    'land_type_for_award': line.land_type,
                    'is_within_distance_for_award': line.is_within_distance,
                })
                changed_parts = []
                if (before_land_type or '') != (line.land_type or ''):
                    changed_parts.append(
                        _('Type for award: %(old)s -> %(new)s') % {
                            'old': before_land_type or '-',
                            'new': line.land_type or '-',
                        }
                    )
                if bool(before_within) != bool(line.is_within_distance):
                    changed_parts.append(
                        _('Within distance: %(old)s -> %(new)s') % {
                            'old': _('Yes') if before_within else _('No'),
                            'new': _('Yes') if line.is_within_distance else _('No'),
                        }
                    )
                if changed_parts:
                    line.survey_id.message_post(
                        body=_(
                            'Survey updated from Section 23 Award by <b>%(user)s</b> (award: %(award)s, khasra: %(khasra)s).<br/>%(changes)s'
                        ) % {
                            'user': self.env.user.name,
                            'award': line.award_id.name if line.award_id else '-',
                            'khasra': line.survey_id.khasra_number or '-',
                            'changes': '<br/>'.join(changed_parts),
                        }
                    )
        return result

    # Master guideline = village rate book: main road vs other road only (no irrigation / diverted).
    guide_line_master_rate = fields.Monetary(
        string='Guide Line Rate (Master) / गाइड लाइन दर (मास्टर)',
        currency_field='currency_id',
        compute='_compute_rate_per_hectare', store=True,
        help='Per-hectare rate from the active land rate master for this village: '
        'main road vs other road only.',
    )
    # Computed effective rate: master × irrigation × diverted (used for basic value / compensation).
    rate_per_hectare = fields.Monetary(
        string='Rate per Hectare / हेक्टेयर दर',
        currency_field='currency_id',
        compute='_compute_rate_per_hectare', store=True,
        help='Effective rate per hectare (master + irrigation and diverted rules) for amount calculation.',
    )

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.ref('base.INR'))

    @api.depends('land_type', 'is_within_distance', 'award_id.village_id',
                 'survey_id.irrigation_type', 'survey_id.has_traded_land',
                 'distance_from_main_road', 'survey_id.survey_type')
    def _compute_rate_per_hectare(self):
        """Master rate = rate book (village, main road vs not). Effective = master × irrigation × diverted."""
        for line in self:
            line.guide_line_master_rate = 0.0
            line.rate_per_hectare = 0.0
            if not (line.award_id and line.award_id.village_id and line.land_type):
                continue
            rate_master = self.env['bhu.rate.master'].search([
                ('village_id', '=', line.award_id.village_id.id),
                ('state', '=', 'active'),
            ], limit=1, order='effective_from DESC')
            if not rate_master:
                continue

            dist = line.distance_from_main_road or 0.0
            s_type = line.survey_id.survey_type if line.survey_id else 'rural'
            threshold = 50.0 if s_type == 'rural' else 30.0
            within = dist <= threshold

            base_rate = (rate_master.main_road_rate_hectare if within
                         else rate_master.other_road_rate_hectare) or 0.0
            line.guide_line_master_rate = base_rate

            # Irrigation adjustment — for compensation only (+20% irrigated, -20% unirrigated)
            irrigation_type = line.survey_id.irrigation_type if line.survey_id else False
            if irrigation_type == 'irrigated':
                rate = base_rate * 1.2
            elif irrigation_type in ['non_irrigated', 'unirrigated']:
                rate = base_rate * 0.8
            else:
                rate = base_rate

            if line.survey_id and line.survey_id.has_traded_land == 'yes' and within:
                rate = rate * 1.25

            line.rate_per_hectare = rate

    @api.onchange('survey_id')
    def _onchange_survey_id(self):
        """Sync type/distance from survey when khasra (survey) changes; khasra text is related."""
        for line in self:
            if line.survey_id:
                # Load existing values from survey if available
                if not line.land_type and line.survey_id.land_type_for_award:
                    line.land_type = line.survey_id.land_type_for_award
                distance = line.survey_id.distance_from_main_road or 0.0
                threshold = 50.0 if line.survey_id.survey_type == 'rural' else 30.0
                line.is_within_distance = distance <= threshold

    @api.model_create_multi
    def create(self, vals_list):
        """Sync land type and distance from survey when creating"""
        for vals in vals_list:
            if 'survey_id' in vals:
                survey = self.env['bhu.survey'].browse(vals['survey_id'])
                if survey:
                    # Also sync existing values from survey if not provided
                    if 'land_type' not in vals and survey.land_type_for_award:
                        vals['land_type'] = survey.land_type_for_award
                    if 'is_within_distance' not in vals:
                        distance = survey.distance_from_main_road or 0.0
                        threshold = 50.0 if survey.survey_type == 'rural' else 30.0
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
