/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class ProjectTimelineDialog extends Component {
    static template = "bhuarjan.ProjectTimeline";
    static components = { Dialog };
    static props = {
        projectId: { type: Number },
        stages: { type: Array },
        title: { type: String, optional: true },
        close: { type: Function },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            stages: this.props.stages || [],
        });
    }

    async refreshProgress() {
        console.log("Refreshing progress for project:", this.props.projectId);
        try {
            const stages = await this.orm.call(
                "bhu.project",
                "get_project_progress",
                [this.props.projectId]
            );
            this.state.stages = stages;
            console.log("Progress refreshed:", stages);
        } catch (error) {
            console.error("Failed to refresh progress:", error);
        }
    }
}

export class ProjectStageWidget extends Component {
    static template = "bhuarjan.StageButton";

    setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.state = useState({
            currentStage: "View Progress",
        });

        onWillStart(async () => {
            if (this.props.record.resId) {
                await this.updateCurrentStage();
            }
        });
    }

    async updateCurrentStage() {
        try {
            const stages = await this.orm.call(
                "bhu.project",
                "get_project_progress",
                [this.props.record.resId]
            );
            // Find the last completed or in_progress stage
            const latest = [...stages].reverse().find(s => s.status === 'completed' || s.status === 'in_progress');
            if (latest) {
                this.state.currentStage = latest.name;
            }
        } catch (e) {
            console.error("Failed to fetch project progress", e);
        }
    }

    async onStageClick() {
        if (!this.props.record.resId) {
            this.notification.add("Please save the project first.", { type: "warning" });
            return;
        }

        const stages = await this.orm.call(
            "bhu.project",
            "get_project_progress",
            [this.props.record.resId]
        );

        this.dialog.add(ProjectTimelineDialog, {
            projectId: this.props.record.resId,
            stages: stages,
            title: "Project Progress Timeline",
        }, {
            size: "lg",
        });
    }
}

export const projectStageWidget = {
    component: ProjectStageWidget,
};

registry.category("view_widgets").add("bhu_project_stage", projectStageWidget);
