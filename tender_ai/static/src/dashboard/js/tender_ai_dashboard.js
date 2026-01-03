/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class TenderAIDashboard extends Component {
    static template = "tender_ai.TenderAIDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            stats: {},
            lastUpdate: null,
            error: null,
        });

        onWillStart(async () => {
            await this.refresh();
        });
    }

    async refresh() {
        this.state.loading = true;
        this.state.error = null;
        try {
            const stats = await this.orm.call("tende_ai.dashboard", "get_stats", [], {});
            this.state.stats = stats || {};
            this.state.lastUpdate = new Date().toLocaleString();
        } catch (e) {
            this.state.error = e?.message || String(e);
        } finally {
            this.state.loading = false;
        }
    }

    openJobs(domain = []) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Tender Jobs"),
            res_model: "tende_ai.job",
            view_mode: "list,form",
            domain,
            target: "current",
        });
    }

    openBidders() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Bidders"),
            res_model: "tende_ai.bidder",
            view_mode: "list,form",
            domain: [],
            target: "current",
        });
    }

    openPayments() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Payments"),
            res_model: "tende_ai.payment",
            view_mode: "list,form",
            domain: [],
            target: "current",
        });
    }

    openWorkExperience() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Work Experience"),
            res_model: "tende_ai.work_experience",
            view_mode: "list,form",
            domain: [],
            target: "current",
        });
    }

    openTenders(domain = []) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Tenders"),
            res_model: "tende_ai.tender",
            view_mode: "list,form",
            domain,
            target: "current",
        });
    }
}

registry.category("actions").add("tender_ai.dashboard", TenderAIDashboard);


