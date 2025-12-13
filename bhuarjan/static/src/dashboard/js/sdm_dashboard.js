/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class OwlCrmDashboard extends Component {
    static template = "bhuarjan.SDMTemplate";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.notification = useService("notification");
        
        // Load persisted selections from localStorage
        const savedDepartment = localStorage.getItem('sdm_dashboard_department');
        const savedProject = localStorage.getItem('sdm_dashboard_project');
        const savedProjectName = localStorage.getItem('sdm_dashboard_project_name');
        const savedVillage = localStorage.getItem('sdm_dashboard_village');
        
            this.state = useState({
                loading: true,
                selectedDepartment: savedDepartment ? parseInt(savedDepartment, 10) : null,
                selectedProject: savedProject ? parseInt(savedProject, 10) : null,
                selectedProjectName: savedProjectName || null,
                selectedVillage: savedVillage ? parseInt(savedVillage, 10) : null,
                departments: [],
                projects: [],
                villages: [],
                isCollector: false,
                isProjectExempt: false,
            stats: {
                section4_total: 0, section4_draft: 0, section4_submitted: 0, section4_approved: 0, section4_send_back: 0,
                section11_total: 0, section11_draft: 0, section11_submitted: 0, section11_approved: 0, section11_send_back: 0,
                section15_total: 0, section15_draft: 0, section15_submitted: 0, section15_approved: 0, section15_send_back: 0,
                section19_total: 0, section19_draft: 0, section19_submitted: 0, section19_approved: 0, section19_send_back: 0,
                expert_total: 0, expert_draft: 0, expert_submitted: 0, expert_approved: 0, expert_send_back: 0,
                sia_total: 0, sia_draft: 0, sia_submitted: 0, sia_approved: 0, sia_send_back: 0,
            }
        });

        onWillStart(async () => {
            await this.loadDepartments();
            // Load projects if department is already selected
            if (this.state.selectedDepartment) {
                await this.loadProjects();
            } else {
                this.state.projects = [];
            }
            // Load villages if project is already selected
            if (this.state.selectedProject) {
                await this.loadVillages();
            } else {
                this.state.villages = [];
            }
            await this.loadDashboardData();
        });
    }

    async loadDepartments() {
        try {
            this.state.departments = await this.orm.call("bhu.dashboard", "get_all_departments", []);
        } catch (error) {
            console.error("Error loading departments:", error);
            this.state.departments = [];
        }
    }

    async loadProjects() {
        if (!this.state.selectedDepartment) {
            this.state.projects = [];
            return;
        }
        try {
            this.state.projects = await this.orm.call(
                "bhu.dashboard",
                "get_all_projects_sdm",
                [this.state.selectedDepartment]
            );
        } catch (error) {
            console.error("Error loading projects:", error);
            this.state.projects = [];
        }
    }

    async loadVillages() {
        if (!this.state.selectedProject) {
            this.state.villages = [];
            return;
        }
        try {
            this.state.villages = await this.orm.call(
                "bhu.dashboard",
                "get_villages_by_project_sdm",
                [this.state.selectedProject]
            );
        } catch (error) {
            console.error("Error loading villages:", error);
            this.state.villages = [];
        }
    }

    async loadDashboardData() {
        this.state.loading = true;
        try {
            // If no project is selected, reset all stats to 0
            if (!this.state.selectedProject) {
                this.state.stats = {
                    section4_total: 0, section4_draft: 0, section4_submitted: 0, section4_approved: 0, section4_send_back: 0,
                    section11_total: 0, section11_draft: 0, section11_submitted: 0, section11_approved: 0, section11_send_back: 0,
                    section15_total: 0, section15_draft: 0, section15_submitted: 0, section15_approved: 0, section15_send_back: 0,
                    section19_total: 0, section19_draft: 0, section19_submitted: 0, section19_approved: 0, section19_send_back: 0,
                    expert_total: 0, expert_draft: 0, expert_submitted: 0, expert_approved: 0, expert_send_back: 0,
                    sia_total: 0, sia_draft: 0, sia_submitted: 0, sia_approved: 0, sia_send_back: 0,
                    survey_total: 0, survey_submitted: 0, survey_approved: 0, survey_rejected: 0,
                    draft_award_total: 0, draft_award_draft: 0, draft_award_generated: 0, draft_award_approved: 0,
                    section4_info: null, section11_info: null, section15_info: null, section19_info: null,
                    expert_info: null, sia_info: null, survey_info: null, draft_award_info: null,
                    survey_completion_percent: 0, section4_completion_percent: 0, section11_completion_percent: 0,
                    section15_completion_percent: 0, section19_completion_percent: 0, expert_completion_percent: 0,
                    sia_completion_percent: 0, draft_award_completion_percent: 0
                };
                this.state.loading = false;
                return;
            }
            
            const stats = await this.orm.call(
                "bhu.dashboard",
                "get_sdm_dashboard_stats",
                [
                    this.state.selectedDepartment || null,
                    this.state.selectedProject || null,
                    this.state.selectedVillage || null
                ]
            );
            this.state.stats = stats || this.state.stats;
            this.state.isCollector = stats ? (stats.is_collector || false) : false;
            this.state.isProjectExempt = stats ? (stats.is_project_exempt || false) : false;
        } catch (error) {
            console.error("Error loading dashboard stats:", error);
        } finally {
            this.state.loading = false;
        }
    }

    async onDepartmentChange(ev) {
        const value = ev.target.value;
        const departmentId = value ? parseInt(value, 10) : null;
        this.state.selectedDepartment = departmentId;
        
        // Save to localStorage
        if (departmentId) {
            localStorage.setItem('sdm_dashboard_department', String(departmentId));
        } else {
            localStorage.removeItem('sdm_dashboard_department');
        }
        
        // Only reset project/village if department actually changed
        if (departmentId) {
            // Check if current project belongs to new department
            const currentProject = this.state.projects.find(p => p.id === this.state.selectedProject);
            if (!currentProject || currentProject.department_id !== departmentId) {
                this.state.selectedProject = null;
                this.state.selectedProjectName = null;
                this.state.selectedVillage = null;
                this.state.villages = [];
                localStorage.removeItem('sdm_dashboard_project');
                localStorage.removeItem('sdm_dashboard_project_name');
                localStorage.removeItem('sdm_dashboard_village');
            }
            await this.loadProjects();
        } else {
            this.state.projects = [];
            this.state.selectedProject = null;
            this.state.selectedProjectName = null;
            this.state.selectedVillage = null;
            this.state.villages = [];
            localStorage.removeItem('sdm_dashboard_project');
            localStorage.removeItem('sdm_dashboard_project_name');
            localStorage.removeItem('sdm_dashboard_village');
        }
        // Don't auto-load dashboard data - wait for submit
    }

    async onProjectChange(ev) {
        const value = ev.target.value;
        const projectId = value ? parseInt(value, 10) : null;
        this.state.selectedProject = projectId;
        
        // Save to localStorage
        if (projectId) {
            localStorage.setItem('sdm_dashboard_project', String(projectId));
            const project = this.state.projects.find(p => p.id === projectId);
            this.state.selectedProjectName = project ? project.name : null;
            if (this.state.selectedProjectName) {
                localStorage.setItem('sdm_dashboard_project_name', this.state.selectedProjectName);
            }
        } else {
            localStorage.removeItem('sdm_dashboard_project');
            localStorage.removeItem('sdm_dashboard_project_name');
            this.state.selectedProjectName = null;
        }
        
        // Only reset village if project actually changed
        if (projectId) {
            // Check if current village belongs to new project
            const currentVillage = this.state.villages.find(v => v.id === this.state.selectedVillage);
            if (!currentVillage) {
                this.state.selectedVillage = null;
                localStorage.removeItem('sdm_dashboard_village');
            }
            await this.loadVillages();
            // Auto-refresh dashboard data when project is selected
            await this.loadDashboardData();
        } else {
            this.state.selectedVillage = null;
            this.state.villages = [];
            localStorage.removeItem('sdm_dashboard_village');
            // Refresh dashboard data when project is cleared
            await this.loadDashboardData();
        }
    }

    async onVillageChange(ev) {
        const value = ev.target.value;
        const villageId = value ? parseInt(value, 10) : null;
        this.state.selectedVillage = villageId;
        
        // Save to localStorage
        if (villageId) {
            localStorage.setItem('sdm_dashboard_village', String(villageId));
        } else {
            localStorage.removeItem('sdm_dashboard_village');
        }
        // Auto-refresh dashboard data when village is selected
        await this.loadDashboardData();
    }

    async onSubmitFilters() {
        await this.loadDashboardData();
    }

    // Check if project is selected
    checkProjectSelected() {
        if (!this.state.selectedProject) {
            this.notification.add(_t("Please select a project first"), { type: "warning" });
            return false;
        }
        return true;
    }

    // Open list view for a specific section
    openSectionList(sectionModel) {
        if (!this.checkProjectSelected()) {
            return;
        }
        
        let domain = [];
        if (this.state.selectedProject) {
            domain.push(["project_id", "=", this.state.selectedProject]);
        }
        if (this.state.selectedVillage) {
            domain.push(["village_id", "=", this.state.selectedVillage]);
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: this.getSectionName(sectionModel),
            res_model: sectionModel,
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: domain,
            target: "current",
        });
    }

    // Get section display name
    getSectionName(sectionModel) {
        const sectionNames = {
            'bhu.survey': 'Surveys',
            'bhu.sia.team': 'SIA Team',
            'bhu.section4.notification': 'Section 4 Notifications',
            'bhu.expert.committee.report': 'Expert Group Reports',
            'bhu.section11.preliminary.report': 'Section 11 Notifications',
            'bhu.section15.objection': 'Section 15 Objections',
            'bhu.section19.notification': 'Section 19 Notifications',
            'bhu.draft.award': 'Sec 21 notice',
        };
        return sectionNames[sectionModel] || 'Document';
    }

    // Helper to convert value to string for select binding
    toString(value) {
        return value ? String(value) : '';
    }

    // Open first document in form view with pagination (for View button)
    openFirstDocument(sectionModel, sectionInfo) {
        if (!this.checkProjectSelected()) {
            return;
        }
        
        let domain = [];
        if (this.state.selectedProject) {
            domain.push(["project_id", "=", this.state.selectedProject]);
        }
        if (this.state.selectedVillage) {
            domain.push(["village_id", "=", this.state.selectedVillage]);
        }
        
        // Try to get first pending, otherwise first document
        let recordId = false;
        if (sectionInfo) {
            if (sectionInfo.first_pending_id) {
                recordId = sectionInfo.first_pending_id;
            } else if (sectionInfo.first_document_id) {
                recordId = sectionInfo.first_document_id;
            }
        }
        
        const sectionName = this.getSectionName(sectionModel);
        
        if (recordId) {
            // If only 1 document, open directly in form view, otherwise use list,form for pagination
            const totalCount = sectionInfo ? (sectionInfo.total || 0) : 0;
            const viewMode = totalCount === 1 ? "form" : "list,form";
            const views = totalCount === 1 ? [[false, "form"]] : [[false, "list"], [false, "form"]];
            
            this.action.doAction({
                type: "ir.actions.act_window",
                name: sectionName,
                res_model: sectionModel,
                res_id: recordId,
                view_mode: viewMode,
                views: views,
                domain: domain,
                target: "current",
                context: {
                    'default_project_id': this.state.selectedProject || false,
                    'default_village_id': this.state.selectedVillage || false,
                },
            });
        } else {
            // No documents, open list view
            this.openSectionList(sectionModel);
        }
    }

    // Create new record for a section
    createSectionRecord(sectionModel) {
        if (!this.checkProjectSelected()) {
            return;
        }
        
        let context = {};
        if (this.state.selectedProject) {
            context.default_project_id = this.state.selectedProject;
        }
        if (this.state.selectedVillage) {
            context.default_village_id = this.state.selectedVillage;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("New Record"),
            res_model: sectionModel,
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
            context: context,
        });
    }

    // Open first pending document in form view for approval/rejection
    openFirstPending(sectionModel, pendingId, sectionInfo) {
        if (!this.checkProjectSelected()) {
            return;
        }
        
        if (!pendingId) {
            // No pending documents, just open list view
            this.openSectionList(sectionModel);
            return;
        }
        
        let domain = [];
        if (this.state.selectedProject) {
            domain.push(["project_id", "=", this.state.selectedProject]);
        }
        if (this.state.selectedVillage) {
            domain.push(["village_id", "=", this.state.selectedVillage]);
        }
        // Filter to only submitted records for pagination
        domain.push(["state", "=", "submitted"]);
        
        const sectionName = this.getSectionName(sectionModel);
        
        // If only 1 submitted document, open directly in form view, otherwise use list,form for pagination
        const submittedCount = sectionInfo ? (sectionInfo.submitted_count || 0) : 0;
        const viewMode = submittedCount === 1 ? "form" : "list,form";
        const views = submittedCount === 1 ? [[false, "form"]] : [[false, "list"], [false, "form"]];
        
        this.action.doAction({
            type: "ir.actions.act_window",
            name: sectionName,
            res_model: sectionModel,
            res_id: pendingId,
            view_mode: viewMode,
            views: views,
            domain: domain,
            target: "current",
            context: {
                'default_project_id': this.state.selectedProject || false,
                'default_village_id': this.state.selectedVillage || false,
            },
        });
    }

    // Check if all surveys are approved (for surveys, check approved + rejected)
    isAllApprovedSurvey(sectionInfo) {
        if (!sectionInfo) return true;
        const total = sectionInfo.total || 0;
        const approved = sectionInfo.approved_count || 0;
        const rejected = sectionInfo.rejected_count || 0;
        // All are approved or rejected (no pending)
        return total > 0 && (approved + rejected) === total;
    }

    // Check if all documents are approved for a section (disable buttons if all approved or no submitted)
    isAllApproved(sectionInfo) {
        if (!sectionInfo) return true;
        // Disable if all approved, no total records, or no submitted records
        return sectionInfo.all_approved || sectionInfo.total === 0 || sectionInfo.submitted_count === 0;
    }
}

// Register the action
registry.category("actions").add(
    "bhuarjan.sdm_dashboard_tag",
    OwlCrmDashboard
);
