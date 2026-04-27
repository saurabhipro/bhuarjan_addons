# -*- coding: utf-8 -*-

from odoo import models, _
from odoo.exceptions import ValidationError


class Section23AwardConsolidated(models.Model):
    _inherit = 'bhu.section23.award'

    def get_consolidated_report_project_name(self):
        """Project name for consolidated PDF/Excel; sudo browse for ACL-safe display."""
        self.ensure_one()
        pid = self.project_id.id
        if not pid:
            return ''
        project = self.env['bhu.project'].sudo().browse(pid)
        return (project.name or '').strip()

    def action_download_consolidated_pdf(self):
        """Download consolidated award sheet as PDF (one row per khasra) using QWeb template."""
        self.ensure_one()
        consolidated_data = self.get_consolidated_award_data()
        if not consolidated_data:
            raise ValidationError(_('No consolidated data available for this award.'))

        # Use standard report_action so Odoo passes docs/o context correctly.
        report_action = self.env.ref('bhuarjan.action_report_consolidated_award_sheet')
        return report_action.sudo().report_action(self)

    def action_download_consolidated_excel(self):
        """Download consolidated award sheet as Excel (one row per khasra)."""
        self.ensure_one()
        import io
        import base64
        try:
            import xlsxwriter
        except ImportError:
            raise ValidationError(_("Python library 'xlsxwriter' is not installed."))

        consolidated_data = self.get_consolidated_award_data()
        if not consolidated_data:
            raise ValidationError(_('No consolidated data available for this award.'))

        award_headers = self.get_award_header_constants()
        consolidated_headers = award_headers['excel']['consolidated_award_headers']

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Consolidated Award')

        # ── Formats ────────────────────────────────────────────────────────
        FONT = 'Noto Sans Devanagari'
        title_fmt = workbook.add_format({
            'bold': True, 'font_size': 13, 'font_name': FONT,
            'align': 'center', 'valign': 'vcenter', 'border': 1,
            'bg_color': '#FFFFFF',
        })
        subtitle_fmt = workbook.add_format({
            'font_size': 10, 'font_name': FONT,
            'align': 'center', 'valign': 'vcenter', 'border': 1,
            'text_wrap': True,
        })
        header_fmt = workbook.add_format({
            'bold': True, 'font_size': 9, 'font_name': FONT,
            'bg_color': '#D3D3D3', 'align': 'center', 'valign': 'vcenter',
            'border': 1, 'text_wrap': True,
        })
        cell_fmt = workbook.add_format({
            'font_size': 10, 'font_name': FONT,
            'border': 1, 'valign': 'top', 'align': 'left',
        })
        cell_fmt_alt = workbook.add_format({
            'font_size': 10, 'font_name': FONT,
            'border': 1, 'valign': 'top', 'align': 'left',
            'bg_color': '#F8F8F8',
        })
        name_fmt = workbook.add_format({
            'font_size': 10, 'font_name': FONT,
            'border': 1, 'valign': 'top', 'align': 'left', 'text_wrap': True,
        })
        name_fmt_alt = workbook.add_format({
            'font_size': 10, 'font_name': FONT,
            'border': 1, 'valign': 'top', 'align': 'left', 'text_wrap': True,
            'bg_color': '#F8F8F8',
        })
        num_fmt = workbook.add_format({
            'font_size': 10, 'font_name': FONT,
            'border': 1, 'align': 'right', 'valign': 'vcenter',
            'num_format': '#,##0.00',
        })
        num_fmt_alt = workbook.add_format({
            'font_size': 10, 'font_name': FONT,
            'border': 1, 'align': 'right', 'valign': 'vcenter',
            'num_format': '#,##0.00',
            'bg_color': '#F8F8F8',
        })
        area_fmt = workbook.add_format({
            'font_size': 10, 'font_name': FONT,
            'border': 1, 'align': 'right', 'valign': 'vcenter',
            'num_format': '0.0000',
        })
        area_fmt_alt = workbook.add_format({
            'font_size': 10, 'font_name': FONT,
            'border': 1, 'align': 'right', 'valign': 'vcenter',
            'num_format': '0.0000',
            'bg_color': '#F8F8F8',
        })
        total_label_fmt = workbook.add_format({
            'bold': True, 'font_size': 10, 'font_name': FONT,
            'bg_color': '#D3D3D3', 'border': 1,
            'align': 'center', 'valign': 'vcenter',
        })
        total_num_fmt = workbook.add_format({
            'bold': True, 'font_size': 10, 'font_name': FONT,
            'bg_color': '#D3D3D3', 'border': 1,
            'align': 'right', 'valign': 'vcenter',
            'num_format': '#,##0.00',
        })
        total_area_fmt = workbook.add_format({
            'bold': True, 'font_size': 10, 'font_name': FONT,
            'bg_color': '#D3D3D3', 'border': 1,
            'align': 'right', 'valign': 'vcenter',
            'num_format': '0.0000',
        })

        # ── Title ──────────────────────────────────────────────────────────
        sheet.set_row(0, 24)
        sheet.merge_range(0, 0, 0, 8,
            'भूमि, परिसंपत्तियों तथा वृक्षों के मुआवजा का गोशवारा भाग -1 (घ)',
            title_fmt)

        # ── Subtitle ───────────────────────────────────────────────────────
        village_name = self.village_id.name or '-'
        tehsil_name = self.village_id.tehsil_id.name if self.village_id and self.village_id.tehsil_id else '-'
        district_name = self.village_id.district_id.name if self.village_id and self.village_id.district_id else '-'
        state_name = (self.village_id.district_id.state_id.name
                      if self.village_id and self.village_id.district_id and self.village_id.district_id.state_id
                      else '')
        district_full = f"{district_name} ({state_name})" if state_name else district_name
        date_str = self.award_date.strftime('%d-%m-%Y') if self.award_date else ''
        project_name = self.get_consolidated_report_project_name()
        subtitle = (
            f"भू-अर्जन प्रकरण क्रमांक {self.case_number or ''} / "
            f"ग्राम-{village_name}  "
            f"Project: {project_name}  "
            f"तहसील-{tehsil_name}  जिला-{district_full}  दिनांक: {date_str}"
        )
        sheet.set_row(1, 36)
        sheet.merge_range(1, 0, 1, 8, subtitle, subtitle_fmt)

        # ── Two-row column headers ─────────────────────────────────────────
        header_row = 3
        sheet.set_row(header_row, 36)
        sheet.set_row(header_row + 1, 30)
        sheet.merge_range(header_row, 0, header_row + 1, 0, consolidated_headers[0], header_fmt)
        sheet.merge_range(header_row, 1, header_row + 1, 1, consolidated_headers[1], header_fmt)
        sheet.merge_range(header_row, 2, header_row, 3, 'अर्जित भूमि का विवरण', header_fmt)
        sheet.write(header_row + 1, 2, 'खसरा नं.', header_fmt)
        sheet.write(header_row + 1, 3, 'रकबा (हे.)', header_fmt)
        for col in range(4, 9):
            sheet.merge_range(header_row, col, header_row + 1, col, consolidated_headers[col], header_fmt)

        # ── Data rows ─────────────────────────────────────────────────────
        row = 5
        t_ha = t_land = t_asset = t_tree = t_det = 0.0
        for idx, data in enumerate(consolidated_data):
            is_alt = idx % 2 == 1
            # Estimate row height: each owner block ~3 lines × 15pt; min 20
            num_owners = len(data.get('owners') or [])
            row_height = max(20, num_owners * 42)
            sheet.set_row(row, row_height)

            # Choose formats based on row color
            cur_cell = cell_fmt_alt if is_alt else cell_fmt
            cur_name = name_fmt_alt if is_alt else name_fmt
            cur_area = area_fmt_alt if is_alt else area_fmt
            cur_num = num_fmt_alt if is_alt else num_fmt

            sheet.write(row, 0, data['serial'], cur_cell)
            sheet.write(row, 1, data['owner_details'], cur_name)
            sheet.write(row, 2, data['khasra_acquired'], cur_cell)
            ha = float(data['acquired_area_ha'] or 0.0)
            land_c = float(data['land_compensation'] or 0.0)
            asset_c = float(data['asset_compensation'] or 0.0)
            tree_c = float(data['tree_compensation'] or 0.0)
            det = float(data['determined_total'] or 0.0)
            sheet.write_number(row, 3, ha, cur_area)
            sheet.write_number(row, 4, land_c, cur_num)
            sheet.write_number(row, 5, asset_c, cur_num)
            sheet.write_number(row, 6, tree_c, cur_num)
            sheet.write_number(row, 7, det, cur_num)
            sheet.write(row, 8, '', cur_cell)
            t_ha += ha
            t_land += land_c
            t_asset += asset_c
            t_tree += tree_c
            t_det += det
            row += 1

        # ── Total row ─────────────────────────────────────────────────────
        sheet.set_row(row, 20)
        sheet.merge_range(row, 0, row, 2, 'कुल / Total', total_label_fmt)
        sheet.write_number(row, 3, t_ha, total_area_fmt)
        sheet.write_number(row, 4, t_land, total_num_fmt)
        sheet.write_number(row, 5, t_asset, total_num_fmt)
        sheet.write_number(row, 6, t_tree, total_num_fmt)
        sheet.write_number(row, 7, t_det, total_num_fmt)
        sheet.write(row, 8, '', total_label_fmt)

        # ── Column widths ─────────────────────────────────────────────────
        sheet.set_column(0, 0, 7)
        sheet.set_column(1, 1, 30)
        sheet.set_column(2, 2, 12)
        sheet.set_column(3, 3, 10)
        sheet.set_column(4, 7, 14)
        sheet.set_column(8, 8, 12)

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())
        output.close()

        attachment = self.env['ir.attachment'].create({
            'name': f"ConsolidatedAwardSheet_{self.village_id.name or 'Award'}.xlsx",
            'type': 'binary',
            'datas': file_data,
            'res_model': 'bhu.section23.award',
            'res_id': self.id,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def get_consolidated_award_data(self):
        """Get consolidated award data by khasra (summary sheet columns)."""
        self.ensure_one()

        land_data = self.get_land_compensation_grouped_data()
        tree_data = self.get_tree_compensation_grouped_data()
        asset_data = self.get_structure_compensation_grouped_data()

        def _blank_entry(khasra):
            return {
                'khasra': khasra,
                # owners: list of dicts {name, father_name, address}
                'owners': [],
                'owner_keys': set(),   # dedup key: (name, father)
                'total_rakba_ha': 0.0,
                'acquired_area_ha': 0.0,
                'land_compensation': 0.0,
                'asset_compensation': 0.0,
                'tree_compensation': 0.0,
                'remarks': '',
            }

        def _add_owner(entry, name, father='', spouse='', address=''):
            name = (name or '').strip()
            father = (father or '').strip()
            spouse = (spouse or '').strip()
            key = (name.lower(), father.lower() or spouse.lower())
            if name and key not in entry['owner_keys']:
                entry['owner_keys'].add(key)
                entry['owners'].append({
                    'name': name,
                    'father_name': father,
                    'spouse_name': spouse,
                    'address': (address or '').strip(),
                })

        consolidated = {}

        for group in land_data:
            for line in group.get('lines', []):
                khasra = line.get('khasra', '')
                if khasra not in consolidated:
                    consolidated[khasra] = _blank_entry(khasra)
                _add_owner(
                    consolidated[khasra],
                    group.get('landowner_name', ''),
                    group.get('father_name', ''),
                    group.get('spouse_name', ''),
                    group.get('address', ''),
                )
                consolidated[khasra]['total_rakba_ha'] += line.get('original_area', 0.0) or 0.0
                acquired_ha = (line.get('acquired_area', 0.0) or line.get('original_area', 0.0) or 0.0)
                consolidated[khasra]['acquired_area_ha'] += acquired_ha
                consolidated[khasra]['land_compensation'] += line.get('total_compensation', 0.0) or 0.0

        for group in tree_data:
            for line in group.get('lines', []):
                khasra = line.get('tree_khasra', line.get('khasra', ''))
                if khasra not in consolidated:
                    consolidated[khasra] = _blank_entry(khasra)
                _add_owner(
                    consolidated[khasra],
                    group.get('landowner_name', ''),
                    group.get('father_name', ''),
                    group.get('spouse_name', ''),
                    group.get('address', ''),
                )
                consolidated[khasra]['tree_compensation'] += line.get('total', 0.0) or 0.0

        for group in asset_data:
            for line in group.get('lines', []):
                khasra = line.get('asset_khasra', '')
                if khasra not in consolidated:
                    consolidated[khasra] = _blank_entry(khasra)
                _add_owner(
                    consolidated[khasra],
                    group.get('landowner_name', ''),
                    group.get('father_name', ''),
                    group.get('spouse_name', ''),
                    group.get('address', ''),
                )
                consolidated[khasra]['asset_compensation'] += line.get('total', 0.0) or 0.0

        result = []
        for khasra in sorted(consolidated.keys()):
            data = consolidated[khasra]
            acquired_area_ha = data['acquired_area_ha'] or 0.0
            determined_total = (
                (data['land_compensation'] or 0.0)
                + (data['asset_compensation'] or 0.0)
                + (data['tree_compensation'] or 0.0)
            )
            # Build plain-text owner details for Excel — same logic as Form 10, with serial numbers
            owner_lines = []
            for idx, owner in enumerate(data['owners'], 1):
                block = f"{idx}. {owner['name']}"
                if owner['father_name']:
                    block += f" पिता {owner['father_name']}"
                elif owner['spouse_name']:
                    block += f" पति {owner['spouse_name']}"
                if owner['address']:
                    block += f"\nनिवासी: {owner['address']}"
                owner_lines.append(block)
            owner_details_text = '\n'.join(owner_lines) if owner_lines else ''

            result.append({
                'serial': len(result) + 1,
                'owners': data['owners'],            # list of dicts — used in PDF
                'owner_details': owner_details_text, # plain text — used in Excel
                'khasra_total': khasra,
                'total_rakba_ha': data['total_rakba_ha'],
                'khasra_acquired': khasra,
                'acquired_area_ha': acquired_area_ha,
                'land_compensation': data['land_compensation'],
                'asset_compensation': data['asset_compensation'],
                'tree_compensation': data['tree_compensation'],
                'determined_total': determined_total,
                'remarks': data['remarks'],
            })

        return result
