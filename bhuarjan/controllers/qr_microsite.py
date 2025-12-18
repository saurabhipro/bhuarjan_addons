from odoo import http
from odoo.http import request
import logging
import re
import base64

_logger = logging.getLogger(__name__)


class Form10PDFController(http.Controller):
    """Controller for direct PDF download from QR code scan"""

    @http.route('/bhuarjan/form10/<path:project_uuid>/<path:village_uuid>/download', type='http', auth='public', methods=['GET'], csrf=False, website=False)
    def download_pdf(self, project_uuid, village_uuid, **kwargs):
        """Download Form 10 PDF directly using project and village UUIDs - gets all surveys for that project in that village"""
        _logger.info(f"PDF download route called: project_uuid={project_uuid}, village_uuid={village_uuid}")
        try:
            # Find project by UUID - clear cache to ensure fresh lookup
            project = request.env['bhu.project'].sudo().with_context({}).search([('project_uuid', '=', project_uuid)], limit=1)
            _logger.info(f"Project search result: found={bool(project)}, uuid={project_uuid}, project_id={project.id if project else None}, project_name={project.name if project else None}")
            if not project:
                _logger.error(f"Project not found with UUID: {project_uuid}")
                return request.not_found("Project not found")
            
            # Find village by UUID - clear cache to ensure fresh lookup
            # IMPORTANT: Check for duplicate UUIDs - if multiple villages have the same UUID, we have a problem
            all_villages_with_uuid = request.env['bhu.village'].sudo().with_context({}).search([('village_uuid', '=', village_uuid)])
            _logger.info(f"Villages with UUID {village_uuid}: {len(all_villages_with_uuid)} found (IDs: {all_villages_with_uuid.ids})")
            
            if len(all_villages_with_uuid) > 1:
                _logger.error(f"DUPLICATE UUID ERROR! UUID {village_uuid} is assigned to {len(all_villages_with_uuid)} villages: {[(v.id, v.name) for v in all_villages_with_uuid]}")
                # Regenerate UUIDs for all duplicates except the first one
                for dup_village in all_villages_with_uuid[1:]:
                    import uuid
                    new_uuid = str(uuid.uuid4())
                    _logger.warning(f"Regenerating UUID for village {dup_village.id} ({dup_village.name}): {village_uuid} -> {new_uuid}")
                    dup_village.write({'village_uuid': new_uuid})
                # Use the first village (keep its UUID)
                village = all_villages_with_uuid[0]
            elif len(all_villages_with_uuid) == 1:
                village = all_villages_with_uuid[0]
            else:
                village = False
            
            _logger.info(f"Village search result: found={bool(village)}, uuid={village_uuid}, village_id={village.id if village else None}, village_name={village.name if village else None}")
            if not village:
                _logger.error(f"Village not found with UUID: {village_uuid}")
                return request.not_found("Village not found")
            
            # Verify UUIDs match to prevent any confusion
            if project.project_uuid != project_uuid:
                _logger.error(f"Project UUID mismatch! Expected {project_uuid}, got {project.project_uuid}")
            if village.village_uuid != village_uuid:
                _logger.error(f"Village UUID mismatch! Expected {village_uuid}, got {village.village_uuid}")
            
            # Generate PDF report using Odoo's standard rendering
            try:
                report_action = request.env.ref('bhuarjan.action_report_form10_bulk_table').sudo()
            except ValueError:
                return request.not_found("Report not found")
            
            if not report_action.exists():
                return request.not_found("Report not found")
            
            # Get all surveys for the specific project AND village
            # Use explicit AND operator to ensure strict filtering
            domain = [
                '&',  # Explicit AND operator
                ('project_id', '=', project.id),
                ('village_id', '=', village.id)
            ]
            
            # Log the search domain for debugging
            _logger.info(f"Searching surveys with domain: {domain}")
            _logger.info(f"Expected: Project ID={project.id} (UUID={project.project_uuid}, Name={project.name}), Village ID={village.id} (UUID={village.village_uuid}, Name={village.name})")
            
            # Clear any existing context/cache and search fresh
            # Also disable project.filter mixin by clearing bhuarjan_current_project_id
            all_surveys = request.env['bhu.survey'].sudo().with_context(
                active_test=False,
                bhuarjan_current_project_id=False
            ).search(domain, order='id')
            
            # Log ALL surveys found (for debugging)
            _logger.info(f"Found {len(all_surveys)} surveys. Details:")
            for survey in all_surveys:
                survey_info = f"  Survey ID={survey.id}: Project ID={survey.project_id.id} (Name={survey.project_id.name}), Village ID={survey.village_id.id} (Name={survey.village_id.name}, UUID={survey.village_id.village_uuid})"
                _logger.info(survey_info)
                
                # Verify each survey belongs to the correct project and village
                if survey.project_id.id != project.id:
                    _logger.error(f"ERROR: Survey {survey.id} has wrong project! Expected Project ID={project.id}, got {survey.project_id.id}")
                if survey.village_id.id != village.id:
                    _logger.error(f"ERROR: Survey {survey.id} has wrong village! Expected Village ID={village.id} (UUID={village.village_uuid}, Name={village.name}), got Village ID={survey.village_id.id} (UUID={survey.village_id.village_uuid}, Name={survey.village_id.name})")
                if survey.village_id.village_uuid != village_uuid:
                    _logger.error(f"ERROR: Survey {survey.id} belongs to village with different UUID! Expected {village_uuid}, got {survey.village_id.village_uuid}")
            
            if not all_surveys:
                # Check if there are ANY surveys for this project (to help debug)
                project_surveys = request.env['bhu.survey'].sudo().search([('project_id', '=', project.id)])
                _logger.warning(f"No surveys found for project {project.id} and village {village.id}. Total surveys for this project: {len(project_surveys)}")
                if project_surveys:
                    _logger.warning(f"Villages with surveys in this project: {set(project_surveys.mapped('village_id.id'))}")
                return request.not_found("No surveys found for this project and village")
            
            # Log how many surveys we're including for debugging
            _logger.info(f"Generating PDF for {len(all_surveys)} surveys from project {project.name} (ID: {project.id}) in village {village.name} (ID: {village.id}) (Survey IDs: {all_surveys.ids})")
            
            # Convert recordset to list of IDs for PDF rendering
            # Ensure we have the correct IDs
            res_ids = [int(sid) for sid in all_surveys.ids]
            
            if not res_ids:
                return request.not_found("No survey IDs found")
            
            # Double-check: Browse the records again and FILTER OUT any that don't match
            # This ensures we're passing ONLY the correct IDs to the PDF renderer
            verify_surveys = request.env['bhu.survey'].sudo().browse(res_ids)
            correct_survey_ids = []
            for survey in verify_surveys:
                if survey.project_id.id != project.id:
                    _logger.error(f"FILTERING OUT Survey {survey.id}: Wrong project! Expected Project ID={project.id}, got {survey.project_id.id}")
                    continue
                if survey.village_id.id != village.id:
                    _logger.error(f"FILTERING OUT Survey {survey.id}: Wrong village! Expected Village ID={village.id} (UUID={village.village_uuid}, Name={village.name}), got Village ID={survey.village_id.id} (UUID={survey.village_id.village_uuid}, Name={survey.village_id.name})")
                    continue
                if survey.village_id.village_uuid != village_uuid:
                    _logger.error(f"FILTERING OUT Survey {survey.id}: Village UUID mismatch! Expected {village_uuid}, got {survey.village_id.village_uuid}")
                    continue
                # Survey is correct, include it
                correct_survey_ids.append(survey.id)
            
            # Use only the correct survey IDs
            if len(correct_survey_ids) != len(res_ids):
                _logger.warning(f"Filtered out {len(res_ids) - len(correct_survey_ids)} incorrect surveys. Using {len(correct_survey_ids)} correct surveys.")
            
            if not correct_survey_ids:
                _logger.error("No correct surveys found after filtering!")
                return request.not_found("No valid surveys found for this project and village")
            
            # Update res_ids to only include correct surveys
            res_ids = correct_survey_ids
            
            # Log the exact IDs being passed
            _logger.info(f"Rendering PDF with res_ids: {res_ids}")
            
            # Invalidate report cache to ensure fresh generation
            # This prevents any caching issues that might cause the wrong data to appear
            report_action.invalidate_recordset(['report_name', 'report_file'])
            
            # Render PDF directly - Odoo will populate 'docs' in template with these records
            # _render_qweb_pdf signature: (reportname, docids, data=None)
            # Odoo automatically populates 'docs' from res_ids, so we don't need to pass it explicitly
            report_name = report_action.report_name
            
            # Verify surveys exist before rendering
            verify_surveys = request.env['bhu.survey'].sudo().browse(res_ids)
            _logger.info(f"Verifying {len(verify_surveys)} surveys before PDF render: {verify_surveys.ids}")
            if not verify_surveys:
                _logger.error("No surveys found to render PDF!")
                return request.not_found("No surveys found for PDF generation")
            
            data = {
                'report_type': 'qweb-pdf',
                'context': {
                    'project_id': project.id,
                    'village_id': village.id,
                }
            }
            try:
                pdf_result = report_action.sudo()._render_qweb_pdf(report_name, res_ids, data=data)
            except Exception as render_error:
                # Fallback: try with minimal data
                _logger.warning(f"PDF render with data failed: {str(render_error)}, trying fallback")
                try:
                    pdf_result = report_action.sudo()._render_qweb_pdf(report_name, res_ids, data={})
                except Exception as render_error2:
                    _logger.error(f"PDF rendering failed: {str(render_error2)}", exc_info=True)
                    # Final fallback: redirect to Odoo's standard URL (use first survey ID)
                    if all_surveys:
                        report_url = f'/report/pdf/{report_action.report_name}/{all_surveys[0].id}'
                        return request.redirect(report_url)
                    return request.not_found("No surveys available for PDF generation")
            
            # Extract PDF bytes from result
            if not pdf_result:
                return request.not_found("Error: PDF rendering returned empty result")
            
            # Handle tuple/list result (pdf_bytes, format)
            if isinstance(pdf_result, (tuple, list)) and len(pdf_result) > 0:
                pdf_data = pdf_result[0]
            else:
                pdf_data = pdf_result
            
            # Ensure pdf_data is bytes
            if not isinstance(pdf_data, bytes):
                if isinstance(pdf_data, str):
                    pdf_data = pdf_data.encode('utf-8')
                else:
                    _logger.error(f"Unexpected PDF data type: {type(pdf_data)}")
                    return request.not_found(f"Error: Invalid PDF data type: {type(pdf_data)}")
            
            # Return PDF response with proper headers
            # Use project and village name in filename
            # Sanitize filename to avoid Unicode issues in HTTP headers (must be latin-1 compatible)
            project_name = (project.name or 'All').replace(' ', '_')
            village_name = (village.name or 'All').replace(' ', '_')
            
            # Create ASCII-safe filename (remove/replace non-ASCII characters)
            project_name_ascii = re.sub(r'[^\x00-\x7F]+', '', project_name) or 'Project'
            village_name_ascii = re.sub(r'[^\x00-\x7F]+', '', village_name) or 'Village'
            
            # If names become empty after removing non-ASCII, use project/village IDs
            if not project_name_ascii or project_name_ascii == '_':
                project_name_ascii = f'Project_{project.id}'
            if not village_name_ascii or village_name_ascii == '_':
                village_name_ascii = f'Village_{village.id}'
            
            filename = f"Form10_{project_name_ascii}_{village_name_ascii}.pdf"
            
            return request.make_response(
                pdf_data,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', f'attachment; filename="{filename}"'),
                    ('Content-Length', str(len(pdf_data)))
                ]
            )
            
        except Exception as e:
            _logger.error(f"Error generating PDF for project {project_uuid} and village {village_uuid}: {str(e)}", exc_info=True)
            return request.not_found(f"Error generating PDF: {str(e)}")
    
    @http.route('/bhuarjan/section4/<path:notification_uuid>/download', type='http', auth='public', methods=['GET'], csrf=False, website=False)
    def download_section4_pdf(self, notification_uuid, **kwargs):
        """Download Section 4 Notification PDF using notification UUID - serves signed document if exists, else unsigned PDF"""
        _logger.info(f"Section 4 PDF download route called: notification_uuid={notification_uuid}")
        try:
            # Find notification by UUID
            notification = request.env['bhu.section4.notification'].sudo().with_context({}).search([('notification_uuid', '=', notification_uuid)], limit=1)
            
            if not notification:
                _logger.error(f"Notification not found with UUID: {notification_uuid}")
                return request.not_found("Notification not found")
            
            _logger.info(f"Notification found: id={notification.id}, name={notification.name}, has_signed={bool(notification.signed_document_file)}")
            
            # If signed document exists, serve it
            if notification.signed_document_file:
                _logger.info("Serving signed document")
                pdf_data = base64.b64decode(notification.signed_document_file)
                filename = notification.signed_document_filename or f"Section4_Notification_{notification.name}_Signed.pdf"
                
                response = request.make_response(
                    pdf_data,
                    headers=[
                        ('Content-Type', 'application/pdf'),
                        ('Content-Disposition', f'attachment; filename="{filename}"'),
                        ('Content-Length', str(len(pdf_data))),
                    ]
                )
                return response
            
            # Otherwise, generate unsigned PDF
            _logger.info("Generating unsigned PDF")
            report_action = request.env.ref('bhuarjan.action_report_section4_notification')
            
            # Create wizard with notification data
            wizard = request.env['bhu.section4.notification.wizard'].sudo().create({
                'project_id': notification.project_id.id,
                'village_id': notification.village_id.id,
                'public_purpose': notification.public_purpose,
                'public_hearing_datetime': notification.public_hearing_datetime,
                'public_hearing_place': notification.public_hearing_place,
                'q1_brief_description': notification.q1_brief_description,
                'q2_directly_affected': notification.q2_directly_affected,
                'q3_indirectly_affected': notification.q3_indirectly_affected,
                'q4_private_assets': notification.q4_private_assets,
                'q5_government_assets': notification.q5_government_assets,
                'q6_minimal_acquisition': notification.q6_minimal_acquisition,
                'q7_alternatives_considered': notification.q7_alternatives_considered,
                'q8_total_cost': notification.q8_total_cost,
                'q9_project_benefits': notification.q9_project_benefits,
                'q10_compensation_measures': notification.q10_compensation_measures,
                'q11_other_components': notification.q11_other_components,
            })
            
            # Generate PDF
            pdf_result = report_action.sudo()._render_qweb_pdf(report_action.report_name, [wizard.id], data={})
            
            if not pdf_result:
                return request.not_found("Error: PDF rendering returned empty result")
            
            # Extract PDF bytes
            if isinstance(pdf_result, (tuple, list)) and len(pdf_result) > 0:
                pdf_data = pdf_result[0]
            else:
                pdf_data = pdf_result
            
            if not isinstance(pdf_data, bytes):
                if isinstance(pdf_data, str):
                    pdf_data = pdf_data.encode('utf-8')
                else:
                    _logger.error(f"Unexpected PDF data type: {type(pdf_data)}")
                    return request.not_found(f"Error: Invalid PDF data type: {type(pdf_data)}")
            
            # Return PDF response
            filename = f"Section4_Notification_{notification.name}.pdf"
            response = request.make_response(
                pdf_data,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', f'attachment; filename="{filename}"'),
                    ('Content-Length', str(len(pdf_data))),
                ]
            )
            return response
        
        except Exception as e:
            _logger.error(f"Error in download_section4_pdf: {str(e)}", exc_info=True)
            return request.not_found(f"Error: {str(e)}")
    
    @http.route('/bhuarjan/sia/<path:sia_team_uuid>/download', type='http', auth='public', methods=['GET'], csrf=False, website=False)
    def download_sia_pdf(self, sia_team_uuid, **kwargs):
        """Download SIA Team PDF using SIA team UUID"""
        _logger.info(f"SIA PDF download route called: sia_team_uuid={sia_team_uuid}")
        try:
            # Find SIA team by UUID
            sia_team = request.env['bhu.sia.team'].sudo().with_context({}).search([('sia_team_uuid', '=', sia_team_uuid)], limit=1)
            
            if not sia_team:
                _logger.error(f"SIA team not found with UUID: {sia_team_uuid}")
                return request.not_found("SIA team not found")
            
            _logger.info(f"SIA team found: id={sia_team.id}, name={sia_team.name}")
            
            # Generate PDF
            _logger.info("Generating SIA PDF")
            try:
                # Use sudo() to bypass access rights when getting the report action
                report_action = request.env['ir.actions.report'].sudo().search([
                    ('report_name', '=', 'bhuarjan.sia_order_report')
                ], limit=1)
                
                if not report_action:
                    # Fallback: try using ir.model.data
                    _logger.info("SIA download: Report not found by name, trying ir.model.data")
                    try:
                        report_data = request.env['ir.model.data'].sudo().search([
                            ('module', '=', 'bhuarjan'),
                            ('name', '=', 'action_report_sia_order')
                        ], limit=1)
                        if report_data and report_data.res_id:
                            report_action = request.env['ir.actions.report'].sudo().browse(report_data.res_id)
                    except Exception as e:
                        _logger.error(f"SIA download: Error in fallback: {str(e)}", exc_info=True)
                
                if not report_action or not report_action.exists():
                    _logger.error("SIA download: Report action not found")
                    return request.not_found("Report not found")
                
                _logger.info(f"SIA download: Report action found: {report_action.id}, report_name: {report_action.report_name}")
            except Exception as e:
                _logger.error(f"SIA download: Error getting report action: {str(e)}", exc_info=True)
                return request.not_found(f"Error accessing report: {str(e)}")
            
            # Generate PDF directly from SIA team record
            pdf_result = report_action.sudo()._render_qweb_pdf(report_action.report_name, [sia_team.id], data={})
            
            if not pdf_result:
                return request.not_found("Error: PDF rendering returned empty result")
            
            # Extract PDF bytes
            if isinstance(pdf_result, (tuple, list)) and len(pdf_result) > 0:
                pdf_data = pdf_result[0]
            else:
                pdf_data = pdf_result
            
            if not isinstance(pdf_data, bytes):
                if isinstance(pdf_data, str):
                    pdf_data = pdf_data.encode('utf-8')
                else:
                    _logger.error(f"Unexpected PDF data type: {type(pdf_data)}")
                    return request.not_found(f"Error: Invalid PDF data type: {type(pdf_data)}")
            
            # Return PDF response
            project_name = (sia_team.project_id.name or 'Project').replace(' ', '_')
            filename = f"SIA_{project_name}_{sia_team.create_date.strftime('%Y%m%d') if sia_team.create_date else 'Date'}.pdf"
            response = request.make_response(
                pdf_data,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', f'attachment; filename="{filename}"'),
                    ('Content-Length', str(len(pdf_data))),
                ]
            )
            return response
        
        except Exception as e:
            _logger.error(f"Error in download_sia_pdf: {str(e)}", exc_info=True)
            return request.not_found(f"Error: {str(e)}")
    
    @http.route('/bhuarjan/section11/<path:report_uuid>/download', type='http', auth='public', methods=['GET'], csrf=False, website=False)
    def download_section11_pdf(self, report_uuid, **kwargs):
        """Download Section 11 Preliminary Report PDF using report UUID - serves signed document if exists, else unsigned PDF"""
        _logger.info(f"Section 11 PDF download route called: report_uuid={report_uuid}")
        try:
            # Find report by UUID
            report = request.env['bhu.section11.preliminary.report'].sudo().with_context({}).search([('report_uuid', '=', report_uuid)], limit=1)
            
            if not report:
                _logger.error(f"Report not found with UUID: {report_uuid}")
                return request.not_found("Report not found")
            
            _logger.info(f"Report found: id={report.id}, name={report.name}, has_signed={bool(report.signed_document_file)}")
            
            # If signed document exists, serve it
            if report.signed_document_file:
                _logger.info("Serving signed document")
                pdf_data = base64.b64decode(report.signed_document_file)
                filename = report.signed_document_filename or f"Section11_Preliminary_Report_{report.name}_Signed.pdf"
                
                response = request.make_response(
                    pdf_data,
                    headers=[
                        ('Content-Type', 'application/pdf'),
                        ('Content-Disposition', f'attachment; filename="{filename}"'),
                        ('Content-Length', str(len(pdf_data))),
                    ]
                )
                return response
            
            # Otherwise, generate unsigned PDF
            _logger.info("Generating unsigned PDF")
            report_action = request.env.ref('bhuarjan.action_report_section11_preliminary')
            
            # Generate PDF directly from report record
            pdf_result = report_action.sudo()._render_qweb_pdf(report_action.report_name, [report.id], data={})
            
            if not pdf_result:
                return request.not_found("Error: PDF rendering returned empty result")
            
            # Extract PDF bytes
            if isinstance(pdf_result, (tuple, list)) and len(pdf_result) > 0:
                pdf_data = pdf_result[0]
            else:
                pdf_data = pdf_result
            
            if not isinstance(pdf_data, bytes):
                if isinstance(pdf_data, str):
                    pdf_data = pdf_data.encode('utf-8')
                else:
                    _logger.error(f"Unexpected PDF data type: {type(pdf_data)}")
                    return request.not_found(f"Error: Invalid PDF data type: {type(pdf_data)}")
            
            # Return PDF response
            filename = f"Section11_Preliminary_Report_{report.name}.pdf"
            response = request.make_response(
                pdf_data,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', f'attachment; filename="{filename}"'),
                    ('Content-Length', str(len(pdf_data))),
                ]
            )
            return response
        
        except Exception as e:
            _logger.error(f"Error in download_section11_pdf: {str(e)}", exc_info=True)
            return request.not_found(f"Error: {str(e)}")
