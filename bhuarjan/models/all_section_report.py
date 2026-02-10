from odoo import models, fields, tools

class AllSectionReport(models.Model):
    _name = 'bhu.all.section.report'
    _description = 'All Sections Report'
    _auto = False
    _order = 'create_date desc'

    name = fields.Char(string='Reference/Name', readonly=True)
    section_type = fields.Selection([
        ('sec4', 'Section 4 Notification'),
        ('sec11', 'Section 11 Preliminary Report'),
        ('sec19', 'Section 19 Notification'),
        ('sec21', 'Section 21 Notification'),
        ('sec23', 'Section 23 Award'),
        ('sia', 'SIA Team'),
        ('expert', 'Expert Committee'),
    ], string='Section Type', readonly=True)
    
    project_id = fields.Many2one('bhu.project', string='Project', readonly=True)
    village_id = fields.Many2one('bhu.village', string='Village', readonly=True)
    department_id = fields.Many2one('bhu.department', string='Department', readonly=True)
    status = fields.Char(string='Status', readonly=True)
    create_date = fields.Datetime(string='Created On', readonly=True)
    
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    (id + 100000000) as id,
                    name,
                    'sec4' as section_type,
                    project_id,
                    village_id,
                    (SELECT department_id FROM bhu_project WHERE id = project_id) as department_id,
                    state as status,
                    create_date
                FROM bhu_section4_notification
                
                UNION ALL
                
                SELECT
                    (id + 200000000) as id,
                    name,
                    'sec11' as section_type,
                    project_id,
                    village_id,
                    (SELECT department_id FROM bhu_project WHERE id = project_id) as department_id,
                    state as status,
                    create_date
                FROM bhu_section11_preliminary_report
                
                UNION ALL
                
                SELECT
                    (id + 300000000) as id,
                    name,
                    'sec19' as section_type,
                    project_id,
                    village_id,
                    (SELECT department_id FROM bhu_project WHERE id = project_id) as department_id,
                    state as status,
                    create_date
                FROM bhu_section19_notification
                
                UNION ALL
                
                SELECT
                    (id + 400000000) as id,
                    name,
                    'sec21' as section_type,
                    project_id,
                    village_id,
                    (SELECT department_id FROM bhu_project WHERE id = project_id) as department_id,
                    state as status,
                    create_date
                FROM bhu_section21_notification
                
                UNION ALL
                
                SELECT
                    (id + 500000000) as id,
                    name,
                    'sec23' as section_type,
                    project_id,
                    village_id,
                    (SELECT department_id FROM bhu_project WHERE id = project_id) as department_id,
                    state as status,
                    create_date
                FROM bhu_section23_award
                
                UNION ALL
                
                SELECT
                    (id + 600000000) as id,
                    name,
                    'sia' as section_type,
                    project_id,
                    village_id,
                    (SELECT department_id FROM bhu_project WHERE id = project_id) as department_id,
                    state as status,
                    create_date
                FROM bhu_sia_team

                UNION ALL
                
                SELECT
                    (id + 700000000) as id,
                    name,
                    'expert' as section_type,
                    project_id,
                    village_id,
                    (SELECT department_id FROM bhu_project WHERE id = project_id) as department_id,
                    state as status,
                    create_date
                FROM bhu_expert_committee_report
            )
        """ % (self._table,))
