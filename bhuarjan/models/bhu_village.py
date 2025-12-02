from odoo import models, fields, api, _
from odoo.exceptions import UserError
import uuid
import logging

_logger = logging.getLogger(__name__)

class BhuVillage(models.Model):
    _name = 'bhu.village'
    _description = 'Village'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    def _get_state_domain(self):
        state_ids = self.env['bhu.district'].search([]).mapped('state_id.id')    
        return [('id', 'in', state_ids)]

    village_uuid = fields.Char(string='Village UUID', readonly=True, copy=False, default=lambda self: str(uuid.uuid4()))
    
    def action_regenerate_all_uuids(self):
        """Regenerate unique UUIDs for all villages to ensure uniqueness"""
        all_villages = self.search([])
        total = len(all_villages)
        fixed = 0
        duplicates_found = 0
        
        _logger.info(f"Starting UUID regeneration for {total} villages...")
        
        # Track UUIDs we've assigned to ensure uniqueness
        assigned_uuids = set()
        
        for village in all_villages:
            original_uuid = village.village_uuid
            
            # Check if UUID is missing
            if not village.village_uuid:
                new_uuid = str(uuid.uuid4())
                # Ensure the new UUID is unique (very unlikely but check anyway)
                while new_uuid in assigned_uuids:
                    new_uuid = str(uuid.uuid4())
                village.write({'village_uuid': new_uuid})
                assigned_uuids.add(new_uuid)
                fixed += 1
                _logger.info(f"Village {village.id} ({village.name}) - Generated new UUID: {new_uuid}")
                continue
            
            # Check for duplicates
            duplicate_villages = self.search([
                ('village_uuid', '=', village.village_uuid),
                ('id', '!=', village.id)
            ])
            
            if duplicate_villages or village.village_uuid in assigned_uuids:
                duplicates_found += 1
                new_uuid = str(uuid.uuid4())
                # Ensure the new UUID is unique
                while new_uuid in assigned_uuids:
                    new_uuid = str(uuid.uuid4())
                village.write({'village_uuid': new_uuid})
                assigned_uuids.add(new_uuid)
                fixed += 1
                _logger.info(f"Village {village.id} ({village.name}) - Duplicate UUID found! Regenerated: {original_uuid} -> {new_uuid}")
            else:
                assigned_uuids.add(village.village_uuid)
        
        message = f"UUID regeneration completed!\n\nTotal villages: {total}\nUUIDs regenerated: {fixed}\nDuplicates found: {duplicates_found}"
        _logger.info(message)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'UUID Regeneration Complete',
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_regenerate_uuid(self):
        """Regenerate UUID for a single village"""
        if not self:
            return
        new_uuid = str(uuid.uuid4())
        # Ensure the new UUID is unique
        while self.env['bhu.village'].search([('village_uuid', '=', new_uuid)]):
            new_uuid = str(uuid.uuid4())
        
        self.write({'village_uuid': new_uuid})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'UUID Regenerated',
                'message': f'New UUID: {new_uuid}',
                'type': 'success',
                'sticky': False,
            }
        }
    
    @api.model
    def regenerate_all_uuids_cron(self):
        """Cron method to ensure all villages have unique UUIDs"""
        self.action_regenerate_all_uuids()
    
    state_id = fields.Many2one('res.country.state', string='State', tracking=True)
    district_id = fields.Many2one('bhu.district', string='District / जिला', tracking=True)
    sub_division_id = fields.Many2one('bhu.sub.division', string='Sub Division / उपभाग', tracking=True)
    tehsil_id = fields.Many2one('bhu.tehsil', string='Tehsil / तहसील', tracking=True)
    name = fields.Char(string='Village Name / ग्राम का नाम', required=True)
    village_code = fields.Char(string='Village Code / ग्राम कोड', required=True, tracking=True, copy=False, help='Unique code for the village')
    pincode = fields.Char(string='Pincode / पिनकोड', tracking=True)
    
    # Related records counts
    section4_notification_count = fields.Integer(string='Section 4 Notifications', compute='_compute_notification_counts', store=False)
    
    def _compute_notification_counts(self):
        """Compute counts of related notifications"""
        for village in self:
            # Count Section 4 Notifications that include this village
            section4_count = self.env['bhu.section4.notification'].search_count([
                ('village_id', '=', village.id)
            ])
            village.section4_notification_count = section4_count
    
    def action_view_section4_notifications(self):
        """Open Section 4 Notifications for this village"""
        self.ensure_one()
        return {
            'name': _('Section 4 Notifications / धारा 4 अधिसूचनाएं'),
            'type': 'ir.actions.act_window',
            'res_model': 'bhu.section4.notification',
            'view_mode': 'list,form',
            'domain': [('village_id', '=', self.id)],
            'context': {'default_village_id': self.id},
        }
    
    _sql_constraints = [
        ('village_code_unique', 'UNIQUE(village_code)', 'Village Code must be unique! / ग्राम कोड अद्वितीय होना चाहिए!')
    ]



