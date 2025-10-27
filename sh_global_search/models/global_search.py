# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
import logging
from odoo import fields, models, api, _
from odoo.tools import html2plaintext
from odoo.osv import expression
from odoo.exceptions import UserError

FIELD_TYPES = [(key, key) for key in sorted(fields.Field.by_type)]
_logger = logging.getLogger(__name__)

class ResCompany(models.Model):
    "In-herite company"
    _inherit = 'res.company'
    enable_menu_search = fields.Boolean(
        "Enable Menu Global Search", default=True)
    start_search_after_letter = fields.Integer(
        "Search Start After Letter", default=0)


class ResConfigSettings(models.TransientModel):
    "inherite setting for add configuration"
    _inherit = 'res.config.settings'

    enable_menu_search = fields.Boolean(
        related="company_id.enable_menu_search",
        string="Enable Menu Global Search", readonly=False)
    start_search_after_letter = fields.Integer(
        related="company_id.start_search_after_letter",
        string="Search Start After Letter", readonly=False)


class GlobalSearch(models.Model):
    _name = 'global.search'
    _description = 'Global search'
    _rec_name = 'model_id'

    model_id = fields.Many2one('ir.model', string='Applies To',
                               required=True, index=True, ondelete='cascade',
                               help="The model this field belongs to")

    field_ids = fields.Many2many(
        'ir.model.fields', string='Fields', domain="[('model_id','=',model_id)]")
    main_field_id = fields.Many2one('ir.model.fields', string="Name Field",
                                    required=True, domain="[('model_id','=',model_id)]",
                                    ondelete='cascade')
    global_field_ids = fields.One2many(
        'global.search.fields', 'global_search_id', string='Fields ')

    @api.model
    def get_search_result(self, query):
        search_result = {}
        if self.env.user.company_id.enable_menu_search:
            menu_roots = self.env['ir.ui.menu'].search(
                [('parent_id', '=', False)])
            menu_data = self.env['ir.ui.menu'].search(
                [('id', 'child_of', menu_roots.ids), ('action', '!=', False)])
            if menu_data:
                menu_data = menu_data._filter_visible_menus()
                for menu in menu_data:
                    if query[0].lower() in menu.complete_name.lower():
                        search_result['menu| ' + menu.complete_name] = {
                            'id': menu.id, 'action': menu.action.id, 'name': menu.complete_name}

        # if company id field is not in model
        for search_rec in self.env['global.search'].sudo().search([]):

            # All Field List including name field
            normal_fields_list = []
            m2o_fields_list = []
            o2m_fields_list = []
            for fields in search_rec.global_field_ids:
                field = fields.field_id
                if field.ttype in ['char', 'boolean', 'text', 'date',
                                   'datetime', 'float', 'integer', 'selection',
                                   'monetary', 'html']:
                    normal_fields_list.append(field)
                elif field.ttype in ['many2one']:
                    if search_rec.main_field_id not in m2o_fields_list:
                        m2o_fields_list.append(search_rec.main_field_id)
                    m2o_fields_list.append(field)
                elif field.ttype in ['one2many']:
                    o2m_fields_list.append(field)

            # Fetch all record of this current model with defined field list
            try:
                # check company_id field in model
                company_id_field = self.env['ir.model.fields'].sudo().search(
                    [('name', '=', 'company_id'), ('model_id', '=', search_rec.model_id.id)])
                if not company_id_field:
                    if normal_fields_list:
                        normal_fields = []
                        domain = []
                        count = 0
                        for field_row in normal_fields_list:
                            field = field_row.name
                            normal_fields.append(field)
                            if field != 'display_name':
                                domain.append((field, 'ilike', query[0]))
                            else:
                                count += 1
                        if normal_fields:
                            model_obj = self.env[search_rec.model_id.model].search_read(
                                domain, normal_fields, order='id')
                            for model_rec in model_obj:
                                for field_row in normal_fields_list:
                                    field = field_row
                                    if model_rec.get(field.name):
                                        object_data = model_rec.get(field.name)

                                        if (object_data and
                                                query[0].lower() in str(object_data).casefold()):
                                            model_rec['model'] = field.model_id.model
                                            model_rec['model_name'] = field.model_id.name
                                            search_result_record = model_rec.get(
                                                search_rec.main_field_id.name) or ''
                                            search_result[
                                                self.env.user.company_id.name + '|' +
                                                search_result_record + ' > ' +
                                                field.field_description + ' : ' +
                                                str(object_data)] = model_rec

                        if count != 0:
                            field_list = ['display_name']
                            model_obj = self.env[search_rec.model_id.model].search_read(
                                [], field_list, order='id')
                            for model_rec in model_obj:
                                if model_rec.get('display_name'):
                                    object_data = model_rec.get('display_name')
                                    if (object_data and
                                            query[0].lower() in str(object_data).casefold()):
                                        model_rec['model'] = search_rec.model_id.model
                                        model_rec['model_name'] = search_rec.model_id.name
                                        search_result[
                                            self.env.user.company_id.name +
                                            '|' + "Display Name" +
                                            ' : ' + str(object_data)] = model_rec
                    if m2o_fields_list:
                        m2o_fields = []
                        domain = []
                        for field_row in m2o_fields_list:
                            field = field_row.name
                            m2o_fields.append(field)
                            domain.append(
                                (f"{field}.name", 'ilike', query[0]))
                        model_obj = self.env[search_rec.model_id.model].search_read(
                            domain, m2o_fields, order='id')
                        for model_rec in model_obj:
                            for field_row in m2o_fields_list:
                                field = field_row
                                if field.name != 'display_name':
                                    if model_rec.get(field.name):
                                        object_data = model_rec.get(field.name)

                                        if (object_data and
                                                query[0].lower() in str(object_data).casefold()):
                                            model_rec['model'] = field.model_id.model
                                            model_rec['model_name'] = field.model_id.name
                                            search_result_record = model_rec.get(
                                                search_rec.main_field_id.name) or ''

                                            str_object_data = str(
                                                object_data[1])
                                            search_result[
                                                self.env.user.company_id.name + '|' +
                                                search_result_record + ' > ' +
                                                field.field_description + ' : ' +
                                                str_object_data] = model_rec
                    if o2m_fields_list:
                        for super_field_row in o2m_fields_list:
                            field = super_field_row.field_id.name
                            inside_normal_fields = []
                            inside_m2o_field_list = []
                            for o2m_field in super_field_row.field_ids:
                                field = o2m_field.field_id
                                if field.ttype in ['char', 'boolean', 'text', 'date', 'datetime',
                                                   'float', 'integer','selection', 'monetary',
                                                   'html']:
                                    inside_normal_fields.append(field)
                                elif field.ttype in ['many2one']:
                                    inside_m2o_field_list.append(field)
                                    if search_rec.main_field_id not in inside_m2o_field_list:
                                        inside_m2o_field_list.append(
                                            search_rec.main_field_id)
                                if search_rec.main_field_id not in inside_normal_fields:
                                    inside_normal_fields.append(
                                        search_rec.main_field_id)
                        if inside_normal_fields:
                            normal_fields = []
                            domain = []
                            for field_row in inside_normal_fields:
                                field = field_row.name
                                normal_fields.append(field)
                                domain.append((field, 'ilike', query[0]))
                            model_obj = self.env[search_rec.model_id.model].search_read(
                                domain, normal_fields, order='id')
                            for model_rec in model_obj:
                                for field_row in inside_normal_fields:
                                    field = field_row
                                    if model_rec.get(field.name):
                                        object_data = model_rec.get(field.name)
                                        if field.ttype == 'html':
                                            object_data = html2plaintext(
                                                object_data)

                                        if (object_data and
                                                query[0].lower() in str(object_data).casefold()):
                                            some_id = model_rec['id']
                                            some_record = (
                                                self.env[super_field_row.model_id.model].browse(
                                                some_id))
                                            search_result_record = model_rec.get(
                                                search_rec.main_field_id.name) or ''
                                            parent_obj = getattr(
                                                some_record,
                                                super_field_row.field_id.relation_field)
                                            model_rec['model'] = parent_obj._name
                                            model_rec['model_name'] = parent_obj._name.upper(
                                            )
                                            model_rec['id'] = parent_obj.id
                                            str_object_data = str(
                                                object_data)
                                            search_result[
                                                self.env.user.company_id.name + '|' +
                                                parent_obj.name + ' > ' +
                                                field.field_description + ' : ' +
                                                str_object_data] = model_rec
                        if inside_m2o_field_list:
                            m2o_fields = []
                            domain = []
                            for field_row in inside_m2o_field_list:
                                field = field_row.name
                                m2o_fields.append(field)
                                domain.append(
                                    (f"{field}.name", 'ilike', query[0]))
                            model_obj = self.env[search_rec.model_id.model].search_read(
                                domain, m2o_fields, order='id')
                            for model_rec in model_obj:
                                for field_row in inside_m2o_field_list:
                                    field = field_row
                                    if field.name != 'display_name':
                                        if model_rec.get(field.name):
                                            object_data = model_rec.get(
                                                field.name)
                                            if field.ttype == 'html':
                                                object_data = html2plaintext(
                                                    object_data)

                                            if (object_data and
                                                    query[0].lower() in str(object_data).casefold()):
                                                some_id = model_rec['id']
                                                some_record = self.env[super_field_row.model_id.model].browse(
                                                    some_id)
                                                search_result_record = model_rec.get(
                                                    search_rec.main_field_id.name) or ''
                                                parent_obj = getattr(
                                                    some_record,
                                                    super_field_row.field_id.relation_field)
                                                model_rec['model'] = parent_obj._name
                                                model_rec['model_name'] = parent_obj._name.upper(
                                                )
                                                model_rec['id'] = parent_obj.id
                                                str_object_data = str(
                                                    object_data[1])
                                                search_result[
                                                    self.env.user.company_id.name + '|' +
                                                    parent_obj.name + ' > ' +
                                                    field.field_description + ' : ' +
                                                    str_object_data] = model_rec

            except Exception as e:
                print(e)

        # if company id field is in model
        # All Global Search Records
        count = 1
        for company in self.env['res.company'].search([]):
            # in self.env.context.get('allowed_company_ids')
            if company.id:
                for search_rec in self.env['global.search'].sudo().search([]):
                    # All Field List including name field
                    field_list = []
                    for field in search_rec.global_field_ids:
                        field_list.append(field.field_id.name)
                    if search_rec.main_field_id.name not in field_list:
                        field_list.append(search_rec.main_field_id.name)
                    normal_fields_list = []
                    m2o_fields_list = []
                    o2m_fields_list = []
                    external_addition = 0
                    for fields in search_rec.global_field_ids:
                        field = fields.field_id
                        if field.ttype in ['char', 'boolean', 'text', 'date', 'datetime', 'float',
                                           'integer','selection', 'monetary', 'html']:
                            normal_fields_list.append(field)
                        elif field.ttype in ['many2one']:
                            m2o_fields_list.append(field)
                        elif field.ttype in ['one2many']:
                            o2m_fields_list.append(fields)
                    if search_rec.main_field_id not in m2o_fields_list:
                        m2o_fields_list.append(search_rec.main_field_id)
                    if search_rec.main_field_id not in normal_fields_list:
                        external_addition += 1
                        normal_fields_list.append(search_rec.main_field_id)
                    try:
                        # check company_id field in model
                        company_id_field = self.env['ir.model.fields'].sudo().search(
                            [('name', '=', 'company_id'),
                             ('model_id', '=', search_rec.model_id.id)])

                        if company_id_field:
                            if normal_fields_list:
                                normal_fields = [
                                    field_row.name for field_row in normal_fields_list]
                                domain = []
                                domain_multi_company = [
                                    ('company_id', 'in', [company.id, False])]
                                field_domain = expression.OR(
                                    [[(field_row.name, 'ilike', query[0])
                                      ] for field_row in normal_fields_list if
                                     field_row.name != 'display_name'])
                                domain = expression.AND(
                                    [domain_multi_company, field_domain])
                                if normal_fields:
                                    model_obj = self.env[search_rec.model_id.model].search_read(
                                        domain, normal_fields, order='id')
                                    for model_rec in model_obj:
                                        for field_row in normal_fields_list:
                                            field = field_row
                                            if field.name != 'display_name':
                                                if model_rec.get(field.name):
                                                    object_data = model_rec.get(
                                                        field.name)
                                                    if field.ttype == 'html':
                                                        object_data = html2plaintext(
                                                            object_data)
                                                    if (object_data or
                                                            query[0].lower() in str(object_data).casefold()):
                                                        model_rec['model'] = field.model_id.model
                                                        model_rec['model_name'] = field.model_id.name
                                                        search_result_record = model_rec.get(
                                                            search_rec.main_field_id.name) or ''

                                                        search_result_record = html2plaintext(
                                                            search_result_record)

                                                        search_result[
                                                            self.env.user.company_id.name + '|' +
                                                            search_result_record + ' > ' +
                                                            field.field_description + ' : ' + str(
                                                                object_data)] = model_rec

                                if external_addition == 0:
                                    field_list = ['display_name']
                                    model_obj = self.env[search_rec.model_id.model].search_read(
                                        ['|', ('company_id', '=', company.id),
                                         ('company_id', '=', False)], field_list,
                                        order='id')
                                    for model_rec in model_obj:
                                        if model_rec.get('display_name'):
                                            object_data = model_rec.get(
                                                'display_name')
                                            if (object_data and
                                                    query[0].lower() in str(object_data).casefold()):
                                                model_rec['model'] = search_rec.model_id.model
                                                model_rec['model_name'] = search_rec.model_id.name
                                                search_result[company.name + '|' +
                                                              "Display Name" + ' : ' + str(
                                                    object_data)] = model_rec
                            if m2o_fields_list:
                                m2o_fields = [
                                    field_row.name for field_row in m2o_fields_list]

                                domain = []
                                domain_multi_company = [
                                    ('company_id', 'in', [company.id, False])]
                                search_fields_domain = []

                                for field_row in m2o_fields_list:
                                    if field_row.name != 'display_name':
                                        try:
                                            related_model = self.env[field_row.relation]
                                            if 'name' in related_model._fields:
                                                search_fields_domain.append(
                                                    (f"{field_row.name}.name", 'ilike', query[0]))
                                        except KeyError:
                                            # If the relation is invalid or not accessible, skip it
                                            continue

                                field_domain = expression.OR([
                                    [(f"{field_row.name}.name", 'ilike', query[0])]
                                    for field_row in m2o_fields_list
                                    if field_row.name != 'display_name'])
                                domain = expression.AND(
                                    [domain_multi_company, field_domain])
                                model_obj = self.env[search_rec.model_id.model].search_read(
                                    domain, m2o_fields, order='id')
                                for model_rec in model_obj:
                                    for field_row in m2o_fields_list:
                                        field = field_row
                                        if field.name != 'display_name':
                                            if model_rec.get(field.name):
                                                object_data = model_rec.get(
                                                    field.name)

                                                if object_data:
                                                    model_rec['model'] = field.model_id.model
                                                    model_rec['model_name'] = field.model_id.name
                                                    search_result_record = model_rec.get(
                                                        search_rec.main_field_id.name) or ''
                                                    search_result_record = search_result_record

                                                    if isinstance(search_result_record, tuple):
                                                        search_result_record = object_data[1]
                                                    if isinstance(object_data, tuple):
                                                        object_data = object_data[1]
                                                    search_result[company.name + '|' +
                                                                  search_result_record + ' > ' +
                                                                  field.field_description + ' : ' +
                                                                  object_data] = model_rec

                            if o2m_fields_list:
                                for super_field_row in o2m_fields_list:
                                    field = super_field_row.field_id.name
                                    inside_normal_fields = []
                                    inside_m2o_field_list = []
                                    for o2m_field in super_field_row.field_ids:
                                        field = o2m_field.field_id
                                        if field.ttype in ['char', 'boolean', 'text', 'date',
                                                           'datetime', 'float','integer',
                                                           'selection', 'monetary', 'html']:
                                            inside_normal_fields.append(field)
                                        elif field.ttype in ['many2one']:
                                            if (search_rec.main_field_id not in
                                                    inside_m2o_field_list):
                                                inside_m2o_field_list.append(
                                                    search_rec.main_field_id)
                                            inside_m2o_field_list.append(field)
                                        if search_rec.main_field_id not in inside_normal_fields:
                                            inside_normal_fields.append(
                                                search_rec.main_field_id)
                                    if inside_normal_fields:
                                        normal_fields = [
                                            field_row.name for field_row in inside_normal_fields]
                                        domain = []
                                        domain_multi_company = []
                                        field_domain = expression.OR(
                                            [[(field_row.name, 'ilike', query[0])
                                              ] for field_row in inside_normal_fields
                                             if field_row.name != 'display_name'])
                                        domain = expression.AND(
                                            [domain_multi_company, field_domain])
                                        model_obj = self.env[super_field_row.related_model_id].search_read(
                                            domain, normal_fields, order='id')
                                        for model_rec in model_obj:
                                            for field_row in inside_normal_fields:
                                                field = field_row
                                                if model_rec.get(field.name):

                                                    object_data = model_rec.get(
                                                        field.name)
                                                    if field.ttype == 'html':
                                                        object_data = html2plaintext(
                                                            object_data)

                                                    if object_data and query[0].lower() in str(object_data).casefold():
                                                        some_id = model_rec['id']
                                                        some_record = self.env[super_field_row.model_id.model].browse(
                                                            some_id)
                                                        search_result_record = model_rec.get(
                                                            search_rec.main_field_id.name) or ''

                                                        # Get the raw value from the field (could be an int, recordset, etc.)
                                                        related_value = getattr(some_record,
                                                                                super_field_row.field_id.relation_field)

                                                        # If the field is a Many2one-like relation but only returns an integer, fetch the related record manually
                                                        if isinstance(related_value, int):
                                                            relation_model = self.env[super_field_row.field_id.relation]
                                                            parent_obj = relation_model.browse(related_value)
                                                        else:
                                                            parent_obj = related_value

                                                        # Assign resolved model and ID to result dict
                                                        model_rec[
                                                            'model'] = super_field_row.field_id.model  # parent_obj._name
                                                        model_rec[
                                                            'model_name'] = super_field_row.field_id.model.upper()  # parent_obj._name.upper()
                                                        model_rec['id'] = parent_obj.id

                                                        str_object_data = str(object_data)
                                                        search_result_record = model_rec.get(
                                                            search_rec.main_field_id.name) or ''
                                                        search_result[
                                                            company.name + '|' +
                                                            search_result_record + ' > ' +
                                                            field.field_description + ' : ' +
                                                            str_object_data
                                                            ] = model_rec

                                    if inside_m2o_field_list:
                                        m2o_fields = [
                                            field_row.name for field_row in inside_m2o_field_list]
                                        domain = []
                                        domain_multi_company = [
                                            ('company_id', 'in', [company.id, False])]
                                        if len(m2o_fields) > 1:
                                            field_domain = expression.OR([[
                                                (f"{field_row.name}.name", 'ilike', query[0])
                                                        ] for field_row in inside_m2o_field_list if
                                                            field_row.name != 'display_name'])
                                        else:
                                            field_domain = (
                                                [(f"{field_row.name}.name", 'ilike', query[0])] for field_row in
                                                m2o_fields)
                                        domain = expression.AND(
                                            [domain_multi_company, field_domain])
                                        model_obj = self.env[super_field_row.related_model_id].search_read(
                                            domain, m2o_fields, order='id')
                                        for model_rec in model_obj:
                                            for field_row in inside_m2o_field_list:
                                                field = field_row
                                                if field.name != 'display_name':
                                                    if model_rec.get(field.name):
                                                        object_data = model_rec.get(
                                                            field.name)

                                                        if object_data and query[0].lower() in str(
                                                                object_data[1]).casefold():
                                                            some_id = model_rec['id']
                                                            some_record = self.env[
                                                                super_field_row.model_id.model].browse(
                                                                some_id)
                                                            search_result_record = model_rec.get(
                                                                search_rec.main_field_id.name) or ''
                                                            parent_obj = getattr(
                                                                some_record, super_field_row.field_id.relation_field)
                                                            model_rec['model'] = parent_obj._name
                                                            model_rec['model_name'] = parent_obj._name.upper(
                                                            )
                                                            model_rec['id'] = parent_obj.id
                                                            str_object_data = str(
                                                                object_data[1])
                                                            search_result[company.name + '|' +
                                                                          parent_obj.name + ' > ' +
                                                                          field.field_description +
                                                                          ' : ' + str_object_data] = model_rec
                    except Exception as e:
                        _logger.exception(e)

        return search_result


