# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class S23TreeEditWizard(models.TransientModel):
    _name = 'bhu.s23.tree.edit.wizard'
    _description = 'Section 23 - Edit tree inputs'

    survey_line_id = fields.Many2one(
        'bhu.section23.award.survey.line',
        string='Survey line',
        required=True,
        ondelete='cascade',
    )
    survey_id = fields.Many2one(
        'bhu.survey',
        string='Survey',
        related='survey_line_id.survey_id',
        readonly=True,
    )
    khasra_display = fields.Char(string='Khasra / खसरा', readonly=True)
    tree_line_ids = fields.One2many(
        'bhu.s23.tree.edit.wizard.line',
        'wizard_id',
        string='Tree rows',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        line_id = self.env.context.get('default_survey_line_id')
        if not line_id:
            return res
        line = self.env['bhu.section23.award.survey.line'].browse(line_id)
        if not (line.exists() and line.survey_id):
            return res
        commands = []
        for tline in line.survey_id.tree_line_ids:
            commands.append((0, 0, {
                'tree_master_id': tline.tree_master_id.id,
                'development_stage': tline.development_stage,
                'girth_cm': tline.girth_cm,
                'quantity': tline.quantity,
            }))
        res.update({
            'survey_line_id': line.id,
            'khasra_display': line.survey_id.khasra_number or '',
            'tree_line_ids': commands,
        })
        return res

    def action_apply(self):
        self.ensure_one()
        survey = self.survey_id
        if not survey:
            raise UserError(_('No survey linked on this line.'))
        if any((line.quantity or 0) <= 0 for line in self.tree_line_ids):
            raise UserError(_('Tree quantity must be greater than zero for all rows.'))

        commands = [(5, 0, 0)]
        for line in self.tree_line_ids:
            commands.append((0, 0, {
                'tree_master_id': line.tree_master_id.id,
                'development_stage': line.development_stage,
                'girth_cm': line.girth_cm or 0.0,
                'quantity': int(line.quantity or 0),
            }))
        survey.write({'tree_line_ids': commands})

        if self.survey_line_id and self.survey_line_id.award_id:
            self.survey_line_id.award_id.message_post(
                body=_(
                    'Tree details updated from Section 23 popup by <b>%(user)s</b> '
                    'for khasra <b>%(khasra)s</b>.'
                ) % {
                    'user': self.env.user.name,
                    'khasra': survey.khasra_number or '-',
                }
            )
        return {'type': 'ir.actions.client', 'tag': 'reload'}


class S23TreeEditWizardLine(models.TransientModel):
    _name = 'bhu.s23.tree.edit.wizard.line'
    _description = 'Section 23 - Edit tree row'

    wizard_id = fields.Many2one(
        'bhu.s23.tree.edit.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    tree_master_id = fields.Many2one(
        'bhu.tree.master',
        string='Tree / वृक्ष',
        required=True,
    )
    tree_type = fields.Selection(
        related='tree_master_id.tree_type',
        string='Tree Type',
        readonly=True,
    )
    development_stage = fields.Selection([
        ('undeveloped', 'Undeveloped / अविकसित'),
        ('semi_developed', 'Semi-developed / अर्ध-विकसित'),
        ('fully_developed', 'Fully Developed / पूर्ण विकसित'),
    ], string='Development Stage / विकास स्तर', default='undeveloped')
    girth_cm = fields.Float(string='Girth (cm) / छाती (से.मी.)', digits=(10, 2))
    quantity = fields.Integer(string='Quantity / मात्रा', required=True, default=1)
