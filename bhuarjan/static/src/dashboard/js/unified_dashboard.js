/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

/**
 * Unified Dashboard Component - Configurable for all dashboard types
 * 
 * CONFIGURATION GUIDE:
 * To add a new dashboard type, add it to DASHBOARD_CONFIG below:
 * 
 * DASHBOARD_CONFIG = {
 *     'dashboard_type_name': {
 *         template: 'bhuarjan.TemplateName',
 *         registryKey: 'bhuarjan.registry_key',
 *         pageTitle: 'Dashboard Title',
 *         localStoragePrefix: 'local_storage_prefix',
 *         showDepartmentFilter: true/false,
 *         showProjectFilter: true/false,
 *         showVillageFilter: true/false,
 *         initialDataMethod: 'method_name', // Optional: custom method for initial data
 *         statsMapping: { // Map backend stats keys to frontend state keys
 *             'survey_total': 'survey_total',
 *             ...
 *         }
 *     }
 * }
 */

// ========== CONFIGURATION: Dashboard Types ==========
const DASHBOARD_CONFIG = {
    'sdm': {
        template: 'bhuarjan.SDMTemplate',
        registryKey: 'bhuarjan.sdm_dashboard_tag',
        pageTitle: 'SDM Dashboard',
        localStoragePrefix: 'sdm_dashboard',
        showDepartmentFilter: true,
        showProjectFilter: true,
        showVillageFilter: true,
        statsMapping: {
            // Maps backend response keys to frontend state keys
            'survey_total': 'survey_total',
            'survey_draft': 'survey_draft',
            'survey_submitted': 'survey_submitted',
            'survey_approved': 'survey_approved',
            'survey_rejected': 'survey_rejected',
            'section4_total': 'section4_total',
            'section4_draft': 'section4_draft',
            'section4_submitted': 'section4_submitted',
            'section4_approved': 'section4_approved',
            'section4_send_back': 'section4_send_back',
            'section11_total': 'section11_total',
            'section11_draft': 'section11_draft',
            'section11_submitted': 'section11_submitted',
            'section11_approved': 'section11_approved',
            'section11_send_back': 'section11_send_back',
            'section15_total': 'section15_total',
            'section15_draft': 'section15_draft',
            'section15_submitted': 'section15_submitted',
            'section15_approved': 'section15_approved',
            'section15_send_back': 'section15_send_back',
            'section19_total': 'section19_total',
            'section19_draft': 'section19_draft',
            'section19_submitted': 'section19_submitted',
            'section19_approved': 'section19_approved',
            'section19_send_back': 'section19_send_back',
            'expert_total': 'expert_total',
            'expert_draft': 'expert_draft',
            'expert_submitted': 'expert_submitted',
            'expert_approved': 'expert_approved',
            'expert_send_back': 'expert_send_back',
            'sia_total': 'sia_total',
            'sia_draft': 'sia_draft',
            'sia_submitted': 'sia_submitted',
            'sia_approved': 'sia_approved',
            'sia_send_back': 'sia_send_back',
        }
    },
    'collector': {
        template: 'bhuarjan.CollectorDashboardTemplate',
        registryKey: 'bhuarjan.collector_dashboard',
        pageTitle: 'Collector Dashboard',
        localStoragePrefix: 'collector_dashboard',
        showDepartmentFilter: true,
        showProjectFilter: true,
        showVillageFilter: true,
        statsMapping: {
            // Same as SDM
            'survey_total': 'survey_total',
            'survey_draft': 'survey_draft',
            'survey_submitted': 'survey_submitted',
            'survey_approved': 'survey_approved',
            'survey_rejected': 'survey_rejected',
            'section4_total': 'section4_total',
            'section4_draft': 'section4_draft',
            'section4_submitted': 'section4_submitted',
            'section4_approved': 'section4_approved',
            'section4_send_back': 'section4_send_back',
            'section11_total': 'section11_total',
            'section11_draft': 'section11_draft',
            'section11_submitted': 'section11_submitted',
            'section11_approved': 'section11_approved',
            'section11_send_back': 'section11_send_back',
            'section15_total': 'section15_total',
            'section15_draft': 'section15_draft',
            'section15_submitted': 'section15_submitted',
            'section15_approved': 'section15_approved',
            'section15_send_back': 'section15_send_back',
            'section19_total': 'section19_total',
            'section19_draft': 'section19_draft',
            'section19_submitted': 'section19_submitted',
            'section19_approved': 'section19_approved',
            'section19_send_back': 'section19_send_back',
            'expert_total': 'expert_total',
            'expert_draft': 'expert_draft',
            'expert_submitted': 'expert_submitted',
            'expert_approved': 'expert_approved',
            'expert_send_back': 'expert_send_back',
            'sia_total': 'sia_total',
            'sia_draft': 'sia_draft',
            'sia_submitted': 'sia_submitted',
            'sia_approved': 'sia_approved',
            'sia_send_back': 'sia_send_back',
        }
    },
    'admin': {
        template: 'bhuarjan.AdminDashboardTemplate',
        registryKey: 'bhuarjan.admin_dashboard',
        pageTitle: 'Admin Dashboard',
        localStoragePrefix: 'admin_dashboard',
        showDepartmentFilter: true,
        showProjectFilter: true,
        showVillageFilter: true,
        statsMapping: {
            // Map backend field names to admin dashboard state field names
            'survey_total': 'total_surveys',
            'survey_draft': 'draft_surveys',
            'survey_submitted': 'submitted_surveys',
            'survey_approved': 'approved_surveys',
            'survey_rejected': 'rejected_surveys',
            'total_surveys_done': 'total_surveys_done',
            'pending_surveys': 'pending_surveys',
            'section4_total': 'section4_total',
            'section4_draft': 'section4_draft',
            'section4_submitted': 'section4_submitted',
            'section4_approved': 'section4_approved',
            'section4_send_back': 'section4_send_back',
            'section11_total': 'section11_total',
            'section11_draft': 'section11_draft',
            'section11_submitted': 'section11_submitted',
            'section11_approved': 'section11_approved',
            'section11_send_back': 'section11_send_back',
            'section19_total': 'section19_total',
            'section19_draft': 'section19_draft',
            'section19_submitted': 'section19_submitted',
            'section19_approved': 'section19_approved',
            'section19_send_back': 'section19_send_back',
            'section15_total': 'section15_total',
            'section15_draft': 'section15_draft',
            'section15_submitted': 'section15_submitted',
            'section15_approved': 'section15_approved',
            'section15_send_back': 'section15_send_back',
            'expert_total': 'expert_committee_total',
            'expert_draft': 'expert_committee_draft',
            'expert_submitted': 'expert_committee_submitted',
            'expert_approved': 'expert_committee_approved',
            'expert_send_back': 'expert_committee_send_back',
            'sia_total': 'sia_total',
            'sia_draft': 'sia_draft',
            'sia_submitted': 'sia_submitted',
            'sia_approved': 'sia_approved',
            'sia_send_back': 'sia_send_back',
        }
    },
    'department': {
        template: 'bhuarjan.DepartmentDashboardTemplate',
        registryKey: 'bhuarjan.department_dashboard',
        pageTitle: 'Department User Dashboard',
        localStoragePrefix: 'department_dashboard',
        showDepartmentFilter: false, // Department is auto-selected
        showProjectFilter: true,
        showVillageFilter: true,
        initialDataMethod: 'get_department_user_department',
        statsMapping: {
            'survey_total': 'survey_total',
            'survey_draft': 'survey_draft',
            'survey_submitted': 'survey_submitted',
            'survey_approved': 'survey_approved',
            'survey_rejected': 'survey_rejected',
            'survey_completion_percent': 'survey_completion_percent',
        }
    },
    'admin': {
        template: 'bhuarjan.AdminDashboardTemplate',
        registryKey: 'bhuarjan.admin_dashboard',
        pageTitle: 'Admin Dashboard',
        localStoragePrefix: 'admin_dashboard',
        showDepartmentFilter: true,
        showProjectFilter: true,
        showVillageFilter: true,
        statsMapping: {
            // Admin sees all stats - same as SDM
            'survey_total': 'survey_total',
            'survey_draft': 'survey_draft',
            'survey_submitted': 'survey_submitted',
            'survey_approved': 'survey_approved',
            'survey_rejected': 'survey_rejected',
            'section4_total': 'section4_total',
            'section4_draft': 'section4_draft',
            'section4_submitted': 'section4_submitted',
            'section4_approved': 'section4_approved',
            'section4_send_back': 'section4_send_back',
            'section11_total': 'section11_total',
            'section11_draft': 'section11_draft',
            'section11_submitted': 'section11_submitted',
            'section11_approved': 'section11_approved',
            'section11_send_back': 'section11_send_back',
            'section15_total': 'section15_total',
            'section15_draft': 'section15_draft',
            'section15_submitted': 'section15_submitted',
            'section15_approved': 'section15_approved',
            'section15_send_back': 'section15_send_back',
            'section19_total': 'section19_total',
            'section19_draft': 'section19_draft',
            'section19_submitted': 'section19_submitted',
            'section19_approved': 'section19_approved',
            'section19_send_back': 'section19_send_back',
            'expert_total': 'expert_total',
            'expert_draft': 'expert_draft',
            'expert_submitted': 'expert_submitted',
            'expert_approved': 'expert_approved',
            'expert_send_back': 'expert_send_back',
            'sia_total': 'sia_total',
            'sia_draft': 'sia_draft',
            'sia_submitted': 'sia_submitted',
            'sia_approved': 'sia_approved',
            'sia_send_back': 'sia_send_back',
        }
    }
};

