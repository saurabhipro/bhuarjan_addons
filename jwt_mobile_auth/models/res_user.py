import datetime
from odoo import models, fields

class ResUsers(models.Model):
    _inherit = "res.users"

    mobile = fields.Char(string="Mobile")
