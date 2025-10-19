from odoo import models, fields, api, _

class BhuCircle(models.Model):
    _name = 'bhu.circle'
    _description = 'Circle'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _get_state_domain(self):
        state_ids = self.env['bhu.district'].search([]).mapped('state_id.id')    
        return [('id', 'in', state_ids)]

    state_id = fields.Many2one('res.country.state', string='State', required=True, domain=lambda self: self._get_state_domain())
    district_id = fields.Many2one('bhu.district', string='District / जिला', required=True)
    sub_division_id = fields.Many2one('bhu.sub.division', string='Sub Division / उपभाग', required=True)
    tehsil_id = fields.Many2one('bhu.tehsil', string='Tehsil / तहसील', required=True)
    name = fields.Char(string='Circle', required=True)
