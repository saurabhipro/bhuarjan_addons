# -*- coding: utf-8 -*-

from odoo import models, api, tools


class Menu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    @tools.ormcache("frozenset(self.env.user.show_menu_access_ids.ids)", "debug")
    def _visible_menu_ids(self, debug=False):
        """Return the ids of the menu items visible to the user."""
        self.clear_caches()
        visible = super()._visible_menu_ids(debug=debug)
        if not self.env.user.has_group('base.group_system') and self.env.user.user_menu_access_ids:
            context = {'ir.ui.menu.full_list': True}
            menus = self.env.user.show_menu_access_ids

            groups = self.env.user.groups_id
            if not debug:
                groups = groups - self.env.ref('base.group_no_one')
            # first discard all menus with groups the user does not have
            menus = menus.filtered(
                lambda menu: not menu.groups_id or menu.groups_id & groups)

            # take apart menus that have an action
            action_menus = menus.filtered(lambda m: m.action and m.action.exists())
            folder_menus = menus - action_menus
            visible = self.browse()

            # process action menus, check whether their action is allowed
            access = self.env['ir.model.access']
            MODEL_GETTER = {
                'ir.actions.act_window': lambda action: action.res_model,
                'ir.actions.report': lambda action: action.model,
                'ir.actions.server': lambda action: action.model_id.model,
            }
            for menu in action_menus:
                get_model = MODEL_GETTER.get(menu.action._name)
                if not get_model or not get_model(menu.action) or access.check(get_model(menu.action), 'read', False):
                    # make menu visible, and its folder ancestors, too
                    visible += menu
                    menu = menu.parent_id
                    while menu and menu in folder_menus and menu not in visible:
                        visible += menu
                        menu = menu.parent_id

            return set(visible.ids)
        return visible

    def get_child_menus(self):
        Menus = self
        if self.child_id:
            for menu in self.child_id:
                Menus |= menu.get_child_menus()
            return Menus
        else:
            Menus |= self.child_id
            return Menus
