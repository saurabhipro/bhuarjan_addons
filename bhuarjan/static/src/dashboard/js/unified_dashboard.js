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
            'section8_total': 'section8_total',
            'section8_draft': 'section8_draft',
            'section8_approved': 'section8_approved',
            'section8_rejected': 'section8_rejected',
            'section23_award_total': 'section23_award_total',
            'section23_award_draft': 'section23_award_draft',
            'section23_award_submitted': 'section23_award_submitted',
            'section23_award_approved': 'section23_award_approved',
            'section23_award_send_back': 'section23_award_send_back',
            'section23_award_completion_percent': 'section23_award_completion_percent',
            'payment_file_total': 'payment_file_total',
            'payment_file_draft': 'payment_file_draft',
            'payment_file_generated': 'payment_file_generated',
            'payment_file_completion_percent': 'payment_file_completion_percent',
            'payment_file_info': 'payment_file_info',
            'reconciliation_total': 'reconciliation_total',
            'reconciliation_draft': 'reconciliation_draft',
            'reconciliation_processed': 'reconciliation_processed',
            'reconciliation_completed': 'reconciliation_completed',
            'reconciliation_completion_percent': 'reconciliation_completion_percent',
            'reconciliation_info': 'reconciliation_info',
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
            'section8_total': 'section8_total',
            'section8_draft': 'section8_draft',
            'section8_approved': 'section8_approved',
            'section8_rejected': 'section8_rejected',
            'section23_award_total': 'section23_award_total',
            'section23_award_draft': 'section23_award_draft',
            'section23_award_submitted': 'section23_award_submitted',
            'section23_award_approved': 'section23_award_approved',
            'section23_award_send_back': 'section23_award_send_back',
            'section23_award_completion_percent': 'section23_award_completion_percent',
            'payment_file_total': 'payment_file_total',
            'payment_file_draft': 'payment_file_draft',
            'payment_file_generated': 'payment_file_generated',
            'payment_file_completion_percent': 'payment_file_completion_percent',
            'payment_file_info': 'payment_file_info',
            'reconciliation_total': 'reconciliation_total',
            'reconciliation_draft': 'reconciliation_draft',
            'reconciliation_processed': 'reconciliation_processed',
            'reconciliation_completed': 'reconciliation_completed',
            'reconciliation_completion_percent': 'reconciliation_completion_percent',
            'reconciliation_info': 'reconciliation_info',
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
            'section8_total': 'section8_total',
            'section8_draft': 'section8_draft',
            'section8_approved': 'section8_approved',
            'section8_rejected': 'section8_rejected',
            'section23_award_total': 'section23_award_total',
            'section23_award_draft': 'section23_award_draft',
            'section23_award_submitted': 'section23_award_submitted',
            'section23_award_approved': 'section23_award_approved',
            'section23_award_send_back': 'section23_award_send_back',
            'section23_award_completion_percent': 'section23_award_completion_percent',
            'payment_file_total': 'payment_file_total',
            'payment_file_draft': 'payment_file_draft',
            'payment_file_generated': 'payment_file_generated',
            'payment_file_completion_percent': 'payment_file_completion_percent',
            'payment_file_info': 'payment_file_info',
            'reconciliation_total': 'reconciliation_total',
            'reconciliation_draft': 'reconciliation_draft',
            'reconciliation_processed': 'reconciliation_processed',
            'reconciliation_completed': 'reconciliation_completed',
            'reconciliation_completion_percent': 'reconciliation_completion_percent',
            'reconciliation_info': 'reconciliation_info',
        }
    },
    'department': {
        template: 'bhuarjan.DepartmentDashboardTemplate',
        registryKey: 'bhuarjan.department_dashboard',
        pageTitle: 'Department User Dashboard',
        localStoragePrefix: 'department_dashboard',
        showDepartmentFilter: false, // Department users have only one department - no dropdown needed
        showProjectFilter: true,
        showVillageFilter: true,
        statsMapping: {
            'survey_total': 'survey_total',
            'survey_draft': 'survey_draft',
            'survey_submitted': 'survey_submitted',
            'survey_approved': 'survey_approved',
            'survey_rejected': 'survey_rejected',
            'survey_completion_percent': 'survey_completion_percent',
            'section8_total': 'section8_total',
            'section8_draft': 'section8_draft',
            'section8_approved': 'section8_approved',
            'section8_rejected': 'section8_rejected',
            'section23_award_total': 'section23_award_total',
            'section23_award_draft': 'section23_award_draft',
            'section23_award_submitted': 'section23_award_submitted',
            'section23_award_approved': 'section23_award_approved',
            'section23_award_send_back': 'section23_award_send_back',
            'section23_award_completion_percent': 'section23_award_completion_percent',
            'payment_file_total': 'payment_file_total',
            'payment_file_draft': 'payment_file_draft',
            'payment_file_generated': 'payment_file_generated',
            'payment_file_completion_percent': 'payment_file_completion_percent',
            'payment_file_info': 'payment_file_info',
            'reconciliation_total': 'reconciliation_total',
            'reconciliation_draft': 'reconciliation_draft',
            'reconciliation_processed': 'reconciliation_processed',
            'reconciliation_completed': 'reconciliation_completed',
            'reconciliation_completion_percent': 'reconciliation_completion_percent',
            'reconciliation_info': 'reconciliation_info',
        }
    },
    'district': {
        template: 'bhuarjan.DistrictDashboardTemplate',
        registryKey: 'bhuarjan.district_dashboard',
        pageTitle: 'District Admin Dashboard',
        localStoragePrefix: 'district_dashboard',
        showDepartmentFilter: true,
        showProjectFilter: true,
        showVillageFilter: true,
        isReadOnly: true, // District admin can only view, not create
        statsMapping: {
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
            'section8_total': 'section8_total',
            'section8_draft': 'section8_draft',
            'section8_approved': 'section8_approved',
            'section8_rejected': 'section8_rejected',
            'section23_award_total': 'section23_award_total',
            'section23_award_draft': 'section23_award_draft',
            'section23_award_submitted': 'section23_award_submitted',
            'section23_award_approved': 'section23_award_approved',
            'section23_award_send_back': 'section23_award_send_back',
            'section23_award_completion_percent': 'section23_award_completion_percent',
            'payment_file_total': 'payment_file_total',
            'payment_file_draft': 'payment_file_draft',
            'payment_file_generated': 'payment_file_generated',
            'payment_file_completion_percent': 'payment_file_completion_percent',
            'payment_file_info': 'payment_file_info',
            'reconciliation_total': 'reconciliation_total',
            'reconciliation_draft': 'reconciliation_draft',
            'reconciliation_processed': 'reconciliation_processed',
            'reconciliation_completed': 'reconciliation_completed',
            'reconciliation_completion_percent': 'reconciliation_completion_percent',
            'reconciliation_info': 'reconciliation_info',
        }
    },

};

