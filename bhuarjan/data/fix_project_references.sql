-- Fix for bhuarjan settings master project_id references
-- This script fixes any existing records that reference invalid project IDs

-- Check and fix bhuarjan_settings_master table
UPDATE bhuarjan_settings_master 
SET project_id = NULL 
WHERE project_id IS NOT NULL 
AND project_id NOT IN (SELECT id FROM bhu_project);

-- Check and fix bhuarjan_sequence_settings table  
UPDATE bhuarjan_sequence_settings 
SET project_id = NULL 
WHERE project_id IS NOT NULL 
AND project_id NOT IN (SELECT id FROM bhu_project);

-- Check and fix bhuarjan_workflow_settings table
UPDATE bhuarjan_workflow_settings 
SET project_id = NULL 
WHERE project_id IS NOT NULL 
AND project_id NOT IN (SELECT id FROM bhu_project);

-- Display results
SELECT 'bhuarjan_settings_master' as table_name, COUNT(*) as records_with_null_project 
FROM bhuarjan_settings_master WHERE project_id IS NULL
UNION ALL
SELECT 'bhuarjan_sequence_settings' as table_name, COUNT(*) as records_with_null_project 
FROM bhuarjan_sequence_settings WHERE project_id IS NULL
UNION ALL  
SELECT 'bhuarjan_workflow_settings' as table_name, COUNT(*) as records_with_null_project 
FROM bhuarjan_workflow_settings WHERE project_id IS NULL;
