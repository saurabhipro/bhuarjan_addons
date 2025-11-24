import jwt
import datetime
import random
import logging
import requests  # Import requests to send API call
from odoo import http
from odoo.http import request, Response
from odoo import models, fields
import json
import random

_logger = logging.getLogger(__name__)

import jwt

from odoo.exceptions import AccessError, UserError


from functools import wraps

def check_permission(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth_header = request.httprequest.headers.get('Authorization')
        if not auth_header or not auth_header.startswith("Bearer "):
            raise AccessError('Authorization header is missing or invalid')

        token = auth_header[7:]

        try:
            decoded_token = jwt.decode(token, options={"verify_signature": False})
            user_id = decoded_token['user_id']
            user = request.env['res.users'].sudo().search([('id', '=', user_id)])
            if not user:
                raise AccessError('User not found')
            request.user = user  # Optionally store for later use
        except jwt.ExpiredSignatureError:
            raise AccessError('JWT token has expired')
        except jwt.InvalidTokenError:
            raise AccessError('Invalid JWT token')
        except Exception as e:
            raise AccessError(str(e))

        return func(*args, **kwargs)
    return wrapper


def check_app_version(func):
    """Decorator to check app version code from query parameters or request body"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Get app_version_code from query parameters (works for all HTTP methods)
            app_version_code = request.httprequest.args.get('app_version_code', type=int)
            
            # If not in query params, try request body for POST/PUT/PATCH
            if not app_version_code and request.httprequest.method in ('POST', 'PUT', 'PATCH'):
                try:
                    if hasattr(request.httprequest, 'data') and request.httprequest.data:
                        # Try to get data - it might be bytes or already parsed
                        data_str = None
                        if isinstance(request.httprequest.data, bytes):
                            data_str = request.httprequest.data.decode('utf-8')
                        elif isinstance(request.httprequest.data, str):
                            data_str = request.httprequest.data
                        elif hasattr(request.httprequest, 'json') and request.httprequest.json:
                            # Already parsed JSON
                            app_version_code = request.httprequest.json.get('app_version_code')
                            if app_version_code:
                                try:
                                    app_version_code = int(app_version_code)
                                except (ValueError, TypeError):
                                    app_version_code = None
                        
                        if data_str and not app_version_code:
                            try:
                                data = json.loads(data_str or '{}')
                                app_version_code = data.get('app_version_code')
                                if app_version_code:
                                    try:
                                        app_version_code = int(app_version_code)
                                    except (ValueError, TypeError):
                                        app_version_code = None
                            except (json.JSONDecodeError, AttributeError):
                                pass
                except (AttributeError, UnicodeDecodeError):
                    pass
            
            # If app_version_code is provided, check it
            if app_version_code:
                # Check if version check is enforced in settings
                settings_master = request.env['bhuarjan.settings.master'].sudo().search([
                    ('active', '=', True),
                    ('enforce_app_version_check', '=', True)
                ], limit=1)
                
                if settings_master:
                    # Version check is enforced - validate the version
                    version_status = request.env['bhu.app.version'].sudo().check_version_status(app_version_code)
                    
                    if not version_status.get('allowed', False):
                        # Version is not allowed - return error
                        latest_version = version_status.get('latest_version', {})
                        error_message = version_status.get('message', 'App version is old. Please update to the latest version.')
                        
                        # For auth endpoints, include version_error flag for backward compatibility
                        is_auth_endpoint = '/api/auth/' in request.httprequest.path
                        error_response = {
                            'error': error_message,
                            'error_code': 'APP_VERSION_OUTDATED',
                            'latest_version': latest_version
                        }
                        if is_auth_endpoint:
                            error_response['version_error'] = True
                        else:
                            error_response['success'] = False
                        
                        return Response(
                            json.dumps(error_response),
                            status=403,
                            content_type='application/json'
                        )
                # If version check is not enforced, allow all versions
            
            # Version check passed or not enforced - proceed with the request
            return func(*args, **kwargs)
            
        except Exception as e:
            _logger.error(f"Error in check_app_version: {str(e)}", exc_info=True)
            # Don't block the request if version check fails due to error
            # Just log and proceed
            return func(*args, **kwargs)
    
    return wrapper


