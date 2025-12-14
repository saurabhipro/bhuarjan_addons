/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class DepartmentDashboard extends Component {
    static template = "bhuarjan.DepartmentDashboardTemplate";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            selectedDepartment: null,
            selectedDepartmentName: null,
            selectedProject: null,
            selectedProjectName: null,
            selectedVillage: null,
            departments: [],
            projects: [],
            villages: [],
            stats: {
                survey_total: 0,
                survey_draft: 0,
                survey_submitted: 0,
                survey_approved: 0,
                survey_rejected: 0,
                survey_completion_percent: 0,
                survey_info: null,
            },
            lastUpdate: null,
        });

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

    async loadInitialData() {
        try {
            console.log("Loading initial data for department user...");
            
            // Get user's locked department from project master
            const userDepartment = await this.orm.call(
                "bhuarjan.dashboard",
                "get_department_user_department",
                []
            );

            console.log("Department response from backend:", userDepartment);
            console.log("Response type:", typeof userDepartment);
            console.log("Response keys:", userDepartment ? Object.keys(userDepartment) : 'null');

            if (userDepartment) {
                // Handle both object and array responses
                const deptId = userDepartment.id || (Array.isArray(userDepartment) && userDepartment[0]?.id);
                const deptName = userDepartment.name || (Array.isArray(userDepartment) && userDepartment[0]?.name);
                
                if (deptId) {
                    this.state.selectedDepartment = deptId;
                    this.state.selectedDepartmentName = deptName || `Department ${deptId}`;
                    this.state.departments = [{
                        id: deptId,
                        name: deptName || `Department ${deptId}`
                    }];
                    console.log("Successfully loaded department:", {
                        id: this.state.selectedDepartment,
                        name: this.state.selectedDepartmentName
                    });
                } else {
                    console.error("Department response missing id:", userDepartment);
                    this.notification.add("Department data format error. Please check server logs.", { 
                        type: "warning",
                        sticky: true
                    });
                }
            } else {
                console.warn("No department found for user. Response:", userDepartment);
                this.notification.add("No department assigned to your projects. Please ensure: 1) You are mapped to a project, 2) The project has a department assigned. Contact administrator if issue persists.", { 
                    type: "warning",
                    sticky: true
                });
            }

            // Load mapped projects for the department
            if (this.state.selectedDepartment) {
                await this.loadProjects();
            } else {
                console.warn("Cannot load projects - no department selected");
            }
        } catch (error) {
            console.error("Error loading initial data:", error);
            console.error("Error stack:", error.stack);
            this.notification.add("Error loading department information: " + (error.message || String(error)), { 
                type: "danger",
                sticky: true
            });
        }
    }

    async loadProjects() {
        try {
            const projects = await this.orm.call(
                "bhuarjan.dashboard",
                "get_department_user_projects",
                [this.state.selectedDepartment]
            );
            this.state.projects = projects || [];
            
            // Auto-select first project if only one
            if (this.state.projects.length === 1 && !this.state.selectedProject) {
                this.state.selectedProject = this.state.projects[0].id;
                this.state.selectedProjectName = this.state.projects[0].name;
                await this.loadVillages();
            }
        } catch (error) {
            console.error("Error loading projects:", error);
            this.state.projects = [];
        }
    }

    async loadVillages() {
        try {
            if (!this.state.selectedProject) {
                this.state.villages = [];
                return;
            }
            const villages = await this.orm.call(
                "bhuarjan.dashboard",
                "get_villages_by_project",
                [this.state.selectedProject]
            );
            this.state.villages = villages || [];
        } catch (error) {
            console.error("Error loading villages:", error);
            this.state.villages = [];
        }
    }

    async loadDashboardData() {
        try {
            this.state.loading = true;
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
            
            console.log("Received stats:", stats);

            if (stats) {
                this.state.stats = {
                    survey_total: stats.total_surveys || 0,
                    survey_draft: stats.draft_surveys || 0,
                    survey_submitted: stats.submitted_surveys || 0,
                    survey_approved: stats.approved_surveys || 0,
                    survey_rejected: stats.rejected_surveys || 0,
                    survey_completion_percent: stats.survey_completion_percent || 0,
                    survey_info: {
                        total: stats.total_surveys || 0,
                        draft_count: stats.draft_surveys || 0,
                        submitted_count: stats.submitted_surveys || 0,
                        approved_count: stats.approved_surveys || 0,
                        rejected_count: stats.rejected_surveys || 0,
                        is_completed: stats.survey_completion_percent === 100,
                    },
                };
            }
            
            this.state.lastUpdate = new Date().toLocaleTimeString();
            this.state.loading = false;
        } catch (error) {
            console.error("Error loading dashboard:", error);
            this.state.loading = false;
        }
    }

    async onProjectChange(ev) {
        const value = ev.target.value;
        const projectId = value ? parseInt(value, 10) : null;
        this.state.selectedProject = projectId;
        
        if (projectId) {
            const project = this.state.projects.find(p => p.id === projectId);
            this.state.selectedProjectName = project ? project.name : null;
            await this.loadVillages();
            
            // Clear village selection if current village doesn't belong to new project
            if (this.state.selectedVillage) {
                const villageExists = this.state.villages.find(v => v.id === this.state.selectedVillage);
                if (!villageExists) {
                    this.state.selectedVillage = null;
                }
            }
        } else {
            this.state.selectedProjectName = null;
            this.state.selectedVillage = null;
            this.state.villages = [];
        }
        
        await this.loadDashboardData();
    }

    async onVillageChange(ev) {
        const value = ev.target.value;
        const villageId = value ? parseInt(value, 10) : null;
        this.state.selectedVillage = villageId;
        await this.loadDashboardData();
    }

    toString(value) {
        return value ? String(value) : "";
    }

    async openFirstDocument(model, info) {
        try {
            if (!info || !info.total || info.total === 0) {
                await this.openSectionList(model);
                return;
            }

            // Get the first record
            const records = await this.orm.searchRead(
                model,
                this.getDomain(),
                ["id"],
                { limit: 1 }
            );

            if (records && records.length > 0) {
                const domain = this.getDomain();
                await this.action.doAction({
                    type: 'ir.actions.act_window',
                    name: 'Surveys',
                    res_model: model,
                    res_id: records[0].id,
                    view_mode: 'form',
                    views: [[false, 'form']],
                    domain: domain,
                    target: 'current',
                    context: {
                        'default_project_id': this.state.selectedProject || false,
                        'default_village_id': this.state.selectedVillage || false,
                    },
                });
            } else {
                await this.openSectionList(model);
            }
        } catch (error) {
            console.error("Error opening document:", error);
            await this.openSectionList(model);
        }
    }

    async openSectionList(model) {
        const domain = this.getDomain();
        await this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Surveys',
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
}

// Register the component
registry.category("actions").add("bhuarjan.department_dashboard", DepartmentDashboard);
