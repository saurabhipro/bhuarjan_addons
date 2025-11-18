# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class SurveyPhoto(models.Model):
    _name = 'bhu.survey.photo'
    _description = 'Survey Photo / सर्वे फोटो'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, create_date desc'

    survey_id = fields.Many2one('bhu.survey', string='Survey / सर्वे', required=True, 
                               ondelete='cascade', tracking=True)
    photo_type_id = fields.Many2one('bhu.photo.type', string='Photo Type / फोटो प्रकार', 
                                    required=True, tracking=True,
                                    help='Type of photo (e.g., Land, Well, House)')
    photo_type_name = fields.Char(related='photo_type_id.name', string='Photo Type Name', 
                                 readonly=True, store=True)
    s3_url = fields.Char(string='S3 URL / S3 यूआरएल', required=True, tracking=True,
                        help='Full S3 URL of the uploaded photo')
    filename = fields.Char(string='Filename / फ़ाइल नाम', tracking=True,
                          help='Original filename of the uploaded photo')
    file_size = fields.Integer(string='File Size (bytes) / फ़ाइल आकार', tracking=True,
                              help='Size of the file in bytes')
    sequence = fields.Integer(string='Sequence / क्रम', default=10, tracking=True,
                             help='Display order')
    description = fields.Text(string='Description / विवरण', tracking=True,
                            help='Additional description or notes about the photo')
    active = fields.Boolean(string='Active / सक्रिय', default=True, tracking=True)
    
    # Computed fields
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)

    @api.depends('photo_type_id', 'filename', 'survey_id')
    def _compute_display_name(self):
        for record in self:
            parts = []
            if record.photo_type_id:
                parts.append(record.photo_type_id.name)
            if record.filename:
                parts.append(record.filename)
            if record.survey_id:
                parts.append(f"Survey {record.survey_id.name or record.survey_id.id}")
            record.display_name = ' - '.join(parts) if parts else f"Photo {record.id}"

    _sql_constraints = [
        ('s3_url_unique', 'unique(s3_url)', 'S3 URL must be unique! / S3 यूआरएल अद्वितीय होना चाहिए!')
    ]

