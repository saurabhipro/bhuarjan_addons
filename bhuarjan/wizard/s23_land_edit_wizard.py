# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class S23LandEditWizard(models.TransientModel):
    _name = 'bhu.s23.land.edit.wizard'
    _description = 'Section 23 – Edit land inputs (distance / irrigation / diverted)'

    survey_line_id = fields.Many2one(
        'bhu.section23.award.survey.line',
        string='Survey line',
        required=True,
        ondelete='cascade',
    )
    khasra_display = fields.Char(string='Khasra / खसरा', readonly=True)
    survey_type = fields.Selection(
        related='survey_line_id.survey_id.survey_type',
        string='Survey type',
        readonly=True,
    )
    distance_help = fields.Char(
        string='MR/BMR threshold',
        compute='_compute_distance_help',
    )

    distance_from_main_road = fields.Float(
        string='Distance from main road (m) / मुख्य मार्ग से दूरी (मी.)',
        digits=(10, 2),
    )
    road_type = fields.Selection(
        [
            ('mr',  'MR – main road rate / मुख्य मार्ग दर'),
            ('mbr', 'BMR – beyond main road / मार्ग से परे'),
        ],
        string='Road rate band / मार्ग दर',
        required=True,
    )
    irrigation_type = fields.Selection(
        [
            ('irrigated',   'Irrigated / सिंचित'),
            ('unirrigated', 'Unirrigated / असिंचित'),
        ],
        string='Irrigation / सिंचाई',
    )
    has_traded_land = fields.Selection(
        [
            ('yes', 'Yes – diverted (traded) / हाँ – विचलित'),
            ('no',  'No / नहीं'),
        ],
        string='Diverted land / विचलित भूमि',
    )

    # ------------------------------------------------------------------ helpers
    def _threshold(self):
        st = (
            self.survey_line_id.survey_id.survey_type
            if self.survey_line_id and self.survey_line_id.survey_id
            else 'rural'
        )
        return 50.0 if st == 'rural' else 20.0

    @api.depends('survey_line_id', 'survey_type')
    def _compute_distance_help(self):
        for wiz in self:
            st = (
                wiz.survey_line_id.survey_id.survey_type
                if wiz.survey_line_id and wiz.survey_line_id.survey_id
                else False
            )
            th   = 50.0 if st == 'rural' else 20.0 if st == 'urban' else 50.0
            kind = 'Rural / ग्रामीण' if st == 'rural' else 'Urban / शहरी' if st == 'urban' else '—'
            wiz.distance_help = _(
                'MR if ≤ %(th)s m  |  BMR if > %(th)s m  (%(kind)s)'
            ) % {'th': int(th), 'kind': kind}

    # ------------------------------------------------------------------ onchanges
    @api.onchange('distance_from_main_road')
    def _onchange_distance_auto_road_type(self):
        th = self._threshold()
        d  = self.distance_from_main_road or 0.0
        self.road_type = 'mr' if d <= th else 'mbr'

    @api.onchange('road_type')
    def _onchange_road_type_adjust_distance(self):
        th = self._threshold()
        d  = self.distance_from_main_road or 0.0
        if self.road_type == 'mr' and d > th:
            self.distance_from_main_road = th
        elif self.road_type == 'mbr' and d <= th:
            self.distance_from_main_road = th + 1.0

    # ------------------------------------------------------------------ default_get
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        line_id = self.env.context.get('default_survey_line_id')
        if not line_id:
            return res
        line = self.env['bhu.section23.award.survey.line'].browse(line_id)
        if not (line.exists() and line.survey_id):
            return res
        s   = line.survey_id
        d   = s.distance_from_main_road or 0.0
        th  = 50.0 if s.survey_type == 'rural' else 20.0
        res.update({
            'survey_line_id':          line.id,
            'khasra_display':          s.khasra_number or '',
            'distance_from_main_road': d,
            'road_type':               'mr' if d <= th else 'mbr',
            'irrigation_type':         s.irrigation_type or 'unirrigated',
            'has_traded_land':         s.has_traded_land or 'no',
        })
        return res

    # ------------------------------------------------------------------ apply
    def action_apply(self):
        self.ensure_one()
        line   = self.survey_line_id
        survey = line.survey_id if line else False
        if not survey:
            raise UserError(_('No survey linked on this line.'))

        th = 50.0 if survey.survey_type == 'rural' else 20.0
        d  = self.distance_from_main_road or 0.0
        if self.road_type == 'mr':
            d = min(d, th)
        else:
            if d <= th:
                d = th + 1.0

        survey.write({
            'distance_from_main_road': d,
            'irrigation_type':         self.irrigation_type,
            'has_traded_land':         self.has_traded_land,
        })
        # Recompute the award line rate so it reflects immediately
        line._compute_rate_per_hectare()
        # Also refresh award totals
        if line.award_id:
            line.award_id._compute_s23_section_previews()
            line.award_id._compute_s23_premium_totals()

        return {'type': 'ir.actions.act_window_close'}
