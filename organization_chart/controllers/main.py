from odoo import http
from odoo.http import request

import logging
_logger = logging.getLogger(__name__)

class OrgChart(http.Controller):
    
    @http.route('/orgchart/get_user_group', type="json", auth='user')                
    def get_user_group(self, user_id):
        if user_id:
            data = []
            is_hr_manager = request.env.user.has_group('hr.group_hr_manager')
            is_hr_user = request.env.user.has_group('hr.group_hr_user')
            data.append({
                'is_hr_user': is_hr_user,
                'is_hr_manager': is_hr_manager,
            })
            return data
        else:
            return False

    @http.route('/orgchart/getdata', type="json", auth="user")
    def get_orgchart_data(self, company_id):
        company = request.env['res.company'].sudo().browse(int(company_id))
        if not company.exists():
            return {'data': {}}

        data = {
            'id': -company.id,  # Negative to differentiate from employees
            'name': company.name,
            'title': company.country_id.name or '',
            '_name': company._name,
        }

        employees = request.env['hr.employee'].sudo().search([
            ('parent_id', '=', False),
            ('company_id', '=', company.id)
        ])

        children = []
        for employee in employees:
            employee_data = self.get_reportees(employee, company)
            if employee_data:
                children.append(employee_data)

        if children:
            data['children'] = children

        return {'data': data}

    def get_reportees(self, employee, company):
        employee_env = request.env['hr.employee'].sudo()

        data = {
            'id': employee.id,
            'name': employee.name,
            'title': employee.job_id.name,
            '_name': employee._name,
        }

        children = []
        direct_reportees = employee_env.search([
            ('parent_id', '=', employee.id),
            ('company_id', '=', company.id)
        ])

        for reportee in direct_reportees:
            reportee_data = self.get_reportees(reportee, company)
            if reportee_data:
                children.append(reportee_data)

        if children:
            data['children'] = children

        return data
    
    @http.route('/orgchart/update', type='json', auth="user")
    def update_org_chart(self, source_id, target_id):
        if source_id and target_id:
            source = request.env['hr.employee'].search([('id','=',int(source_id))], limit=1)
            target = request.env['hr.employee'].search([('id','=',int(target_id))], limit=1)
            if source and target:
                source.sudo().write({
                    'parent_id' : target.id,
                })
                return True
            else:
                return False
        else:
            return False