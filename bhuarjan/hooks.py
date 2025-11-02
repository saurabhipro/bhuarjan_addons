# -*- coding: utf-8 -*-

import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Hook to invalidate all sessions after module update or server restart"""
    try:
        _logger.warning("=== POST_INIT_HOOK: Module update/restart detected ===")
        
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
    except Exception as e:
        _logger.error("POST_INIT_HOOK: Error in post_init_hook: %s", e, exc_info=True)

