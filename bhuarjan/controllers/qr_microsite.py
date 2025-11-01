from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class Form10PDFController(http.Controller):
    """Controller for direct PDF download from QR code scan"""

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
            
            # Generate PDF directly using Odoo's report rendering
            # Convert to list of integers to avoid any type issues
            res_ids = [int(survey.id)]
            
            # Render PDF directly
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
            return request.make_response(
                pdf_data,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', f'attachment; filename="Form10_{survey.name or survey_uuid}.pdf"'),
                    ('Content-Length', str(len(pdf_data)))
                ]
            )
            
        except Exception as e:
            _logger.error(f"Error generating PDF for survey {survey_uuid}: {str(e)}", exc_info=True)
            return request.not_found(f"Error generating PDF: {str(e)}")