export class UnifiedDashboard extends Component {
    // Template will be set dynamically based on dashboard type
    static template = "bhuarjan.SDMTemplate"; // Default, will be overridden

    setup() {
        // Determine dashboard type from props or context
        // Only set dashboardType if not already set by child class
        if (!this.dashboardType) {
            this.dashboardType = this.props.dashboardType || 'sdm';
        }
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
        const savedVillageName = localStorage.getItem(`${localStoragePrefix}_village_name`);

        // Initialize state based on configuration
        const initialState = {
            loading: true,
            selectedDepartment: savedDepartment ? parseInt(savedDepartment, 10) : null,
            selectedProject: savedProject ? parseInt(savedProject, 10) : null,
            selectedProjectName: savedProjectName || null,
            selectedVillage: savedVillage ? parseInt(savedVillage, 10) : null,
            selectedVillageName: savedVillageName || null,
            departments: [],
            projects: [],
            villages: [],
            isCollector: false,
            isProjectExempt: false,
            isDisplacement: false,
            isReadOnly: this.config.isReadOnly || false, // District admin is read-only
            allowedSectionNames: [], // Sections mapped to project'
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
        if (this.dashboardType === 'sdm' || this.dashboardType === 'collector' || this.dashboardType === 'district' || this.dashboardType === 'admin') {
            stats.section4_info = null;
            stats.section11_info = null;
            stats.section15_info = null;
            stats.section19_info = null;
            stats.expert_info = null;
            stats.sia_info = null;
            stats.section8_info = null;
            stats.survey_info = null;
            stats.draft_award_info = null;
            stats.section23_award_info = null;
        }

        return stats;
    }

    async loadInitialData() {
        const localStoragePrefix = this.config.localStoragePrefix;

        // For department dashboard, always load department (even if filter is hidden)
        if (this.dashboardType === 'department') {
            await this.loadDepartments();
            // Department should now be auto-selected and projects loaded
        } else if (this.config.showDepartmentFilter) {
            // For other dashboards, load departments if filter is shown
            await this.loadDepartments();
        } else if (this.config.initialDataMethod) {
            // Custom data loading method
            await this.loadUserDepartment();
        }

        // Load projects (if not already loaded by loadDepartments for department dashboard)
        // For department dashboard, projects are already loaded in loadDepartments()
        // For collector dashboards, allow all projects without department selection
        // For others, only load if department is selected
        if (this.dashboardType === 'collector') {
            await this.loadProjects();
        } else if (this.dashboardType !== 'department' && (this.state.selectedDepartment || !this.config.showDepartmentFilter)) {
            await this.loadProjects();
        }

        // Load villages if project is selected
        if (this.state.selectedProject) {
            await this.loadVillages();

            // Restore saved village name after villages are loaded
            const savedVillageName = localStorage.getItem(`${localStoragePrefix}_village_name`);
            if (this.state.selectedVillage && this.state.villages.length > 0) {
                // If we have a saved village name, use it; otherwise get it from the loaded list
                if (savedVillageName) {
                    this.state.selectedVillageName = savedVillageName;
                } else {
                    const village = this.state.villages.find(v => v.id === this.state.selectedVillage);
                    if (village) {
                        this.state.selectedVillageName = village.name;
                        localStorage.setItem(`${localStoragePrefix}_village_name`, village.name);
                    }
                }
            } else {
                this.state.selectedVillageName = null;
            }
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
            // Auto-select department for department users (they only have one department)
            if (this.dashboardType === 'department' && this.state.departments.length === 1) {
                this.state.selectedDepartment = this.state.departments[0].id;
                this.state.selectedDepartmentName = this.state.departments[0].name;
                // Save to localStorage
                const prefix = this.config.localStoragePrefix;
                localStorage.setItem(`${prefix}_department`, String(this.state.selectedDepartment));
                // Auto-load projects after department selection
                await this.loadProjects();
            }
        } catch (error) {
            console.error("Error loading departments:", error);
            this.state.departments = [];
        }
    }

    async loadProjects() {
        // Get department ID from state
        // For department dashboard, use selectedDepartment even if filter is hidden
        const departmentId = this.state.selectedDepartment || null;

        // For most dashboards, if department filter is shown and no department is selected, clear projects
        if (departmentId === null && this.config.showDepartmentFilter && !['department', 'collector'].includes(this.dashboardType)) {
            this.state.projects = [];
            return;
        }

        try {
            // Pass departmentId to get_user_projects to filter projects by department
            const projects = await this.orm.call(
                "bhuarjan.dashboard",
                "get_user_projects",
                [departmentId]
            );

            // Ensure we have an array
            const projectsArray = Array.isArray(projects) ? projects : [];
            this.state.projects = projectsArray;
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
                if (stats.is_displacement !== undefined) {
                    this.state.isDisplacement = stats.is_displacement;
                }
                if (stats.user_type !== undefined) {
                    this.state.isAdmin = (stats.user_type === 'admin');
                }
                // Store allowed section names from project's law
                if (stats.allowed_section_names !== undefined) {
                    this.state.allowedSectionNames = stats.allowed_section_names || [];
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
        if (backendStats.section8_info) {
            this.state.stats.section8_info = backendStats.section8_info;
        }
        if (backendStats.draft_award_info) {
            this.state.stats.draft_award_info = backendStats.draft_award_info;
        }
        if (backendStats.section23_award_info) {
            this.state.stats.section23_award_info = backendStats.section23_award_info;
        }
    }

    async onDepartmentChange(ev) {
        if (!this.config.showDepartmentFilter) return;

        const value = ev.target.value;
        const departmentId = value && value !== '' ? parseInt(value, 10) : null;

        // Update state
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
        this.state.selectedProjectName = null;
        this.state.selectedVillage = null;
        this.state.selectedVillageName = null;
        this.state.projects = [];
        this.state.villages = [];
        localStorage.removeItem(`${prefix}_project`);
        localStorage.removeItem(`${prefix}_project_name`);
        localStorage.removeItem(`${prefix}_village`);
        localStorage.removeItem(`${prefix}_village_name`);

        // Load projects for the selected department
        if (departmentId) {
            try {
                await this.loadProjects();
            } catch (error) {
                console.error("Error in loadProjects after department change:", error);
            }
        }

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
                this.state.selectedVillageName = null;
                localStorage.removeItem(`${prefix}_village`);
                localStorage.removeItem(`${prefix}_village_name`);
            } else {
                // Update village name if village still exists
                this.state.selectedVillageName = currentVillage.name;
                localStorage.setItem(`${prefix}_village_name`, currentVillage.name);
            }
        } else {
            this.state.selectedVillage = null;
            this.state.selectedVillageName = null;
            this.state.villages = [];
            localStorage.removeItem(`${prefix}_village`);
            localStorage.removeItem(`${prefix}_village_name`);
        }

        // Save selection to server for bulk approval
        await this.saveDashboardSelection();

        await this.loadDashboardData();
    }

    async onVillageChange(ev) {
        if (!this.config.showVillageFilter) return;

        const value = ev.target.value;
        const villageId = value ? parseInt(value, 10) : null;
        this.state.selectedVillage = villageId;

        // Get and save village name
        const prefix = this.config.localStoragePrefix;
        if (villageId) {
            localStorage.setItem(`${prefix}_village`, String(villageId));
            const village = this.state.villages.find(v => v.id === villageId);
            if (village) {
                this.state.selectedVillageName = village.name;
                localStorage.setItem(`${prefix}_village_name`, village.name);
            }
        } else {
            localStorage.removeItem(`${prefix}_village`);
            localStorage.removeItem(`${prefix}_village_name`);
            this.state.selectedVillageName = null;
        }

        // Save selection to server for bulk approval
        await this.saveDashboardSelection();

        await this.loadDashboardData();
    }

    async onSubmitFilters() {
        await this.loadDashboardData();
    }

    async saveDashboardSelection() {
        /**
         * Save the current dashboard selection (project and village) to the server
         * This allows the bulk approval wizard to retrieve these values
         */
        try {
            await this.orm.call(
                "bhuarjan.dashboard",
                "save_dashboard_selection",
                [this.state.selectedProject || false, this.state.selectedVillage || false]
            );
        } catch (error) {
            console.error("Error saving dashboard selection:", error);
        }
    }

    async downloadForm10() {
        /**
         * Open Form 10 download wizard with pre-filled project and village
         */
        if (!this.state.selectedProject) {
            this.notification.add(_t("Please select a project first"), { type: "warning" });
            return;
        }

        if (!this.state.selectedVillage) {
            this.notification.add(_t("Please select a village first"), { type: "warning" });
            return;
        }

        try {
            await this.action.doAction({
                type: 'ir.actions.act_window',
                name: 'Download Form 10',
                res_model: 'report.wizard',
                view_mode: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    'default_project_id': this.state.selectedProject,
                    'default_village_id': this.state.selectedVillage,
                    'default_export_type': 'excel',  // Default to Excel export
                },
            });
        } catch (error) {
            console.error("Error opening Form 10 download wizard:", error);
        }
    }

