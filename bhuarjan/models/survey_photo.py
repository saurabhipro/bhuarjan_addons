# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
import base64
import os
from datetime import datetime

# Try to import boto3 for S3 operations
try:
    import boto3
    from botocore.exceptions import ClientError
    from botocore.config import Config
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

_logger = logging.getLogger(__name__)


class SurveyPhoto(models.Model):
    _name = 'bhu.survey.photo'
    _description = 'Survey Photo / सर्वे फोटो'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, create_date desc'

    survey_id = fields.Many2one('bhu.survey', string='Survey / सर्वे', required=True, 
                               ondelete='cascade', tracking=True)
    photo_type_id = fields.Many2one('bhu.photo.type', string='Photo Type / फोटो प्रकार', 
                                    required=False, tracking=True,
                                    help='Type of photo (e.g., Land, Well, House). Optional.')
    photo_type_name = fields.Char(related='photo_type_id.name', string='Photo Type Name', 
                                 readonly=True, store=True)
    s3_url = fields.Char(string='S3 URL / S3 यूआरएल', required=False, tracking=True,
                        index=False,  # Don't create index to avoid PostgreSQL row size limit
                        help='Full S3 URL of the uploaded photo. Will be automatically set when a file is uploaded.')
    filename = fields.Char(string='Filename / फ़ाइल नाम', tracking=True,
                          help='Original filename of the uploaded photo')
    file_size = fields.Integer(string='File Size (bytes) / फ़ाइल आकार', tracking=True,
                              help='Size of the file in bytes')
    sequence = fields.Integer(string='Sequence / क्रम', default=10, tracking=True,
                             help='Display order')
    
    # Binary field for file upload
    file_upload = fields.Binary(string='Upload File / फ़ाइल अपलोड करें', 
                                help='Select a file to upload to S3. The file will be automatically uploaded and the S3 URL will be generated.')
    
    # Computed fields
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    
    # Short filename from S3 URL for display
    s3_filename_display = fields.Char(string='S3 File / S3 फ़ाइल', 
                                      compute='_compute_s3_filename_display',
                                      store=False,
                                      help='Short filename extracted from S3 URL')

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

    @api.depends('s3_url')
    def _compute_s3_filename_display(self):
        """Extract just the filename from S3 URL for display"""
        for record in self:
            if record.s3_url:
                # Extract filename from URL (last part after /)
                filename = record.s3_url.split('/')[-1]
                # Remove query parameters if any
                filename = filename.split('?')[0]
                # Show just the filename, not the full path
                record.s3_filename_display = filename
            else:
                record.s3_filename_display = ''

    def _upload_file_to_s3(self, file_data, filename=None):
        """Helper method to upload file to S3"""
        if not HAS_BOTO3:
            raise ValidationError(_('boto3 library is not installed. Please install it to upload files to S3.'))
        
        if not self.survey_id:
            raise ValidationError(_('Please select a survey first before uploading a file.'))
        
        # Get S3 settings from settings master
        settings = self.env['bhuarjan.settings.master'].search([], limit=1)
        if not settings:
            raise ValidationError(_('S3 settings not configured. Please configure AWS settings in Bhuarjan Settings.'))
        
        if not all([settings.aws_access_key, settings.aws_secret_key, settings.s3_bucket_name, settings.aws_region]):
            raise ValidationError(_('S3 settings are incomplete. Please configure all AWS settings in Bhuarjan Settings.'))
        
        file_size = len(file_data)
        
        # Determine file extension and content type from file data or filename
        file_ext = '.jpg'
        content_type = 'image/jpeg'
        
        # Check file signature (magic bytes) to determine file type
        if file_data.startswith(b'\x89PNG\r\n\x1a\n'):
            file_ext = '.png'
            content_type = 'image/png'
        elif file_data.startswith(b'%PDF'):
            file_ext = '.pdf'
            content_type = 'application/pdf'
        elif file_data.startswith(b'\xff\xd8\xff'):
            file_ext = '.jpg'
            content_type = 'image/jpeg'
        
        # Use filename if available, otherwise generate one
        if filename:
            # Extract extension from filename if provided
            filename_ext = os.path.splitext(filename)[1]
            if filename_ext:
                file_ext = filename_ext
                # Update content type based on extension
                if file_ext.lower() == '.png':
                    content_type = 'image/png'
                elif file_ext.lower() == '.pdf':
                    content_type = 'application/pdf'
                elif file_ext.lower() in ['.jpg', '.jpeg']:
                    content_type = 'image/jpeg'
        else:
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"photo_{timestamp}{file_ext}"
        
        # Generate S3 key
        survey_id = self.survey_id.id
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        s3_key = f"surveys/{survey_id}/{timestamp}{file_ext}"
        
        # Initialize S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.aws_access_key,
            aws_secret_access_key=settings.aws_secret_key,
            region_name=settings.aws_region,
            config=Config(signature_version='s3v4', s3={'addressing_style': 'virtual'})
        )
        
        # Upload to S3
        s3_client.put_object(
            Bucket=settings.s3_bucket_name,
            Key=s3_key,
            Body=file_data,
            ContentType=content_type
        )
        
        # Generate S3 URL
        s3_url = f"https://{settings.s3_bucket_name}.s3.{settings.aws_region}.amazonaws.com/{s3_key}"
        
        return {
            's3_url': s3_url,
            'filename': filename,
            'file_size': file_size
        }

    @api.onchange('file_upload')
    def _onchange_file_upload(self):
        """Upload file to S3 when file_upload is set"""
        if not self.file_upload:
            return
        
        try:
            # Decode base64 file
            file_data = base64.b64decode(self.file_upload)
            
            # Upload to S3
            result = self._upload_file_to_s3(file_data, self.filename)
            
            # Update fields
            self.s3_url = result['s3_url']
            self.filename = result['filename']
            self.file_size = result['file_size']
            
            # Clear the binary field after upload
            self.file_upload = False
            
            _logger.info(f"File uploaded to S3: {result['s3_url']}")
            
        except ValidationError:
            raise
        except ClientError as e:
            _logger.error(f"Error uploading file to S3: {str(e)}", exc_info=True)
            raise ValidationError(_('Error uploading file to S3: %s') % str(e))
        except Exception as e:
            _logger.error(f"Unexpected error uploading file: {str(e)}", exc_info=True)
            raise ValidationError(_('Error uploading file: %s') % str(e))

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle file upload"""
        records_to_create = []
        for vals in vals_list:
            if vals.get('file_upload'):
                file_data = base64.b64decode(vals['file_upload'])
                # Create a temporary record to use the upload method
                temp_vals = vals.copy()
                temp_vals.pop('file_upload', None)  # Remove file_upload to avoid issues
                temp_record = self.new(temp_vals)
                result = temp_record._upload_file_to_s3(file_data, vals.get('filename'))
                vals['s3_url'] = result['s3_url']
                vals['filename'] = result['filename']
                vals['file_size'] = result['file_size']
                vals['file_upload'] = False  # Clear binary field
        
        return super().create(vals_list)

    def write(self, vals):
        """Override write to handle file upload"""
        if vals.get('file_upload'):
            file_data = base64.b64decode(vals['file_upload'])
            result = self._upload_file_to_s3(file_data, vals.get('filename'))
            vals['s3_url'] = result['s3_url']
            vals['filename'] = result['filename']
            vals['file_size'] = result['file_size']
            vals['file_upload'] = False  # Clear binary field
        
        return super().write(vals)

    @api.constrains('s3_url')
    def _check_s3_url_unique(self):
        """Check S3 URL uniqueness at application level (not database level to avoid index size issues)"""
        for record in self:
            if record.s3_url:
                duplicates = self.search([
                    ('s3_url', '=', record.s3_url),
                    ('id', '!=', record.id)
                ])
                if duplicates:
                    raise ValidationError(_('S3 URL must be unique! / S3 यूआरएल अद्वितीय होना चाहिए!'))
    
    # Note: Removed unique constraint on s3_url because:
    # 1. Long URLs can exceed PostgreSQL's index row size limit (8191 bytes)
    # 2. Uniqueness is now enforced at the application level via _check_s3_url_unique
    # 3. S3 URLs are already unique by design (they include timestamps and unique identifiers)
    # _sql_constraints = [
    #     ('s3_url_unique', 'unique(s3_url)', 'S3 URL must be unique! / S3 यूआरएल अद्वितीय होना चाहिए!')
    # ]

