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
            
            # Use Odoo's built-in report download mechanism to avoid internal rendering issues
            # Redirect to Odoo's standard report URL which handles PDF generation correctly
            report_name = report_action.report_name
            survey_id = survey.id
            
            # Use Odoo's standard report download URL format
            # Format: /report/pdf/{report_name}/{record_ids}
            report_url = f'/report/pdf/{report_name}/{survey_id}'
            
            # Redirect to Odoo's built-in report controller which handles PDF correctly
            return request.redirect(report_url)
            
        except Exception as e:
            _logger.error(f"Error generating PDF for survey {survey_uuid}: {str(e)}", exc_info=True)
            return request.not_found(f"Error generating PDF: {str(e)}")
