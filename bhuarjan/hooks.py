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
        
        # Delete all active sessions using ORM
        try:
            Session = env.get('ir.session')
            if Session:
                # Use env directly since it's already superuser context in hook
                sessions = Session.search([])
                session_count = len(sessions)
                if session_count > 0:
                    sessions.unlink()
                    _logger.warning("POST_INIT_HOOK: All %d sessions invalidated via ORM on module update", session_count)
                else:
                    _logger.info("POST_INIT_HOOK: No active sessions found")
            else:
                _logger.warning("POST_INIT_HOOK: ir.session model not found, trying SQL")
                env.cr.execute("DELETE FROM ir_session")
                env.cr.commit()
                _logger.warning("POST_INIT_HOOK: Sessions deleted via SQL")
        except Exception as e:
            _logger.error("POST_INIT_HOOK: Could not invalidate sessions via ORM: %s", e)
            # Try fallback SQL
            try:
                env.cr.execute("DELETE FROM ir_session")
                env.cr.commit()
                _logger.warning("POST_INIT_HOOK: Sessions deleted via SQL fallback")
            except Exception as sql_err:
                _logger.error("POST_INIT_HOOK: SQL fallback also failed: %s", sql_err)
        
        # Also set server PID for future restart detection
        import os
        current_pid = str(os.getpid())
        
        # Check if parameter exists
        Param = env.get('ir.config_parameter')
        if Param:
            stored_pid = Param.get_param('bhuarjan.server_pid', default='')
            Param.set_param('bhuarjan.server_pid', current_pid)
            if stored_pid and stored_pid != current_pid:
                _logger.warning("POST_INIT_HOOK: Server PID changed from %s to %s (server restarted)", stored_pid, current_pid)
            else:
                _logger.info("POST_INIT_HOOK: Server PID set/updated: %s", current_pid)
        
        # FIX: Ensure web.base.url does not have trailing slash to prevent double slashes (e.g. //action-...)
        base_url = env['ir.config_parameter'].sudo().get_param('web.base.url')
        if base_url and base_url.endswith('/'):
            clean_url = base_url.rstrip('/')
            env['ir.config_parameter'].sudo().set_param('web.base.url', clean_url)
            _logger.info("POST_INIT_HOOK: Removed trailing slash from web.base.url: %s -> %s", base_url, clean_url)

    except Exception as e:
        _logger.error("POST_INIT_HOOK: Error in post_init_hook: %s", e, exc_info=True)

