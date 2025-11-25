from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

try:
    import xlsxwriter
    HAS_XLSXWRITER = True
except ImportError:
    HAS_XLSXWRITER = False


class UserReportWizard(models.TransientModel):
    _name = 'user.report.wizard'
    _description = 'User Report Excel Export Wizard'

    def _export_users_excel(self):
        """Generate Excel report for all users with their details"""
        if not HAS_XLSXWRITER:
            raise UserError(_('xlsxwriter library is not installed. Please install it to export Excel files.'))

        # Create a file-like object in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Users Report')

        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#366092',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
        })
        
        cell_format = workbook.add_format({
            'align': 'left',
            'valign': 'top',
            'border': 1,
            'text_wrap': True,
        })

        # Set column widths
        worksheet.set_column('A:A', 8)   # Sr No
        worksheet.set_column('B:B', 25)   # Patwari Name
        worksheet.set_column('C:C', 15)   # Mobile No
        worksheet.set_column('D:D', 20)   # Department
        worksheet.set_column('E:E', 30)   # Projects
        worksheet.set_column('F:F', 20)   # Tehsil
        worksheet.set_column('G:G', 20)   # Subdivision
        worksheet.set_column('H:H', 30)   # Village

        # Write headers
        headers = ['Sr No', 'Patwari Name', 'Mobile No', 'Department', 'Projects', 'Tehsil', 'Subdivision', 'Village']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # Get all users (or filter by patwari role if needed)
        users = self.env['res.users'].sudo().search([], order='name')
        
        row = 1
        for user in users:
            # Sr No
            worksheet.write(row, 0, row, cell_format)
            
            # Patwari Name
            worksheet.write(row, 1, user.name or '', cell_format)
            
            # Mobile No
            worksheet.write(row, 2, user.mobile or '', cell_format)
            
            # Projects - Get projects that have villages matching user's villages
            projects = []
            departments = set()
            if user.village_ids:
                user_village_ids = user.village_ids.ids
                projects = self.env['bhu.project'].sudo().search([
                    ('village_ids', 'in', user_village_ids)
                ])
                # Get departments that have these projects
                if projects:
                    project_ids = projects.ids
                    depts = self.env['bhu.department'].sudo().search([
                        ('project_ids', 'in', project_ids)
                    ])
                    departments = {dept.name for dept in depts}
            
            # Department - Display all departments
            department_str = '\n'.join(sorted(departments)) if departments else ''
            worksheet.write(row, 3, department_str, cell_format)
            project_names = '\n'.join([p.name for p in projects]) if projects else ''
            worksheet.write(row, 4, project_names, cell_format)
            
            # Tehsil - Get unique tehsils from user's villages
            tehsils = set()
            if user.village_ids:
                for village in user.village_ids:
                    if village.tehsil_id:
                        tehsils.add(village.tehsil_id.name)
            tehsil_str = '\n'.join(sorted(tehsils)) if tehsils else ''
            worksheet.write(row, 5, tehsil_str, cell_format)
            
            # Subdivision - Get unique subdivisions from user's villages
            subdivisions = set()
            if user.village_ids:
                for village in user.village_ids:
                    if village.sub_division_id:
                        subdivisions.add(village.sub_division_id.name)
            subdivision_str = '\n'.join(sorted(subdivisions)) if subdivisions else ''
            worksheet.write(row, 6, subdivision_str, cell_format)
            
            # Village - Get all villages assigned to user
            village_names = '\n'.join([v.name for v in user.village_ids]) if user.village_ids else ''
            worksheet.write(row, 7, village_names, cell_format)
            
            row += 1

        workbook.close()
        output.seek(0)
        return base64.b64encode(output.read()).decode()

    def action_export_excel(self):
        """Export users report to Excel"""
        try:
            excel_data = self._export_users_excel()
            filename = f'Users_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            
            # Create attachment
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': excel_data,
                'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'res_model': 'res.users',
            })
            
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            }
        except Exception as e:
            _logger.error(f"Error exporting users report: {str(e)}", exc_info=True)
            raise UserError(_('Error generating Excel report: %s') % str(e))

