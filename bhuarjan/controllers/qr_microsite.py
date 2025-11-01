from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class Form10PDFController(http.Controller):
    """Controller for direct PDF download from QR code scan"""

    @http.route('/bhuarjan/qr/<string:survey_uuid>', type='http', auth='public', methods=['GET'], csrf=False, website=False)
    def qr_redirect(self, survey_uuid, **kwargs):
        """Redirect QR code scan (UUID only) to PDF download"""
        # Redirect to the download route
        return request.redirect(f'/bhuarjan/form10/{survey_uuid}/download')

    @http.route('/bhuarjan/form10/<string:survey_uuid>/download', type='http', auth='public', methods=['GET'], csrf=False, website=False)
    def download_pdf(self, survey_uuid, **kwargs):
        """Download Form 10 PDF directly"""
        try:
            survey = request.env['bhu.survey'].sudo().search([('survey_uuid', '=', survey_uuid)], limit=1)
            
            if not survey:
                return request.not_found("Survey not found")
            
            # Generate PDF report using Odoo's standard rendering
            try:
                report_action = request.env.ref('bhuarjan.action_report_form10_bulk_table')
            except ValueError:
                return request.not_found("Report not found")
            
            if not report_action.exists():
                return request.not_found("Report not found")
            
            # Get all surveys from the same village (matching the report wizard behavior)
            # This ensures the PDF contains all relevant surveys from the village
            domain = [
                ('village_id', '=', survey.village_id.id)
            ]
            all_surveys = request.env['bhu.survey'].sudo().search(domain, order='id')
            
            if not all_surveys:
                return request.not_found("No surveys found for this village")
            
            # Log how many surveys we're including for debugging
            _logger.info(f"Generating PDF for {len(all_surveys)} surveys from village {survey.village_id.name} (IDs: {all_surveys.ids})")
            
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
                    # Final fallback: redirect to Odoo's standard URL
                    report_url = f'/report/pdf/{report_action.report_name}/{survey.id}'
                    return request.redirect(report_url)
            
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
            # Use village name in filename since it contains all surveys from that village
            village_name = survey.village_id.name or 'All'
            filename = f"Form10_{village_name}_{survey.project_id.name or ''}.pdf".replace(' ', '_')
            return request.make_response(
                pdf_data,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', f'attachment; filename="{filename}"'),
                    ('Content-Length', str(len(pdf_data)))
                ]
            )
            
        except Exception as e:
            _logger.error(f"Error generating PDF for survey {survey_uuid}: {str(e)}", exc_info=True)
            return request.not_found(f"Error generating PDF: {str(e)}")
