from odoo import api, fields, models
from odoo.exceptions import AccessError


class SupplyFlowWorkspace(models.AbstractModel):
    _name = "supplyflow.workspace"
    _description = "SupplyFlow operations workspace"

    @api.model
    def get_overview(self):
        if not self.env.user.has_group("supplyflow_office.group_user"):
            raise AccessError(self.env._("SupplyFlow access is required."))
        requests = self.env["supplyflow.request"]
        issues = self.env["supplyflow.issue"]
        open_issues = issues.search([("state", "in", ["submitted", "approved"])])
        waiting_returns = issues.search([("state", "=", "return_created")]).filtered(
            lambda issue: issue.return_picking_id.state not in ("done", "cancel")
        )
        recent = requests.search([], limit=8, order="create_date desc, id desc")
        return {
            "company": self.env.company.name,
            "today": fields.Date.context_today(self),
            "pending_requests": requests.search_count([("state", "=", "submitted")]),
            "open_issues": len(open_issues),
            "overdue_issues": len(open_issues.filtered(lambda issue: issue.resolution_due and issue.resolution_due < fields.Date.context_today(self))),
            "pending_returns": len(waiting_returns),
            "recent_requests": [{
                "id": request.id,
                "name": request.name,
                "vendor": request.vendor_id.display_name,
                "requester": request.requester_id.name,
                "state": dict(request._fields["state"]._description_selection(self.env))[request.state],
                "amount": request.currency_id.format(request.amount_estimated),
            } for request in recent],
        }
