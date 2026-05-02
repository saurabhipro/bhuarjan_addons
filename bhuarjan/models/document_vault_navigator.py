# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class DocumentVaultNavigator(models.Model):
    _name = 'bhu.document.vault.navigator'
    _description = 'Document Vault Navigator'

    name = fields.Char(string='Name', default='Document Vault Navigator')
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, index=True)
    department_id = fields.Many2one('bhu.department', string='Department / विभाग')
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना')
    village_id = fields.Many2one(
        'bhu.village',
        string='Village / ग्राम',
        domain="[('project_ids', 'in', project_id)]",
    )
    section_line_ids = fields.One2many(
        'bhu.document.vault.navigator.line',
        'navigator_id',
        string='Sections',
        copy=False,
    )
    selected_document_id = fields.Many2one('bhu.document.vault', string='Selected Document')
    selected_attachment_id = fields.Many2one('ir.attachment', string='Selected Attachment')
    selected_source_model = fields.Char(string='Selected Source Model')
    selected_source_record_id = fields.Integer(string='Selected Source Record ID')
    selected_source_file_field = fields.Char(string='Selected Source File Field')
    selected_source_filename_field = fields.Char(string='Selected Source Filename Field')
    selected_document_file = fields.Binary(string='PDF Preview', compute='_compute_selected_preview', readonly=True)
    selected_document_filename = fields.Char(string='Filename', compute='_compute_selected_preview', readonly=True)
    selected_document_hint = fields.Html(
        string='Preview Hint',
        compute='_compute_selected_document_hint',
        sanitize=False,
    )

    @api.depends(
        'selected_document_id',
        'selected_attachment_id',
        'selected_source_model',
        'selected_source_record_id',
        'selected_source_file_field',
        'selected_source_filename_field',
    )
    def _compute_selected_preview(self):
        for rec in self:
            rec.selected_document_file = False
            rec.selected_document_filename = False
            if rec.selected_document_id:
                rec.selected_document_file = rec.selected_document_id.document_file
                rec.selected_document_filename = rec.selected_document_id.document_filename
            elif rec.selected_attachment_id:
                rec.selected_document_file = rec.selected_attachment_id.datas
                rec.selected_document_filename = rec.selected_attachment_id.name
            elif rec.selected_source_model and rec.selected_source_record_id and rec.selected_source_file_field:
                src = self.env[rec.selected_source_model].sudo().browse(rec.selected_source_record_id)
                if src.exists():
                    rec.selected_document_file = src[rec.selected_source_file_field]
                    if rec.selected_source_filename_field:
                        rec.selected_document_filename = src[rec.selected_source_filename_field]
                    if not rec.selected_document_filename:
                        rec.selected_document_filename = '%s_%s.pdf' % (rec.selected_source_model.replace('.', '_'), rec.selected_source_record_id)

    @api.depends('selected_document_id', 'selected_attachment_id', 'selected_source_model', 'selected_source_record_id', 'selected_source_file_field')
    def _compute_selected_document_hint(self):
        for rec in self:
            if rec.selected_document_id or rec.selected_attachment_id or (rec.selected_source_model and rec.selected_source_record_id and rec.selected_source_file_field):
                rec.selected_document_hint = ''
            else:
                rec.selected_document_hint = _(
                    '<div class="o_docvault_empty_hint">'
                    '<h3>Select a section on the left</h3>'
                    '<p>The generated PDF for that section will appear here.</p>'
                    '</div>'
                )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec._apply_default_scope_if_needed()
            rec._refresh_section_lines()
        return records

    def _apply_default_scope_if_needed(self):
        self.ensure_one()
        # Keep department aligned with selected project.
        if self.project_id and self.project_id.department_id:
            self.department_id = self.project_id.department_id.id

        # If project is selected but village is missing, use the first village of that project.
        if self.project_id and not self.village_id and self.project_id.village_ids:
            self.village_id = self.project_id.village_ids[0].id

        # If both are present, scope is ready.
        if self.project_id and self.village_id:
            return

        # Prefer latest Section 23 award scope (primary generated source).
        latest_award = self.env['bhu.section23.award'].search([], order='create_date desc, id desc', limit=1)
        if latest_award and latest_award.project_id and latest_award.village_id:
            self.department_id = latest_award.project_id.department_id.id if latest_award.project_id.department_id else False
            self.project_id = latest_award.project_id.id
            self.village_id = latest_award.village_id.id
            return

        # Secondary fallback: latest manual document-vault row if available.
        latest_doc = self.env['bhu.document.vault'].search([], order='signed_date desc, create_date desc', limit=1)
        if latest_doc and latest_doc.project_id and latest_doc.village_id:
            self.department_id = latest_doc.project_id.department_id.id if latest_doc.project_id.department_id else False
            self.project_id = latest_doc.project_id.id
            self.village_id = latest_doc.village_id.id
            return

        # Fallback to first available project having villages.
        fallback_project = self.env['bhu.project'].search([('village_ids', '!=', False)], order='id asc', limit=1)
        if fallback_project:
            self.department_id = fallback_project.department_id.id if fallback_project.department_id else False
            self.project_id = fallback_project.id
            self.village_id = fallback_project.village_ids[:1].id or False

    @api.onchange('department_id')
    def _onchange_department_id(self):
        self.project_id = False
        self.village_id = False
        self.selected_document_id = False
        self.selected_attachment_id = False
        self.selected_source_model = False
        self.selected_source_record_id = False
        self.selected_source_file_field = False
        self.selected_source_filename_field = False
        self.section_line_ids = [(5, 0, 0)]
        if self.department_id:
            return {'domain': {'project_id': [('department_id', '=', self.department_id.id)], 'village_id': []}}
        return {'domain': {'project_id': [], 'village_id': []}}

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.project_id and self.project_id.department_id:
            self.department_id = self.project_id.department_id.id
        self.village_id = False
        self.selected_document_id = False
        self.selected_attachment_id = False
        self.selected_source_model = False
        self.selected_source_record_id = False
        self.selected_source_file_field = False
        self.selected_source_filename_field = False
        self.section_line_ids = [(5, 0, 0)]
        project_domain = []
        if self.department_id:
            project_domain.append(('department_id', '=', self.department_id.id))
        village_domain = [('id', 'in', self.project_id.village_ids.ids)] if self.project_id and self.project_id.village_ids else []
        return {'domain': {'project_id': project_domain, 'village_id': village_domain}}

    @api.onchange('village_id')
    def _onchange_village_id(self):
        self.selected_document_id = False
        self.selected_attachment_id = False
        self.selected_source_model = False
        self.selected_source_record_id = False
        self.selected_source_file_field = False
        self.selected_source_filename_field = False
        self._refresh_section_lines()

    @api.model
    def action_open_navigator(self):
        navigator = self.search([('user_id', '=', self.env.user.id)], limit=1, order='id desc')
        if not navigator:
            navigator = self.create({'user_id': self.env.user.id})
        else:
            ctx = self.env.context
            if ctx.get('active_project_id'):
                navigator.project_id = ctx.get('active_project_id')
            if ctx.get('active_village_id'):
                navigator.village_id = ctx.get('active_village_id')
            if navigator.project_id and navigator.project_id.department_id:
                navigator.department_id = navigator.project_id.department_id.id
            navigator._apply_default_scope_if_needed()
            navigator._refresh_section_lines()
        return navigator._action_open_self()

    def _action_open_self(self):
        self.ensure_one()
        try:
            view_id = self.env.ref('bhuarjan.view_document_vault_navigator_form').id
        except Exception:
            view_id = False
        return {
            'type': 'ir.actions.act_window',
            'name': _('Document Vault Navigator'),
            'res_model': 'bhu.document.vault.navigator',
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'res_id': self.id,
            'target': 'current',
            'context': {'create': False, 'delete': False},
        }

    def action_refresh_sections(self):
        self.ensure_one()
        self._apply_default_scope_if_needed()
        self._refresh_section_lines()
        return self._action_open_self()

    def action_open_selected_document(self):
        self.ensure_one()
        if self.selected_document_id:
            return self.selected_document_id.action_preview()
        if self.selected_attachment_id:
            return {
                'type': 'ir.actions.act_url',
                'url': '/web/content/%s' % self.selected_attachment_id.id,
                'target': 'new',
            }
        if self.selected_source_model and self.selected_source_record_id and self.selected_source_file_field:
            src = self.env[self.selected_source_model].sudo().browse(self.selected_source_record_id)
            if src.exists() and src[self.selected_source_file_field]:
                filename = src[self.selected_source_filename_field] if self.selected_source_filename_field else 'document.pdf'
                return {
                    'type': 'ir.actions.act_url',
                    'url': '/web/content/%s/%s/%s/%s' % (
                        self.selected_source_model,
                        src.id,
                        self.selected_source_file_field,
                        filename or 'document.pdf',
                    ),
                    'target': 'new',
                }
        return False

    def _get_latest_cached_attachment(self, res_model, res_ids, name_like):
        """Generic cached attachment lookup used by navigator."""
        self.ensure_one()
        if not res_ids:
            return False
        return self.env['ir.attachment'].search([
            ('res_model', '=', res_model),
            ('res_id', 'in', res_ids),
            ('name', 'ilike', name_like),
            ('type', '=', 'binary'),
        ], order='create_date desc, id desc', limit=1)

    def _get_latest_award_cache_attachment(self, scope='all', variant='standard'):
        """Read latest generated award cache (currently Section 23 format)."""
        self.ensure_one()
        awards = self.env['bhu.section23.award'].search([
            ('project_id', '=', self.project_id.id),
            ('village_id', '=', self.village_id.id),
        ], order='create_date desc')
        if not awards:
            return False
        # Keep backward compatibility with existing naming scheme.
        name_like = "S23_CACHE__%s__%s__pdf__" % ((variant or 'standard').lower(), (scope or 'all').lower())
        return self._get_latest_cached_attachment('bhu.section23.award', awards.ids, name_like)

    def _get_latest_payment_attachment(self):
        self.ensure_one()
        payments = self.env['bhu.payment.file'].search([
            ('project_id', '=', self.project_id.id),
            ('village_id', '=', self.village_id.id),
        ], order='generation_date desc, create_date desc')
        if not payments:
            return False
        # Prefer PDF attachment if any external process has uploaded it.
        att = self.env['ir.attachment'].search([
            ('res_model', '=', 'bhu.payment.file'),
            ('res_id', 'in', payments.ids),
            ('mimetype', 'ilike', 'pdf'),
            ('type', '=', 'binary'),
        ], order='create_date desc, id desc', limit=1)
        if att:
            return att
        # Fallback to generated xlsx attachment if present.
        return self.env['ir.attachment'].search([
            ('res_model', '=', 'bhu.payment.file'),
            ('res_id', 'in', payments.ids),
            ('type', '=', 'binary'),
        ], order='create_date desc, id desc', limit=1)

    def _get_latest_workflow_record(self, model_name):
        self.ensure_one()
        Model = self.env[model_name].sudo()
        if model_name == 'bhu.sia.team':
            return Model.search([
                ('project_id', '=', self.project_id.id),
                '|',
                ('village_id', '=', self.village_id.id),
                ('village_ids', 'in', self.village_id.id),
            ], order='create_date desc, id desc', limit=1)
        return Model.search([
            ('project_id', '=', self.project_id.id),
            ('village_id', '=', self.village_id.id),
        ], order='create_date desc, id desc', limit=1)

    def _workflow_line_vals(self, step, section_label, role_label, model_name, file_field, filename_field):
        rec = self._get_latest_workflow_record(model_name)
        has_file = bool(rec and rec.exists() and rec[file_field])
        return {
            'step_no': step,
            'document_type': False,
            'section_label': '%s - %s' % (section_label, role_label),
            'step_label': _("Step %s") % step,
            'document_id': False,
            'attachment_id': False,
            'signed_date': False,
            'document_count': 1 if rec else 0,
            'is_available': has_file,
            'source_model': model_name if rec else False,
            'source_record_id': rec.id if rec else False,
            'source_file_field': file_field if rec else False,
            'source_filename_field': filename_field if rec else False,
        }

    def _refresh_section_lines(self):
        self.ensure_one()
        self.section_line_ids = [(5, 0, 0)]
        if not (self.project_id and self.village_id):
            return
        workflow_steps = [
            (1, _('Section 4'), 'bhu.section4.notification'),
            (2, _('SIA Reports'), 'bhu.sia.team'),
            (3, _('Section 11'), 'bhu.section11.preliminary.report'),
            (4, _('Section 15'), 'bhu.section15.objection'),
            (5, _('Section 19'), 'bhu.section19.notification'),
            (6, _('Section 21'), 'bhu.section21.notification'),
        ]
        commands = []
        first_document_id = False
        first_attachment_id = False
        first_source = False

        step = 1
        for _step_idx, sec_label, model_name in workflow_steps:
            commands.append((0, 0, self._workflow_line_vals(step, sec_label, _('SDM PDF'), model_name, 'sdm_signed_file', 'sdm_signed_filename')))
            step += 1
            commands.append((0, 0, self._workflow_line_vals(step, sec_label, _('Collector PDF'), model_name, 'collector_signed_file', 'collector_signed_filename')))
            step += 1

        s23_defs = [
            {'step': step, 'doc_type': 'section23_land_award', 'label': _('Section 23 Land Award')},
            {'step': step + 1, 'doc_type': 'section23_tree_award', 'label': _('Section 23 Tree Award')},
            {'step': step + 2, 'doc_type': 'section23_asset_award', 'label': _('Section 23 Asset Award')},
            {'step': step + 3, 'doc_type': 'section23_consolidated_award', 'label': _('Section 23 Consolidated Award')},
            {'step': step + 4, 'doc_type': 'section23_rr_award', 'label': _('Section 23 R&R Award')},
        ]

        for item in s23_defs:
            doc_type = item['doc_type']
            label = item['label']
            attachment = False
            if doc_type == 'section23_land_award':
                attachment = self._get_latest_award_cache_attachment(scope='land', variant='standard')
            elif doc_type == 'section23_tree_award':
                attachment = self._get_latest_award_cache_attachment(scope='tree', variant='standard')
            elif doc_type == 'section23_asset_award':
                attachment = self._get_latest_award_cache_attachment(scope='asset', variant='standard')
            elif doc_type == 'section23_consolidated_award':
                attachment = self._get_latest_award_cache_attachment(scope='all', variant='consolidated')
            elif doc_type == 'section23_rr_award':
                attachment = self._get_latest_award_cache_attachment(scope='all', variant='rr')
            if attachment and not first_attachment_id:
                first_attachment_id = attachment.id
            available = bool(attachment)
            commands.append((0, 0, {
                'step_no': item['step'],
                'document_type': doc_type,
                'section_label': label,
                'step_label': _("Step %s") % item['step'],
                'document_id': False,
                'attachment_id': attachment.id if attachment else False,
                'signed_date': False,
                'document_count': 1 if attachment else 0,
                'is_available': available,
                'source_model': False,
                'source_record_id': False,
                'source_file_field': False,
                'source_filename_field': False,
            }))
        self.section_line_ids = commands
        available_ids = self.section_line_ids.mapped('document_id').ids
        if self.selected_document_id and self.selected_document_id.id not in available_ids:
            self.selected_document_id = False
        available_attachment_ids = self.section_line_ids.mapped('attachment_id').ids
        if self.selected_attachment_id and self.selected_attachment_id.id not in available_attachment_ids:
            self.selected_attachment_id = False
        available_sources = self.section_line_ids.filtered(lambda l: l.source_model and l.source_record_id and l.source_file_field and l.is_available)
        if self.selected_source_model and self.selected_source_record_id and self.selected_source_file_field:
            match = available_sources.filtered(
                lambda l: l.source_model == self.selected_source_model and
                l.source_record_id == self.selected_source_record_id and
                l.source_file_field == self.selected_source_file_field
            )
            if not match:
                self.selected_source_model = False
                self.selected_source_record_id = False
                self.selected_source_file_field = False
                self.selected_source_filename_field = False
        if not self.selected_document_id and first_document_id:
            self.selected_document_id = first_document_id
        elif not self.selected_document_id and not self.selected_attachment_id and first_attachment_id:
            self.selected_attachment_id = first_attachment_id
        elif not self.selected_document_id and not self.selected_attachment_id and available_sources:
            first_source = available_sources[0]
            self.selected_source_model = first_source.source_model
            self.selected_source_record_id = first_source.source_record_id
            self.selected_source_file_field = first_source.source_file_field
            self.selected_source_filename_field = first_source.source_filename_field


