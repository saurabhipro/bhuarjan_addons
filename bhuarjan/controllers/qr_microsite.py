from odoo import http, fields
from odoo.http import request
import qrcode
import io
import base64


class QRMicrositeController(http.Controller):

    @http.route('/form10/<string:survey_uuid>', type='http', auth='public', website=True)
    def form10_microsite(self, survey_uuid, **kwargs):
        """Display Form 10 report as a microsite for QR code scanning"""
        try:
            # Find survey by UUID
            survey = request.env['bhu.survey'].sudo().search([('survey_uuid', '=', survey_uuid)], limit=1)
            
            if not survey:
                return request.render('bhuarjan.qr_form10_not_found', {
                    'error_message': 'Survey not found or invalid QR code'
                })
            
            # Generate QR code for this survey
            qr_code_data = request.httprequest.url_root + f'form10/{survey_uuid}'
            qr_code_img = self._generate_qr_code(qr_code_data)
            
            return request.render('bhuarjan.qr_form10_microsite', {
                'survey': survey,
                'qr_code_img': qr_code_img,
                'qr_code_data': qr_code_data
            })
            
        except Exception as e:
            return request.render('bhuarjan.qr_form10_error', {
                'error_message': f'Error loading survey: {str(e)}'
            })

    def _generate_qr_code(self, data):
        """Generate QR code image as base64 string"""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return img_str
        except ImportError:
            # Fallback if qrcode library is not installed
            return None

    @http.route('/form10/<string:survey_uuid>/pdf', type='http', auth='public')
    def form10_pdf_download(self, survey_uuid, **kwargs):
        """Download Form 10 PDF directly"""
        try:
            survey = request.env['bhu.survey'].sudo().search([('survey_uuid', '=', survey_uuid)], limit=1)
            
            if not survey:
                return request.not_found()
            
            # Generate PDF report
            report_action = request.env.ref('bhuarjan.action_report_form10_survey')
            pdf_data = report_action._render_qweb_pdf(survey.ids)[0]
            
            return request.make_response(
                pdf_data,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', f'attachment; filename="Form10_{survey.name}.pdf"')
                ]
            )
            
        except Exception as e:
            return request.not_found()