export class UnifiedDashboard extends Component {
    // Template will be set dynamically based on dashboard type
    static template = "bhuarjan.SDMTemplate"; // Default, will be overridden

    setup() {
        // Determine dashboard type from props or context
        this.dashboardType = this.props.dashboardType || 'sdm';
        this.config = DASHBOARD_CONFIG[this.dashboardType] || DASHBOARD_CONFIG['sdm'];
        
        // Set template dynamically
        this.constructor.template = this.config.template;
        
        this.pageTitle = this.config.pageTitle;
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        
        const localStoragePrefix = this.config.localStoragePrefix;
        
        // Load persisted selections from localStorage
        const savedDepartment = localStorage.getItem(`${localStoragePrefix}_department`);
        const savedProject = localStorage.getItem(`${localStoragePrefix}_project`);
        const savedProjectName = localStorage.getItem(`${localStoragePrefix}_project_name`);
        const savedVillage = localStorage.getItem(`${localStoragePrefix}_village`);
        
        // Initialize state based on configuration
        const initialState = {
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
            stats: this._getInitialStats(),
            lastUpdate: null,
        };
        
        this.state = useState(initialState);

        onWillStart(async () => {
            try {
                await this.loadInitialData();
                await this.loadDashboardData();
            } catch (error) {
                console.error("Error in onWillStart:", error);
                this.state.loading = false;
            }
        });
    }

