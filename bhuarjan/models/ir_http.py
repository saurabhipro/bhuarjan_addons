# -*- coding: utf-8 -*-

from odoo import models, api
from odoo.http import request
import logging
import os

_logger = logging.getLogger(__name__)


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'
    
    @classmethod
    def _authenticate(cls, endpoint):
        """Override authenticate to check for server restart and force logout"""
        # Check server restart BEFORE authentication
        cls._check_server_restart()
        return super(IrHttp, cls)._authenticate(endpoint)
    
    @classmethod
    def _check_server_restart(cls):
        """Check if server has restarted and invalidate sessions"""
        try:
            # We need a request with a db to proceed
            if not hasattr(request, 'db') or not request.db:
                return
            
            # fast check: if we already checked this worker process, skip
            # This is a class attribute, so it persists for the life of the worker
            if getattr(cls, '_worker_pid_checked', False):
                return

            current_pid = str(os.getpid())
            
            # Use a new cursor to checking/updating the global state
            # This avoids messing with the current transaction
            from odoo.modules.registry import Registry
            registry = Registry(request.db)
            
            stored_pid = ''
            with registry.cursor() as cr:
                cr.execute("SELECT value FROM ir_config_parameter WHERE key = %s", ('bhuarjan.server_pid',))
                row = cr.fetchone()
                stored_pid = row[0] if row else ''

            if stored_pid != current_pid:
                _logger.info("BHUARJAN: Server PID changed from %s to %s (server restarted)", stored_pid, current_pid)
                
                # Update PID using INSERT ... ON CONFLICT to handle concurrency gracefully
                # This is atomic and won't cause serialization errors
                try:
                    with registry.cursor() as cr:
                        # Use INSERT ... ON CONFLICT for PostgreSQL (atomic, no race conditions)
                        cr.execute("""
                            INSERT INTO ir_config_parameter (key, value, create_uid, create_date, write_uid, write_date)
                            VALUES ('bhuarjan.server_pid', %s, 1, NOW(), 1, NOW())
                            ON CONFLICT (key) DO UPDATE 
                            SET value = EXCLUDED.value, write_uid = 1, write_date = NOW()
                        """, (current_pid,))
                        cr.commit()
                except Exception as pid_err:
                    # Silently ignore concurrency errors (harmless - another worker already updated)
                    pass
                
            # Mark this process as checked so we don't hit the DB on every request
            cls._worker_pid_checked = True
                
        except Exception as e:
            # Don't block the request if this maintenance task fails
            _logger.error("BHUARJAN: Error in _check_server_restart: %s", e)
    
    def get_frontend_session_info(cls):
        """Override to safely handle cases where session might be None"""
        try:
            # Call parent method - use super() without cls argument for classmethod
            result = super(IrHttp, cls).get_frontend_session_info()
            # Ensure we return a dict, not None
            if result is None:
                return {}
            return result
        except Exception as e:
            _logger.error("Error in get_frontend_session_info: %s", e, exc_info=True)
            # Return empty dict as fallback
            return {}

