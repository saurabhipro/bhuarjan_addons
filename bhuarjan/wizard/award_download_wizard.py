# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AwardDownloadWizard(models.TransientModel):
    _name = 'bhu.award.download.wizard'
    _description = 'Award Download Wizard (PDF/Excel only)'

    res_model = fields.Char(string='Model Name', required=True)
    res_id = fields.Integer(string='Record ID', required=True)
    report_xml_id = fields.Char(string='Report XML ID', required=True)
    filename = fields.Char(string='Filename')

    format = fields.Selection([
        ('pdf', 'PDF Format'),
        ('excel', 'Excel Format (.xlsx)'),
    ], string='Download Format', default='pdf', required=True)

    export_scope = fields.Selection(
        [
            ('all', '📋 All sections / सभी पत्रक (भूमि + परिसम्पत्ति + वृक्ष)'),
            ('land', '🧾 Land only (Part Ka) / केवल भूमि (भाग-1 क)'),
            ('asset', '🏠 Structure only (Part Kh) / केवल परिसम्पत्ति (भाग-1 ख)'),
            ('tree', '🌳 Trees only (Part Ga) / केवल वृक्ष (भाग-1 ग)'),
        ],
        string='Sections / पत्रक',
        default='all',
        required=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('active_model') and self.env.context.get('active_id'):
            res.setdefault('res_model', self.env.context.get('active_model'))
            res.setdefault('res_id', self.env.context.get('active_id'))
        return res

    def action_download(self):
        self.ensure_one()
        record = self.env[self.res_model].browse(self.res_id)
        if not record.exists():
            raise UserError(_(
                "The selected record no longer exists. "
                "Please reopen the document and try download again."
            ))
        scope = (self.export_scope or 'all')
        if scope not in ('all', 'land', 'asset', 'tree'):
            scope = 'all'
        if self.format == 'pdf':
            # PDF always renders the full award (all sections).
            # Scope filtering applies only to Excel (handled below).
            report = self.env.ref(self.report_xml_id)
            return report.report_action(record)
        if self.format == 'excel':
            # Keep wizard generic: support standard Excel hook and
            # Section 23 consolidated components Excel hook.
            if hasattr(record, 'action_download_excel'):
                return record.action_download_excel(export_scope=scope)
            if hasattr(record, 'action_download_excel_components'):
                return record.action_download_excel_components(export_scope=scope)
            raise UserError(_("Excel export is not supported for this report."))
        raise UserError(_("Selected download format is not supported."))
