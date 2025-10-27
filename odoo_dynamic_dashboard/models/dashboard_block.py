# -*- coding: utf-8 -*-
##############################################################################
#
#    In2IT Technologies Pvt. Ltd
#    Copyright (C) 2025 (https://www.in2ittech.com)
#
##############################################################################
from ast import literal_eval
from odoo import api, fields, models
from odoo.osv import expression
from dateutil.parser import parse  


class DashboardBlock(models.Model):
    """Class is used to create charts and tiles in dashboard"""
    _name = "dashboard.block"
    _description = "Dashboard Block"

    def get_default_action(self):
        """Function to get values from dashboard if action_id is true return
        id else return false"""
        action_id = self.env.ref(
            'odoo_dynamic_dashboard.dashboard_view_action')
        if action_id:
            return action_id.id
        return False

    name = fields.Char(string="Name", help='Name of the block')
    fa_icon = fields.Char(string="Icon", help="Add icon for tile")
    operation = fields.Selection(
        selection=[("sum", "Sum"), ("avg", "Average"), ("count", "Count")],
        string="Operation",
        help='Tile Operation that needs to bring values for tile',
    )
    graph_type = fields.Selection(
        selection=[("bar", "Bar"), ("radar", "Radar"), ("pie", "Pie"),
                   ("polarArea", "polarArea"), ("line", "Line"),
                   ("doughnut", "Doughnut")],
        string="Chart Type", help='Type of Chart')
    measured_field_id = fields.Many2one("ir.model.fields",
                                        string="Measured Field",
                                        help="Select the Measured")
    client_action_id = fields.Many2one('ir.actions.client',
                                       string="Client action",
                                       default=get_default_action,
                                       help="Client action")
    type = fields.Selection(
        selection=[("graph", "Chart"), ("tile", "Tile")],
        string="Type", help='Type of Block ie, Chart or Tile')
    x_axis = fields.Char(string="X-Axis", help="Chart X-axis")
    y_axis = fields.Char(string="Y-Axis", help="Chart Y-axis")
    height = fields.Char(string="Height ", help="Height of the block")
    width = fields.Char(string="Width", help="Width of the block")
    translate_x = fields.Char(string="Translate_X",
                              help="x value for the style transform translate")
    translate_y = fields.Char(string="Translate_Y",
                              help="y value for the style transform translate")
    data_x = fields.Char(string="Data_X", help="Data x value for resize")
    data_y = fields.Char(string="Data_Y", help="Data y value for resize")
    group_by_id = fields.Many2one("ir.model.fields", store=True,
                                  string="Group by(Y-Axis)",
                                  help='Field value for Y-Axis')
    tile_color = fields.Char(string="Tile Color", help='Primary Color of Tile')
    text_color = fields.Char(string="Text Color", help='Text Color of Tile')
    val_color = fields.Char(string="Value Color", help='Value Color of Tile')
    fa_color = fields.Char(string="Icon Color", help='Icon Color of Tile')
    filter = fields.Char(string="Filter", help="Add filter")
    model_id = fields.Many2one('ir.model', string='Model',
                               help="Select the module name")
    model_name = fields.Char(related='model_id.model', string="Model Name",
                             help="Added model_id model")
    kpi_id = fields.Many2one("dashboard.kpi",string="Select KPI")    
    
    measureable_function_id = fields.Many2one('kpi.functions',string="Measureable Function",compute='_compute_measured_id', store=True)
    edit_mode = fields.Boolean(string="Edit Mode",
                               help="Enable to edit chart and tile",
                               default=False, invisible=True)
    show = fields.Boolean('Show',default=False)


    def get_action_id(self):
        action = self.env.ref('odoo_dynamic_dashboard.dashboard_view_action',raise_if_not_found=False)
        if action:
            return action.id
        return False
    
    def get_pop_up_tree_view_id (self):
        action = self.env.ref('odoo_dynamic_dashboard.dashboard_block_view_tree_modal_popup',raise_if_not_found=False)
        if action:
            return action.id
        return False
    
    def get_current_action_kpis(self, action_id):
            dashboard_block = self.env['dashboard.block'].sudo().search_read(
                domain=[('client_action_id', '=', int(action_id))],
                fields=['id','name', 'type']
            )
            return [{'id':block['id'] ,'name': block['name'], 'type': block['type']} for block in dashboard_block]

        
    def make_active_current_kpi(self,kpi_id):
        dashboard_block = self.browse(kpi_id)
        dashboard_block.sudo().write({'show': True})

    def make_kpi_inactive(self,kpi_id):
        dashboard_block = self.browse(kpi_id)
        dashboard_block.sudo().write({'show': False,'data_x':'','data_y':'','translate_x':'','translate_y':''})

    @api.depends('kpi_id')
    def _compute_measured_id(self):
        for rec in self:
            rec.measureable_function_id = rec.kpi_id.measureable_function_id.id if rec.kpi_id else False


    @api.onchange('model_id')
    def _onchange_model_id(self):
        if self.operation or self.measured_field_id:
            self.operation = False
            self.measured_field_id = False

    def set_dashboard_vals(self,block_id,translate_x):
        block = self.env['dashboard.block'].sudo().search(
                [('id', '=', int(block_id))])
        block.sudo().write({
            'translate_x':translate_x
        })


    def get_dashboard_vals(self, action_id, start_date=None, end_date=None):
        """Fetch block values from js and create chart"""
        block_id = []
        for rec in self.env['dashboard.block'].sudo().search(
                [('client_action_id', '=', int(action_id)),('show','=',True)],order='write_date asc'):
            if rec.filter is False:
                rec.filter = "[]"
            filter_list = literal_eval(rec.filter)
            filter_list = [filter_item for filter_item in filter_list if not (
                    isinstance(filter_item, tuple) and filter_item[
                0] == 'create_date')]
            rec.filter = repr(filter_list)
            vals = {'id': rec.id, 'name': rec.name, 'type': rec.type,
                    'graph_type': rec.graph_type, 'icon': rec.fa_icon,
                    'model_name': rec.model_name,
                    'color': f'background-color: {rec.tile_color};' if rec.tile_color else '#1f6abb;',
                    'text_color': f'color: {rec.text_color};' if rec.text_color else '#FFFFFF;',
                    'val_color': f'color: {rec.val_color};' if rec.val_color else '#FFFFFF;',
                    'icon_color': f'color: {rec.tile_color};' if rec.tile_color else '#1f6abb;',
                    'height': rec.height,
                    'width': rec.width,
                    'translate_x': rec.translate_x,
                    'translate_y': rec.translate_y,
                    'data_x': rec.data_x,
                    'data_y': rec.data_y,
                    'domain': filter_list,
                    'is_officer':True if self.env.user.has_group('odoo_dynamic_dashboard.group_dashboard_officer') else False
                    }
            domain = []
            if rec.filter:
                domain = expression.AND([literal_eval(rec.filter)])

            date_domain = []
            if start_date and start_date != "null":
                date_domain.append(('create_date', '>=', start_date))
            if end_date and end_date != "null":
                date_domain.append(('create_date', '<=', end_date))

            if date_domain:
                domain = expression.AND([domain, date_domain])
            
            
            if rec.type == 'graph':
                
                method_name = rec.measureable_function_id.name
                method = getattr(rec, method_name, None)

                if method and callable(method):
                    records = method('graph',domain)  
                else:
                    raise ValueError(f"Method {method_name} not found or not callable.")

                x_axis = []
                y_axis = []
                for rec in records:
                    x_axis.append(rec.get('name'))
                    y_axis.append(rec.get('value'))
                
                vals.update({'x_axis': x_axis, 'y_axis': y_axis})
            else:
            
                method_name = rec.measureable_function_id.name
                method = getattr(rec, method_name, None)

                if method and callable(method):
                    value = method('tile',domain)  
                else:
                    raise ValueError(f"Method {method_name} not found or not callable.")

                
                vals.update({'value':value})
            block_id.append(vals)
        return block_id

    def get_save_layout(self, grid_data_list):
        """Function fetch edited values while edit layout of the chart or tile
         and save values in a database"""
        for data in grid_data_list:
            block = self.browse(int(data['id']))
            if data.get('data-x'):
                block.sudo().write({
                    'translate_x': f"{data['top']}",
                    'translate_y': f"{data['left']}",
                    'data_x': data['data-x'],
                    'data_y': data['data-y'],
                })
            if data.get('height'):
                block.sudo().write({
                    'height': f"{data['height']}px",
                    'width': f"{data['width']}px",
                })
        return True

   


    def get_job_positions_by_recruiter(self, type, domain):
        # Ensure user_id is not null
        domain = expression.AND([domain, [('user_id', '!=', False)]])
        # results = self.env['hr.job'].read_group(
        #     domain,
        #     fields=['user_id'],
        #     groupby=['user_id'],
        #     lazy=False,
        # )

        # data = []
        # total_job_assigned_to_recruiter = 0

        # for res in results:
        #     user = self.env['res.users'].browse(res['user_id'][0]) if res['user_id'] else None
        #     job_count = res['__count']
        #     data.append({
        #         'name': user.name if user else 'Unknown',
        #         'value': job_count,
        #     })
        #     total_job_assigned_to_recruiter += job_count

        if type == "graph":
            return []
        else:
            return 34

        
    def get_active_job_positions(self,type,domain):
        domain = expression.AND([domain, [('position_status', '=', 'hiring')]])
        jobs = self.env['hr.job'].sudo().search(domain)
        data = []
        total_active_job_position = 0
        for job in jobs:
            data.append({'id': job.id, 'name': job.name,'value':job.no_of_recruitment})
            total_active_job_position += job.no_of_recruitment
        if type == "graph":
            return data
        else:
            return total_active_job_position
        
    def get_applications_per_job(self,type,domain):
        domain = expression.AND([domain, [('position_status', '=', 'hiring')]])
        jobs = self.env['hr.job'].sudo().search(domain)
        if type == "graph":
            return [{'id': job.id, 'name': job.name,'value':job.all_application_count} for job in jobs]
        else:
            total_applicant_count = 0
            for job in jobs:
                total_applicant_count += job.all_application_count
            return total_applicant_count
        


    def get_applicant_per_stage(self, type, domain):
        domain = expression.AND([domain, [('stage_id', '!=', False)]])

        results = self.env['hr.applicant'].read_group(
            domain=domain,
            fields=['stage_id'],
            groupby=['stage_id'],
            lazy=False
        )

        data = []
        total_applicant_on_stages = 0
        for res in results:
            stage_name = res['stage_id'][1] if res['stage_id'] else 'Unknown'
            applicant_count = res['__count']
            data.append({
                'name': stage_name,
                'value': applicant_count,
            })
            total_applicant_on_stages += applicant_count
        if type=="graph":
            return data
        return total_applicant_on_stages
    
    
    def get_average_number_of_days_from_posting_to_acceptance(self,type,domain):
        # total number of days = (jobpostingdate - when it is moved to hired stage).days 
        #total number of days taken by all the applicant per job/total_no_of_applicants which is on hired stage per job
        domain = expression.AND([domain,[('stage_id', '!=', False)]])

        results = self.env['hr.applicant'].search(domain)
        hired_stage = self.env['approval.cycle.stage'].search_read([('hired_stage','=',True)],['id','name'],limit=1)

        data = {}
        hired_applicant = {}
        for res in results:
            job_posting_date = res.job_id.create_date
            if res.job_id.name in data:
                # data[res.job_id.name] = 0
                total_no_of_days = data[res.job_id.name]
            else:
                total_no_of_days = 0
            
            if f'{res.job_id.name}_count' not in hired_applicant:
                hired_applicant[f'{res.job_id.name}_count'] = 0

            if hired_stage:
                hired_stage_id = hired_stage[0]['id']
                applicant = self.env['approval.cycle'].search([('applicant_id','=',res.id),('job_id','=',res.job_id.id),('stage_id','=',hired_stage_id)],limit=1)
                messages = applicant.message_ids.filtered(lambda m: m.tracking_value_ids)
                for msg in messages:
                    for tracking in msg.tracking_value_ids:
                        if tracking.field_id.name == 'stage_id' and tracking.new_value_char == hired_stage[0]['name']:
                            number_of_days = (msg.date.date() - job_posting_date.date()).days
                            total_no_of_days += number_of_days
                            data[res.job_id.name] = total_no_of_days
                            hired_applicant[f'{res.job_id.name}_count'] += 1
        data_items = []
        for key,value in data.items():
            data_items.append({'name':key,'value': "{:.2f}".format(value / hired_applicant[f'{key}_count']) if hired_applicant[f'{key}_count']>0 else "0.00"})

        if type=="graph":
            return data_items
        values = 0
        for items in data_items:
            values += float(items['value'])

        return round(values/len(data),2) if len(data)>0 else 0

    def get_average_number_of_days_taken__to_screen(self,type,domain):
        domain = expression.AND([domain,[('stage_id', '!=', False)]])

        results = self.env['hr.applicant'].search(domain)
        data = {}
        interview_applicant = {}
        screen_stage = self.env['hr.recruitment.stage'].search([('name', 'ilike', 'Screening')], limit=1)
        next_stage = self.env['hr.recruitment.stage'].search([('sequence', '=', screen_stage.sequence + 1)], limit=1)
        for res in results:
            applicant_create_date = res.create_date
            if res.job_id.name in data:
                # data[res.job_id.name] = 0
                total_no_of_days = data[res.job_id.name]
            else:
                total_no_of_days = 0
            
            if f'{res.job_id.name}_count' not in interview_applicant:
                interview_applicant[f'{res.job_id.name}_count'] = 0

            messages = res.message_ids.filtered(lambda m: m.tracking_value_ids)
            for msg in messages:
                for tracking in msg.tracking_value_ids:
                    if tracking.field_id.name == 'stage_id' and tracking.new_value_char == next_stage.name if next_stage else 'First Interview':
                        number_of_days = (msg.date.date() - applicant_create_date.date()).days
                        total_no_of_days += number_of_days
                        data[res.job_id.name] = total_no_of_days
                        interview_applicant[f'{res.job_id.name}_count'] += 1
        data_items = []
        for key,value in data.items():
            data_items.append({'name':key,'value': "{:.2f}".format(value / interview_applicant[f'{key}_count']) if interview_applicant[f'{key}_count']>0 else "0.00" })

        if type=="graph":
            return data_items
        values = 0
        for items in data_items:
            values += float(items['value'])
        return round(values/len(data),2) if len(data)>0 else 0
    

    def get_interview_velocity(self,type,domain):
        domain = expression.AND([domain,[('stage_id', '!=', False)]])
        date_filters = [d for d in domain if (
            isinstance(d, (list, tuple)) and d[0] == 'create_date' and d[1] in ('>=', '<=')
        )]
        if len(date_filters) < 2:
            week = 4
        else:
            date_ge = None
            date_le = None
            for f in date_filters:
                operator = f[1]
                date_val = f[2]
                if isinstance(date_val, str):
                    date_val = parse(date_val).date()
                elif hasattr(date_val, 'date'): 
                    date_val = date_val.date()
                
                if operator == '>=':
                    date_ge = date_val
                elif operator == '<=':
                    date_le = date_val

            if date_ge and date_le:
                diff_days = (date_le - date_ge).days

                diff_weeks = diff_days // 7


                if diff_weeks < 1:
                    week = 4
                else:
                    week = diff_weeks

        results = self.env['hr.applicant'].search(domain)
        data = {}
        total_interview_count = 0 
        for res in results:
            if res.job_id.name in data:
                total_interview_count = data[res.job_id.name]
            else:
                total_interview_count = 0

            interview_count = self.env['calendar.event'].search_count([('applicant_id','=',res.id),('applicant_stage_id','!=',False)])
            total_interview_count += interview_count
            data[res.job_id.name] = total_interview_count
        
        data_items = []
        values = 0
        for key,value in data.items():
            data_items.append({'name':key,'value': "{:.2f}".format(value / week)})
            values += value

        if type=="graph":
            return data_items
        
        return round(values/week,2)
        


class DashboarKPI(models.Model):
    _name = 'dashboard.kpi'
    _description = 'Dashboard kPI'

    name = fields.Char("Name")
    description = fields.Text(string="Description")
    measureable_function_id = fields.Many2one('kpi.functions',string="Measureable Function")

class KpiFunctions(models.Model):
    _name = "kpi.functions"
    _description = "KPI Functions"

    name = fields.Char("Name")
