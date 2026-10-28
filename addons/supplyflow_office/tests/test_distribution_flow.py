from datetime import timedelta

from odoo import Command, fields
from odoo.tests import Form, TransactionCase, tagged
from odoo.tests.common import new_test_user


@tagged("post_install", "-at_install", "supplyflow")
class TestDistributionFlow(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.po_double_validation = "one_step"
        cls.warehouse_a, cls.warehouse_b = cls.env["stock.warehouse"].create([
            {
                "name": "Distribution test warehouse A", "code": "SFDTA",
                "company_id": cls.company.id, "reception_steps": "one_step",
                "delivery_steps": "ship_only",
            },
            {
                "name": "Distribution test warehouse B", "code": "SFDTB",
                "company_id": cls.company.id, "reception_steps": "one_step",
                "delivery_steps": "ship_only",
            },
        ])
        cls.warehouse_a.in_type_id.create_backorder = "ask"
        cls.warehouse_b.in_type_id.create_backorder = "ask"
        cls.product = cls.env["product.product"].create({
            "name": "Distribution test A4 paper", "type": "consu", "is_storable": True,
            "purchase_ok": True, "sale_ok": True, "list_price": 16,
        })
        cls.vendor = cls.env["res.partner"].create({"name": "Distribution test supplier", "supplier_rank": 1})
        cls.customer = cls.env["res.partner"].create({"name": "Distribution test customer", "customer_rank": 1})
        company_values = {
            "company_id": cls.company.id, "company_ids": [Command.set(cls.company.ids)],
        }
        cls.buyer = new_test_user(
            cls.env, login="sf_distribution_test_buyer",
            groups="base.group_user,purchase.group_purchase_user,stock.group_stock_user,supplyflow_office.group_user",
            **company_values,
        )
        cls.approver = new_test_user(
            cls.env, login="sf_distribution_test_approver",
            groups="base.group_user,purchase.group_purchase_user,stock.group_stock_user,supplyflow_office.group_approver",
            **company_values,
        )
        cls.operator = new_test_user(
            cls.env, login="sf_distribution_test_operator",
            groups="base.group_user,stock.group_stock_user", **company_values,
        )
        cls.salesperson = new_test_user(
            cls.env, login="sf_distribution_test_sales",
            groups="base.group_user,sales_team.group_sale_salesman,stock.group_stock_user", **company_values,
        )

    def _purchase_for(self, warehouse, quantity):
        request = self.env["supplyflow.request"].with_user(self.buyer).create({
            "company_id": self.company.id, "vendor_id": self.vendor.id,
            "warehouse_id": warehouse.id,
            "requested_date": fields.Date.today() + timedelta(days=5),
            "purpose": "Distribution test replenishment through the approved purchase workflow.",
            "line_ids": [Command.create({
                "product_id": self.product.id, "product_qty": quantity, "price_estimated": 10,
            })],
        })
        request.action_submit()
        request.with_user(self.approver).action_approve()
        request.with_user(self.approver).action_create_rfq()
        order = request.purchase_order_id.with_user(self.buyer)
        order.button_confirm()
        self.assertEqual(order.state, "purchase")
        receipt = order.picking_ids.filtered(lambda picking: picking.picking_type_code == "incoming")
        self.assertEqual(len(receipt), 1)
        self.assertEqual(receipt.move_ids.purchase_line_id, order.order_line)
        return request, order, receipt.with_user(self.operator)

    def _finish_picking(self, picking):
        picking = picking.with_user(self.operator)
        picking.action_assign()
        for move in picking.move_ids.filtered(lambda move: move.state not in ("done", "cancel")):
            move.write({"quantity": move.product_uom_qty, "picked": True})
        result = picking.button_validate()
        self.assertIs(result, True, "A fully processed test transfer must not require a backorder decision.")
        self.assertEqual(picking.state, "done")

    def _stock_at(self, warehouse):
        quants = self.env["stock.quant"].search([
            ("product_id", "=", self.product.id),
            ("company_id", "=", self.company.id),
            ("location_id", "child_of", warehouse.lot_stock_id.id),
        ])
        return sum(quants.mapped("quantity"))

    def test_approved_purchase_partial_receipt_return_and_customer_delivery(self):
        request, order, receipt = self._purchase_for(self.warehouse_a, 20)
        self.assertEqual(request.state, "rfq_created")
        self.assertEqual(receipt.location_dest_id, self.warehouse_a.lot_stock_id)
        self.assertEqual(self._stock_at(self.warehouse_a), 0)

        receipt.move_ids.write({"quantity": 12, "picked": True})
        action = receipt.button_validate()
        self.assertEqual(action["res_model"], "stock.backorder.confirmation")
        self.assertNotEqual(receipt.state, "done")
        wizard = Form.from_action(receipt.env, action).save()
        self.assertEqual(wizard.pick_ids, receipt)
        self.assertTrue(wizard.backorder_confirmation_line_ids.to_backorder)
        wizard.process()
        self.assertEqual(receipt.state, "done")
        self.assertEqual(order.order_line.qty_received, 12)
        self.assertEqual(self._stock_at(self.warehouse_a), 12)

        backorder = order.picking_ids.filtered(lambda picking: picking.backorder_id == receipt)
        self.assertEqual(len(backorder), 1)
        self.assertEqual(backorder.move_ids.product_uom_qty, 8)
        self.assertEqual(backorder.move_ids.purchase_line_id, order.order_line)
        self._finish_picking(backorder)
        self.assertEqual(order.order_line.qty_received, 20)
        self.assertEqual(self._stock_at(self.warehouse_a), 20)

        issue = self.env["supplyflow.issue"].with_user(self.buyer).create({
            "company_id": self.company.id, "picking_id": receipt.id,
            "reason": "damage", "description": "Distribution test: two received paper cartons are damaged.",
            "resolver_id": self.approver.id,
            "line_ids": [Command.create({"move_id": receipt.move_ids.id, "affected_qty": 2})],
        })
        issue.action_submit()
        issue.with_user(self.approver).action_approve()
        issue.with_user(self.approver).action_create_return()
        returned = issue.return_picking_id
        self.assertEqual(returned.return_id, receipt)
        self.assertEqual(returned.move_ids.origin_returned_move_id, receipt.move_ids)
        self.assertEqual(returned.move_ids.purchase_line_id, order.order_line)
        self.assertEqual(returned.move_ids.product_uom_qty, 2)
        self.assertNotEqual(returned.state, "done")
        self.assertEqual(self._stock_at(self.warehouse_a), 20)
        self.assertEqual(order.order_line.qty_received, 20)
        self._finish_picking(returned)
        self.assertEqual(issue.return_state, "done")
        self.assertEqual(order.order_line.qty_received, 18)
        self.assertEqual(self._stock_at(self.warehouse_a), 18)

        sale = self.env["sale.order"].with_user(self.salesperson).create({
            "partner_id": self.customer.id, "company_id": self.company.id,
            "warehouse_id": self.warehouse_a.id,
            "order_line": [Command.create({
                "product_id": self.product.id, "product_uom_qty": 7,
                "product_uom_id": self.product.uom_id.id, "price_unit": 16,
            })],
        })
        sale.action_confirm()
        self.assertEqual(sale.state, "sale")
        delivery = sale.picking_ids.filtered(lambda picking: picking.picking_type_code == "outgoing")
        self.assertEqual(len(delivery), 1)
        self.assertEqual(delivery.sale_id, sale)
        self.assertEqual(delivery.move_ids.sale_line_id, sale.order_line)
        self.assertEqual(delivery.location_id, self.warehouse_a.lot_stock_id)
        delivery.with_user(self.operator).action_assign()
        self.assertEqual(delivery.state, "assigned")
        self.assertEqual(delivery.move_ids.quantity, 7)
        self.assertEqual(sale.order_line.qty_delivered, 0)
        self.assertEqual(self._stock_at(self.warehouse_a), 18)
        self._finish_picking(delivery)
        self.assertEqual(sale.order_line.qty_delivered, 7)
        self.assertEqual(sale.delivery_status, "full")
        self.assertEqual(self._stock_at(self.warehouse_a), 11)
        self.assertEqual(self._stock_at(self.warehouse_b), 0)
        self.product.invalidate_recordset(["qty_available"])
        self.assertEqual(self.product.qty_available, 11)

    def test_selected_receiving_warehouse_then_native_internal_transfer(self):
        request, order, receipt = self._purchase_for(self.warehouse_b, 10)
        self.assertEqual(request.warehouse_id, self.warehouse_b)
        self.assertEqual(order.picking_type_id, self.warehouse_b.in_type_id)
        self.assertEqual(receipt.location_dest_id, self.warehouse_b.lot_stock_id)
        self.assertEqual(receipt.move_ids.location_dest_id, self.warehouse_b.lot_stock_id)
        self._finish_picking(receipt)
        self.assertEqual(self._stock_at(self.warehouse_a), 0)
        self.assertEqual(self._stock_at(self.warehouse_b), 10)

        transfer = self.env["stock.picking"].with_user(self.operator).create({
            "company_id": self.company.id, "picking_type_id": self.warehouse_b.int_type_id.id,
            "origin": "Distribution test warehouse rebalance",
            "location_id": self.warehouse_b.lot_stock_id.id,
            "location_dest_id": self.warehouse_a.lot_stock_id.id,
            "move_ids": [Command.create({
                "company_id": self.company.id, "product_id": self.product.id,
                "product_uom_qty": 4, "product_uom": self.product.uom_id.id,
                "location_id": self.warehouse_b.lot_stock_id.id,
                "location_dest_id": self.warehouse_a.lot_stock_id.id,
            })],
        })
        transfer.action_confirm()
        transfer.action_assign()
        self.assertEqual(transfer.state, "assigned")
        self.assertEqual(self._stock_at(self.warehouse_a), 0)
        self.assertEqual(self._stock_at(self.warehouse_b), 10)
        self._finish_picking(transfer)
        self.assertEqual(self._stock_at(self.warehouse_a), 4)
        self.assertEqual(self._stock_at(self.warehouse_b), 6)
        self.assertEqual(order.order_line.qty_received, 10)
        self.product.invalidate_recordset(["qty_available"])
        self.assertEqual(self.product.qty_available, 10)
