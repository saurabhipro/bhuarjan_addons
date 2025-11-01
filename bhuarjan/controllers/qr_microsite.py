from odoo import http
from odoo.http import request
import logging
import re

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
                report_action = request.env.ref('bhuarjan.action_report_form10_bulk_table')
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
            # Pass explicit data dict to ensure correct context
            report_name = report_action.report_name
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
                # Fallback: try with minimal data (no context)
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
