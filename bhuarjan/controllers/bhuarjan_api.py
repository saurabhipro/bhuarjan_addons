# -*- coding: utf-8 -*-
"""
Bhuarjan REST API Controller
Provides REST APIs for mobile app integration
Public APIs - No authentication required
"""
from odoo import http
from odoo.http import request, Response
import json
import logging
import base64
from .main import *

_logger = logging.getLogger(__name__)


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
            
            # Get default user (admin) or use provided user_id
            user_id = data.get('user_id')
            if not user_id:
                # Use admin user as default
                admin_user = request.env['res.users'].sudo().search([('login', '=', 'admin')], limit=1)
                user_id = admin_user.id if admin_user else 2  # Fallback to user ID 2 (usually admin)
            
            # Prepare survey values
            survey_vals = {
                'user_id': user_id,
                'project_id': data.get('project_id'),
                'village_id': data.get('village_id'),
                'department_id': data.get('department_id'),
                'tehsil_id': data.get('tehsil_id'),
                'khasra_number': data.get('khasra_number'),
                'total_area': data.get('total_area', 0.0),
                'acquired_area': data.get('acquired_area', 0.0),
                'survey_date': data.get('survey_date'),
                'crop_type': data.get('crop_type', 'single'),
                'irrigation_type': data.get('irrigation_type', 'irrigated'),
                'tree_development_stage': data.get('tree_development_stage'),
                'tree_count': data.get('tree_count', 0),
                'has_house': data.get('has_house', 'no'),
                'house_type': data.get('house_type'),
                'house_area': data.get('house_area', 0.0),
                'shed_area': data.get('shed_area', 0.0),
                'has_well': data.get('has_well', 'no'),
                'well_type': data.get('well_type', 'kachcha'),
                'has_tubewell': data.get('has_tubewell', 'no'),
                'has_pond': data.get('has_pond', 'no'),
                'trees_description': data.get('trees_description'),
                'latitude': data.get('latitude'),
                'longitude': data.get('longitude'),
                'location_accuracy': data.get('location_accuracy'),
                'location_timestamp': data.get('location_timestamp'),
                'remarks': data.get('remarks'),
                'state': data.get('state', 'draft'),
            }

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

            # Link landowners if provided
            if data.get('landowner_ids'):
                landowner_ids = data.get('landowner_ids', [])
                if isinstance(landowner_ids, list):
                    survey.sudo().write({'landowner_ids': [(6, 0, landowner_ids)]})

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
                'survey_date': survey.survey_date.strftime('%Y-%m-%d') if survey.survey_date else None,
                'crop_type': survey.crop_type,
                'irrigation_type': survey.irrigation_type,
                'tree_development_stage': survey.tree_development_stage,
                'tree_count': survey.tree_count,
                'has_house': survey.has_house,
                'house_type': survey.house_type,
                'house_area': survey.house_area,
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
    @check_permission
    def download_form10(self, **kwargs):
        """
        Download Form 10 (Section 4 Notification) PDF
        Query params: project_id, village_id (or notification_id)
        Returns: PDF file
        """
        try:
            # Get query parameters
            project_id = request.httprequest.args.get('project_id', type=int)
            village_id = request.httprequest.args.get('village_id', type=int)
            notification_id = request.httprequest.args.get('notification_id', type=int)

            if notification_id:
                # Get notification by ID
                notification = request.env['bhu.section4.notification'].sudo().browse(notification_id)
                if not notification.exists():
                    return Response(
                        json.dumps({'error': 'Notification not found'}),
                        status=404,
                        content_type='application/json'
                    )
                project_id = notification.project_id.id
                village_id = notification.village_id.id
            elif not project_id or not village_id:
                return Response(
                    json.dumps({'error': 'project_id and village_id (or notification_id) are required'}),
                    status=400,
                    content_type='application/json'
                )

            # Get or create Section 4 notification
            notification = request.env['bhu.section4.notification'].sudo().search([
                ('project_id', '=', project_id),
                ('village_id', '=', village_id)
            ], limit=1, order='create_date desc')

            if not notification:
                return Response(
                    json.dumps({'error': 'Section 4 Notification not found for this project and village'}),
                    status=404,
                    content_type='application/json'
                )

            # Create wizard for PDF generation
            wizard = request.env['bhu.section4.notification.wizard'].sudo().create({
                'project_id': project_id,
                'village_id': village_id,
                'public_purpose': notification.public_purpose or '',
                'public_hearing_date': notification.public_hearing_date,
                'public_hearing_time': notification.public_hearing_time or '',
                'public_hearing_place': notification.public_hearing_place or '',
                'q1_brief_description': notification.q1_brief_description or '',
                'q2_directly_affected': notification.q2_directly_affected or '',
                'q3_indirectly_affected': notification.q3_indirectly_affected or '',
                'q4_private_assets': notification.q4_private_assets or '',
                'q5_government_assets': notification.q5_government_assets or '',
                'q6_minimal_acquisition': notification.q6_minimal_acquisition or '',
                'q7_alternatives_considered': notification.q7_alternatives_considered or '',
                'q8_total_cost': notification.q8_total_cost or '',
                'q9_project_benefits': notification.q9_project_benefits or '',
                'q10_compensation_measures': notification.q10_compensation_measures or '',
                'q11_other_components': notification.q11_other_components or '',
            })

            # Generate PDF
            report_action = request.env.ref('bhuarjan.action_report_section4_notification')
            pdf_result = report_action.sudo()._render_qweb_pdf(report_action.report_name, [wizard.id], data={})

            if not pdf_result:
                return Response(
                    json.dumps({'error': 'Error generating PDF'}),
                    status=500,
                    content_type='application/json'
                )

            # Extract PDF bytes
            if isinstance(pdf_result, (tuple, list)) and len(pdf_result) > 0:
                pdf_data = pdf_result[0]
            else:
                pdf_data = pdf_result

            if not isinstance(pdf_data, bytes):
                return Response(
                    json.dumps({'error': 'Invalid PDF data'}),
                    status=500,
                    content_type='application/json'
                )

            # Return PDF
            return request.make_response(
                pdf_data,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', f'attachment; filename="Section4_Notification_{notification.name or "Form10"}.pdf"')
                ]
            )

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

