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
            
            # Render PDF - ensure res_ids is a simple list of integers (not recordset)
            # Convert to plain list to avoid any recordset-related issues
            survey_id = int(survey.id) if survey.id else None
            if not survey_id:
                return request.not_found("Invalid survey ID")
            
            res_ids = [survey_id]
            
            # Render PDF using the standard Odoo method
            # _render_qweb_pdf(res_ids, data=None) returns tuple (pdf_bytes, format)
            try:
                # First try with data=None
                pdf_result = report_action.sudo()._render_qweb_pdf(res_ids, data=None)
            except (TypeError, AttributeError) as e1:
                # If that fails, try without data parameter (some Odoo versions)
                try:
                    pdf_result = report_action.sudo()._render_qweb_pdf(res_ids)
                except Exception as e2:
                    # Last resort: try with empty dict
                    _logger.warning(f"Render attempts failed. Trying with empty dict. Error 1: {str(e1)}, Error 2: {str(e2)}")
                    pdf_result = report_action.sudo()._render_qweb_pdf(res_ids, data={})
            
            # Extract PDF bytes from tuple result
            if not isinstance(pdf_result, tuple) or len(pdf_result) < 1:
                _logger.error(f"Unexpected PDF result format: {type(pdf_result)}")
                return request.not_found("Error: Invalid PDF result format")
            
            pdf_data = pdf_result[0]
            
            # Ensure pdf_data is bytes
            if not isinstance(pdf_data, bytes):
                if isinstance(pdf_data, str):
                    pdf_data = pdf_data.encode('utf-8')
                elif pdf_data is None:
                    _logger.error("PDF data is None")
                    return request.not_found("Error: PDF generation returned None")
                else:
                    _logger.error(f"Unexpected PDF data type: {type(pdf_data)}, value: {pdf_data[:100] if hasattr(pdf_data, '__getitem__') else 'N/A'}")
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
