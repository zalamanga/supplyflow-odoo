from datetime import timedelta
from math import isfinite

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_round


class SupplyflowIssue(models.Model):
    _name = "supplyflow.issue"
    _description = "Supplier Receipt Issue"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"
    _check_company_auto = True

    name = fields.Char(required=True, default="New", readonly=True, copy=False, index=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True
    )
    picking_id = fields.Many2one(
        "stock.picking", string="Received shipment", required=True,
        check_company=True, ondelete="restrict", tracking=True,
        domain="[('state', '=', 'done'), ('picking_type_code', '=', 'incoming'), ('company_id', '=', company_id)]",
    )
    requester_id = fields.Many2one(
        "res.users", string="Reported by", required=True, readonly=True,
        default=lambda self: self.env.user, copy=False,
    )
    reason = fields.Selection(
        [("damage", "Damaged goods"), ("wrong_item", "Incorrect goods"), ("shortage", "Quantity shortage")],
        required=True, default="damage", tracking=True,
    )
    description = fields.Text(required=True)
    resolver_id = fields.Many2one(
        "res.users", string="Assigned resolver", required=True,
        default=lambda self: self.env.user,
        domain="[('share', '=', False), ('company_ids', 'in', [company_id])]",
        tracking=True,
    )
    resolution_due = fields.Date(
        string="Resolution due", required=True, tracking=True,
        default=lambda self: fields.Date.context_today(self) + timedelta(days=7),
    )
    state = fields.Selection(
        [("draft", "Draft"), ("submitted", "Awaiting review"), ("approved", "Return approved"),
         ("return_created", "Return transfer created"), ("accepted", "Resolved without return"),
         ("cancelled", "Cancelled")],
        required=True, default="draft", readonly=True, copy=False, tracking=True, index=True,
    )
    line_ids = fields.One2many("supplyflow.issue.line", "issue_id", string="Affected goods", copy=True)
    approved_by_id = fields.Many2one("res.users", string="Reviewed by", readonly=True, copy=False)
    approved_at = fields.Datetime(string="Reviewed at", readonly=True, copy=False)
    return_picking_id = fields.Many2one(
        "stock.picking", string="Supplier return", check_company=True,
        readonly=True, copy=False, ondelete="restrict",
    )
    return_state = fields.Selection(related="return_picking_id.state", string="Transfer status")
    resolution_note = fields.Text(tracking=True, copy=False)

    _protected_fields = {
        "name", "state", "requester_id", "approved_by_id", "approved_at", "return_picking_id", "return_state",
        "create_uid", "create_date", "write_uid", "write_date",
    }
    _content_fields = {
        "company_id", "picking_id", "reason", "description", "resolver_id", "resolution_due", "line_ids",
    }

    def _check_member(self):
        if not self.env.user.has_group("supplyflow_office.group_user"):
            raise AccessError(_("You do not have access to supplier receipt issues."))

    def _check_approver(self):
        self._check_member()
        if not self.env.user.has_group("supplyflow_office.group_approver"):
            raise AccessError(_("Only an operations approver can review supplier issues."))

    def _check_draft_owner(self):
        self._check_member()
        self.check_access("write")
        for issue in self:
            if issue.state != "draft":
                raise UserError(_("Submitted supplier issues cannot be edited."))
            if issue.requester_id != self.env.user:
                raise AccessError(_("Only the person who reported a draft may edit it."))

    def _transition(self, values):
        return super(SupplyflowIssue, self).write(values)

    def _lock(self):
        self.check_access("write")
        self.lock_for_update()
        self.invalidate_recordset()
        self.check_access("write")

    def _check_independent_reviewer(self):
        self._check_approver()
        if any(issue.requester_id == self.env.user for issue in self):
            raise UserError(_("Ask another approver to review an issue you reported yourself."))

    @api.model_create_multi
    def create(self, vals_list):
        self._check_member()
        prepared = []
        for values in vals_list:
            values = dict(values)
            if {"create_uid", "create_date", "write_uid", "write_date", "return_state"}.intersection(values):
                raise AccessError(_("Issue audit and transfer details are assigned by the workflow."))
            if values.get("state", "draft") != "draft" or values.get("requester_id", self.env.uid) != self.env.uid:
                raise AccessError(_("Issues must start as a draft reported by the current user."))
            if values.get("name", "New") != "New" or any(
                values.get(field) for field in ("approved_by_id", "approved_at", "return_picking_id")
            ):
                raise AccessError(_("Issue references and review details are assigned by the workflow."))
            values["name"] = self.env["ir.sequence"].next_by_code("supplyflow.issue") or "New"
            values["requester_id"] = self.env.uid
            values["state"] = "draft"
            values["approved_by_id"] = False
            values["approved_at"] = False
            values["return_picking_id"] = False
            values["company_id"] = values.get("company_id") or self.env.company.id
            if values["company_id"] not in self.env.companies.ids:
                raise AccessError(_("Choose a company available in your current workspace."))
            prepared.append(values)
        context = {key: value for key, value in self.env.context.items()
                   if key not in {"default_" + field for field in self._protected_fields}}
        return super(SupplyflowIssue, self.with_context(context)).create(prepared)

    def write(self, vals):
        self._check_member()
        if self._protected_fields.intersection(vals):
            raise AccessError(_("Use the issue workflow actions to change review details or status."))
        if self._content_fields.intersection(vals) or "resolution_note" in vals:
            self._lock()
        if self._content_fields.intersection(vals):
            self._check_draft_owner()
        if "resolution_note" in vals:
            for issue in self:
                if issue.state == "draft":
                    issue._check_draft_owner()
                elif issue.state == "submitted":
                    issue._check_independent_reviewer()
                else:
                    raise UserError(_("A completed review note cannot be changed."))
        return super().write(vals)

    def unlink(self):
        self._lock()
        self._check_draft_owner()
        return super().unlink()

    @api.constrains("picking_id", "company_id", "resolver_id", "description")
    def _check_receipt(self):
        for issue in self:
            issue.picking_id.check_access("read")
            if issue.picking_id.state != "done" or issue.picking_id.picking_type_code != "incoming":
                raise ValidationError(_("Choose a completed incoming shipment."))
            if issue.picking_id.company_id != issue.company_id:
                raise ValidationError(_("The received shipment and issue must belong to the same company."))
            if issue.resolver_id.share or issue.company_id not in issue.resolver_id.company_ids:
                raise ValidationError(_("Assign an internal resolver who can access this company."))
            if not (issue.description or "").strip():
                raise ValidationError(_("Describe what happened with the received goods."))
            if issue.line_ids.filtered(lambda line: line.move_id.picking_id != issue.picking_id):
                raise ValidationError(_("All affected goods must come from the selected shipment."))

    def _check_lines(self, *, returning=False):
        for issue in self:
            issue._check_receipt()
            if not issue.line_ids:
                raise UserError(_("Add at least one affected product from the received shipment."))
            issue.line_ids._check_source_move()
            if returning and issue.reason == "shortage":
                raise UserError(_("Missing goods cannot be returned. Resolve a shortage with a review note."))
            if returning or issue.reason != "shortage":
                for line in issue.line_ids:
                    remaining = line._remaining_returnable_quantity()
                    if float_compare(line.affected_qty, remaining, precision_rounding=line.product_uom_id.rounding) > 0:
                        raise UserError(_(
                            "The quantity for %(product)s exceeds the %(quantity)s units still available for return. "
                            "Existing unfinished return transfers also reserve their quantities.",
                            product=line.product_id.display_name, quantity=remaining,
                        ))

    def action_submit(self):
        self.ensure_one()
        self._check_draft_owner()
        self._lock()
        self._check_draft_owner()
        self._check_lines()
        self._transition({"state": "submitted"})
        self.message_post(body=_("Supplier issue submitted for independent review."))
        return True

    def action_approve(self):
        self.ensure_one()
        self._check_independent_reviewer()
        self._lock()
        if self.state != "submitted":
            raise UserError(_("Only submitted issues can be approved for return."))
        self._check_lines(returning=True)
        self._transition({
            "state": "approved", "approved_by_id": self.env.uid, "approved_at": fields.Datetime.now(),
        })
        self.message_post(body=_("Supplier return approved. Create a return transfer for the warehouse to process."))
        return True

    def action_accept_resolution(self):
        self.ensure_one()
        self._check_independent_reviewer()
        self._lock()
        if self.state != "submitted":
            raise UserError(_("Only submitted issues can be resolved without a return."))
        self._check_lines()
        if not (self.resolution_note or "").strip():
            raise UserError(_("Enter a resolution note before accepting the discrepancy."))
        self._transition({
            "state": "accepted", "approved_by_id": self.env.uid, "approved_at": fields.Datetime.now(),
        })
        self.message_post(body=_("Issue resolved without a stock return. See the recorded resolution note."))
        return True

    def action_cancel(self):
        self.ensure_one()
        self._check_member()
        self._lock()
        if self.state == "cancelled":
            return True
        if self.state not in ("draft", "submitted", "approved"):
            raise UserError(_("A completed review or created return transfer cannot be cancelled here."))
        is_approver = self.env.user.has_group("supplyflow_office.group_approver")
        if self.requester_id != self.env.user and not is_approver:
            raise AccessError(_("Only the reporter or an operations approver can cancel this issue."))
        if self.state == "approved" and not is_approver:
            raise AccessError(_("Only an operations approver can cancel an approved supplier return."))
        self._transition({"state": "cancelled"})
        return True

    def _return_action(self):
        self.return_picking_id.check_access("read")
        return {
            "type": "ir.actions.act_window", "name": _("Supplier return"),
            "res_model": "stock.picking", "view_mode": "form",
            "res_id": self.return_picking_id.id,
        }

    def action_open_return(self):
        self.ensure_one()
        self._check_member()
        self.check_access("read")
        if not self.return_picking_id:
            raise UserError(_("This issue does not have a return transfer yet."))
        return self._return_action()

    def action_create_return(self):
        self.ensure_one()
        self._check_approver()
        self._lock()
        if self.return_picking_id:
            return self._return_action()
        if self.state != "approved":
            raise UserError(_("Approve the supplier issue before creating a return transfer."))
        moves = self.line_ids.move_id.sorted("id")
        moves.check_access("write")
        moves.lock_for_update()
        moves.invalidate_recordset()
        self._check_lines(returning=True)
        # Updating a source revision makes stale repeatable-read transactions retry safely.
        moves._supplyflow_advance_return_revision()
        wizard = self.env["stock.return.picking"].with_context(
            {}, allowed_company_ids=self.env.companies.ids, lang=self.env.lang, tz=self.env.user.tz,
            active_model="stock.picking", active_id=self.picking_id.id, active_ids=self.picking_id.ids,
        ).create({"picking_id": self.picking_id.id})
        quantities = {line.move_id.id: line.affected_qty for line in self.line_ids}
        for return_line in wizard.product_return_moves:
            return_line.quantity = quantities.get(return_line.move_id.id, 0.0)
        action = wizard.action_create_returns()
        picking = self.env["stock.picking"].browse(action["res_id"])
        self._transition({"return_picking_id": picking.id, "state": "return_created"})
        self.message_post(body=_("Supplier return transfer created. Stock changes only when the warehouse validates it."))
        return self._return_action()


