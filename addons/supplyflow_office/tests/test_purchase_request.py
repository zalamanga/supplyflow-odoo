from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import TransactionCase, tagged
from odoo.tests.common import new_test_user


@tagged("post_install", "-at_install", "supplyflow")
class TestPurchaseRequest(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "SupplyFlow Other Company"})
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1
        )
        cls.other_warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.other_company.id)], limit=1
        )
        if not cls.other_warehouse:
            cls.other_warehouse = cls.env["stock.warehouse"].create({
                "name": "Other Warehouse", "code": "SFOTH", "company_id": cls.other_company.id,
            })
        cls.vendor = cls.env["res.partner"].create({"name": "Paper Supply Vendor", "supplier_rank": 1})
        cls.other_vendor = cls.env["res.partner"].create({
            "name": "Other Company Vendor", "company_id": cls.other_company.id,
        })
        cls.product = cls.env["product.product"].create({
            "name": "A4 Copy Paper", "type": "consu", "is_storable": True,
            "purchase_ok": True, "sale_ok": True,
        })
        cls.other_product = cls.env["product.product"].create({
            "name": "Restricted Company Paper", "type": "consu", "is_storable": True,
            "company_id": cls.other_company.id,
        })
        shared_groups = "base.group_user,purchase.group_purchase_user,stock.group_stock_user"
        cls.requester = new_test_user(
            cls.env, login="sf_req_user", groups=f"{shared_groups},supplyflow_office.group_user",
            company_id=cls.company.id,
        )
        cls.approver = new_test_user(
            cls.env, login="sf_req_approver", groups=f"{shared_groups},supplyflow_office.group_approver",
            company_id=cls.company.id,
        )
        cls.peer = new_test_user(
            cls.env, login="sf_req_peer", groups=f"{shared_groups},supplyflow_office.group_user",
            company_id=cls.company.id,
        )
        cls.outsider = new_test_user(
            cls.env, login="sf_req_outsider", groups=shared_groups, company_id=cls.company.id,
        )
        cls.multi_approver = new_test_user(
            cls.env, login="sf_req_multi", groups=f"{shared_groups},supplyflow_office.group_approver,base.group_multi_company",
            company_id=cls.company.id, company_ids=[fields.Command.set([cls.company.id, cls.other_company.id])],
        )
        cls.reviewer_only = new_test_user(
            cls.env, login="sf_req_review_only", groups="base.group_user,supplyflow_office.group_approver,stock.group_stock_user",
            company_id=cls.company.id,
        )

    def _values(self, **overrides):
        values = {
            "vendor_id": self.vendor.id, "warehouse_id": self.warehouse.id,
            "company_id": self.company.id,
            "requested_date": fields.Date.today() + timedelta(days=7),
            "purpose": "Replenish paper for outgoing office orders.",
            "line_ids": [fields.Command.create({
                "product_id": self.product.id, "product_qty": 12,
                "price_estimated": 8.5,
            })],
        }
        values.update(overrides)
        return values

    def _request(self, user=None, **overrides):
        return self.env["supplyflow.request"].with_user(user or self.requester).create(self._values(**overrides))

    def _approved_request(self):
        request = self._request()
        request.action_submit()
        request.with_user(self.approver).action_approve()
        return request

    def test_request_to_native_rfq_uses_company_warehouse_and_estimate(self):
        request = self._approved_request()
        self.assertEqual(request.amount_estimated, 102)
        action = request.with_user(self.approver).action_create_rfq()
        order = request.purchase_order_id
        self.assertEqual(request.state, "rfq_created")
        self.assertEqual(action["res_id"], order.id)
        self.assertEqual(order.state, "draft")
        self.assertEqual(order.origin, request.name)
        self.assertEqual(order.partner_id, self.vendor)
        self.assertEqual(order.company_id, self.company)
        self.assertEqual(order.currency_id, self.company.currency_id)
        self.assertEqual(order.picking_type_id, self.warehouse.in_type_id)
        self.assertEqual(order.order_line.product_id, self.product)
        self.assertEqual(order.order_line.product_uom_id, self.product.uom_id)
        self.assertEqual(order.order_line.product_qty, 12)
        self.assertEqual(order.order_line.price_unit, 8.5)
        self.assertEqual(request.approved_by_id, self.approver)
        self.assertTrue(request.approved_at)

    def test_rfq_conversion_is_idempotent(self):
        request = self._approved_request()
        first = request.with_user(self.approver).action_create_rfq()
        second = request.with_user(self.approver).action_create_rfq()
        self.assertEqual(first["res_id"], second["res_id"])
        orders = self.env["purchase.order"].search([("origin", "=", request.name)])
        self.assertEqual(orders, request.purchase_order_id)

    def test_rfq_preserves_estimate_even_when_vendor_prices_are_configured(self):
        self.env["product.supplierinfo"].create({
            "partner_id": self.vendor.id, "product_tmpl_id": self.product.product_tmpl_id.id,
            "min_qty": 0, "price": 35, "delay": 21,
            "currency_id": self.company.currency_id.id, "company_id": self.company.id,
        })
        request = self._request()
        request.line_ids.write({"price_estimated": 0})
        request.action_submit()
        request.with_user(self.approver).action_approve()
        request.with_user(self.approver).action_create_rfq()
        self.assertEqual(request.purchase_order_id.order_line.price_unit, 0)
        self.assertEqual(request.purchase_order_id.order_line.date_planned.date(), request.requested_date)

    def test_approval_needs_an_independent_reviewer(self):
        own = self._request(user=self.approver)
        own.action_submit()
        with self.assertRaises(AccessError):
            own.action_approve()
        with self.assertRaises(AccessError):
            own.write({"decision_reason": "I approve my own request"})
        request = self._request()
        request.action_submit()
        with self.assertRaises(AccessError):
            request.action_approve()
        with self.assertRaises(AccessError):
            request.with_user(self.peer).action_reject()
        request.with_user(self.approver).action_approve()
        self.assertEqual(request.state, "approved")

    def test_reject_and_revision_preserve_chatter_then_require_new_approval(self):
        request = self._request()
        request.action_submit()
        review = request.with_user(self.approver)
        with self.assertRaises(UserError):
            review.action_reject()
        review.write({"decision_reason": "Reduce quantity to match current shelf capacity."})
        review.action_reject()
        self.assertEqual(request.rejected_by_id, self.approver)
        with self.assertRaises(UserError):
            request.line_ids.write({"product_qty": 8})
        with self.assertRaises(AccessError):
            review.action_reset_draft()
        request.action_reset_draft()
        self.assertFalse(request.approved_by_id)
        self.assertFalse(request.rejected_by_id)
        self.assertFalse(request.decision_reason)
        self.assertTrue(any("shelf capacity" in str(body) for body in request.message_ids.mapped("body")))
        request.line_ids.write({"product_qty": 8})
        request.action_submit()
        with self.assertRaises(UserError):
            review.action_create_rfq()
        review.action_approve()
        review.action_create_rfq()
        self.assertEqual(request.purchase_order_id.order_line.product_qty, 8)

    def test_direct_state_audit_and_link_changes_are_blocked(self):
        request = self._request()
        for values in (
            {"state": "approved"}, {"approved_by_id": self.approver.id},
            {"purchase_order_id": False}, {"requester_id": self.approver.id},
            {"create_uid": self.approver.id}, {"name": "FORGED"},
            {"currency_id": self.company.currency_id.id}, {"amount_estimated": 1},
        ):
            with self.subTest(values=values), self.assertRaises(AccessError):
                request.with_context(supplyflow_skip_security=True, bypass_approval=True).write(values)
        for values in ({"state": "approved"}, {"approved_by_id": self.approver.id}, {"requester_id": self.approver.id}):
            with self.subTest(values=values), self.assertRaises(AccessError):
                self._request(**values)

    def test_context_defaults_cannot_forge_approval_or_link(self):
        request = self.env["supplyflow.request"].with_user(self.requester).with_context(
            default_state="approved", default_approved_by_id=self.approver.id,
            default_requester_id=self.approver.id,
        ).create(self._values())
        self.assertEqual(request.state, "draft")
        self.assertEqual(request.requester_id, self.requester)
        self.assertFalse(request.approved_by_id)

    def test_submitted_parent_and_every_line_mutation_path_are_frozen(self):
        request = self._request()
        draft = self._request()
        line = request.line_ids
        request.action_submit()
        mutations = (
            lambda: request.write({"purpose": "Changed after review"}),
            lambda: request.write({"line_ids": [fields.Command.clear()]}),
            lambda: line.write({"product_qty": 50}),
            lambda: line.unlink(),
            lambda: self.env["supplyflow.request.line"].with_user(self.requester).create({
                "request_id": request.id, "product_id": self.product.id, "product_qty": 1,
            }),
            lambda: draft.write({"line_ids": [fields.Command.link(line.id)]}),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(UserError):
                mutation()
        self.assertEqual(request.line_ids, line)
        self.assertEqual(line.product_qty, 12)

    def test_peers_cannot_edit_another_requesters_draft(self):
        request = self._request()
        with self.assertRaises(AccessError):
            request.with_user(self.peer).write({"purpose": "Peer edit"})
        with self.assertRaises(AccessError):
            request.line_ids.with_user(self.peer).write({"product_qty": 9})
        with self.assertRaises(AccessError):
            request.with_user(self.approver).action_submit()

    def test_standard_purchase_rights_are_still_required(self):
        request = self._approved_request()
        with self.assertRaises(AccessError):
            request.with_user(self.reviewer_only).action_create_rfq()
        self.assertFalse(request.purchase_order_id)
        self.assertEqual(request.state, "approved")
        request.with_user(self.approver).action_create_rfq()
        self.assertTrue(request.purchase_order_id)

    def test_same_company_is_enforced_for_warehouse_vendor_and_product(self):
        for overrides in (
            {"warehouse_id": self.other_warehouse.id},
            {"vendor_id": self.other_vendor.id},
            {"line_ids": [fields.Command.create({"product_id": self.other_product.id, "product_qty": 1})]},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(ValidationError):
                self._request(user=self.multi_approver, **overrides)

    def test_company_record_rules_hide_requests_and_lines(self):
        request = self._request()
        other_user = new_test_user(
            self.env, login="sf_req_other_company", groups="base.group_user,supplyflow_office.group_user,stock.group_stock_user,purchase.group_purchase_user",
            company_id=self.other_company.id,
        )
        self.assertFalse(self.env["supplyflow.request"].with_user(other_user).search([("id", "=", request.id)]))
        self.assertFalse(self.env["supplyflow.request.line"].with_user(other_user).search([("id", "=", request.line_ids.id)]))
        with self.assertRaises(AccessError):
            request.with_user(other_user).action_submit()

    def test_empty_invalid_and_non_stock_items_are_rejected(self):
        empty = self._request(line_ids=[])
        with self.assertRaises(UserError):
            empty.action_submit()
        service = self.env["product.product"].create({"name": "Consultation", "type": "service"})
        for item in (
            {"product_id": self.product.id, "product_qty": 0},
            {"product_id": self.product.id, "product_qty": -1},
            {"product_id": self.product.id, "product_qty": 0.00000001},
            {"product_id": self.product.id, "product_qty": 1, "price_estimated": -1},
            {"product_id": self.product.id, "product_qty": float("nan")},
            {"product_id": self.product.id, "product_qty": float("inf")},
            {"product_id": self.product.id, "product_qty": 1, "price_estimated": float("nan")},
            {"product_id": self.product.id, "product_qty": 1, "price_estimated": float("inf")},
            {"product_id": self.product.id, "product_qty": 1, "price_estimated": 1e308},
            {"product_id": service.id, "product_qty": 1},
        ):
            with self.subTest(item=item), self.assertRaises(ValidationError):
                self._request(line_ids=[fields.Command.create(item)])

    def test_numeric_edits_are_validated_before_database_conversion(self):
        request = self._request()
        line = request.line_ids
        line.write({"product_qty": 1})
        for values in (
            {"product_qty": 0}, {"product_qty": 0.00000001}, {"product_qty": -1},
            {"product_qty": float("nan")}, {"product_qty": float("inf")},
            {"price_estimated": -1}, {"price_estimated": float("nan")},
            {"price_estimated": float("inf")},
            {"price_estimated": 1e308},
        ):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                line.write(values)
        self.assertEqual(line.product_qty, 1)
        self.assertEqual(line.price_estimated, 8.5)

    def test_workflow_actions_have_no_state_shortcuts(self):
        request = self._request()
        with self.assertRaises(UserError):
            request.with_user(self.approver).action_approve()
        with self.assertRaises(UserError):
            request.with_user(self.approver).action_create_rfq()
        request.action_submit()
        with self.assertRaises(UserError):
            request.action_submit()
        request.action_cancel()
        self.assertEqual(request.state, "cancelled")
        with self.assertRaises(UserError):
            request.with_user(self.approver).action_approve()
        with self.assertRaises(UserError):
            request.action_reset_draft()

    def test_approved_request_can_only_be_cancelled_by_an_independent_approver(self):
        request = self._approved_request()
        self.assertFalse(request.decision_reason)
        with self.assertRaises(AccessError):
            request.action_cancel()
        request.with_user(self.approver).action_cancel()
        self.assertEqual(request.state, "cancelled")
        self.assertTrue(any("cancelled by" in str(body) for body in request.message_ids.mapped("body")))
        with self.assertRaises(UserError):
            request.with_user(self.approver).action_create_rfq()

    def test_no_supplyflow_role_denies_creation_and_actions(self):
        with self.assertRaises(AccessError):
            self._request(user=self.outsider)
        request = self._request()
        with self.assertRaises(AccessError):
            request.with_user(self.outsider).action_submit()
