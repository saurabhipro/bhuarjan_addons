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
            selectedProject: null,
            selectedVillage: null,
            departments: [],
            projects: [],
            villages: [],
            stats: {
                // Survey counts - main focus for Department Users
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
                await this.loadDashboardData();
            } catch (error) {
                console.error("Error in onWillStart:", error);
                this.state.loading = false;
            }
        });
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
            
            // Use the same controller method but filter for department user view
            const stats = await this.orm.call(
                "bhuarjan.dashboard",
                "get_dashboard_stats",
                [filters]
            );

            if (stats) {
                // Only show survey-related stats for Department Users
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

    async openSurveyList() {
        await this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'bhu.survey',
            view_mode: 'list,form',
            name: 'Surveys',
        });
    }

    async openSurveysByState(state) {
        await this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'bhu.survey',
            view_mode: 'list,form',
            domain: [['state', '=', state]],
            name: `Surveys - ${state.charAt(0).toUpperCase() + state.slice(1)}`,
        });
    }
}

// Register the component
registry.category("actions").add("bhuarjan.department_dashboard", DepartmentDashboard);

