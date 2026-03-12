from odoo import http
from odoo.http import request
import json

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
                'tehsils': [t.name for t in u.tehsil_ids] if u.tehsil_ids else [],
                'sub_divisions': [s.name for s in u.sub_division_ids] if u.sub_division_ids else [],
            })
        return data

    @http.route('/bhuarjan/detailed_hierarchy', type='json', auth='user')
    def get_detailed_hierarchy(self):
        """
        Returns a complete tree starting from Raigarh district.
        Structure: District -> Tehsils -> Villages -> Users (by role)
        """
        # 1. Find the parent District (Raigarh)
        district = request.env['bhu.district'].sudo().search([('name', 'ilike', 'Raigarh')], limit=1)
        if not district:
            # Fallback to the first district if Raigarh not found
            district = request.env['bhu.district'].sudo().search([], limit=1)
        
        if not district:
            return {'error': 'No district found'}

        # 2. Get all Tehsils under this district
        tehsils = request.env['bhu.tehsil'].sudo().search([('district_id', '=', district.id)])
        
        # 3. Get all Users for this district
        users = request.env['res.users'].sudo().search([('district_id', '=', district.id), ('active', '=', True)])
        
        # Helper to get avatar
        def get_avatar(u):
            return u.avatar_128.decode('utf-8') if u.avatar_128 else None

        # Build the tree
        tree = {
            'id': f'd_{district.id}',
            'name': district.name,
            'type': 'district',
            'children': []
        }

        # Sub-hierarchy for Users directly under District (e.g. Collector, Admin)
        district_users = users.filtered(lambda u: not u.tehsil_ids and not u.village_ids and u.bhuarjan_role in ['collector', 'additional_collector', 'district_administrator', 'administrator'])
        for u in district_users:
            tree['children'].append({
                'id': f'u_{u.id}',
                'name': u.name,
                'type': 'user',
                'role': u.bhuarjan_role,
                'avatar': get_avatar(u),
                'title': u.login
            })

        for tehsil in tehsils:
            tehsil_node = {
                'id': f't_{tehsil.id}',
                'name': tehsil.name,
                'type': 'tehsil',
                'children': []
            }
            
            # Users assigned to this Tehsil (but no specific villages) - e.g. SDM, Tehsildar
            tehsil_users = users.filtered(lambda u: tehsil.id in u.tehsil_ids.ids and not u.village_ids)
            for u in tehsil_users:
                tehsil_node['children'].append({
                    'id': f'u_{u.id}',
                    'name': u.name,
                    'type': 'user',
                    'role': u.bhuarjan_role,
                    'avatar': get_avatar(u),
                    'title': u.login
                })
            
            # Villages under this Tehsil
            villages = request.env['bhu.village'].sudo().search([('tehsil_id', '=', tehsil.id)])
            for village in villages:
                village_node = {
                    'id': f'v_{village.id}',
                    'name': village.name,
                    'type': 'village',
                    'children': []
                }
                
                # Users assigned to this Village - e.g. Patwari, RI
                village_users = users.filtered(lambda u: village.id in u.village_ids.ids)
                for u in village_users:
                    village_node['children'].append({
                        'id': f'u_{u.id}',
                        'name': u.name,
                        'type': 'user',
                        'role': u.bhuarjan_role,
                        'avatar': get_avatar(u),
                        'title': u.login
                    })
                
                if village_node['children'] or True: # Always show village node or hide if empty? 
                                                     # User wants complete tree, so keep it.
                    tehsil_node['children'].append(village_node)
            
            tree['children'].append(tehsil_node)
            
        return tree