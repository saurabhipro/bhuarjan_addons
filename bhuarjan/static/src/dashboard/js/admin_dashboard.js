/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, onMounted, onWillUnmount, useState, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class AdminDashboard extends Component {
    static template = "bhuarjan.AdminDashboardTemplate";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            selectedDepartment: null,
            selectedProject: null,
            selectedVillage: null,
            departments: [],
            projects: [],
            villages: [],
            stats: {
                // Master Data
                total_districts: 0,
                total_sub_divisions: 0,
                total_tehsils: 0,
                total_villages: 0,
                total_projects: 0,
                total_departments: 0,
                total_landowners: 0,
                total_rate_masters: 0,
                active_mobile_users: 0,
                // Surveys
                total_surveys: 0,
                total_surveys_done: 0,
                draft_surveys: 0,
                approved_surveys: 0,
                rejected_surveys: 0,
                pending_surveys: 0,
                submitted_surveys: 0,
                // Section counts
                section4_total: 0, section4_draft: 0, section4_submitted: 0, section4_approved: 0, section4_send_back: 0,
                section11_total: 0, section11_draft: 0, section11_submitted: 0, section11_approved: 0, section11_send_back: 0,
                section19_total: 0, section19_draft: 0, section19_submitted: 0, section19_approved: 0, section19_send_back: 0,
                section15_total: 0, section15_draft: 0, section15_submitted: 0, section15_approved: 0, section15_send_back: 0,
                expert_committee_total: 0, expert_committee_draft: 0, expert_committee_submitted: 0, expert_committee_approved: 0, expert_committee_send_back: 0,
                sia_total: 0, sia_draft: 0, sia_submitted: 0, sia_approved: 0, sia_send_back: 0,
            },
            lastUpdate: null,
        });

        this.refreshInterval = null;

        onWillStart(async () => {
            try {
                // Load departments and projects first
                this.state.departments = await this.orm.call("bhuarjan.dashboard", "get_all_departments", []);
                this.state.projects = await this.orm.call("bhuarjan.dashboard", "get_all_projects", []);
                await this.loadDashboardData();
            } catch (error) {
                console.error("Error in onWillStart:", error);
                this.state.loading = false;
            }
        });

        onMounted(() => {
            // Auto-refresh disabled as per user request
            // this.refreshInterval = setInterval(() => {
            //     this.loadDashboardData();
            // }, 30000);
        });

        onWillUnmount(() => {
            if (this.refreshInterval) {
                clearInterval(this.refreshInterval);
            }
            if (this.refreshTimeout) {
                clearTimeout(this.refreshTimeout);
            }
        });
    }

    async loadDashboardData() {
        try {
            this.state.loading = true;
            // Get dashboard stats with optional department, project and village filter
            const filters = {};
            if (this.state.selectedDepartment) {
                filters.department_id = parseInt(this.state.selectedDepartment);
            }
            if (this.state.selectedProject) {
                filters.project_id = parseInt(this.state.selectedProject);
            }
            if (this.state.selectedVillage) {
                filters.village_id = parseInt(this.state.selectedVillage);
            }
            
            console.log("Loading dashboard with filters:", filters);
            
            const stats = await this.orm.call(
                "bhuarjan.dashboard",
                "get_dashboard_stats",
                [filters]
            );

            console.log("Dashboard stats received:", stats);
            
            if (stats) {
                Object.assign(this.state.stats, stats);
                console.log("State stats after assignment:", this.state.stats);
            } else {
                console.warn("No stats returned from server");
            }
            
            this.state.lastUpdate = new Date().toLocaleTimeString();
            this.state.loading = false;
        } catch (error) {
            console.error("Error loading dashboard:", error);
            console.error("Error details:", error.message, error.stack);
            this.state.loading = false;
            try {
                this.notification.add(_t("Error loading dashboard data: " + (error.message || "Unknown error")), { type: "danger" });
            } catch (notifError) {
                console.error("Notification error:", notifError);
            }
        }
    }


    async onRefresh() {
        await this.loadDashboardData();
        try {
            this.notification.add(_t("Dashboard refreshed"), { type: "success" });
        } catch (error) {
            console.error("Notification error:", error);
        }
    }
    
    async onDepartmentChange(ev) {
        this.state.selectedDepartment = ev.target.value ? parseInt(ev.target.value) : null;
        this.state.selectedProject = null; // Reset project when department changes
        this.state.selectedVillage = null; // Reset village when department changes
        
        // Load projects for selected department
        if (this.state.selectedDepartment) {
            try {
                this.state.projects = await this.orm.call("bhuarjan.dashboard", "get_all_projects", [this.state.selectedDepartment]);
            } catch (error) {
                console.error("Error loading projects:", error);
                this.state.projects = [];
            }
        } else {
            // Load all projects if no department selected
            try {
                this.state.projects = await this.orm.call("bhuarjan.dashboard", "get_all_projects", []);
            } catch (error) {
                console.error("Error loading projects:", error);
                this.state.projects = [];
            }
        }
        
        this.state.villages = []; // Clear villages when department changes
    }
    
    async onProjectChange(ev) {
        this.state.selectedProject = ev.target.value ? parseInt(ev.target.value) : null;
        this.state.selectedVillage = null; // Reset village when project changes
        
        // Load villages for selected project
        if (this.state.selectedProject) {
            try {
                this.state.villages = await this.orm.call("bhuarjan.dashboard", "get_villages_by_project", [this.state.selectedProject]);
            } catch (error) {
                console.error("Error loading villages:", error);
                this.state.villages = [];
            }
        } else {
            this.state.villages = [];
        }
    }
    
    async onVillageChange(ev) {
        this.state.selectedVillage = ev.target.value ? parseInt(ev.target.value) : null;
    }
    
    async onSubmitFilters() {
        // Reload dashboard data with all selected filters
        await this.loadDashboardData();
        try {
            this.notification.add(_t("Filters applied"), { type: "success" });
        } catch (error) {
            console.error("Notification error:", error);
        }
    }

    async openAction(actionName) {
        try {
            console.log("Opening action:", actionName);
            
            // Call the action method on the dashboard model (these are @api.model methods, no record needed)
            const action = await this.orm.call(
                "bhuarjan.dashboard",
                actionName,
                []
            );
            
            console.log("Action returned:", action);
            
            if (action && typeof action === 'object') {
                // Check if action has required fields
                if (action.type) {
                    await this.action.doAction(action);
                } else if (action.id) {
                    // If it's just an ID, try to load it
                    const fullAction = await this.orm.call("ir.actions.act_window", "read", [[action.id]]);
                    if (fullAction && fullAction.length > 0) {
                        await this.action.doAction(fullAction[0]);
                    } else {
                        throw new Error("Could not load action with ID: " + action.id);
                    }
                } else {
                    console.error("Invalid action format:", action);
                    throw new Error("Action returned invalid format");
                }
            } else {
                console.error("No action returned from server for:", actionName);
                throw new Error("No action returned for: " + actionName);
            }
        } catch (error) {
            console.error(`Error opening ${actionName}:`, error);
            console.error("Error details:", error.message, error.stack);
            try {
                this.notification.add(_t("Error: " + (error.message || actionName)), { type: "danger" });
            } catch (notifError) {
                console.error("Notification error:", notifError);
            }
        }
    }
}

// Register the action
registry.category("actions").add(
    "bhuarjan.admin_dashboard",
    AdminDashboard
);

