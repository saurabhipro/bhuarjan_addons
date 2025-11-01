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
            
            # Use _render_qweb_pdf - it expects a list of record IDs and returns (pdf_data, format)
            pdf_result = report_action.sudo()._render_qweb_pdf([survey.id])
            
            # Handle the return value - it's a tuple (pdf_bytes, format)
            if isinstance(pdf_result, tuple):
                pdf_data = pdf_result[0]
            else:
                pdf_data = pdf_result
            
            # Ensure we have bytes
            if not isinstance(pdf_data, bytes):
                if isinstance(pdf_data, (list, tuple)):
                    pdf_data = pdf_data[0] if pdf_data else b''
                else:
                    pdf_data = bytes(pdf_data) if not isinstance(pdf_data, str) else pdf_data.encode('utf-8')
            
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
