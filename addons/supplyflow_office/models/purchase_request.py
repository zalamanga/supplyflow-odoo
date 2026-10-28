import math
from datetime import datetime, time

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class SupplyFlowRequest(models.Model):
    _name = "supplyflow.request"
    _description = "Purchase Requisition"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"
    _check_company_auto = True

    name = fields.Char(required=True, readonly=True, copy=False, default="New", index=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True
    )
    currency_id = fields.Many2one(related="company_id.currency_id", store=True)
    requester_id = fields.Many2one(
        "res.users", required=True, readonly=True, copy=False,
        default=lambda self: self.env.user, check_company=True, tracking=True,
    )
    vendor_id = fields.Many2one("res.partner", required=True, check_company=True, tracking=True)
    warehouse_id = fields.Many2one(
        "stock.warehouse", required=True, check_company=True, tracking=True,
        default=lambda self: self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        ),
    )
    requested_date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    purpose = fields.Text(required=True, tracking=True)
    line_ids = fields.One2many("supplyflow.request.line", "request_id", string="Items", copy=True)
    amount_estimated = fields.Monetary(
        string="Estimated Total", compute="_compute_amount_estimated", store=True,
        help="Estimated amount before taxes, in the company's currency.",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"), ("submitted", "Awaiting Approval"),
            ("approved", "Approved"), ("rejected", "Rejected"),
            ("rfq_created", "RFQ Created"), ("cancelled", "Cancelled"),
        ], default="draft", required=True, readonly=True, copy=False, index=True, tracking=True,
    )
    decision_reason = fields.Text(string="Decision Note", copy=False, tracking=True)
    submitted_by_id = fields.Many2one("res.users", readonly=True, copy=False, check_company=True)
    submitted_at = fields.Datetime(readonly=True, copy=False)
    approved_by_id = fields.Many2one("res.users", readonly=True, copy=False, check_company=True)
    approved_at = fields.Datetime(readonly=True, copy=False)
    rejected_by_id = fields.Many2one("res.users", readonly=True, copy=False, check_company=True)
    rejected_at = fields.Datetime(readonly=True, copy=False)
    purchase_order_id = fields.Many2one(
        "purchase.order", string="Request for Quotation", readonly=True, copy=False,
        check_company=True, ondelete="restrict", index=True,
    )
    _unique_rfq = models.Constraint(
        "UNIQUE(purchase_order_id)", "An RFQ can only belong to one requisition."
    )
    _unique_reference = models.Constraint(
        "UNIQUE(company_id, name)", "The requisition reference must be unique within its company."
    )

    _AUDIT_FIELDS = frozenset({
        "name", "requester_id", "state", "purchase_order_id", "currency_id", "amount_estimated",
        "submitted_by_id", "submitted_at", "approved_by_id", "approved_at",
        "rejected_by_id", "rejected_at", "create_uid", "create_date", "write_uid", "write_date",
    })
    _DRAFT_FIELDS = frozenset({
        "company_id", "vendor_id", "warehouse_id", "requested_date", "purpose", "line_ids",
    })

    @api.depends("line_ids.subtotal")
    def _compute_amount_estimated(self):
        for request in self:
            total = sum(request.line_ids.mapped("subtotal"))
            try:
                rounded = request.currency_id.round(total)
            except (ValueError, OverflowError) as error:
                raise ValidationError(_("The estimated total is outside the currency's supported numeric range.")) from error
            if not math.isfinite(rounded):
                raise ValidationError(_("The estimated total must be finite."))
            request.amount_estimated = total

    @api.onchange("company_id")
    def _onchange_company_id(self):
        self.warehouse_id = self.env["stock.warehouse"].search(
            [("company_id", "=", self.company_id.id)], limit=1
        )

    @api.constrains("company_id", "vendor_id", "warehouse_id", "purpose", "requester_id")
    def _check_request_details(self):
        for request in self:
            if not (request.purpose or "").strip():
                raise ValidationError(_("Describe why these items are needed."))
            if request.warehouse_id.company_id != request.company_id:
                raise ValidationError(_("Choose a warehouse in the requisition's company."))
            if request.vendor_id.company_id and request.vendor_id.company_id != request.company_id:
                raise ValidationError(_("Choose a shared vendor or a vendor in this company."))

    @api.model
    def _require_group(self, group="supplyflow_office.group_user"):
        if not self.env.user.has_group(group):
            raise AccessError(_("You do not have the required SupplyFlow role."))

    def _lock_for_change(self):
        self._require_group()
        self.check_access("write")
        self.flush_recordset()
        self.lock_for_update()
        self.invalidate_recordset()
        self.check_access("write")

    def _require_requester(self):
        if any(request.requester_id != self.env.user for request in self):
            raise AccessError(_("Only the requester can edit or withdraw this requisition."))

    def _require_independent_approver(self):
        self._require_group("supplyflow_office.group_approver")
        if any(
            self.env.user in (request.requester_id | request.create_uid)
            for request in self
        ):
            raise AccessError(_("Another approver must review your own requisition."))

    def _require_draft(self):
        self._require_requester()
        if any(request.state != "draft" for request in self):
            raise UserError(_("Items and requisition details can only be edited in Draft."))

    def _transition(self, values):
        # Only private, validated actions use this path; RPC context flags cannot unlock it.
        return super().write(values)

    @api.model_create_multi
    def create(self, vals_list):
        self._require_group()
        prepared = []
        for original in vals_list:
            values = dict(original)
            forbidden = self._AUDIT_FIELDS.intersection(values) - {"state", "requester_id", "name"}
            if forbidden or values.get("state", "draft") != "draft":
                raise AccessError(_("Approval, audit and RFQ fields are set by workflow actions."))
            if values.get("requester_id", self.env.uid) != self.env.uid:
                raise AccessError(_("Create requisitions under your own user account."))
            if values.get("name", "New") not in (False, "New"):
                raise AccessError(_("The requisition reference is assigned automatically."))
            company_id = values.get("company_id", self.env.company.id)
            if company_id not in self.env.companies.ids:
                raise AccessError(_("This company is not in your active companies."))
            company = self.env["res.company"].browse(company_id)
            reference = self.env["ir.sequence"].with_company(company).next_by_code("supplyflow.request")
            if not reference:
                raise UserError(_("The purchase requisition sequence is missing. Update SupplyFlow Office."))
            values.update({
                "name": reference, "company_id": company_id, "requester_id": self.env.uid,
                "state": "draft", "purchase_order_id": False, "decision_reason": False,
                "submitted_by_id": False, "submitted_at": False,
                "approved_by_id": False, "approved_at": False,
                "rejected_by_id": False, "rejected_at": False,
            })
            prepared.append(values)
        safe_context = {
            key: value for key, value in self.env.context.items()
            if key not in {f"default_{field}" for field in self._AUDIT_FIELDS}
        }
        return super(SupplyFlowRequest, self.with_context(safe_context)).create(prepared)

    def write(self, values):
        self._lock_for_change()
        if self._AUDIT_FIELDS.intersection(values):
            raise AccessError(_("Approval, audit and RFQ fields are set by workflow actions."))
        if self._DRAFT_FIELDS.intersection(values):
            self._require_draft()
        if "company_id" in values and any(request.company_id.id != values["company_id"] for request in self):
            raise UserError(_("Create a new requisition to use another company."))
        if "decision_reason" in values:
            self._require_independent_approver()
            if any(request.state != "submitted" for request in self):
                raise UserError(_("Decision notes can only be entered while awaiting approval."))
        return super().write(values)

    def unlink(self):
        self._lock_for_change()
        self._require_draft()
        return super().unlink()

    def action_submit(self):
        self._lock_for_change()
        self._require_draft()
        for request in self:
            if not request.line_ids:
                raise UserError(_("Add at least one item before submitting."))
            request._check_request_details()
            request.line_ids._check_line_details()
            request._check_company()
        self._transition({
            "state": "submitted", "submitted_by_id": self.env.uid,
            "submitted_at": fields.Datetime.now(), "decision_reason": False,
        })
        for request in self:
            request.message_post(body=_("Submitted for independent review."))
        return True

    def action_approve(self):
        self._lock_for_change()
        self._require_independent_approver()
        if any(request.state != "submitted" for request in self):
            raise UserError(_("Only submitted requisitions can be approved."))
        self._transition({
            "state": "approved", "approved_by_id": self.env.uid,
            "approved_at": fields.Datetime.now(),
        })
        for request in self:
            request.message_post(body=_("Approved. Decision note: %s", request.decision_reason or "No note supplied."))
        return True

    def action_reject(self):
        self._lock_for_change()
        self._require_independent_approver()
        if any(request.state != "submitted" for request in self):
            raise UserError(_("Only submitted requisitions can be rejected."))
        if any(not (request.decision_reason or "").strip() for request in self):
            raise UserError(_("Enter a decision note explaining the rejection."))
        self._transition({
            "state": "rejected", "rejected_by_id": self.env.uid,
            "rejected_at": fields.Datetime.now(),
        })
        for request in self:
            request.message_post(body=_("Rejected: %s", request.decision_reason))
        return True

    def action_reset_draft(self):
        self._lock_for_change()
        self._require_requester()
        if any(request.state != "rejected" for request in self):
            raise UserError(_("Only rejected requisitions can return to Draft."))
        self._transition({
            "state": "draft", "decision_reason": False,
            "submitted_by_id": False, "submitted_at": False,
            "approved_by_id": False, "approved_at": False,
            "rejected_by_id": False, "rejected_at": False,
        })
        for request in self:
            request.message_post(body=_("Returned to Draft for revision; previous decisions remain in the chatter."))
        return True

    def action_cancel(self):
        self._lock_for_change()
        for request in self:
            if request.state in ("draft", "submitted", "rejected"):
                request._require_requester()
            elif request.state == "approved":
                request._require_independent_approver()
            else:
                raise UserError(_("This requisition cannot be cancelled. Manage an existing RFQ in Purchase."))
        self._transition({"state": "cancelled"})
        for request in self:
            request.message_post(body=_("Requisition cancelled by %s before RFQ creation.", self.env.user.display_name))
        return True

    def action_create_rfq(self):
        self.ensure_one()
        self._lock_for_change()
        self._require_group("supplyflow_office.group_approver")
        if self.purchase_order_id:
            self.purchase_order_id.check_access("read")
            return self._rfq_action()
        if self.state != "approved":
            raise UserError(_("Approve this requisition before creating an RFQ."))
        self._check_request_details()
        self.line_ids._check_line_details()
        self._check_company()
        self.vendor_id.check_access("read")
        self.warehouse_id.check_access("read")
        self.line_ids.product_id.check_access("read")
        order = self.env["purchase.order"].with_company(self.company_id).create({
            "partner_id": self.vendor_id.id,
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "picking_type_id": self.warehouse_id.in_type_id.id,
            "origin": self.name,
            "user_id": self.env.uid,
            "state": "draft",
            "locked": False,
            "order_line": [fields.Command.create({
                "product_id": line.product_id.id,
                "name": line.name,
                "product_uom_id": line.product_uom_id.id,
                "product_qty": line.product_qty,
                "price_unit": line.price_estimated,
                "date_planned": datetime.combine(self.requested_date, time(hour=12)),
            }) for line in self.line_ids],
        })
        order.order_line._compute_tax_id()
        # Native vendor computations can replace input prices, including an intentional zero estimate.
        for requested, purchased in zip(self.line_ids, order.order_line):
            purchased.write({
                "name": requested.name,
                "price_unit": requested.price_estimated,
                "technical_price_unit": requested.price_estimated,
                "date_planned": datetime.combine(self.requested_date, time(hour=12)),
            })
        self._transition({"state": "rfq_created", "purchase_order_id": order.id})
        self.message_post(body=_("RFQ %s created. Review vendor prices and taxes in Purchase before confirmation.", order.name))
        return self._rfq_action()

    def _rfq_action(self):
        return {
            "type": "ir.actions.act_window", "name": _("Request for Quotation"),
            "res_model": "purchase.order", "view_mode": "form",
            "res_id": self.purchase_order_id.id, "target": "current",
        }


