from odoo import models, fields, api, _
import uuid

class BhuProject(models.Model):
    _name = 'bhu.project'
    _description = 'Project'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Project Name', required=True, tracking=True)
    project_uuid = fields.Char(string='Project UUID', readonly=True, copy=False, default=lambda self: str(uuid.uuid4()))
    
    def action_regenerate_uuid(self):
        """Regenerate UUID for a single project"""
        if not self:
            return
        new_uuid = str(uuid.uuid4())
        # Ensure the new UUID is unique
        while self.env['bhu.project'].search([('project_uuid', '=', new_uuid)]):
            new_uuid = str(uuid.uuid4())
        
        self.write({'project_uuid': new_uuid})
        
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
    code = fields.Char(string='Project Code', tracking=True)
    department_id = fields.Many2one('bhu.department', string='Department / विभाग', tracking=True,
                                    help='Select the department for this project')
    district_id = fields.Many2one('bhu.district', string='District / जिला', tracking=True, help='Select the district for this project')
    description = fields.Text(string='Description', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    def action_set_draft(self):
        """Set project status to Draft"""
        self.write({'state': 'draft'})
        return True
    
    def action_set_active(self):
        """Set project status to Active"""
        self.write({'state': 'active'})
        return True
    
    def action_set_completed(self):
        """Set project status to Completed"""
        self.write({'state': 'completed'})
        return True
    
    def action_set_cancelled(self):
        """Set project status to Cancelled"""
        self.write({'state': 'cancelled'})
        return True
    village_ids = fields.Many2many('bhu.village', string="Villages", tracking=True)
    sdm_ids = fields.Many2many('res.users', 'bhu_project_sdm_rel', 'project_id', 'user_id',
                               string="SDM / उप-विभागीय मजिस्ट्रेट", 
                               domain="[('bhuarjan_role', '=', 'sdm')]", tracking=True,
                               help="Select Sub-Divisional Magistrates for this project")
    tehsildar_ids = fields.Many2many('res.users', 'bhu_project_tehsildar_rel', 'project_id', 'user_id',
                                     string="Tehsildar / तहसीलदार", 
                                     domain="[('bhuarjan_role', '=', 'sdm')]", tracking=True,
                                     help="Select Tehsildars for this project (using SDM role)")
    department_user_ids = fields.Many2many('res.users', 'bhu_project_department_user_rel', 'project_id', 'user_id',
                                           string="Department User / विभाग उपयोगकर्ता", 
                                           domain="[('bhuarjan_role', '=', 'department_user')]", tracking=True,
                                           help="Select Department Users for this project. They can approve/reject surveys.")
    
    patwari_ids = fields.Many2many('res.users', 'bhu_project_patwari_rel', 'project_id', 'user_id',
                                   string="Patwaris / पटवारी", 
                                   compute='_compute_patwari_ids', store=False, readonly=True,
                                   help="Patwaris assigned to villages in this project")
    
    @api.depends('village_ids')
    def _compute_patwari_ids(self):
        """Compute patwaris assigned to villages in this project"""
        for project in self:
            if project.village_ids:
                # Find all patwaris who have at least one village in common with project villages
                patwaris = self.env['res.users'].search([
                    ('bhuarjan_role', '=', 'patwari'),
                    ('village_ids', 'in', project.village_ids.ids)
                ])
                project.patwari_ids = patwaris
            else:
                project.patwari_ids = False
    
    def action_view_patwari_surveys(self, patwari_id):
        """Open surveys for a specific patwari in this project"""
        self.ensure_one()
        patwari = self.env['res.users'].browse(patwari_id)
        if not patwari.exists():
            return False
        return patwari.action_view_surveys_in_project(self.id)
    
    # Law Master - Many to One relationship
    law_master_id = fields.Many2one('bhu.law.master', string='Law', tracking=True,
                                    help='Select the law applicable to this project')
    
    # SIA Exemption - If True, project is exempt from Social Impact Assessment
    is_sia_exempt = fields.Boolean(string='SIA Exempt / सामाजिक समाघत अध्ययन से छूट', 
                                   default=False, tracking=True,
                                   help='If checked, this project is exempt from Social Impact Assessment. Section 4 and Expert Group will be disabled for this project.')
    
    # Company field for multi-company support
    company_id = fields.Many2one('res.company', string='Company', required=True, 
                                default=lambda self: self.env.company, tracking=True)
    
    # Section 4 Notification fields - These are project-level fields
    directly_affected = fields.Char(string='(दो) प्रत्यक्ष रूप से प्रभावित परिवारों की संख्या / Number of directly affected families', tracking=True,
                                      help='Number of directly affected families for this project')
    indirectly_affected = fields.Char(string='(तीन) अप्रत्यक्ष रूप से प्रभावित परिवारों की संख्या / Number of indirectly affected families', tracking=True,
                                        help='Number of indirectly affected families for this project')
    private_assets = fields.Char(string='(चार) प्रभावित क्षेत्र में निजी मकानों तथा अन्य परिसंपत्तियों की अनुमानित संख्या / Estimated number of private houses and other assets', tracking=True,
                                    help='Esti  mated number of private houses and other assets in the affected area')
    government_assets = fields.Char(string='(पाँच) प्रभावित क्षेत्र में शासकीय मकान तथा अन्य परिसंपत्तियों की अनुमानित संख्या / Estimated number of government houses and other assets', tracking=True,
                                      help='Estimated number of government houses and other assets in the affected area')
    total_cost = fields.Char(string='(आठ) परियोजना की कुल लागत / Total cost of the project', tracking=True,
                               help='Total cost of the project')
    project_benefits = fields.Text(string='(नौ) परियोजना से होने वाला लाभ / Benefits from the project', tracking=True,
                                      help='Benefits from the project')
    compensation_measures = fields.Text(string='(दस) प्रस्तावित सामाजिक समाघात की प्रतिपूर्ति के लिये उपाय तथा उस पर होने वाला संभावित व्यय / Measures for compensation and likely expenditure', tracking=True,
                                           help='Measures for compensation of proposed social impact and potential expenditure thereon')
    other_components = fields.Text(string='(ग्यारह) परियोजना द्वारा प्रभावित होने वाले अन्य घटक / Other components affected by the project', tracking=True,
                                      help='Other components affected by the project')
    
    # Section 11 Preliminary Report fields - These are project-level fields
    map_inspection_location = fields.Char(string='Land Map Inspection / भूमि मानचित्र निरीक्षण', tracking=True,
                                                       help='Location where land map can be inspected (SDO Revenue office)')
    authorized_officer = fields.Char(string='Officer authorized by Section 12 / धारा 12 द्वारा प्राधिकृत अधिकारी', tracking=True,
                                               help='Officer authorized by Section 12')
    is_displacement = fields.Boolean(string='Is Displacement Involved? / कितने परिवारों का विस्थापन निहित है।', 
                                                 default=False, tracking=True,
                                                 help='Whether displacement is involved for this project')
    affected_families_count = fields.Integer(string='Affected Families Count / प्रभावित परिवारों की संख्या', tracking=True,
                                                         help='Number of affected families if displacement is involved')
    affected_persons_count = fields.Integer(string='Affected Persons Count / प्रभावित व्यक्तियों की संख्या', tracking=True,
                                                         help='Number of persons affected by the proposed land acquisition who will be rehabilitated')
    is_exemption = fields.Boolean(string='Is Exemption Granted? / क्या प्रस्तावित परियोजना के लिए अधिनियम 2013 के अध्याय "दो" एवं "तीन" के प्रावधानों से छूट प्रदान की गई है।',
                                               default=False, tracking=True,
                                               help='Whether exemption is granted from Chapters Two and Three of Act 2013')
    section5_text_type = fields.Selection([
        ('exemption', 'प्रस्तावित प्रयोजन के लिए भूमि अर्जन को छत्तीसगढ़ शासन, राजस्व एवं आपदा प्रबंधन विभाग के अधिसूचना क्र. एफ 4-28/सात-1/2014, दिनाँक 02.03.2015 के द्वारा अधिनियम, 2013 के अध्याय "दो" एवं "तीन" के प्रावधानों से छूट प्रदान की गई है।'),
        ('sia_justification', 'प्रस्तावित प्रयोजन के भू-अर्जन के लिये कराये गये सामाजिक समाघात अध्ययन के अनुसार भूमि का अर्जन अंतिम विकल्प के रूप में किया जाना प्रस्तावित है तथा भूमि अर्जन से सामाजिक समाघात की तुलना में सामाजिक लाभ अधिक होना पाया गया है।')
    ], string='Section 5 Text / धारा 5 पाठ', default='exemption', tracking=True,
       help='Select which text to display in Section 5 of the report')
    exemption_details = fields.Text(string='Exemption Details / छूट विवरण', tracking=True,
                                                 help='Details of exemption notification (number, date, exempted chapters)')
    sia_justification = fields.Text(string='SIA Justification / SIA औचित्य', tracking=True,
                                                help='SIA justification details (last resort, social benefits)')
    rehab_admin_name = fields.Char(string='Rehabilitation Administrator / पुनर्वास प्रशासक', tracking=True,
                                               help='Name/Designation of Rehabilitation and Resettlement Administrator')
    
    # Rehabilitation Allocation Fields (shown when is_displacement is True)
    allocated_village = fields.Char(string='Allocated Village / आवंटित ग्राम', tracking=True,
                                     help='Village allocated for rehabilitation and resettlement')
    allocated_tehsil = fields.Char(string='Allocated Tehsil / आवंटित तहसील', tracking=True,
                                  help='Tehsil allocated for rehabilitation and resettlement')
    allocated_district = fields.Char(string='Allocated District / आवंटित जिला', tracking=True,
                                     help='District allocated for rehabilitation and resettlement')
    allocated_khasra_number = fields.Char(string='Allocated Khasra Number / आवंटित खसरा नंबर', tracking=True,
                                         help='Khasra number of the allocated land for rehabilitation')
    allocated_area_hectares = fields.Float(string='Allocated Area (Hectares) / आवंटित रकबा (हेक्टेयर)', 
                                          digits=(16, 4), tracking=True,
                                          help='Area in hectares allocated for rehabilitation and resettlement')
    
    @api.model
    def _search(self, args, offset=0, limit=None, order=None):
        """Override search to filter projects by user's assigned projects"""
        # Skip filtering if context flag is set (to avoid recursion)
        if self.env.context.get('skip_project_domain_filter'):
            return super()._search(args, offset=offset, limit=limit, order=order)
        
        # Get current user
        user = self.env.user
        
        # Allow public users to access all projects if they have access rights
        # This is needed for API endpoints that use auth='public' with sudo()
        if user.has_group('base.group_public') and not user.has_group('base.group_user'):
            # Public user - check if they have access rights, if so, allow access to all projects
            # The access rights check will happen at the ORM level, so we don't filter here
            return super()._search(args, offset=offset, limit=limit, order=order)
        
        # Admin, system users, and collectors see all projects - no filtering needed
        if not (user.has_group('bhuarjan.group_bhuarjan_admin') or 
                user.has_group('bhuarjan.group_bhuarjan_department_user') or
                user.has_group('base.group_system') or
                user.has_group('bhuarjan.group_bhuarjan_collector') or
                user.has_group('bhuarjan.group_bhuarjan_additional_collector')):
            try:
                # Get user's assigned projects using sudo() to bypass access rights and context flag to avoid recursion
                # Use sudo() to ensure we can search even if user doesn't have direct access
                # Include department users in the search
                assigned_projects = self.sudo().with_context(skip_project_domain_filter=True).search([
                    '|',
                    '|',
                    ('sdm_ids', 'in', user.id),
                    ('tehsildar_ids', 'in', user.id),
                    ('department_user_ids', 'in', user.id)
                ])
                
                if assigned_projects:
                    # Add domain to filter by assigned projects
                    args = args + [('id', 'in', assigned_projects.ids)]
                else:
                    # No assigned projects, return domain that matches nothing
                    args = args + [('id', 'in', [])]
            except Exception as e:
                # If there's an error getting assigned projects, log it and continue without filtering
                # This ensures users can still access projects if they have proper access rights
                import logging
                _logger = logging.getLogger(__name__)
                _logger.warning(f"Error filtering projects by assigned projects for user {user.id}: {e}")
                # Continue with original args - don't filter if there's an error
        
        # Call parent search with modified domain
        return super()._search(args, offset=offset, limit=limit, order=order)