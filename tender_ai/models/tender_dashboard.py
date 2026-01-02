# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, timedelta
import json
import logging

_logger = logging.getLogger(__name__)


class TenderDashboard(models.TransientModel):
    _name = 'tende_ai.dashboard'
    _description = 'Tender AI Dashboard'
    
    @api.model
    def default_get(self, fields_list):
        """Create a default record to display dashboard"""
        res = super().default_get(fields_list)
        return res
    
    @api.model
    def get_dashboard_record(self):
        """Get or create a dashboard record for display"""
        # For TransientModel, we create a new record each time
        return self.create({})

    # KPI Fields - Overall Statistics
    total_jobs = fields.Integer(string='Total Jobs', compute='_compute_statistics', readonly=True)
    completed_jobs = fields.Integer(string='Completed Jobs', compute='_compute_statistics', readonly=True)
    processing_jobs = fields.Integer(string='Processing Jobs', compute='_compute_statistics', readonly=True)
    failed_jobs = fields.Integer(string='Failed Jobs', compute='_compute_statistics', readonly=True)
    success_rate = fields.Float(string='Success Rate (%)', compute='_compute_statistics', readonly=True)
    
    # Company & Bidder Statistics
    total_companies = fields.Integer(string='Total Companies', compute='_compute_statistics', readonly=True)
    total_bidders = fields.Integer(string='Total Bidders', compute='_compute_statistics', readonly=True)
    total_payments = fields.Integer(string='Total Payments', compute='_compute_statistics', readonly=True)
    total_work_experience = fields.Integer(string='Total Work Experience', compute='_compute_statistics', readonly=True)
    
    # Processing Statistics
    total_pdfs_processed = fields.Integer(string='Total PDFs Processed', compute='_compute_statistics', readonly=True)
    total_gemini_calls = fields.Integer(string='Total AI API Calls', compute='_compute_statistics', readonly=True)
    total_tokens_used = fields.Integer(string='Total Tokens Used', compute='_compute_statistics', readonly=True)
    avg_processing_time = fields.Float(string='Avg Processing Time (min)', compute='_compute_statistics', readonly=True)
    
    # Financial Statistics
    total_payment_amount = fields.Float(string='Total Payment Amount', compute='_compute_statistics', readonly=True)
    avg_payment_amount = fields.Float(string='Avg Payment Amount', compute='_compute_statistics', readonly=True)
    
    # Time-based Statistics
    jobs_today = fields.Integer(string='Jobs Today', compute='_compute_statistics', readonly=True)
    jobs_this_week = fields.Integer(string='Jobs This Week', compute='_compute_statistics', readonly=True)
    jobs_this_month = fields.Integer(string='Jobs This Month', compute='_compute_statistics', readonly=True)
    
    # Recent Activity
    last_processed_date = fields.Datetime(string='Last Processed', compute='_compute_statistics', readonly=True)
    fastest_processing_time = fields.Float(string='Fastest Processing (min)', compute='_compute_statistics', readonly=True)
    slowest_processing_time = fields.Float(string='Slowest Processing (min)', compute='_compute_statistics', readonly=True)

    @api.depends()
    def _compute_statistics(self):
        """Compute all dashboard statistics"""
        for record in self:
            # Job Statistics
            jobs = self.env['tende_ai.job'].search([])
            record.total_jobs = len(jobs)
            record.completed_jobs = len(jobs.filtered(lambda j: j.state == 'completed'))
            record.processing_jobs = len(jobs.filtered(lambda j: j.state == 'processing'))
            record.failed_jobs = len(jobs.filtered(lambda j: j.state == 'failed'))
            
            if record.total_jobs > 0:
                record.success_rate = (record.completed_jobs / record.total_jobs) * 100
            else:
                record.success_rate = 0.0
            
            # Company & Bidder Statistics
            bidders = self.env['tende_ai.bidder'].search([])
            record.total_bidders = len(bidders)
            
            # Get unique companies
            unique_companies = bidders.mapped('vendor_company_name')
            record.total_companies = len(set(unique_companies))
            
            # Payment Statistics
            payments = self.env['tende_ai.payment'].search([])
            record.total_payments = len(payments)
            
            # Calculate total payment amount (try to parse amount_inr)
            total_amount = 0.0
            valid_amounts = 0
            for payment in payments:
                try:
                    amount_str = payment.amount_inr or '0'
                    # Remove commas and currency symbols
                    amount_str = amount_str.replace(',', '').replace('₹', '').replace('INR', '').strip()
                    if amount_str:
                        amount = float(amount_str)
                        total_amount += amount
                        valid_amounts += 1
                except (ValueError, AttributeError):
                    continue
            
            record.total_payment_amount = total_amount
            record.avg_payment_amount = total_amount / valid_amounts if valid_amounts > 0 else 0.0
            
            # Work Experience Statistics
            work_exp = self.env['tende_ai.work_experience'].search([])
            record.total_work_experience = len(work_exp)
            
            # Processing Statistics from Analytics
            total_pdfs = 0
            total_calls = 0
            total_tokens = 0
            processing_times = []
            
            for job in jobs.filtered(lambda j: j.state == 'completed' and j.analytics):
                try:
                    analytics_str = job.analytics
                    if isinstance(analytics_str, str):
                        analytics = json.loads(analytics_str)
                    else:
                        analytics = analytics_str
                    
                    if isinstance(analytics, dict):
                        total_pdfs += int(analytics.get('totalValidPdfProcessed', 0) or 0)
                        total_calls += int(analytics.get('geminiCallsTotal', 0) or 0)
                        
                        tokens = analytics.get('tokensTotal', {})
                        if isinstance(tokens, dict):
                            total_tokens += int(tokens.get('totalTokens', 0) or 0)
                        
                        duration_sec = analytics.get('durationSeconds', 0) or 0
                        if duration_sec > 0:
                            processing_times.append(duration_sec / 60)  # Convert to minutes
                except (json.JSONDecodeError, ValueError, TypeError):
                    continue
            
            record.total_pdfs_processed = total_pdfs
            record.total_gemini_calls = total_calls
            record.total_tokens_used = total_tokens
            
            if processing_times:
                record.avg_processing_time = sum(processing_times) / len(processing_times)
                record.fastest_processing_time = min(processing_times)
                record.slowest_processing_time = max(processing_times)
            else:
                record.avg_processing_time = 0.0
                record.fastest_processing_time = 0.0
                record.slowest_processing_time = 0.0
            
            # Time-based Statistics
            today = datetime.now().date()
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)
            
            jobs_today_list = jobs.filtered(lambda j: j.create_date and j.create_date.date() == today)
            jobs_week_list = jobs.filtered(lambda j: j.create_date and j.create_date.date() >= week_ago)
            jobs_month_list = jobs.filtered(lambda j: j.create_date and j.create_date.date() >= month_ago)
            
            record.jobs_today = len(jobs_today_list)
            record.jobs_this_week = len(jobs_week_list)
            record.jobs_this_month = len(jobs_month_list)
            
            # Last processed date
            completed_jobs_list = jobs.filtered(lambda j: j.state == 'completed')
            if completed_jobs_list:
                last_job = max(completed_jobs_list, key=lambda j: j.write_date or j.create_date)
                record.last_processed_date = last_job.write_date or last_job.create_date
            else:
                record.last_processed_date = False

    def action_open_jobs(self):
        """Open all jobs"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tender Processing Jobs',
            'res_model': 'tende_ai.job',
            'view_mode': 'list,form',
            'domain': [],
        }

    def action_open_completed_jobs(self):
        """Open completed jobs"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Completed Jobs',
            'res_model': 'tende_ai.job',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'completed')],
        }

    def action_open_bidders(self):
        """Open all bidders"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bidders',
            'res_model': 'tende_ai.bidder',
            'view_mode': 'list,form',
            'domain': [],
        }

    def action_open_payments(self):
        """Open all payments"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payments',
            'res_model': 'tende_ai.payment',
            'view_mode': 'list,form',
            'domain': [],
        }

