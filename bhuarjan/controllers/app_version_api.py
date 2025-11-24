# -*- coding: utf-8 -*-

import json
import logging
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class AppVersionAPIController(http.Controller):
    """API Controller for App Version Management"""

    @http.route('/api/bhuarjan/app/version/check', type='http', auth='public', methods=['GET'], csrf=False)
    def check_version(self, **kwargs):
        """
        Check if the app version is allowed to be used
        
        Query Parameters:
        - version_code (int, required): The version code of the app
        
        Returns:
        {
            "success": true/false,
            "data": {
                "allowed": true/false,
                "message": "Status message",
                "latest_version": {
                    "name": "1.0.0",
                    "version_code": 1,
                    "force_update": false
                },
                "update_available": true/false,
                "version_check_enforced": true/false
            }
        }
        """
        try:
            version_code = request.httprequest.args.get('version_code', type=int)
            
            if not version_code:
                return Response(
                    json.dumps({
                        'success': False,
                        'error': 'version_code is required'
                    }),
                    status=400,
                    content_type='application/json'
                )
            
            # Check if version check is enforced in settings
            settings_master = request.env['bhuarjan.settings.master'].sudo().search([
                ('active', '=', True),
                ('enforce_app_version_check', '=', True)
            ], limit=1)
            
            version_check_enforced = bool(settings_master)
            
            # If version check is not enforced, return success
            if not version_check_enforced:
                latest_version = request.env['bhu.app.version'].sudo().get_latest_version()
                return Response(
                    json.dumps({
                        'success': True,
                        'data': {
                            'allowed': True,
                            'message': 'Version check is not enforced. All versions are allowed.',
                            'latest_version': {
                                'name': latest_version.name if latest_version else None,
                                'version_code': latest_version.version_code if latest_version else None,
                                'force_update': latest_version.force_update if latest_version else False
                            } if latest_version else None,
                            'version_check_enforced': False
                        }
                    }),
                    status=200,
                    content_type='application/json'
                )
            
            # Version check is enforced - check the version
            version_status = request.env['bhu.app.version'].sudo().check_version_status(version_code)
            version_status['version_check_enforced'] = True
            
            # If version is not allowed, return error
            if not version_status.get('allowed', False):
                return Response(
                    json.dumps({
                        'success': False,
                        'error': version_status.get('message', 'Version not allowed'),
                        'data': version_status
                    }),
                    status=403,
                    content_type='application/json'
                )
            
            return Response(
                json.dumps({
                    'success': True,
                    'data': version_status
                }),
                status=200,
                content_type='application/json'
            )
            
        except Exception as e:
            _logger.error(f"Error in check_version: {str(e)}", exc_info=True)
            return Response(
                json.dumps({
                    'success': False,
                    'error': str(e)
                }),
                status=500,
                content_type='application/json'
            )

    @http.route('/api/bhuarjan/app/version/latest', type='http', auth='public', methods=['GET'], csrf=False)
    def get_latest_version(self, **kwargs):
        """
        Get the latest app version information
        
        Returns:
        {
            "success": true/false,
            "data": {
                "name": "1.0.0",
                "version_code": 1,
                "force_update": false,
                "description": "Version description",
                "is_active": true
            }
        }
        """
        try:
            latest_version = request.env['bhu.app.version'].sudo().get_latest_version()
            
            if not latest_version:
                return Response(
                    json.dumps({
                        'success': False,
                        'error': 'No active version found'
                    }),
                    status=404,
                    content_type='application/json'
                )
            
            return Response(
                json.dumps({
                    'success': True,
                    'data': {
                        'name': latest_version.name,
                        'version_code': latest_version.version_code,
                        'force_update': latest_version.force_update,
                        'description': latest_version.description or '',
                        'is_active': latest_version.is_active
                    }
                }),
                status=200,
                content_type='application/json'
            )
            
        except Exception as e:
            _logger.error(f"Error in get_latest_version: {str(e)}", exc_info=True)
            return Response(
                json.dumps({
                    'success': False,
                    'error': str(e)
                }),
                status=500,
                content_type='application/json'
            )

    @http.route('/api/bhuarjan/app/version/list', type='http', auth='user', methods=['GET'], csrf=False)
    def list_versions(self, **kwargs):
        """
        List all app versions (requires authentication)
        
        Returns:
        {
            "success": true/false,
            "data": [
                {
                    "id": 1,
                    "name": "1.0.0",
                    "version_code": 1,
                    "is_active": true,
                    "is_latest": true,
                    "activated_date": "2025-01-01 00:00:00",
                    "deactivated_date": null,
                    "force_update": false,
                    "description": "Version description"
                }
            ]
        }
        """
        try:
            versions = request.env['bhu.app.version'].sudo().search([])
            
            version_list = []
            for version in versions:
                version_list.append({
                    'id': version.id,
                    'name': version.name,
                    'version_code': version.version_code,
                    'is_active': version.is_active,
                    'is_latest': version.is_latest,
                    'activated_date': version.activated_date.isoformat() if version.activated_date else None,
                    'deactivated_date': version.deactivated_date.isoformat() if version.deactivated_date else None,
                    'force_update': version.force_update,
                    'description': version.description or ''
                })
            
            return Response(
                json.dumps({
                    'success': True,
                    'data': version_list
                }),
                status=200,
                content_type='application/json'
            )
            
        except Exception as e:
            _logger.error(f"Error in list_versions: {str(e)}", exc_info=True)
            return Response(
                json.dumps({
                    'success': False,
                    'error': str(e)
                }),
                status=500,
                content_type='application/json'
            )

