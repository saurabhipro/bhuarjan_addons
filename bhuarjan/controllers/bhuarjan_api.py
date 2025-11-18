# -*- coding: utf-8 -*-
"""
Bhuarjan REST API Controller
Provides REST APIs for mobile app integration
Public APIs - No authentication required
"""
from odoo import http
from odoo.http import request, Response
from odoo.exceptions import ValidationError
import json
import logging
import base64
import re
from .main import *
import datetime
from datetime import timedelta, timezone

_logger = logging.getLogger(__name__)

try:
    import boto3
    from botocore.exceptions import ClientError
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False
    _logger.warning("boto3 library not found. S3 presigned URL generation will not be available.")


class BhuarjanAPIController(http.Controller):
    """REST API Controller for Bhuarjan mobile app"""

    @http.route('/api/bhuarjan/user/projects', type='http', auth='public', methods=['GET'], csrf=False)
    @check_permission
    def get_user_projects(self, **kwargs):
        """
        Get projects and villages mapped to a specific user
        Query params: user_id (optional - if not provided, returns all projects and villages)
        Returns: JSON with projects and their associated villages (filtered by user if user_id provided)
        """
        try:
            # Get query parameters
            user_id = request.httprequest.args.get('user_id', type=int)

            # Get user's villages if user_id is provided
            user_village_ids = []
            user_info = None
            if user_id:
                user = request.env['res.users'].sudo().browse(user_id)
                if not user.exists():
                    return Response(
                        json.dumps({'error': f'User with ID {user_id} not found'}),
                        status=404,
                        content_type='application/json'
                    )
                user_village_ids = user.village_ids.ids if user.village_ids else []
                user_info = {
                    'id': user.id,
                    'name': user.name,
                    'login': user.login,
                    'bhuarjan_role': user.bhuarjan_role or '',
                }

            # Get projects
            if user_id and user_village_ids:
                # Filter projects that have villages mapped to this user
                projects = request.env['bhu.project'].sudo().search([
                    ('village_ids', 'in', user_village_ids)
                ])
            else:
                # Get all projects if no user_id provided
                projects = request.env['bhu.project'].sudo().search([])

            result = []
            for project in projects:
                # Filter villages based on user if user_id provided
                if user_id and user_village_ids:
                    project_villages = project.village_ids.filtered(
                        lambda v: v.id in user_village_ids
                    )
                else:
                    project_villages = project.village_ids
                
                villages_data = []
                for village in project_villages:
                    villages_data.append({
                        'id': village.id,
                        'name': village.name,
                        'village_code': village.village_code or '',
                        'village_uuid': village.village_uuid or '',
                        'district_id': village.district_id.id if village.district_id else None,
                        'district_name': village.district_id.name if village.district_id else '',
                        'tehsil_id': village.tehsil_id.id if village.tehsil_id else None,
                        'tehsil_name': village.tehsil_id.name if village.tehsil_id else '',
                        'pincode': village.pincode or '',
                    })
                
                # Only include project if it has villages (after filtering)
                if villages_data:
                    result.append({
                        'id': project.id,
                        'name': project.name,
                        'code': project.code or '',
                        'project_uuid': project.project_uuid or '',
                        'description': project.description or '',
                        'state': project.state,
                        'villages': villages_data
                    })

            response_data = {
                'success': True,
                'data': result
            }
            
            # Include user info if user_id was provided
            if user_info:
                response_data['user'] = user_info

            return Response(
                json.dumps(response_data),
                status=200,
                content_type='application/json'
            )

        except Exception as e:
            _logger.error(f"Error in get_user_projects: {str(e)}", exc_info=True)
            return Response(
                json.dumps({'error': str(e)}),
                status=500,
                content_type='application/json'
            )

    @http.route('/api/bhuarjan/users', type='http', auth='public', methods=['GET'], csrf=False)
    @check_permission
    def get_all_users(self, **kwargs):
        """
        Get all users with their details
        Query params: limit, offset, role (optional filter by bhuarjan_role)
        Returns: JSON list of users
        """
        try:
            # Get query parameters
            limit = request.httprequest.args.get('limit', type=int) or 100
            offset = request.httprequest.args.get('offset', type=int) or 0
            role = request.httprequest.args.get('role')

            # Build domain
            domain = []
            if role:
                domain.append(('bhuarjan_role', '=', role))

            # Search users
            users = request.env['res.users'].sudo().search(domain, limit=limit, offset=offset, order='name')

            # Build response
            users_data = []
            for user in users:
                # Get village IDs and names
                villages_data = []
                for village in user.village_ids:
                    villages_data.append({
                        'id': village.id,
                        'name': village.name,
                        'village_code': village.village_code or '',
                    })

                # Get tehsil IDs and names
                tehsils_data = []
                for tehsil in user.tehsil_ids:
                    tehsils_data.append({
                        'id': tehsil.id,
                        'name': tehsil.name,
                    })

                # Get sub division IDs and names
                sub_divisions_data = []
                for sub_div in user.sub_division_ids:
                    sub_divisions_data.append({
                        'id': sub_div.id,
                        'name': sub_div.name,
                    })

                # Get circle IDs and names
                circles_data = []
                for circle in user.circle_ids:
                    circles_data.append({
                        'id': circle.id,
                        'name': circle.name,
                    })

                users_data.append({
                    'id': user.id,
                    'name': user.name,
                    'login': user.login,
                    'email': user.email or '',
                    'mobile': user.mobile or '',
                    'bhuarjan_role': user.bhuarjan_role or '',
                    'state_id': user.state_id.id if user.state_id else None,
                    'state_name': user.state_id.name if user.state_id else '',
                    'district_id': user.district_id.id if user.district_id else None,
                    'district_name': user.district_id.name if user.district_id else '',
                    'parent_id': user.parent_id.id if user.parent_id else None,
                    'parent_name': user.parent_id.name if user.parent_id else '',
                    'villages': villages_data,
                    'tehsils': tehsils_data,
                    'sub_divisions': sub_divisions_data,
                    'circles': circles_data,
                    'active': user.active,
                })

            # Get total count
            total_count = request.env['res.users'].sudo().search_count(domain)

            return Response(
                json.dumps({
                    'success': True,
                    'data': users_data,
                    'total': total_count,
                    'limit': limit,
                    'offset': offset
                }),
                status=200,
                content_type='application/json'
            )

        except Exception as e:
            _logger.error(f"Error in get_all_users: {str(e)}", exc_info=True)
            return Response(
                json.dumps({'error': str(e)}),
                status=500,
                content_type='application/json'
            )

    @http.route('/api/bhuarjan/users/autocomplete', type='http', auth='public', methods=['GET'], csrf=False)
    @check_permission
    def autocomplete_users(self, **kwargs):
        """
        Autocomplete API for users based on username/name
        Query params: q (search query - minimum 3 characters required), limit (optional, default: 20, max: 50)
        Returns: JSON list of matching users with id, name, login, email, mobile
        """
        try:
            # Get query parameters
            query = request.httprequest.args.get('q', '').strip()
            limit = min(request.httprequest.args.get('limit', type=int) or 20, 50)  # Default 20, max 50
            
            # Validate minimum query length
            if len(query) < 3:
                return Response(
                    json.dumps({
                        'success': True,
                        'data': [],
                        'message': 'Please enter at least 3 characters to search',
                        'total': 0
                    }),
                    status=200,
                    content_type='application/json'
                )
            
            # Build search domain - search in both name and login fields
            domain = [
                '|',
                ('name', 'ilike', query),
                ('login', 'ilike', query)
            ]
            
            # Only search active users
            domain.append(('active', '=', True))
            
            # Search users
            users = request.env['res.users'].sudo().search(domain, limit=limit, order='name')
            
            # Build response - simplified user objects for autocomplete
            users_data = []
            for user in users:
                users_data.append({
                    'id': user.id,
                    'name': user.name or '',
                    'login': user.login or '',
                    'email': user.email or '',
                    'mobile': user.mobile or '',
                    'display_name': f"{user.name} ({user.login})" if user.name and user.login else (user.name or user.login or ''),
                })
            
            # Get total count (for pagination info, but we limit results)
            total_count = request.env['res.users'].sudo().search_count(domain)
            
            return Response(
                json.dumps({
                    'success': True,
                    'data': users_data,
                    'total': total_count,
                    'limit': limit,
                    'query': query
                }),
                status=200,
                content_type='application/json'
            )
            
        except Exception as e:
            _logger.error(f"Error in autocomplete_users: {str(e)}", exc_info=True)
            return Response(
                json.dumps({
                    'success': False,
                    'error': 'Internal server error',
                    'message': str(e)
                }),
                status=500,
                content_type='application/json'
            )

    @http.route('/api/bhuarjan/departments', type='http', auth='public', methods=['GET'], csrf=False)
    def get_all_departments(self, **kwargs):
        """
        Get all departments
        Query params: limit, offset
        Returns: JSON list of departments
        """
        try:
            # Get query parameters
            limit = request.httprequest.args.get('limit', type=int) or 100
            offset = request.httprequest.args.get('offset', type=int) or 0

            # Search departments
            departments = request.env['bhu.department'].sudo().search([], limit=limit, offset=offset, order='name')

            # Build response
            departments_data = []
            for dept in departments:
                departments_data.append({
                    'id': dept.id,
                    'name': dept.name,
                    'code': dept.code or '',
                    'description': dept.description or '',
                    'head_of_department': dept.head_of_department or '',
                    'contact_number': dept.contact_number or '',
                    'email': dept.email or '',
                    'address': dept.address or '',
                })

            # Get total count
            total_count = request.env['bhu.department'].sudo().search_count([])

            return Response(
                json.dumps({
                    'success': True,
                    'data': departments_data,
                    'total': total_count,
                    'limit': limit,
                    'offset': offset
                }),
                status=200,
                content_type='application/json'
            )

        except Exception as e:
            _logger.error(f"Error in get_all_departments: {str(e)}", exc_info=True)
            return Response(
                json.dumps({'error': str(e)}),
                status=500,
                content_type='application/json'
            )

    @http.route('/api/bhuarjan/departments/<int:department_id>/projects', type='http', auth='public', methods=['GET'], csrf=False)
    def get_department_projects(self, department_id, **kwargs):
        """
        Get all projects in a department
        Path param: department_id (required)
        Query params: limit, offset
        Returns: JSON list of projects
        """
        try:
            # Validate department exists
            department = request.env['bhu.department'].sudo().browse(department_id)
            if not department.exists():
                return Response(
                    json.dumps({
                        'success': False,
                        'error': 'Department not found',
                        'message': f'Department with ID {department_id} does not exist'
                    }),
                    status=404,
                    content_type='application/json'
                )

            # Get query parameters
            limit = request.httprequest.args.get('limit', type=int) or 100
            offset = request.httprequest.args.get('offset', type=int) or 0

            # Get projects from department
            projects = department.project_ids.sudo()
            total_count = len(projects)

            # Apply pagination
            paginated_projects = projects[offset:offset + limit] if projects else []

            # Build response
            projects_data = []
            for project in paginated_projects:
                projects_data.append({
                    'id': project.id,
                    'name': project.name or '',
                    'code': project.code or '',
                    'description': project.description or '',
                    'budget': project.budget or 0.0,
                    'start_date': project.start_date.strftime('%Y-%m-%d') if project.start_date else None,
                    'end_date': project.end_date.strftime('%Y-%m-%d') if project.end_date else None,
                    'state': project.state or '',
                    'project_uuid': project.project_uuid or '',
                    'village_ids': project.village_ids.ids if project.village_ids else [],
                    'village_count': len(project.village_ids) if project.village_ids else 0,
                })

            return Response(
                json.dumps({
                    'success': True,
                    'data': projects_data,
                    'total': total_count,
                    'limit': limit,
                    'offset': offset,
                    'department_id': department_id,
                    'department_name': department.name or ''
                }),
                status=200,
                content_type='application/json'
            )

        except ValueError as e:
            _logger.error(f"Error in get_department_projects: Invalid department_id: {str(e)}", exc_info=True)
            return Response(
                json.dumps({
                    'success': False,
                    'error': 'Invalid department ID',
                    'message': 'department_id must be a valid integer'
                }),
                status=400,
                content_type='application/json'
            )
        except Exception as e:
            _logger.error(f"Error in get_department_projects: {str(e)}", exc_info=True)
            return Response(
                json.dumps({
                    'success': False,
                    'error': str(e)
                }),
                status=500,
                content_type='application/json'
            )

    @http.route('/api/bhuarjan/channels', type='http', auth='public', methods=['GET'], csrf=False)
    @check_permission
    def get_all_channels(self, **kwargs):
        """
        Get all channels
        Query params: limit, offset, active (optional filter - default True), channel_type (optional: web/mobile)
        Returns: JSON list of channels
        """
        try:
            limit = request.httprequest.args.get('limit', type=int) or 100
            offset = request.httprequest.args.get('offset', type=int) or 0
            active_filter = request.httprequest.args.get('active')
            channel_type = request.httprequest.args.get('channel_type')
            
            domain = []
            if active_filter is not None:
                active_bool = active_filter.lower() in ('true', '1', 'yes')
                domain.append(('active', '=', active_bool))
            else:
                domain.append(('active', '=', True))
            
            if channel_type:
                domain.append(('channel_type', '=', channel_type))
        
            channels = request.env['bhu.channel.master'].sudo().search(domain, limit=limit, offset=offset, order='name')
        
            channels_data = []
            for channel in channels:
                channels_data.append({
                    'id': channel.id,
                    'name': channel.name or '',
                    'code': channel.code or '',
                    'channel_type': channel.channel_type or '',
                    'active': channel.active,
                    'description': channel.description or '',
                })
        
            total_count = request.env['bhu.channel.master'].sudo().search_count(domain)
        
            return Response(
                json.dumps({
                    'success': True,
                    'data': channels_data,
                    'total': total_count,
                    'limit': limit,
                    'offset': offset
                }),
                status=200,
                content_type='application/json'
            )
        
        except Exception as e:
            _logger.error(f"Error in get_all_channels: {str(e)}", exc_info=True)
            return Response(
                json.dumps({'error': str(e)}),
                status=500,
                content_type='application/json'
            )

    @http.route('/api/bhuarjan/land-types', type='http', auth='public', methods=['GET'], csrf=False)
    def get_all_land_types(self, **kwargs):
        """
        Get all land types
        Query params: limit, offset, active (optional filter - default True)
        Returns: JSON list of land types
        """
        try:
            # Get query parameters
            limit = request.httprequest.args.get('limit', type=int) or 100
            offset = request.httprequest.args.get('offset', type=int) or 0
            active_filter = request.httprequest.args.get('active')
            
            # Build domain - filter by active if specified
            domain = []
            if active_filter is not None:
                active_bool = active_filter.lower() in ('true', '1', 'yes')
                domain.append(('active', '=', active_bool))
            else:
                # Default to active only
                domain.append(('active', '=', True))

            # Search land types
            land_types = request.env['bhu.land.type'].sudo().search(domain, limit=limit, offset=offset, order='name')

            # Build response
            land_types_data = []
            for land_type in land_types:
                land_types_data.append({
                    'id': land_type.id,
                    'name': land_type.name or '',
                    'code': land_type.code or '',
                    'description': land_type.description or '',
                    'active': land_type.active,
                })

            # Get total count
            total_count = request.env['bhu.land.type'].sudo().search_count(domain)

            return Response(
                json.dumps({
                    'success': True,
                    'data': land_types_data,
                    'total': total_count,
                    'limit': limit,
                    'offset': offset
                }),
                status=200,
                content_type='application/json'
            )

        except Exception as e:
            _logger.error(f"Error in get_all_land_types: {str(e)}", exc_info=True)
            return Response(
                json.dumps({'error': str(e)}),
                status=500,
                content_type='application/json'
            )

    @http.route('/api/bhuarjan/trees', type='http', auth='public', methods=['GET'], csrf=False)
    def get_all_trees(self, **kwargs):
        """
        Get all tree masters with optional filters by name and development stage
        Query params: 
            - name (optional): Filter by tree name (partial match, case-insensitive)
            - development_stage (optional): Filter by development stage and return rate for that stage
                Values: 'undeveloped', 'semi_developed', 'fully_developed'
            - limit (optional, default 100)
            - offset (optional, default 0)
            - active (optional filter - default True)
        Returns: JSON list of tree masters with rates
        """
        try:
            # Get query parameters
            limit = request.httprequest.args.get('limit', type=int) or 100
            offset = request.httprequest.args.get('offset', type=int) or 0
            active_filter = request.httprequest.args.get('active')
            name_filter = request.httprequest.args.get('name', '').strip()
            development_stage = request.httprequest.args.get('development_stage', '').strip().lower()
            
            # Validate development_stage if provided
            valid_stages = ['undeveloped', 'semi_developed', 'fully_developed']
            if development_stage and development_stage not in valid_stages:
                return Response(
                    json.dumps({
                        'error': f'Invalid development_stage: {development_stage}. Must be one of: {", ".join(valid_stages)}'
                    }),
                    status=400,
                    content_type='application/json'
                )
            
            # Build domain
            domain = []
            if active_filter is not None:
                active_bool = active_filter.lower() in ('true', '1', 'yes')
                domain.append(('active', '=', active_bool))
            else:
                # Default to active only
                domain.append(('active', '=', True))
            
            # Filter by name (partial match, case-insensitive)
            if name_filter:
                domain.append(('name', 'ilike', name_filter))

            # Search tree masters
            trees = request.env['bhu.tree.master'].sudo().search(domain, limit=limit, offset=offset, order='name')

            # Build response
            trees_data = []
            for tree in trees:
                tree_data = {
                    'id': tree.id,
                    'name': tree.name or '',
                    'code': tree.code or '',
                    'undeveloped_rate': tree.undeveloped_rate or 0.0,
                    'semi_developed_rate': tree.semi_developed_rate or 0.0,
                    'fully_developed_rate': tree.fully_developed_rate or 0.0,
                    'currency_id': tree.currency_id.id if tree.currency_id else None,
                    'currency_name': tree.currency_id.name if tree.currency_id else '',
                    'description': tree.description or '',
                    'active': tree.active
                }
                
                # If development_stage is specified, add the rate for that stage
                if development_stage:
                    if development_stage == 'undeveloped':
                        tree_data['rate'] = tree.undeveloped_rate or 0.0
                    elif development_stage == 'semi_developed':
                        tree_data['rate'] = tree.semi_developed_rate or 0.0
                    elif development_stage == 'fully_developed':
                        tree_data['rate'] = tree.fully_developed_rate or 0.0
                
                trees_data.append(tree_data)

            # Get total count
            total_count = request.env['bhu.tree.master'].sudo().search_count(domain)

            return Response(
                json.dumps({
                    'success': True,
                    'data': trees_data,
                    'total': total_count,
                    'count': len(trees_data),
                    'limit': limit,
                    'offset': offset,
                    'filters': {
                        'name': name_filter if name_filter else None,
                        'development_stage': development_stage if development_stage else None
                    }
                }),
                status=200,
                content_type='application/json'
            )

        except Exception as e:
            _logger.error(f"Error in get_all_trees: {str(e)}", exc_info=True)
            return Response(
                json.dumps({'error': str(e)}),
                status=500,
                content_type='application/json'
            )

    @http.route('/api/bhuarjan/survey', type='http', auth='public', methods=['POST'], csrf=False)
    @check_permission
    def create_survey(self, **kwargs):
        """
        Create a new survey
        Accepts: JSON data with survey fields
        Returns: Created survey details
        """
        try:
            # Parse request data
            data = json.loads(request.httprequest.data.decode('utf-8') or '{}')
            
            # Validate that at least one landowner is provided
            landowner_ids = data.get('landowner_ids', [])
            if not landowner_ids or (isinstance(landowner_ids, list) and len(landowner_ids) == 0):
                return Response(
                    json.dumps({
                        'error': 'Please select at least one landowner',
                        'message': 'At least one landowner is required to create a survey'
                    }),
                    status=400,
                    content_type='application/json'
                )
            
            # Validate that all landowner IDs exist and are valid
            if isinstance(landowner_ids, list):
                invalid_ids = []
                valid_ids = []
                for landowner_id in landowner_ids:
                    if not isinstance(landowner_id, int):
                        invalid_ids.append(f"{landowner_id} (not an integer)")
                    else:
                        landowner = request.env['bhu.landowner'].sudo().browse(landowner_id)
                        if not landowner.exists():
                            invalid_ids.append(str(landowner_id))
                        else:
                            valid_ids.append(landowner_id)
                
                if invalid_ids:
                    return Response(
                        json.dumps({
                            'error': 'Invalid landowner ID(s)',
                            'message': f'The following landowner ID(s) do not exist or are invalid: {", ".join(invalid_ids)}',
                            'invalid_ids': invalid_ids,
                            'valid_ids': valid_ids
                        }),
                        status=400,
                        content_type='application/json'
                    )
                
                # Use only valid IDs
                landowner_ids = valid_ids
            
            # Validate required fields
            required_fields = {
                'project_id': 'Project',
                'village_id': 'Village',
                'department_id': 'Department',
                'tehsil_id': 'Tehsil',
                'khasra_number': 'Khasra Number',
                'total_area': 'Total Area',
                'acquired_area': 'Acquired Area'
            }
            
            missing_fields = []
            for field, label in required_fields.items():
                if field not in data or data.get(field) is None or data.get(field) == '':
                    missing_fields.append(label)
            
            if missing_fields:
                return Response(
                    json.dumps({
                        'error': 'Missing required fields',
                        'message': f'The following required fields are missing: {", ".join(missing_fields)}',
                        'missing_fields': missing_fields
                    }),
                    status=400,
                    content_type='application/json'
                )
            
            # Validate that referenced IDs exist
            validation_errors = []
            
            # Validate project_id
            if data.get('project_id'):
                project = request.env['bhu.project'].sudo().browse(data['project_id'])
                if not project.exists():
                    validation_errors.append(f'Project ID {data["project_id"]} does not exist')
            
            # Validate village_id
            if data.get('village_id'):
                village = request.env['bhu.village'].sudo().browse(data['village_id'])
                if not village.exists():
                    validation_errors.append(f'Village ID {data["village_id"]} does not exist')
            
            # Validate department_id
            if data.get('department_id'):
                department = request.env['bhu.department'].sudo().browse(data['department_id'])
                if not department.exists():
                    validation_errors.append(f'Department ID {data["department_id"]} does not exist')
            
            # Validate tehsil_id
            if data.get('tehsil_id'):
                tehsil = request.env['bhu.tehsil'].sudo().browse(data['tehsil_id'])
                if not tehsil.exists():
                    validation_errors.append(f'Tehsil ID {data["tehsil_id"]} does not exist')
            
            if validation_errors:
                return Response(
                    json.dumps({
                        'error': 'Invalid reference ID(s)',
                        'message': '; '.join(validation_errors),
                        'details': validation_errors
                    }),
                    status=400,
                    content_type='application/json'
                )
            
            # Get default user (admin) or use provided user_id
            user_id = data.get('user_id')
            if not user_id:
                # Use admin user as default
                admin_user = request.env['res.users'].sudo().search([('login', '=', 'admin')], limit=1)
                user_id = admin_user.id if admin_user else 2  # Fallback to user ID 2 (usually admin)
            
            # Handle crop_type - accept crop_type (ID) and map to crop_type_id in model
            crop_type_id = None
            if 'crop_type' in data:
                crop_type_value = data.get('crop_type')
                if isinstance(crop_type_value, int):
                    # If it's an integer, treat it as land type ID
                    # Validate that the land type exists
                    land_type = request.env['bhu.land.type'].sudo().browse(crop_type_value)
                    if land_type.exists():
                        crop_type_id = crop_type_value
                    else:
                        return Response(
                            json.dumps({
                                'error': f'Invalid crop_type: Land type with ID {crop_type_value} does not exist'
                            }),
                            status=400,
                            content_type='application/json'
                        )
                elif isinstance(crop_type_value, str):
                    # Backward compatibility: map old crop_type string to land type ID
                    crop_type_str = crop_type_value.lower()
                    if crop_type_str in ('single', 'single1'):
                        single_crop = request.env['bhu.land.type'].sudo().search([
                            ('code', '=', 'SINGLE_CROP')
                        ], limit=1)
                        crop_type_id = single_crop.id if single_crop else None
                    elif crop_type_str in ('double', 'double1'):
                        double_crop = request.env['bhu.land.type'].sudo().search([
                            ('code', '=', 'DOUBLE_CROP')
                        ], limit=1)
                        crop_type_id = double_crop.id if double_crop else None
            elif 'crop_type_id' in data:
                # Also support crop_type_id for backward compatibility
                crop_type_id_value = data.get('crop_type_id')
                if crop_type_id_value:
                    # Validate that the land type exists
                    land_type = request.env['bhu.land.type'].sudo().browse(crop_type_id_value)
                    if land_type.exists():
                        crop_type_id = crop_type_id_value
                    else:
                        return Response(
                            json.dumps({
                                'error': f'Invalid crop_type_id: Land type with ID {crop_type_id_value} does not exist'
                            }),
                            status=400,
                            content_type='application/json'
                        )
            
            # Validate area values before creating survey
            total_area = data.get('total_area', 0.0)
            acquired_area = data.get('acquired_area', 0.0)
            
            # Area validation checks
            if total_area is None or total_area <= 0:
                return Response(
                    json.dumps({
                        'error': 'Validation Error',
                        'message': 'Total Area must be greater than 0.'
                    }),
                    status=400,
                    content_type='application/json'
                )
            
            if acquired_area is None or acquired_area <= 0:
                return Response(
                    json.dumps({
                        'error': 'Validation Error',
                        'message': 'Acquired Area must be greater than 0.'
                    }),
                    status=400,
                    content_type='application/json'
                )
            
            if acquired_area > total_area:
                return Response(
                    json.dumps({
                        'error': 'Validation Error',
                        'message': 'Acquired Area cannot be greater than Total Area.'
                    }),
                    status=400,
                    content_type='application/json'
                )
            
            # Prepare survey values
            survey_vals = {
                'user_id': user_id,
                'project_id': data.get('project_id'),
                'village_id': data.get('village_id'),
                'department_id': data.get('department_id'),
                'tehsil_id': data.get('tehsil_id'),
                'khasra_number': data.get('khasra_number'),
                'total_area': total_area,
                'acquired_area': acquired_area,
                'has_traded_land': data.get('has_traded_land', 'no'),
                'traded_land_area': data.get('traded_land_area', 0.0),
                'irrigation_type': data.get('irrigation_type', 'irrigated'),
                'undeveloped_tree_count': data.get('undeveloped_tree_count', 0),
                'semi_developed_tree_count': data.get('semi_developed_tree_count', 0),
                'fully_developed_tree_count': data.get('fully_developed_tree_count', 0),
                'has_house': data.get('has_house', 'no'),
                'house_type': data.get('house_type'),
                'house_area': data.get('house_area', 0.0),
                'has_shed': data.get('has_shed', 'no'),
                'shed_area': data.get('shed_area', 0.0),
                'has_well': data.get('has_well', 'no'),
                'has_tubewell': data.get('has_tubewell', 'no'),
                'has_pond': data.get('has_pond', 'no'),
                'latitude': data.get('latitude'),
                'longitude': data.get('longitude'),
                'location_accuracy': data.get('location_accuracy'),
                'location_timestamp': data.get('location_timestamp'),
                'remarks': data.get('remarks'),
                'state': data.get('state', 'draft'),
            }
            
            # Handle trees_description - always include it, defaulting to empty string if not provided
            survey_vals['trees_description'] = data.get('trees_description') or ''
            
            # Set crop_type_id only if it has a valid value (not None)
            if crop_type_id:
                survey_vals['crop_type_id'] = crop_type_id
            
            # Explicitly remove crop_type from survey_vals if it exists (shouldn't happen, but safety check)
            survey_vals.pop('crop_type', None)
            
            # Handle survey_date - only set if explicitly provided, otherwise use model default (today's date)
            if 'survey_date' in data and data.get('survey_date'):
                survey_vals['survey_date'] = data.get('survey_date')
            
            # Handle well_type separately - only set if provided (optional field)
            if 'well_type' in data and data.get('well_type'):
                survey_vals['well_type'] = data.get('well_type')

            # Handle survey image if provided (base64 encoded)
            if data.get('survey_image'):
                try:
                    image_data = data['survey_image']
                    if isinstance(image_data, str):
                        # Remove data URL prefix if present
                        if ',' in image_data:
                            image_data = image_data.split(',')[1]
                        survey_vals['survey_image'] = base64.b64decode(image_data)
                        survey_vals['survey_image_filename'] = data.get('survey_image_filename', 'survey_image.jpg')
                except Exception as e:
                    _logger.warning(f"Error processing survey image: {str(e)}")

            # Create survey
            survey = request.env['bhu.survey'].sudo().create(survey_vals)

            # Link landowners (already validated above - at least one is required)
            if isinstance(landowner_ids, list) and len(landowner_ids) > 0:
                survey.sudo().write({'landowner_ids': [(6, 0, landowner_ids)]})
            
            # Handle tree lines (merged structure - single array with development_stage)
            tree_line_vals = []
            
            # Support new format: tree_lines array with development_stage
            if 'tree_lines' in data and isinstance(data['tree_lines'], list):
                for tree_line in data['tree_lines']:
                    if isinstance(tree_line, dict) and 'development_stage' in tree_line:
                        # Support both tree_master_id (integer) and tree_name (string) for tree selection
                        tree_master_id = None
                        if 'tree_master_id' in tree_line and tree_line['tree_master_id']:
                            tree_master_id = tree_line['tree_master_id']
                        elif 'tree_name' in tree_line and tree_line['tree_name']:
                            # Look up tree by name
                            tree_master = request.env['bhu.tree.master'].sudo().search([
                                ('name', '=', tree_line['tree_name'])
                            ], limit=1)
                            if tree_master:
                                tree_master_id = tree_master.id
                            else:
                                return Response(
                                    json.dumps({
                                        'error': f'Tree with name "{tree_line["tree_name"]}" not found in tree master'
                                    }),
                                    status=400,
                                    content_type='application/json'
                                )
                        else:
                            return Response(
                                json.dumps({
                                    'error': 'Either tree_master_id or tree_name must be provided for each tree line'
                                }),
                                status=400,
                                content_type='application/json'
                            )
                        
                        # Validate development_stage
                        development_stage = tree_line.get('development_stage')
                        if development_stage not in ('undeveloped', 'semi_developed', 'fully_developed'):
                            return Response(
                                json.dumps({
                                    'error': f'Invalid development_stage: {development_stage}. Must be one of: undeveloped, semi_developed, fully_developed'
                                }),
                                status=400,
                                content_type='application/json'
                            )
                        
                        tree_line_vals.append((0, 0, {
                            'tree_master_id': tree_master_id,
                            'development_stage': development_stage,
                            'quantity': tree_line.get('quantity', 1)
                        }))
            
            # Backward compatibility: support old format with separate arrays
            if 'undeveloped_tree_lines' in data and isinstance(data['undeveloped_tree_lines'], list):
                for tree_line in data['undeveloped_tree_lines']:
                    if isinstance(tree_line, dict) and 'tree_master_id' in tree_line:
                        tree_line_vals.append((0, 0, {
                            'tree_master_id': tree_line['tree_master_id'],
                            'development_stage': 'undeveloped',
                            'quantity': tree_line.get('quantity', 1)
                        }))
            
            if 'semi_developed_tree_lines' in data and isinstance(data['semi_developed_tree_lines'], list):
                for tree_line in data['semi_developed_tree_lines']:
                    if isinstance(tree_line, dict) and 'tree_master_id' in tree_line:
                        tree_line_vals.append((0, 0, {
                            'tree_master_id': tree_line['tree_master_id'],
                            'development_stage': 'semi_developed',
                            'quantity': tree_line.get('quantity', 1)
                        }))
            
            if 'fully_developed_tree_lines' in data and isinstance(data['fully_developed_tree_lines'], list):
                for tree_line in data['fully_developed_tree_lines']:
                    if isinstance(tree_line, dict) and 'tree_master_id' in tree_line:
                        tree_line_vals.append((0, 0, {
                            'tree_master_id': tree_line['tree_master_id'],
                            'development_stage': 'fully_developed',
                            'quantity': tree_line.get('quantity', 1)
                        }))
            
            # Create tree lines if any
            if tree_line_vals:
                survey.sudo().write({'tree_line_ids': tree_line_vals})

            # Return created survey details
            return Response(
                json.dumps({
                    'success': True,
                    'data': {
                        'id': survey.id,
                        'name': survey.name,
                        'survey_uuid': survey.survey_uuid,
                        'khasra_number': survey.khasra_number,
                        'state': survey.state,
                    }
                }),
                status=201,
                content_type='application/json'
            )

        except ValidationError as ve:
            _logger.error(f"Validation error in create_survey: {str(ve)}", exc_info=True)
            return Response(
                json.dumps({
                    'error': 'Validation Error',
                    'message': str(ve)
                }),
                status=400,
                content_type='application/json'
            )
        except Exception as e:
            _logger.error(f"Error in create_survey: {str(e)}", exc_info=True)
            return Response(
                json.dumps({'error': str(e)}),
                status=500,
                content_type='application/json'
            )

    @http.route('/api/bhuarjan/survey/<int:survey_id>', type='http', auth='public', methods=['GET'], csrf=False)
    @check_permission
    def get_survey_details(self, survey_id, **kwargs):
        """
        Get detailed survey information
        Returns: JSON with complete survey details
        """
        try:
            survey = request.env['bhu.survey'].sudo().browse(survey_id)
            if not survey.exists():
                return Response(
                    json.dumps({'error': 'Survey not found'}),
                    status=404,
                    content_type='application/json'
                )

            # Get survey image as base64 if exists
            survey_image = None
            if survey.survey_image:
                survey_image = base64.b64encode(survey.survey_image).decode('utf-8')

            # Build response data
            survey_data = {
                'id': survey.id,
                'name': survey.name,
                'survey_uuid': survey.survey_uuid,
                'project_id': survey.project_id.id if survey.project_id else None,
                'project_name': survey.project_id.name if survey.project_id else '',
                'village_id': survey.village_id.id if survey.village_id else None,
                'village_name': survey.village_id.name if survey.village_id else '',
                'department_id': survey.department_id.id if survey.department_id else None,
                'department_name': survey.department_id.name if survey.department_id else '',
                'tehsil_id': survey.tehsil_id.id if survey.tehsil_id else None,
                'tehsil_name': survey.tehsil_id.name if survey.tehsil_id else '',
                'district_name': survey.district_name or '',
                'khasra_number': survey.khasra_number or '',
                'total_area': survey.total_area,
                'acquired_area': survey.acquired_area,
                'has_traded_land': survey.has_traded_land or 'no',
                'traded_land_area': survey.traded_land_area or 0.0,
                'survey_date': survey.survey_date.strftime('%Y-%m-%d') if survey.survey_date else None,
                'crop_type': survey.crop_type_id.id if survey.crop_type_id else None,
                'crop_type_name': survey.crop_type_id.name if survey.crop_type_id else '',
                'crop_type_code': survey.crop_type_id.code if survey.crop_type_id else '',
                'irrigation_type': survey.irrigation_type,
                'undeveloped_tree_count': survey.undeveloped_tree_count or 0,
                'semi_developed_tree_count': survey.semi_developed_tree_count or 0,
                'fully_developed_tree_count': survey.fully_developed_tree_count or 0,
                'tree_count': survey.tree_count or 0,
                'tree_lines': [{
                    'id': line.id,
                    'development_stage': line.development_stage,
                    'development_stage_name': dict(line._fields['development_stage'].selection).get(line.development_stage, ''),
                    'tree_master_id': line.tree_master_id.id,
                    'tree_name': line.tree_master_id.name,
                    'quantity': line.quantity,
                    'rate': line.rate,
                    'total_amount': line.total_amount
                } for line in survey.tree_line_ids],
                'has_house': survey.has_house,
                'house_type': survey.house_type,
                'house_area': survey.house_area,
                'has_shed': survey.has_shed,
                'shed_area': survey.shed_area,
                'has_well': survey.has_well,
                'well_type': survey.well_type,
                'has_tubewell': survey.has_tubewell,
                'has_pond': survey.has_pond,
                'trees_description': survey.trees_description or '',
                'latitude': survey.latitude,
                'longitude': survey.longitude,
                'location_accuracy': survey.location_accuracy,
                'location_timestamp': survey.location_timestamp.strftime('%Y-%m-%d %H:%M:%S') if survey.location_timestamp else None,
                'remarks': survey.remarks or '',
                'state': survey.state,
                'notification4_generated': survey.notification4_generated,
                'survey_image': survey_image,
                'landowner_ids': [{
                    'id': lo.id,
                    'name': lo.name,
                    'father_name': lo.father_name or '',
                    'gender': lo.gender,
                    'age': lo.age,
                    'aadhar_number': lo.aadhar_number or '',
                    'pan_number': lo.pan_number or '',
                    'phone': lo.phone or '',
                    'owner_address': lo.owner_address or '',
                } for lo in survey.landowner_ids],
            }

            return Response(
                json.dumps({
                    'success': True,
                    'data': survey_data
                }),
                status=200,
                content_type='application/json'
            )

        except Exception as e:
            _logger.error(f"Error in get_survey_details: {str(e)}", exc_info=True)
            return Response(
                json.dumps({'error': str(e)}),
                status=500,
                content_type='application/json'
            )

    @http.route('/api/bhuarjan/surveys', type='http', auth='public', methods=['GET'], csrf=False)
    @check_permission
    def list_surveys(self, **kwargs):
        """
        List surveys with optional filters
        Query params: project_id, village_id, state, limit, offset
        Returns: JSON list of surveys
        """
        try:
            # Get query parameters
            project_id = request.httprequest.args.get('project_id', type=int)
            village_id = request.httprequest.args.get('village_id', type=int)
            state = request.httprequest.args.get('state')
            limit = request.httprequest.args.get('limit', type=int) or 100
            offset = request.httprequest.args.get('offset', type=int) or 0

            # Build domain
            domain = []
            if project_id:
                domain.append(('project_id', '=', project_id))
            if village_id:
                domain.append(('village_id', '=', village_id))
            if state:
                domain.append(('state', '=', state))

            # Search surveys
            surveys = request.env['bhu.survey'].sudo().search(domain, limit=limit, offset=offset, order='create_date desc')

            # Build response
            surveys_data = []
            for survey in surveys:
                surveys_data.append({
                    'id': survey.id,
                    'name': survey.name,
                    'survey_uuid': survey.survey_uuid,
                    'khasra_number': survey.khasra_number or '',
                    'project_id': survey.project_id.id if survey.project_id else None,
                    'project_name': survey.project_id.name if survey.project_id else '',
                    'village_id': survey.village_id.id if survey.village_id else None,
                    'village_name': survey.village_id.name if survey.village_id else '',
                    'survey_date': survey.survey_date.strftime('%Y-%m-%d') if survey.survey_date else None,
                    'total_area': survey.total_area,
                    'acquired_area': survey.acquired_area,
                    'has_traded_land': survey.has_traded_land or 'no',
                    'traded_land_area': survey.traded_land_area or 0.0,
                    'state': survey.state,
                    'notification4_generated': survey.notification4_generated,
                })

            # Get total count
            total_count = request.env['bhu.survey'].sudo().search_count(domain)

            return Response(
                json.dumps({
                    'success': True,
                    'data': surveys_data,
                    'total': total_count,
                    'limit': limit,
                    'offset': offset
                }),
                status=200,
                content_type='application/json'
            )

        except Exception as e:
            _logger.error(f"Error in list_surveys: {str(e)}", exc_info=True)
            return Response(
                json.dumps({'error': str(e)}),
                status=500,
                content_type='application/json'
            )

    @http.route('/api/bhuarjan/form10/download', type='http', auth='public', methods=['GET'], csrf=False)
    # @check_permission
    def download_form10(self, **kwargs):
        """
        Download Form 10 (Bulk Table Report) PDF based on village_id
        Query params: village_id (required), project_id (optional), limit (optional, max 100)
        Returns: PDF file
        """
        try:
            _logger.info("Form 10 download API called")
            
            # Get query parameters
            village_id = request.httprequest.args.get('village_id', type=int)
            project_id = request.httprequest.args.get('project_id', type=int)
            limit = min(request.httprequest.args.get('limit', type=int, default=20), 50)  # Default 20, max 50

            if not village_id:
                _logger.warning("Form 10 download: village_id is missing")
                return Response(
                    json.dumps({'error': 'village_id is required'}),
                    status=400,
                    content_type='application/json'
                )

            _logger.info(f"Form 10 download: village_id={village_id}, project_id={project_id}, limit={limit}")

            # Verify village exists
            village = request.env['bhu.village'].sudo().browse(village_id)
            if not village.exists():
                _logger.warning(f"Form 10 download: Village {village_id} not found")
                return Response(
                    json.dumps({'error': 'Village not found'}),
                    status=404,
                    content_type='application/json'
                )

            # Build domain to get surveys for the village
            domain = [('village_id', '=', village_id)]
            
            # If project_id is provided, filter by project as well
            if project_id:
                # Verify project exists
                project = request.env['bhu.project'].sudo().browse(project_id)
                if not project.exists():
                    _logger.warning(f"Form 10 download: Project {project_id} not found")
                    return Response(
                        json.dumps({'error': 'Project not found'}),
                        status=404,
                        content_type='application/json'
                    )
                domain.append(('project_id', '=', project_id))
                project_name = project.name
            else:
                project_name = 'All'

            _logger.info(f"Form 10 download: Searching surveys with domain {domain}")

            # Get all surveys for the village (and project if specified)
            # Limit to prevent server overload
            surveys = request.env['bhu.survey'].sudo().with_context(
                active_test=False,
                bhuarjan_current_project_id=False
            ).search(domain, order='id', limit=limit)

            _logger.info(f"Form 10 download: Found {len(surveys)} surveys")

            if not surveys:
                _logger.warning(f"Form 10 download: No surveys found for village_id={village_id}")
                return Response(
                    json.dumps({'error': f'No surveys found for village_id={village_id}' + (f' and project_id={project_id}' if project_id else '')}),
                    status=404,
                    content_type='application/json'
                )

            # Get the Form 10 bulk table report
            _logger.info("Form 10 download: Getting report action")
            try:
                # Use sudo() to bypass access rights when getting the report action
                report_action = request.env['ir.actions.report'].sudo().search([
                    ('report_name', '=', 'bhuarjan.form10_bulk_table_report')
                ], limit=1)
                
                if not report_action:
                    # Fallback: try using ir.model.data
                    _logger.info("Form 10 download: Report not found by name, trying ir.model.data")
                    try:
                        report_data = request.env['ir.model.data'].sudo().search([
                            ('module', '=', 'bhuarjan'),
                            ('name', '=', 'action_report_form10_bulk_table')
                        ], limit=1)
                        if report_data and report_data.res_id:
                            report_action = request.env['ir.actions.report'].sudo().browse(report_data.res_id)
                    except Exception as e:
                        _logger.error(f"Form 10 download: Error in fallback: {str(e)}", exc_info=True)
                
                if not report_action or not report_action.exists():
                    _logger.error("Form 10 download: Report action not found")
                    return Response(
                        json.dumps({'error': 'Form 10 report not found'}),
                        status=404,
                        content_type='application/json'
                    )
                
                _logger.info(f"Form 10 download: Report action found: {report_action.id}, report_name: {report_action.report_name}")
            except Exception as e:
                _logger.error(f"Form 10 download: Error getting report action: {str(e)}", exc_info=True)
                return Response(
                    json.dumps({'error': f'Error accessing report: {str(e)}'}),
                    status=500,
                    content_type='application/json'
                )

            # Convert surveys to list of IDs for PDF rendering
            res_ids = [int(sid) for sid in surveys.ids]
            
            _logger.info(f"Form 10 download: Rendering PDF for {len(res_ids)} surveys: {res_ids[:10]}..." if len(res_ids) > 10 else f"Form 10 download: Rendering PDF for {len(res_ids)} surveys: {res_ids}")
            
            if not res_ids:
                _logger.warning("Form 10 download: No survey IDs found")
                return Response(
                    json.dumps({'error': 'No survey IDs found'}),
                    status=404,
                    content_type='application/json'
                )

            # Generate PDF with error handling
            report_name = report_action.report_name
            _logger.info(f"Form 10 download: Starting PDF generation with report_name: {report_name} for {len(res_ids)} surveys")
            
            try:
                # Use with_context to ensure clean environment
                pdf_result = report_action.sudo().with_context(
                    lang='en_US',
                    tz='UTC'
                )._render_qweb_pdf(report_name, res_ids, data={})
                _logger.info(f"Form 10 download: PDF generation completed, result type: {type(pdf_result)}")
            except MemoryError as mem_error:
                _logger.error(f"Form 10 download: Memory error during PDF generation: {str(mem_error)}")
                return Response(
                    json.dumps({'error': 'PDF generation failed due to memory constraints. Please reduce the number of surveys or contact administrator.'}),
                    status=500,
                    content_type='application/json'
                )
            except Exception as render_error:
                _logger.error(f"Form 10 download: PDF rendering failed: {str(render_error)}", exc_info=True)
                return Response(
                    json.dumps({'error': f'Error generating PDF: {str(render_error)}'}),
                    status=500,
                    content_type='application/json'
                )

            if not pdf_result:
                return Response(
                    json.dumps({'error': 'Error generating PDF'}),
                    status=500,
                    content_type='application/json'
                )

            # Extract PDF bytes
            _logger.info("Form 10 download: Extracting PDF bytes from result")
            if isinstance(pdf_result, (tuple, list)) and len(pdf_result) > 0:
                pdf_data = pdf_result[0]
            else:
                pdf_data = pdf_result

            if not isinstance(pdf_data, bytes):
                _logger.error(f"Form 10 download: Invalid PDF data type: {type(pdf_data)}")
                return Response(
                    json.dumps({'error': 'Invalid PDF data'}),
                    status=500,
                    content_type='application/json'
                )

            _logger.info(f"Form 10 download: PDF data extracted, size: {len(pdf_data)} bytes")

            # Generate filename - sanitize to ASCII only for HTTP headers
            def sanitize_filename(name):
                """Remove non-ASCII characters and sanitize for HTTP headers"""
                if not name:
                    return 'Unknown'
                # Convert to string and encode to ASCII, ignoring non-ASCII characters
                try:
                    # First, try to encode to ASCII and ignore errors
                    name = name.encode('ascii', 'ignore').decode('ascii')
                except (UnicodeEncodeError, UnicodeDecodeError):
                    # If encoding fails, remove all non-ASCII characters manually
                    name = ''.join(char for char in name if ord(char) < 128)
                
                # Remove any remaining non-alphanumeric characters except underscores and hyphens
                name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
                # Replace multiple underscores/hyphens with single underscore
                name = re.sub(r'[_\-\s]+', '_', name)
                # Remove leading/trailing underscores
                name = name.strip('_')
                return name[:50] if name else 'Unknown'
            
            village_name_ascii = sanitize_filename(village.name if village.name else 'Village')
            filename = f"Form10_{village_name_ascii}.pdf"
            if project_id:
                project_name_ascii = sanitize_filename(project_name if project_name else 'Project')
                filename = f"Form10_{project_name_ascii}_{village_name_ascii}.pdf"

            _logger.info(f"Form 10 download: Returning PDF response with filename: {filename}")

            # Return PDF
            response = request.make_response(
                pdf_data,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', f'attachment; filename="{filename}"'),
                    ('Content-Length', str(len(pdf_data)))
                ]
            )
            _logger.info("Form 10 download: PDF response created successfully")
            return response

        except Exception as e:
            _logger.error(f"Error in download_form10: {str(e)}", exc_info=True)
            return Response(
                json.dumps({'error': str(e)}),
                status=500,
                content_type='application/json'
            )

    @http.route('/api/bhuarjan/landowner', type='http', auth='public', methods=['POST'], csrf=False)
    @check_permission
    def create_landowner(self, **kwargs):
        """
        Create a new landowner
        Accepts: JSON data with landowner fields
        Returns: Created landowner details
        """
        try:
            # Parse request data
            data = json.loads(request.httprequest.data.decode('utf-8') or '{}')

            # Prepare landowner values
            landowner_vals = {
                'name': data.get('name'),
                'father_name': data.get('father_name'),
                'mother_name': data.get('mother_name'),
                'spouse_name': data.get('spouse_name'),
                'age': data.get('age'),
                'gender': data.get('gender'),
                'phone': data.get('phone'),
                'village_id': data.get('village_id'),
                'tehsil_id': data.get('tehsil_id'),
                'district_id': data.get('district_id'),
                'owner_address': data.get('owner_address'),
                'aadhar_number': data.get('aadhar_number'),
                'pan_number': data.get('pan_number'),
                'bank_name': data.get('bank_name'),
                'bank_branch': data.get('bank_branch'),
                'account_number': data.get('account_number'),
                'ifsc_code': data.get('ifsc_code'),
                'account_holder_name': data.get('account_holder_name'),
            }

            # Handle document uploads if provided (base64 encoded)
            if data.get('aadhar_card'):
                try:
                    aadhar_data = data['aadhar_card']
                    if isinstance(aadhar_data, str):
                        if ',' in aadhar_data:
                            aadhar_data = aadhar_data.split(',')[1]
                        landowner_vals['aadhar_card'] = base64.b64decode(aadhar_data)
                except Exception as e:
                    _logger.warning(f"Error processing Aadhar card: {str(e)}")

            if data.get('pan_card'):
                try:
                    pan_data = data['pan_card']
                    if isinstance(pan_data, str):
                        if ',' in pan_data:
                            pan_data = pan_data.split(',')[1]
                        landowner_vals['pan_card'] = base64.b64decode(pan_data)
                except Exception as e:
                    _logger.warning(f"Error processing PAN card: {str(e)}")

            # Create landowner
            landowner = request.env['bhu.landowner'].sudo().create(landowner_vals)

            # Return created landowner details
            return Response(
                json.dumps({
                    'success': True,
                    'data': {
                        'id': landowner.id,
                        'name': landowner.name,
                        'father_name': landowner.father_name or '',
                        'gender': landowner.gender,
                        'age': landowner.age,
                        'aadhar_number': landowner.aadhar_number or '',
                        'pan_number': landowner.pan_number or '',
                        'phone': landowner.phone or '',
                        'village_id': landowner.village_id.id if landowner.village_id else None,
                        'village_name': landowner.village_id.name if landowner.village_id else '',
                        'owner_address': landowner.owner_address or '',
                    }
                }),
                status=201,
                content_type='application/json'
            )

        except Exception as e:
            _logger.error(f"Error in create_landowner: {str(e)}", exc_info=True)
            return Response(
                json.dumps({'error': str(e)}),
                status=500,
                content_type='application/json'
            )

    @http.route('/api/bhuarjan/s3/presigned-urls', type='http', auth='public', methods=['POST'], csrf=False)
    # @check_permission
    def generate_s3_presigned_urls(self, **kwargs):
        """
        Generate S3 presigned URLs for file upload (supports single or multiple files)
        Accepts: JSON data with file_names (list) or file_name (string) and survey_id
        Returns: Presigned URLs for S3 upload
        """
        try:
            if not HAS_BOTO3:
                return Response(
                    json.dumps({'error': 'boto3 library is not installed. Please install it to use S3 presigned URLs.'}),
                    status=500,
                    content_type='application/json'
                )
            
            # Parse request data
            data = json.loads(request.httprequest.data.decode('utf-8') or '{}')
            
            # Support both single file_name and multiple file_names
            file_names = data.get('file_names', [])
            file_name = data.get('file_name')
            survey_id = data.get('survey_id')
            
            # Track if single file was provided
            is_single_file = False
            
            # If single file_name provided, convert to list
            if file_name and not file_names:
                file_names = [file_name]
                is_single_file = True
            
            if not file_names or not isinstance(file_names, list) or len(file_names) == 0:
                return Response(
                    json.dumps({'error': 'file_names (list) or file_name (string) is required'}),
                    status=400,
                    content_type='application/json'
                )
            
            if not survey_id:
                return Response(
                    json.dumps({'error': 'survey_id is required'}),
                    status=400,
                    content_type='application/json'
                )
            
            # Get survey to find project
            survey = request.env['bhu.survey'].sudo().browse(survey_id)
            if not survey.exists():
                return Response(
                    json.dumps({'error': f'Survey with ID {survey_id} not found'}),
                    status=404,
                    content_type='application/json'
                )
            
            if not survey.project_id:
                return Response(
                    json.dumps({'error': 'Survey does not have an associated project'}),
                    status=400,
                    content_type='application/json'
                )
            
            # Get AWS settings from global settings master
            settings_master = request.env['bhuarjan.settings.master'].sudo().search([
                ('active', '=', True)
            ], limit=1)
            
            if not settings_master:
                return Response(
                    json.dumps({'error': 'AWS settings not found. Please configure AWS settings in Bhuarjan Settings Master.'}),
                    status=404,
                    content_type='application/json'
                )
            
            if not settings_master.s3_bucket_name:
                return Response(
                    json.dumps({'error': 'S3 bucket name is not configured in settings'}),
                    status=400,
                    content_type='application/json'
                )
            
            if not settings_master.aws_access_key or not settings_master.aws_secret_key:
                return Response(
                    json.dumps({'error': 'AWS credentials are not configured in settings'}),
                    status=400,
                    content_type='application/json'
                )
            
            # Get AWS region (default to ap-south-1 if not set)
            aws_region = settings_master.aws_region or 'ap-south-1'
            
            # Create S3 client
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings_master.aws_access_key,
                aws_secret_access_key=settings_master.aws_secret_key,
                region_name=aws_region
            )
            
            # Generate presigned URL (valid for 1 hour)
            expiration = timedelta(hours=1)
            expires_at = datetime.datetime.now(timezone.utc) + expiration
            
            # Generate presigned URLs for all files
            presigned_urls = []
            errors = []
            
            for file_name in file_names:
                try:
                    # Generate S3 key (path) for the file
                    s3_key = f"surveys/{survey_id}/{file_name}"
                    
                    # Determine content type based on file extension
                    content_type = 'application/octet-stream'  # default
                    file_ext = file_name.lower().split('.')[-1] if '.' in file_name else ''
                    content_type_map = {
                        'jpg': 'image/jpeg',
                        'jpeg': 'image/jpeg',
                        'png': 'image/png',
                        'gif': 'image/gif',
                        'pdf': 'application/pdf',
                        'doc': 'application/msword',
                        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        'xls': 'application/vnd.ms-excel',
                        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    }
                    if file_ext in content_type_map:
                        content_type = content_type_map[file_ext]
                    
                    # Generate presigned URL for PUT operation
                    presigned_url = s3_client.generate_presigned_url(
                        'put_object',
                        Params={
                            'Bucket': settings_master.s3_bucket_name,
                            'Key': s3_key,
                            'ContentType': content_type
                        },
                        ExpiresIn=int(expiration.total_seconds())
                    )
                    
                    presigned_urls.append({
                        'file_name': file_name,
                        'presigned_url': presigned_url,
                        's3_key': s3_key,
                        'bucket_name': settings_master.s3_bucket_name,
                        'content_type': content_type,
                        'expires_in': int(expiration.total_seconds()),
                        'expires_at': expires_at.isoformat()
                    })
                    
                except ClientError as e:
                    error_msg = f"Error generating presigned URL for {file_name}: {str(e)}"
                    _logger.error(error_msg, exc_info=True)
                    errors.append({
                        'file_name': file_name,
                        'error': str(e)
                    })
                except Exception as e:
                    error_msg = f"Unexpected error for {file_name}: {str(e)}"
                    _logger.error(error_msg, exc_info=True)
                    errors.append({
                        'file_name': file_name,
                        'error': str(e)
                    })
            
            # Return response
            # If single file, return simplified response for backward compatibility
            if is_single_file and len(presigned_urls) == 1:
                return Response(
                    json.dumps({
                        'success': True,
                        'data': presigned_urls[0]
                    }),
                    status=200,
                    content_type='application/json'
                )
            
            # Multiple files response
            response_data = {
                'success': True,
                'data': {
                    'presigned_urls': presigned_urls,
                    'total_files': len(file_names),
                    'successful': len(presigned_urls),
                    'failed': len(errors),
                    'survey_id': survey_id
                }
            }
            
            if errors:
                response_data['data']['errors'] = errors
            
            return Response(
                json.dumps(response_data),
                status=200,
                content_type='application/json'
            )
            
        except Exception as e:
            _logger.error(f"Error in generate_s3_presigned_urls: {str(e)}", exc_info=True)
            return Response(
                json.dumps({'error': str(e)}),
                status=500,
                content_type='application/json'
            )

    @http.route('/api/bhuarjan/landowners', type='http', auth='public', methods=['GET'], csrf=False)
    @check_permission
    def get_landowners(self, **kwargs):
        """
        Get landowners based on survey_id and/or village_id (both optional)
        Query params: survey_id (optional), village_id (optional), limit (optional, default 100), offset (optional, default 0)
        Returns: JSON list of landowners
        """
        try:
            survey_id = request.httprequest.args.get('survey_id', type=int)
            village_id = request.httprequest.args.get('village_id', type=int)
            limit = request.httprequest.args.get('limit', type=int) or 100
            offset = request.httprequest.args.get('offset', type=int) or 0

            domain = []
            
            # Filter by survey_id if provided
            if survey_id:
                survey = request.env['bhu.survey'].sudo().browse(survey_id)
                if not survey.exists():
                    return Response(
                        json.dumps({'error': f'Survey with ID {survey_id} not found'}),
                        status=404,
                        content_type='application/json'
                    )
                # Get landowners from the survey
                domain.append(('survey_ids', 'in', [survey_id]))
            
            # Filter by village_id if provided
            if village_id:
                village = request.env['bhu.village'].sudo().browse(village_id)
                if not village.exists():
                    return Response(
                        json.dumps({'error': f'Village with ID {village_id} not found'}),
                        status=404,
                        content_type='application/json'
                    )
                domain.append(('village_id', '=', village_id))

            landowners = request.env['bhu.landowner'].sudo().search(domain, limit=limit, offset=offset, order='name')

            landowners_data = []
            for landowner in landowners:
                landowners_data.append({
                    'id': landowner.id,
                    'name': landowner.name or '',
                    'father_name': landowner.father_name or '',
                    'mother_name': landowner.mother_name or '',
                    'spouse_name': landowner.spouse_name or '',
                    'age': landowner.age or 0,
                    'gender': landowner.gender or '',
                    'phone': landowner.phone or '',
                    'village_id': landowner.village_id.id if landowner.village_id else None,
                    'village_name': landowner.village_id.name if landowner.village_id else '',
                    'tehsil_id': landowner.tehsil_id.id if landowner.tehsil_id else None,
                    'tehsil_name': landowner.tehsil_id.name if landowner.tehsil_id else '',
                    'district_id': landowner.district_id.id if landowner.district_id else None,
                    'district_name': landowner.district_id.name if landowner.district_id else '',
                    'owner_address': landowner.owner_address or '',
                    'aadhar_number': landowner.aadhar_number or '',
                    'pan_number': landowner.pan_number or '',
                    'bank_name': landowner.bank_name or '',
                    'bank_branch': landowner.bank_branch or '',
                    'account_number': landowner.account_number or '',
                    'ifsc_code': landowner.ifsc_code or '',
                    'account_holder_name': landowner.account_holder_name or '',
                    'survey_ids': landowner.survey_ids.ids if landowner.survey_ids else [],
                })

            total_count = request.env['bhu.landowner'].sudo().search_count(domain)

            return Response(
                json.dumps({
                    'success': True,
                    'data': landowners_data,
                    'total': total_count,
                    'limit': limit,
                    'offset': offset
                }),
                status=200,
                content_type='application/json'
            )

        except Exception as e:
            _logger.error(f"Error in get_landowners: {str(e)}", exc_info=True)
            return Response(
                json.dumps({'error': str(e)}),
                status=500,
                content_type='application/json'
            )

    @http.route('/api/bhuarjan/survey/<int:survey_id>', type='http', auth='public', methods=['PATCH'], csrf=False)
    @check_permission
    def update_survey(self, survey_id, **kwargs):
        """
        Update survey (PATCH) - only allowed if state is 'draft' or 'submitted'
        Request body: JSON with fields to update
        Returns: Updated survey data
        """
        try:
            survey = request.env['bhu.survey'].sudo().browse(survey_id)
            if not survey.exists():
                return Response(
                    json.dumps({'error': f'Survey with ID {survey_id} not found'}),
                    status=404,
                    content_type='application/json'
                )

            # Check if survey can be edited (only draft and submitted states allow editing)
            if survey.state not in ('draft', 'submitted'):
                return Response(
                    json.dumps({
                        'error': f'Survey cannot be edited. Current state: {survey.state}. Only surveys in draft or submitted state can be edited.'
                    }),
                    status=400,
                    content_type='application/json'
                )

            # Parse request data
            data = json.loads(request.httprequest.data.decode('utf-8') or '{}')

            # List of fields that can be updated via API
            allowed_fields = [
                'project_id', 'department_id', 'village_id', 'tehsil_id', 'survey_date',
                'khasra_number', 'total_area', 'acquired_area', 'has_traded_land', 'traded_land_area',
                'crop_type_id', 'irrigation_type', 'undeveloped_tree_count', 'semi_developed_tree_count', 'fully_developed_tree_count',
                'has_house', 'house_type', 'house_area', 'has_shed', 'shed_area',
                'has_well', 'well_type', 'has_tubewell', 'has_pond',
                'trees_description', 'landowner_ids', 'survey_image', 'survey_image_filename',
                'remarks'
            ]
            
            # Note: 'crop_type' is handled separately above and mapped to 'crop_type_id'

            # Handle crop_type - accept crop_type (ID) and map to crop_type_id in model
            if 'crop_type' in data:
                crop_type_value = data.get('crop_type')
                if isinstance(crop_type_value, int):
                    # If it's an integer, treat it as land type ID
                    data['crop_type_id'] = crop_type_value
                elif isinstance(crop_type_value, str):
                    # Backward compatibility: map old crop_type string to land type ID
                    crop_type_str = crop_type_value.lower()
                    if crop_type_str in ('single', 'single1'):
                        single_crop = request.env['bhu.land.type'].sudo().search([('code', '=', 'SINGLE_CROP')], limit=1)
                        data['crop_type_id'] = single_crop.id if single_crop else None
                    elif crop_type_str in ('double', 'double1'):
                        double_crop = request.env['bhu.land.type'].sudo().search([('code', '=', 'DOUBLE_CROP')], limit=1)
                        data['crop_type_id'] = double_crop.id if double_crop else None
                # Remove crop_type from data as we'll use crop_type_id internally
                data.pop('crop_type', None)
            elif 'crop_type_id' in data:
                # Also support crop_type_id for backward compatibility
                pass  # Keep it as is

            # Validate area values if they are being updated
            if 'total_area' in data or 'acquired_area' in data:
                # Get the values that will be used after update
                # If field is in data, use the new value; otherwise use existing value from survey
                total_area = data.get('total_area') if 'total_area' in data else survey.total_area
                acquired_area = data.get('acquired_area') if 'acquired_area' in data else survey.acquired_area
                
                # Validate total_area if it's being updated or if we need to check the relationship
                if 'total_area' in data:
                    if total_area is None or total_area <= 0:
                        return Response(
                            json.dumps({
                                'error': 'Validation Error',
                                'message': 'Total Area must be greater than 0.'
                            }),
                            status=400,
                            content_type='application/json'
                        )
                
                # Validate acquired_area if it's being updated or if we need to check the relationship
                if 'acquired_area' in data:
                    if acquired_area is None or acquired_area <= 0:
                        return Response(
                            json.dumps({
                                'error': 'Validation Error',
                                'message': 'Acquired Area must be greater than 0.'
                            }),
                            status=400,
                            content_type='application/json'
                        )
                
                # Validate relationship between areas (only if both values are available)
                if total_area is not None and acquired_area is not None:
                    if acquired_area > total_area:
                        return Response(
                            json.dumps({
                                'error': 'Validation Error',
                                'message': 'Acquired Area cannot be greater than Total Area.'
                            }),
                            status=400,
                            content_type='application/json'
                        )
            
            # Prepare update values
            update_vals = {}
            for field, value in data.items():
                if field in allowed_fields:
                    # Handle well_type - no conversion needed, use as is
                    # Handle Many2many fields (landowner_ids)
                    if field == 'landowner_ids' and isinstance(value, list):
                        update_vals[field] = [(6, 0, value)]  # Replace all
                    # Handle Many2one fields
                    elif field.endswith('_id') and value:
                        update_vals[field] = value
                    # Handle binary fields (survey_image)
                    elif field == 'survey_image' and value:
                        # If base64 encoded, decode it
                        if isinstance(value, str) and value.startswith('data:'):
                            # Extract base64 part
                            base64_data = value.split(',')[1] if ',' in value else value
                            update_vals[field] = base64.b64decode(base64_data)
                        else:
                            update_vals[field] = value
                    # Handle text fields (trees_description, remarks) - allow None and empty strings
                    elif field in ['trees_description', 'remarks']:
                        update_vals[field] = value if value is not None else ''
                    # Handle other fields
                    else:
                        update_vals[field] = value
                else:
                    _logger.warning(f"Field '{field}' is not allowed to be updated via API")

            if not update_vals:
                return Response(
                    json.dumps({'error': 'No valid fields to update'}),
                    status=400,
                    content_type='application/json'
                )

            # Update the survey
            survey.write(update_vals)
            
            # Handle tree lines (if provided)
            if 'tree_lines' in data and isinstance(data['tree_lines'], list):
                tree_line_vals = []
                for tree_line in data['tree_lines']:
                    if isinstance(tree_line, dict) and 'development_stage' in tree_line:
                        # Support both tree_master_id (integer) and tree_name (string) for tree selection
                        tree_master_id = None
                        if 'tree_master_id' in tree_line and tree_line['tree_master_id']:
                            tree_master_id = tree_line['tree_master_id']
                        elif 'tree_name' in tree_line and tree_line['tree_name']:
                            # Look up tree by name
                            tree_master = request.env['bhu.tree.master'].sudo().search([
                                ('name', '=', tree_line['tree_name'])
                            ], limit=1)
                            if tree_master:
                                tree_master_id = tree_master.id
                            else:
                                return Response(
                                    json.dumps({
                                        'error': f'Tree with name "{tree_line["tree_name"]}" not found in tree master'
                                    }),
                                    status=400,
                                    content_type='application/json'
                                )
                        else:
                            return Response(
                                json.dumps({
                                    'error': 'Either tree_master_id or tree_name must be provided for each tree line'
                                }),
                                status=400,
                                content_type='application/json'
                            )
                        
                        # Validate development_stage
                        development_stage = tree_line.get('development_stage')
                        if development_stage not in ('undeveloped', 'semi_developed', 'fully_developed'):
                            return Response(
                                json.dumps({
                                    'error': f'Invalid development_stage: {development_stage}. Must be one of: undeveloped, semi_developed, fully_developed'
                                }),
                                status=400,
                                content_type='application/json'
                            )
                        
                        tree_line_vals.append((0, 0, {
                            'tree_master_id': tree_master_id,
                            'development_stage': development_stage,
                            'quantity': tree_line.get('quantity', 1)
                        }))
                
                # Replace all tree lines with new ones
                if tree_line_vals:
                    survey.write({'tree_line_ids': [(5, 0, 0)] + tree_line_vals})

            # Return updated survey data
            survey_data = {
                'id': survey.id,
                'name': survey.name or '',
                'survey_uuid': survey.survey_uuid or '',
                'project_id': survey.project_id.id if survey.project_id else None,
                'project_name': survey.project_id.name if survey.project_id else '',
                'department_id': survey.department_id.id if survey.department_id else None,
                'department_name': survey.department_id.name if survey.department_id else '',
                'village_id': survey.village_id.id if survey.village_id else None,
                'village_name': survey.village_id.name if survey.village_id else '',
                'tehsil_id': survey.tehsil_id.id if survey.tehsil_id else None,
                'tehsil_name': survey.tehsil_id.name if survey.tehsil_id else '',
                'survey_date': survey.survey_date.strftime('%Y-%m-%d') if survey.survey_date else '',
                'khasra_number': survey.khasra_number or '',
                'total_area': survey.total_area or 0.0,
                'acquired_area': survey.acquired_area or 0.0,
                'has_traded_land': survey.has_traded_land or 'no',
                'traded_land_area': survey.traded_land_area or 0.0,
                'crop_type': survey.crop_type_id.id if survey.crop_type_id else None,
                'crop_type_name': survey.crop_type_id.name if survey.crop_type_id else '',
                'crop_type_code': survey.crop_type_id.code if survey.crop_type_id else '',
                'irrigation_type': survey.irrigation_type or '',
                'undeveloped_tree_count': survey.undeveloped_tree_count or 0,
                'semi_developed_tree_count': survey.semi_developed_tree_count or 0,
                'fully_developed_tree_count': survey.fully_developed_tree_count or 0,
                'tree_count': survey.tree_count or 0,
                'tree_lines': [{
                    'id': line.id,
                    'development_stage': line.development_stage,
                    'development_stage_name': dict(line._fields['development_stage'].selection).get(line.development_stage, ''),
                    'tree_master_id': line.tree_master_id.id,
                    'tree_name': line.tree_master_id.name,
                    'quantity': line.quantity,
                    'rate': line.rate,
                    'total_amount': line.total_amount
                } for line in survey.tree_line_ids],
                'has_house': survey.has_house or '',
                'house_type': survey.house_type or '',
                'house_area': survey.house_area or 0.0,
                'has_shed': survey.has_shed or '',
                'shed_area': survey.shed_area or 0.0,
                'has_well': survey.has_well or '',
                'well_type': survey.well_type or '',
                'has_tubewell': survey.has_tubewell or '',
                'has_pond': survey.has_pond or '',
                'trees_description': survey.trees_description or '',
                'landowner_ids': survey.landowner_ids.ids if survey.landowner_ids else [],
                'state': survey.state or 'draft',
                'remarks': survey.remarks or '',
            }

            return Response(
                json.dumps({
                    'success': True,
                    'message': 'Survey updated successfully',
                    'data': survey_data
                }),
                status=200,
                content_type='application/json'
            )

        except json.JSONDecodeError as e:
            _logger.error(f"JSON decode error in update_survey: {str(e)}", exc_info=True)
            return Response(
                json.dumps({'error': 'Invalid JSON in request body', 'details': str(e)}),
                status=400,
                content_type='application/json'
            )
        except ValidationError as ve:
            _logger.error(f"Validation error in update_survey: {str(ve)}", exc_info=True)
            return Response(
                json.dumps({
                    'error': 'Validation Error',
                    'message': str(ve)
                }),
                status=400,
                content_type='application/json'
            )
        except Exception as e:
            _logger.error(f"Error in update_survey: {str(e)}", exc_info=True)
            return Response(
                json.dumps({'error': str(e)}),
                status=500,
                content_type='application/json'
            )

    @http.route('/api/bhuarjan/survey/<int:survey_id>', type='http', auth='public', methods=['DELETE'], csrf=False)
    @check_permission
    def delete_survey(self, survey_id, **kwargs):
        """
        Delete a survey
        Only allowed if survey is in 'draft' or 'submitted' state
        Returns: Success message
        """
        try:
            survey = request.env['bhu.survey'].sudo().browse(survey_id)
            if not survey.exists():
                return Response(
                    json.dumps({
                        'success': False,
                        'error': 'Survey not found',
                        'message': f'Survey with ID {survey_id} does not exist'
                    }),
                    status=404,
                    content_type='application/json'
                )

            # Check if survey can be deleted (only draft and submitted states allow deletion)
            if survey.state not in ('draft', 'submitted'):
                return Response(
                    json.dumps({
                        'success': False,
                        'error': 'Survey cannot be deleted',
                        'message': f'Survey cannot be deleted. Current state: {survey.state}. Only surveys in draft or submitted state can be deleted.'
                    }),
                    status=400,
                    content_type='application/json'
                )

            # Store survey details for response
            survey_name = survey.name
            survey_khasra = survey.khasra_number

            # Delete the survey
            survey.unlink()

            return Response(
                json.dumps({
                    'success': True,
                    'message': 'Survey deleted successfully',
                    'data': {
                        'id': survey_id,
                        'name': survey_name,
                        'khasra_number': survey_khasra
                    }
                }),
                status=200,
                content_type='application/json'
            )

        except ValidationError as ve:
            _logger.error(f"Validation error in delete_survey: {str(ve)}", exc_info=True)
            return Response(
                json.dumps({
                    'success': False,
                    'error': 'Validation Error',
                    'message': str(ve)
                }),
                status=400,
                content_type='application/json'
            )
        except Exception as e:
            _logger.error(f"Error in delete_survey: {str(e)}", exc_info=True)
            return Response(
                json.dumps({
                    'success': False,
                    'error': str(e)
                }),
                status=500,
                content_type='application/json'
            )

    @http.route('/api/bhuarjan/dashboard/village', type='http', auth='public', methods=['GET'], csrf=False)
    @check_permission
    def get_village_dashboard(self, **kwargs):
        """
        Get survey statistics dashboard for a village
        Query params: village_id (required)
        Returns: JSON with survey counts by state (total, draft, submitted, approved, rejected, locked)
        """
        try:
            village_id = request.httprequest.args.get('village_id', type=int)
            
            if not village_id:
                return Response(
                    json.dumps({'error': 'village_id is required'}),
                    status=400,
                    content_type='application/json'
                )

            # Verify village exists
            village = request.env['bhu.village'].sudo().browse(village_id)
            if not village.exists():
                return Response(
                    json.dumps({'error': f'Village with ID {village_id} not found'}),
                    status=404,
                    content_type='application/json'
                )

            # Get all surveys for this village
            all_surveys = request.env['bhu.survey'].sudo().search([('village_id', '=', village_id)])
            
            # Count surveys by state
            total_surveys = len(all_surveys)
            draft_count = len(all_surveys.filtered(lambda s: s.state == 'draft'))
            submitted_count = len(all_surveys.filtered(lambda s: s.state == 'submitted'))
            approved_count = len(all_surveys.filtered(lambda s: s.state == 'approved'))
            rejected_count = len(all_surveys.filtered(lambda s: s.state == 'rejected'))
            locked_count = len(all_surveys.filtered(lambda s: s.state == 'locked'))

            # Build response
            dashboard_data = {
                'village_id': village_id,
                'village_name': village.name or '',
                'village_code': village.village_code or '',
                'statistics': {
                    'total_surveys': total_surveys,
                    'draft': draft_count,
                    'submitted': submitted_count,
                    'approved': approved_count,
                    'rejected': rejected_count,
                    'locked': locked_count
                },
                'breakdown': {
                    'draft_percentage': round((draft_count / total_surveys * 100) if total_surveys > 0 else 0, 2),
                    'submitted_percentage': round((submitted_count / total_surveys * 100) if total_surveys > 0 else 0, 2),
                    'approved_percentage': round((approved_count / total_surveys * 100) if total_surveys > 0 else 0, 2),
                    'rejected_percentage': round((rejected_count / total_surveys * 100) if total_surveys > 0 else 0, 2),
                    'locked_percentage': round((locked_count / total_surveys * 100) if total_surveys > 0 else 0, 2)
                }
            }

            return Response(
                json.dumps({
                    'success': True,
                    'data': dashboard_data
                }),
                status=200,
                content_type='application/json'
            )

        except Exception as e:
            _logger.error(f"Error in get_village_dashboard: {str(e)}", exc_info=True)
            return Response(
                json.dumps({'error': str(e)}),
                status=500,
                content_type='application/json'
            )

