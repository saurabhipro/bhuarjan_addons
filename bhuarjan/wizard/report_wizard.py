from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io
import csv
import uuid
import logging

_logger = logging.getLogger(__name__)

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
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True)
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम', required=True)
    allowed_village_ids = fields.Many2many(
        'bhu.village',
        string='Allowed Villages',
        compute='_compute_allowed_village_ids',
        store=False,
    )
    
    @api.depends('project_id')
    def _compute_allowed_village_ids(self):
        """Compute allowed villages based on project and user role"""
        for wizard in self:
            if wizard.project_id and wizard.project_id.village_ids:
                # Get project villages
                project_village_ids = wizard.project_id.village_ids.ids
                if wizard.env.user.bhuarjan_role == 'patwari':
                    # For patwari, only show villages that are both in project AND assigned to user
                    user_village_ids = wizard.env.user.village_ids.ids
                    allowed_ids = list(set(project_village_ids) & set(user_village_ids))
                else:
                    # For other users, show all project villages
                    allowed_ids = project_village_ids
                wizard.allowed_village_ids = [(6, 0, allowed_ids)]
            else:
                # No project selected or project has no villages
                if wizard.env.user.bhuarjan_role == 'patwari':
                    # For patwari, show only their assigned villages
                    wizard.allowed_village_ids = [(6, 0, wizard.env.user.village_ids.ids)]
                else:
                    # For other users, show no villages until project is selected
                    wizard.allowed_village_ids = [(6, 0, [])]
    
    
    @api.onchange('project_id')
    def _onchange_project_id(self):
        """Reset village when project changes and update domain to filter by project villages"""
        self.village_id = False
        if self.project_id and self.project_id.village_ids:
            # Get project villages
            project_village_ids = self.project_id.village_ids.ids
            if self.env.user.bhuarjan_role == 'patwari':
                # For patwari, only show villages that are both in project AND assigned to user
                user_village_ids = self.env.user.village_ids.ids
                allowed_ids = list(set(project_village_ids) & set(user_village_ids))
            else:
                # For other users, show all project villages
                allowed_ids = project_village_ids
            return {'domain': {'village_id': [('id', 'in', allowed_ids)]}}
        else:
            # No project selected or project has no villages
            if self.env.user.bhuarjan_role == 'patwari':
                # For patwari, show only their assigned villages
                return {'domain': {'village_id': [('id', 'in', self.env.user.village_ids.ids)]}}
            else:
                # For other users, show no villages until project is selected
                return {'domain': {'village_id': [('id', '=', False)]}}

    def action_print_report(self):
        """Generate Form 10 report in selected format (PDF/Excel/CSV)"""
        if self.env.user.bhuarjan_role == 'patwari' and self.village_id and self.village_id.id not in self.env.user.village_ids.ids:
            raise UserError("You are not allowed to download for this village.")
        
        # Ensure UUIDs exist and are UNIQUE
        if not self.project_id.project_uuid:
            self.project_id.write({'project_uuid': str(uuid.uuid4())})
        
        # Check for duplicate village UUIDs - regenerate if found
        if not self.village_id.village_uuid:
            self.village_id.write({'village_uuid': str(uuid.uuid4())})
        else:
            # Verify this UUID is unique to this village
            duplicate_villages = self.env['bhu.village'].search([
                ('village_uuid', '=', self.village_id.village_uuid),
                ('id', '!=', self.village_id.id)
            ])
            if duplicate_villages:
                _logger.warning(f"Village {self.village_id.id} ({self.village_id.name}) has duplicate UUID! Regenerating...")
                self.village_id.write({'village_uuid': str(uuid.uuid4())})
        
        # STRICT FILTERING: Only get surveys for the EXACT project AND village
        # Verify village is correctly selected
        if not self.village_id:
            raise UserError("Please select a village.")
        if not self.project_id:
            raise UserError("Please select a project.")
        
        # Log the exact village being used
        selected_village_id = self.village_id.id
        selected_village_name = self.village_id.name
        selected_village_uuid = self.village_id.village_uuid
        selected_project_id = self.project_id.id
        selected_project_name = self.project_id.name
        
        _logger.info(f"Wizard: SELECTED Village - ID={selected_village_id}, Name='{selected_village_name}', UUID={selected_village_uuid}")
        _logger.info(f"Wizard: SELECTED Project - ID={selected_project_id}, Name='{selected_project_name}'")
        
        # Clear context completely to avoid any mixin interference (project.filter, etc.)
        # Use explicit domain with AND logic
        domain = [
            '&',  # Explicit AND operator
            ('project_id', '=', selected_project_id),
            ('village_id', '=', selected_village_id)
        ]
        
        _logger.info(f"Wizard: Search domain: {domain}")
        
        # Search with completely cleared context to avoid any mixin filters
        all_records = self.env['bhu.survey'].sudo().with_context(
            active_test=False,
            bhuarjan_current_project_id=False
        ).search(domain, order='id')
        
        # STRICT VALIDATION: Filter out any surveys that don't match exactly
        # This ensures data integrity even if there are database inconsistencies
        _logger.info(f"Wizard: Found {len(all_records)} surveys from search. Validating each one...")
        correct_records = self.env['bhu.survey']
        for survey in all_records:
            survey_village_id = survey.village_id.id
            survey_village_name = survey.village_id.name
            survey_project_id = survey.project_id.id
            
            # Strict validation - must match exactly
            if survey_project_id != selected_project_id:
                _logger.error(f"Wizard: FILTERING OUT Survey {survey.id} - Wrong Project! Expected Project ID={selected_project_id} ('{selected_project_name}'), got Project ID={survey_project_id} ('{survey.project_id.name}')")
                continue
            if survey_village_id != selected_village_id:
                _logger.error(f"Wizard: FILTERING OUT Survey {survey.id} - Wrong Village! Expected Village ID={selected_village_id} (Name='{selected_village_name}'), got Village ID={survey_village_id} (Name='{survey_village_name}')")
                continue
            
            # Survey matches - include it
            _logger.info(f"Wizard: Survey {survey.id} VALID - Project ID={survey_project_id}, Village ID={survey_village_id} (Name='{survey_village_name}')")
            correct_records |= survey
        
        if not correct_records:
            _logger.warning(f"Wizard: No valid records found for Project ID={self.project_id.id}, Village ID={self.village_id.id}")
            raise UserError(f"No records found for this project ({self.project_id.name}) and village ({self.village_id.name}).")
        
        if len(correct_records) != len(all_records):
            _logger.warning(f"Wizard: Filtered out {len(all_records) - len(correct_records)} incorrect surveys. Using {len(correct_records)} correct surveys.")
        
        _logger.info(f"Wizard: Found {len(correct_records)} correct surveys: {correct_records.ids}")
        
        all_records = correct_records

        if self.export_type == 'pdf':
            # Use the same controller route as QR code for consistency
            # Redirect to the download URL with project and village UUIDs
            project_uuid = self.project_id.project_uuid
            village_uuid = self.village_id.village_uuid
            download_url = f'/bhuarjan/form10/{project_uuid}/{village_uuid}/download'
            return {
                'type': 'ir.actions.act_url',
                'url': download_url,
                'target': 'new',
            }
        elif self.export_type == 'excel':
            return self._export_to_excel(all_records)
        elif self.export_type == 'csv':
            return self._export_to_csv(all_records)

    def _export_to_excel(self, surveys):
        """Export surveys to Excel format matching PDF structure"""
        # Use utility function to generate Excel
        export_utils = self.env['form10.export.utils']
        excel_data = export_utils.generate_form10_excel(surveys)
        
        # Generate filename using utility function
        filename = export_utils.generate_form10_filename(surveys, file_extension='xlsx')
        
        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(excel_data),
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
                    if lo.father_name:
                        name += f" पिता {lo.father_name}"
                    elif lo.spouse_name:
                        name += f" पति {lo.spouse_name}"
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
                    survey.undeveloped_tree_count if survey.undeveloped_tree_count > 0 else "नहीं",
                    survey.semi_developed_tree_count if survey.semi_developed_tree_count > 0 else "नहीं",
                    survey.fully_developed_tree_count if survey.fully_developed_tree_count > 0 else "नहीं",
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
