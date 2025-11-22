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

_logger = logging.getLogger(__name__)


class BhuarjanAPIController(http.Controller):
    """REST API Controller for Bhuarjan mobile app"""
    
    def _get_selection_label(self, record, field_name, value):
        """Get the label for a selection field value"""
        if not value:
            return ''
        try:
            field = record._fields.get(field_name)
            if not field:
                return ''
            selection = field.selection
            # Handle callable selection (dynamic selection)
            if callable(selection):
                selection = selection(record)
            # Convert to dict and get label
            selection_dict = dict(selection) if selection else {}
            return selection_dict.get(value, '')
        except Exception:
            return ''

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
        Get all projects in a department with village objects
        Path param: department_id (required)
        Query params: user_id (optional), limit, offset
        Returns: JSON list of projects with village objects (filtered by user if user_id provided)
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
            user_id = request.httprequest.args.get('user_id', type=int)

            # Get user's villages if user_id is provided
            user_village_ids = []
            user_info = None
            if user_id:
                user = request.env['res.users'].sudo().browse(user_id)
                if not user.exists():
                    return Response(
                        json.dumps({
                            'success': False,
                            'error': 'User not found',
                            'message': f'User with ID {user_id} does not exist'
                        }),
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

            # Get projects from department
            projects = department.project_ids.sudo()
            total_count = len(projects)

            # Apply pagination
            paginated_projects = projects[offset:offset + limit] if projects else []

            # Build response
            projects_data = []
            for project in paginated_projects:
                # Filter villages based on user if user_id provided
                if user_id and user_village_ids:
                    project_villages = project.village_ids.filtered(
                        lambda v: v.id in user_village_ids
                    )
                else:
                    project_villages = project.village_ids
                
                # Build village objects
                villages_data = []
                for village in project_villages:
                    villages_data.append({
                        'id': village.id,
                        'name': village.name or '',
                        'village_code': village.village_code or '',
                        'village_uuid': village.village_uuid or '',
                        'district_id': village.district_id.id if village.district_id else None,
                        'district_name': village.district_id.name if village.district_id else '',
                        'tehsil_id': village.tehsil_id.id if village.tehsil_id else None,
                        'tehsil_name': village.tehsil_id.name if village.tehsil_id else '',
                        'pincode': village.pincode or '',
                    })
                
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
                    'villages': villages_data,
                    'village_count': len(villages_data),
                })

            response_data = {
                'success': True,
                'data': projects_data,
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'department_id': department_id,
                'department_name': department.name or ''
            }
            
            # Include user info if user_id was provided
            if user_info:
                response_data['user'] = user_info

            return Response(
                json.dumps(response_data),
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
        Get all tree masters with optional filters by name, development stage, and girth
        Query params: 
            - type (optional): Filter by tree type. Values: 'fruit_bearing' or 'non_fruit_bearing'
            - name (optional): Filter by tree name (partial match, case-insensitive)
            - development_stage (optional): Filter by development stage (for rate lookup)
                Values: 'undeveloped', 'semi_developed', 'fully_developed'
            - girth_cm (optional): Girth in cm to lookup rate (requires development_stage)
            - limit (optional, default 100)
            - offset (optional, default 0)
        Returns: JSON list of tree masters with rates (rate populated if development_stage and girth_cm provided)
        """
        try:
            # Get query parameters
            limit = request.httprequest.args.get('limit', type=int) or 100
            offset = request.httprequest.args.get('offset', type=int) or 0
            name_filter = request.httprequest.args.get('name', '').strip()
            tree_type_filter = request.httprequest.args.get('type', '').strip().lower()
            development_stage = request.httprequest.args.get('development_stage', '').strip().lower()
            girth_cm = request.httprequest.args.get('girth_cm', type=float)
            
            # Validate tree_type if provided
            valid_tree_types = ['fruit_bearing', 'non_fruit_bearing']
            if tree_type_filter and tree_type_filter not in valid_tree_types:
                return Response(
                    json.dumps({
                        'error': f'Invalid type: {tree_type_filter}. Must be one of: {", ".join(valid_tree_types)}'
                    }),
                    status=400,
                    content_type='application/json'
                )
            
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
            # Filter by tree_type
            if tree_type_filter:
                domain.append(('tree_type', '=', tree_type_filter))
            
            # Filter by name (partial match, case-insensitive)
            if name_filter:
                domain.append(('name', 'ilike', name_filter))

            # Search tree masters - sort by tree_type first, then by name
            trees = request.env['bhu.tree.master'].sudo().search(domain, limit=limit, offset=offset, order='tree_type, name')

            # Build response
            trees_data = []
            for tree in trees:
                tree_data = {
                    'id': tree.id,
                    'name': tree.name or '',
                    'tree_type': tree.tree_type,
                    'rate': None  # Rate will be determined from tree_rate_ids
                }
                
                # If development_stage and girth are specified, lookup rate from tree_rate_master
                # This works for both fruit-bearing and non-fruit-bearing trees now
                if development_stage and girth_cm:
                    rate_master = request.env['bhu.tree.rate.master']
                    tree_data['rate'] = rate_master.get_rate_for_tree(
                        tree.id,
                        girth_cm,
                        development_stage
                    )
                
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
                        'type': tree_type_filter if tree_type_filter else None,
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
                        'success': False,
                        'error': 'VALIDATION_ERROR',
                        'error_code': 'MISSING_LANDOWNERS',
                        'message': 'At least one landowner is required to create a survey',
                        'fields': ['landowner_ids']
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
                        'success': False,
                        'error': 'VALIDATION_ERROR',
                        'error_code': 'INVALID_LANDOWNER_IDS',
                        'message': f'The following landowner ID(s) do not exist or are invalid: {", ".join(invalid_ids)}',
                        'fields': ['landowner_ids']
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
            
            missing_field_names = []
            missing_field_labels = []
            for field, label in required_fields.items():
                if field not in data or data.get(field) is None or data.get(field) == '':
                    missing_field_names.append(field)
                    missing_field_labels.append(label)
            
            if missing_field_names:
                return Response(
                    json.dumps({
                        'success': False,
                        'error': 'VALIDATION_ERROR',
                        'error_code': 'MISSING_REQUIRED_FIELDS',
                        'message': f'The following required fields are missing: {", ".join(missing_field_labels)}',
                        'fields': missing_field_names
                    }),
                    status=400,
                    content_type='application/json'
                )
            
            # Validate that referenced IDs exist
            validation_errors = []
            invalid_fields = []
            
            # Validate project_id
            if data.get('project_id'):
                project = request.env['bhu.project'].sudo().browse(data['project_id'])
                if not project.exists():
                    validation_errors.append(f'Project ID {data["project_id"]} does not exist')
                    invalid_fields.append('project_id')
            
            # Validate village_id
            if data.get('village_id'):
                village = request.env['bhu.village'].sudo().browse(data['village_id'])
                if not village.exists():
                    validation_errors.append(f'Village ID {data["village_id"]} does not exist')
                    invalid_fields.append('village_id')
            
            # Validate department_id
            if data.get('department_id'):
                department = request.env['bhu.department'].sudo().browse(data['department_id'])
                if not department.exists():
                    validation_errors.append(f'Department ID {data["department_id"]} does not exist')
                    invalid_fields.append('department_id')
            
            # Validate tehsil_id
            if data.get('tehsil_id'):
                tehsil = request.env['bhu.tehsil'].sudo().browse(data['tehsil_id'])
                if not tehsil.exists():
                    validation_errors.append(f'Tehsil ID {data["tehsil_id"]} does not exist')
                    invalid_fields.append('tehsil_id')
            
            if validation_errors:
                return Response(
                    json.dumps({
                        'success': False,
                        'error': 'VALIDATION_ERROR',
                        'error_code': 'INVALID_REFERENCE_IDS',
                        'message': '; '.join(validation_errors),
                        'fields': invalid_fields
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
            
            # Area validation checks with clear error messages
            if total_area is None or total_area <= 0:
                return Response(
                    json.dumps({
                        'success': False,
                        'error': 'VALIDATION_ERROR',
                        'error_code': 'INVALID_TOTAL_AREA',
                        'message': f'Total Area must be greater than 0. Provided value: {total_area}',
                        'fields': ['total_area']
                    }),
                    status=400,
                    content_type='application/json'
                )
            
            if acquired_area is None or acquired_area <= 0:
                return Response(
                    json.dumps({
                        'success': False,
                        'error': 'VALIDATION_ERROR',
                        'error_code': 'INVALID_ACQUIRED_AREA',
                        'message': f'Acquired Area must be greater than 0. Provided value: {acquired_area}',
                        'fields': ['acquired_area']
                    }),
                    status=400,
                    content_type='application/json'
                )
            
            if acquired_area > total_area:
                return Response(
                    json.dumps({
                        'success': False,
                        'error': 'VALIDATION_ERROR',
                        'error_code': 'ACQUIRED_AREA_EXCEEDS_TOTAL',
                        'message': f'Acquired Area ({acquired_area} hectares) cannot be greater than Total Area ({total_area} hectares).',
                        'fields': ['acquired_area', 'total_area']
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
                # API creates surveys in 'submitted' state by default (unless explicitly set)
                'state': data.get('state', 'submitted'),
            }
            
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

            # VALIDATE ALL TREE LINES BEFORE CREATING SURVEY
            # Handle tree lines (new format: supports fruit-bearing and non-fruit-bearing trees)
            tree_line_vals = []
            
            # Support new format: tree_lines array with tree_type
            if 'tree_lines' in data and isinstance(data['tree_lines'], list):
                for tree_line in data['tree_lines']:
                    if isinstance(tree_line, dict):
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
                        
                        # Get tree master to determine tree_type
                        tree_master = request.env['bhu.tree.master'].sudo().browse(tree_master_id)
                        if not tree_master.exists():
                            return Response(
                                json.dumps({
                                    'error': f'Tree master with ID {tree_master_id} not found'
                                }),
                                status=400,
                                content_type='application/json'
                            )
                        
                        # Get tree_type from tree_master or from request
                        tree_type = tree_line.get('tree_type') or tree_master.tree_type
                        if not tree_type:
                            return Response(
                                json.dumps({
                                    'error': 'tree_type must be provided or tree_master must have a tree_type'
                                }),
                                status=400,
                                content_type='application/json'
                            )
                        
                        # Validate tree_type matches tree_master
                        if tree_master.tree_type != tree_type:
                            return Response(
                                json.dumps({
                                    'error': f'Tree type mismatch: tree_master "{tree_master.name}" is {tree_master.tree_type}, but provided tree_type is {tree_type}'
                                }),
                                status=400,
                                content_type='application/json'
                            )
                        
                        # Prepare tree line values
                        tree_line_data = {
                            'tree_master_id': tree_master_id,
                            'tree_type': tree_type,
                            'quantity': tree_line.get('quantity', 1)
                        }
                        
                        # Handle development_stage - required for all tree types
                        development_stage = tree_line.get('development_stage')
                        if not development_stage:
                            return Response(
                                json.dumps({
                                    'error': 'development_stage is required for all trees'
                                }),
                                status=400,
                                content_type='application/json'
                            )
                        
                        # Validate development_stage
                        if development_stage not in ('undeveloped', 'semi_developed', 'fully_developed'):
                            return Response(
                                json.dumps({
                                    'error': f'Invalid development_stage: {development_stage}. Must be one of: undeveloped, semi_developed, fully_developed'
                                }),
                                status=400,
                                content_type='application/json'
                            )
                        tree_line_data['development_stage'] = development_stage
                        
                        # For non-fruit-bearing trees, handle girth_cm
                        if tree_type == 'non_fruit_bearing':
                            # Handle girth_cm for non-fruit-bearing trees
                            girth_cm = tree_line.get('girth_cm')
                            # girth_cm is optional - if provided, it must be > 0
                            # Check if girth_cm is explicitly provided (not None and not empty string)
                            if girth_cm is not None and girth_cm != '':
                                try:
                                    girth_cm_float = float(girth_cm)
                                    if girth_cm_float <= 0:
                                        return Response(
                                            json.dumps({
                                                'error': 'girth_cm must be greater than 0 if provided'
                                            }),
                                            status=400,
                                            content_type='application/json'
                                        )
                                    tree_line_data['girth_cm'] = girth_cm_float
                                except (ValueError, TypeError):
                                    return Response(
                                        json.dumps({
                                            'error': 'girth_cm must be a valid number if provided'
                                        }),
                                        status=400,
                                        content_type='application/json'
                                    )
                            # Don't set girth_cm if not provided - Odoo will use default/False
                        
                        tree_line_vals.append((0, 0, tree_line_data))
            
            # Backward compatibility: support old format with separate arrays
            if 'undeveloped_tree_lines' in data and isinstance(data['undeveloped_tree_lines'], list):
                for tree_line in data['undeveloped_tree_lines']:
                    if isinstance(tree_line, dict) and 'tree_master_id' in tree_line:
                        # Validate tree_master_id exists
                        tree_master = request.env['bhu.tree.master'].sudo().browse(tree_line['tree_master_id'])
                        if not tree_master.exists():
                            return Response(
                                json.dumps({
                                    'error': f'Tree master with ID {tree_line["tree_master_id"]} not found'
                                }),
                                status=400,
                                content_type='application/json'
                            )
                        tree_line_vals.append((0, 0, {
                            'tree_master_id': tree_line['tree_master_id'],
                            'development_stage': 'undeveloped',
                            'quantity': tree_line.get('quantity', 1)
                        }))
            
            if 'semi_developed_tree_lines' in data and isinstance(data['semi_developed_tree_lines'], list):
                for tree_line in data['semi_developed_tree_lines']:
                    if isinstance(tree_line, dict) and 'tree_master_id' in tree_line:
                        # Validate tree_master_id exists
                        tree_master = request.env['bhu.tree.master'].sudo().browse(tree_line['tree_master_id'])
                        if not tree_master.exists():
                            return Response(
                                json.dumps({
                                    'error': f'Tree master with ID {tree_line["tree_master_id"]} not found'
                                }),
                                status=400,
                                content_type='application/json'
                            )
                        tree_line_vals.append((0, 0, {
                            'tree_master_id': tree_line['tree_master_id'],
                            'development_stage': 'semi_developed',
                            'quantity': tree_line.get('quantity', 1)
                        }))
            
            if 'fully_developed_tree_lines' in data and isinstance(data['fully_developed_tree_lines'], list):
                for tree_line in data['fully_developed_tree_lines']:
                    if isinstance(tree_line, dict) and 'tree_master_id' in tree_line:
                        # Validate tree_master_id exists
                        tree_master = request.env['bhu.tree.master'].sudo().browse(tree_line['tree_master_id'])
                        if not tree_master.exists():
                            return Response(
                                json.dumps({
                                    'error': f'Tree master with ID {tree_line["tree_master_id"]} not found'
                                }),
                                status=400,
                                content_type='application/json'
                            )
                        tree_line_vals.append((0, 0, {
                            'tree_master_id': tree_line['tree_master_id'],
                            'development_stage': 'fully_developed',
                            'quantity': tree_line.get('quantity', 1)
                        }))
            
            # VALIDATE PHOTOS BEFORE CREATING SURVEY
            photo_vals = []
            if 'photos' in data and isinstance(data['photos'], list):
                for photo in data['photos']:
                    if isinstance(photo, dict):
                        # s3_url is mandatory
                        if 's3_url' not in photo or not photo['s3_url']:
                            continue
                        
                        # Validate photo_type_id if provided
                        photo_type_id = photo.get('photo_type_id')
                        photo_type = None
                        if photo_type_id:
                            photo_type = request.env['bhu.photo.type'].sudo().browse(photo_type_id)
                            if not photo_type.exists():
                                # Skip this photo if photo_type_id is invalid
                                continue
                        
                        # Build photo values
                        photo_data = {
                            's3_url': photo['s3_url'],
                            'filename': photo.get('filename', ''),
                            'file_size': photo.get('file_size', 0)
                        }
                        
                        # Only add photo_type_id if it was provided and is valid
                        if photo_type_id and photo_type:
                            photo_data['photo_type_id'] = photo_type_id
                        
                        photo_vals.append((0, 0, photo_data))
            
            # ALL VALIDATIONS PASSED - NOW CREATE SURVEY
            # Include all related data in survey_vals for atomic creation
            # This ensures if any validation fails, nothing gets saved
            
            # Add landowners to survey_vals
            if isinstance(landowner_ids, list) and len(landowner_ids) > 0:
                survey_vals['landowner_ids'] = [(6, 0, landowner_ids)]
            
            # Add tree lines to survey_vals
            if tree_line_vals:
                survey_vals['tree_line_ids'] = tree_line_vals
            
            # Add photos to survey_vals
            if photo_vals:
                survey_vals['photo_ids'] = photo_vals
            
            # Create survey with all related data atomically
            survey = request.env['bhu.survey'].sudo().create(survey_vals)

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
            # CRITICAL: Rollback transaction to ensure survey is NOT saved
            try:
                request.env.cr.rollback()
            except Exception as rollback_error:
                _logger.error(f"Error during rollback: {str(rollback_error)}", exc_info=True)
            
            # Extract clear error message from ValidationError
            error_message = str(ve)
            # If ValidationError has a name attribute (translated message), use it
            if hasattr(ve, 'name') and ve.name:
                error_message = ve.name
            # If it's a list of messages, join them
            elif isinstance(ve.args, tuple) and len(ve.args) > 0:
                if isinstance(ve.args[0], (list, tuple)):
                    error_message = '; '.join(str(msg) for msg in ve.args[0])
                else:
                    error_message = str(ve.args[0])
            
            # Try to identify which fields caused the validation error
            fields_list = []
            error_lower = error_message.lower()
            if 'khasra' in error_lower:
                fields_list.append('khasra_number')
            if 'area' in error_lower or 'acquired' in error_lower:
                fields_list.extend(['total_area', 'acquired_area'])
            if 'landowner' in error_lower:
                fields_list.append('landowner_ids')
            
            return Response(
                json.dumps({
                    'success': False,
                    'error': 'VALIDATION_ERROR',
                    'error_code': 'MODEL_VALIDATION_FAILED',
                    'message': error_message,
                    'fields': fields_list if fields_list else []
                }),
                status=400,
                content_type='application/json'
            )
        except Exception as e:
            _logger.error(f"Error in create_survey: {str(e)}", exc_info=True)
            # CRITICAL: Rollback transaction to ensure survey is NOT saved
            try:
                request.env.cr.rollback()
            except Exception as rollback_error:
                _logger.error(f"Error during rollback: {str(rollback_error)}", exc_info=True)
            
            # Try to extract meaningful error message from generic exceptions
            error_message = str(e)
            error_type = type(e).__name__
            
            # Provide more descriptive messages for common errors
            if 'unique constraint' in error_message.lower() or 'duplicate' in error_message.lower():
                if 'khasra' in error_message.lower():
                    error_message = 'Khasra number already exists in this village for another survey.'
                else:
                    error_message = 'A record with these values already exists. Please check for duplicates.'
            elif 'foreign key' in error_message.lower():
                error_message = 'Invalid reference: One or more related records do not exist.'
            elif 'not null' in error_message.lower() or 'required' in error_message.lower():
                error_message = 'Required field is missing. Please check all required fields are provided.'
            
            return Response(
                json.dumps({
                    'success': False,
                    'error': 'SERVER_ERROR',
                    'error_code': error_type.upper().replace(' ', '_'),
                    'message': error_message
                }),
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
                'tree_lines': [{
                    'id': line.id,
                    'tree_type': line.tree_type,
                    'tree_master_id': line.tree_master_id.id,
                    'tree_name': line.tree_master_id.name,
                    'development_stage': line.development_stage,
                    'girth_cm': line.girth_cm if line.tree_type == 'non_fruit_bearing' else None,
                    'quantity': line.quantity
                } for line in survey.tree_line_ids],
                'photos': [{
                    'id': photo.id,
                    'photo_type_id': photo.photo_type_id.id if photo.photo_type_id else None,
                    'photo_type_name': photo.photo_type_id.name if photo.photo_type_id else '',
                    's3_url': photo.s3_url or '',
                    'filename': photo.filename or '',
                    'file_size': photo.file_size or 0,
                    'sequence': photo.sequence or 10
                } for photo in survey.photo_ids],
                'has_house': survey.has_house,
                'house_type': survey.house_type,
                'house_area': survey.house_area,
                'has_shed': survey.has_shed,
                'shed_area': survey.shed_area,
                'has_well': survey.has_well,
                'well_type': survey.well_type,
                'has_tubewell': survey.has_tubewell,
                'has_pond': survey.has_pond,
                'latitude': survey.latitude,
                'longitude': survey.longitude,
                'location_accuracy': survey.location_accuracy,
                'location_timestamp': survey.location_timestamp.strftime('%Y-%m-%d %H:%M:%S') if survey.location_timestamp else None,
                'remarks': survey.remarks or '',
                'state': survey.state,
                'is_notification_4_generated': survey.is_notification_4_generated,
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
            _logger.error(f"Error in get_survey_details for survey_id {survey_id}: {str(e)}", exc_info=True)
            import traceback
            error_trace = traceback.format_exc()
            _logger.error(f"Traceback: {error_trace}")
            return Response(
                json.dumps({
                    'error': str(e),
                    'message': f'Error retrieving survey details: {str(e)}',
                    'survey_id': survey_id
                }),
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
                    'is_notification_4_generated': survey.is_notification_4_generated,
                    'surveyor_id': survey.user_id.id if survey.user_id else None,
                    'surveyor_name': survey.user_id.name if survey.user_id else '',
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

    # Form 10 PDF and Excel export endpoints have been moved to separate controllers:
    # - form10_pdf_api.py for PDF exports
    # - form10_excel_api.py for Excel exports

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

    @http.route('/api/bhuarjan/form10/survey/download', type='http', auth='public', methods=['GET'], csrf=False)
    # @check_permission
    def download_form10_by_survey(self, **kwargs):
        """
        Download Form 10 (Bulk Table Report) PDF for a specific survey
        Query params: survey_id (required)
        Returns: PDF file
        """
        try:
            _logger.info("Form 10 download by survey API called")
            
            # Get query parameters
            survey_id = request.httprequest.args.get('survey_id', type=int)

            if not survey_id:
                _logger.warning("Form 10 download by survey: survey_id is missing")
                return Response(
                    json.dumps({'error': 'survey_id is required'}),
                    status=400,
                    content_type='application/json'
                )

            _logger.info(f"Form 10 download by survey: survey_id={survey_id}")

            # Verify survey exists
            survey = request.env['bhu.survey'].sudo().browse(survey_id)
            if not survey.exists():
                _logger.warning(f"Form 10 download by survey: Survey {survey_id} not found")
                return Response(
                    json.dumps({'error': 'Survey not found'}),
                    status=404,
                    content_type='application/json'
                )

            # Get the Form 10 bulk table report
            _logger.info("Form 10 download by survey: Getting report action")
            try:
                # Use sudo() to bypass access rights when getting the report action
                report_action = request.env['ir.actions.report'].sudo().search([
                    ('report_name', '=', 'bhuarjan.form10_bulk_table_report')
                ], limit=1)
                
                if not report_action:
                    # Fallback: try using ir.model.data
                    _logger.info("Form 10 download by survey: Report not found by name, trying ir.model.data")
                    try:
                        report_data = request.env['ir.model.data'].sudo().search([
                            ('module', '=', 'bhuarjan'),
                            ('name', '=', 'action_report_form10_bulk_table')
                        ], limit=1)
                        if report_data and report_data.res_id:
                            report_action = request.env['ir.actions.report'].sudo().browse(report_data.res_id)
                    except Exception as e:
                        _logger.error(f"Form 10 download by survey: Error in fallback: {str(e)}", exc_info=True)
                
                if not report_action or not report_action.exists():
                    _logger.error("Form 10 download by survey: Report action not found")
                    return Response(
                        json.dumps({'error': 'Form 10 report not found'}),
                        status=404,
                        content_type='application/json'
                    )
                
                _logger.info(f"Form 10 download by survey: Report action found: {report_action.id}, report_name: {report_action.report_name}")
            except Exception as e:
                _logger.error(f"Form 10 download by survey: Error getting report action: {str(e)}", exc_info=True)
                return Response(
                    json.dumps({'error': f'Error accessing report: {str(e)}'}),
                    status=500,
                    content_type='application/json'
                )

            # Use single survey ID for PDF rendering
            res_ids = [survey_id]
            
            _logger.info(f"Form 10 download by survey: Rendering PDF for survey ID: {survey_id}")

            # Generate PDF with error handling
            report_name = report_action.report_name
            _logger.info(f"Form 10 download by survey: Starting PDF generation with report_name: {report_name} for survey {survey_id}")
            
            try:
                # Use with_context to ensure clean environment
                pdf_result = report_action.sudo().with_context(
                    lang='en_US',
                    tz='UTC'
                )._render_qweb_pdf(report_name, res_ids, data={})
                _logger.info(f"Form 10 download by survey: PDF generation completed, result type: {type(pdf_result)}")
            except MemoryError as mem_error:
                _logger.error(f"Form 10 download by survey: Memory error during PDF generation: {str(mem_error)}")
                return Response(
                    json.dumps({'error': 'PDF generation failed due to memory constraints. Please contact administrator.'}),
                    status=500,
                    content_type='application/json'
                )
            except Exception as render_error:
                _logger.error(f"Form 10 download by survey: PDF rendering failed: {str(render_error)}", exc_info=True)
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
            _logger.info("Form 10 download by survey: Extracting PDF bytes from result")
            if isinstance(pdf_result, (tuple, list)) and len(pdf_result) > 0:
                pdf_data = pdf_result[0]
            else:
                pdf_data = pdf_result

            if not isinstance(pdf_data, bytes):
                _logger.error(f"Form 10 download by survey: Invalid PDF data type: {type(pdf_data)}")
                return Response(
                    json.dumps({'error': 'Invalid PDF data'}),
                    status=500,
                    content_type='application/json'
                )

            _logger.info(f"Form 10 download by survey: PDF data extracted, size: {len(pdf_data)} bytes")

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
            
            # Generate filename with survey name or ID
            survey_name_ascii = sanitize_filename(survey.name if survey.name else f"Survey_{survey_id}")
            filename = f"Form10_{survey_name_ascii}.pdf"

            _logger.info(f"Form 10 download by survey: Returning PDF response with filename: {filename}")

            # Return PDF
            response = request.make_response(
                pdf_data,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', f'attachment; filename="{filename}"'),
                    ('Content-Length', str(len(pdf_data)))
                ]
            )
            _logger.info("Form 10 download by survey: PDF response created successfully")
            return response

        except Exception as e:
            _logger.error(f"Error in download_form10_by_survey: {str(e)}", exc_info=True)
            return Response(
                json.dumps({'error': str(e)}),
                status=500,
                content_type='application/json'
            )

    def _generate_form10_excel(self, surveys):
        """Helper function to generate Excel file for Form 10 (without logo and QR code)"""
        if not HAS_XLSXWRITER:
            raise Exception("xlsxwriter library is required for Excel export. Please install it: pip install xlsxwriter")
        
        if not surveys:
            raise Exception("No surveys found.")
        
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Form 10')
        
        # Define formats
        title_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 18
        })
        
        header_info_format = workbook.add_format({
            'bold': True,
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
            'font_size': 12
        })
        
        header_info_value_format = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
            'font_size': 12
        })
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3',
            'align': 'center',
            'valign': 'vcenter',
            'border': 2,
            'text_wrap': True,
            'font_size': 11
        })
        
        cell_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'text_wrap': True,
            'font_size': 11
        })
        
        signature_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 12
        })
        
        first = surveys[0]
        current_row = 0
        
        # Title
        worksheet.merge_range(current_row, 0, current_row, 17, 'भू अर्जन प्रारंभिक सर्वे प्रपत्र', title_format)
        current_row += 1
        current_row += 1  # Spacing
        
        # Header info table (3 rows) - WITHOUT logo and QR code columns
        # Row 1: Project and Department
        worksheet.write(current_row, 0, 'परियोजना का नाम :', header_info_format)
        worksheet.merge_range(current_row, 1, current_row, 8, first.project_id.name or '', header_info_value_format)
        worksheet.write(current_row, 9, 'विभाग का नाम', header_info_format)
        worksheet.merge_range(current_row, 10, current_row, 17, first.department_id.name or '', header_info_value_format)
        current_row += 1
        
        # Row 2: Village and Tehsil
        worksheet.write(current_row, 0, 'ग्राम का नाम', header_info_format)
        worksheet.merge_range(current_row, 1, current_row, 8, first.village_id.name or '', header_info_value_format)
        worksheet.write(current_row, 9, 'तहसील का नाम', header_info_format)
        worksheet.merge_range(current_row, 10, current_row, 16, f"{first.tehsil_id.name or ''} जिला-रायगढ़ (छ.ग.)", header_info_value_format)
        current_row += 1
        
        # Row 3: Survey Date
        survey_date_str = first.survey_date.strftime('%d/%m/%Y') if first.survey_date else ''
        worksheet.write(current_row, 0, 'सर्वे दिनाँक', header_info_format)
        worksheet.merge_range(current_row, 1, current_row, 17, survey_date_str, header_info_value_format)
        current_row += 1
        current_row += 1  # Spacing
        
        # Table headers (2 rows - matching PDF structure)
        # First header row
        worksheet.write(current_row, 0, 'क्र.', header_format)
        worksheet.write(current_row, 1, 'प्रभावित खसरा क्रमांक', header_format)
        worksheet.write(current_row, 2, 'कुल रकबा (हे.में.)', header_format)
        worksheet.write(current_row, 3, 'अर्जन हेतु प्रस्तावित क्षेत्रफल (हेक्टेयर)', header_format)
        worksheet.write(current_row, 4, 'भूमिस्वामी का नाम', header_format)
        worksheet.merge_range(current_row, 5, current_row, 8, 'भूमि का प्रकार', header_format)
        worksheet.merge_range(current_row, 9, current_row, 11, 'भूमि पर स्थित वृक्ष की संख्या (प्रजातिवार)', header_format)
        worksheet.merge_range(current_row, 12, current_row, 17, 'भूमि पर स्थित परिसंपत्तियों का विवरण', header_format)
        current_row += 1
        
        # Second header row
        worksheet.write(current_row, 0, '', header_format)  # Skip first 4 columns (merged above)
        worksheet.write(current_row, 1, '', header_format)
        worksheet.write(current_row, 2, '', header_format)
        worksheet.write(current_row, 3, '', header_format)
        worksheet.write(current_row, 4, '', header_format)
        worksheet.write(current_row, 5, 'एक फसली', header_format)
        worksheet.write(current_row, 6, 'दो फसली', header_format)
        worksheet.write(current_row, 7, 'सिंचित', header_format)
        worksheet.write(current_row, 8, 'असिंचित', header_format)
        worksheet.write(current_row, 9, 'अविकसित', header_format)
        worksheet.write(current_row, 10, 'अर्द्ध विकसित', header_format)
        worksheet.write(current_row, 11, 'पूर्ण विकसित', header_format)
        worksheet.write(current_row, 12, 'मकान (कच्चा/पक्का) क्षेत्रफल वर्गफुट में', header_format)
        worksheet.write(current_row, 13, 'शेड (क्षेत्रफल वर्गफुट में)', header_format)
        worksheet.write(current_row, 14, 'कुँआ (कच्चा/पक्का) (हाँ/नहीं)', header_format)
        worksheet.write(current_row, 15, 'ट्यूबवेल / सम्बमर्शिबल पम्प फिटिंग सहित (हाँ/नहीं)', header_format)
        worksheet.write(current_row, 16, 'तालाब (हाँ/नहीं)', header_format)
        worksheet.write(current_row, 17, 'रिमार्क', header_format)
        current_row += 1
        
        # Data rows
        for idx, survey in enumerate(surveys):
            serial_num = idx + 1
            
            # Get landowner names
            owner_names = []
            counter = 1
            for lo in survey.landowner_ids:
                name = lo.name or ''
                if lo.father_name:
                    name += f" पिता {lo.father_name}"
                elif lo.spouse_name:
                    name += f" पति {lo.spouse_name}"
                owner_names.append(f"{counter}. {name}")
                counter += 1
            owner_str = "\n".join(owner_names) if owner_names else "नहीं"
            
            # Well type
            well_str = "नहीं"
            if survey.has_well == 'yes':
                if survey.well_type == 'kachcha':
                    well_str = "हाँ-कच्चा"
                elif survey.well_type == 'pakka':
                    well_str = "हाँ-पक्का"
            
            # House type
            house_str = "नहीं"
            if survey.house_type and survey.house_area:
                house_type_str = "पक्का" if survey.house_type == 'pakka' else ("कच्चा" if survey.house_type == 'kaccha' else survey.house_type)
                house_str = f"{house_type_str} / {survey.house_area} वर्गफुट"
            
            # Tree details by development stage (matching PDF structure)
            undeveloped_trees = []
            semi_developed_trees = []
            fully_developed_trees = []
            
            if survey.tree_line_ids:
                for tree_line in survey.tree_line_ids:
                    if tree_line.tree_type == 'non_fruit_bearing':
                        tree_name = tree_line.tree_master_id.name if tree_line.tree_master_id else ''
                        quantity = tree_line.quantity or 0
                        if tree_line.development_stage == 'undeveloped' and quantity > 0:
                            undeveloped_trees.append(f"{tree_name} - {quantity}")
                        elif tree_line.development_stage == 'semi_developed' and quantity > 0:
                            semi_developed_trees.append(f"{tree_name} - {quantity}")
                        elif tree_line.development_stage == 'fully_developed' and quantity > 0:
                            fully_developed_trees.append(f"{tree_name} - {quantity}")
            
            undeveloped_str = "\n".join(undeveloped_trees) if undeveloped_trees else "नहीं"
            semi_developed_str = "\n".join(semi_developed_trees) if semi_developed_trees else "नहीं"
            fully_developed_str = "\n".join(fully_developed_trees) if fully_developed_trees else "नहीं"
            
            # Remarks
            remarks_parts = []
            if survey.has_traded_land == 'yes' and survey.traded_land_area:
                remarks_parts.append(f"व्यपवर्तित-{survey.traded_land_area} हेक्टेयर")
            if survey.crop_type_id and (survey.crop_type_id.code == 'FALLOW' or 'पड़ती' in (survey.crop_type_id.name or '')):
                remarks_parts.append("पड़ती भूमि")
            if survey.remarks:
                remarks_parts.append(survey.remarks)
            remarks_str = "\n".join(remarks_parts) if remarks_parts else "नहीं"
            
            data = [
                serial_num,
                survey.khasra_number or "नहीं",
                survey.total_area or 0,
                survey.acquired_area or 0,
                owner_str,
                "हाँ" if survey.is_single_crop else "नहीं",
                "हाँ" if survey.is_double_crop else "नहीं",
                "हाँ" if survey.is_irrigated else "नहीं",
                "हाँ" if survey.is_unirrigated else "नहीं",
                undeveloped_str,
                semi_developed_str,
                fully_developed_str,
                house_str,
                f"{survey.shed_area} वर्गफुट" if survey.shed_area else "नहीं",
                well_str,
                "हाँ" if survey.has_tubewell == 'yes' else "नहीं",
                "हाँ" if survey.has_pond == 'yes' else "नहीं",
                remarks_str
            ]
            
            for col, value in enumerate(data):
                worksheet.write(current_row, col, value, cell_format)
            current_row += 1
        
        # Signature section at the end
        current_row += 1  # Spacing
        signature_start_row = current_row
        
        # Signature headers
        worksheet.write(current_row, 0, '(हस्ताक्षर)', signature_format)
        worksheet.merge_range(current_row, 1, current_row, 4, 'अपेक्षक निकाय के अधिकृत प्रतिनिधि', signature_format)
        worksheet.write(current_row, 5, '(हस्ताक्षर)', signature_format)
        worksheet.merge_range(current_row, 6, current_row, 9, 'तहसीलदार', signature_format)
        worksheet.write(current_row, 10, '(हस्ताक्षर)', signature_format)
        worksheet.merge_range(current_row, 11, current_row, 14, 'नायब तहसीलदार', signature_format)
        worksheet.write(current_row, 15, '(हस्ताक्षर)', signature_format)
        worksheet.merge_range(current_row, 16, current_row, 17, 'राजस्व निरीक्षक', signature_format)
        current_row += 1
        
        # Signature details
        worksheet.merge_range(current_row, 0, current_row, 4, 'नाम -', signature_format)
        worksheet.merge_range(current_row, 5, current_row, 5, 'पदनाम', signature_format)
        worksheet.merge_range(current_row, 6, current_row, 9, 'नाम -', signature_format)
        worksheet.merge_range(current_row, 10, current_row, 14, 'नाम -', signature_format)
        worksheet.merge_range(current_row, 15, current_row, 16, 'नाम-', signature_format)
        worksheet.write(current_row, 17, 'रा.नि.मं.', signature_format)
        current_row += 1
        
        # Set column widths
        worksheet.set_column(0, 0, 5)   # Serial
        worksheet.set_column(1, 1, 20)  # Khasra
        worksheet.set_column(2, 3, 15)  # Areas
        worksheet.set_column(4, 4, 30)  # Landowners
        worksheet.set_column(5, 8, 12)  # Land type columns
        worksheet.set_column(9, 11, 15)  # Tree columns
        worksheet.set_column(12, 17, 15)  # Asset columns
        
        workbook.close()
        output.seek(0)
        return output.read()

    @http.route('/api/bhuarjan/form10/excel/download', type='http', auth='public', methods=['GET'], csrf=False)
    # @check_permission
    def download_form10_excel(self, **kwargs):
        """
        Download Form 10 (Bulk Table Report) Excel based on village_id
        Query params: village_id (required), project_id (optional), limit (optional, max 100)
        Returns: Excel file (without logo and QR code)
        """
        try:
            _logger.info("Form 10 Excel download API called")
            
            if not HAS_XLSXWRITER:
                return Response(
                    json.dumps({'error': 'xlsxwriter library is required for Excel export. Please install it: pip install xlsxwriter'}),
                    status=500,
                    content_type='application/json'
                )
            
            # Get query parameters
            village_id = request.httprequest.args.get('village_id', type=int)
            project_id = request.httprequest.args.get('project_id', type=int)
            limit = min(request.httprequest.args.get('limit', type=int, default=100), 100)  # Default 100, max 100

            if not village_id:
                _logger.warning("Form 10 Excel download: village_id is missing")
                return Response(
                    json.dumps({'error': 'village_id is required'}),
                    status=400,
                    content_type='application/json'
                )

            _logger.info(f"Form 10 Excel download: village_id={village_id}, project_id={project_id}, limit={limit}")

            # Verify village exists
            village = request.env['bhu.village'].sudo().browse(village_id)
            if not village.exists():
                _logger.warning(f"Form 10 Excel download: Village {village_id} not found")
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
                    _logger.warning(f"Form 10 Excel download: Project {project_id} not found")
                    return Response(
                        json.dumps({'error': 'Project not found'}),
                        status=404,
                        content_type='application/json'
                    )
                domain.append(('project_id', '=', project_id))
                project_name = project.name
            else:
                project_name = 'All'

            _logger.info(f"Form 10 Excel download: Searching surveys with domain {domain}")

            # Get all surveys for the village (and project if specified)
            surveys = request.env['bhu.survey'].sudo().with_context(
                active_test=False,
                bhuarjan_current_project_id=False
            ).search(domain, order='id', limit=limit)

            _logger.info(f"Form 10 Excel download: Found {len(surveys)} surveys")

            if not surveys:
                _logger.warning(f"Form 10 Excel download: No surveys found for village_id={village_id}")
                return Response(
                    json.dumps({'error': f'No surveys found for village_id={village_id}' + (f' and project_id={project_id}' if project_id else '')}),
                    status=404,
                    content_type='application/json'
                )

            # Generate Excel file
            _logger.info("Form 10 Excel download: Generating Excel file")
            excel_data = self._generate_form10_excel(surveys)

            # Generate filename - sanitize to ASCII only for HTTP headers
            def sanitize_filename(name):
                """Remove non-ASCII characters and sanitize for HTTP headers"""
                if not name:
                    return 'Unknown'
                try:
                    name = name.encode('ascii', 'ignore').decode('ascii')
                except (UnicodeEncodeError, UnicodeDecodeError):
                    name = ''.join(char for char in name if ord(char) < 128)
                name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
                name = re.sub(r'[_\-\s]+', '_', name)
                name = name.strip('_')
                return name[:50] if name else 'Unknown'
            
            village_name_ascii = sanitize_filename(village.name if village.name else 'Village')
            filename = f"Form10_{village_name_ascii}.xlsx"
            if project_id:
                project_name_ascii = sanitize_filename(project_name if project_name else 'Project')
                filename = f"Form10_{project_name_ascii}_{village_name_ascii}.xlsx"

            _logger.info(f"Form 10 Excel download: Returning Excel response with filename: {filename}")

            # Return Excel file
            response = request.make_response(
                excel_data,
                headers=[
                    ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                    ('Content-Disposition', f'attachment; filename="{filename}"'),
                    ('Content-Length', str(len(excel_data)))
                ]
            )
            _logger.info("Form 10 Excel download: Excel response created successfully")
            return response

        except Exception as e:
            _logger.error(f"Error in download_form10_excel: {str(e)}", exc_info=True)
            return Response(
                json.dumps({'error': str(e)}),
                status=500,
                content_type='application/json'
            )

    @http.route('/api/bhuarjan/form10/excel/survey/download', type='http', auth='public', methods=['GET'], csrf=False)
    # @check_permission
    def download_form10_excel_by_survey(self, **kwargs):
        """
        Download Form 10 (Bulk Table Report) Excel for a specific survey
        Query params: survey_id (required)
        Returns: Excel file (without logo and QR code)
        """
        try:
            _logger.info("Form 10 Excel download by survey API called")
            
            if not HAS_XLSXWRITER:
                return Response(
                    json.dumps({'error': 'xlsxwriter library is required for Excel export. Please install it: pip install xlsxwriter'}),
                    status=500,
                    content_type='application/json'
                )
            
            # Get query parameters
            survey_id = request.httprequest.args.get('survey_id', type=int)

            if not survey_id:
                _logger.warning("Form 10 Excel download by survey: survey_id is missing")
                return Response(
                    json.dumps({'error': 'survey_id is required'}),
                    status=400,
                    content_type='application/json'
                )

            _logger.info(f"Form 10 Excel download by survey: survey_id={survey_id}")

            # Verify survey exists
            survey = request.env['bhu.survey'].sudo().browse(survey_id)
            if not survey.exists():
                _logger.warning(f"Form 10 Excel download by survey: Survey {survey_id} not found")
                return Response(
                    json.dumps({'error': 'Survey not found'}),
                    status=404,
                    content_type='application/json'
                )

            # Generate Excel file for single survey
            _logger.info("Form 10 Excel download by survey: Generating Excel file")
            excel_data = self._generate_form10_excel(survey)

            # Generate filename - sanitize to ASCII only for HTTP headers
            def sanitize_filename(name):
                """Remove non-ASCII characters and sanitize for HTTP headers"""
                if not name:
                    return 'Unknown'
                try:
                    name = name.encode('ascii', 'ignore').decode('ascii')
                except (UnicodeEncodeError, UnicodeDecodeError):
                    name = ''.join(char for char in name if ord(char) < 128)
                name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
                name = re.sub(r'[_\-\s]+', '_', name)
                name = name.strip('_')
                return name[:50] if name else 'Unknown'
            
            # Generate filename with survey name or ID
            survey_name_ascii = sanitize_filename(survey.name if survey.name else f"Survey_{survey_id}")
            filename = f"Form10_{survey_name_ascii}.xlsx"

            _logger.info(f"Form 10 Excel download by survey: Returning Excel response with filename: {filename}")

            # Return Excel file
            response = request.make_response(
                excel_data,
                headers=[
                    ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                    ('Content-Disposition', f'attachment; filename="{filename}"'),
                    ('Content-Length', str(len(excel_data)))
                ]
            )
            _logger.info("Form 10 Excel download by survey: Excel response created successfully")
            return response

        except Exception as e:
            _logger.error(f"Error in download_form10_excel_by_survey: {str(e)}", exc_info=True)
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
            # Convert string IDs to integers if provided as strings
            village_id = data.get('village_id')
            if village_id:
                try:
                    village_id = int(village_id) if isinstance(village_id, str) else village_id
                except (ValueError, TypeError):
                    village_id = None
            
            tehsil_id = data.get('tehsil_id')
            if tehsil_id:
                try:
                    tehsil_id = int(tehsil_id) if isinstance(tehsil_id, str) else tehsil_id
                except (ValueError, TypeError):
                    tehsil_id = None
            
            district_id = data.get('district_id')
            if district_id:
                try:
                    district_id = int(district_id) if isinstance(district_id, str) else district_id
                except (ValueError, TypeError):
                    district_id = None
            
            landowner_vals = {
                'name': data.get('name'),
                'father_name': data.get('father_name'),
                'mother_name': data.get('mother_name'),
                'spouse_name': data.get('spouse_name'),
                'age': data.get('age'),
                'gender': data.get('gender'),
                'phone': data.get('phone'),
                'village_id': village_id,
                'tehsil_id': tehsil_id,
                'district_id': district_id,
                'owner_address': data.get('owner_address'),
                'aadhar_number': data.get('aadhar_number'),
                'pan_number': data.get('pan_number'),
                'bank_name': data.get('bank_name'),
                'bank_branch': data.get('bank_branch'),
                'account_number': data.get('account_number'),
                'ifsc_code': data.get('ifsc_code'),
                'account_holder_name': data.get('account_holder_name'),
            }
            
            # Remove None values for ID fields only (to avoid invalid references)
            # Keep all text fields even if empty string or None (Odoo will handle None as not setting the field)
            landowner_vals = {k: v for k, v in landowner_vals.items() 
                            if v is not None or k not in ['village_id', 'tehsil_id', 'district_id', 'age']}

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
                        'mother_name': landowner.mother_name or '',
                        'spouse_name': landowner.spouse_name or '',
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

    @http.route('/api/bhuarjan/landowner/<int:landowner_id>', type='http', auth='public', methods=['PATCH'], csrf=False)
    @check_permission
    def update_landowner(self, landowner_id, **kwargs):
        """
        Update an existing landowner
        Path param: landowner_id (required)
        Accepts: JSON data with landowner fields to update
        Returns: Updated landowner details
        """
        try:
            # Parse request data
            data = json.loads(request.httprequest.data.decode('utf-8') or '{}')
            
            # Find the landowner
            landowner = request.env['bhu.landowner'].sudo().browse(landowner_id)
            if not landowner.exists():
                return Response(
                    json.dumps({
                        'success': False,
                        'error': 'NOT_FOUND',
                        'error_code': 'LANDOWNER_NOT_FOUND',
                        'message': f'Landowner with ID {landowner_id} not found',
                        'fields': ['landowner_id']
                    }),
                    status=404,
                    content_type='application/json'
                )
            
            # Prepare landowner values for update
            # Convert string IDs to integers if provided as strings
            village_id = data.get('village_id')
            if village_id is not None:
                try:
                    village_id = int(village_id) if isinstance(village_id, str) else village_id
                except (ValueError, TypeError):
                    village_id = None
            
            tehsil_id = data.get('tehsil_id')
            if tehsil_id is not None:
                try:
                    tehsil_id = int(tehsil_id) if isinstance(tehsil_id, str) else tehsil_id
                except (ValueError, TypeError):
                    tehsil_id = None
            
            district_id = data.get('district_id')
            if district_id is not None:
                try:
                    district_id = int(district_id) if isinstance(district_id, str) else district_id
                except (ValueError, TypeError):
                    district_id = None
            
            # Build update values - only include fields that are provided in the request
            landowner_vals = {}
            
            # Text fields - include if provided (even if empty string)
            if 'name' in data:
                landowner_vals['name'] = data.get('name')
            if 'father_name' in data:
                landowner_vals['father_name'] = data.get('father_name')
            if 'mother_name' in data:
                landowner_vals['mother_name'] = data.get('mother_name')
            if 'spouse_name' in data:
                landowner_vals['spouse_name'] = data.get('spouse_name')
            if 'phone' in data:
                landowner_vals['phone'] = data.get('phone')
            if 'owner_address' in data:
                landowner_vals['owner_address'] = data.get('owner_address')
            if 'aadhar_number' in data:
                landowner_vals['aadhar_number'] = data.get('aadhar_number')
            if 'pan_number' in data:
                landowner_vals['pan_number'] = data.get('pan_number')
            if 'bank_name' in data:
                landowner_vals['bank_name'] = data.get('bank_name')
            if 'bank_branch' in data:
                landowner_vals['bank_branch'] = data.get('bank_branch')
            if 'account_number' in data:
                landowner_vals['account_number'] = data.get('account_number')
            if 'ifsc_code' in data:
                landowner_vals['ifsc_code'] = data.get('ifsc_code')
            if 'account_holder_name' in data:
                landowner_vals['account_holder_name'] = data.get('account_holder_name')
            
            # Integer and selection fields
            if 'age' in data:
                landowner_vals['age'] = data.get('age')
            if 'gender' in data:
                landowner_vals['gender'] = data.get('gender')
            
            # ID fields - only include if provided and valid
            if village_id is not None:
                # Validate village exists
                village = request.env['bhu.village'].sudo().browse(village_id)
                if village.exists():
                    landowner_vals['village_id'] = village_id
                else:
                    return Response(
                        json.dumps({
                            'success': False,
                            'error': 'VALIDATION_ERROR',
                            'error_code': 'INVALID_VILLAGE_ID',
                            'message': f'Village with ID {village_id} not found',
                            'fields': ['village_id']
                        }),
                        status=400,
                        content_type='application/json'
                    )
            
            if tehsil_id is not None:
                # Validate tehsil exists
                tehsil = request.env['bhu.tehsil'].sudo().browse(tehsil_id)
                if tehsil.exists():
                    landowner_vals['tehsil_id'] = tehsil_id
                else:
                    return Response(
                        json.dumps({
                            'success': False,
                            'error': 'VALIDATION_ERROR',
                            'error_code': 'INVALID_TEHSIL_ID',
                            'message': f'Tehsil with ID {tehsil_id} not found',
                            'fields': ['tehsil_id']
                        }),
                        status=400,
                        content_type='application/json'
                    )
            
            if district_id is not None:
                # Validate district exists
                district = request.env['bhu.district'].sudo().browse(district_id)
                if district.exists():
                    landowner_vals['district_id'] = district_id
                else:
                    return Response(
                        json.dumps({
                            'success': False,
                            'error': 'VALIDATION_ERROR',
                            'error_code': 'INVALID_DISTRICT_ID',
                            'message': f'District with ID {district_id} not found',
                            'fields': ['district_id']
                        }),
                        status=400,
                        content_type='application/json'
                    )
            
            # Handle document uploads if provided (base64 encoded)
            if 'aadhar_card' in data and data.get('aadhar_card'):
                try:
                    aadhar_data = data['aadhar_card']
                    if isinstance(aadhar_data, str):
                        if ',' in aadhar_data:
                            aadhar_data = aadhar_data.split(',')[1]
                        landowner_vals['aadhar_card'] = base64.b64decode(aadhar_data)
                except Exception as e:
                    _logger.warning(f"Error processing Aadhar card: {str(e)}")
            
            if 'pan_card' in data and data.get('pan_card'):
                try:
                    pan_data = data['pan_card']
                    if isinstance(pan_data, str):
                        if ',' in pan_data:
                            pan_data = pan_data.split(',')[1]
                        landowner_vals['pan_card'] = base64.b64decode(pan_data)
                except Exception as e:
                    _logger.warning(f"Error processing PAN card: {str(e)}")
            
            # Check if there's anything to update
            if not landowner_vals:
                return Response(
                    json.dumps({
                        'success': False,
                        'error': 'VALIDATION_ERROR',
                        'error_code': 'NO_FIELDS_TO_UPDATE',
                        'message': 'No valid fields provided for update',
                        'fields': []
                    }),
                    status=400,
                    content_type='application/json'
                )
            
            # Update landowner
            try:
                landowner.write(landowner_vals)
            except ValidationError as ve:
                # Extract field names from validation error if possible
                error_msg = str(ve)
                fields_list = []
                
                # Try to identify which field caused the error
                if 'aadhar' in error_msg.lower():
                    fields_list.append('aadhar_number')
                elif 'pan' in error_msg.lower():
                    fields_list.append('pan_number')
                elif 'account' in error_msg.lower():
                    fields_list.append('account_number')
                elif 'ifsc' in error_msg.lower():
                    fields_list.append('ifsc_code')
                elif 'age' in error_msg.lower():
                    fields_list.append('age')
                
                return Response(
                    json.dumps({
                        'success': False,
                        'error': 'VALIDATION_ERROR',
                        'error_code': 'MODEL_VALIDATION_FAILED',
                        'message': error_msg,
                        'fields': fields_list if fields_list else []
                    }),
                    status=400,
                    content_type='application/json'
                )
            except Exception as e:
                _logger.error(f"Error updating landowner: {str(e)}", exc_info=True)
                return Response(
                    json.dumps({
                        'success': False,
                        'error': 'UPDATE_FAILED',
                        'error_code': 'UPDATE_ERROR',
                        'message': f'Failed to update landowner: {str(e)}',
                        'fields': []
                    }),
                    status=500,
                    content_type='application/json'
                )
            
            # Return updated landowner details
            return Response(
                json.dumps({
                    'success': True,
                    'data': {
                        'id': landowner.id,
                        'name': landowner.name,
                        'father_name': landowner.father_name or '',
                        'mother_name': landowner.mother_name or '',
                        'spouse_name': landowner.spouse_name or '',
                        'gender': landowner.gender or '',
                        'age': landowner.age or 0,
                        'aadhar_number': landowner.aadhar_number or '',
                        'pan_number': landowner.pan_number or '',
                        'phone': landowner.phone or '',
                        'village_id': landowner.village_id.id if landowner.village_id else None,
                        'village_name': landowner.village_id.name if landowner.village_id else '',
                        'tehsil_id': landowner.tehsil_id.id if landowner.tehsil_id else None,
                        'tehsil_name': landowner.tehsil_id.name if landowner.tehsil_id else '',
                        'district_id': landowner.district_id.id if landowner.district_id else None,
                        'district_name': landowner.district_id.name if landowner.district_id else '',
                        'owner_address': landowner.owner_address or '',
                        'bank_name': landowner.bank_name or '',
                        'bank_branch': landowner.bank_branch or '',
                        'account_number': landowner.account_number or '',
                        'ifsc_code': landowner.ifsc_code or '',
                        'account_holder_name': landowner.account_holder_name or '',
                    }
                }),
                status=200,
                content_type='application/json'
            )
            
        except json.JSONDecodeError:
            return Response(
                json.dumps({
                    'success': False,
                    'error': 'INVALID_JSON',
                    'error_code': 'INVALID_JSON',
                    'message': 'Invalid JSON in request body',
                    'fields': []
                }),
                status=400,
                content_type='application/json'
            )
        except Exception as e:
            _logger.error(f"Error in update_landowner: {str(e)}", exc_info=True)
            return Response(
                json.dumps({
                    'success': False,
                    'error': 'SERVER_ERROR',
                    'error_code': 'INTERNAL_ERROR',
                    'message': f'Internal server error: {str(e)}',
                    'fields': []
                }),
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

            # Parse request data
            data = json.loads(request.httprequest.data.decode('utf-8') or '{}')
            
            # Check if survey can be edited (only draft and submitted states allow editing)
            # Exception: allow state updates regardless of current state
            is_state_update = 'state' in data
            has_other_fields = any(key != 'state' for key in data.keys())
            
            if has_other_fields and survey.state not in ('draft', 'submitted'):
                return Response(
                    json.dumps({
                        'error': f'Survey cannot be edited. Current state: {survey.state}. Only surveys in draft or submitted state can be edited. State updates are allowed regardless of current state.'
                    }),
                    status=400,
                    content_type='application/json'
                )

            # Handle state updates - validate and set submitted_date if needed
            if 'state' in data:
                new_state = data.get('state')
                valid_states = ['draft', 'submitted', 'approved', 'rejected']
                if new_state not in valid_states:
                    return Response(
                        json.dumps({
                            'error': 'Validation Error',
                            'message': f'Invalid state value. Valid states are: {", ".join(valid_states)}'
                        }),
                        status=400,
                        content_type='application/json'
                    )
                
                # Special handling for state = 'submitted'
                if new_state == 'submitted':
                    # Validate khasra_number is present (required for submission)
                    if not survey.khasra_number:
                        return Response(
                            json.dumps({
                                'error': 'Validation Error',
                                'message': 'Khasra number is required before submitting the survey.'
                            }),
                            status=400,
                            content_type='application/json'
                        )
                    # Set submitted_date if not already set
                    if not survey.submitted_date:
                        from datetime import datetime, timezone
                        data['submitted_date'] = datetime.now(timezone.utc).replace(tzinfo=None)

            # List of fields that can be updated via API
            allowed_fields = [
                'project_id', 'department_id', 'village_id', 'tehsil_id', 'survey_date',
                'khasra_number', 'total_area', 'acquired_area', 'has_traded_land', 'traded_land_area',
                'crop_type_id', 'irrigation_type',
                'has_house', 'house_type', 'house_area', 'has_shed', 'shed_area',
                'has_well', 'well_type', 'has_tubewell', 'has_pond',
                'landowner_ids', 'survey_image', 'survey_image_filename',
                'remarks', 'state', 'submitted_date'
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
                    # Handle text fields (remarks) - allow None and empty strings
                    elif field in ['remarks']:
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
            
            # Handle tree lines (if provided - new format: supports fruit-bearing and non-fruit-bearing trees)
            if 'tree_lines' in data and isinstance(data['tree_lines'], list):
                tree_line_vals = []
                for tree_line in data['tree_lines']:
                    if isinstance(tree_line, dict):
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
                        
                        # Get tree master to determine tree_type
                        tree_master = request.env['bhu.tree.master'].sudo().browse(tree_master_id)
                        if not tree_master.exists():
                            return Response(
                                json.dumps({
                                    'error': f'Tree master with ID {tree_master_id} not found'
                                }),
                                status=400,
                                content_type='application/json'
                            )
                        
                        # Get tree_type from tree_master or from request
                        tree_type = tree_line.get('tree_type') or tree_master.tree_type
                        if not tree_type:
                            return Response(
                                json.dumps({
                                    'error': 'tree_type must be provided or tree_master must have a tree_type'
                                }),
                                status=400,
                                content_type='application/json'
                            )
                        
                        # Validate tree_type matches tree_master
                        if tree_master.tree_type != tree_type:
                            return Response(
                                json.dumps({
                                    'error': f'Tree type mismatch: tree_master "{tree_master.name}" is {tree_master.tree_type}, but provided tree_type is {tree_type}'
                                }),
                                status=400,
                                content_type='application/json'
                            )
                        
                        # Prepare tree line values
                        tree_line_data = {
                            'tree_master_id': tree_master_id,
                            'tree_type': tree_type,
                            'quantity': tree_line.get('quantity', 1)
                        }
                        
                        # Handle development_stage - required for all tree types
                        development_stage = tree_line.get('development_stage')
                        if not development_stage:
                            return Response(
                                json.dumps({
                                    'error': 'development_stage is required for all trees'
                                }),
                                status=400,
                                content_type='application/json'
                            )
                        
                        # Validate development_stage
                        if development_stage not in ('undeveloped', 'semi_developed', 'fully_developed'):
                            return Response(
                                json.dumps({
                                    'error': f'Invalid development_stage: {development_stage}. Must be one of: undeveloped, semi_developed, fully_developed'
                                }),
                                status=400,
                                content_type='application/json'
                            )
                        tree_line_data['development_stage'] = development_stage
                        
                        # For non-fruit-bearing trees, handle girth_cm
                        if tree_type == 'non_fruit_bearing':
                            # Handle girth_cm for non-fruit-bearing trees
                            girth_cm = tree_line.get('girth_cm')
                            # girth_cm is optional - if provided, it must be > 0
                            # Check if girth_cm is explicitly provided (not None and not empty string)
                            if girth_cm is not None and girth_cm != '':
                                try:
                                    girth_cm_float = float(girth_cm)
                                    if girth_cm_float <= 0:
                                        return Response(
                                            json.dumps({
                                                'error': 'girth_cm must be greater than 0 if provided'
                                            }),
                                            status=400,
                                            content_type='application/json'
                                        )
                                    tree_line_data['girth_cm'] = girth_cm_float
                                except (ValueError, TypeError):
                                    return Response(
                                        json.dumps({
                                            'error': 'girth_cm must be a valid number if provided'
                                        }),
                                        status=400,
                                        content_type='application/json'
                                    )
                            # Don't set girth_cm if not provided - Odoo will use default/False
                        
                        tree_line_vals.append((0, 0, tree_line_data))
                
                # Replace all tree lines with new ones
                if tree_line_vals:
                    survey.write({'tree_line_ids': [(5, 0, 0)] + tree_line_vals})
            
            # Handle photos (if provided - adds new photos, doesn't replace existing)
            if 'photos' in data and isinstance(data['photos'], list):
                photo_vals = []
                for photo in data['photos']:
                    if not isinstance(photo, dict) or 's3_url' not in photo or not photo['s3_url']:
                        continue
                    
                    # Validate photo_type_id if provided
                    photo_type_id = photo.get('photo_type_id')
                    photo_type = None
                    if photo_type_id:
                        photo_type = request.env['bhu.photo.type'].sudo().browse(photo_type_id)
                        if not photo_type.exists():
                            # Skip this photo if photo_type_id is invalid
                            continue
                    
                    # Build photo values
                    photo_data = {
                        's3_url': photo['s3_url'],
                        'filename': photo.get('filename', ''),
                        'file_size': photo.get('file_size', 0)
                    }
                    
                    # Only add photo_type_id if it was provided and is valid
                    if photo_type_id and photo_type:
                        photo_data['photo_type_id'] = photo_type_id
                    
                    photo_vals.append((0, 0, photo_data))
                
                if photo_vals:
                    survey.write({'photo_ids': photo_vals})

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
                'tree_lines': [{
                    'id': line.id,
                    'tree_type': line.tree_type,
                    'tree_master_id': line.tree_master_id.id,
                    'tree_name': line.tree_master_id.name,
                    'development_stage': line.development_stage,
                    'girth_cm': line.girth_cm if line.tree_type == 'non_fruit_bearing' else None,
                    'quantity': line.quantity
                } for line in survey.tree_line_ids],
                'photos': [{
                    'id': photo.id,
                    'photo_type_id': photo.photo_type_id.id if photo.photo_type_id else None,
                    'photo_type_name': photo.photo_type_id.name if photo.photo_type_id else '',
                    's3_url': photo.s3_url or '',
                    'filename': photo.filename or '',
                    'file_size': photo.file_size or 0,
                    'sequence': photo.sequence or 10
                } for photo in survey.photo_ids],
                'has_house': survey.has_house or '',
                'house_type': survey.house_type or '',
                'house_area': survey.house_area or 0.0,
                'has_shed': survey.has_shed or '',
                'shed_area': survey.shed_area or 0.0,
                'has_well': survey.has_well or '',
                'well_type': survey.well_type or '',
                'has_tubewell': survey.has_tubewell or '',
                'has_pond': survey.has_pond or '',
                'landowner_ids': survey.landowner_ids.ids if survey.landowner_ids else [],
                'state': survey.state or 'submitted',
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
                json.dumps({
                    'success': False,
                    'error': 'VALIDATION_ERROR',
                    'error_code': 'INVALID_JSON',
                    'message': 'Invalid JSON in request body. Please check your request format.'
                }),
                status=400,
                content_type='application/json'
            )
        except ValidationError as ve:
            _logger.error(f"Validation error in update_survey: {str(ve)}", exc_info=True)
            # Extract clear error message from ValidationError
            error_message = str(ve)
            if hasattr(ve, 'name') and ve.name:


                error_message = ve.name
            elif isinstance(ve.args, tuple) and len(ve.args) > 0:
                if isinstance(ve.args[0], (list, tuple)):
                    error_message = '; '.join(str(msg) for msg in ve.args[0])
                else:
                    error_message = str(ve.args[0])
            
            return Response(
                json.dumps({
                    'success': False,
                    'error': 'VALIDATION_ERROR',
                    'error_code': 'MODEL_VALIDATION_FAILED',
                    'message': error_message
                }),
                status=400,
                content_type='application/json'
            )
        except Exception as e:
            _logger.error(f"Error in update_survey: {str(e)}", exc_info=True)
            error_message = str(e)
            error_type = type(e).__name__
            
            # Provide more descriptive messages for common errors
            if 'unique constraint' in error_message.lower() or 'duplicate' in error_message.lower():
                if 'khasra' in error_message.lower():
                    error_message = 'Khasra number already exists in this village for another survey.'
                else:
                    error_message = 'A record with these values already exists. Please check for duplicates.'
            elif 'foreign key' in error_message.lower():
                error_message = 'Invalid reference: One or more related records do not exist.'
            elif 'not null' in error_message.lower() or 'required' in error_message.lower():
                error_message = 'Required field is missing. Please check all required fields are provided.'
            
            return Response(
                json.dumps({
                    'success': False,
                    'error': 'SERVER_ERROR',
                    'error_code': error_type.upper().replace(' ', '_'),
                    'message': error_message
                }),
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

    @http.route('/api/bhuarjan/photo-types', type='http', auth='public', methods=['GET'], csrf=False)
    @check_permission
    def get_all_photo_types(self, **kwargs):
        """
        Get all photo types
        Query params: limit, offset, active (optional filter - default True)
        Returns: JSON list of photo types
        """
        try:
            # Get query parameters
            limit = request.httprequest.args.get('limit', type=int) or 100
            offset = request.httprequest.args.get('offset', type=int) or 0
            active_filter = request.httprequest.args.get('active')
            
            # Build domain
            domain = []
            if active_filter is not None:
                active_bool = active_filter.lower() in ('true', '1', 'yes')
                domain.append(('active', '=', active_bool))
            else:
                # Default to active only
                domain.append(('active', '=', True))

            # Search photo types
            photo_types = request.env['bhu.photo.type'].sudo().search(domain, limit=limit, offset=offset, order='sequence, name')

            # Build response
            photo_types_data = []
            for photo_type in photo_types:
                photo_types_data.append({
                    'id': photo_type.id,
                    'name': photo_type.name or '',
                    'code': photo_type.code or '',
                    'description': photo_type.description or '',
                    'sequence': photo_type.sequence or 10,
                    'active': photo_type.active
                })

            # Get total count
            total_count = request.env['bhu.photo.type'].sudo().search_count(domain)

            return Response(
                json.dumps({
                    'success': True,
                    'data': photo_types_data,
                    'total': total_count,
                    'count': len(photo_types_data),
                    'limit': limit,
                    'offset': offset
                }),
                status=200,
                content_type='application/json'
            )

        except Exception as e:
            _logger.error(f"Error in get_all_photo_types: {str(e)}", exc_info=True)
            return Response(
                json.dumps({'error': str(e)}),
                status=500,
                content_type='application/json'
            )

    @http.route('/api/bhuarjan/survey/photos', type='http', auth='public', methods=['POST'], csrf=False)
    @check_permission
    def add_survey_photos(self, **kwargs):
        """
        Add photos to a survey
        Query param: survey_id (required)
        Body: JSON with photos array
        Each photo must have: s3_url (required)
        Optional fields: photo_type_id, filename, file_size
        Returns: Success message with added photos
        """
        try:
            # Get survey_id from query parameters
            survey_id = request.httprequest.args.get('survey_id')
            if not survey_id:
                return Response(
                    json.dumps({
                        'success': False,
                        'error': 'Missing survey_id',
                        'message': 'survey_id query parameter is required'
                    }),
                    status=400,
                    content_type='application/json'
                )
            
            # Log the received survey_id for debugging
            _logger.info(f"add_survey_photos: Received survey_id={survey_id}, type={type(survey_id)}")
            
            # Ensure survey_id is an integer
            try:
                survey_id = int(survey_id)
            except (ValueError, TypeError):
                return Response(
                    json.dumps({
                        'success': False,
                        'error': 'Invalid survey_id',
                        'message': f'survey_id must be an integer, got: {survey_id}'
                    }),
                    status=400,
                    content_type='application/json'
                )
            
            # Parse request data
            data = json.loads(request.httprequest.data.decode('utf-8') or '{}')
            
            # Validate survey exists
            survey = request.env['bhu.survey'].sudo().browse(survey_id)
            if not survey.exists():
                _logger.warning(f"add_survey_photos: Survey {survey_id} not found")
                return Response(
                    json.dumps({
                        'success': False,
                        'error': 'Survey not found',
                        'message': f'Survey with ID {survey_id} does not exist'
                    }),
                    status=404,
                    content_type='application/json'
                )
            
            _logger.info(f"add_survey_photos: Survey {survey_id} found, name: {survey.name}")
            
            # Validate photos array
            if 'photos' not in data or not isinstance(data['photos'], list):
                return Response(
                    json.dumps({
                        'success': False,
                        'error': 'Invalid request',
                        'message': 'photos array is required in request body'
                    }),
                    status=400,
                    content_type='application/json'
                )
            
            if len(data['photos']) == 0:
                return Response(
                    json.dumps({
                        'success': False,
                        'error': 'Invalid request',
                        'message': 'At least one photo is required'
                    }),
                    status=400,
                    content_type='application/json'
                )
            
            # Build photo values
            photo_vals = []
            added_photos = []
            for photo in data['photos']:
                if not isinstance(photo, dict):
                    continue
                
                # s3_url is mandatory
                if 's3_url' not in photo or not photo['s3_url']:
                    continue
                
                # Validate photo_type_id if provided
                photo_type_id = photo.get('photo_type_id')
                photo_type = None
                if photo_type_id:
                    photo_type = request.env['bhu.photo.type'].sudo().browse(photo_type_id)
                    if not photo_type.exists():
                        # If photo_type_id is provided but invalid, skip this photo
                        continue
                
                # Build photo values - only include photo_type_id if it's valid
                photo_data = {
                    'survey_id': survey_id,  # Required field
                    's3_url': photo['s3_url'],
                    'filename': photo.get('filename', ''),
                    'file_size': photo.get('file_size', 0)
                }
                
                # Only add photo_type_id if it was provided and is valid
                if photo_type_id and photo_type:
                    photo_data['photo_type_id'] = photo_type_id
                
                photo_vals.append((0, 0, photo_data))
                
                added_photos.append({
                    'photo_type_id': photo_type_id if photo_type else None,
                    'photo_type_name': photo_type.name if photo_type else None,
                    's3_url': photo['s3_url'],
                    'filename': photo.get('filename', '')
                })
            
            if not photo_vals:
                return Response(
                    json.dumps({
                        'success': False,
                        'error': 'Invalid photos',
                        'message': 'No valid photos provided. Each photo must have s3_url'
                    }),
                    status=400,
                    content_type='application/json'
                )
            
            # Add photos to survey
            try:
                survey.write({'photo_ids': photo_vals})
            except Exception as write_error:
                _logger.error(f"Error writing photos to survey {survey_id}: {str(write_error)}", exc_info=True)
                # Check if it's a unique constraint violation
                if 'unique' in str(write_error).lower() or 'duplicate' in str(write_error).lower():
                    return Response(
                        json.dumps({
                            'success': False,
                            'error': 'Duplicate S3 URL',
                            'message': 'One or more S3 URLs already exist. Each photo must have a unique S3 URL.'
                        }),
                        status=400,
                        content_type='application/json'
                    )
                raise
            
            return Response(
                json.dumps({
                    'success': True,
                    'message': f'Successfully added {len(photo_vals)} photo(s) to survey',
                    'data': {
                        'survey_id': survey_id,
                        'added_photos': added_photos,
                        'total_photos': len(survey.photo_ids)
                    }
                }),
                status=200,
                content_type='application/json'
            )

        except json.JSONDecodeError:
            return Response(
                json.dumps({
                    'success': False,
                    'error': 'VALIDATION_ERROR',
                    'error_code': 'INVALID_JSON',
                    'message': 'Request body must be valid JSON. Please check your request format.'
                }),
                status=400,
                content_type='application/json'
            )
        except Exception as e:
            _logger.error(f"Error in add_survey_photos: {str(e)}", exc_info=True)
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
        Returns: JSON with survey counts by state (total, submitted, approved, rejected) and statistics
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
            
            # Total Surveys Done = Approved + Rejected
            total_surveys_done = approved_count + rejected_count
            # Pending = Submitted + Rejected (as per user requirement)
            pending_count = submitted_count + rejected_count

            # Build response
            dashboard_data = {
                'village_id': village_id,
                'village_name': village.name or '',
                'village_code': village.village_code or '',
                'statistics': {
                    'total_surveys': total_surveys,
                    'total_surveys_done': total_surveys_done,
                    'draft': draft_count,
                    'submitted': submitted_count,
                    'approved': approved_count,
                    'rejected': rejected_count,
                    'pending': pending_count
                },
                'breakdown': {
                    'draft_percentage': round((draft_count / total_surveys * 100) if total_surveys > 0 else 0, 2),
                    'submitted_percentage': round((submitted_count / total_surveys * 100) if total_surveys > 0 else 0, 2),
                    'approved_percentage': round((approved_count / total_surveys * 100) if total_surveys > 0 else 0, 2),
                    'rejected_percentage': round((rejected_count / total_surveys * 100) if total_surveys > 0 else 0, 2),
                    'pending_percentage': round((pending_count / total_surveys * 100) if total_surveys > 0 else 0, 2)
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

