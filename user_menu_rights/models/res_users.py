# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    user_menu_access_ids = fields.Many2many('res.users.menu.access', string="Show Access Menu")
    show_menu_access_ids = fields.Many2many('ir.ui.menu', 'ir_ui_show_menu_rel', 'uid', 'menu_id',
                                            string='Access Menu Show')
    parent_show_menu_access_ids = fields.Many2many('ir.ui.menu', 'ir_ui_parent_show_menu_rel', 'uid', 'menu_id',
                                                   string='Show Access Menus')

    @api.onchange('user_menu_access_ids')
    def _onchange_user_menu_access_ids(self):
        if self.user_menu_access_ids:
            menu_ids = self.user_menu_access_ids.mapped('menu_ids')
            self.show_menu_access_ids = [(6, 0, menu_ids.ids)]
        else:
            self.show_menu_access_ids = [(6, 0, [])]

    @api.onchange('parent_show_menu_access_ids')
    def _onchange_parent_show_menu_access_ids(self):
        if self.parent_show_menu_access_ids:
            IrMenu = self.env['ir.ui.menu']
            for menu in self.parent_show_menu_access_ids:
                IrMenu |= menu.get_child_menus()
            self.show_menu_access_ids = [(6, 0, IrMenu.ids)]
        else:
            self.show_menu_access_ids = [(6, 0, [self.env.ref('mail.menu_root_discuss').id])]

    @api.model
    def default_get(self, fields_lst):
        res = super(ResUsers, self).default_get(fields_lst)
        res['show_menu_access_ids'] = [(6, 0, [self.env.ref('mail.menu_root_discuss').id])]
        return res

    @classmethod
    def authenticate(self, db, login, password):
        res = super(ResUsers, self).authenticate(db, login, password)
        self.clear_caches()
        return res


class ResUsersMenuAccess(models.Model):
    _name = 'res.users.menu.access'
    _description = "Res Users Menu Access"

    name = fields.Char(string="Access Name")
    menu_ids = fields.Many2many('ir.ui.menu', 'user_access_menu_rel', 'user_menu_access_id', 'menu_id',
                                string='Menus')
    def write(self, vals):
        record = super(ResUsersMenuAccess, self).write(vals)
        user_ids = self.env['res.users'].sudo().search([('user_menu_access_ids', 'in', self.ids)])
        for user_id in user_ids:
            if user_id.user_menu_access_ids:
                menu_ids = user_id.user_menu_access_ids.mapped('menu_ids')
                user_id.show_menu_access_ids = [(6, 0, menu_ids.ids)]
            else:
                user_id.show_menu_access_ids = [(6, 0, [])]

