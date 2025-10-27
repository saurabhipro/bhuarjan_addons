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
                'role': u.bhuarjan_role or 'No Role',
                'state': u.state_id.name if u.state_id else 'No State',
                'district': u.district_id.name if u.district_id else 'No District',
                'mobile': u.mobile or 'No Mobile',
                'active': u.active,
                'avatar': u.avatar_128.decode('utf-8') if u.avatar_128 else None,
                'subordinates_count': len(u.child_ids),
                'villages': [v.name for v in u.village_ids] if u.village_ids else [],
                'circles': [c.name for c in u.circle_ids] if u.circle_ids else [],
                'tehsils': [t.name for t in u.tehsil_ids] if u.tehsil_ids else [],
                'sub_divisions': [s.name for s in u.sub_division_ids] if u.sub_division_ids else [],
            })
        return data