
# import logging
# from odoo import api, SUPERUSER_ID

# _logger = logging.getLogger(__name__)

# def run(env):
#     """
#     Script to inspect and fix critical system parameters and clear potential old data from the bad module.
#     """
#     Param = env['ir.config_parameter'].sudo()

#     # 1. Check and potentially fix web.base.url
#     base_url = Param.get_param('web.base.url')
#     _logger.info(f"Current web.base.url: {base_url}")
    
#     # If base_url looks broken (e.g. contains double slashes or wrong protocol), fix it
#     # For now, we just ensure it doesn't end with slash, which my hook already does.
#     # But let's check if it's set to something wildly incorrect like 'odoo' or 'apps'
#     if base_url and (base_url == 'odoo' or base_url == 'apps' or '://' not in base_url):
#         _logger.warning("web.base.url seems invalid! Resetting to empty so Odoo re-detects it.")
#         Param.set_param('web.base.url', '') 
    
#     # 2. DELETE web.base.sorturl if it exists
#     # This was the parameter used by the deleted module to rewrite URLs.
#     # If it exists, it might be confusing someone (though code is gone)
#     sort_url = Param.get_param('web.base.sorturl')
#     if sort_url:
#         _logger.warning(f"Found web.base.sorturl: {sort_url}. Deleting it.")
#         # Find the record and unlink it
#         param_record = Param.search([('key', '=', 'web.base.sorturl')])
#         if param_record:
#             param_record.unlink()
#             _logger.info("Deleted web.base.sorturl parameter.")
            
#     # 3. Clear caches and regenerate assets
#     _logger.info("Clearing caches and regenerating assets...")
#     env.registry.clear_cache()
#     env['ir.attachment'].regenerate_assets_bundles()
#     _logger.info("Assets regenerated.")

#     # 4. Check for any leftover ir.ui.view or ir.ui.menu or action related to the deleted module
#     # The module name was technically just 'bhuarjan', but the files were specific.
#     # We look for xmlids
    
#     # Remove any lingering views if they exist (though file deletion should have removed them on update)
#     deprecated_views = env['ir.ui.view'].search([
#         ('name', 'in', ['remove.odoo.url.view', 'bhuarjan.settings.inherit']) # Example names
#     ])
#     if deprecated_views:
#          _logger.info(f"Found {len(deprecated_views)} deprecated views. Unlinking.")
#          deprecated_views.unlink()
         
#     return "Check completed. See logs."
