from pathlib import Path

from odoo import Command

parameters = env["ir.config_parameter"].sudo()
if not parameters.get_param("supplyflow.initialized"):
    admin = env.ref("base.user_admin")
    admin.write({
        "login": "admin",
        "password": Path("/run/secrets/admin_password").read_text().strip(),
        "group_ids": [Command.link(env.ref("supplyflow_office.group_approver").id)],
    })
    env.company.write({"name": "SupplyFlow Office", "currency_id": env.ref("base.IDR").id})
    parameters.set_param("supplyflow.initialized", "1")
    parameters.set_param("web.base.url", "http://localhost:8070")
    parameters.set_param("web.base.url.freeze", "True")
    parameters.set_param("report.url", "http://127.0.0.1:8069")
    env.cr.commit()
    print("SupplyFlow initialized. Local credentials are in .secrets/LOCAL-CREDENTIALS.txt.")
else:
    print("SupplyFlow is already initialized; credentials and business records preserved.")
