from odoo import models, fields, api
from odoo.exceptions import UserError

class ReportWizard(models.TransientModel):
    _name = 'report.wizard'
    _description = 'Report Wizard'

    form_10 = fields.Boolean(string="Form 10 Download")

    def action_print_report(self):
        print("\n\n>>> Report Wizard Triggered <<<")
        all_records = self.env['bhu.survey'].search([
            ('village_id', 'in', self.env.user.village_ids.ids)
        ])
        if not all_records:
            raise UserError("No records found for your villages.")

        report_action = self.env.ref('bhuarjan.action_report_form10_survey')
        return report_action.report_action(all_records.ids, data={'model': 'bhu.survey'})

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}
