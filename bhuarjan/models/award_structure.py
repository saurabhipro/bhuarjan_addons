# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AwardStructureDetails(models.Model):
    _name = 'bhu.award.structure.details'
    _description = 'Award Structure Line'
    _order = 'id desc'

    survey_id = fields.Many2one(
        'bhu.survey',
        string='Khasra / खसरा',
        required=True,
        ondelete='cascade'
    )
    simulator_id = fields.Many2one(
        'bhu.award.simulator',
        string='Award Simulator',
        ondelete='set null'
    )
    award_id = fields.Many2one(
        'bhu.section23.award',
        string='Section 23 Award',
        ondelete='set null'
    )

    project_id = fields.Many2one(
        'bhu.project',
        string='Project',
        related='survey_id.project_id',
        store=True,
        readonly=True
    )
    village_id = fields.Many2one(
        'bhu.village',
        string='Village',
        related='survey_id.village_id',
        store=True,
        readonly=True
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

    asset_count = fields.Integer(string='Asset Count', default=1)
    area_sqm = fields.Float(string='Area (Sq. Meter) / क्षेत्रफल (वर्ग मीटर)', digits=(10, 2))
    market_rate_per_sqm = fields.Float(string='Market Rate per Sq. Meter (₹) / बाजार मूल्य दर (प्रति वर्ग मीटर)', digits=(16, 2))

    asset_value = fields.Float(
        string='Asset Value (₹) / परिसम्पत्ति की कीमत',
        digits=(16, 2),
        compute='_compute_line_total',
        store=True
    )
    line_total = fields.Float(
        string='Line Total (₹) / पंक्ति कुल',
        digits=(16, 2),
        compute='_compute_line_total',
        store=True
    )

    @api.depends('asset_count', 'market_rate_per_sqm')
    def _compute_line_total(self):
        for line in self:
            # Unified UX: value is always Count x Rate.
            computed_value = (line.asset_count or 0) * (line.market_rate_per_sqm or 0.0)
            line.asset_value = computed_value
            line.line_total = computed_value

    @api.onchange('structure_type')
    def _onchange_structure_type_default_rate(self):
        """Set standard base rate for well entries."""
        for line in self:
            if line.structure_type == 'well' and not line.market_rate_per_sqm:
                line.market_rate_per_sqm = 90000.0

    def get_structure_type_label(self):
        self.ensure_one()
        base = dict(self._fields['structure_type'].selection).get(self.structure_type, self.structure_type or 'Other')
        if self.construction_type:
            ctype = dict(self._fields['construction_type'].selection).get(self.construction_type, self.construction_type)
            return f"{base} ({ctype})"
        return base