class GlobalSearchFields(models.Model):
    "Custom Global Seach Field"
    _name = 'global.search.fields'
    _description = 'Global search fields'

    global_search_id = fields.Many2one('global.search', string='Related Model')
    sequence = fields.Integer(string='Sequence', default=10)
    field_id = fields.Many2one(
        'ir.model.fields', string='Position Field', ondelete='cascade')
    name = fields.Char("Label", related="field_id.field_description")
    model_id = fields.Many2one('ir.model', string='Model', ondelete='cascade')
    related_model_id = fields.Char(
        string='Relation With', related="field_id.relation")
    ttype = fields.Selection(
        string='Field Type', required=True, related="field_id.ttype")
    field_ids = fields.One2many(
        'o2m.global.search.fields', 'global_o2m_search_id', string='Fields')

    @api.onchange('field_id')
    def _onchange_field_id(self):
        if self.field_id:
            if self.field_id.relation:
                model = self.env['ir.model'].sudo().search(
                    [('model', '=', self.field_id.relation)], limit=1)
                if model:
                    self.model_id = model.id

    def sh_o2m_dynamic_action_action(self):
        if self.ttype == 'one2many':
            view = self.env.ref('sh_global_search.sh_o2m_global_search_form')
            return {
                'name': _('O2M Object Fields'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'global.search.fields',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': self.id,

            }
        else:
            view = self.env.ref('sh_global_search.sh_m2o_global_search_form')
            return {
                'name': _('M2O Object Fields'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'global.search.fields',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': self.id,

            }


class O2MGlobalSearch(models.Model):
    "One2many global search field"
    _name = 'o2m.global.search.fields'
    _description = 'O2m Global search fields'

    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char("Label")
    field_id = fields.Many2one(
        'ir.model.fields', string='Position Field', ondelete='cascade')
    global_o2m_search_id = fields.Many2one(
        'global.search.fields', string='Global O2M Search', ondelete='cascade')
    model_id = fields.Many2one(
        'ir.model', string='Relation With ', ondelete='cascade')
    related_model_id = fields.Char(
        string='Relation With', related="field_id.relation")
    ttype = fields.Selection(
        string='Field Type', required=True, related="field_id.ttype")

    @api.onchange('field_id')
    def _onchange_field_id(self):
        if self.field_id:
            if self.field_id.ttype in ['one2many', 'many2many']:
                raise UserError(
                    "Field type One2many and Many2many not supported inside O2M wizard !")
            self.name = self.field_id.field_description
            if self.field_id.relation:
                model = self.env['ir.model'].sudo().search(
                    [('model', '=', self.field_id.relation)], limit=1)
                if model:
                    self.model_id = model.id
