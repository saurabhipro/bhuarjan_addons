from odoo import models, fields, api
from odoo.exceptions import UserError

class ReportWizard(models.TransientModel):
    _name = 'report.wizard'
    _description = 'Report Wizard'

    form_10 = fields.Boolean(string="Form 10 Download")
    village_id = fields.Many2one('bhu.village', string='Village', required=True)

    def action_print_report(self):
        # Fetch all surveys for the selected village, irrespective of status
        all_records = self.env['bhu.survey'].search([
            ('village_id', '=', self.village_id.id)
        ])
        if not all_records:
            raise UserError("No records found for your villages.")

        # Use consolidated single-PDF table report
        report_action = self.env.ref('bhuarjan.action_report_form10_bulk_table')
        return report_action.report_action(all_records)  

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}
