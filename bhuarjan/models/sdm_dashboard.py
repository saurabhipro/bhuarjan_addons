from odoo import models, fields, api
from odoo.exceptions import ValidationError

class BhuDashboard(models.Model):
    _name = "bhu.dashboard"
    _description = 'Bhuarjan Dashboard'


    @api.model
    def get_all_projects(self):
        print("\n\n function is working fine")
        if self.env.user.has_group('bhuarjan.group_bhuarjan_sdm'):
            projects = self.env['bhu.project'].search([
                ('sdm_ids', 'in', [self.env.user.id])
            ])
        else:
            projects = self.env['bhu.project'].search([])

        return [{
            "id": p.id,
            "name": p.name
        } for p in projects]