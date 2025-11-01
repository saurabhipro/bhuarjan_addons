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
                report_action = request.env.ref('bhuarjan.action_report_form10_survey')
            except ValueError:
                return request.not_found("Report not found")
            
            if not report_action.exists():
                return request.not_found("Report not found")
            
            # Render PDF - The 'split' error suggests Odoo is processing something incorrectly
            # Use the recordset's IDs list directly without conversion
            res_ids = survey.ids  # This is already a list-like object from recordset
            
            # Render PDF with empty data dict (not None) to avoid internal processing issues
            try:
                # Use empty dict - Odoo expects dict type for data parameter
                pdf_result = report_action.sudo()._render_qweb_pdf(res_ids, data={})
            except Exception as e:
                _logger.error(f"PDF rendering failed: {str(e)}", exc_info=True)
                # Log full traceback to understand where 'split' is being called
                raise
            
            # Extract PDF bytes from result (always returns tuple: (pdf_bytes, format))
            if not pdf_result:
                return request.not_found("Error: PDF rendering returned empty result")
            
            if isinstance(pdf_result, tuple):
                pdf_data = pdf_result[0] if len(pdf_result) > 0 else None
            elif isinstance(pdf_result, list):
                pdf_data = pdf_result[0] if len(pdf_result) > 0 else None
            else:
                pdf_data = pdf_result
            
            if pdf_data is None:
                return request.not_found("Error: PDF data is None")
            
            # Ensure pdf_data is bytes
            if not isinstance(pdf_data, bytes):
                if isinstance(pdf_data, str):
                    pdf_data = pdf_data.encode('utf-8')
                elif pdf_data is None:
                    _logger.error("PDF data is None")
                    return request.not_found("Error: PDF generation returned None")
                else:
                    _logger.error(f"Unexpected PDF data type: {type(pdf_data)}")
                    return request.not_found(f"Error: Invalid PDF data type: {type(pdf_data)}")
            
            return request.make_response(
                pdf_data,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', f'attachment; filename="Form10_{survey.name or survey_uuid}.pdf"')
                ]
            )
            
        except Exception as e:
            _logger.error(f"Error generating PDF for survey {survey_uuid}: {str(e)}", exc_info=True)
            return request.not_found(f"Error generating PDF: {str(e)}")
