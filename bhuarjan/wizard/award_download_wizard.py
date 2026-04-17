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
        if self.format == 'pdf':
            report = self.env.ref(self.report_xml_id)
            return report.report_action(record)
        if self.format == 'excel':
            if hasattr(record, 'action_download_excel'):
                return record.action_download_excel()
            raise UserError(_("Excel export is not supported for this report."))
        raise UserError(_("Selected download format is not supported."))
