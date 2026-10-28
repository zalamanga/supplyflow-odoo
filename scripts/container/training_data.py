import json
from datetime import timedelta
from pathlib import Path

from odoo import Command, fields


MODULE = "supplyflow_training"
COMPLETED_PARAMETER = "supplyflow.training_completed"
INDEX_PARAMETER = "supplyflow.training_json"


def seed_training(environment):
    parameters = environment["ir.config_parameter"].sudo()
    if parameters.get_param(COMPLETED_PARAMETER) == "1":
        print("Training data is already present. Existing records and account passwords were preserved.")
        return
    if parameters.get_param("supplyflow.initialized") != "1":
        raise RuntimeError("Initialize SupplyFlow before loading the optional training dataset.")

    company = environment.company
    company.lock_for_update()
    if company.currency_id.name != "IDR":
        raise RuntimeError("The training dataset expects the initialized company's IDR currency.")

    raw_credentials = json.loads(Path("/run/secrets/training_credentials.json").read_text())
    if not isinstance(raw_credentials, dict):
        raise RuntimeError("The training credentials secret must contain a JSON object.")
    passwords = {}
    for role in ("buyer", "approver", "warehouse"):
        entry = raw_credentials.get(role)
        password = entry.get("password") if isinstance(entry, dict) else entry
        if not isinstance(password, str) or len(password) < 16:
            raise RuntimeError("Each training role needs its own generated password of at least 16 characters.")
        passwords[role] = password
    if len(set(passwords.values())) != len(passwords):
        raise RuntimeError("Training role passwords must be distinct.")

    # Training partners have no email addresses; account creation must not send invitations.
    admin = environment.ref("base.user_admin")
    environment = environment(user=admin.id, context={
        "allowed_company_ids": company.ids, "lang": "en_US", "tz": "Asia/Jakarta",
        "no_reset_password": True, "mail_create_nosubscribe": True, "mail_notify_force_send": False,
    })
    today = fields.Date.context_today(environment["res.company"])
    identifiers = {}

    def existing(name, model):
        record = environment.ref(f"{MODULE}.{name}", raise_if_not_found=False)
        if record:
            record = record.exists()
            if record and record._name != model:
                raise RuntimeError(f"Training identifier {name} belongs to a different model.")
        return record

    def bind(name, record):
        record.ensure_one()
        current = environment["ir.model.data"].search([
            ("module", "=", MODULE), ("name", "=", name),
        ], limit=1)
        values = {"model": record._name, "res_id": record.id, "noupdate": True}
        if current:
            if current.model != record._name or current.res_id != record.id:
                raise RuntimeError(f"Training identifier {name} already refers to another record.")
        else:
            environment["ir.model.data"].create({"module": MODULE, "name": name, **values})
        identifiers[name] = record.id
        return record

    def ensure(name, model, create):
        record = existing(name, model)
        return bind(name, record or create())

    groups = {
        "buyer": ["base.group_user", "supplyflow_office.group_user", "purchase.group_purchase_user", "stock.group_stock_user"],
        "approver": ["base.group_user", "supplyflow_office.group_approver", "purchase.group_purchase_user", "stock.group_stock_user"],
        "warehouse": ["base.group_user", "supplyflow_office.group_user", "stock.group_stock_user", "sales_team.group_sale_salesman_all_leads"],
    }
    users = {}
    role_labels = {"buyer": "Purchasing buyer", "approver": "Operations approver", "warehouse": "Warehouse operator"}
    for role in groups:
        key = "warehouse_user" if role == "warehouse" else role

        def create_user(role=role):
            if environment["res.users"].with_context(active_test=False).search_count([("login", "=", role)]):
                raise RuntimeError(f"Login '{role}' already exists outside the training dataset; no account was changed.")
            return environment["res.users"].create({
                "name": f"[Training] {role_labels[role]}", "login": role, "password": passwords[role],
                "email": False, "notification_type": "inbox", "lang": "en_US", "tz": "Asia/Jakarta",
                "company_id": company.id, "company_ids": [Command.set(company.ids)],
                "group_ids": [Command.set([environment.ref(xml_id).id for xml_id in groups[role]])],
            })

        users[role] = ensure(key, "res.users", create_user)

    vendor = ensure("vendor", "res.partner", lambda: environment["res.partner"].create({
        "name": "[Training] Paper supplier", "is_company": True, "supplier_rank": 1,
        "company_id": company.id, "email": False, "comment": "Synthetic supplier for the opt-in SupplyFlow training dataset.",
    }))
    customer = ensure("customer", "res.partner", lambda: environment["res.partner"].create({
        "name": "[Training] Office customer", "is_company": True, "customer_rank": 1,
        "company_id": company.id, "email": False, "comment": "Synthetic customer for the opt-in SupplyFlow training dataset.",
    }))
    pricelist = ensure("pricelist", "product.pricelist", lambda: environment["product.pricelist"].create({
        "name": "[Training] IDR office supplies", "currency_id": company.currency_id.id,
        "company_id": company.id,
    }))

    def make_warehouse(name, code):
        if environment["stock.warehouse"].with_context(active_test=False).search_count([
            ("company_id", "=", company.id), ("code", "=", code),
        ]):
            raise RuntimeError(f"Warehouse code '{code}' already exists outside the training dataset.")
        return environment["stock.warehouse"].create({
            "name": f"[Training] {name}", "code": code, "company_id": company.id,
            "reception_steps": "one_step", "delivery_steps": "ship_only",
        })

    main_warehouse = ensure("warehouse_main", "stock.warehouse", lambda: make_warehouse("Main warehouse", "SFMN"))
    branch_warehouse = ensure("warehouse2", "stock.warehouse", lambda: make_warehouse("Branch warehouse", "SFBR"))

    def make_product(name, code, cost, price):
        if environment["product.product"].with_context(active_test=False).search_count([("default_code", "=", code)]):
            raise RuntimeError(f"Product code '{code}' already exists outside the training dataset.")
        return environment["product.product"].create({
            "name": f"[Training] {name}", "default_code": code, "type": "consu", "is_storable": True,
            "purchase_ok": True, "sale_ok": True, "company_id": company.id,
            "standard_price": cost, "list_price": price,
            "taxes_id": [Command.clear()], "supplier_taxes_id": [Command.clear()],
        })

    paper = ensure("product", "product.product", lambda: make_product("A4 paper", "TRAIN-A4", 45000, 60000))
    folders = ensure("product_folder", "product.product", lambda: make_product("Document folders", "TRAIN-FOLDER", 10000, 15000))
    pens = ensure("product_pen", "product.product", lambda: make_product("Black pens", "TRAIN-PEN", 2500, 4000))

    def create_request(purpose, items):
        return environment["supplyflow.request"].with_user(users["buyer"]).create({
            "company_id": company.id, "vendor_id": vendor.id, "warehouse_id": main_warehouse.id,
            "requested_date": today + timedelta(days=5), "purpose": f"[Training] {purpose}",
            "line_ids": [Command.create({
                "product_id": product.id, "product_qty": quantity, "price_estimated": cost,
            }) for product, quantity, cost in items],
        })

    def submit(request):
        if request.state == "draft":
            request.with_user(users["buyer"]).action_submit()

    def approve(request):
        submit(request)
        if request.state == "submitted":
            request.with_user(users["approver"]).action_approve()

    received_request = ensure("request_received", "supplyflow.request", lambda: create_request(
        "Initial office supplies replenishment. These quantities are synthetic training inputs.",
        [(paper, 120, 45000), (folders, 80, 10000), (pens, 200, 2500)],
    ))
    approve(received_request)
    if received_request.state == "approved":
        received_request.with_user(users["approver"]).action_create_rfq()
    purchase = bind("purchase", received_request.purchase_order_id)
    if purchase.state in ("draft", "sent"):
        purchase.with_user(admin).button_confirm()
    if purchase.state == "to approve":
        purchase.with_user(admin).button_approve()
    if purchase.state != "purchase":
        raise RuntimeError("The training replenishment purchase order did not confirm.")

    receipt = existing("receipt", "stock.picking")
    if not receipt:
        candidates = purchase.picking_ids.filtered(lambda picking: picking.picking_type_code == "incoming")
        if len(candidates) != 1:
            raise RuntimeError("Expected one native receipt for the training replenishment order.")
        receipt = candidates
    bind("receipt", receipt)
    if receipt.state != "done":
        for move in receipt.move_ids.filtered(lambda move: move.state not in ("done", "cancel")):
            move.write({"quantity": move.product_uom_qty, "picked": True})
        receipt.with_user(admin).button_validate()
    if receipt.state != "done":
        raise RuntimeError("The training stock receipt did not complete through native validation.")

    pending_request = ensure("request_submitted", "supplyflow.request", lambda: create_request(
        "Branch stationery refill awaiting an independent purchasing decision.", [(paper, 25, 45000), (folders, 10, 10000)],
    ))
    submit(pending_request)
    ready_request = ensure("request_approved", "supplyflow.request", lambda: create_request(
        "Approved replenishment ready for RFQ creation in the walkthrough.", [(folders, 30, 10000), (pens, 100, 2500)],
    ))
    approve(ready_request)

    paper_move = receipt.move_ids.filtered(lambda move: move.product_id == paper and move.state == "done")
    paper_move.ensure_one()

    def create_issue(description, reason, quantity, due):
        return environment["supplyflow.issue"].with_user(users["warehouse"]).create({
            "company_id": company.id, "picking_id": receipt.id, "reason": reason,
            "description": f"[Training] {description}", "resolver_id": users["approver"].id,
            "resolution_due": due,
            "line_ids": [Command.create({"move_id": paper_move.id, "affected_qty": quantity})],
        })

    pending_issue = ensure("issue_submitted", "supplyflow.issue", lambda: create_issue(
        "Two paper cartons have damaged packaging. The overdue date is intentional for the training queue.",
        "damage", 2, today - timedelta(days=1),
    ))
    if pending_issue.state == "draft":
        pending_issue.with_user(users["warehouse"]).action_submit()
    approved_issue = ensure("issue_approved", "supplyflow.issue", lambda: create_issue(
        "Three received units were not the agreed paper specification. Ready for the supplier return walkthrough.",
        "wrong_item", 3, today + timedelta(days=2),
    ))
    if approved_issue.state == "draft":
        approved_issue.with_user(users["warehouse"]).action_submit()
    if approved_issue.state == "submitted":
        approved_issue.with_user(users["approver"]).action_approve()

    def create_branch_transfer():
        return environment["stock.picking"].create({
            "picking_type_id": main_warehouse.int_type_id.id, "company_id": company.id,
            "location_id": main_warehouse.lot_stock_id.id, "location_dest_id": branch_warehouse.lot_stock_id.id,
            "origin": "[Training] Branch folder allocation",
            "move_ids": [Command.create({
                "product_id": folders.id, "product_uom": folders.uom_id.id, "product_uom_qty": 10,
                "company_id": company.id, "location_id": main_warehouse.lot_stock_id.id,
                "location_dest_id": branch_warehouse.lot_stock_id.id,
            })],
        })

    transfer = ensure("branch_transfer", "stock.picking", create_branch_transfer)
    if transfer.state != "done":
        transfer.action_confirm()
        transfer.action_assign()
        transfer.move_ids.write({"quantity": 10, "picked": True})
        transfer.button_validate()
    if transfer.state != "done":
        raise RuntimeError("The training internal transfer did not complete through native validation.")

    sale = ensure("sale", "sale.order", lambda: environment["sale.order"].create({
        "partner_id": customer.id, "company_id": company.id, "warehouse_id": main_warehouse.id,
        "pricelist_id": pricelist.id,
        "client_order_ref": "[Training] Office stationery order", "origin": "[Training] Customer fulfillment walkthrough",
        "order_line": [Command.create({
            "product_id": product.id, "product_uom_id": product.uom_id.id,
            "product_uom_qty": quantity, "price_unit": price,
        }) for product, quantity, price in [(paper, 10, 60000), (pens, 30, 4000)]],
    }))
    if sale.state in ("draft", "sent"):
        sale.action_confirm()
    if sale.state != "sale":
        raise RuntimeError("The training customer sales order did not confirm.")
    delivery = sale.picking_ids.filtered(lambda picking: picking.picking_type_code == "outgoing")
    if len(delivery) != 1:
        raise RuntimeError("Expected one native delivery for the training customer order.")
    bind("delivery", delivery)

    parameters.set_param(INDEX_PARAMETER, json.dumps(identifiers, sort_keys=True))
    parameters.set_param(COMPLETED_PARAMETER, "1")
    environment.cr.commit()
    print("Optional training dataset loaded through real purchasing, receipt, transfer and sales workflows.")
    print("Synthetic partners, products, accounts and document purposes are marked [Training].")
    print("Training account credentials remain in the local ignored credentials file.")


try:
    seed_training(env)
except Exception:
    env.cr.rollback()
    raise