class SupplyFlowRequestLine(models.Model):
    _name = "supplyflow.request.line"
    _description = "Purchase Requisition Item"
    _order = "id"
    _check_company_auto = True

    request_id = fields.Many2one("supplyflow.request", required=True, ondelete="cascade", index=True, check_company=True)
    company_id = fields.Many2one(related="request_id.company_id", store=True, index=True)
    currency_id = fields.Many2one(related="request_id.currency_id")
    product_id = fields.Many2one("product.product", required=True, check_company=True, ondelete="restrict")
    name = fields.Char(string="Description", required=True, compute="_compute_name", store=True, readonly=False, precompute=True)
    product_uom_id = fields.Many2one("uom.uom", string="Unit", compute="_compute_product_uom_id", store=True)
    product_qty = fields.Float(string="Quantity", default=1, required=True, digits="Product Unit")
    price_estimated = fields.Monetary(string="Estimated Unit Price", required=True, default=0)
    subtotal = fields.Monetary(compute="_compute_subtotal", store=True)

    _positive_quantity = models.Constraint("CHECK(product_qty > 0)", "Item quantity must be greater than zero.")
    _nonnegative_price = models.Constraint("CHECK(price_estimated >= 0)", "Estimated price cannot be negative.")

    @api.depends("product_id")
    def _compute_name(self):
        for line in self:
            line.name = line.product_id.display_name

    @api.depends("product_id")
    def _compute_product_uom_id(self):
        for line in self:
            line.product_uom_id = line.product_id.uom_id

    @api.depends("product_qty", "price_estimated")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.product_qty * line.price_estimated

    @api.constrains("product_id", "product_qty", "price_estimated", "company_id")
    def _check_line_details(self):
        for line in self:
            if not all(math.isfinite(value) for value in (
                line.product_qty, line.price_estimated, line.product_qty * line.price_estimated,
            )):
                raise ValidationError(_("Quantity and estimated price must be finite numbers."))
            if line.product_qty <= 0 or line.product_uom_id.compare(line.product_qty, 0) <= 0:
                raise ValidationError(_("Item quantity must be greater than zero at the product's unit precision."))
            if line.price_estimated < 0:
                raise ValidationError(_("Estimated price cannot be negative."))
            if not line.product_id.purchase_ok or not line.product_id.is_storable:
                raise ValidationError(_("Choose a stock-tracked product that can be purchased."))
            if line.product_id.company_id and line.product_id.company_id != line.company_id:
                raise ValidationError(_("The product belongs to another company."))

    @api.model
    def _validate_numeric_input(self, quantity, price, unit, currency):
        try:
            quantity, price = float(quantity), float(price)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValidationError(_("Enter numeric quantities and estimated prices.")) from error
        if not all(math.isfinite(value) for value in (quantity, price, quantity * price)):
            raise ValidationError(_("Quantity and estimated price must be finite numbers."))
        if quantity <= 0:
            raise ValidationError(_("Item quantity must be greater than zero."))
        if price < 0:
            raise ValidationError(_("Estimated price cannot be negative."))
        if unit:
            try:
                is_positive = unit.compare(quantity, 0) > 0
            except (ValueError, OverflowError) as error:
                raise ValidationError(_("The quantity is outside the supported numeric range.")) from error
            if not is_positive:
                raise ValidationError(_("Item quantity must be greater than zero at the product's unit precision."))
        try:
            monetary_values = [currency.round(value) for value in (price, quantity * price)]
        except (ValueError, OverflowError) as error:
            raise ValidationError(_("The estimated price or subtotal is outside the currency's supported numeric range.")) from error
        if not all(math.isfinite(value) for value in monetary_values):
            raise ValidationError(_("Estimated price and subtotal must be finite."))
        return quantity, price

    @api.model_create_multi
    def create(self, vals_list):
        self.env["supplyflow.request"]._require_group()
        defaults = self.default_get(["product_id", "product_qty", "price_estimated"])
        prepared = []
        for original in vals_list:
            values = dict(original)
            if {"company_id", "currency_id", "subtotal", "product_uom_id", "create_uid", "create_date", "write_uid", "write_date"}.intersection(values):
                raise AccessError(_("Item company, unit and totals are assigned automatically."))
            request_id = values.get("request_id", self.env.context.get("default_request_id"))
            if not request_id:
                raise ValidationError(_("An item must belong to a requisition."))
            request = self.env["supplyflow.request"].browse(request_id)
            request._lock_for_change()
            request._require_draft()
            values["request_id"] = request_id
            product = self.env["product.product"].browse(values.get("product_id", defaults.get("product_id")))
            values["product_qty"], values["price_estimated"] = self._validate_numeric_input(
                values.get("product_qty", defaults.get("product_qty", 1)),
                values.get("price_estimated", defaults.get("price_estimated", 0)),
                product.uom_id, request.currency_id,
            )
            prepared.append(values)
        protected_defaults = {
            f"default_{field}" for field in (
                "company_id", "currency_id", "subtotal", "product_uom_id",
                "create_uid", "create_date", "write_uid", "write_date",
            )
        }
        safe_context = {key: value for key, value in self.env.context.items() if key not in protected_defaults}
        return super(SupplyFlowRequestLine, self.with_context(safe_context)).create(prepared)

    def write(self, values):
        self.check_access("write")
        requests = self.mapped("request_id")
        requests._lock_for_change()
        requests._require_draft()
        if {"request_id", "company_id", "currency_id", "subtotal", "product_uom_id", "create_uid", "create_date", "write_uid", "write_date"}.intersection(values):
            raise AccessError(_("Items cannot be moved between requisitions or assigned manual totals or units."))
        for line in self:
            unit = self.env["product.product"].browse(values["product_id"]).uom_id if "product_id" in values else line.product_uom_id
            line._validate_numeric_input(
                values.get("product_qty", line.product_qty),
                values.get("price_estimated", line.price_estimated), unit, line.currency_id,
            )
        return super().write(values)

    def unlink(self):
        self.check_access("unlink")
        requests = self.mapped("request_id")
        requests._lock_for_change()
        requests._require_draft()
        return super().unlink()
