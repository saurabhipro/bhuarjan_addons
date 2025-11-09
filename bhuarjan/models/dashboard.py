# -*- coding: utf-8 -*-

from odoo import models, fields, api


class BhuarjanDashboard(models.TransientModel):
    _name = 'bhuarjan.dashboard'
    _description = 'Bhuarjan Dashboard'
    

    # Master Data Counts
    total_districts = fields.Integer(string='Total Districts', readonly=True, default=0)
    total_sub_divisions = fields.Integer(string='Total Sub Divisions', readonly=True, default=0)
    total_tehsils = fields.Integer(string='Total Tehsils', readonly=True, default=0)
    total_circles = fields.Integer(string='Total Circles', readonly=True, default=0)
    total_villages = fields.Integer(string='Total Villages', readonly=True, default=0)
    total_projects = fields.Integer(string='Total Projects', readonly=True, default=0)
    total_departments = fields.Integer(string='Total Departments', readonly=True, default=0)
    total_landowners = fields.Integer(string='Total Landowners', readonly=True, default=0)
    
    # Survey Counts
    total_surveys = fields.Integer(string='Total Surveys', readonly=True, default=0)
    draft_surveys = fields.Integer(string='Draft Surveys', readonly=True, default=0)
    submitted_surveys = fields.Integer(string='Submitted Surveys', readonly=True, default=0)
    approved_surveys = fields.Integer(string='Approved Surveys', readonly=True, default=0)
    locked_surveys = fields.Integer(string='Locked Surveys', readonly=True, default=0)
    
    # Process Counts
    total_section4_notifications = fields.Integer(string='Section 4 Notifications', readonly=True, default=0)
    draft_section4 = fields.Integer(string='Draft Section 4', readonly=True, default=0)
    generated_section4 = fields.Integer(string='Generated Section 4', readonly=True, default=0)
    signed_section4 = fields.Integer(string='Signed Section 4', readonly=True, default=0)
    
    total_section11_reports = fields.Integer(string='Section 11 Reports', readonly=True, default=0)
    draft_section11 = fields.Integer(string='Draft Section 11', readonly=True, default=0)
    generated_section11 = fields.Integer(string='Generated Section 11', readonly=True, default=0)
    signed_section11 = fields.Integer(string='Signed Section 11', readonly=True, default=0)
    
    total_expert_committee_reports = fields.Integer(string='Expert Committee Reports', readonly=True, default=0)
    total_section15_objections = fields.Integer(string='Section 15 Objections', readonly=True, default=0)
    
    # Section 19 Notifications
    total_section19_notifications = fields.Integer(string='Section 19 Notifications', readonly=True, default=0)
    draft_section19 = fields.Integer(string='Draft Section 19', readonly=True, default=0)
    generated_section19 = fields.Integer(string='Generated Section 19', readonly=True, default=0)
    signed_section19 = fields.Integer(string='Signed Section 19', readonly=True, default=0)
    
    # Payment File Counts
    total_payment_files = fields.Integer(string='Payment Files', readonly=True, default=0)
    draft_payment_files = fields.Integer(string='Draft Payment Files', readonly=True, default=0)
    generated_payment_files = fields.Integer(string='Generated Payment Files', readonly=True, default=0)
    
    # Payment Reconciliation Counts
    total_payment_reconciliations = fields.Integer(string='Payment Reconciliations', readonly=True, default=0)
    draft_reconciliations = fields.Integer(string='Draft Reconciliations', readonly=True, default=0)
    processed_reconciliations = fields.Integer(string='Processed Reconciliations', readonly=True, default=0)
    completed_reconciliations = fields.Integer(string='Completed Reconciliations', readonly=True, default=0)
    
    # Document Vault Counts
    total_documents = fields.Integer(string='Total Documents', readonly=True, default=0)

    def _compute_all_counts(self):
        """Compute all counts for the dashboard"""
        for record in self:
            # Master Data Counts
            record.total_districts = self.env['bhu.district'].search_count([])
            record.total_sub_divisions = self.env['bhu.sub.division'].search_count([])
            record.total_tehsils = self.env['bhu.tehsil'].search_count([])
            record.total_circles = self.env['bhu.circle'].search_count([])
            record.total_villages = self.env['bhu.village'].search_count([])
            record.total_projects = self.env['bhu.project'].search_count([])
            record.total_departments = self.env['bhu.department'].search_count([])
            record.total_landowners = self.env['bhu.landowner'].search_count([])
            
            # Survey Counts
            record.total_surveys = self.env['bhu.survey'].search_count([])
            record.draft_surveys = self.env['bhu.survey'].search_count([('state', '=', 'draft')])
            record.submitted_surveys = self.env['bhu.survey'].search_count([('state', '=', 'submitted')])
            record.approved_surveys = self.env['bhu.survey'].search_count([('state', '=', 'approved')])
            record.locked_surveys = self.env['bhu.survey'].search_count([('state', '=', 'locked')])
            
            # Section 4 Notifications
            record.total_section4_notifications = self.env['bhu.section4.notification'].search_count([])
            record.draft_section4 = self.env['bhu.section4.notification'].search_count([('state', '=', 'draft')])
            record.generated_section4 = self.env['bhu.section4.notification'].search_count([('state', '=', 'generated')])
            record.signed_section4 = self.env['bhu.section4.notification'].search_count([('state', '=', 'signed')])
            
            # Section 11 Reports
            record.total_section11_reports = self.env['bhu.section11.preliminary.report'].search_count([])
            record.draft_section11 = self.env['bhu.section11.preliminary.report'].search_count([('state', '=', 'draft')])
            record.generated_section11 = self.env['bhu.section11.preliminary.report'].search_count([('state', '=', 'generated')])
            record.signed_section11 = self.env['bhu.section11.preliminary.report'].search_count([('state', '=', 'signed')])
            
            # Expert Committee Reports
            record.total_expert_committee_reports = self.env['bhu.expert.committee.report'].search_count([])
            
            # Section 15 Objections
            record.total_section15_objections = self.env['bhu.section15.objection'].search_count([])
            
            # Section 19 Notifications
            record.total_section19_notifications = self.env['bhu.section19.notification'].search_count([])
            record.draft_section19 = self.env['bhu.section19.notification'].search_count([('state', '=', 'draft')])
            record.generated_section19 = self.env['bhu.section19.notification'].search_count([('state', '=', 'generated')])
            record.signed_section19 = self.env['bhu.section19.notification'].search_count([('state', '=', 'signed')])
            
            # Payment Files
            record.total_payment_files = self.env['bhu.payment.file'].search_count([])
            record.draft_payment_files = self.env['bhu.payment.file'].search_count([('state', '=', 'draft')])
            record.generated_payment_files = self.env['bhu.payment.file'].search_count([('state', '=', 'generated')])
            
            # Payment Reconciliations
            record.total_payment_reconciliations = self.env['bhu.payment.reconciliation.bank'].search_count([])
            record.draft_reconciliations = self.env['bhu.payment.reconciliation.bank'].search_count([('state', '=', 'draft')])
            record.processed_reconciliations = self.env['bhu.payment.reconciliation.bank'].search_count([('state', '=', 'processed')])
            record.completed_reconciliations = self.env['bhu.payment.reconciliation.bank'].search_count([('state', '=', 'completed')])
            
            # Document Vault
            record.total_documents = self.env['bhu.document.vault'].search_count([])
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to compute and cache counts immediately"""
        # Pre-compute all counts once
        counts = self._get_all_counts()
        
        # Apply computed values to all records
        for vals in vals_list:
            vals.update(counts)
        
        records = super().create(vals_list)
        return records
    
    def read(self, fields=None, load='_classic_read'):
        """Override read to ensure values are computed if missing"""
        result = super().read(fields=fields, load=load)
        
        # If any record has zero values, refresh them
        for record_data in result:
            if record_data.get('total_districts', 0) == 0:
                # This record needs refreshing
                record = self.browse(record_data['id'])
                counts = self._get_all_counts()
                record.write(counts)
                # Re-read to get updated values
                result = super().read(fields=fields, load=load)
                break
        
        return result
    
    @api.model
    def _get_all_counts(self):
        """Get all counts - cached computation"""
        return {
            # Master Data Counts
            'total_districts': self.env['bhu.district'].search_count([]),
            'total_sub_divisions': self.env['bhu.sub.division'].search_count([]),
            'total_tehsils': self.env['bhu.tehsil'].search_count([]),
            'total_circles': self.env['bhu.circle'].search_count([]),
            'total_villages': self.env['bhu.village'].search_count([]),
            'total_projects': self.env['bhu.project'].search_count([]),
            'total_departments': self.env['bhu.department'].search_count([]),
            'total_landowners': self.env['bhu.landowner'].search_count([]),
            
            # Survey Counts
            'total_surveys': self.env['bhu.survey'].search_count([]),
            'draft_surveys': self.env['bhu.survey'].search_count([('state', '=', 'draft')]),
            'submitted_surveys': self.env['bhu.survey'].search_count([('state', '=', 'submitted')]),
            'approved_surveys': self.env['bhu.survey'].search_count([('state', '=', 'approved')]),
            'locked_surveys': self.env['bhu.survey'].search_count([('state', '=', 'locked')]),
            
            # Section 4 Notifications
            'total_section4_notifications': self.env['bhu.section4.notification'].search_count([]),
            'draft_section4': self.env['bhu.section4.notification'].search_count([('state', '=', 'draft')]),
            'generated_section4': self.env['bhu.section4.notification'].search_count([('state', '=', 'generated')]),
            'signed_section4': self.env['bhu.section4.notification'].search_count([('state', '=', 'signed')]),
            
            # Section 11 Reports
            'total_section11_reports': self.env['bhu.section11.preliminary.report'].search_count([]),
            'draft_section11': self.env['bhu.section11.preliminary.report'].search_count([('state', '=', 'draft')]),
            'generated_section11': self.env['bhu.section11.preliminary.report'].search_count([('state', '=', 'generated')]),
            'signed_section11': self.env['bhu.section11.preliminary.report'].search_count([('state', '=', 'signed')]),
            
            # Expert Committee Reports
            'total_expert_committee_reports': self.env['bhu.expert.committee.report'].search_count([]),
            
            # Section 15 Objections
            'total_section15_objections': self.env['bhu.section15.objection'].search_count([]),
            
            # Section 19 Notifications
            'total_section19_notifications': self.env['bhu.section19.notification'].search_count([]),
            'draft_section19': self.env['bhu.section19.notification'].search_count([('state', '=', 'draft')]),
            'generated_section19': self.env['bhu.section19.notification'].search_count([('state', '=', 'generated')]),
            'signed_section19': self.env['bhu.section19.notification'].search_count([('state', '=', 'signed')]),
            
            # Payment Files
            'total_payment_files': self.env['bhu.payment.file'].search_count([]),
            'draft_payment_files': self.env['bhu.payment.file'].search_count([('state', '=', 'draft')]),
            'generated_payment_files': self.env['bhu.payment.file'].search_count([('state', '=', 'generated')]),
            
            # Payment Reconciliations
            'total_payment_reconciliations': self.env['bhu.payment.reconciliation.bank'].search_count([]),
            'draft_reconciliations': self.env['bhu.payment.reconciliation.bank'].search_count([('state', '=', 'draft')]),
            'processed_reconciliations': self.env['bhu.payment.reconciliation.bank'].search_count([('state', '=', 'processed')]),
            'completed_reconciliations': self.env['bhu.payment.reconciliation.bank'].search_count([('state', '=', 'completed')]),
            
            # Document Vault
            'total_documents': self.env['bhu.document.vault'].search_count([]),
        }
    
    def action_refresh(self):
        """Refresh dashboard data"""
        counts = self._get_all_counts()
        self.write(counts)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Dashboard Refreshed',
                'message': 'Dashboard data has been updated.',
                'type': 'success',
                'sticky': False,
            }
        }
    
    def name_get(self):
        """Return a name for the dashboard"""
        return [(record.id, 'Dashboard') for record in self]
    
    
    @api.model
    def action_open_dashboard(self):
        """Open dashboard - reuses existing record or creates new one with cached values"""
        # Try to find existing dashboard record (transient models persist until server restart)
        dashboard = self.search([], limit=1, order='create_date desc')
        
        if not dashboard:
            # Create new dashboard with pre-computed values
            dashboard = self.create({})
        else:
            # Always refresh values to ensure they're up-to-date, but do it efficiently
            # Check if any key field is 0, which might indicate stale data
            needs_refresh = (
                dashboard.total_districts == 0 and 
                dashboard.total_surveys == 0 and 
                dashboard.total_section4_notifications == 0 and
                dashboard.total_payment_files == 0
            )
            if needs_refresh:
                counts = self._get_all_counts()
                dashboard.write(counts)
        
        # Ensure values are always present (double-check)
        if dashboard.total_districts == 0:
            counts = self._get_all_counts()
            dashboard.write(counts)
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Dashboard',
            'res_model': 'bhuarjan.dashboard',
            'view_mode': 'form',
            'res_id': dashboard.id,
            'target': 'current',
            'context': {'create': False, 'delete': False},
        }
    
    def action_open_districts(self):
        return self.env.ref('bhuarjan.action_bhu_district').read()[0]
    
    def action_open_sub_divisions(self):
        return self.env.ref('bhuarjan.action_bhu_sub_division').read()[0]
    
    def action_open_tehsils(self):
        return self.env.ref('bhuarjan.action_bhu_tehsil').read()[0]
    
    def action_open_circles(self):
        return self.env.ref('bhuarjan.action_bhu_circle').read()[0]
    
    def action_open_villages(self):
        return self.env.ref('bhuarjan.action_bhu_village').read()[0]
    
    def action_open_projects(self):
        return self.env.ref('bhuarjan.action_bhu_project').read()[0]
    
    def action_open_departments(self):
        return self.env.ref('bhuarjan.action_bhu_department').read()[0]
    
    def action_open_landowners(self):
        return self.env.ref('bhuarjan.action_bhu_landowner').read()[0]
    
    def action_open_surveys(self):
        return self.env.ref('bhuarjan.action_bhu_survey').read()[0]
    
    def action_open_surveys_draft(self):
        action = self.env.ref('bhuarjan.action_bhu_survey').read()[0]
        action['domain'] = [('state', '=', 'draft')]
        return action
    
    def action_open_surveys_submitted(self):
        action = self.env.ref('bhuarjan.action_bhu_survey').read()[0]
        action['domain'] = [('state', '=', 'submitted')]
        return action
    
    def action_open_surveys_approved(self):
        action = self.env.ref('bhuarjan.action_bhu_survey').read()[0]
        action['domain'] = [('state', '=', 'approved')]
        return action
    
    def action_open_surveys_locked(self):
        action = self.env.ref('bhuarjan.action_bhu_survey').read()[0]
        action['domain'] = [('state', '=', 'locked')]
        return action
    
    def action_open_expert_committee(self):
        return self.env.ref('bhuarjan.action_expert_committee_report').read()[0]
    
    def action_open_section15(self):
        return self.env.ref('bhuarjan.action_section15_objections').read()[0]
    
    def action_open_documents(self):
        return self.env.ref('bhuarjan.action_document_vault').read()[0]
    
    def action_open_section19(self):
        return self.env.ref('bhuarjan.action_section19_notification').read()[0]
    
    def action_open_section19_draft(self):
        action = self.env.ref('bhuarjan.action_section19_notification').read()[0]
        action['domain'] = [('state', '=', 'draft')]
        return action
    
    def action_open_section19_generated(self):
        action = self.env.ref('bhuarjan.action_section19_notification').read()[0]
        action['domain'] = [('state', '=', 'generated')]
        return action
    
    def action_open_section19_signed(self):
        action = self.env.ref('bhuarjan.action_section19_notification').read()[0]
        action['domain'] = [('state', '=', 'signed')]
        return action
    
    def action_open_payment_files(self):
        return self.env.ref('bhuarjan.action_payment_file').read()[0]
    
    def action_open_payment_files_draft(self):
        action = self.env.ref('bhuarjan.action_payment_file').read()[0]
        action['domain'] = [('state', '=', 'draft')]
        return action
    
    def action_open_payment_files_generated(self):
        action = self.env.ref('bhuarjan.action_payment_file').read()[0]
        action['domain'] = [('state', '=', 'generated')]
        return action
    
    def action_open_payment_reconciliations(self):
        return self.env.ref('bhuarjan.action_payment_reconciliation_bank').read()[0]
    
    def action_open_reconciliations_draft(self):
        action = self.env.ref('bhuarjan.action_payment_reconciliation_bank').read()[0]
        action['domain'] = [('state', '=', 'draft')]
        return action
    
    def action_open_reconciliations_processed(self):
        action = self.env.ref('bhuarjan.action_payment_reconciliation_bank').read()[0]
        action['domain'] = [('state', '=', 'processed')]
        return action
    
    def action_open_reconciliations_completed(self):
        action = self.env.ref('bhuarjan.action_payment_reconciliation_bank').read()[0]
        action['domain'] = [('state', '=', 'completed')]
        return action

