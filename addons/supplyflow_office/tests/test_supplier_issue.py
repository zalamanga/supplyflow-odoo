from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import TransactionCase, tagged
from odoo.tests.common import new_test_user


@tagged("post_install", "-at_install", "supplyflow")
class TestSupplierIssue(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.reporter = new_test_user(
            cls.env, login="supplyflow_issue_reporter",
            groups="base.group_user,stock.group_stock_user,supplyflow_office.group_user",
            company_id=cls.company.id, company_ids=[Command.set(cls.company.ids)],
        )
        cls.other_reporter = new_test_user(
            cls.env, login="supplyflow_issue_other_reporter",
            groups="base.group_user,stock.group_stock_user,supplyflow_office.group_user",
            company_id=cls.company.id, company_ids=[Command.set(cls.company.ids)],
        )
        cls.approver = new_test_user(
            cls.env, login="supplyflow_issue_approver",
            groups="base.group_user,stock.group_stock_user,supplyflow_office.group_approver",
            company_id=cls.company.id, company_ids=[Command.set(cls.company.ids)],
        )
        cls.warehouse = cls.env["stock.warehouse"].create({
            "name": "Supplier issue test warehouse", "code": "SIT", "company_id": cls.company.id,
        })
        cls.product = cls.env["product.product"].create({
            "name": "Receipt issue test paper", "type": "consu", "is_storable": True,
        })
        cls.vendor = cls.env["res.partner"].create({"name": "Receipt issue test supplier"})
        cls.receipt = cls._make_receipt(cls.product, 10)
        cls.source_move = cls.receipt.move_ids

    @classmethod
    def _make_receipt(cls, product, quantity):
        receipt = cls.env["stock.picking"].create({
            "picking_type_id": cls.warehouse.in_type_id.id,
            "location_id": cls.env.ref("stock.stock_location_suppliers").id,
            "location_dest_id": cls.warehouse.lot_stock_id.id,
            "partner_id": cls.vendor.id, "company_id": cls.company.id,
            "move_ids": [Command.create({
                "product_id": product.id, "product_uom_qty": quantity,
                "product_uom": product.uom_id.id,
                "location_id": cls.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": cls.warehouse.lot_stock_id.id,
                "company_id": cls.company.id,
            })],
        })
        receipt.action_confirm()
        receipt.move_ids.write({"quantity": quantity, "picked": True})
        receipt.button_validate()
        if receipt.state != "done":
            raise AssertionError("The test fixture must complete a real incoming stock transfer.")
        return receipt

    def _issue(self, quantity=3, *, reporter=None, context=None, **values):
        reporter = reporter or self.reporter
        data = {
            "company_id": self.company.id, "picking_id": self.receipt.id,
            "reason": "damage", "description": "Paper cartons arrived with water damage.",
            "resolver_id": self.approver.id,
            "line_ids": [Command.create({"move_id": self.source_move.id, "affected_qty": quantity})],
        }
        data.update(values)
        model = self.env["supplyflow.issue"].with_user(reporter)
        if context:
            model = model.with_context(**context)
        return model.create(data)

    def _approve(self, issue):
        issue.action_submit()
        issue.with_user(self.approver).action_approve()
        return issue.with_user(self.approver)

    def test_independent_approval_creates_native_return_without_moving_stock(self):
        issue = self._approve(self._issue())
        before = self.product.qty_available
        action = issue.action_create_return()
        returned = self.env["stock.picking"].browse(action["res_id"])
        self.assertEqual(issue.state, "return_created")
        self.assertEqual(issue.return_picking_id, returned)
        self.assertEqual(returned.return_id, self.receipt)
        self.assertEqual(returned.move_ids.origin_returned_move_id, self.source_move)
        self.assertEqual(returned.move_ids.product_uom_qty, 3)
        self.assertNotEqual(returned.state, "done")
        self.product.invalidate_recordset(["qty_available"])
        self.assertEqual(self.product.qty_available, before)
        returned.move_ids.write({"quantity": 3, "picked": True})
        returned.button_validate()
        self.assertEqual(returned.state, "done")
        self.product.invalidate_recordset(["qty_available"])
        self.assertEqual(self.product.qty_available, before - 3)
        self.assertEqual(issue.return_state, "done")

    def test_return_creation_is_idempotent(self):
        issue = self._approve(self._issue())
        first = issue.action_create_return()
        second = issue.action_create_return()
        self.assertEqual(first["res_id"], second["res_id"])
        self.assertEqual(self.env["stock.picking"].search_count([("return_id", "=", self.receipt.id)]), 1)
        self.assertEqual(self.source_move.supplyflow_return_revision, 1)

    def test_existing_pending_returns_reserve_their_quantity(self):
        first = self._issue(7)
        second = self._issue(4)
        self._approve(first)
        self._approve(second)
        first.with_user(self.approver).action_create_return()
        with self.assertRaises(UserError):
            second.with_user(self.approver).action_create_return()
        self.assertFalse(second.return_picking_id)
        self.assertEqual(second.state, "approved")

    def test_native_pending_return_is_included_in_returnability(self):
        wizard = self.env["stock.return.picking"].with_context(
            active_model="stock.picking", active_id=self.receipt.id,
        ).create({"picking_id": self.receipt.id})
        wizard.product_return_moves.quantity = 8
        wizard.action_create_returns()
        issue = self._issue(3)
        with self.assertRaises(UserError):
            issue.action_submit()

    def test_cancelled_return_does_not_consume_returnable_quantity(self):
        issue = self._approve(self._issue(7))
        issue.action_create_return()
        issue.return_picking_id.action_cancel()
        replacement = self._approve(self._issue(8))
        replacement.action_create_return()
        self.assertEqual(replacement.return_picking_id.move_ids.product_uom_qty, 8)

    def test_reporter_cannot_approve_or_create_return(self):
        issue = self._issue()
        issue.action_submit()
        with self.assertRaises(AccessError):
            issue.action_approve()
        issue.with_user(self.approver).action_approve()
        with self.assertRaises(AccessError):
            issue.action_create_return()

    def test_approver_cannot_approve_own_issue(self):
        issue = self._issue(reporter=self.approver, resolution_note="Supplier has acknowledged this issue.")
        issue.action_submit()
        with self.assertRaises(UserError):
            issue.action_approve()
        with self.assertRaises(UserError):
            issue.action_accept_resolution()

    def test_direct_state_and_review_writes_cannot_bypass_workflow(self):
        issue = self._issue()
        for values in (
            {"state": "approved"}, {"requester_id": self.approver.id},
            {"approved_by_id": self.approver.id}, {"return_picking_id": self.receipt.id},
        ):
            with self.assertRaises(AccessError):
                issue.with_context(supplyflow_internal=True).write(values)
        with self.assertRaises(AccessError):
            self._issue(state="approved")

    def test_context_defaults_cannot_seed_review_or_forge_audit(self):
        issue = self._issue(context={
            "default_name": "FORGED", "default_state": "return_created",
            "default_requester_id": self.approver.id,
            "default_approved_by_id": self.approver.id, "default_approved_at": "2001-01-01 00:00:00",
            "default_return_picking_id": self.receipt.id,
            "default_create_uid": self.approver.id, "default_write_uid": self.approver.id,
            "default_create_date": "2001-01-01 00:00:00", "default_write_date": "2001-01-01 00:00:00",
        })
        self.assertEqual(issue.state, "draft")
        self.assertNotEqual(issue.name, "FORGED")
        self.assertEqual(issue.requester_id, self.reporter)
        self.assertEqual(issue.create_uid, self.reporter)
        self.assertFalse(issue.approved_by_id)
        self.assertFalse(issue.approved_at)
        self.assertFalse(issue.return_picking_id)
        for field in ("create_uid", "create_date", "write_uid", "write_date"):
            with self.assertRaises(AccessError):
                self._issue(**{field: False})
            with self.assertRaises(AccessError):
                issue.write({field: False})

    def test_line_defaults_cannot_replace_derived_receipt_details(self):
        issue = self._issue(line_ids=[])
        other_product = self.env["product.product"].create({"name": "Unrelated product"})
        line_model = self.env["supplyflow.issue.line"].with_user(self.reporter).with_context(
            default_issue_id=issue.id, default_company_id=self.company.id,
            default_product_id=other_product.id, default_product_uom_id=other_product.uom_id.id,
            default_picking_id=False, default_returnable_qty=1000,
            default_create_uid=self.approver.id,
        )
        line = line_model.create({"move_id": self.source_move.id, "affected_qty": 2})
        self.assertEqual(line.product_id, self.product)
        self.assertEqual(line.picking_id, self.receipt)
        self.assertEqual(line.product_uom_id, self.source_move.product_uom)
        self.assertEqual(line.company_id, self.company)
        self.assertEqual(line.create_uid, self.reporter)
        for field in ("product_id", "company_id", "returnable_qty", "create_uid"):
            with self.assertRaises(AccessError):
                line_model.create({"move_id": self.source_move.id, "affected_qty": 1, field: False})

    def test_return_wizard_context_cannot_replace_approved_goods(self):
        other = self._make_receipt(self.product, 9)
        issue = self._approve(self._issue())
        action = issue.with_context(
            default_picking_id=other.id,
            default_product_return_moves=[Command.create({
                "move_id": other.move_ids.id, "product_id": self.product.id, "quantity": 9,
            })],
        ).action_create_return()
        returned = self.env["stock.picking"].browse(action["res_id"])
        self.assertEqual(returned.return_id, self.receipt)
        self.assertEqual(returned.move_ids.origin_returned_move_id, self.source_move)
        self.assertEqual(returned.move_ids.product_uom_qty, 3)

    def test_submitted_issue_and_lines_are_frozen(self):
        issue = self._issue()
        issue.action_submit()
        with self.assertRaises(UserError):
            issue.write({"description": "Changed after review submission"})
        with self.assertRaises(UserError):
            issue.line_ids.write({"affected_qty": 1})
        with self.assertRaises(UserError):
            issue.line_ids.unlink()
        with self.assertRaises(UserError):
            self.env["supplyflow.issue.line"].with_user(self.reporter).create({
                "issue_id": issue.id, "move_id": self.source_move.id, "affected_qty": 1,
            })

    def test_another_reporter_cannot_edit_draft_or_reparent_line(self):
        issue = self._issue()
        other = self._issue(reporter=self.other_reporter)
        with self.assertRaises(AccessError):
            issue.with_user(self.other_reporter).write({"description": "Not my draft"})
        with self.assertRaises(AccessError):
            issue.line_ids.write({"issue_id": other.id})

    def test_invalid_source_and_nonpositive_quantity_are_rejected(self):
        other = self._make_receipt(self.product, 4)
        with self.assertRaises(ValidationError):
            self._issue(line_ids=[Command.create({"move_id": other.move_ids.id, "affected_qty": 1})])
        with self.assertRaises(ValidationError):
            self._issue(0)
        with self.assertRaises(ValidationError):
            self._issue(-1)
        with self.assertRaises(ValidationError):
            self._issue(float("nan"))
        with self.assertRaises(ValidationError):
            self._issue(float("inf"))

    def test_empty_or_excessive_issue_cannot_be_submitted(self):
        issue = self._issue(line_ids=[])
        with self.assertRaises(UserError):
            issue.action_submit()
        excessive = self._issue(11)
        with self.assertRaises(UserError):
            excessive.action_submit()

    def test_shortage_requires_written_nonreturn_resolution(self):
        issue = self._issue(reason="shortage")
        issue.action_submit()
        reviewer = issue.with_user(self.approver)
        with self.assertRaises(UserError):
            reviewer.action_approve()
        with self.assertRaises(UserError):
            reviewer.action_accept_resolution()
        reviewer.resolution_note = "Supplier will deliver the missing cartons under the existing backorder."
        reviewer.action_accept_resolution()
        self.assertEqual(issue.state, "accepted")
        self.assertFalse(issue.return_picking_id)
        self.assertEqual(issue.approved_by_id, self.approver)
        with self.assertRaises(UserError):
            reviewer.write({"resolution_note": "A changed decision"})

    def test_issue_company_must_match_received_shipment(self):
        issue = self._issue()
        issue.line_ids.ensure_one()
        self.assertTrue(issue.exists())
        self.assertTrue(issue.line_ids.exists())
        self.assertEqual(issue.company_id, self.company)
        other_company = self.env["res.company"].create({"name": "Supplier issue other company"})
        other_user = new_test_user(
            self.env, login="supplyflow_issue_foreign_company",
            groups="base.group_user,stock.group_stock_user,supplyflow_office.group_approver",
            company_id=other_company.id, company_ids=[Command.set(other_company.ids)],
        )
        context = {"allowed_company_ids": other_user.company_ids.ids}
        foreign_issue = issue.with_user(other_user).with_context(**context)
        foreign_line = issue.line_ids.with_user(other_user).with_context(**context)
        issue_model = self.env["supplyflow.issue"].with_user(other_user).with_context(**context)
        line_model = self.env["supplyflow.issue.line"].with_user(other_user).with_context(**context)
        issue_model.check_access("read")
        line_model.check_access("read")
        self.assertFalse(issue_model.search([("id", "=", issue.id)]))
        self.assertFalse(line_model.search([("id", "=", issue.line_ids.id)]))
        with self.assertRaises(AccessError):
            foreign_issue.read(["name", "description"])
        with self.assertRaises(AccessError):
            foreign_line.read(["affected_qty"])
        with self.assertRaises(AccessError):
            foreign_issue.write({"description": "An unauthorized company edit"})
        with self.assertRaises(AccessError):
            foreign_line.write({"affected_qty": 99})
        with self.assertRaises(AccessError):
            foreign_issue.action_submit()
        self.assertEqual(issue.state, "draft")
        self.assertEqual(issue.line_ids.affected_qty, 3)
        with self.assertRaises(AccessError):
            self._issue(company_id=other_company.id)
        self.reporter.write({"company_ids": [Command.link(other_company.id)]})
        with self.assertRaises(ValidationError):
            self._issue(
                company_id=other_company.id, line_ids=[],
                context={"allowed_company_ids": [self.company.id, other_company.id]},
            )

    def test_invalid_numeric_inputs_are_rejected_before_field_conversion(self):
        issue = self._issue()
        for quantity in (float("nan"), float("inf"), -float("inf"), "not a quantity", 1e308):
            with self.subTest(quantity=quantity), self.assertRaises(ValidationError):
                issue.line_ids.write({"affected_qty": quantity})
        empty_issue = self._issue(line_ids=[])
        with self.assertRaises(ValidationError):
            self.env["supplyflow.issue.line"].with_user(self.reporter).with_context(
                default_issue_id=empty_issue.id, default_affected_qty=float("nan"),
            ).create({"move_id": self.source_move.id})

    def test_source_revision_cannot_be_forged(self):
        with self.assertRaises(AccessError):
            self.source_move.write({"supplyflow_return_revision": 100})

    def test_only_reporter_or_approver_can_cancel_open_issue(self):
        issue = self._issue()
        with self.assertRaises(AccessError):
            issue.with_user(self.other_reporter).action_cancel()
        issue.action_cancel()
        issue.action_cancel()
        self.assertEqual(issue.state, "cancelled")
        with self.assertRaises(UserError):
            issue.action_submit()
