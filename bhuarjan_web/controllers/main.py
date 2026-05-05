from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.session import Session


class BhuarjanWebsite(http.Controller):

    @http.route('/', type='http', auth='public', website=True, sitemap=True)
    def homepage(self, **kwargs):
        return request.render('bhuarjan_web.homepage')

    @http.route('/contact', type='http', auth='public', website=True, sitemap=True)
    def contact(self, **kwargs):
        return request.render('bhuarjan_web.contact_page')

    @http.route('/features', type='http', auth='public', website=True, sitemap=True)
    def features(self, **kwargs):
        return request.render('bhuarjan_web.features_page')

    @http.route('/acts', type='http', auth='public', website=True, sitemap=True)
    def acts(self, **kwargs):
        return request.render('bhuarjan_web.acts_page')

    @http.route('/mobile-app', type='http', auth='public', website=True, sitemap=True)
    def mobile_app(self, **kwargs):
        return request.render('bhuarjan_web.mobile_app_page')

    @http.route('/contact/submit', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def contact_submit(self, **post):
        name = post.get('name', '')
        email = post.get('email', '')
        phone = post.get('phone', '')
        message = post.get('message', '')
        if name and email:
            request.env['mail.message'].sudo().create({
                'body': f'<p><b>From:</b> {name} ({email})<br/>'
                        f'<b>Phone:</b> {phone}<br/>'
                        f'<b>Message:</b> {message}</p>',
                'message_type': 'comment',
                'subject': f'Website Contact: {name}',
                'subtype_id': request.env.ref('mail.mt_comment').id,
            })
        return request.render('bhuarjan_web.contact_thanks')

    @http.route('/logout', type='http', auth='public', website=True, sitemap=False)
    def logout(self, **kwargs):
        """Convenient public logout that always returns to the homepage."""
        request.session.logout(keep_db=True)
        return request.redirect('/')


class BhuarjanSession(Session):
    """Override Odoo's default logout so users land on our homepage instead of /odoo."""

    @http.route('/web/session/logout', type='http', auth="none")
    def logout(self, redirect='/'):
        return super().logout(redirect=redirect)
