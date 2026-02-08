
import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

def post_init_hook(env):
    """
    Hook to clean up broken URL configuration one last time.
    """
    try:
        _logger.info("============== STARTING URL CLEANUP HOOK ==============")
        
        # FIX: Ensure web.base.url is clean and valid.
        param_obj = env['ir.config_parameter'].sudo()
        base_url = param_obj.get_param('web.base.url')

        # 1. Remove trailing slash
        if base_url and base_url.endswith('/'):
            clean_url = base_url.rstrip('/')
            param_obj.set_param('web.base.url', clean_url)
            _logger.info("FIXED: Removed trailing slash from web.base.url: %s -> %s", base_url, clean_url)

        # 2. Reset if it looks completely broken (e.g. 'odoo', 'apps', or no protocol)
        if base_url and ('://' not in base_url or base_url in ['odoo', 'apps']):
             _logger.warning("FIXED: web.base.url detected as invalid (%s). Resetting to empty to force regeneration.", base_url)
             param_obj.set_param('web.base.url', '') 

        # 3. Remove web.base.sorturl (from deleted module)
        sort_url_param = param_obj.search([('key', '=', 'web.base.sorturl')])
        if sort_url_param:
            _logger.info("FIXED: Removing deprecated web.base.sorturl parameter.")
            sort_url_param.unlink()
            
        # 4. Regenerate assets to ensure no old JS code is cached
        _logger.info("FIXED: Regenerating assets bundles...")
        env['ir.attachment'].regenerate_assets_bundles()
        env.registry.clear_cache()
        
        _logger.info("============== URL CLEANUP COMPLETED ==============")

    except Exception as e:
        _logger.error("Error in post_init_hook cleanup: %s", e, exc_info=True)
