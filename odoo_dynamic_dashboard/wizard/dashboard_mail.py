# -*- coding: utf-8 -*-
##############################################################################
#
#    In2IT Technologies Pvt. Ltd
#    Copyright (C) 2025 (https://www.in2ittech.com)
#
##############################################################################
from odoo import fields, models


class DashboardMail(models.TransientModel):
    _name = 'dashboard.mail'
    _description = 'Dashboard Mail'

    user_ids = fields.Many2many('res.users', string="Users",
                                domain="[('id','!=', uid)]",
                                help="Select User")
    base64code = fields.Char(string='Base 64', help='Base64 Code of the pdf')

    def send_mail(self):
        """
        Function for sending mail to the selected users
        """
        for user in self.user_ids:
            mail_content = (
                           'Hi %s, <br/> '
                           'I hope this mail finds you well. I am pleased to share the <b>Dashboard Report</b> with you.<br/>'
                           'Please find the attachment<br/>') % user.name
            mail_values = {
                'subject': 'Dashboard Report',
                'author_id': self.env.user.partner_id.id,
                'body_html': mail_content,
                'email_to': user.email,
            }
            mail_id = self.env['mail.mail'].create(mail_values)
            attachment_values = {
                'name': 'Dashboard.pdf',
                'datas': self.base64code,
                'type': 'binary',
                'res_model': 'mail.mail',
                'res_id': mail_id.id,
            }
            attachment_id = self.env['ir.attachment'].create(attachment_values)
            mail_id.write({
                'attachment_ids': [(4, attachment_id.id)]
            })
            mail_id.send()

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def cancel_mail(self):
        """
        Function for refreshing the page while clicking cancel
        """
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
