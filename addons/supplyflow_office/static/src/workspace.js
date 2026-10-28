import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";

export class SupplyFlowWorkspace extends Component {
    static template = "supplyflow_office.Workspace";
    static components = { Layout };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ loading: true, error: "", data: null });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        this.state.error = "";
        try {
            this.state.data = await this.orm.call("supplyflow.workspace", "get_overview", []);
        } catch {
            this.state.error = "The workspace could not be loaded. Check your connection and try again.";
        } finally {
            this.state.loading = false;
        }
    }

    openRequests(pending = false) {
        return this.action.doAction("supplyflow_office.action_requests", {
            additionalContext: pending ? { search_default_awaiting_approval: 1 } : {},
        });
    }

    openIssues(filter = "") {
        return this.action.doAction("supplyflow_office.action_issues", {
            additionalContext: filter ? { [`search_default_${filter}`]: 1 } : {},
        });
    }

    openRequest(id) {
        return this.action.doAction({ type: "ir.actions.act_window", res_model: "supplyflow.request", res_id: id, views: [[false, "form"]], target: "current" });
    }
}

registry.category("actions").add("supplyflow_workspace", SupplyFlowWorkspace);