class DocumentVaultNavigatorLine(models.Model):
    _name = 'bhu.document.vault.navigator.line'
    _description = 'Document Vault Navigator Line'
    _order = 'step_no, id'

    navigator_id = fields.Many2one('bhu.document.vault.navigator', required=True, ondelete='cascade')
    step_no = fields.Integer(string='Step')
    step_label = fields.Char(string='Step Label')
    document_type = fields.Selection(selection=lambda self: self.env['bhu.document.vault']._fields['document_type'].selection)
    section_label = fields.Char(string='Section')
    document_id = fields.Many2one('bhu.document.vault', string='Document')
    attachment_id = fields.Many2one('ir.attachment', string='Attachment')
    source_model = fields.Char(string='Source Model')
    source_record_id = fields.Integer(string='Source Record ID')
    source_file_field = fields.Char(string='Source File Field')
    source_filename_field = fields.Char(string='Source Filename Field')
    signed_date = fields.Date(string='Signed Date')
    document_count = fields.Integer(string='Count')
    is_available = fields.Boolean(string='Available')
    status_display = fields.Char(string='Status', compute='_compute_status_display')
    availability_icon = fields.Char(string='Doc', compute='_compute_availability_icon')
    is_selected = fields.Boolean(string='Selected', compute='_compute_is_selected')

    @api.depends('document_id', 'attachment_id', 'source_model', 'source_record_id', 'source_file_field')
    def _compute_status_display(self):
        for line in self:
            line.status_display = _('Available') if (
                line.document_id or line.attachment_id or (
                    line.source_model and line.source_record_id and line.source_file_field
                )
            ) else _('Missing')

    @api.depends('is_available')
    def _compute_availability_icon(self):
        for line in self:
            line.availability_icon = '✅' if line.is_available else '⚪'

    @api.depends(
        'navigator_id.selected_document_id',
        'navigator_id.selected_attachment_id',
        'navigator_id.selected_source_model',
        'navigator_id.selected_source_record_id',
        'navigator_id.selected_source_file_field',
        'document_id',
        'attachment_id',
        'source_model',
        'source_record_id',
        'source_file_field',
    )
    def _compute_is_selected(self):
        for line in self:
            line.is_selected = bool(
                line.navigator_id and (
                    (line.navigator_id.selected_document_id and line.document_id and line.document_id.id == line.navigator_id.selected_document_id.id) or
                    (line.navigator_id.selected_attachment_id and line.attachment_id and line.attachment_id.id == line.navigator_id.selected_attachment_id.id) or
                    (
                        line.navigator_id.selected_source_model and
                        line.navigator_id.selected_source_record_id and
                        line.navigator_id.selected_source_file_field and
                        line.source_model == line.navigator_id.selected_source_model and
                        line.source_record_id == line.navigator_id.selected_source_record_id and
                        line.source_file_field == line.navigator_id.selected_source_file_field
                    )
                )
            )

    def action_select_document(self):
        self.ensure_one()
        if not self.navigator_id:
            return False
        source_rec = False
        source_has_file = False
        if self.source_model and self.source_record_id and self.source_file_field:
            source_rec = self.env[self.source_model].sudo().browse(self.source_record_id)
            source_has_file = bool(source_rec.exists() and source_rec[self.source_file_field])
        is_available = bool(
            self.document_id or
            self.attachment_id or
            source_has_file
        )
        if not is_available:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Not Available'),
                    'message': _('This section is not generated yet, or no PDF is available for this section.'),
                    'type': 'warning',
                    'sticky': False,
                },
            }
        self.navigator_id.selected_document_id = self.document_id.id if self.document_id else False
        self.navigator_id.selected_attachment_id = self.attachment_id.id if self.attachment_id else False
        self.navigator_id.selected_source_model = self.source_model if self.source_model else False
        self.navigator_id.selected_source_record_id = self.source_record_id if self.source_record_id else False
        self.navigator_id.selected_source_file_field = self.source_file_field if self.source_file_field else False
        self.navigator_id.selected_source_filename_field = self.source_filename_field if self.source_filename_field else False
        return self.navigator_id._action_open_self()

    def get_formview_action(self, access_uid=None):
        """Prevent x2many row click popup; keep selection in navigator only."""
        self.ensure_one()
        return self.action_select_document()
