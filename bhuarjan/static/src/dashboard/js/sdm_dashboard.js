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

        this.state = useState({
            loading: true,
            selectedDepartment: null,
            selectedProject: null,
            selectedVillage: null,
            departments: [],
            projects: [],
            villages: [],
            isCollector: false,
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
            // Don't load projects initially - wait for department selection
            this.state.projects = [];
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
        } catch (error) {
            console.error("Error loading dashboard stats:", error);
        } finally {
            this.state.loading = false;
        }
    }

    async onDepartmentChange(ev) {
        const value = ev.target.value;
        this.state.selectedDepartment = value ? parseInt(value) : null;
        this.state.selectedProject = null;
        this.state.selectedVillage = null;
        this.state.villages = [];
        if (this.state.selectedDepartment) {
            await this.loadProjects();
        } else {
            this.state.projects = [];
        }
        // Don't auto-load dashboard data - wait for submit
    }

    async onProjectChange(ev) {
        const value = ev.target.value;
        this.state.selectedProject = value ? parseInt(value) : null;
        this.state.selectedVillage = null;
        if (this.state.selectedProject) {
            await this.loadVillages();
        } else {
            this.state.villages = [];
        }
        // Don't auto-load dashboard data - wait for submit
    }

    async onVillageChange(ev) {
        const value = ev.target.value;
        this.state.selectedVillage = value ? parseInt(value) : null;
        // Don't auto-load dashboard data - wait for submit
    }

    async onSubmitFilters() {
        await this.loadDashboardData();
    }

    // Open list view for a specific section
    openSectionList(sectionModel) {
        let domain = [];
        if (this.state.selectedProject) {
            domain.push(["project_id", "=", this.state.selectedProject]);
        }
        if (this.state.selectedVillage) {
            domain.push(["village_id", "=", this.state.selectedVillage]);
        }
        this.action.doAction({
            type: "ir.actions.act_window",
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
            'bhu.sia.team': 'SIA Team',
            'bhu.section4.notification': 'Section 4 Notification',
            'bhu.expert.committee.report': 'Expert Committee Report',
            'bhu.section11.preliminary.report': 'Section 11 Preliminary Report',
            'bhu.section15.objection': 'Section 15 Objection',
            'bhu.section19.notification': 'Section 19 Notification',
        };
        return sectionNames[sectionModel] || 'Document';
    }

    // Open first document in form view with pagination (for View button)
    openFirstDocument(sectionModel, sectionInfo) {
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
