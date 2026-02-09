/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { ProjectTimelineDialog } from "../../js/components/project_timeline";
import { _t } from "@web/core/l10n/translation";

export class GroupDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.state = useState({
            projects: [],
            loading: true,
            searchTerm: "",
            sortConfig: {
                field: "create_date",
                direction: "desc"
            },
            stats: {
                total_projects: 0,
                sia_stage: 0,
                section4_stage: 0,
                section11_stage: 0,
                section19_stage: 0,
                section21_stage: 0,
                award_stage: 0,
            }
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        try {
            // Fetch all projects with their current stage information
            const projects = await this.orm.searchRead(
                "bhu.project",
                [["company_id", "in", this.env.services.company.activeCompanyIds]],
                ["name", "code", "department_id", "district_id", "state", "village_ids", "create_date"],
                { order: "create_date desc" }
            );

            // For each project, determine its current stage, counts and last survey date
            for (let project of projects) {
                project.current_stage = await this.determineProjectStage(project.id);
                project.village_count = project.village_ids.length;

                // Fetch last survey date for the project
                try {
                    const lastSurvey = await this.orm.searchRead(
                        "bhu.survey",
                        [["project_id", "=", project.id]],
                        ["survey_date"],
                        { limit: 1, order: "survey_date desc" }
                    );
                    project.last_survey_date = lastSurvey.length > 0 ? lastSurvey[0].survey_date : "No Survey";
                } catch (error) {
                    console.warn("Could not fetch last survey date for project", project.id, error);
                    project.last_survey_date = "N/A";
                }

                // Get total khasras count - with error handling
                try {
                    const khasras = await this.orm.searchRead(
                        "bhu.survey",
                        [["project_id", "=", project.id]],
                        ["id"]
                    );
                    project.total_khasras = khasras.length;
                } catch (error) {
                    console.warn("Could not fetch khasras for project", project.id, error);
                    project.total_khasras = 0;
                }

                // Get total landowners count - with error handling
                try {
                    const landowners = await this.orm.searchRead(
                        "bhu.landowner",
                        [["survey_ids.project_id", "=", project.id]],
                        ["id"]
                    );
                    project.total_landowners = landowners.length;
                } catch (error) {
                    console.warn("Could not fetch landowners for project", project.id, error);
                    project.total_landowners = 0;
                }
            }

            this.state.projects = projects;
            this.state.stats.total_projects = projects.length;

            // Calculate stage statistics
            this.calculateStageStats(projects);

            this.state.loading = false;
        } catch (error) {
            console.error("Error loading dashboard data:", error);
            this.state.loading = false;
        }
    }

    get filteredProjects() {
        let projects = [...this.state.projects];

        // 1. Apply Filtering
        if (this.state.searchTerm) {
            const term = this.state.searchTerm.toLowerCase();
            projects = projects.filter(p =>
                (p.name && p.name.toLowerCase().includes(term)) ||
                (p.code && p.code.toLowerCase().includes(term)) ||
                (p.district_id && p.district_id[1].toLowerCase().includes(term)) ||
                (p.department_id && p.department_id[1].toLowerCase().includes(term))
            );
        }

        // 2. Apply Sorting
        const { field, direction } = this.state.sortConfig;
        projects.sort((a, b) => {
            let valA = this.getFieldValue(a, field);
            let valB = this.getFieldValue(b, field);

            if (valA === null || valA === undefined) valA = "";
            if (valB === null || valB === undefined) valB = "";

            if (valA < valB) return direction === "asc" ? -1 : 1;
            if (valA > valB) return direction === "asc" ? 1 : -1;
            return 0;
        });

        return projects;
    }

    getFieldValue(obj, field) {
        if (field === "department_id" || field === "district_id") {
            return obj[field] ? obj[field][1] : "";
        }
        if (field === "total_khasras" || field === "total_landowners" || field === "village_count") {
            return obj[field] || 0;
        }
        return obj[field];
    }

    onSearchInput(ev) {
        this.state.searchTerm = ev.target.value;
    }

    sortBy(field) {
        if (this.state.sortConfig.field === field) {
            this.state.sortConfig.direction = this.state.sortConfig.direction === "asc" ? "desc" : "asc";
        } else {
            this.state.sortConfig.field = field;
            this.state.sortConfig.direction = "asc";
        }
    }

    getSortIcon(field) {
        if (this.state.sortConfig.field !== field) return "fa-sort text-muted opacity-50";
        return this.state.sortConfig.direction === "asc" ? "fa-sort-up" : "fa-sort-down";
    }

    async openProject(projectId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "bhu.project",
            res_id: projectId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async openDepartment(departmentId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "bhu.department",
            res_id: departmentId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async openDistrict(districtId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "bhu.district",
            res_id: districtId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async determineProjectStage(projectId) {
        // Check stages in reverse order (latest first)

        // Check for Awards (Section 23)
        const awards = await this.orm.searchCount("bhu.section23.award", [
            ["project_id", "=", projectId]
        ]);
        if (awards > 0) return "award";

        // Check for Section 21
        const sec21 = await this.orm.searchCount("bhu.section21.notification", [
            ["project_id", "=", projectId]
        ]);
        if (sec21 > 0) return "section21";

        // Check for Section 19
        const sec19 = await this.orm.searchCount("bhu.section19.notification", [
            ["project_id", "=", projectId]
        ]);
        if (sec19 > 0) return "section19";

        // Check for Section 11
        const sec11 = await this.orm.searchCount("bhu.section11.preliminary.report", [
            ["project_id", "=", projectId]
        ]);
        if (sec11 > 0) return "section11";

        // Check for Section 4
        const sec4 = await this.orm.searchCount("bhu.section4.notification", [
            ["project_id", "=", projectId]
        ]);
        if (sec4 > 0) return "section4";

        // Check for SIA
        const sia = await this.orm.searchCount("bhu.sia.team", [
            ["project_id", "=", projectId]
        ]);
        if (sia > 0) return "sia";

        return "initial";
    }

    async calculateDelay(project) {
        // Calculate delay based on Land Acquisition Act timelines
        const createDate = new Date(project.create_date);
        const today = new Date();
        const daysSinceCreation = Math.floor((today - createDate) / (1000 * 60 * 60 * 24));

        // Define expected timelines as per Act (in days)
        const timelines = {
            sia: 180,          // 6 months for SIA completion
            section4: 210,     // 7 months for Section 4
            section11: 365,    // 12 months for Section 11
            section19: 455,    // 15 months for Section 19
            section21: 545,    // 18 months for Section 21
            award: 730         // 24 months for Award
        };

        let expectedDays = 0;
        let stageName = "";

        switch (project.current_stage) {
            case "sia":
                expectedDays = timelines.sia;
                stageName = "SIA";
                break;
            case "section4":
                expectedDays = timelines.section4;
                stageName = "Section 4";
                break;
            case "section11":
                expectedDays = timelines.section11;
                stageName = "Section 11";
                break;
            case "section19":
                expectedDays = timelines.section19;
                stageName = "Section 19";
                break;
            case "section21":
                expectedDays = timelines.section21;
                stageName = "Section 21";
                break;
            case "award":
                expectedDays = timelines.award;
                stageName = "Award";
                break;
            default:
                expectedDays = 90; // 3 months for initial stage
                stageName = "Initial";
        }

        const delayDays = daysSinceCreation - expectedDays;
        const isDelayed = delayDays > 0;

        return {
            is_delayed: isDelayed,
            delay_days: Math.abs(delayDays),
            days_since_creation: daysSinceCreation,
            expected_days: expectedDays,
            stage_name: stageName
        };
    }

    calculateStageStats(projects) {
        const stageCounts = {
            sia: 0,
            section4: 0,
            section11: 0,
            section19: 0,
            section21: 0,
            award: 0,
            initial: 0
        };

        projects.forEach(project => {
            if (stageCounts[project.current_stage] !== undefined) {
                stageCounts[project.current_stage]++;
            }
        });

        this.state.stats.sia_stage = stageCounts.sia;
        this.state.stats.section4_stage = stageCounts.section4;
        this.state.stats.section11_stage = stageCounts.section11;
        this.state.stats.section19_stage = stageCounts.section19;
        this.state.stats.section21_stage = stageCounts.section21;
        this.state.stats.award_stage = stageCounts.award;
    }

    getStageLabel(stage) {
        const labels = {
            initial: "Initial / प्रारंभिक",
            sia: "SIA Stage / SIA चरण",
            section4: "Section 4 / धारा 4",
            section11: "Section 11 / धारा 11",
            section19: "Section 19 / धारा 19",
            section21: "Section 21 / धारा 21",
            award: "Award Stage / पुरस्कार चरण"
        };
        return labels[stage] || stage;
    }

    getStageColor(stage) {
        const colors = {
            initial: "#6c757d",
            sia: "#17a2b8",
            section4: "#007bff",
            section11: "#28a745",
            section19: "#ffc107",
            section21: "#fd7e14",
            award: "#28a745"
        };
        return colors[stage] || "#6c757d";
    }

    getDelayBadgeClass(delayInfo) {
        if (!delayInfo.is_delayed) {
            return "badge-success";
        } else if (delayInfo.delay_days <= 30) {
            return "badge-warning";
        } else {
            return "badge-danger";
        }
    }

    getDelayText(delayInfo) {
        if (!delayInfo.is_delayed) {
            return `On Track (${delayInfo.delay_days} days ahead)`;
        } else {
            return `Delayed by ${delayInfo.delay_days} days`;
        }
    }

    async openProject(projectId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "bhu.project",
            res_id: projectId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async refreshDashboard() {
        this.state.loading = true;
        await this.loadDashboardData();
    }

    async showTimeline(projectId) {
        console.log("showTimeline triggered for project:", projectId);
        try {
            this.notification.add(_t("Fetching progress data..."), { type: "info", sticky: false });

            const stages = await this.orm.call(
                "bhu.project",
                "get_project_progress",
                [projectId]
            );

            console.log("Stages data received:", stages);

            if (!ProjectTimelineDialog) {
                console.error("ProjectTimelineDialog is undefined in showTimeline!");
                this.notification.add(_t("Technical Error: Dialog component not found."), { type: "danger" });
                return;
            }

            this.dialog.add(ProjectTimelineDialog, {
                projectId: projectId,
                stages: stages,
                title: _t("Project Progress Timeline"),
            }, {
                size: "lg",
            });
            console.log("Dialog.add called successfully");
        } catch (error) {
            console.error("FATAL: Failed to show timeline:", error);
            this.notification.add(_t("Server Error: Could not load project progress."), { type: "danger" });
        }
    }
}

GroupDashboard.template = "bhuarjan.GroupDashboard";

registry.category("actions").add("bhuarjan.group_dashboard", GroupDashboard);