    _getInitialStats() {
        // Initialize stats based on dashboard type configuration
        const stats = {};
        const mapping = this.config.statsMapping || {};
        
        // Initialize all mapped stats to 0
        for (const [backendKey, frontendKey] of Object.entries(mapping)) {
            stats[frontendKey] = 0;
        }
        
        // Add info objects for sections that need them
        if (this.dashboardType === 'sdm' || this.dashboardType === 'collector') {
            stats.section4_info = null;
            stats.section11_info = null;
            stats.section15_info = null;
            stats.section19_info = null;
            stats.expert_info = null;
            stats.sia_info = null;
            stats.survey_info = null;
            stats.draft_award_info = null;
        }
        
        return stats;
    }

    async loadInitialData() {
        // Load department if configured
        if (this.config.showDepartmentFilter) {
            await this.loadDepartments();
        } else if (this.config.initialDataMethod) {
            // For department dashboard, load user's department
            await this.loadUserDepartment();
        }
        
        // Load projects if department is selected
        if (this.state.selectedDepartment || !this.config.showDepartmentFilter) {
            await this.loadProjects();
        }
        
        // Load villages if project is selected
        if (this.state.selectedProject) {
            await this.loadVillages();
        }
    }

    async loadUserDepartment() {
        try {
            const userDepartment = await this.orm.call(
                "bhuarjan.dashboard",
                this.config.initialDataMethod,
                []
            );
            
            if (userDepartment) {
                const deptId = userDepartment.id || (Array.isArray(userDepartment) && userDepartment[0]?.id);
                const deptName = userDepartment.name || (Array.isArray(userDepartment) && userDepartment[0]?.name);
                
                if (deptId) {
                    this.state.selectedDepartment = deptId;
                    this.state.departments = [{
                        id: deptId,
                        name: deptName || `Department ${deptId}`
                    }];
                }
            }
        } catch (error) {
            console.error("Error loading user department:", error);
        }
    }

