# -*- coding: utf-8 -*-
from odoo import http
from .main import *

class Smkc(http.Controller):

    @http.route(['/api/zone', '/api/zone/<int:zone_id>'], type='http', auth='none', methods=['GET', 'POST', 'PUT', 'DELETE'], csrf=False)
    def get_zones(self, zone_id=None, **kwargs):
        try:
            data = json.loads(request.httprequest.data or "{}")
            
            if request.httprequest.method == 'GET':
                if zone_id:
                    zone = request.env['smkc.zone'].sudo().browse(zone_id)
                    if not zone.exists():
                        return Response(json.dumps({'error': 'Zone not found'}), status=404, content_type='application/json')
                    return Response(json.dumps({'id': zone.id, 'name': zone.name}), status=200, content_type='application/json')
                
                zones = request.env['smkc.zone'].sudo().search([])
                return Response(json.dumps([{'id': zone.id, 'name': zone.name} for zone in zones]), status=200, content_type='application/json')
            

            if request.httprequest.method == 'POST':
                name = data.get('name')
                if not name:
                    return Response(json.dumps({'error': 'Name is required'}), status=400, content_type='application/json')
                
                zone = request.env['smkc.zone'].sudo().create({'name': name})
                return Response(json.dumps({'id': zone.id, 'name': zone.name}), status=201, content_type='application/json')
            

            if request.httprequest.method == 'PUT' and zone_id:
                zone = request.env['smkc.zone'].sudo().browse(zone_id)
                if not zone.exists():
                    return Response(json.dumps({'error': 'Zone not found'}), status=404, content_type='application/json')

                name = data.get('name')
                if name:
                    zone.write({'name': name})

                return Response(json.dumps({'id': zone.id, 'name': zone.name}), status=200, content_type='application/json')
            

            if request.httprequest.method == 'DELETE' and zone_id:
                zone = request.env['smkc.zone'].sudo().browse(zone_id)
                if not zone.exists():
                    return Response(json.dumps({'error': 'Zone not found'}), status=404, content_type='application/json')
                
                zone.unlink()
                return Response(json.dumps({'status': 'deleted'}), status=200, content_type='application/json')

        except Exception as e:
            # Catch any unexpected errors and return a 500 status code with error message
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')
                


        except jwt.ExpiredSignatureError:
            raise AccessError('JWT token has expired')
        except jwt.InvalidTokenError:
            raise AccessError('Invalid JWT token')
        


    @http.route(['/api/ward', '/api/ward/<int:ward_id>'], type='http', auth='none', methods=['GET', 'POST', 'PUT', 'DELETE'], csrf=False)
    def get_wards(self, ward_id=None, **kwargs):
        print("self -- , ", self)
        try:
            # Parsing the incoming JSON body if present
            data = json.loads(request.httprequest.data or "{}")
            
            if request.httprequest.method == 'GET':
                if ward_id:
                    # Fetch a single ward by ID
                    ward = request.env['smkc.ward'].sudo().browse(ward_id)
                    if not ward.exists():
                        return Response(json.dumps({'error': 'Ward not found'}), status=404, content_type='application/json')
                    return Response(json.dumps({'id': ward.id, 'name': ward.name, 'zone_id': ward.zone.id, 'zone_name': ward.zone.name if ward.zone else None}), 
                                    status=200, content_type='application/json')
                
                # Fetch all wards
                wards = request.env['smkc.ward'].sudo().search([])
                print("asldkfjs")
                return Response(json.dumps([{'id': ward.id, 'name': ward.name, 'zone_id': ward.zone.id if ward.zone else None, 'zone_name': ward.zone.name if ward.zone else None} for ward in wards]), 
                                status=200, content_type='application/json')
            
            if request.httprequest.method == 'POST':
                name = data.get('name')
                zone_id = data.get('zone_id')
                if not name or not zone_id:
                    return Response(json.dumps({'error': 'Name and zone_id are required'}), status=400, content_type='application/json')
                
                # Create a new ward
                ward = request.env['smkc.ward'].sudo().create({
                    'name': name,
                    'zone': zone_id
                })
                return Response(json.dumps({'id': ward.id, 'name': ward.name, 'zone_id': ward.zone.id, 'zone_name': ward.zone.name if ward.zone else None}), 
                                status=201, content_type='application/json')
            
            if request.httprequest.method == 'PUT' and ward_id:
                ward = request.env['smkc.ward'].sudo().browse(ward_id)
                if not ward.exists():
                    return Response(json.dumps({'error': 'Ward not found'}), status=404, content_type='application/json')

                # Update the ward's name and zone
                name = data.get('name')
                zone_id = data.get('zone_id')
                if name:
                    ward.write({'name': name})
                if zone_id:
                    ward.write({'zone': zone_id})

                return Response(json.dumps({'id': ward.id, 'name': ward.name, 'zone_id': ward.zone.id, 'zone_name': ward.zone.name if ward.zone else None}),
                                status=200, content_type='application/json')
            
            if request.httprequest.method == 'DELETE' and ward_id:
                ward = request.env['smkc.ward'].sudo().browse(ward_id)
                if not ward.exists():
                    return Response(json.dumps({'error': 'Ward not found'}), status=404, content_type='application/json')
                
                # Delete the ward
                ward.unlink()
                return Response(json.dumps({'status': 'deleted'}), status=200, content_type='application/json')

        except Exception as e:
            # Catch any unexpected errors and return a 500 status code with error message
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')
