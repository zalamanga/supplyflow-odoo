from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestWorkspace(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env["res.users"].create({
            "name": "Workspace test requester", "login": "sf_workspace_requester",
            "company_id": cls.env.company.id,
            "company_ids": [Command.set(cls.env.company.ids)],
            "group_ids": [Command.set([cls.env.ref("supplyflow_office.group_user").id, cls.env.ref("stock.group_stock_user").id])],
        })
        cls.outsider = cls.env["res.users"].create({
            "name": "Workspace test outsider", "login": "sf_workspace_outsider",
            "company_id": cls.env.company.id,
            "company_ids": [Command.set(cls.env.company.ids)],
            "group_ids": [Command.set([cls.env.ref("base.group_user").id])],
        })

    def test_empty_workspace_uses_real_counts(self):
        overview = self.env["supplyflow.workspace"].with_user(self.user).get_overview()
        self.assertEqual(overview["pending_requests"], 0)
        self.assertEqual(overview["open_issues"], 0)
        self.assertEqual(overview["pending_returns"], 0)
        self.assertEqual(overview["recent_requests"], [])

    def test_unassigned_user_cannot_call_workspace(self):
        with self.assertRaises(AccessError):
            self.env["supplyflow.workspace"].with_user(self.outsider).get_overview()

    def test_counts_follow_request_workflow(self):
        vendor = self.env["res.partner"].create({"name": "Workspace test supplier"})
        product = self.env["product.product"].create({"name": "Workspace test paper", "type": "consu", "is_storable": True})
        request = self.env["supplyflow.request"].with_user(self.user).create({
            "vendor_id": vendor.id, "purpose": "Workspace count verification",
            "line_ids": [Command.create({"product_id": product.id, "product_qty": 2, "price_estimated": 100})],
        })
        request.action_submit()
        overview = self.env["supplyflow.workspace"].with_user(self.user).get_overview()
        self.assertEqual(overview["pending_requests"], 1)
        self.assertEqual(overview["recent_requests"][0]["id"], request.id)
        request.action_cancel()
        self.assertEqual(self.env["supplyflow.workspace"].with_user(self.user).get_overview()["pending_requests"], 0)
