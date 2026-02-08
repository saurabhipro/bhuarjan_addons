# -*- coding: utf-8 -*-

import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Hook to invalidate all sessions after module update or server restart and set project_id for sample data"""
    try:
        _logger.warning("=== POST_INIT_HOOK: Module update/restart detected ===")
        
        # Set project_id for sample data records that don't have it set
        try:
            # Find project with code PROJ01
            project = env['bhu.project'].search([('code', '=', 'PROJ01')], limit=1)
            if project:
                # Update Expert Committee Reports
                expert_reports = env['bhu.expert.committee.report'].search([
                    ('name', 'like', 'Expert Committee Report -'),
                    ('project_id', '=', False)
                ])
                if expert_reports:
                    expert_reports.write({'project_id': project.id})
                    _logger.info("POST_INIT_HOOK: Updated %d Expert Committee Reports with project PROJ01", len(expert_reports))
                
                # Update Section 4 Notifications
                section4_notifications = env['bhu.section4.notification'].search([
                    ('name', 'like', 'Section 4 Notification -'),
                    ('project_id', '=', False)
                ])
                if section4_notifications:
                    section4_notifications.write({'project_id': project.id})
                    _logger.info("POST_INIT_HOOK: Updated %d Section 4 Notifications with project PROJ01", len(section4_notifications))
            else:
                _logger.warning("POST_INIT_HOOK: Project with code PROJ01 not found, skipping sample data update")
        except Exception as e:
            _logger.error("POST_INIT_HOOK: Error updating sample data project_id: %s", e, exc_info=True)
        
        # Session invalidation and PID tracking removed as per user request.

        
        # FIX: Ensure web.base.url is clean and valid.
        param_obj = env['ir.config_parameter'].sudo()
        base_url = param_obj.get_param('web.base.url')

        # 1. Remove trailing slash
        if base_url and base_url.endswith('/'):
            clean_url = base_url.rstrip('/')
            param_obj.set_param('web.base.url', clean_url)
            _logger.info("POST_INIT_HOOK: Removed trailing slash from web.base.url: %s -> %s", base_url, clean_url)

        # 2. Reset if it looks completely broken (e.g. 'odoo', 'apps', or no protocol)
        if base_url and ('://' not in base_url or base_url in ['odoo', 'apps']):
             _logger.warning("POST_INIT_HOOK: web.base.url detected as invalid (%s). Resetting to empty to force regeneration.", base_url)
             param_obj.set_param('web.base.url', '') 

        # 3. Remove web.base.sorturl (from deleted module)
        sort_url_param = param_obj.search([('key', '=', 'web.base.sorturl')])
        if sort_url_param:
            _logger.info("POST_INIT_HOOK: Removing deprecated web.base.sorturl parameter.")
            sort_url_param.unlink()
            
        # 4. Regenerate assets to ensure no old JS code is cached
        _logger.info("POST_INIT_HOOK: Regenerating assets bundles...")
        env['ir.attachment'].regenerate_assets_bundles()
        env.registry.clear_cache()

    except Exception as e:
        _logger.error("POST_INIT_HOOK: Error in post_init_hook: %s", e, exc_info=True)

