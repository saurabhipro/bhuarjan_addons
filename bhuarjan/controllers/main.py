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
    """Decorator to check app version code from headers only (for all HTTP methods)"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Get app_version_code ONLY from headers (for all HTTP methods: GET, POST, PUT, PATCH, DELETE)
            app_version_code_str = request.httprequest.headers.get('app_version_code') or request.httprequest.headers.get('App-Version-Code') or request.httprequest.headers.get('X-App-Version-Code')
            app_version_code = None
            
            if app_version_code_str:
                try:
                    app_version_code = int(app_version_code_str)
                except (ValueError, TypeError):
                    app_version_code = None
            
            # app_version_code is MANDATORY - return error if missing
            if not app_version_code:
                # For auth endpoints, include version_error flag for backward compatibility
                is_auth_endpoint = '/api/auth/' in request.httprequest.path
                error_response = {
                    'error': 'app_version_code parameter is required',
                    'error_code': 'MISSING_APP_VERSION_CODE',
                }
                if is_auth_endpoint:
                    error_response['version_error'] = True
                else:
                    error_response['success'] = False
                
                return Response(
                    json.dumps(error_response),
                    status=400,
                    content_type='application/json'
                )
            
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
            
            # Version check passed - proceed with the request
            return func(*args, **kwargs)
            
        except Exception as e:
            _logger.error(f"Error in check_app_version: {str(e)}", exc_info=True)
            # Don't block the request if version check fails due to error
            # Just log and proceed
            return func(*args, **kwargs)
    
    return wrapper


