# -*- coding: utf-8 -*-

from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class DashboardHelpers(models.AbstractModel):
    """Generic helper methods for dashboard counts"""
    _name = 'bhuarjan.dashboard.helpers'
    _description = 'Dashboard Helper Methods'

    @api.model
    def _get_model_count_by_status(self, model_name, base_domain, status=None, state_field='state'):
        """Generic method to get count by status for any model
        Args:
            model_name: Model name (e.g., 'bhu.survey')
            base_domain: Base domain to filter by
            status: Status value, list of statuses, or None for total count
                   (e.g., 'approved', ['approved', 'rejected'], or None)
            state_field: Field name for state (default: 'state')
        Returns:
            int: Count of records matching the domain and status
        """
        if not base_domain:
            base_domain = []
        
        if status is None:
            # Return total count without status filter
            return self.env[model_name].search_count(base_domain)
        
        if isinstance(status, list):
            status_domain = [(state_field, 'in', status)]
        else:
            status_domain = [(state_field, '=', status)]
        
        return self.env[model_name].search_count(base_domain + status_domain)
    
    @api.model
    def _get_section_counts(self, model_name, base_domain, state_field='state', states=None):
        """Generic method to get all state counts for a section
        Args:
            model_name: Model name (e.g., 'bhu.section4.notification')
            base_domain: Base domain to filter by
            state_field: Field name for state (default: 'state')
            states: List of states to count (default: ['draft', 'submitted', 'approved', 'send_back'])
        Returns:
            dict: Dictionary with total and counts for each state
        """
        if states is None:
            states = ['draft', 'submitted', 'approved', 'send_back']
        
        if not base_domain:
            base_domain = []
        
        total = self.env[model_name].search_count(base_domain)
        counts = {}
        for state in states:
            counts[f'{state}'] = self._get_model_count_by_status(model_name, base_domain, state, state_field)
        
        return {
            'total': total,
            **counts
        }
    
    @api.model
    def _get_simple_section_counts(self, model_name, base_domain):
        """Simple count method for sections without workflow states
        Args:
            model_name: Model name (e.g., 'bhu.section20a.railways')
            base_domain: Base domain to filter by
        Returns:
            dict: Dictionary with total count only (no state breakdown)
        """
        if not base_domain:
            base_domain = []
        
        total = self.env[model_name].search_count(base_domain)
        
        return {
            'total': total,
            'draft': 0,
            'submitted': 0,
            'approved': 0,
            'send_back': 0,
        }
    
    @api.model
    def _get_survey_counts(self, base_domain):
        """Get all survey counts with completion percentage
        Args:
            base_domain: Base domain to filter surveys (can be empty list for all)
        Returns:
            dict: Dictionary with all survey counts and completion percentage
        """
        if not base_domain:
            base_domain = []
        
        total = self._get_model_count_by_status('bhu.survey', base_domain, None)
        draft = self._get_model_count_by_status('bhu.survey', base_domain, 'draft')
        submitted = self._get_model_count_by_status('bhu.survey', base_domain, 'submitted')
        approved = self._get_model_count_by_status('bhu.survey', base_domain, 'approved')
        rejected = self._get_model_count_by_status('bhu.survey', base_domain, 'rejected')
        total_done = self._get_model_count_by_status('bhu.survey', base_domain, ['approved', 'rejected'])
        pending = self._get_model_count_by_status('bhu.survey', base_domain, ['submitted', 'rejected'])
        
        # Calculate completion percentage
        # For surveys: completion = (approved + rejected) / total
        # If all are approved or rejected, it's 100%
        completion_percent = 0
        if total > 0:
            completion_percent = round(((approved + rejected) / total) * 100, 1)
            # Ensure it's between 0 and 100
            completion_percent = max(0.0, min(100.0, completion_percent))
        
        return {
            'total': total,
            'draft': draft,
            'submitted': submitted,
            'approved': approved,
            'rejected': rejected,
            'total_done': total_done,
            'pending': pending,
            'completion_percent': completion_percent,
        }