    async downloadGanttChart() {
        if (!this.state.selectedProject) {
            this.notification.add(_t("Please select a project first"), { type: "warning" });
            return;
        }

        try {
            // Create wizard record
            const wizardId = await this.orm.create("bhuarjan.gantt.report.wizard", [{
                project_id: parseInt(this.state.selectedProject)
            }]);

            // Call method to get download action
            const action = await this.orm.call("bhuarjan.gantt.report.wizard", "action_download_report", [wizardId]);

            // Execute action
            await this.action.doAction(action);

        } catch (error) {
            console.error("Error generating Gantt report:", error);
            this.notification.add(_t("Error generating report"), { type: "danger" });
        }
    }

    // Helper methods for domain building
    getDomain(model = null) {
        const domain = [];

        // Models that have department_id field
        const modelsWithDepartment = [
            'bhu.project',
            'bhu.section4.notification',
            'bhu.survey',
            'bhu.section23.award',
            'bhu.draft.award',  // Legacy, keeping for compatibility
            'bhu.payment.file',
            'bhu.payment.reconciliation.bank',
        ];

        // Only add department_id if model has this field
        if (this.state.selectedDepartment && (!model || modelsWithDepartment.includes(model))) {
            domain.push(['department_id', '=', parseInt(this.state.selectedDepartment)]);
        }

        if (this.state.selectedProject) {
            domain.push(['project_id', '=', parseInt(this.state.selectedProject)]);
        }

        // Models that have village_id field and should be filtered by village selection
        const modelsWithVillage = [
            'bhu.survey',
            'bhu.section4.notification',
            'bhu.section11.preliminary.report',
            'bhu.section15.objection',
            'bhu.section19.notification',
            'bhu.section21.notification',
            'bhu.section23.award',
            'bhu.section20a.railways',
            'bhu.section20d.railways',
            'bhu.section20e.railways',
            'bhu.section3a.nh',
            'bhu.section3c.nh',
            'bhu.section3d.nh',
            'bhu.mutual.consent.policy',
            'bhu.payment.file',
            'bhu.payment.reconciliation.bank',
        ];

        if (this.state.selectedVillage && (!model || modelsWithVillage.includes(model))) {
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

        const domain = this.getDomain(model);
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

        const domain = this.getDomain(sectionModel);

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
                    'active_project_id': this.state.selectedProject || false,
                    'active_village_id': this.state.selectedVillage || false,
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

        // District admin cannot create records - read-only mode
        if (this.config.isReadOnly) {
            this.notification.add(_t("District Admin can only view data. Cannot create records."), {
                type: "warning",
                sticky: false
            });
            return;
        }

        // Special handling for R and R Scheme - open form directly (one per project)
        if (sectionModel === 'bhu.section18.rr.scheme') {
            await this.openRRSchemeForm();
            return;
        }

        // Village-specific sections that require village selection
        const villageSpecificSections = {
            'bhu.section4.notification': 'Section 4 Notification',
            'bhu.section11.preliminary.report': 'Section 11 Preliminary Report',
            'bhu.section19.notification': 'Section 19 Notification',
            'bhu.section21.notification': 'Section 21 Notification',
            'bhu.section23.award': 'Section 23 Award',
            'bhu.section20a.railways': 'Section 20 A (Railways)',
            'bhu.section20d.railways': 'Section 20 D (Railways)',
            'bhu.section20e.railways': 'Section 20 E (Railways)',
            'bhu.section3a.nh': 'Section 3A (NH)',
            'bhu.section3c.nh': 'Section 3C (NH)',
            'bhu.section3d.nh': 'Section 3D (NH)',
            'bhu.mutual.consent.policy': 'Mutual Consent Policy',
            'bhu.payment.file': 'Payment File',
            'bhu.payment.reconciliation.bank': 'Payment Reconciliation',
        };

        if (villageSpecificSections[sectionModel]) {
            if (!this.state.selectedVillage) {
                this.notification.add(_t(`Please select a village first before creating ${villageSpecificSections[sectionModel]}.`), {
                    type: "warning",
                    sticky: true
                });
                return;
            }
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

        const domain = this.getDomain(sectionModel);
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
        let domain = this.getDomain('bhu.survey');  // Survey has department_id

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
                'active_project_id': this.state.selectedProject || false,
                'active_village_id': this.state.selectedVillage || false,
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
            'bhu.section21.notification': 'Section 21 Notifications',
            'bhu.section23.award': 'Section 23 Awards',
            'bhu.section20a.railways': 'Section 20 A (Railways)',
            'bhu.section20d.railways': 'Section 20 D (Railways)',
            'bhu.section20e.railways': 'Section 20 E (Railways)',
            'bhu.section3a.nh': 'Section 3A (NH)',
            'bhu.section3c.nh': 'Section 3C (NH)',
            'bhu.section3d.nh': 'Section 3D (NH)',
            'bhu.mutual.consent.policy': 'Mutual Consent Policy',
            'bhu.payment.file': 'Payment File',
            'bhu.payment.reconciliation.bank': 'Payment Reconciliation',
        };
        return names[model] || model;
    }

    // Mapping between dashboard section display names and section master names
    getSectionMasterName(dashboardSectionName) {
        const mapping = {
            'Surveys': 'Surveys',
            'Create SIA Team': '(Sec 4) Create SIA Team',  // Map to backend name (with Sec 4 prefix)
            '(Sec 4) Create SIA Team': '(Sec 4) Create SIA Team',
            '(Sec 4) Section 4 Notifications': '(Sec 4) Section 4 Notifications',
            'Expert Group': 'Expert Group',
            'Section 8': 'Section 8',
            'Section 11 Notifications': 'Section 11 Notifications',
            '(Sec 15) Objections': '(Sec 15) Objections',
            'Section 18 R and R Scheme': 'Section 18 R and R Scheme',
            '(Sec 19) Section 19 Notifications': '(Sec 19) Section 19 Notifications',
            'Sec 21 notice': 'Sec 21 notice',
            'Section 23 Award': 'Section 23 Award',
            'Sec 20 A (Railways)': 'Sec 20 A (Railways)',
            'Sec 20 D (Railways)': 'Sec 20 D (Objection) (Railways)',
            'Sec 20 E (Railways)': 'Sec 20 E (Railways)',
            'Sec 3A (NH)': 'Sec 3A (NH)',
            'Sec 3C (NH)': 'Sec 3C (Objection) (NH)',
            'Sec 3D (NH)': 'Sec 3D (NH)',
            'Mutual Consent': 'आपसी सहमति की क्रय नीति (Only in रायगढ़ and पसौर)',
            'Payment File': 'Payment File',
            'Payment Reconciliation': 'Payment Reconciliation',
        };
        return mapping[dashboardSectionName] || dashboardSectionName;
    }

    // Check if a section should be visible based on project's law
    getStepNumber(sectionName, defaultText) {
        if (!this.state.allowedSectionNames) {
            return defaultText;
        }

        // Check for Railways
        const isRailways = this.state.allowedSectionNames.includes('Sec 20 A (Railways)');
        if (isRailways) {
            const steps = {
                'Surveys': 'Step 1',
                'Sec 20 A (Railways)': 'Step 2',
                'Sec 20 D (Objection) (Railways)': 'Step 3',
                'Sec 20 E (Railways)': 'Step 4'
            };
            if (steps[sectionName]) return steps[sectionName];
        }

        // Check for NHAI
        const isNHAI = this.state.allowedSectionNames.includes('Sec 3A (NH)');
        if (isNHAI) {
            const steps = {
                'Surveys': 'Step 1',
                'Sec 3A (NH)': 'Step 2',
                'Sec 3C (Objection) (NH)': 'Step 3',
                'Sec 3D (NH)': 'Step 4'
            };
            if (steps[sectionName]) return steps[sectionName];
        }

        return defaultText;
    }

    isSectionVisible(dashboardSectionName) {
        try {
            // Railway and NH sections require department to be selected
            // Check both dashboard names and mapped names
            const railwayNhSections = [
                'Sec 20 A (Railways)',
                'Sec 20 D (Railways)',  // Dashboard name
                'Sec 20 D (Objection) (Railways)',  // Mapped name
                'Sec 20 E (Railways)',
                'Sec 3A (NH)',
                'Sec 3C (NH)',  // Dashboard name
                'Sec 3C (Objection) (NH)',  // Mapped name
                'Sec 3D (NH)'
            ];

            // Check if this is a Railway or NH section
            const isRailwayNh = railwayNhSections.includes(dashboardSectionName) ||
                dashboardSectionName.includes('Railways') ||
                dashboardSectionName.includes('(NH)');

            if (isRailwayNh) {
                // For Railway and NH sections, require department to be selected
                if (!this.state || !this.state.selectedDepartment) {
                    return false;
                }
            }

            // If no project is selected, show all sections (except Railway/NH which need department)
            if (!this.state || !this.state.selectedProject) {
                return true;
            }

            // Always show Payment File and Payment Reconciliation if they are present
            if (dashboardSectionName === 'Payment File' || dashboardSectionName === 'Payment Reconciliation') {
                return true;
            }

            // If project is selected but no allowed sections configured, hide all sections
            // This prevents showing all sections when law master is not configured
            if (!this.state.allowedSectionNames || this.state.allowedSectionNames.length === 0) {
                console.warn(`Project ${this.state.selectedProject} has no law master sections configured. Hiding all sections.`);
                return false;
            }

            // Get the section master name for this dashboard section
            const sectionMasterName = this.getSectionMasterName(dashboardSectionName);

            // Check if this section is in the allowed list
            const isVisible = this.state.allowedSectionNames.includes(sectionMasterName);

            return isVisible;
        } catch (error) {
            console.error('Error in isSectionVisible:', error);
            // On error, show the section to avoid breaking the UI
            return true;
        }
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

