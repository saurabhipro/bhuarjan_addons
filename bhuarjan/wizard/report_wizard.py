from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io
import csv

try:
    import xlsxwriter
    HAS_XLSXWRITER = True
except ImportError:
    HAS_XLSXWRITER = False

class ReportWizard(models.TransientModel):
    _name = 'report.wizard'
    _description = 'Report Wizard'

    form_10 = fields.Boolean(string="Form 10 Download")
    export_type = fields.Selection([
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('csv', 'CSV')
    ], string='Export Type', default='pdf', required=True)
    village_id = fields.Many2one('bhu.village', string='Village', required=True)
    allowed_village_ids = fields.Many2many(
        'bhu.village',
        string='Allowed Villages',
        default=lambda self: [(6, 0, self.env.user.village_ids.ids)],
    )

    def action_print_report(self):
        """Generate Form 10 report in selected format (PDF/Excel/CSV)"""
        if self.env.user.bhuarjan_role == 'patwari' and self.village_id and self.village_id.id not in self.env.user.village_ids.ids:
            raise UserError("You are not allowed to download for this village.")
        
        all_records = self.env['bhu.survey'].search([
            ('village_id', '=', self.village_id.id)
        ])
        if not all_records:
            raise UserError("No records found for your villages.")

        if self.export_type == 'pdf':
            # Use consolidated single-PDF table report
            report_action = self.env.ref('bhuarjan.action_report_form10_bulk_table')
            return report_action.report_action(all_records)
        elif self.export_type == 'excel':
            return self._export_to_excel(all_records)
        elif self.export_type == 'csv':
            return self._export_to_csv(all_records)

    def _export_to_excel(self, surveys):
        """Export surveys to Excel format matching PDF structure"""
        if not HAS_XLSXWRITER:
            raise UserError(_("xlsxwriter library is required for Excel export. Please install it: pip install xlsxwriter"))
        
        if not surveys:
            raise UserError(_("No surveys found."))
        
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Form 10')
        
        # Define formats
        title_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 16
        })
        
        header_info_format = workbook.add_format({
            'bold': True,
            'align': 'left',
            'valign': 'vcenter',
            'border': 1
        })
        
        header_info_value_format = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'border': 1
        })
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#f2f4f7',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'text_wrap': True
        })
        
        cell_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'text_wrap': True
        })
        
        signature_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        first = surveys[0]
        current_row = 0
        
        # Process surveys in chunks of 5
        for start_idx in range(0, len(surveys), 5):
            chunk = surveys[start_idx:start_idx + 5]
            
            # Title
            worksheet.merge_range(current_row, 0, current_row, 17, 'भू-अर्जन फार्म-10 (प्रारंभिक सर्वे प्रपत्र)', title_format)
            current_row += 1
            
            # Header info table (3 rows)
            # Row 1: Project and Department
            worksheet.write(current_row, 0, 'परियोजना का नाम :', header_info_format)
            worksheet.merge_range(current_row, 1, current_row, 8, first.project_id.name or '', header_info_value_format)
            worksheet.write(current_row, 9, 'विभाग का नाम', header_info_format)
            worksheet.merge_range(current_row, 10, current_row, 17, first.department_id.name or '', header_info_value_format)
            current_row += 1
            
            # Row 2: Village and Tehsil
            worksheet.write(current_row, 0, 'ग्राम का नाम', header_info_format)
            worksheet.merge_range(current_row, 1, current_row, 8, first.village_id.name or '', header_info_value_format)
            worksheet.write(current_row, 9, 'तहसील का नाम', header_info_format)
            worksheet.merge_range(current_row, 10, current_row, 16, f"{first.tehsil_id.name or ''} जिला-रायगढ़ (छ.ग.)", header_info_value_format)
            current_row += 1
            
            # Row 3: Survey Date
            survey_date_str = first.survey_date.strftime('%d/%m/%Y') if first.survey_date else ''
            worksheet.write(current_row, 0, 'सर्वे दिनाँक', header_info_format)
            worksheet.merge_range(current_row, 1, current_row, 17, survey_date_str, header_info_value_format)
            current_row += 1
            current_row += 1  # Spacing
            
            # Table headers (2 rows - matching PDF structure)
            # First header row
            worksheet.write(current_row, 0, 'क्र.', header_format)
            worksheet.write(current_row, 1, 'प्रभावित खसरा क्रमांक', header_format)
            worksheet.write(current_row, 2, 'कुल रकबा (हे.में.)', header_format)
            worksheet.write(current_row, 3, 'अर्जन हेतु प्रस्तावित क्षेत्रफल (हेक्टेयर)', header_format)
            worksheet.write(current_row, 4, 'भूमिस्वामी का नाम', header_format)
            worksheet.merge_range(current_row, 5, current_row, 8, 'भूमि का प्रकार', header_format)
            worksheet.merge_range(current_row, 9, current_row, 11, 'भूमि पर स्थित वृक्ष की संख्या (प्रजातिवार)', header_format)
            worksheet.merge_range(current_row, 12, current_row, 17, 'भूमि पर स्थित परिसंपत्तियों का विवरण', header_format)
            current_row += 1
            
            # Second header row
            worksheet.write(current_row, 0, '', header_format)  # Skip first 4 columns (merged above)
            worksheet.write(current_row, 1, '', header_format)
            worksheet.write(current_row, 2, '', header_format)
            worksheet.write(current_row, 3, '', header_format)
            worksheet.write(current_row, 4, '', header_format)
            worksheet.write(current_row, 5, 'एक फसली', header_format)
            worksheet.write(current_row, 6, 'दो फसली', header_format)
            worksheet.write(current_row, 7, 'सिंचित', header_format)
            worksheet.write(current_row, 8, 'असिंचित', header_format)
            worksheet.write(current_row, 9, 'अविकसित', header_format)
            worksheet.write(current_row, 10, 'अर्द्ध विकसित', header_format)
            worksheet.write(current_row, 11, 'पूर्ण विकसित', header_format)
            worksheet.write(current_row, 12, 'मकान (कच्चा/पक्का) क्षेत्रफल वर्गफुट में', header_format)
            worksheet.write(current_row, 13, 'शेड (क्षेत्रफल वर्गफुट में)', header_format)
            worksheet.write(current_row, 14, 'कुँआ (कच्चा/पक्का) (हाँ/नहीं)', header_format)
            worksheet.write(current_row, 15, 'ट्यूबवेल / सम्बमर्शिबल पम्प फिटिंग सहित (हाँ/नहीं)', header_format)
            worksheet.write(current_row, 16, 'तालाब (हाँ/नहीं)', header_format)
            worksheet.write(current_row, 17, 'रिमार्क', header_format)
            current_row += 1
            
            # Data rows (max 5 per chunk)
            for idx, survey in enumerate(chunk):
                serial_num = start_idx + idx + 1
                
                # Get landowner names
                owner_names = []
                counter = 1
                for lo in survey.landowner_ids:
                    name = lo.name
                    if lo.gender == 'female' and lo.spouse_name:
                        name += f" पत्नी {lo.spouse_name}"
                    elif lo.father_name:
                        name += f" पिता {lo.father_name}"
                    owner_names.append(f"{counter}. {name}")
                    counter += 1
                owner_str = "\n".join(owner_names) if owner_names else "नहीं"
                
                # Well type
                well_str = "नहीं"
                if survey.has_well == 'yes':
                    if survey.well_type == 'kachcha':
                        well_str = "हाँ-कच्चा"
                    elif survey.well_type == 'pakka':
                        well_str = "हाँ-पक्का"
                
                # House type
                house_str = "नहीं"
                if survey.house_type and survey.house_area:
                    house_str = f"{survey.house_type} / {survey.house_area}"
                
                data = [
                    serial_num,
                    survey.khasra_number or "नहीं",
                    survey.total_area or 0,
                    survey.acquired_area or 0,
                    owner_str,
                    "हाँ" if survey.is_single_crop else "नहीं",
                    "हाँ" if survey.is_double_crop else "नहीं",
                    "हाँ" if survey.is_irrigated else "नहीं",
                    "हाँ" if survey.is_unirrigated else "नहीं",
                    survey.tree_count if survey.tree_development_stage == 'undeveloped' else "नहीं",
                    survey.tree_count if survey.tree_development_stage == 'semi_developed' else "नहीं",
                    survey.tree_count if survey.tree_development_stage == 'fully_developed' else "नहीं",
                    house_str,
                    survey.shed_area or "नहीं",
                    well_str,
                    "हाँ" if survey.has_tubewell == 'yes' else "नहीं",
                    "हाँ" if survey.has_pond == 'yes' else "नहीं",
                    survey.remarks or "नहीं"
                ]
                
                for col, value in enumerate(data):
                    worksheet.write(current_row, col, value, cell_format)
                current_row += 1
            
            # Signature section after each chunk of 5 rows
            current_row += 1  # Spacing
            signature_start_row = current_row
            
            # Signature headers
            worksheet.write(current_row, 0, '(हस्ताक्षर)', signature_format)
            worksheet.merge_range(current_row, 1, current_row, 4, 'अपेक्षक निकाय के अधिकृत प्रतिनिधि', signature_format)
            worksheet.write(current_row, 5, '(हस्ताक्षर)', signature_format)
            worksheet.merge_range(current_row, 6, current_row, 9, 'तहसीलदार', signature_format)
            worksheet.write(current_row, 10, '(हस्ताक्षर)', signature_format)
            worksheet.merge_range(current_row, 11, current_row, 14, 'नायब तहसीलदार', signature_format)
            worksheet.write(current_row, 15, '(हस्ताक्षर)', signature_format)
            worksheet.merge_range(current_row, 16, current_row, 17, 'राजस्व निरीक्षक', signature_format)
            current_row += 1
            
            # Signature details
            worksheet.merge_range(current_row, 0, current_row, 4, 'नाम -', signature_format)
            worksheet.merge_range(current_row, 5, current_row, 5, 'पदनाम', signature_format)
            worksheet.merge_range(current_row, 6, current_row, 9, 'नाम -', signature_format)
            worksheet.merge_range(current_row, 10, current_row, 14, 'नाम -', signature_format)
            worksheet.merge_range(current_row, 15, current_row, 16, 'नाम-', signature_format)
            worksheet.write(current_row, 17, 'रा.नि.मं.', signature_format)
            current_row += 2  # Spacing before next chunk
        
        # Set column widths
        worksheet.set_column(0, 0, 5)   # Serial
        worksheet.set_column(1, 1, 20)  # Khasra
        worksheet.set_column(2, 3, 15)  # Areas
        worksheet.set_column(4, 4, 30)  # Landowners
        worksheet.set_column(5, 17, 12)  # Other columns
        
        workbook.close()
        output.seek(0)
        
        # Create attachment
        village_name = surveys[0].village_id.name if surveys else "All"
        filename = f"Form10_{village_name}.xlsx"
        
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': 'report.wizard',
            'res_id': self.id,
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
    
    def _export_to_csv(self, surveys):
        """Export surveys to CSV format matching PDF structure"""
        if not surveys:
            raise UserError(_("No surveys found."))
        
        output = io.StringIO()
        writer = csv.writer(output)
        first = surveys[0]
        
        # Process surveys in chunks of 5
        for start_idx in range(0, len(surveys), 5):
            chunk = surveys[start_idx:start_idx + 5]
            
            # Title
            writer.writerow(['भू-अर्जन फार्म-10 (प्रारंभिक सर्वे प्रपत्र)'] + [''] * 17)
            writer.writerow([])  # Empty row
            
            # Header info (project/department/village/tehsil/date)
            project_name = first.project_id.name or ''
            dept_name = first.department_id.name or ''
            village_name = first.village_id.name or ''
            tehsil_name = first.tehsil_id.name or ''
            survey_date_str = first.survey_date.strftime('%d/%m/%Y') if first.survey_date else ''
            
            writer.writerow(['परियोजना का नाम :', project_name] + [''] * 16)
            writer.writerow(['विभाग का नाम', dept_name] + [''] * 16)
            writer.writerow(['ग्राम का नाम', village_name] + [''] * 16)
            writer.writerow(['तहसील का नाम', f"{tehsil_name} जिला-रायगढ़ (छ.ग.)"] + [''] * 16)
            writer.writerow(['सर्वे दिनाँक', survey_date_str] + [''] * 16)
            writer.writerow([])  # Empty row
            
            # Table headers (2 rows - matching PDF structure)
            # First header row
            writer.writerow([
                'क्र.', 'प्रभावित खसरा क्रमांक', 'कुल रकबा (हे.में.)', 
                'अर्जन हेतु प्रस्तावित क्षेत्रफल (हेक्टेयर)', 'भूमिस्वामी का नाम',
                'भूमि का प्रकार', '', '', '',
                'भूमि पर स्थित वृक्ष की संख्या (प्रजातिवार)', '', '',
                'भूमि पर स्थित परिसंपत्तियों का विवरण', '', '', '', '', ''
            ])
            # Second header row
            writer.writerow([
                '', '', '', '', '',
                'एक फसली', 'दो फसली', 'सिंचित', 'असिंचित',
                'अविकसित', 'अर्द्ध विकसित', 'पूर्ण विकसित',
                'मकान (कच्चा/पक्का) क्षेत्रफल वर्गफुट में', 'शेड (क्षेत्रफल वर्गफुट में)',
                'कुँआ (कच्चा/पक्का) (हाँ/नहीं)', 'ट्यूबवेल / सम्बमर्शिबल पम्प फिटिंग सहित (हाँ/नहीं)', 
                'तालाब (हाँ/नहीं)', 'रिमार्क'
            ])
            
            # Data rows (max 5 per chunk)
            for idx, survey in enumerate(chunk):
                serial_num = start_idx + idx + 1
                
                # Get landowner names
                owner_names = []
                counter = 1
                for lo in survey.landowner_ids:
                    name = lo.name
                    if lo.gender == 'female' and lo.spouse_name:
                        name += f" पत्नी {lo.spouse_name}"
                    elif lo.father_name:
                        name += f" पिता {lo.father_name}"
                    owner_names.append(f"{counter}. {name}")
                    counter += 1
                owner_str = ", ".join(owner_names) if owner_names else "नहीं"
                
                # Well type
                well_str = "नहीं"
                if survey.has_well == 'yes':
                    if survey.well_type == 'kachcha':
                        well_str = "हाँ-कच्चा"
                    elif survey.well_type == 'pakka':
                        well_str = "हाँ-पक्का"
                
                # House type
                house_str = "नहीं"
                if survey.house_type and survey.house_area:
                    house_str = f"{survey.house_type} / {survey.house_area}"
                
                data = [
                    serial_num,
                    survey.khasra_number or "नहीं",
                    survey.total_area or 0,
                    survey.acquired_area or 0,
                    owner_str,
                    "हाँ" if survey.is_single_crop else "नहीं",
                    "हाँ" if survey.is_double_crop else "नहीं",
                    "हाँ" if survey.is_irrigated else "नहीं",
                    "हाँ" if survey.is_unirrigated else "नहीं",
                    survey.tree_count if survey.tree_development_stage == 'undeveloped' else "नहीं",
                    survey.tree_count if survey.tree_development_stage == 'semi_developed' else "नहीं",
                    survey.tree_count if survey.tree_development_stage == 'fully_developed' else "नहीं",
                    house_str,
                    survey.shed_area or "नहीं",
                    well_str,
                    "हाँ" if survey.has_tubewell == 'yes' else "नहीं",
                    "हाँ" if survey.has_pond == 'yes' else "नहीं",
                    survey.remarks or "नहीं"
                ]
                
                writer.writerow(data)
            
            # Signature section after each chunk of 5 rows
            writer.writerow([])  # Empty row
            writer.writerow(['(हस्ताक्षर)', 'अपेक्षक निकाय के अधिकृत प्रतिनिधि', '', '', '',
                            '(हस्ताक्षर)', 'तहसीलदार', '', '', '',
                            '(हस्ताक्षर)', 'नायब तहसीलदार', '', '', '',
                            '(हस्ताक्षर)', 'राजस्व निरीक्षक', '', ''])
            writer.writerow(['नाम -', 'पदनाम', '', '', '',
                            'नाम -', '', '', '', '',
                            'नाम -', '', '', '', '',
                            'नाम-', 'रा.नि.मं.', '', ''])
            writer.writerow([])  # Empty row before next chunk
            writer.writerow([])  # Extra spacing
        
        csv_data = output.getvalue()
        output.close()
        
        # Create attachment
        village_name = surveys[0].village_id.name if surveys else "All"
        filename = f"Form10_{village_name}.csv"
        
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(csv_data.encode('utf-8-sig')),
            'mimetype': 'text/csv',
            'res_model': 'report.wizard',
            'res_id': self.id,
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}
