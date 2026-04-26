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

    # True when opened from Section 23 "Generate award" (same UI as Award Simulator)
    section23_generate = fields.Boolean(string='Section 23 Generate', default=False)
    add_cover_letter = fields.Boolean(
        string='Add Cover Letter / कवर लेटर जोड़ें',
        default=False,
        help='Include executive summary cover page in Section 23 PDF.',
    )

    section23_avg_three_year_sales_sort_rate = fields.Integer(
        string='विगत तीन वर्षों का औसत बिक्री छांट दर',
        default=0,
        help='Required to generate the Section 23 award; saved on the award record (integer only).',
    )
    
    consolidated_award_sheet = fields.Boolean(
        string='Consolidated Award Sheet / समेकित अवार्ड शीट',
        default=False,
        help='Download consolidated summary by khasra (one row per khasra with totals).',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('active_model') and self.env.context.get('active_id'):
            res.setdefault('res_model', self.env.context.get('active_model'))
            res.setdefault('res_id', self.env.context.get('active_id'))
        if self.env.context.get('default_section23_generate'):
            res['section23_generate'] = True
        else:
            # Show consolidated option only in download mode (not generate)
            res.setdefault('consolidated_award_sheet', False)
        res_id = res.get('res_id') or self.env.context.get('default_res_id')
        res_model = res.get('res_model') or self.env.context.get('default_res_model')
        if res_model == 'bhu.section23.award' and res_id:
            award = self.env['bhu.section23.award'].browse(res_id)
            if award.exists():
                res.setdefault(
                    'section23_avg_three_year_sales_sort_rate',
                    int(award.avg_three_year_sales_sort_rate or 0),
                )
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

        if self.res_model == 'bhu.section23.award':
            rate = int(self.section23_avg_three_year_sales_sort_rate or 0)
            if self.section23_generate and rate <= 0:
                raise UserError(_(
                    'Please enter विगत तीन वर्षों का औसत बिक्री छांट दर (must be greater than zero) '
                    'before generating the award.'
                ))
            if self.section23_generate and rate > 0:
                record.write({'avg_three_year_sales_sort_rate': float(rate)})

        if self.section23_generate and self.res_model == 'bhu.section23.award':
            if not hasattr(record, 'apply_generate_from_download_wizard'):
                raise UserError(_('This record does not support the generate flow.'))
            return record.apply_generate_from_download_wizard(
                file_format=self.format, export_scope=scope, include_cover_letter=bool(self.add_cover_letter)
            )
        
        # Consolidated award sheet download
        if self.consolidated_award_sheet and self.res_model == 'bhu.section23.award':
            if self.format == 'pdf':
                if hasattr(record, 'action_download_consolidated_pdf'):
                    return record.action_download_consolidated_pdf()
            elif self.format == 'excel':
                if hasattr(record, 'action_download_consolidated_excel'):
                    return record.action_download_consolidated_excel()

        if self.format == 'pdf':
            if self.res_model == 'bhu.section23.award' and hasattr(record, 'action_download_pdf_components'):
                return record.action_download_pdf_components(
                    export_scope=scope,
                    include_cover_letter=bool(self.add_cover_letter),
                )
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
