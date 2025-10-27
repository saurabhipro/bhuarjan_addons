# -*- coding: utf-8 -*-

def migrate(cr, version):
    """
    Migration script to fix project_id references in settings master models
    """
    if not version:
        return
    
    # Check if there are any records with invalid project_id references
    cr.execute("""
        SELECT id FROM bhuarjan_settings_master 
        WHERE project_id IS NOT NULL 
        AND project_id NOT IN (SELECT id FROM bhu_project)
    """)
    
    invalid_records = cr.fetchall()
    if invalid_records:
        print(f"Found {len(invalid_records)} invalid project references in settings master")
        # Set project_id to NULL for invalid records
        cr.execute("""
            UPDATE bhuarjan_settings_master 
            SET project_id = NULL 
            WHERE project_id IS NOT NULL 
            AND project_id NOT IN (SELECT id FROM bhu_project)
        """)
        print("Cleared invalid project references")
    
    # Check sequence settings
    cr.execute("""
        SELECT id FROM bhuarjan_sequence_settings 
        WHERE project_id IS NOT NULL 
        AND project_id NOT IN (SELECT id FROM bhu_project)
    """)
    
    invalid_seq_records = cr.fetchall()
    if invalid_seq_records:
        print(f"Found {len(invalid_seq_records)} invalid project references in sequence settings")
        cr.execute("""
            UPDATE bhuarjan_sequence_settings 
            SET project_id = NULL 
            WHERE project_id IS NOT NULL 
            AND project_id NOT IN (SELECT id FROM bhu_project)
        """)
        print("Cleared invalid project references in sequence settings")
    
    # Check workflow settings
    cr.execute("""
        SELECT id FROM bhuarjan_workflow_settings 
        WHERE project_id IS NOT NULL 
        AND project_id NOT IN (SELECT id FROM bhu_project)
    """)
    
    invalid_workflow_records = cr.fetchall()
    if invalid_workflow_records:
        print(f"Found {len(invalid_workflow_records)} invalid project references in workflow settings")
        cr.execute("""
            UPDATE bhuarjan_workflow_settings 
            SET project_id = NULL 
            WHERE project_id IS NOT NULL 
            AND project_id NOT IN (SELECT id FROM bhu_project)
        """)
        print("Cleared invalid project references in workflow settings")
