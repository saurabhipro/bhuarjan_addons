# -*- coding: utf-8 -*-

import os
import zipfile
import uuid
import threading
import traceback
import time
import logging
import base64
import json
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from psycopg2.errors import SerializationFailure

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.api import Environment

from ..services.zip_utils import safe_extract_zip, ZipSecurityError
from ..services.tender_parser import extract_tender_from_pdf_with_gemini
from ..services.company_parser import extract_company_bidder_and_payments

_logger = logging.getLogger(__name__)


class TenderJob(models.Model):
    _name = 'tende_ai.job'
    _description = 'Tender Processing Job'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Job ID', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    state = fields.Selection([
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, required=True)

    # Tender Information
    tender_id = fields.Many2one('tende_ai.tender', string='Tender', readonly=True, ondelete='cascade')
    tender_reference = fields.Char(string='Tender Reference', tracking=True)
    tender_description = fields.Text(string='Description', tracking=True)

    # File Information
    zip_file = fields.Binary(string='ZIP File', required=True)
    zip_filename = fields.Char(string='ZIP Filename')
    zip_path = fields.Char(string='ZIP Path', readonly=True)
    extract_dir = fields.Char(string='Extract Directory', readonly=True)

    # Processing Information
    companies_detected = fields.Integer(string='Companies Detected', default=0, readonly=True)
    error_message = fields.Text(string='Error Message', readonly=True)

    # Analytics
    analytics = fields.Text(string='Analytics (JSON)', readonly=True)
    analytics_html = fields.Html(string='Analytics Summary', compute='_compute_analytics_html', sanitize=False, readonly=True)
    processing_time_minutes = fields.Float(
        string='Processing Time (min)',
        compute='_compute_processing_time_minutes',
        store=True,
        readonly=True,
    )

    # Related Records
    bidders = fields.One2many('tende_ai.bidder', 'job_id', string='Bidders', readonly=True)
    eligibility_criteria = fields.One2many('tende_ai.eligibility_criteria', 'job_id', string='Eligibility Criteria', readonly=True)

    # Flat tables for Job tabs (no nesting)
    payment_ids = fields.One2many('tende_ai.payment', 'job_id', string='Payments', readonly=True)
    work_experience_ids = fields.One2many('tende_ai.work_experience', 'job_id', string='Work Experience', readonly=True)

    @api.depends('analytics')
    def _compute_analytics_html(self):
        def _esc(v):
            if v is None:
                return ''
            return (str(v)
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;"))

        for rec in self:
            data = {}
            try:
                if rec.analytics:
                    data = json.loads(rec.analytics) if isinstance(rec.analytics, str) else (rec.analytics or {})
            except Exception:
                data = {}

            if not isinstance(data, dict) or not data:
                rec.analytics_html = "<div class='text-muted'>No analytics yet.</div>"
                continue

            tokens = data.get("tokensTotal") or {}
            kpi_rows = [
                ("Job", data.get("jobId")),
                ("Companies Detected", data.get("companiesDetected")),
                ("Total PDFs Received", data.get("totalPdfReceived")),
                ("Total Valid PDFs Processed", data.get("totalValidPdfProcessed")),
                ("Gemini Calls", data.get("geminiCallsTotal")),
                ("Duration (sec)", data.get("durationSeconds")),
                ("Tokens (prompt)", (tokens.get("promptTokens") if isinstance(tokens, dict) else "")),
                ("Tokens (output)", (tokens.get("outputTokens") if isinstance(tokens, dict) else "")),
                ("Tokens (total)", (tokens.get("totalTokens") if isinstance(tokens, dict) else "")),
            ]

            kpi_html = "".join(
                f"<tr><td style='padding:6px 10px; font-weight:600; white-space:nowrap;'>{_esc(k)}</td>"
                f"<td style='padding:6px 10px;'>{_esc(v)}</td></tr>"
                for k, v in kpi_rows
            )

            per_company = data.get("perCompany") or []
            company_rows = ""
            if isinstance(per_company, list) and per_company:
                for c in per_company[:25]:
                    if not isinstance(c, dict):
                        continue
                    ct = c.get("tokens") or {}
                    company_rows += (
                        "<tr>"
                        f"<td style='padding:6px 10px;'>{_esc(c.get('companyName'))}</td>"
                        f"<td style='padding:6px 10px; text-align:right;'>{_esc(c.get('pdfCountReceived'))}</td>"
                        f"<td style='padding:6px 10px; text-align:right;'>{_esc(c.get('validPdfCount'))}</td>"
                        f"<td style='padding:6px 10px; text-align:right;'>{_esc(c.get('geminiCalls'))}</td>"
                        f"<td style='padding:6px 10px; text-align:right;'>{_esc(c.get('durationSeconds'))}</td>"
                        f"<td style='padding:6px 10px; text-align:right;'>{_esc(ct.get('totalTokens') if isinstance(ct, dict) else '')}</td>"
                        "</tr>"
                    )

            company_table = ""
            if company_rows:
                company_table = (
                    "<div style='margin-top:16px;'>"
                    "<div style='font-weight:700; margin-bottom:8px;'>Per-Company Summary</div>"
                    "<table class='table table-sm table-striped' style='width:100%; border:1px solid #ddd;'>"
                    "<thead><tr>"
                    "<th style='padding:6px 10px;'>Company</th>"
                    "<th style='padding:6px 10px; text-align:right;'>PDFs</th>"
                    "<th style='padding:6px 10px; text-align:right;'>Valid</th>"
                    "<th style='padding:6px 10px; text-align:right;'>Calls</th>"
                    "<th style='padding:6px 10px; text-align:right;'>Sec</th>"
                    "<th style='padding:6px 10px; text-align:right;'>Tokens</th>"
                    "</tr></thead>"
                    f"<tbody>{company_rows}</tbody>"
                    "</table>"
                    "</div>"
                )

            rec.analytics_html = (
                "<div>"
                "<table class='table table-sm' style='width:100%; border:1px solid #ddd;'>"
                f"<tbody>{kpi_html}</tbody>"
                "</table>"
                f"{company_table}"
                "</div>"
            )

    @api.depends('analytics')
    def _compute_processing_time_minutes(self):
        for rec in self:
            minutes = 0.0
            try:
                data = json.loads(rec.analytics) if rec.analytics else {}
                if isinstance(data, dict):
                    seconds = float(data.get('durationSeconds') or 0.0)
                    minutes = round(seconds / 60.0, 2) if seconds else 0.0
            except Exception:
                minutes = 0.0
            rec.processing_time_minutes = minutes

    def _safe_job_write(self, vals, max_retries=5, base_delay=0.15):
        """Write on job with savepoint+retry to survive SerializationFailure."""
        self.ensure_one()
        for attempt in range(max_retries):
            try:
                with self.env.cr.savepoint():
                    self.sudo().with_context(
                        tracking_disable=True,
                        mail_notrack=True,
                        mail_create_nosubscribe=True,
                    ).write(vals)
                return
            except SerializationFailure:
                if attempt >= max_retries - 1:
                    raise
                time.sleep(base_delay * (2 ** attempt))

    def _attach_company_pdfs_to_bidder(self, bidder, pdf_paths, extract_dir=None):
        """Create ir.attachment records for bidder PDFs so they can be previewed/downloaded."""
        if not bidder or not bidder.id or not pdf_paths:
            return 0

        Attachment = self.env['ir.attachment'].sudo()

        # Build deterministic names (keep company folder structure) to avoid collisions
        names = []
        for p in pdf_paths:
            try:
                rel = os.path.relpath(p, extract_dir) if extract_dir else os.path.basename(p)
            except Exception:
                rel = os.path.basename(p)
            names.append(rel)

        existing = set(Attachment.search([
            ('res_model', '=', 'tende_ai.bidder'),
            ('res_id', '=', bidder.id),
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
                'res_id': bidder.id,
                'type': 'binary',
                'mimetype': 'application/pdf',
                'datas': base64.b64encode(content),
            })

        if to_create:
            Attachment.create(to_create)
        return len(to_create)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('tende_ai.job') or _('New')
        return super(TenderJob, self).create(vals)

    def action_process_zip(self):
        """Process the uploaded ZIP file in background"""
        self.ensure_one()
        if self.state != 'draft':
            raise ValidationError(_('Only draft jobs can be processed'))

        _logger.info("=" * 80)
        _logger.info("TENDER AI: Starting processing for Job ID: %s (ID: %s)", self.name, self.id)
        _logger.info("=" * 80)

        # IMPORTANT: commit before starting background thread to avoid concurrent
        # updates on the same job row from two different cursors/transactions.
        self.write({'state': 'processing'})
        try:
            self.env.cr.commit()
        except Exception:
            # If commit fails, let Odoo handle it; background thread will still retry on serialization issues.
            self.env.cr.rollback()

        # Start background processing with proper Odoo environment
        env = self.env
        job_id = self.id
        
        def _background_process_with_env():
            # Create new environment for background thread with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                cr = None
                try:
                    cr = env.registry.cursor()
                    env_background = Environment(cr, env.uid, env.context)
                    job = env_background['tende_ai.job'].browse(job_id)
                    job._background_process()
                    cr.commit()
                    break
                except Exception as e:
                    error_str = str(e).lower()
                    error_type = type(e).__name__
                    
                    is_serialization_error = (
                        'serialize' in error_str or 
                        'concurrent' in error_str or
                        'transaction is aborted' in error_str or
                        'infailedsqltransaction' in error_str or
                        error_type == 'InFailedSqlTransaction' or
                        error_type == 'SerializationFailure'
                    )
                    
                    # Rollback on any error before retrying
                    if cr:
                        try:
                            cr.rollback()
                            _logger.debug("TENDER AI [Job %s]: Rolled back transaction after error", job_id)
                        except Exception as rollback_err:
                            _logger.warning("TENDER AI [Job %s]: Failed to rollback: %s", job_id, str(rollback_err))
                    
                    if is_serialization_error and attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 1.0  # Longer backoff for serialization errors
                        _logger.warning("TENDER AI [Job %s]: Database serialization error, retrying in %.2f seconds (attempt %d/%d)", 
                                      job_id, wait_time, attempt + 1, max_retries)
                        time.sleep(wait_time)
                        continue
                    
                    _logger.error("TENDER AI [Job %s]: Error in background process: %s", job_id, str(e), exc_info=True)
                    # Try to update state to failed
                    try:
                        with env.registry.cursor() as cr2:
                            env2 = Environment(cr2, env.uid, env.context)
                            job2 = env2['tende_ai.job'].browse(job_id)
                            job2.sudo().write({
                                'state': 'failed',
                                'error_message': f'Background processing error: {str(e)}',
                            })
                            cr2.commit()
                    except:
                        pass
                    break
                finally:
                    if cr:
                        try:
                            cr.close()
                        except Exception:
                            pass

        thread = threading.Thread(target=_background_process_with_env, daemon=True)
        thread.start()
        _logger.info("TENDER AI [Job %s]: Background processing thread started", self.name)

        return True

    def action_stop_processing(self):
        """Stop the processing of ZIP file"""
        self.ensure_one()
        if self.state != 'processing':
            raise ValidationError(_('Only processing jobs can be stopped'))

        _logger.info("=" * 80)
        _logger.info("TENDER AI: Stopping processing for Job ID: %s (ID: %s)", self.name, self.id)
        _logger.info("=" * 80)

        # Update state to cancelled
        self.sudo().write({
            'state': 'cancelled',
            'error_message': 'Processing stopped by user',
        })
        
        _logger.info("TENDER AI [Job %s]: Processing stop signal sent", self.name)
        _logger.info("TENDER AI [Job %s]: Job state updated to 'cancelled'", self.name)
        _logger.info("=" * 80)

        return True

    def action_reset_and_reprocess(self):
        """Reset job to draft and allow reprocessing"""
        self.ensure_one()
        if self.state not in ('completed', 'failed', 'cancelled'):
            raise ValidationError(_('Can only reset completed, failed, or cancelled jobs'))

        # Delete related records to start fresh
        self.env['tende_ai.tender'].sudo().search([('job_id', '=', self.id)]).unlink()
        self.env['tende_ai.bidder'].sudo().search([('job_id', '=', self.id)]).unlink()
        self.env['tende_ai.eligibility_criteria'].sudo().search([('job_id', '=', self.id)]).unlink()

        # Reset job to draft
        self.sudo().write({
            'state': 'draft',
            'tender_id': False,
            'tender_reference': '',
            'tender_description': '',
            'companies_detected': 0,
            'error_message': '',
            'analytics': '',
        })

        _logger.info("TENDER AI [Job %s]: Job reset to draft - ready for reprocessing", self.name)
        return True

    def _should_stop(self):
        """Check if processing should be stopped"""
        # Refresh the record to get latest state
        self.invalidate_recordset(['state'])
        # Check state from database
        current_state = self.read(['state'])[0]['state']
        return current_state == 'cancelled'

    def _background_process(self):
        """Background processing of ZIP file"""
        overall_t0 = time.time()
        _logger.info("TENDER AI [Job %s]: Background processing started", self.name)

        try:
            # Check if processing was stopped before starting
            if self._should_stop():
                _logger.info("TENDER AI [Job %s]: Processing cancelled before start", self.name)
                self.sudo().write({
                    'state': 'cancelled',
                    'error_message': 'Processing cancelled by user',
                })
                return
            # Save ZIP file to temporary location
            tmp_dir = os.path.join(self.env['ir.config_parameter'].sudo().get_param('tende_ai.tmp_dir', '/tmp/tende_ai'))
            os.makedirs(tmp_dir, exist_ok=True)
            _logger.info("TENDER AI [Job %s]: Using temp directory: %s", self.name, tmp_dir)

            run_id = uuid.uuid4().hex[:10]
            extract_dir = os.path.join(tmp_dir, f"extracted_{run_id}")
            os.makedirs(extract_dir, exist_ok=True)
            _logger.info("TENDER AI [Job %s]: Created extraction directory: %s", self.name, extract_dir)

            zip_path = os.path.join(tmp_dir, f"{run_id}_{self.zip_filename or 'tender.zip'}")

            # Write ZIP file - Binary fields in Odoo are stored as base64 strings in ir.attachment
            _logger.info("TENDER AI [Job %s]: Writing ZIP file to: %s", self.name, zip_path)
            _logger.info("TENDER AI [Job %s]: ZIP file data type: %s", self.name, type(self.zip_file))
            
            # Get the actual binary data from the attachment
            # Odoo Binary fields stored in ir.attachment are always base64 encoded strings
            zip_data = None
            if self.zip_file:
                raw_data = self.zip_file
                _logger.info("TENDER AI [Job %s]: Raw ZIP data type: %s, length: %s", 
                           self.name, type(raw_data), 
                           len(raw_data) if hasattr(raw_data, '__len__') else 'N/A')
                
                # Convert to string if it's bytes (Odoo sometimes returns base64 as bytes)
                if isinstance(raw_data, bytes):
                    try:
                        # Try to decode as UTF-8 first (base64 is ASCII-compatible)
                        raw_data = raw_data.decode('utf-8')
                        _logger.info("TENDER AI [Job %s]: Converted bytes to string", self.name)
                    except UnicodeDecodeError:
                        # If it's not valid UTF-8, check if it's already binary ZIP data
                        # Check for ZIP signature (PK\x03\x04)
                        if raw_data[:2] == b'PK':
                            _logger.info("TENDER AI [Job %s]: Data is already binary ZIP (starts with PK)", self.name)
                            zip_data = raw_data
                        else:
                            # Try to decode as base64 anyway
                            try:
                                raw_data = raw_data.decode('latin-1')
                                _logger.info("TENDER AI [Job %s]: Converted bytes to string using latin-1", self.name)
                            except:
                                _logger.error("TENDER AI [Job %s]: Cannot decode bytes data", self.name)
                                self.sudo().write({
                                    'state': 'failed',
                                    'error_message': 'Cannot decode ZIP file data',
                                })
                                return
                
                # Now decode base64 if we have a string
                if isinstance(raw_data, str):
                    # Check if it looks like base64 (starts with common base64 chars)
                    if raw_data.startswith('UEs') or len(raw_data) > 100:
                        try:
                            # Decode base64 string
                            zip_data = base64.b64decode(raw_data)
                            _logger.info("TENDER AI [Job %s]: Decoded base64 ZIP data (decoded size: %d bytes)", 
                                        self.name, len(zip_data))
                        except Exception as e:
                            _logger.error("TENDER AI [Job %s]: Failed to decode base64: %s", self.name, str(e))
                            self.sudo().write({
                                'state': 'failed',
                                'error_message': f'Failed to decode ZIP file data: {str(e)}',
                            })
                            return
                    else:
                        # Doesn't look like base64, might be binary data as string
                        _logger.warning("TENDER AI [Job %s]: String data doesn't look like base64, treating as binary", self.name)
                        zip_data = raw_data.encode('latin-1')
                elif zip_data is None:
                    # Already set to binary data above
                    pass
            
            if not zip_data:
                _logger.error("TENDER AI [Job %s]: ZIP file data is empty or None", self.name)
                self.sudo().write({
                    'state': 'failed',
                    'error_message': 'ZIP file data is empty',
                })
                return
            
            # Write the binary data to file
            with open(zip_path, 'wb') as f:
                f.write(zip_data)
            
            zip_size = os.path.getsize(zip_path)
            _logger.info("TENDER AI [Job %s]: ZIP file written successfully (Size: %.2f MB, %d bytes)", 
                        self.name, zip_size / (1024 * 1024), zip_size)

            # Validate ZIP file
            if zip_size == 0:
                _logger.error("TENDER AI [Job %s]: Written ZIP file is empty", self.name)
                self.sudo().write({
                    'state': 'failed',
                    'error_message': 'ZIP file is empty after writing',
                })
                return
            
            # Read first few bytes to verify it's a valid ZIP
            with open(zip_path, 'rb') as f:
                first_bytes = f.read(10)
            
            # Check for ZIP signature (PK\x03\x04)
            if first_bytes[:2] != b'PK':
                _logger.error("TENDER AI [Job %s]: File does not have ZIP signature", self.name)
                _logger.error("TENDER AI [Job %s]: File size: %d bytes, First 10 bytes (hex): %s", 
                            self.name, zip_size, first_bytes.hex())
                _logger.error("TENDER AI [Job %s]: First 10 bytes (repr): %s", self.name, repr(first_bytes))
                _logger.error("TENDER AI [Job %s]: Expected ZIP signature: PK (0x504B), got: %s", 
                            self.name, first_bytes[:2].hex())
                
                # If it looks like base64, suggest the issue
                if first_bytes.startswith(b'UEs'):
                    _logger.error("TENDER AI [Job %s]: File appears to be base64 encoded (starts with UEs)", self.name)
                    _logger.error("TENDER AI [Job %s]: This suggests the base64 decoding failed", self.name)
                
                self.sudo().write({
                    'state': 'failed',
                    'error_message': 'Uploaded file is not a valid ZIP file (missing ZIP signature)',
                })
                return
                
            if not zipfile.is_zipfile(zip_path):
                _logger.error("TENDER AI [Job %s]: zipfile.is_zipfile() returned False", self.name)
                _logger.error("TENDER AI [Job %s]: File size: %d bytes, First 10 bytes (hex): %s", 
                            self.name, zip_size, first_bytes.hex())
                self.sudo().write({
                    'state': 'failed',
                    'error_message': 'Uploaded file is not a valid ZIP file',
                })
                return

            # Store paths (only write once)
            self._safe_job_write({
                'zip_path': zip_path,
                'extract_dir': extract_dir,
            })

            # Safe ZIP extract
            _logger.info("TENDER AI [Job %s]: Extracting ZIP file to: %s", self.name, extract_dir)
            try:
                safe_extract_zip(zip_path, extract_dir)
                _logger.info("TENDER AI [Job %s]: ZIP file extracted successfully", self.name)
            except ZipSecurityError as e:
                _logger.error("TENDER AI [Job %s]: ZIP security error: %s", self.name, str(e))
                self.write({
                    'state': 'failed',
                    'error_message': f'Unsafe ZIP: {str(e)}',
                })
                return

            # Locate tender.pdf
            _logger.info("TENDER AI [Job %s]: Searching for tender.pdf in extracted files", self.name)
            tender_pdf_path = None
            for root, _, files in os.walk(extract_dir):
                for fn in files:
                    if fn.lower() == "tender.pdf":
                        tender_pdf_path = os.path.join(root, fn)
                        break
                if tender_pdf_path:
                    break

            if not tender_pdf_path:
                _logger.error("TENDER AI [Job %s]: tender.pdf not found inside zip", self.name)
                self.sudo().write({
                    'state': 'failed',
                    'error_message': 'tender.pdf not found inside zip',
                })
                return
            
            _logger.info("TENDER AI [Job %s]: Found tender.pdf at: %s", self.name, tender_pdf_path)

            # Check if processing was stopped
            if self._should_stop():
                _logger.info("TENDER AI [Job %s]: Processing cancelled before tender extraction", self.name)
                self.sudo().write({
                    'state': 'cancelled',
                    'error_message': 'Processing cancelled by user',
                })
                return

            # 1️⃣ Tender extraction
            model = os.getenv("GEMINI_TENDER_MODEL", "gemini-3-flash-preview")
            _logger.info("TENDER AI [Job %s]: Starting tender extraction with Gemini API", self.name)
            _logger.info("TENDER AI [Job %s]:   - Model: %s", self.name, model)
            _logger.info("TENDER AI [Job %s]:   - PDF Path: %s", self.name, tender_pdf_path)
            _logger.info("TENDER AI [Job %s]: Calling Gemini API: extract_tender_from_pdf_with_gemini()", self.name)
            tender_start_time = time.time()
            tender_data = extract_tender_from_pdf_with_gemini(tender_pdf_path, model=model, env=self.env) or {}
            tender_duration = time.time() - tender_start_time
            _logger.info("TENDER AI [Job %s]: ✓ Gemini API call completed for tender extraction", self.name)
            _logger.info("TENDER AI [Job %s]:   - Duration: %.2f seconds", self.name, tender_duration)
            
            # Log tender analytics if available
            tender_analytics = tender_data.get("tenderAnalytics") or {}
            if isinstance(tender_analytics, dict):
                tokens = tender_analytics.get("tokens") or {}
                _logger.info("TENDER AI [Job %s]:   - Tokens used: %s", self.name, tokens)

            # Check if processing was stopped after tender extraction
            if self._should_stop():
                _logger.info("TENDER AI [Job %s]: Processing cancelled after tender extraction", self.name)
                self.sudo().write({
                    'state': 'cancelled',
                    'error_message': 'Processing cancelled by user',
                })
                return

            # Create tender record
            tender = self.env['tende_ai.tender'].sudo().create({
                'job_id': self.id,
                'state': 'draft',
                'department_name': tender_data.get('departmentName', ''),
                'tender_id': tender_data.get('tenderId', ''),
                'ref_no': tender_data.get('refNo', ''),
                'tender_creator': tender_data.get('tenderCreator', ''),
                'procurement_category': tender_data.get('procurementCategory', ''),
                'tender_type': tender_data.get('tenderType', ''),
                'organization_hierarchy': tender_data.get('organizationHierarchy', ''),
                'estimated_value_inr': tender_data.get('estimatedValueINR', ''),
                'tender_currency': tender_data.get('tenderCurrency', ''),
                'bidding_currency': tender_data.get('biddingCurrency', ''),
                'offer_validity_days': tender_data.get('offerValidityDays', ''),
                'previous_tender_no': tender_data.get('previousTenderNo', ''),
                'published_on': tender_data.get('publishedOn', ''),
                'bid_submission_start': tender_data.get('bidSubmissionStart', ''),
                'bid_submission_end': tender_data.get('bidSubmissionEnd', ''),
                'tender_opened_on': tender_data.get('tenderOpenedOn', ''),
                'description': tender_data.get('description', ''),
                'nit': tender_data.get('nit', ''),
                'analytics': str(tender_data.get('tenderAnalytics', {})),
                'details_html': tender_data.get('description', '') or '',
            })

            # Batch create eligibility criteria
            criteria_list = tender_data.get('bidderEligibilityCriteria', [])
            if criteria_list:
                criteria_records = []
                for crit in criteria_list:
                    criteria_records.append({
                        'job_id': self.id,
                        'tender_id': tender.id,
                        'sl_no': crit.get('slNo', ''),
                        'criteria': crit.get('criteria', ''),
                        'supporting_document': crit.get('supportingDocument', ''),
                    })
                if criteria_records:
                    self.env['tende_ai.eligibility_criteria'].sudo().create(criteria_records)

            # Update job with tender info
            self._safe_job_write({
                'tender_id': tender.id,
                'tender_reference': tender_data.get('refNo', ''),
                'tender_description': tender_data.get('description', ''),
            })
            # Try to commit so tender info appears immediately in UI (but don't fail if it conflicts)
            try:
                self.env.cr.commit()
                _logger.info("TENDER AI [Job %s]: ✓ Tender information saved and committed - visible in UI", self.name)
            except Exception as commit_err:
                # If commit fails due to serialization, continue - data will be visible on next commit
                _logger.debug("TENDER AI [Job %s]: Commit skipped (will commit later): %s", self.name, str(commit_err))
                self.env.cr.rollback()

            # 2️⃣ Company parsing
            _logger.info("TENDER AI [Job %s]: Collecting company folders from extracted ZIP", self.name)
            jobs = self._collect_company_jobs(extract_dir)
            # Update companies count (only write once)
            self._safe_job_write({'companies_detected': len(jobs)})
            _logger.info("TENDER AI [Job %s]: Found %d company folder(s) to process", self.name, len(jobs))

            company_workers = int(os.getenv("COMPANY_WORKERS", "4"))
            pdf_workers = int(os.getenv("PDF_WORKERS_PER_COMPANY", "5"))
            model = os.getenv("GEMINI_COMPANY_MODEL", "gemini-3-flash-preview")
            _logger.info("TENDER AI [Job %s]: Processing configuration - Company Workers: %d, PDF Workers: %d, Model: %s", 
                        self.name, company_workers, pdf_workers, model)

            bidders = []
            payments_by_company = []
            work_experience_by_company = []

            # Analytics aggregation
            total_pdfs_received = 0
            total_valid_pdfs = 0
            total_gemini_calls = 0
            total_tokens = {"promptTokens": 0, "outputTokens": 0, "totalTokens": 0}
            per_company_analytics = []

            # Include tender tokens/calls first
            tender_analytics = tender_data.get("tenderAnalytics") or {}
            tender_tokens = (tender_analytics.get("tokens") or {}) if isinstance(tender_analytics, dict) else {}
            total_tokens = self._merge_tokens_total(total_tokens, tender_tokens)
            total_gemini_calls += 1

            if jobs:
                for j in jobs:
                    total_pdfs_received += len(j.get("pdf_paths") or [])
                _logger.info("TENDER AI [Job %s]: Total PDFs to process across all companies: %d", 
                            self.name, total_pdfs_received)

                _logger.info("TENDER AI [Job %s]: Starting parallel company processing", self.name)
                _logger.info("TENDER AI [Job %s]:   - Companies: %d", self.name, len(jobs))
                _logger.info("TENDER AI [Job %s]:   - Company Workers: %d", self.name, company_workers)
                _logger.info("TENDER AI [Job %s]:   - PDF Workers per Company: %d", self.name, pdf_workers)
                _logger.info("TENDER AI [Job %s]:   - Model: %s", self.name, model)
                
                # Check if processing was stopped before company processing
                if self._should_stop():
                    _logger.info("TENDER AI [Job %s]: Processing cancelled before company processing", self.name)
                    self.sudo().write({
                        'state': 'cancelled',
                        'error_message': 'Processing cancelled by user',
                    })
                    return
                
                with ThreadPoolExecutor(max_workers=company_workers) as ex:
                    futures = [
                        ex.submit(self._process_one_company, job, model, pdf_workers)
                        for job in jobs
                    ]

                    completed = 0
                    for fut in as_completed(futures):
                        # Check if processing was stopped
                        if self._should_stop():
                            _logger.info("TENDER AI [Job %s]: Processing cancelled during company processing", self.name)
                            _logger.info("TENDER AI [Job %s]: Cancelling remaining company processing tasks", self.name)
                            # Cancel remaining futures
                            for remaining_fut in futures:
                                if not remaining_fut.done():
                                    remaining_fut.cancel()
                            self.sudo().write({
                                'state': 'cancelled',
                                'error_message': 'Processing cancelled by user',
                            })
                            return
                        
                        try:
                            completed += 1
                            result = fut.result() or {}
                            company_name = result.get("companyName", "Unknown")
                            _logger.info("TENDER AI [Job %s]: ✓ Completed processing company %d/%d: %s", 
                                        self.name, completed, len(jobs), company_name)

                            # Prepare batch records for efficient database writes
                            bidder_data = result.get("bidder") or {}
                            payments = result.get("payments") or []
                            work_exp = result.get("work_experience") or []
                            pdf_paths = result.get("_pdf_paths") or []
                            
                            # Check if bidder already exists for this job (by company name)
                            vendor_company_name = bidder_data.get('vendorCompanyName', '') or company_name
                            existing_bidder = self.env['tende_ai.bidder'].sudo().search([
                                ('job_id', '=', self.id),
                                ('vendor_company_name', '=', vendor_company_name)
                            ], limit=1)
                            
                            if existing_bidder:
                                # Update existing bidder
                                _logger.debug("TENDER AI [Job %s]: Updating existing bidder: %s", 
                                            self.name, vendor_company_name)
                                existing_bidder.write({
                                    'company_address': bidder_data.get('companyAddress', '') or existing_bidder.company_address,
                                    'email_id': bidder_data.get('emailId', '') or existing_bidder.email_id,
                                    'contact_person': bidder_data.get('contactPerson', '') or existing_bidder.contact_person,
                                    'contact_no': bidder_data.get('contactNo', '') or existing_bidder.contact_no,
                                    'pan': bidder_data.get('pan', '') or existing_bidder.pan,
                                    'gstin': bidder_data.get('gstin', '') or existing_bidder.gstin,
                                    'place_of_registration': bidder_data.get('placeOfRegistration', '') or existing_bidder.place_of_registration,
                                    'offer_validity_days': bidder_data.get('offerValidityDays', '') or existing_bidder.offer_validity_days,
                                })
                                bidder = existing_bidder
                            else:
                                # Create new bidder record
                                bidder = self.env['tende_ai.bidder'].sudo().create({
                                    'job_id': self.id,
                                    'vendor_company_name': vendor_company_name,
                                    'company_address': bidder_data.get('companyAddress', ''),
                                    'email_id': bidder_data.get('emailId', ''),
                                    'contact_person': bidder_data.get('contactPerson', ''),
                                    'contact_no': bidder_data.get('contactNo', ''),
                                    'pan': bidder_data.get('pan', ''),
                                    'gstin': bidder_data.get('gstin', ''),
                                    'place_of_registration': bidder_data.get('placeOfRegistration', ''),
                                    'offer_validity_days': bidder_data.get('offerValidityDays', ''),
                                })
                                _logger.info("TENDER AI [Job %s]: ✓ Created bidder record: %s", self.name, vendor_company_name)

                            # Attach all extracted bidder PDFs (so user can preview/download on bidder form)
                            attached_count = 0
                            try:
                                attached_count = self._attach_company_pdfs_to_bidder(
                                    bidder, pdf_paths, extract_dir=getattr(self, 'extract_dir', None)
                                )
                            except Exception:
                                attached_count = 0
                            if attached_count:
                                _logger.info(
                                    "TENDER AI [Job %s]: ✓ Attached %d PDF(s) to bidder: %s",
                                    self.name, attached_count, vendor_company_name
                                )

                            # Batch create payment records (check for duplicates by transaction_id)
                            if payments:
                                payment_records = []
                                existing_transaction_ids = set(
                                    self.env['tende_ai.payment'].sudo().search([
                                        ('bidder_id', '=', bidder.id)
                                    ]).mapped('transaction_id')
                                )
                                
                                for payment_data in payments:
                                    transaction_id = payment_data.get('transactionId', '').strip()
                                    # Skip if payment with same transaction_id already exists
                                    if transaction_id and transaction_id in existing_transaction_ids:
                                        continue
                                    
                                    payment_records.append({
                                        'bidder_id': bidder.id,
                                        'vendor': payment_data.get('vendor', ''),
                                        'payment_mode': payment_data.get('paymentMode', ''),
                                        'bank_name': payment_data.get('bankName', ''),
                                        'transaction_id': transaction_id,
                                        'amount_inr': payment_data.get('amountINR', ''),
                                        'transaction_date': payment_data.get('transactionDate', ''),
                                        'status': payment_data.get('status', ''),
                                    })
                                if payment_records:
                                    self.env['tende_ai.payment'].sudo().create(payment_records)
                                    _logger.info("TENDER AI [Job %s]: ✓ Created %d payment record(s) for bidder: %s", 
                                                self.name, len(payment_records), vendor_company_name)

                            # Batch create work experience records (check for duplicates)
                            if work_exp:
                                work_records = []
                                # Get existing work experiences for deduplication
                                existing_work = self.env['tende_ai.work_experience'].sudo().search([
                                    ('bidder_id', '=', bidder.id)
                                ])
                                existing_work_keys = set()
                                for ew in existing_work:
                                    key = (
                                        (ew.name_of_work or '').lower().strip(),
                                        (ew.employer or '').lower().strip(),
                                        (ew.location or '').lower().strip(),
                                        (ew.date_of_start or '').lower().strip(),
                                    )
                                    existing_work_keys.add(key)
                                
                                for work_data in work_exp:
                                    # Create deduplication key
                                    work_key = (
                                        (work_data.get('nameOfWork', '') or '').lower().strip(),
                                        (work_data.get('employer', '') or '').lower().strip(),
                                        (work_data.get('location', '') or '').lower().strip(),
                                        (work_data.get('dateOfStart', '') or '').lower().strip(),
                                    )
                                    # Skip if duplicate
                                    if work_key in existing_work_keys:
                                        continue
                                    
                                    work_records.append({
                                        'bidder_id': bidder.id,
                                        'vendor_company_name': work_data.get('vendorCompanyName', ''),
                                        'name_of_work': work_data.get('nameOfWork', ''),
                                        'employer': work_data.get('employer', ''),
                                        'location': work_data.get('location', ''),
                                        'contract_amount_inr': work_data.get('contractAmountINR', ''),
                                        'date_of_start': work_data.get('dateOfStart', ''),
                                        'date_of_completion': work_data.get('dateOfCompletion', ''),
                                        'completion_certificate': work_data.get('completionCertificate', ''),
                                        'attachment': work_data.get('attachment', ''),
                                    })
                                if work_records:
                                    self.env['tende_ai.work_experience'].sudo().create(work_records)
                                    _logger.info("TENDER AI [Job %s]: ✓ Created %d work experience record(s) for bidder: %s", 
                                                self.name, len(work_records), vendor_company_name)
                            
                            # Log completion of bidder processing
                            payment_count = len(payments) if payments else 0
                            work_exp_count = len(work_exp) if work_exp else 0
                            _logger.info("TENDER AI [Job %s]: ✓ Bidder data processed - Company: %s, Payments: %d, Work Experience: %d", 
                                        self.name, vendor_company_name, payment_count, work_exp_count)
                            
                            # Try to commit after each company (but don't fail if it conflicts)
                            # Commit after each bidder to show data immediately
                            try:
                                self.env.cr.commit()
                                _logger.info("TENDER AI [Job %s]: ✓ Committed bidder data - %s is now visible in UI", self.name, vendor_company_name)
                            except Exception as commit_err:
                                # If commit fails, continue - data will be visible on next commit
                                _logger.debug("TENDER AI [Job %s]: Commit skipped (will commit later): %s", self.name, str(commit_err))
                                self.env.cr.rollback()

                            c_an = result.get("analytics") or {}
                            if isinstance(c_an, dict):
                                per_company_analytics.append(c_an)
                                total_valid_pdfs += int(c_an.get("validPdfCount") or 0)
                                total_gemini_calls += int(c_an.get("geminiCalls") or 0)

                                c_tokens = c_an.get("tokens") or {}
                                if isinstance(c_tokens, dict):
                                    total_tokens = self._merge_tokens_total(total_tokens, c_tokens)

                        except Exception:
                            continue

            # Final analytics
            overall_t1 = time.time()
            analytics = {
                "jobId": self.name,
                "durationMs": int((overall_t1 - overall_t0) * 1000),
                "durationSeconds": round(overall_t1 - overall_t0, 3),
                "companiesDetected": len(jobs),
                "totalPdfReceived": total_pdfs_received,
                "totalValidPdfProcessed": total_valid_pdfs,
                "geminiCallsTotal": total_gemini_calls,
                "tokensTotal": total_tokens,
                "perCompany": per_company_analytics,
            }

            # ✅ Completed
            overall_duration = time.time() - overall_t0
            _logger.info("TENDER AI [Job %s]: ✓ Processing completed successfully", self.name)
            _logger.info("TENDER AI [Job %s]:   - Total Duration: %.2f seconds (%.2f minutes)", 
                        self.name, overall_duration, overall_duration / 60)
            _logger.info("TENDER AI [Job %s]:   - Companies Processed: %d", self.name, len(jobs))
            _logger.info("TENDER AI [Job %s]:   - Total PDFs Processed: %d", self.name, total_valid_pdfs)
            _logger.info("TENDER AI [Job %s]:   - Total Gemini API Calls: %d", self.name, total_gemini_calls)
            _logger.info("TENDER AI [Job %s]:   - Total Tokens Used: %s", self.name, total_tokens)
            _logger.info("=" * 80)
            
            # Serialize analytics to JSON string properly
            try:
                analytics_json = json.dumps(analytics, ensure_ascii=False)
            except Exception as e:
                _logger.warning("TENDER AI [Job %s]: Failed to serialize analytics to JSON, using str(): %s", 
                              self.name, str(e))
                analytics_json = str(analytics)
            
            # Truncate analytics if too large to avoid database issues
            if len(analytics_json) > 50000:  # ~50KB limit
                simplified_analytics = analytics.copy()
                simplified_analytics['perCompany'] = [
                    {
                        'companyName': c.get('companyName', ''),
                        'durationMs': c.get('durationMs', 0),
                        'pdfCountReceived': c.get('pdfCountReceived', 0),
                        'validPdfCount': c.get('validPdfCount', 0),
                        'geminiCalls': c.get('geminiCalls', 0),
                        'tokens': c.get('tokens', {}),
                    }
                    for c in per_company_analytics
                ]
                analytics_json = json.dumps(simplified_analytics, ensure_ascii=False)
            
            # Write final state and analytics together (single write is faster)
            self.sudo().write({
                'state': 'completed',
                'error_message': '',
                'analytics': analytics_json,
            })

        except Exception as e:
            error_msg = f"{str(e)}\n{traceback.format_exc()[:4000]}"
            _logger.error("TENDER AI [Job %s]: ✗ Processing failed with error", self.name)
            _logger.error("TENDER AI [Job %s]:   - Error: %s", self.name, str(e))
            _logger.error("TENDER AI [Job %s]:   - Traceback: %s", self.name, traceback.format_exc())
            _logger.info("=" * 80)
            
            self.sudo().write({
                'state': 'failed',
                'error_message': error_msg,
            })

    def _is_company_folder(self, name: str) -> bool:
        """Check if folder name represents a company"""
        if not name:
            return False
        if name.startswith("."):
            return False
        if name.lower() == "__macosx":
            return False
        return True

    def _collect_company_jobs(self, extract_dir: str) -> list:
        """
        Collect company folders and their PDF files.
        Structure expected:
          extract_dir/
            tender.pdf
            CompanyA/ (pdfs...)
            CompanyB/ (pdfs...)
        """
        jobs = []

        for name in os.listdir(extract_dir):
            if not self._is_company_folder(name):
                continue

            company_dir = os.path.join(extract_dir, name)
            if not os.path.isdir(company_dir):
                continue

            company_name = name.strip()

            pdf_paths = []
            for root, _, files in os.walk(company_dir):
                for fn in files:
                    if not fn.lower().endswith(".pdf"):
                        continue
                    if fn.lower() == "tender.pdf":
                        continue
                    pdf_paths.append(os.path.join(root, fn))

            if not pdf_paths:
                continue

            jobs.append({"company_name": company_name, "pdf_paths": pdf_paths})

        return jobs

    def _process_one_company(self, job: dict, model: str, pdf_workers: int) -> dict:
        """Process one company folder"""
        company_name = job.get("company_name", "")
        pdf_paths = job.get("pdf_paths", [])
        
        _logger.info("TENDER AI [Job %s]: Processing company: %s (%d PDFs)", 
                    self.name, company_name, len(pdf_paths))
        _logger.info("TENDER AI [Job %s]:   - Calling Gemini API: extract_company_bidder_and_payments()", 
                    self.name)
        _logger.info("TENDER AI [Job %s]:   - Company: %s", self.name, company_name)
        _logger.info("TENDER AI [Job %s]:   - PDFs: %d", self.name, len(pdf_paths))
        _logger.info("TENDER AI [Job %s]:   - Model: %s", self.name, model)
        _logger.info("TENDER AI [Job %s]:   - Workers: %d", self.name, pdf_workers)
        
        company_start_time = time.time()
        result = extract_company_bidder_and_payments(
            company_name=company_name,
            pdf_paths=pdf_paths,
            model=model,
            max_workers=pdf_workers,
            env=self.env,
        )
        # Keep original PDF paths so we can attach extracted files to the bidder record
        if isinstance(result, dict):
            result["_pdf_paths"] = pdf_paths
        company_duration = time.time() - company_start_time
        
        # Log company analytics
        analytics = result.get("analytics") or {}
        if isinstance(analytics, dict):
            gemini_calls = analytics.get("geminiCalls", 0)
            valid_pdfs = analytics.get("validPdfCount", 0)
            tokens = analytics.get("tokens") or {}
            _logger.info("TENDER AI [Job %s]: ✓ Company processing completed: %s", 
                        self.name, company_name)
            _logger.info("TENDER AI [Job %s]:   - Duration: %.2f seconds", self.name, company_duration)
            _logger.info("TENDER AI [Job %s]:   - Gemini API Calls: %d", self.name, gemini_calls)
            _logger.info("TENDER AI [Job %s]:   - Valid PDFs Processed: %d", self.name, valid_pdfs)
            _logger.info("TENDER AI [Job %s]:   - Tokens Used: %s", self.name, tokens)

        return {
            "companyName": company_name,
            "bidder": result.get("bidder") or {},
            "payments": result.get("payments") or [],
            "work_experience": result.get("work_experience") or [],
            "analytics": result.get("analytics") or {},
        }

    def _safe_write(self, vals):
        """
        Simple write to database. Errors will be handled at job level.
        """
        try:
            self.sudo().write(vals)
        except Exception as e:
            # Log but don't retry - let job-level retry handle it
            _logger.warning("TENDER AI [Job %s]: Write failed: %s", self.name, str(e))
            raise

    def _merge_tokens_total(self, total: dict, incoming: dict) -> dict:
        """Merge token counts"""
        if not isinstance(total, dict):
            total = {"promptTokens": 0, "outputTokens": 0, "totalTokens": 0}
        if not isinstance(incoming, dict):
            return total

        def _to_int(v):
            try:
                return int(v)
            except Exception:
                return 0

        total["promptTokens"] += _to_int(incoming.get("promptTokens"))
        total["outputTokens"] += _to_int(incoming.get("outputTokens"))
        total["totalTokens"] += _to_int(incoming.get("totalTokens"))
        return total

