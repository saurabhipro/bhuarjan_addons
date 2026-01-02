# -*- coding: utf-8 -*-

import base64
import os

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Bidder(models.Model):
    _name = 'tende_ai.bidder'
    _description = 'Bidder/Company Information'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'vendor_company_name'

    job_id = fields.Many2one('tende_ai.job', string='Job', required=True, ondelete='cascade', readonly=True)
    
    # Company Information
    vendor_company_name = fields.Char(string='Company Name', required=True, tracking=True, index=True)
    company_address = fields.Text(string='Company Address', tracking=True)
    email_id = fields.Char(string='Email ID', tracking=True)
    contact_person = fields.Char(string='Contact Person', tracking=True)
    contact_no = fields.Char(string='Contact Number', tracking=True)
    
    # Registration Information
    pan = fields.Char(string='PAN', tracking=True)
    gstin = fields.Char(string='GSTIN', tracking=True)
    place_of_registration = fields.Char(string='Place of Registration', tracking=True)
    offer_validity_days = fields.Char(string='Offer Validity (Days)', tracking=True)
    
    # Related Records
    payments = fields.One2many('tende_ai.payment', 'bidder_id', string='Payments')
    work_experiences = fields.One2many('tende_ai.work_experience', 'bidder_id', string='Work Experiences')
    check_ids = fields.One2many('tende_ai.bidder_check', 'bidder_id', string='Eligibility Checks', readonly=True)

    # Attachments linked via chatter / res_model+res_id
    attachment_ids = fields.Many2many(
        'ir.attachment',
        compute='_compute_attachment_ids',
        string='Attachments',
        readonly=True,
        store=False,
    )

    @api.depends('message_ids')
    def _compute_attachment_ids(self):
        # Do NOT sudo here; we want to respect attachment access rules in UI.
        Attachment = self.env['ir.attachment']
        for rec in self:
            if not rec.id:
                rec.attachment_ids = False
                continue
            rec.attachment_ids = Attachment.search([
                ('res_model', '=', 'tende_ai.bidder'),
                ('res_id', '=', rec.id),
            ])

    def action_open_attachments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Attachments'),
            'res_model': 'ir.attachment',
            'view_mode': 'list,form',
            'domain': [('res_model', '=', 'tende_ai.bidder'), ('res_id', '=', self.id)],
            'context': {
                'default_res_model': 'tende_ai.bidder',
                'default_res_id': self.id,
            },
            'target': 'current',
        }

    def action_generate_attachments(self):
        """Create one ir.attachment per extracted PDF for this bidder (downloadable)."""
        self.ensure_one()
        if not self.job_id or not self.job_id.extract_dir:
            raise ValidationError(_("No extracted folder found for this bidder's job. Please reprocess the ZIP."))

        extract_dir = self.job_id.extract_dir
        if not os.path.isdir(extract_dir):
            raise ValidationError(_("Extract directory not found on server. Please reprocess the ZIP."))

        # Find company folder in extract_dir (best effort, case-insensitive)
        wanted = (self.vendor_company_name or '').strip().lower()
        company_dir = None
        for name in os.listdir(extract_dir):
            p = os.path.join(extract_dir, name)
            if os.path.isdir(p) and name.strip().lower() == wanted:
                company_dir = p
                break
        if not company_dir:
            raise ValidationError(_("Company folder not found in extracted ZIP for this bidder."))

        pdf_paths = []
        for root, _, files in os.walk(company_dir):
            for fn in files:
                if fn.lower().endswith('.pdf') and fn.lower() != 'tender.pdf':
                    pdf_paths.append(os.path.join(root, fn))

        if not pdf_paths:
            raise ValidationError(_("No PDF files found for this bidder in the extracted folder."))

        Attachment = self.env['ir.attachment'].sudo()
        # Use relative path for deterministic names
        names = []
        for p in pdf_paths:
            try:
                rel = os.path.relpath(p, extract_dir)
            except Exception:
                rel = os.path.basename(p)
            names.append(rel)

        existing = set(Attachment.search([
            ('res_model', '=', 'tende_ai.bidder'),
            ('res_id', '=', self.id),
            ('name', 'in', names),
        ]).mapped('name'))

        to_create = []
        for p, name in zip(pdf_paths, names):
            if name in existing:
                continue
            try:
                with open(p, 'rb') as f:
                    content = f.read()
            except Exception:
                continue
            if not content:
                continue
            to_create.append({
                'name': name,
                'res_model': 'tende_ai.bidder',
                'res_id': self.id,
                'type': 'binary',
                'mimetype': 'application/pdf',
                'datas': base64.b64encode(content),
            })

        if to_create:
            Attachment.create(to_create)

        return {'type': 'ir.actions.client', 'tag': 'reload'}

