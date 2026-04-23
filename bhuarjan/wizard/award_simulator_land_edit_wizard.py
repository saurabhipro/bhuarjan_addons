# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AwardSimulatorLandEditWizard(models.TransientModel):
    _name = 'bhu.award.simulator.land.edit.wizard'
    _description = 'Edit land line inputs (survey-backed)'

    line_id = fields.Many2one(
        'bhu.award.simulator.land.line',
        string='Land line',
        required=True,
        ondelete='cascade',
    )
    khasra_display = fields.Char(string='Khasra', readonly=True)
    survey_type = fields.Selection(
        related='line_id.survey_id.survey_type',
        string='Survey type',
        readonly=True,
    )
    distance_help = fields.Char(
        string='Threshold',
        compute='_compute_distance_help',
    )
    distance_from_main_road = fields.Float(
        string='Distance from main road (m) / मुख्य मार्ग से दूरी (मी.)',
        digits=(10, 2),
    )
    road_type = fields.Selection(
        [
            ('mr', 'MR – main road rate / मुख्य मार्ग दर'),
            ('mbr', 'BMR – beyond main road / मार्ग से परे'),
        ],
        string='Road rate band / मार्ग दर',
        required=True,
        help='MR applies when distance is within the rural/urban threshold; BMR when beyond. '
             'Saving adjusts the distance value to match this band if needed.',
    )
    irrigation_type = fields.Selection(
        [
            ('irrigated', 'Irrigated (sanchit) / सिंचित'),
            ('unirrigated', 'Unirrigated / असिंचित'),
        ],
        string='Irrigation / सिंचाई',
    )
    has_traded_land = fields.Selection(
        [
            ('yes', 'Yes – diverted (traded) / हाँ – विचलित'),
            ('no', 'No / नहीं'),
        ],
        string='Diverted (traded) land / विचलित भूमि',
    )

    def _threshold(self):
        """Return the MR/BMR distance threshold for this wizard's survey type."""
        st = self.line_id.survey_id.survey_type if self.line_id and self.line_id.survey_id else False
        return 50.0 if st == 'rural' else 20.0

    @api.depends('line_id', 'survey_type')
    def _compute_distance_help(self):
        for wiz in self:
            st = wiz.line_id.survey_id.survey_type if wiz.line_id and wiz.line_id.survey_id else False
            th = 50.0 if st == 'rural' else 20.0 if st == 'urban' else 50.0
            kind = 'Rural / ग्रामीण' if st == 'rural' else 'Urban / शहरी' if st == 'urban' else '—'
            wiz.distance_help = _('MR if ≤ %(th)s m  |  BMR if > %(th)s m  (%(kind)s)') % {'th': int(th), 'kind': kind}

    @api.onchange('distance_from_main_road')
    def _onchange_distance_auto_road_type(self):
        """Auto-select MR / BMR whenever the distance field changes."""
        th = self._threshold()
        d = self.distance_from_main_road or 0.0
        self.road_type = 'mr' if d <= th else 'mbr'

    @api.onchange('road_type')
    def _onchange_road_type_adjust_distance(self):
        """If user manually flips the band, nudge the distance to a valid value
        so it stays consistent with the chosen band."""
        th = self._threshold()
        d = self.distance_from_main_road or 0.0
        if self.road_type == 'mr' and d > th:
            self.distance_from_main_road = th
        elif self.road_type == 'mbr' and d <= th:
            self.distance_from_main_road = th + 1.0

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        line = self.env['bhu.award.simulator.land.line']
        if self.env.context.get('default_line_id'):
            line = self.env['bhu.award.simulator.land.line'].browse(self.env.context['default_line_id'])
        if line and line.exists() and line.survey_id:
            s = line.survey_id
            res['line_id'] = line.id
            res['khasra_display'] = s.khasra_number or ''
            d = s.distance_from_main_road or 0.0
            res['distance_from_main_road'] = d
            res['irrigation_type'] = s.irrigation_type or 'irrigated'
            res['has_traded_land'] = s.has_traded_land or 'no'
            th = 50.0 if s.survey_type == 'rural' else 20.0
            res['road_type'] = 'mr' if d <= th else 'mbr'
        return res

    def action_apply(self):
        self.ensure_one()
        line = self.line_id
        survey = line.survey_id
        if not survey:
            raise UserError(_('No survey is linked to this land line.'))
        th = 50.0 if survey.survey_type == 'rural' else 20.0
        d = self.distance_from_main_road or 0.0
        if self.road_type == 'mr':
            d = min(d, th)
        else:
            if d <= th:
                d = th + 1.0
        try:
            survey.write({
                'distance_from_main_road': d,
                'irrigation_type': self.irrigation_type,
                'has_traded_land': self.has_traded_land,
            })
        except Exception as e:
            raise UserError(
                _('Could not update the survey. Check your access rights or open the survey form. %s') % (str(e),)
            ) from e
        line._compute_amounts()
        if line.simulator_id:
            line.simulator_id._compute_land_award()
            line.simulator_id._compute_grand_total()
        return {'type': 'ir.actions.act_window_close'}
