# -*- coding: utf-8 -*-
##############################################################################
#
#    In2IT Technologies Pvt. Ltd
#    Copyright (C) 2025 (https://www.in2ittech.com)
#
##############################################################################
from . import controllers
from . import models
from . import wizard
import logging

_logger = logging.getLogger(__name__)

def uninstall_hook(env):
    try:
        dashboard_menu = env['dashboard.menu'].search([])
        for menu in dashboard_menu:
            name = menu.name
            parent_menu = menu.menu_id
            menu_ids = env['ir.ui.menu'].search([('name','=',name),('parent_id','=',parent_menu.id)])
            _logger.info(f"Menu deleted : {menu_ids}")
            if menu_ids:
                menu_ids.unlink()
    except Exception as e:
        _logger.error(f"Error in uninstall_hook: {e}")
                
      
