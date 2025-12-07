/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class OwlCrmDashboard extends Component {
    static template = "bhuarjan.SDMTemplate";   // 🔥 MUST BE INSIDE CLASS

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.projects = useState({ list: [] });
        this.state = useState({ project_id: false });

        onWillStart(async () => {
            this.projects.list = await this.orm.call(
                "bhu.dashboard",
                "get_all_projects",
                []
            );
        });
    }

    mounted() {
        console.log("Refs after mount:", this.refs);
    }

        _onProjectChange(ev) {
        const select = ev.target;  // <-- BEST & SAFE
        const value = select.value;
        this.state.project_id = value ? parseInt(value) : false;
        console.log("Selected:", this.state.project_id);
    }

    // open project form view
    _openProjectForm(ev) {
        const id = ev.target.dataset.id;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "bhu.project",
            res_id: parseInt(id),
            views: [[false, "form"]],
        });
    }

    // open list view
    _openListView(resModel, domain = []) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Properties"),
            res_model: resModel,
            view_mode: "list",
            views: [[false, "list"]],
            domain: domain,
        });
    }

    _openFormView(resModel, domain = []) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Properties"),
            res_model: resModel,
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
            domain: domain,
            res_id: false,
        });
    }

    _onClickSiaTeam() {
        let domain = [];

        if (this.state.project_id) {
            domain = [["project_id", "=", this.state.project_id]];
        }

        this._openListView("bhu.sia.team", domain);
    }

    _onClickSiaTeamFormNew() {
        this._openFormView("bhu.sia.team");
    }
}

// Register the action
registry.category("actions").add(
    "bhuarjan.sdm_dashboard_tag",
    OwlCrmDashboard
);
