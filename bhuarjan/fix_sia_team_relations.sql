-- SQL Commands to fix SIA Team relation tables
-- Run these commands in PostgreSQL to migrate from user_id to member_id

-- 1. Drop foreign key constraints first
ALTER TABLE sia_team_non_govt_social_scientist_rel DROP CONSTRAINT IF EXISTS sia_team_non_govt_social_scientist_rel_user_id_fkey;
ALTER TABLE sia_team_local_bodies_rep_rel DROP CONSTRAINT IF EXISTS sia_team_local_bodies_rep_rel_user_id_fkey;
ALTER TABLE sia_team_resettlement_expert_rel DROP CONSTRAINT IF EXISTS sia_team_resettlement_expert_rel_user_id_fkey;
ALTER TABLE sia_team_technical_expert_rel DROP CONSTRAINT IF EXISTS sia_team_technical_expert_rel_user_id_fkey;

-- 2. Rename columns from user_id to member_id
ALTER TABLE sia_team_non_govt_social_scientist_rel RENAME COLUMN user_id TO member_id;
ALTER TABLE sia_team_local_bodies_rep_rel RENAME COLUMN user_id TO member_id;
ALTER TABLE sia_team_resettlement_expert_rel RENAME COLUMN user_id TO member_id;
ALTER TABLE sia_team_technical_expert_rel RENAME COLUMN user_id TO member_id;

-- 3. The foreign keys will be recreated automatically by Odoo on next update

