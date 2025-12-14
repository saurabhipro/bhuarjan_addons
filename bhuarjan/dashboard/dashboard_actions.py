# -*- coding: utf-8 -*-

from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class DashboardActions(models.AbstractModel):
    """Dashboard action methods for opening various views"""
    _name = 'bhuarjan.dashboard.actions'
    _description = 'Dashboard Action Methods'

    @api.model
    def _get_action_dict(self, action_ref):
        """Helper method to get action dictionary with all required fields"""
        try:
            # Use sudo to bypass any access issues when reading the action
            # Read all fields to ensure we get the complete action
            action = action_ref.sudo().read([])[0]
            # Ensure action has required fields for Odoo 18
            if 'type' not in action:
                action['type'] = 'ir.actions.act_window'
            if 'target' not in action:
                action['target'] = 'current'
            # Ensure views is a list (Odoo 18 requirement)
            # views should be a list of tuples: [(view_id, mode), ...]
            if 'views' not in action or not action.get('views') or action.get('views') == False:
                # If views is missing, create it from view_mode
                view_mode = action.get('view_mode', 'list,form')
                if isinstance(view_mode, str):
                    view_mode = view_mode.split(',')
                action['views'] = [(False, mode.strip()) for mode in view_mode]
            elif isinstance(action.get('views'), list):
                # Ensure all views are tuples
                action['views'] = [
                    (v[0], v[1]) if isinstance(v, (list, tuple)) and len(v) >= 2 else (False, v if isinstance(v, str) else 'list')
                    for v in action['views']
                ]
            return action
        except Exception as e:
            _logger.error(f"Error reading action {action_ref.id}: {e}", exc_info=True)
            # Fallback: create action dynamically from action_ref
            view_mode = action_ref.view_mode or 'list,form'
            if isinstance(view_mode, str):
                view_mode = view_mode.split(',')
            return {
                'type': 'ir.actions.act_window',
                'name': action_ref.name or action_ref.xml_id.split('.')[-1].replace('_', ' ').title() if hasattr(action_ref, 'xml_id') else 'Action',
                'res_model': action_ref.res_model,
                'view_mode': ','.join(view_mode),
                'views': [(False, mode) for mode in view_mode],
                'target': 'current',
            }
    @api.model
    def action_open_districts(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_district')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_bhu_district: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Districts',
                'res_model': 'bhu.district',
                'view_mode': 'list,form',
                'target': 'current',
            }
    @api.model
    def action_open_sub_divisions(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_sub_division')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_bhu_sub_division: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Sub Divisions',
                'res_model': 'bhu.sub.division',
                'view_mode': 'list,form',
                'target': 'current',
            }
    @api.model
    def action_open_tehsils(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_tehsil')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_bhu_tehsil: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Tehsils',
                'res_model': 'bhu.tehsil',
                'view_mode': 'list,form',
                'target': 'current',
            }
    @api.model
    def action_open_villages(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_village')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_bhu_village: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Villages',
                'res_model': 'bhu.village',
                'view_mode': 'list,form',
                'target': 'current',
            }
    @api.model
    def action_open_projects(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_project')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_bhu_project: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Projects',
                'res_model': 'bhu.project',
                'view_mode': 'list,form',
                'target': 'current',
            }
    @api.model
    def action_open_departments(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_department')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_bhu_department: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Departments',
                'res_model': 'bhu.department',
                'view_mode': 'list,form',
                'target': 'current',
            }
    @api.model
    def action_open_landowners(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_landowner')
            action = self._get_action_dict(action_ref)
            # Clear any default filters to prevent saved filters from auto-applying
            if 'context' not in action:
                action['context'] = {}
            action['context'].update({
                'search_default_district_id': False,
            })
            return action
        except Exception as e:
            _logger.error(f"Error getting action_bhu_landowner: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Landowners',
                'res_model': 'bhu.landowner',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'target': 'current',
            }
    @api.model
    def action_open_rate_masters(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_rate_master')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_bhu_rate_master: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Rate Masters',
                'res_model': 'bhu.rate.master',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'target': 'current',
            }
    @api.model
    def action_open_surveys(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_survey')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_bhu_survey: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Surveys',
                'res_model': 'bhu.survey',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'target': 'current',
            }
    @api.model
    def action_open_surveys_draft(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_survey')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'draft')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_bhu_survey: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Draft Surveys',
                'res_model': 'bhu.survey',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'draft')],
                'target': 'current',
            }
    @api.model
    def action_open_surveys_rejected(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_survey')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'rejected')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_bhu_survey: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Rejected Surveys',
                'res_model': 'bhu.survey',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'rejected')],
                'target': 'current',
            }
    @api.model
    def action_open_surveys_submitted(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_survey')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'submitted')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_bhu_survey: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Submitted Surveys',
                'res_model': 'bhu.survey',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'submitted')],
                'target': 'current',
            }
    @api.model
    def action_open_surveys_approved(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_survey')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'approved')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_bhu_survey: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Approved Surveys',
                'res_model': 'bhu.survey',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'approved')],
                'target': 'current',
            }
    @api.model
    def action_open_surveys_pending(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_survey')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', 'in', ['submitted', 'rejected'])]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_bhu_survey: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Pending Surveys',
                'res_model': 'bhu.survey',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', 'in', ['submitted', 'rejected'])],
                'target': 'current',
            }
    @api.model
    def action_open_surveys_done(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_survey')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', 'in', ['approved', 'rejected'])]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_bhu_survey: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Completed Surveys',
                'res_model': 'bhu.survey',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', 'in', ['approved', 'rejected'])],
                'target': 'current',
            }
    @api.model
    def action_open_expert_committee(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_expert_committee_report')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_expert_committee_report: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Expert Committee Reports',
                'res_model': 'bhu.expert.committee.report',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'target': 'current',
            }
    @api.model
    def action_open_section4(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_section4_notification')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_section4_notification: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Section 4 Notifications',
                'res_model': 'bhu.section4.notification',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'target': 'current',
            }
    @api.model
    def action_open_section11(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_section11_preliminary_report')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_section11_preliminary_report: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Section 11 Preliminary Reports',
                'res_model': 'bhu.section11.preliminary.report',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'target': 'current',
            }
    @api.model
    def action_open_section15(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_section15_objections')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_section15_objections: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Section 15 Objections',
                'res_model': 'bhu.section15.objection',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'target': 'current',
            }
    @api.model
    def action_open_documents(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_document_vault')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_document_vault: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Document Vault',
                'res_model': 'bhu.document.vault',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'target': 'current',
            }
    @api.model
    def action_open_section19(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_section19_notification')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_section19_notification: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Section 19 Notifications',
                'res_model': 'bhu.section19.notification',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'target': 'current',
            }
    @api.model
    def action_open_section19_draft(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_section19_notification')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'draft')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_section19_notification: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Section 19 Notifications (Draft)',
                'res_model': 'bhu.section19.notification',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'draft')],
                'target': 'current',
            }
    @api.model
    def action_open_section19_generated(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_section19_notification')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'generated')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_section19_notification: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Section 19 Notifications (Generated)',
                'res_model': 'bhu.section19.notification',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'generated')],
                'target': 'current',
            }
    @api.model
    def action_open_section19_signed(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_section19_notification')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'signed')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_section19_notification: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Section 19 Notifications (Signed)',
                'res_model': 'bhu.section19.notification',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'signed')],
                'target': 'current',
            }
    @api.model
    def action_open_payment_files(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_payment_file')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_payment_file: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Payment Files',
                'res_model': 'bhu.payment.file',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'target': 'current',
            }
    @api.model
    def action_open_payment_files_draft(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_payment_file')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'draft')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_payment_file: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Payment Files (Draft)',
                'res_model': 'bhu.payment.file',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'draft')],
                'target': 'current',
            }
    @api.model
    def action_open_payment_files_generated(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_payment_file')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'generated')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_payment_file: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Payment Files (Generated)',
                'res_model': 'bhu.payment.file',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'generated')],
                'target': 'current',
            }
    @api.model
    def action_open_payment_reconciliations(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_payment_reconciliation_bank')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_payment_reconciliation_bank: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Payment Reconciliations',
                'res_model': 'bhu.payment.reconciliation',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'target': 'current',
            }
    @api.model
    def action_open_reconciliations_draft(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_payment_reconciliation_bank')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'draft')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_payment_reconciliation_bank: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Payment Reconciliations (Draft)',
                'res_model': 'bhu.payment.reconciliation',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'draft')],
                'target': 'current',
            }
    @api.model
    def action_open_reconciliations_processed(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_payment_reconciliation_bank')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'processed')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_payment_reconciliation_bank: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Payment Reconciliations (Processed)',
                'res_model': 'bhu.payment.reconciliation',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'processed')],
                'target': 'current',
            }
    @api.model
    def action_open_reconciliations_completed(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_payment_reconciliation_bank')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'completed')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_payment_reconciliation_bank: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Payment Reconciliations (Completed)',
                'res_model': 'bhu.payment.reconciliation',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'completed')],
                'target': 'current',
            }
    @api.model
    def action_open_sia_teams(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_create_sia_team')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_create_sia_team: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'SIA Teams',
                'res_model': 'bhu.sia.team',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'target': 'current',
            }
    @api.model
    def action_open_sia_teams_draft(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_create_sia_team')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'draft')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_create_sia_team: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'SIA Teams (Draft)',
                'res_model': 'bhu.sia.team',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'draft')],
                'target': 'current',
            }
    @api.model
    def action_open_sia_teams_submitted(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_create_sia_team')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'submitted')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_create_sia_team: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'SIA Teams (Submitted)',
                'res_model': 'bhu.sia.team',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'submitted')],
                'target': 'current',
            }
    @api.model
    def action_open_sia_teams_approved(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_create_sia_team')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'approved')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_create_sia_team: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'SIA Teams (Approved)',
                'res_model': 'bhu.sia.team',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'approved')],
                'target': 'current',
            }
    @api.model
    def action_open_sia_teams_send_back(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_create_sia_team')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'send_back')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_create_sia_team: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'SIA Teams (Sent Back)',
                'res_model': 'bhu.sia.team',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'send_back')],
                'target': 'current',
            }
    @api.model
    def action_open_mobile_users(self):
        """Open mobile users list (JWT tokens with mobile channel)"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Active Mobile Users',
            'res_model': 'jwt.token',
            'view_mode': 'list,form',
            'domain': [('channel_type', '=', 'mobile')],
            'context': {'search_default_group_by_user': 1},
        }