    async loadDepartments() {
        try {
            this.state.departments = await this.orm.call("bhuarjan.dashboard", "get_all_departments", []);
        } catch (error) {
            console.error("Error loading departments:", error);
            this.state.departments = [];
        }
    }

    async loadProjects() {
        const departmentId = this.config.showDepartmentFilter ? this.state.selectedDepartment : this.state.selectedDepartment;
        
        if (!departmentId && this.config.showDepartmentFilter) {
            this.state.projects = [];
            return;
        }
        
        try {
            this.state.projects = await this.orm.call(
                "bhuarjan.dashboard",
                "get_user_projects",
                [departmentId]
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
                "bhuarjan.dashboard",
                "get_villages_by_project",
                [this.state.selectedProject]
            );
        } catch (error) {
            console.error("Error loading villages:", error);
            this.state.villages = [];
        }
    }

    async loadDashboardData() {
        try {
            this.state.loading = true;
            
            console.log("Loading dashboard data with filters:", {
                department: this.state.selectedDepartment,
                project: this.state.selectedProject,
                village: this.state.selectedVillage
            });
            
            const stats = await this.orm.call(
                "bhuarjan.dashboard",
                "get_dashboard_stats",
                [
                    this.state.selectedDepartment || null,
                    this.state.selectedProject || null,
                    this.state.selectedVillage || null
                ]
            );
            
            if (stats) {
                // Map backend stats to frontend state using configuration
                this._mapStatsToState(stats);
                
                // Set additional flags
                if (stats.is_collector !== undefined) {
                    this.state.isCollector = stats.is_collector;
                }
                if (stats.is_project_exempt !== undefined) {
                    this.state.isProjectExempt = stats.is_project_exempt;
                }
            }
            
            this.state.lastUpdate = new Date().toLocaleString();
        } catch (error) {
            console.error("Error loading dashboard stats:", error);
            this.notification.add(_t("Error loading dashboard data"), { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    _mapStatsToState(backendStats) {
        // Map backend stats to frontend state using configuration mapping
        const mapping = this.config.statsMapping || {};
        
        for (const [backendKey, frontendKey] of Object.entries(mapping)) {
            if (backendKey in backendStats) {
                this.state.stats[frontendKey] = backendStats[backendKey] || 0;
            }
        }
        
        // Handle info objects separately (they're not in the mapping)
        if (backendStats.survey_info) {
            this.state.stats.survey_info = backendStats.survey_info;
        }
        if (backendStats.section4_info) {
            this.state.stats.section4_info = backendStats.section4_info;
        }
        if (backendStats.section11_info) {
            this.state.stats.section11_info = backendStats.section11_info;
        }
        if (backendStats.section15_info) {
            this.state.stats.section15_info = backendStats.section15_info;
        }
        if (backendStats.section19_info) {
            this.state.stats.section19_info = backendStats.section19_info;
        }
        if (backendStats.expert_info) {
            this.state.stats.expert_info = backendStats.expert_info;
        }
        if (backendStats.sia_info) {
            this.state.stats.sia_info = backendStats.sia_info;
        }
        if (backendStats.draft_award_info) {
            this.state.stats.draft_award_info = backendStats.draft_award_info;
        }
    }

    async onDepartmentChange(ev) {
        if (!this.config.showDepartmentFilter) return;
        
        const value = ev.target.value;
        const departmentId = value ? parseInt(value, 10) : null;
        this.state.selectedDepartment = departmentId;
        
        // Save to localStorage
        const prefix = this.config.localStoragePrefix;
        if (departmentId) {
            localStorage.setItem(`${prefix}_department`, String(departmentId));
        } else {
            localStorage.removeItem(`${prefix}_department`);
        }
        
        // Reset project and village when department changes
        this.state.selectedProject = null;
        this.state.selectedVillage = null;
        this.state.projects = [];
        this.state.villages = [];
        localStorage.removeItem(`${prefix}_project`);
        localStorage.removeItem(`${prefix}_project_name`);
        localStorage.removeItem(`${prefix}_village`);
        
        await this.loadProjects();
        await this.loadDashboardData();
    }

    async onProjectChange(ev) {
        if (!this.config.showProjectFilter) return;
        
        const value = ev.target.value;
        const projectId = value ? parseInt(value, 10) : null;
        this.state.selectedProject = projectId;
        
        // Save to localStorage
        const prefix = this.config.localStoragePrefix;
        if (projectId) {
            localStorage.setItem(`${prefix}_project`, String(projectId));
            const project = this.state.projects.find(p => p.id === projectId);
            this.state.selectedProjectName = project ? project.name : null;
            if (this.state.selectedProjectName) {
                localStorage.setItem(`${prefix}_project_name`, this.state.selectedProjectName);
            }
        } else {
            localStorage.removeItem(`${prefix}_project`);
            localStorage.removeItem(`${prefix}_project_name`);
            this.state.selectedProjectName = null;
        }
        
        // Check if current village belongs to new project
        if (projectId) {
            await this.loadVillages();
            const currentVillage = this.state.villages.find(v => v.id === this.state.selectedVillage);
            if (!currentVillage) {
                this.state.selectedVillage = null;
                localStorage.removeItem(`${prefix}_village`);
            }
        } else {
            this.state.selectedVillage = null;
            this.state.villages = [];
            localStorage.removeItem(`${prefix}_village`);
        }
        
        await this.loadDashboardData();
    }

    async onVillageChange(ev) {
        if (!this.config.showVillageFilter) return;
        
        const value = ev.target.value;
        const villageId = value ? parseInt(value, 10) : null;
        this.state.selectedVillage = villageId;
        
        // Save to localStorage
        const prefix = this.config.localStoragePrefix;
        if (villageId) {
            localStorage.setItem(`${prefix}_village`, String(villageId));
        } else {
            localStorage.removeItem(`${prefix}_village`);
        }
        
        await this.loadDashboardData();
    }

    async onSubmitFilters() {
        await this.loadDashboardData();
    }

    // Helper methods for domain building
    getDomain() {
        const domain = [];
        if (this.state.selectedDepartment) {
            domain.push(['department_id', '=', parseInt(this.state.selectedDepartment)]);
        }
        if (this.state.selectedProject) {
            domain.push(['project_id', '=', parseInt(this.state.selectedProject)]);
        }
        if (this.state.selectedVillage) {
            domain.push(['village_id', '=', parseInt(this.state.selectedVillage)]);
        }
        return domain;
    }

    checkProjectSelected() {
        if (!this.state.selectedProject) {
            this.notification.add(_t("Please select a project first"), { type: "warning" });
            return false;
        }
        return true;
    }

    // Action methods (can be overridden by specific dashboard types)
    async openAction(actionName) {
        try {
            const action = await this.orm.call("bhuarjan.dashboard", actionName, []);
            if (action && action.type) {
                await this.action.doAction(action);
            }
        } catch (error) {
            console.error(`Error opening ${actionName}:`, error);
            this.notification.add(_t("Error: " + (error.message || actionName)), { type: "danger" });
        }
    }

    async openSectionList(model) {
        if (!this.checkProjectSelected()) {
            return;
        }
        
        // Special handling for R and R Scheme - open form directly (one per project)
        if (model === 'bhu.section18.rr.scheme') {
            await this.openRRSchemeForm();
            return;
        }
        
        const domain = this.getDomain();
        await this.action.doAction({
            type: 'ir.actions.act_window',
            name: this.getSectionName(model),
            res_model: model,
            view_mode: 'list,form',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
            target: 'current',
            context: {
                'default_project_id': this.state.selectedProject || false,
                'default_village_id': this.state.selectedVillage || false,
            },
        });
    }

    // Open first document in form view with pagination (for View button)
    async openFirstDocument(sectionModel, sectionInfo) {
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
            
            await this.action.doAction({
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
            await this.openSectionList(sectionModel);
        }
    }

    // Create new record for a section
    async createSectionRecord(sectionModel) {
        if (!this.checkProjectSelected()) {
            return;
        }
        
        // Special handling for R and R Scheme - open form directly (one per project)
        if (sectionModel === 'bhu.section18.rr.scheme') {
            await this.openRRSchemeForm();
            return;
        }
        
        let context = {};
        if (this.state.selectedProject) {
            context.default_project_id = this.state.selectedProject;
        }
        if (this.state.selectedVillage) {
            context.default_village_id = this.state.selectedVillage;
        }
        await this.action.doAction({
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
    async openFirstPending(sectionModel, pendingId, sectionInfo) {
        if (!this.checkProjectSelected()) {
            return;
        }
        
        if (!pendingId) {
            // No pending documents, just open list view
            await this.openSectionList(sectionModel);
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
        
        await this.action.doAction({
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

    // Open R and R Scheme form directly (one per project)
    async openRRSchemeForm() {
        if (!this.checkProjectSelected()) {
            return;
        }

        try {
            const action = await this.orm.call(
                'bhu.section18.rr.scheme',
                'action_open_rr_scheme_form',
                [this.state.selectedProject]
            );
            if (action && action.type) {
                await this.action.doAction(action);
            }
        } catch (error) {
            console.error('Error opening R and R Scheme:', error);
            // Fallback to list view
            await this.action.doAction({
                type: "ir.actions.act_window",
                name: "Section 18 R and R Scheme",
                res_model: 'bhu.section18.rr.scheme',
                view_mode: "list,form",
                views: [[false, "list"], [false, "form"]],
                target: "current",
            });
        }
    }

    // Check if all items in a section are approved
    isAllApproved(sectionInfo) {
        if (!sectionInfo) {
            return true;
        }
        // Check if all are approved (no submitted or draft)
        return sectionInfo.submitted_count === 0 && sectionInfo.draft_count === 0;
    }

    // Open surveys filtered by state (for department dashboard)
    async openSurveysByState(state) {
        let domain = this.getDomain();
        
        // Add state filter if provided
        if (state === 'draft') {
            domain.push(['state', '=', 'draft']);
        } else if (state === 'submitted') {
            domain.push(['state', '=', 'submitted']);
        } else if (state === 'approved') {
            domain.push(['state', '=', 'approved']);
        } else if (state === 'rejected') {
            domain.push(['state', '=', 'rejected']);
        }
        // If state is null, show all surveys (no additional filter)
        
        await this.action.doAction({
            type: 'ir.actions.act_window',
            name: state ? `${state.charAt(0).toUpperCase() + state.slice(1)} Surveys` : 'All Surveys',
            res_model: 'bhu.survey',
            view_mode: 'list,form',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
            target: 'current',
            context: {
                'default_project_id': this.state.selectedProject || false,
                'default_village_id': this.state.selectedVillage || false,
            },
        });
    }

    // Get section name from model
    getSectionName(model) {
        const names = {
            'bhu.survey': 'Surveys',
            'bhu.section4.notification': 'Section 4 Notifications',
            'bhu.section11.preliminary.report': 'Section 11 Reports',
            'bhu.section15.objection': 'Section 15 Objections',
            'bhu.section19.notification': 'Section 19 Notifications',
            'bhu.expert.committee.report': 'Expert Committee Reports',
            'bhu.sia.team': 'SIA Teams',
            'bhu.section18.rr.scheme': 'Section 18 R and R Scheme',
            'bhu.draft.award': 'Draft Awards',
            'bhu.section23.award': 'Section 23 Awards',
        };
        return names[model] || model;
    }

    toString(value) {
        return value ? String(value) : '';
    }
}

// ========== Register Dashboard Types ==========
// Register each dashboard type from configuration
for (const [dashboardType, config] of Object.entries(DASHBOARD_CONFIG)) {
    // Create a class for this dashboard type
    const DashboardClass = class extends UnifiedDashboard {
        static template = config.template;
        
        setup() {
            this.dashboardType = dashboardType;
            super.setup();
        }
    };
    
    // Register with Odoo
    registry.category("actions").add(config.registryKey, DashboardClass);
}

