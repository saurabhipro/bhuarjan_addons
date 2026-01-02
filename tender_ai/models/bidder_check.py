# -*- coding: utf-8 -*-

from odoo import models, fields, api


class TenderBidderCheck(models.Model):
    _name = 'tende_ai.bidder_check'
    _description = 'Bidder Eligibility Check'
    _order = 'create_date desc'

    job_id = fields.Many2one('tende_ai.job', string='Job', required=True, ondelete='cascade', readonly=True, index=True)
    tender_id = fields.Many2one('tende_ai.tender', string='Tender', readonly=True, related='job_id.tender_id', store=True)
    bidder_id = fields.Many2one('tende_ai.bidder', string='Bidder', required=True, ondelete='cascade', readonly=True, index=True)

    overall_result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('unknown', 'Unknown'),
    ], string='Overall Result', default='unknown', readonly=True, index=True)

    total_criteria = fields.Integer(string='Total Criteria', readonly=True)
    passed_criteria = fields.Integer(string='Passed', readonly=True)
    failed_criteria = fields.Integer(string='Failed', readonly=True)
    unknown_criteria = fields.Integer(string='Unknown', readonly=True)

    duration_seconds = fields.Float(string='Duration (sec)', readonly=True)
    processed_on = fields.Datetime(string='Processed On', readonly=True)
    error_message = fields.Text(string='Error', readonly=True)

    line_ids = fields.One2many('tende_ai.bidder_check_line', 'check_id', string='Criteria Results', readonly=True)


class TenderBidderCheckLine(models.Model):
    _name = 'tende_ai.bidder_check_line'
    _description = 'Bidder Eligibility Check Line'
    _order = 'sl_no, id'

    check_id = fields.Many2one('tende_ai.bidder_check', string='Check', required=True, ondelete='cascade', readonly=True, index=True)
    job_id = fields.Many2one('tende_ai.job', string='Job', related='check_id.job_id', store=True, readonly=True, index=True)
    bidder_id = fields.Many2one('tende_ai.bidder', string='Bidder', related='check_id.bidder_id', store=True, readonly=True, index=True)
    criteria_id = fields.Many2one('tende_ai.eligibility_criteria', string='Criteria', readonly=True)

    sl_no = fields.Char(string='Sl. No.', readonly=True)
    criteria = fields.Text(string='Criteria', readonly=True)
    supporting_document = fields.Text(string='Supporting Document', readonly=True)

    result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('unknown', 'Unknown'),
    ], string='Result', default='unknown', readonly=True, index=True)

    reason = fields.Text(string='Reason', readonly=True)
    evidence = fields.Text(string='Evidence', readonly=True)
    missing_documents = fields.Text(string='Missing Documents', readonly=True)


