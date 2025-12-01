# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SiaTeam(models.Model):
    _name = 'bhu.sia.team'
    _description = 'SIA Team'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Team Name / टीम का नाम', compute='_compute_name', store=True, readonly=True)
    
    # New fields
    sub_division_id = fields.Many2one('bhu.sub.division', string='Sub Division / उपभाग', required=True, tracking=True)
    requiring_body = fields.Char(string='Requiring Body / आवश्यक निकाय', required=True, tracking=True,
                                help='Name of the requiring body/department')
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True, tracking=True, ondelete='cascade')
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम', required=False, tracking=True)
    
    # Workflow
    state = fields.Selection([
        ('draft', 'Draft / प्रारूप'),
        ('submitted', 'Submitted / प्रस्तुत'),
        ('approved', 'Approved / अनुमोदित'),
        ('send_back', 'Send Back / वापस भेजें'),
    ], string='Status / स्थिति', default='draft', tracking=True)
    
    # SIA Team Members - 5 Sections
    # (क) Non-Government Social Scientist
    non_govt_social_scientist_ids = fields.Many2many('bhu.sia.team.member', 
                                                     'sia_team_non_govt_social_scientist_rel',
                                                     'sia_team_id', 'member_id',
                                                     string='Non-Government Social Scientist / गैर शासकीय सामाजिक वैज्ञानिक',
                                                     tracking=True)
    
    # (ख) Representatives of Local Bodies
    local_bodies_representative_ids = fields.Many2many('bhu.sia.team.member',
                                                       'sia_team_local_bodies_rep_rel',
                                                       'sia_team_id', 'member_id',
                                                       string='Representatives of Local Bodies / स्थानीय निकायों के प्रतिनिधि',
                                                       tracking=True)
    
    # (ग) Resettlement Expert
    resettlement_expert_ids = fields.Many2many('bhu.sia.team.member',
                                                'sia_team_resettlement_expert_rel',
                                                'sia_team_id', 'member_id',
                                                string='Resettlement Expert / पुनर्व्यवस्थापन विशेषज्ञ',
                                                tracking=True)
    
    # (घ) Technical Expert on Project Related Subject
    technical_expert_ids = fields.Many2many('bhu.sia.team.member',
                                            'sia_team_technical_expert_rel',
                                            'sia_team_id', 'member_id',
                                            string='Technical Expert / तकनीकी विशेषज्ञ',
                                            tracking=True)
    
    # (ड.) Tehsildar of Affected Area (Convener)
    tehsildar_id = fields.Many2one('bhu.sia.team.member',
                                   string='Tehsildar (Convener) / तहसीलदार (संयोजक)',
                                   tracking=True,
                                   help='Tehsildar of the affected area who will be the convener')
    
    # Documents
    sia_order_file = fields.Binary(string='SIA Order File / SIA आदेश फ़ाइल')
    sia_order_filename = fields.Char(string='SIA Order Filename')
    sia_report_file = fields.Binary(string='SIA Report File / SIA रिपोर्ट फ़ाइल')
    sia_report_filename = fields.Char(string='SIA Report Filename')
    
    # Legacy fields (kept for backward compatibility)
    team_member_ids = fields.Many2many('bhu.sia.team.member', string='Team Members / टीम सदस्य', 
                                      compute='_compute_team_members', store=False)
    description = fields.Text(string='Description / विवरण', tracking=True)
    active = fields.Boolean(string='Active / सक्रिय', default=True, tracking=True)
    
    @api.depends('project_id', 'sub_division_id')
    def _compute_name(self):
        """Generate team name from project and subdivision"""
        for record in self:
            if record.project_id and record.sub_division_id:
                sequence = self.env['ir.sequence'].next_by_code('bhu.sia.team') or 'New'
                record.name = f'SIA-{sequence}'
            else:
                record.name = 'New'
    
    @api.depends('non_govt_social_scientist_ids', 'local_bodies_representative_ids', 
                 'resettlement_expert_ids', 'technical_expert_ids', 'tehsildar_id')
    def _compute_team_members(self):
        """Compute all team members from all sections"""
        for record in self:
            all_members = record.non_govt_social_scientist_ids
            all_members |= record.local_bodies_representative_ids
            all_members |= record.resettlement_expert_ids
            all_members |= record.technical_expert_ids
            if record.tehsildar_id:
                all_members |= record.tehsildar_id
            record.team_member_ids = all_members
    
    # Workflow Actions
    def action_submit(self):
        """Submit SIA Team for approval"""
        self.ensure_one()
        self.state = 'submitted'
    
    def action_approve(self):
        """Approve SIA Team"""
        self.ensure_one()
        self.state = 'approved'
    
    def action_send_back(self):
        """Send back SIA Team for revision"""
        self.ensure_one()
        self.state = 'send_back'
    
    def action_draft(self):
        """Reset to draft"""
        self.ensure_one()
        self.state = 'draft'
    
    # Document Actions
    def action_download_sia_order(self):
        """Download SIA Order PDF"""
        self.ensure_one()
        return self.env.ref('bhuarjan.action_report_sia_order').report_action(self)
    

