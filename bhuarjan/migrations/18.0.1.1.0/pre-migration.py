# -*- coding: utf-8 -*-

def migrate(cr, version):
    """
    Migration script to handle SIA Team Member model change from res.users to bhu.sia.team.member
    Drops old relation tables that used user_id and lets Odoo recreate them with member_id
    """
    # Drop old relation tables that used user_id
    relation_tables = [
        'sia_team_non_govt_social_scientist_rel',
        'sia_team_local_bodies_rep_rel',
        'sia_team_resettlement_expert_rel',
        'sia_team_technical_expert_rel',
    ]
    
    for table in relation_tables:
        cr.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = %s
            );
        """, (table,))
        if cr.fetchone()[0]:
            # Drop foreign key constraints first
            cr.execute("""
                SELECT constraint_name 
                FROM information_schema.table_constraints 
                WHERE table_name = %s 
                AND constraint_type = 'FOREIGN KEY'
            """, (table,))
            constraints = cr.fetchall()
            for constraint in constraints:
                cr.execute("ALTER TABLE %s DROP CONSTRAINT IF EXISTS %s" % (
                    table, constraint[0]
                ))
            
            # Drop the table
            cr.execute("DROP TABLE IF EXISTS %s CASCADE" % table)
            cr.execute("COMMIT")

