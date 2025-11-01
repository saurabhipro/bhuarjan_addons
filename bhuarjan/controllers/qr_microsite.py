from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class Form10PDFController(http.Controller):
    """Controller for direct PDF download from QR code scan"""

    @http.route('/bhuarjan/qr/<string:project_uuid>/<string:village_uuid>', type='http', auth='public', methods=['GET'], csrf=False, website=False)
    def qr_download(self, project_uuid, village_uuid, **kwargs):
        """Direct PDF download from QR code scan (project and village UUIDs)"""
        try:
            if not project_uuid or not village_uuid:
                _logger.error(f"Missing UUIDs: project_uuid={project_uuid}, village_uuid={village_uuid}")
                return request.not_found("Invalid QR code: Missing project or village UUID")
            # Directly download PDF - no redirect
            return self.download_pdf(project_uuid, village_uuid, **kwargs)
        except Exception as e:
            _logger.error(f"Error in QR download route: {str(e)}", exc_info=True)
            return request.not_found(f"Error: {str(e)}")

    @http.route('/bhuarjan/form10/<string:project_uuid>/<string:village_uuid>/download', type='http', auth='public', methods=['GET'], csrf=False, website=False)
    def download_pdf(self, project_uuid, village_uuid, **kwargs):
        """Download Form 10 PDF directly using project and village UUIDs - gets all surveys for that project in that village"""
        try:
            # Find project by UUID
            project = request.env['bhu.project'].sudo().search([('project_uuid', '=', project_uuid)], limit=1)
            if not project:
                return request.not_found("Project not found")
            
            # Find village by UUID
            village = request.env['bhu.village'].sudo().search([('village_uuid', '=', village_uuid)], limit=1)
            if not village:
                return request.not_found("Village not found")
            
            # Generate PDF report using Odoo's standard rendering
            try:
                report_action = request.env.ref('bhuarjan.action_report_form10_bulk_table')
            except ValueError:
                return request.not_found("Report not found")
            
            if not report_action.exists():
                return request.not_found("Report not found")
            
            # Get all surveys for the specific project AND village
            # This ensures the PDF contains all surveys for that project in that village
            domain = [
                ('project_id', '=', project.id),
                ('village_id', '=', village.id)
            ]
            all_surveys = request.env['bhu.survey'].sudo().search(domain, order='id')
            
            if not all_surveys:
                return request.not_found("No surveys found for this project and village")
            
            # Log how many surveys we're including for debugging
            _logger.info(f"Generating PDF for {len(all_surveys)} surveys from project {project.name} in village {village.name} (IDs: {all_surveys.ids})")
            
            # Convert recordset to list of IDs for PDF rendering
            # Odoo's _render_qweb_pdf expects a list of integer IDs
            res_ids = list(all_surveys.ids)
            
            if not res_ids:
                return request.not_found("No survey IDs found")
            
            # Render PDF directly - Odoo will populate 'docs' in template with these records
            try:
                pdf_result = report_action.sudo()._render_qweb_pdf(res_ids, data=None)
            except Exception as render_error:
                # Fallback: try with empty dict
                try:
                    pdf_result = report_action.sudo()._render_qweb_pdf(res_ids, data={})
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
            project_name = project.name or 'All'
            village_name = village.name or 'All'
            filename = f"Form10_{project_name}_{village_name}.pdf".replace(' ', '_')
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
