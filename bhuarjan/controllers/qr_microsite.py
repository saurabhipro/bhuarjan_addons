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
            
            # Render PDF - use positional arguments with empty data dict
            # _render_qweb_pdf(res_ids, data={}) returns (pdf_bytes, format)
            pdf_result = report_action.sudo()._render_qweb_pdf(survey.ids, {})
            
            # Extract PDF bytes from the result
            if isinstance(pdf_result, tuple):
                pdf_data = pdf_result[0]
            elif isinstance(pdf_result, list):
                pdf_data = pdf_result[0] if pdf_result else b''
            else:
                pdf_data = pdf_result
            
            # Ensure pdf_data is bytes
            if not isinstance(pdf_data, bytes):
                if isinstance(pdf_data, str):
                    pdf_data = pdf_data.encode('utf-8')
                elif pdf_data is None:
                    pdf_data = b''
                else:
                    try:
                        pdf_data = bytes(pdf_data)
                    except (TypeError, ValueError):
                        _logger.error(f"Could not convert PDF data to bytes. Type: {type(pdf_data)}")
                        return request.not_found("Error: Invalid PDF data format")
            
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
