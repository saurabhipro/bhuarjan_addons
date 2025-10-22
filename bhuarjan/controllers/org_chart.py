from odoo import http
from odoo.http import request

class OrgChartController(http.Controller):
    @http.route('/bhuarjan/org_chart_data', type='json', auth='user')
    def get_users_tree(self):
        users = request.env['res.users'].sudo().search([])
        data = []
        for u in users:
            data.append({
                'id': u.id,
                'parent': u.parent_id.id or None,
                'name': u.name,
                'title': u.login,
            })
        return data