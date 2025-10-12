from odoo import models, fields, api

class BhuState(models.Model):
    _name = 'bhu.state'
    _description = 'State'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True)


class BhuDistrict(models.Model):
    _name = 'bhu.district'
    _description = 'District'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True)
    state_id = fields.Many2one('bhu.state', string='State', required=True)


class BhuVillage(models.Model):
    _name = 'bhu.village'
    _description = 'Village'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    name = fields.Char(string='Name', required=True)
    district_id = fields.Many2one('bhu.district', string='District', required=True)
    state_id = fields.Many2one('bhu.state', string='State', required=True)

    @api.onchange('district_id')
    def _onchange_district_id(self):
        if self.district_id:
            self.state_id = self.district_id.state_id
        else:
            self.state_id = False
