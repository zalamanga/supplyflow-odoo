import fs from "node:fs";
import { expect } from "@playwright/test";

export function credentials(role = "admin") {
    if (role === "admin") return { login: "admin", password: fs.readFileSync(".secrets/admin_password", "utf8").trim() };
    const passwords = JSON.parse(fs.readFileSync(".secrets/training_credentials.json", "utf8"));
    return { login: role, password: passwords[role] };
}

export async function login(page, role = "admin") {
    await page.goto("/web/login");
    const account = credentials(role);
    await page.locator("#login").fill(account.login);
    await page.locator("#password").fill(account.password);
    await page.getByRole("button", { name: "Log in", exact: true }).click();
    await expect(page.locator(".o_main_navbar")).toBeVisible({ timeout: 120000 });
}

export async function rpc(page, model, method, args = [], kwargs = {}) {
    const response = await page.request.post(`/web/dataset/call_kw/${model}/${method}`, {
        data: { jsonrpc: "2.0", method: "call", params: { model, method, args, kwargs } },
    });
    const body = await response.json();
    if (body.error) throw new Error(body.error.data?.message || body.error.message);
    return body.result;
}

export async function clickWorkflow(page, model, method, buttonName, { confirm = false } = {}) {
    const [response] = await Promise.all([
        page.waitForResponse((candidate) => {
            const request = candidate.request();
            if (request.method() !== "POST" || !new URL(candidate.url()).pathname.startsWith("/web/dataset/call_button")) return false;
            try {
                const params = request.postDataJSON()?.params;
                return params?.model === model && params?.method === method;
            } catch {
                return false;
            }
        }),
        (async () => {
            await page.getByRole("button", { name: buttonName, exact: true }).click();
            if (confirm) await page.getByRole("dialog").getByRole("button", { name: /^(Ok|Confirm)$/ }).click();
        })(),
    ]);
    if (!response.ok()) throw new Error(`Workflow ${model}.${method} returned HTTP ${response.status()}.`);
    const body = await response.json();
    if (body.error) throw new Error(`Workflow ${model}.${method}: ${body.error.data?.message || body.error.message || "RPC failed"}`);
    const action = body.result;
    const nativeFormField = { "purchase.order": "order_line", "stock.picking": "move_ids" }[action?.res_model];
    if (action?.type === "ir.actions.act_window" && nativeFormField) {
        await expect(page.locator(`.o_form_view .o_field_widget[name="${nativeFormField}"]`)).toBeVisible();
    }
    return action;
}

export async function authenticateApi(request, role) {
    const account = credentials(role);
    const response = await request.post("/web/session/authenticate", {
        data: { jsonrpc: "2.0", method: "call", params: { db: "supplyflow", login: account.login, password: account.password } },
    });
    const body = await response.json();
    if (!body.result?.uid) throw new Error(`Authentication failed for training role ${role}`);
}

export async function trainingIndex(page) {
    return JSON.parse(await rpc(page, "ir.config_parameter", "get_param", ["supplyflow.training_json"]));
}

export async function openAction(page, action) {
    await page.goto(`/odoo/action-${action}`);
    await expect(page.locator(".o_action_manager")).toBeVisible();
}

export async function openRecord(page, action, id) {
    await page.goto(`/odoo/action-${action}/${id}`);
    await expect(page.locator(".o_form_view")).toBeVisible();
}
