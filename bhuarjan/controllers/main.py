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
            # First, check if version check is enforced in settings
            settings_master = request.env['bhuarjan.settings.master'].sudo().search([
                ('active', '=', True),
                ('enforce_app_version_check', '=', True)
            ], limit=1)
            
            # If version check is NOT enforced, skip the check entirely
            if not settings_master:
                # Version check is disabled - allow request to proceed without checking
                return func(*args, **kwargs)
            
            # Version check IS enforced - now we need to get and validate app_version_code
            # Get app_version_code ONLY from headers (for all HTTP methods: GET, POST, PUT, PATCH, DELETE)
            # HTTP headers are case-insensitive, check multiple variations
            app_version_code_str = None
            headers = request.httprequest.headers
            
            # Debug: Log all headers to see what we're receiving
            all_headers_dict = dict(headers)
            _logger.error(f"=== APP VERSION CHECK DEBUG === Path: {request.httprequest.path}")
            _logger.error(f"All headers received: {list(all_headers_dict.keys())}")
            _logger.error(f"All headers dict: {all_headers_dict}")
            _logger.error(f"Request method: {request.httprequest.method}")
            
            # Also check raw environment for HTTP_ prefixed headers (some servers add HTTP_ prefix)
            # In WSGI, custom headers are stored as HTTP_HEADER_NAME (uppercase, hyphens become underscores)
            environ = request.httprequest.environ
            _logger.info(f"Checking environ for HTTP_APP_VERSION_CODE: {environ.get('HTTP_APP_VERSION_CODE')}")
            _logger.info(f"Checking environ for HTTP_APP_VERSION_CODE (lowercase): {environ.get('HTTP_APP_VERSION_CODE'.lower())}")
            
            # Check raw environment variables (headers are prefixed with HTTP_ and hyphens become underscores)
            # For "App-Version-Code" header, it becomes "HTTP_APP_VERSION_CODE" in environ
            for env_key, env_value in environ.items():
                if env_key.startswith('HTTP_'):
                    # Remove HTTP_ prefix and normalize
                    normalized_env_key = env_key.replace('HTTP_', '').lower().replace('-', '_')
                    _logger.error(f"Checking environ key: '{env_key}' (normalized: '{normalized_env_key}') = '{env_value}'")
                    if normalized_env_key == 'app_version_code':
                        app_version_code_str = env_value
                        _logger.error(f"✓ Found app_version_code in environ '{env_key}': {app_version_code_str}")
                        break
            
            # First, try to find by iterating through all headers (most reliable method)
            # This handles case-insensitivity and any normalization that might have occurred
            if not app_version_code_str:
                for key, value in headers.items():
                    # Normalize header name (lowercase, replace hyphens with underscores)
                    normalized_key = key.lower().replace('-', '_').replace(' ', '_')
                    _logger.error(f"Checking header: '{key}' (normalized: '{normalized_key}') = '{value}'")
                    if normalized_key == 'app_version_code':
                        app_version_code_str = value
                        _logger.error(f"✓ Found app_version_code in header '{key}' (normalized): {app_version_code_str}")
                        break
            
            # If still not found, try direct header name lookups (case-insensitive)
            if not app_version_code_str:
                header_names = [
                    'App-Version-Code',      # Hyphenated (preferred, standard HTTP header format)
                    'app-version-code',      # Lowercase hyphenated
                    'APP-VERSION-CODE',      # Uppercase hyphenated
                    'app_version_code',      # Underscore format (may be stripped by some servers)
                    'App_Version_Code',      # Mixed
                    'X-App-Version-Code',    # With X- prefix (hyphenated)
                    'X-App_Version_Code',    # With X- prefix (underscore)
                    'APP_VERSION_CODE',      # Uppercase underscore
                ]
                
                for header_name in header_names:
                    app_version_code_str = headers.get(header_name)
                    if app_version_code_str:
                        _logger.error(f"✓ Found app_version_code in header '{header_name}': {app_version_code_str}")
                        break
            
            app_version_code = None
            if app_version_code_str:
                try:
                    app_version_code = int(app_version_code_str)
                except (ValueError, TypeError):
                    _logger.warning(f"Invalid app_version_code value: {app_version_code_str}")
                    app_version_code = None
            
            # app_version_code is MANDATORY only if version check is enforced
            if not app_version_code:
                # Get latest version info to include in error response
                latest_version_obj = request.env['bhu.app.version'].sudo().get_latest_version()
                latest_version_info = None
                if latest_version_obj:
                    latest_version_info = {
                        'name': latest_version_obj.name,
                        'version_code': latest_version_obj.version_code,
                        'force_update': latest_version_obj.force_update,
                        'description': latest_version_obj.description or ''
                    }
                
                # For auth endpoints, include version_error flag for backward compatibility
                is_auth_endpoint = '/api/auth/' in request.httprequest.path
                
                # Create clear error message with version name
                if latest_version_info and latest_version_info.get('name'):
                    version_name = latest_version_info.get('name')
                    error_message = f'app_version_code parameter is required. Please install the latest version: {version_name}'
                else:
                    error_message = 'app_version_code parameter is required when version check is enforced'
                
                error_response = {
                    'error': error_message,
                    'error_code': 'MISSING_APP_VERSION_CODE',
                    'latest_version': latest_version_info
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
            
            # Version check is enforced - validate the version
            version_status = request.env['bhu.app.version'].sudo().check_version_status(app_version_code)
            
            if not version_status.get('allowed', False):
                # Version is not allowed - return error with latest version info
                latest_version = version_status.get('latest_version', {})
                
                # Get latest version info with all fields
                if latest_version:
                    latest_version_info = {
                        'name': latest_version.get('name'),
                        'version_code': latest_version.get('version_code'),
                        'force_update': latest_version.get('force_update', False),
                        'description': latest_version.get('description', '')
                    }
                else:
                    # Fallback: get latest version directly if not in status
                    latest_version_obj = request.env['bhu.app.version'].sudo().get_latest_version()
                    if latest_version_obj:
                        latest_version_info = {
                            'name': latest_version_obj.name,
                            'version_code': latest_version_obj.version_code,
                            'force_update': latest_version_obj.force_update,
                            'description': latest_version_obj.description or ''
                        }
                    else:
                        latest_version_info = None
                
                # Create clear error message with version name prominently displayed
                if latest_version_info and latest_version_info.get('name'):
                    version_name = latest_version_info.get('name')
                    error_message = f'App version is old. Please install the latest version: {version_name}'
                else:
                    error_message = version_status.get('message', 'App version is old. Please update to the latest version.')
                
                # For auth endpoints, include version_error flag for backward compatibility
                is_auth_endpoint = '/api/auth/' in request.httprequest.path
                error_response = {
                    'error': error_message,
                    'error_code': 'APP_VERSION_OUTDATED',
                    'latest_version': latest_version_info
                }
                if is_auth_endpoint:
                    error_response['version_error'] = True
                else:
                    error_response['success'] = False
                
                return Response(
                    json.dumps(error_response),
                    status=401,
                    content_type='application/json'
                )
            
            # Version check passed - proceed with the request
            return func(*args, **kwargs)
            
        except Exception as e:
            # Only log if it's a version-related error, not JWT/auth errors
            error_str = str(e)
            if 'jwt' not in error_str.lower() and 'token' not in error_str.lower() and 'auth' not in error_str.lower():
                _logger.error(f"Error in check_app_version: {str(e)}", exc_info=True)
            # Don't block the request if version check fails due to error
            # Just log and proceed
            return func(*args, **kwargs)
    
    return wrapper


