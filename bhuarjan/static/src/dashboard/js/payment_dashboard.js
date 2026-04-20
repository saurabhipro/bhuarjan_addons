/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class PaymentDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            searchTerm: "",
            expandedProjectId: null,
            stats: {
                total_count: 0,
                success_count: 0,
                failed_count: 0,
                pending_count: 0,
                total_amount: 0,
                success_amount: 0,
                failed_amount: 0,
                pending_amount: 0,
                success_rate: 0,
                project_count: 0,
                village_count: 0,
            },
            projects: [],
            villages: [],
            recent_failures: [],
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        try {
            this.state.loading = true;
            const data = await this.orm.call(
                "bhu.payment.dashboard",
                "get_payment_dashboard_data",
                []
            );
            this.state.stats = data.stats || this.state.stats;
            this.state.projects = data.projects || [];
            this.state.villages = data.villages || [];
            this.state.recent_failures = data.recent_failures || [];
            this.state.loading = false;
        } catch (err) {
            console.error("Payment dashboard load failed:", err);
            this.notification.add("Failed to load payment dashboard data.", { type: "danger" });
            this.state.loading = false;
        }
    }

    // ------------------------------------------------------------------
    // Formatting helpers
    // ------------------------------------------------------------------
    formatInr(value) {
        const v = Number(value || 0);
        if (v >= 10000000) return "₹ " + (v / 10000000).toFixed(2) + " Cr";
        if (v >= 100000) return "₹ " + (v / 100000).toFixed(2) + " L";
        return "₹ " + v.toLocaleString("en-IN", { maximumFractionDigits: 0 });
    }

    formatInrFull(value) {
        return "₹ " + Number(value || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 });
    }

    formatPct(value) {
        return (Number(value || 0)).toFixed(2) + " %";
    }

    rateColor(rate) {
        if (rate >= 90) return "#2e7d32";
        if (rate >= 60) return "#ef6c00";
        return "#c62828";
    }

    rateBg(rate) {
        if (rate >= 90) return "#e8f5e9";
        if (rate >= 60) return "#fff3e0";
        return "#ffebee";
    }

    // ------------------------------------------------------------------
    // Filtering / expansion
    // ------------------------------------------------------------------
    get filteredProjects() {
        const term = (this.state.searchTerm || "").toLowerCase().trim();
        if (!term) return this.state.projects;
        return this.state.projects.filter(p =>
            (p.project_name || "").toLowerCase().includes(term) ||
            (p.project_code || "").toLowerCase().includes(term) ||
            (p.department_name || "").toLowerCase().includes(term) ||
            (p.district_name || "").toLowerCase().includes(term)
        );
    }

    villagesForProject(projectId) {
        return this.state.villages.filter(v => v.project_id === projectId);
    }

    toggleProject(projectId) {
        this.state.expandedProjectId =
            this.state.expandedProjectId === projectId ? null : projectId;
    }

    onSearchInput(ev) {
        this.state.searchTerm = ev.target.value;
    }

    statusBadgeClass(project) {
        const key = project.payment_status_key || "none";
        if (key === "danger") return "pd-status pd-status-danger";
        if (key === "warning") return "pd-status pd-status-warning";
        if (key === "success") return "pd-status pd-status-success";
        return "pd-status pd-status-none";
    }

    // ------------------------------------------------------------------
    // Navigation actions
    // ------------------------------------------------------------------
    async refresh() {
        await this.loadData();
    }

    openAllFailed() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "All Failed Payments",
            res_model: "bhu.payment.reconciliation.bank.line",
            views: [[false, "list"], [false, "form"]],
            domain: [["status", "=", "failed"]],
            target: "current",
        });
    }

    openAllSuccess() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Successful Payments",
            res_model: "bhu.payment.reconciliation.bank.line",
            views: [[false, "list"], [false, "form"]],
            domain: [["status", "=", "settled"]],
            target: "current",
        });
    }

    openAllPending() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Pending Payments",
            res_model: "bhu.payment.reconciliation.bank.line",
            views: [[false, "list"], [false, "form"]],
            domain: [["status", "=", "pending"]],
            target: "current",
        });
    }

    openAllLines() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "All Payment Lines",
            res_model: "bhu.payment.reconciliation.bank.line",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openVillageFailed(village) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: `Failed Payments - ${village.project_name} / ${village.village_name}`,
            res_model: "bhu.payment.reconciliation.bank.line",
            views: [[false, "list"], [false, "form"]],
            domain: [
                ["status", "=", "failed"],
                ["reconciliation_id.project_id", "=", village.project_id],
                ["reconciliation_id.village_id", "=", village.village_id],
            ],
            target: "current",
        });
    }

    openProjectFailed(project) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: `Failed Payments - ${project.project_name}`,
            res_model: "bhu.payment.reconciliation.bank.line",
            views: [[false, "list"], [false, "form"]],
            domain: [
                ["status", "=", "failed"],
                ["reconciliation_id.project_id", "=", project.project_id],
            ],
            target: "current",
        });
    }

    openFailureLine(line) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Bank Reconciliation",
            res_model: "bhu.payment.reconciliation.bank",
            res_id: line.reconciliation_id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openProject(project) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "bhu.project",
            res_id: project.project_id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

PaymentDashboard.template = "bhuarjan.PaymentDashboard";

registry.category("actions").add("bhuarjan.payment_dashboard", PaymentDashboard);
