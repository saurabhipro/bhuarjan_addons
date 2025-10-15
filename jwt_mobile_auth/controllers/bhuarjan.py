# -*- coding: utf-8 -*-
from odoo import http
from .main import *


class ProjectController(http.Controller):

    @http.route(['/project', "/project/<int:project_id>"], type='http', auth='none', methods=['GET'], csrf=False)
    @check_permission
    def get_project(self, project_id=None, **kwargs):
        try:
            data = json.loads(request.httprequest.data or "{}")
            patwari = request.env.ref('bhuarjan.group_bhuarjan_patwari').id
            print("\n\n request user - ", request.user)
            # if patwari_group in user.groups_id:
            #     print("User IS a Patwari.")
                # Do something for Patwari
            
            bhu_project = request.env['bhu.project']
            if request.httprequest.method == 'GET':
                if project_id:
                    project = bhu_project.sudo().browse(project_id)
                    if not project.exists():
                        return Response(json.dumps({'error': 'project not found'}), status=404, content_type='application/json')
                    return Response(json.dumps({'id': project.id, 'name': project.name}), status=200, content_type='application/json')
                
                projects = bhu_project.sudo().search([])
                return Response(json.dumps
                (
                    [
                        {
                            'id': project.id, 
                            'name': project.name, 
                            'villages_ids':[
                                {
                                    'district_id':village.district_id.id,
                                    'district_name':village.district_id.name,
                                    'village_id':village.village_id.id,
                                    'village_name':village.village_id.name
                                }   
                            for village in project.village_ids
                            ]
                        }
                    for project in projects]), 
                status=200, content_type='application/json')
            
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

        except jwt.ExpiredSignatureError:
            raise AccessError('JWT token has expired')
        except jwt.InvalidTokenError:
            raise AccessError('Invalid JWT token')




    @http.route(['/projects'], type='http', auth='none', methods=['GET'], csrf=False)
    def get_zones(self, zone_id=None, **kwargs):
        try:
            data = json.loads(request.httprequest.data or "{}")
            
            if request.httprequest.method == 'GET':
                if zone_id:
                    zone = request.env['bhu.project'].sudo().browse(zone_id)
                    if not zone.exists():
                        return Response(json.dumps({'error': 'Zone not found'}), status=404, content_type='application/json')
                    return Response(json.dumps({'id': zone.id, 'name': zone.name}), status=200, content_type='application/json')
                
                zones = request.env['smkc.zone'].sudo().search([])
                return Response(json.dumps([{'id': zone.id, 'name': zone.name} for zone in zones]), status=200, content_type='application/json')
            
        except Exception as e:
            # Catch any unexpected errors and return a 500 status code with error message
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')
                


        except jwt.ExpiredSignatureError:
            raise AccessError('JWT token has expired')
        except jwt.InvalidTokenError:
            raise AccessError('Invalid JWT token')
        