class SupplyflowIssueLine(models.Model):
    _name = "supplyflow.issue.line"
    _description = "Affected Supplier Receipt Product"
    _check_company_auto = True

    issue_id = fields.Many2one("supplyflow.issue", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="issue_id.company_id", store=True, index=True)
    picking_id = fields.Many2one(related="issue_id.picking_id")
    move_id = fields.Many2one(
        "stock.move", string="Received product", required=True, check_company=True, ondelete="restrict",
        domain="[('picking_id', '=', picking_id), ('state', '=', 'done')]",
    )
    product_id = fields.Many2one(related="move_id.product_id", string="Product")
    product_uom_id = fields.Many2one(related="move_id.product_uom", string="Unit")
    affected_qty = fields.Float(string="Affected quantity", required=True, default=1, digits="Product Unit")
    returnable_qty = fields.Float(string="Available to return", compute="_compute_returnable_qty", digits="Product Unit")

    _unique_issue_move = models.Constraint("UNIQUE(issue_id, move_id)", "Add each received product only once per issue.")
    _derived_fields = {
        "company_id", "product_id", "product_uom_id", "picking_id", "returnable_qty",
        "create_uid", "create_date", "write_uid", "write_date",
    }

    @api.model
    def _validated_quantity_input(self, value):
        try:
            quantity = float(value or 0)
            if not isfinite(quantity):
                raise ValueError
            float_round(quantity, precision_digits=self.env["decimal.precision"].precision_get("Product Unit"))
        except (TypeError, ValueError, OverflowError):
            raise ValidationError(_("Affected quantity must be a finite number within the supported precision.")) from None
        if quantity <= 0:
            raise ValidationError(_("Affected quantity must be greater than zero."))
        return quantity

    @api.depends("move_id", "move_id.quantity", "move_id.returned_move_ids.state",
                 "move_id.returned_move_ids.quantity", "move_id.returned_move_ids.product_uom_qty")
    def _compute_returnable_qty(self):
        for line in self:
            line.returnable_qty = line._remaining_returnable_quantity() if line.move_id else 0.0

    def _remaining_returnable_quantity(self):
        self.ensure_one()
        source = self.move_id
        # Count all returns of an authorized source, even if a custom stock rule hides a sibling transfer.
        returned = self.env["stock.move"].sudo().search([
            ("origin_returned_move_id", "=", source.id), ("company_id", "=", source.company_id.id),
            ("state", "!=", "cancel"),
        ])
        committed = sum(
            move.product_uom._compute_quantity(
                move.quantity if move.state == "done" else move.product_uom_qty, source.product_uom,
                round=False,
            ) for move in returned
        )
        return max(0.0, source.quantity - committed)

    @api.constrains("issue_id", "move_id", "affected_qty")
    def _check_source_move(self):
        for line in self:
            line.move_id.check_access("read")
            if line.move_id.state != "done" or line.move_id.picking_id != line.issue_id.picking_id:
                raise ValidationError(_("Choose a completed product move from this issue's received shipment."))
            if line.move_id.company_id != line.company_id:
                raise ValidationError(_("Affected goods must belong to the issue's company."))
            if not isfinite(line.affected_qty) or float_compare(
                line.affected_qty, 0, precision_rounding=line.product_uom_id.rounding
            ) <= 0:
                raise ValidationError(_("Affected quantity must be greater than zero."))

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        for values in vals_list:
            values = dict(values)
            if self._derived_fields.intersection(values):
                raise AccessError(_("Affected product and audit details come from the original shipment."))
            issue_id = values.get("issue_id", self.env.context.get("default_issue_id"))
            if type(issue_id) is not int or issue_id <= 0:
                raise ValidationError(_("Choose the supplier issue before adding affected goods."))
            issue = self.env["supplyflow.issue"].browse(issue_id).exists()
            if not issue:
                raise ValidationError(_("The supplier issue no longer exists."))
            issue._lock()
            issue._check_draft_owner()
            values["issue_id"] = issue.id
            values["affected_qty"] = self._validated_quantity_input(
                values.get("affected_qty", self.env.context.get("default_affected_qty", 1))
            )
            prepared.append(values)
        context = {key: value for key, value in self.env.context.items()
                   if key not in {"default_" + field for field in self._derived_fields}}
        return super(SupplyflowIssueLine, self.with_context(context)).create(prepared)

    def write(self, vals):
        self.issue_id._lock()
        self.issue_id._check_draft_owner()
        if "issue_id" in vals and any(line.issue_id.id != vals["issue_id"] for line in self):
            raise AccessError(_("An affected product cannot be moved to a different supplier issue."))
        if self._derived_fields.intersection(vals):
            raise AccessError(_("Receipt product details are taken from the original shipment."))
        if "affected_qty" in vals:
            vals = {**vals, "affected_qty": self._validated_quantity_input(vals["affected_qty"])}
        return super().write(vals)

    def unlink(self):
        self.issue_id._lock()
        self.issue_id._check_draft_owner()
        return super().unlink()


class StockMove(models.Model):
    _inherit = "stock.move"

    supplyflow_return_revision = fields.Integer(default=0, readonly=True, copy=False)

    def write(self, vals):
        if "supplyflow_return_revision" in vals:
            raise AccessError(_("Supplier return revisions are managed by the issue workflow."))
        return super().write(vals)

    def _supplyflow_advance_return_revision(self):
        for move in self:
            super(StockMove, move).write({"supplyflow_return_revision": move.supplyflow_return_revision + 1})
