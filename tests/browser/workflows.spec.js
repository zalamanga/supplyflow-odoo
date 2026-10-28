import { test, expect, request as apiRequest } from "@playwright/test";
import fs from "node:fs";
import { authenticateApi, clickWorkflow, login, openAction, openRecord, rpc, trainingIndex } from "./helpers.js";

test("workspace counts, filters and keyboard navigation", async ({ page }) => {
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await login(page);
    await openAction(page, "supplyflow_office.action_workspace");
    await expect(page.getByRole("heading", { name: "Office distribution operations" })).toBeVisible();
    await expect(page.locator(".sf_metric")).toHaveCount(4);
    const overview = await rpc(page, "supplyflow.workspace", "get_overview");
    await expect(page.locator(".sf_metric strong")).toHaveText([
        overview.pending_requests, overview.open_issues, overview.overdue_issues, overview.pending_returns,
    ].map(String));
    const filters = ["Awaiting Approval", "Open submitted issues", "Overdue resolution", "Awaiting warehouse"];
    for (let index = 0; index < filters.length; index++) {
        if (index > 0) await openAction(page, "supplyflow_office.action_workspace");
        const metric = page.locator(".sf_metric").nth(index);
        if (index === 0) {
            await page.getByRole("button", { name: "Refresh", exact: true }).focus();
            await page.keyboard.press("Tab");
            await expect(metric).toBeFocused();
            expect(await metric.evaluate((element) => getComputedStyle(element).outlineStyle)).toBe("solid");
            await page.keyboard.press("Enter");
        } else {
            await metric.click();
        }
        await expect(page.locator(".o_list_view")).toBeVisible();
        await expect(page.locator(".o_searchview")).toContainText(filters[index]);
    }

    await openAction(page, "supplyflow_office.action_workspace");
    await page.getByRole("button", { name: "All requests", exact: true }).click();
    await expect(page.locator(".o_list_view")).toBeVisible();
    await expect(page.locator(".o_searchview_facet")).toHaveCount(0);
    const searchOptions = page.locator(".o_searchview_dropdown_toggler");
    await searchOptions.click();
    await expect(page.locator(".o-dropdown--menu")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.locator(".o-dropdown--menu")).toBeHidden();
    await expect(searchOptions).toBeFocused();

    expect(overview.recent_requests.length).toBeGreaterThan(0);
    const recent = overview.recent_requests[0];
    await openAction(page, "supplyflow_office.action_workspace");
    await page.locator(".sf_recent").getByRole("button", { name: recent.name, exact: true }).click();
    await expect(page.locator('.o_form_view .o_field_widget[name="name"]')).toHaveText(recent.name);
    await expect(page).toHaveURL(new RegExp(`/${recent.id}(?:[?#].*)?$`));
    expect(errors).toEqual([]);
});

test("workspace recovers from RPC failure and fits a narrow screen", async ({ page }) => {
    await login(page);
    const endpoint = "**/web/dataset/call_kw/supplyflow.workspace/get_overview";
    await openAction(page, "supplyflow_office.action_workspace");
    await expect(page.locator(".sf_metric")).toHaveCount(4);
    let releaseEmptyResponse;
    const emptyResponseGate = new Promise((resolve) => { releaseEmptyResponse = resolve; });
    await page.route(endpoint, async (route) => {
        await emptyResponseGate;
        await route.fulfill({
            contentType: "application/json",
            body: JSON.stringify({ jsonrpc: "2.0", result: {
                company: "[Browser test] Controlled empty workspace response",
                today: new Date().toISOString().slice(0, 10),
                pending_requests: 0, open_issues: 0, overdue_issues: 0, pending_returns: 0,
                recent_requests: [],
            } }),
        });
    });
    const emptyResponse = page.waitForResponse(endpoint);
    try {
        await page.getByRole("button", { name: "Refresh", exact: true }).click();
        await expect(page.getByRole("status")).toContainText("Loading operations");
        await expect(page.getByRole("button", { name: "Refresh", exact: true })).toBeDisabled();
        await expect(page.locator(".sf_metric")).toHaveCount(0);
    } finally {
        releaseEmptyResponse();
    }
    await emptyResponse;
    await expect(page.locator(".sf_metric strong")).toHaveText(["0", "0", "0", "0"]);
    await expect(page.locator(".sf_recent")).toContainText("No purchase requests yet.");
    await expect(page.locator(".sf_recent tbody tr")).toHaveCount(0);
    await page.unroute(endpoint);

    await page.route(endpoint, (route) => route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ jsonrpc: "2.0", error: { code: 200, message: "Verification failure", data: { name: "odoo.exceptions.UserError", message: "Verification failure", arguments: ["Verification failure"] } } }),
    }));
    await page.getByRole("button", { name: "Refresh", exact: true }).click();
    await expect(page.getByRole("alert")).toContainText("The workspace could not be loaded");
    await page.unroute(endpoint);
    await page.getByRole("button", { name: "Try again", exact: true }).click();
    await expect(page.locator(".sf_metric")).toHaveCount(4);
    await page.setViewportSize({ width: 390, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(false);
    const refreshed = page.waitForResponse(endpoint);
    await page.getByRole("button", { name: "Refresh", exact: true }).focus();
    await page.keyboard.press("Enter");
    await refreshed;
    await expect(page.locator(".sf_metric").first()).toBeVisible();
});

test("purchase request QWeb produces a real PDF", async ({ page }) => {
    await login(page);
    const index = await trainingIndex(page);
    const response = await page.request.get(`/report/pdf/supplyflow_office.report_request/${index.request_approved}`);
    expect(response.ok()).toBe(true);
    expect(response.headers()["content-type"]).toContain("application/pdf");
    const pdf = await response.body();
    expect(pdf.subarray(0, 5).toString()).toBe("%PDF-");
    expect(pdf.length).toBeGreaterThan(2000);
    fs.mkdirSync(".local", { recursive: true });
    fs.writeFileSync(".local/request-summary.pdf", pdf);
});

test("requester creates a request through the form and withdraws it", async ({ page }) => {
    await login(page, "buyer");
    await openAction(page, "supplyflow_office.action_requests");
    await page.getByRole("button", { name: "New", exact: true }).click();
    await page.locator('.o_field_widget[name="vendor_id"] input').fill("[Training] Paper supplier");
    await page.locator(".o-autocomplete--dropdown-menu").getByText("[Training] Paper supplier", { exact: true }).click();
    await page.locator('.o_field_widget[name="warehouse_id"] input').fill("[Training] Main warehouse");
    await page.locator(".o-autocomplete--dropdown-menu").getByText("[Training] Main warehouse", { exact: true }).click();
    const purpose = `[Browser test] Form entry ${Date.now()}`;
    await page.locator('.o_field_widget[name="purpose"] textarea').fill(purpose);
    await page.getByText("Add a line", { exact: true }).click();
    await page.locator('.o_field_widget[name="line_ids"] .o_field_widget[name="product_id"] input').fill("TRAIN-A4");
    await page.locator(".o-autocomplete--dropdown-menu").getByText(/\[Training\] A4 paper/).click();
    await page.locator('.o_field_widget[name="product_qty"] input').fill("2");
    await page.locator('.o_field_widget[name="price_estimated"] input').fill("45000");
    await clickWorkflow(page, "supplyflow.request", "action_submit", "Submit for Approval");
    await expect(page.getByRole("button", { name: "Withdraw", exact: true })).toBeVisible();
    const [record] = await rpc(page, "supplyflow.request", "search_read", [[['purpose', '=', purpose]]], { fields: ["id", "state"] });
    expect(record.state).toBe("submitted");
    await clickWorkflow(page, "supplyflow.request", "action_cancel", "Withdraw", { confirm: true });
    const [withdrawn] = await rpc(page, "supplyflow.request", "read", [[record.id]], { fields: ["state"] });
    expect(withdrawn.state).toBe("cancelled");
});

test("requester cannot approve, independent approver creates one native RFQ", async ({ browser, baseURL }) => {
    const adminApi = await apiRequest.newContext({ baseURL });
    await authenticateApi(adminApi, "admin");
    const admin = { request: adminApi };
    const index = await trainingIndex(admin);
    await adminApi.dispose();
    const context = await browser.newContext();
    const page = await context.newPage();
    await login(page, "buyer");
    const requestId = await rpc(page, "supplyflow.request", "create", [{
        vendor_id: index.vendor, warehouse_id: index.warehouse_main,
        purpose: "[Browser test] Independent purchasing review",
        line_ids: [[0, 0, { product_id: index.product, product_qty: 2, price_estimated: 45000 }]],
    }]);
    await openRecord(page, "supplyflow_office.action_requests", requestId);
    await clickWorkflow(page, "supplyflow.request", "action_submit", "Submit for Approval");
    await expect(page.getByRole("button", { name: "Approve", exact: true })).toHaveCount(0);
    const denied = await page.request.post("/web/dataset/call_kw/supplyflow.request/action_approve", {
        data: { jsonrpc: "2.0", method: "call", params: { model: "supplyflow.request", method: "action_approve", args: [[requestId]], kwargs: {} } },
    });
    expect((await denied.json()).error).toBeTruthy();
    await context.close();
    const reviewerContext = await browser.newContext();
    const reviewer = await reviewerContext.newPage();
    await login(reviewer, "approver");
    await openRecord(reviewer, "supplyflow_office.action_requests", requestId);
    await clickWorkflow(reviewer, "supplyflow.request", "action_approve", "Approve");
    await expect(reviewer.getByRole("button", { name: "Create RFQ", exact: true })).toBeVisible();
    await clickWorkflow(reviewer, "supplyflow.request", "action_create_rfq", "Create RFQ");
    await expect(reviewer.locator('.o_form_view .o_field_widget[name="partner_id"] input')).toHaveValue("[Training] Paper supplier");
    const [record] = await rpc(reviewer, "supplyflow.request", "read", [[requestId]], { fields: ["state", "purchase_order_id"] });
    expect(record.state).toBe("rfq_created");
    expect(record.purchase_order_id[0]).toBeTruthy();
    const repeat = await rpc(reviewer, "supplyflow.request", "action_create_rfq", [[requestId]]);
    expect(repeat.res_id).toBe(record.purchase_order_id[0]);
    await reviewerContext.close();
});

test("supplier review creates return without completing warehouse transfer", async ({ browser, baseURL }) => {
    const adminApi = await apiRequest.newContext({ baseURL });
    await authenticateApi(adminApi, "admin");
    const admin = { request: adminApi };
    const index = await trainingIndex(admin);
    const reporterContext = await browser.newContext();
    const reporter = await reporterContext.newPage();
    await login(reporter, "warehouse");
    const [move] = await rpc(reporter, "stock.move", "search_read", [[['picking_id', '=', index.receipt], ['product_id', '=', index.product]]], { fields: ["id"], limit: 1 });
    const issueId = await rpc(reporter, "supplyflow.issue", "create", [{
        picking_id: index.receipt, reason: "damage", description: "[Browser test] Damaged paper pack",
        resolver_id: index.approver, line_ids: [[0, 0, { move_id: move.id, affected_qty: 1 }]],
    }]);
    await openRecord(reporter, "supplyflow_office.action_issues", issueId);
    await clickWorkflow(reporter, "supplyflow.issue", "action_submit", "Submit for review");
    await expect(reporter.getByRole("button", { name: "Approve supplier return", exact: true })).toHaveCount(0);
    await reporterContext.close();
    const context = await browser.newContext();
    const page = await context.newPage();
    await login(page, "approver");
    await openRecord(page, "supplyflow_office.action_issues", issueId);
    await clickWorkflow(page, "supplyflow.issue", "action_approve", "Approve supplier return");
    await clickWorkflow(page, "supplyflow.issue", "action_create_return", "Create return transfer");
    await expect(page.locator(".o_form_view")).toBeVisible();
    const [issue] = await rpc(page, "supplyflow.issue", "read", [[issueId]], { fields: ["state", "return_picking_id", "return_state"] });
    expect(issue.state).toBe("return_created");
    expect(issue.return_picking_id[0]).toBeTruthy();
    expect(issue.return_state).not.toBe("done");
    const repeat = await rpc(page, "supplyflow.issue", "action_create_return", [[issueId]]);
    expect(repeat.res_id).toBe(issue.return_picking_id[0]);
    await openRecord(page, "supplyflow_office.action_issues", issueId);
    await clickWorkflow(page, "supplyflow.issue", "action_open_return", /Supplier return/);
    await expect(page.locator(".o_form_view")).toBeVisible();
    await rpc(admin, "stock.picking", "action_cancel", [[issue.return_picking_id[0]]]);
    await context.close();
    await adminApi.dispose();
});

test("rejection, revision and approval cancellation work through form buttons", async ({ page, baseURL }) => {
    const adminApi = await apiRequest.newContext({ baseURL });
    await authenticateApi(adminApi, "admin");
    const index = await trainingIndex({ request: adminApi });
    await adminApi.dispose();
    await login(page, "buyer");
    const id = await rpc(page, "supplyflow.request", "create", [{
        vendor_id: index.vendor, warehouse_id: index.warehouse_main,
        purpose: "[Browser test] Review and revision controls",
        line_ids: [[0, 0, { product_id: index.product, product_qty: 1, price_estimated: 45000 }]],
    }]);
    await openRecord(page, "supplyflow_office.action_requests", id);
    await clickWorkflow(page, "supplyflow.request", "action_submit", "Submit for Approval");
    await authenticateApi(page.request, "approver");
    await openRecord(page, "supplyflow_office.action_requests", id);
    await page.getByRole("tab", { name: "Approval", exact: true }).click();
    await page.locator('.o_field_widget[name="decision_reason"] textarea').fill("[Browser test] Revise the procurement purpose.");
    await clickWorkflow(page, "supplyflow.request", "action_reject", "Reject");
    await authenticateApi(page.request, "buyer");
    await openRecord(page, "supplyflow_office.action_requests", id);
    await clickWorkflow(page, "supplyflow.request", "action_reset_draft", "Revise Draft");
    await page.locator('.o_field_widget[name="purpose"] textarea').fill("[Browser test] Revised office procurement purpose");
    await clickWorkflow(page, "supplyflow.request", "action_submit", "Submit for Approval");
    await authenticateApi(page.request, "approver");
    await openRecord(page, "supplyflow_office.action_requests", id);
    await clickWorkflow(page, "supplyflow.request", "action_approve", "Approve");
    await clickWorkflow(page, "supplyflow.request", "action_cancel", "Cancel Approval", { confirm: true });
    const [record] = await rpc(page, "supplyflow.request", "read", [[id]], { fields: ["state"] });
    expect(record.state).toBe("cancelled");
});

test("shortage resolution and issue cancellation work through form buttons", async ({ page, baseURL }) => {
    const adminApi = await apiRequest.newContext({ baseURL });
    await authenticateApi(adminApi, "admin");
    const index = await trainingIndex({ request: adminApi });
    await adminApi.dispose();
    await login(page, "warehouse");
    const [move] = await rpc(page, "stock.move", "search_read", [[['picking_id', '=', index.receipt], ['product_id', '=', index.product]]], { fields: ["id"], limit: 1 });
    const makeIssue = (reason) => rpc(page, "supplyflow.issue", "create", [{
        picking_id: index.receipt, reason, description: "[Browser test] Supplier resolution controls",
        resolver_id: index.approver, line_ids: [[0, 0, { move_id: move.id, affected_qty: 1 }]],
    }]);
    const shortage = await makeIssue("shortage");
    await openRecord(page, "supplyflow_office.action_issues", shortage);
    await clickWorkflow(page, "supplyflow.issue", "action_submit", "Submit for review");
    await authenticateApi(page.request, "approver");
    await openRecord(page, "supplyflow_office.action_issues", shortage);
    await expect(page.getByRole("button", { name: "Approve supplier return", exact: true })).toHaveCount(0);
    await page.locator('.o_field_widget[name="resolution_note"] textarea').fill("[Browser test] Supplier agreed to deliver the missing pack separately.");
    await clickWorkflow(page, "supplyflow.issue", "action_accept_resolution", "Resolve without return");
    const [resolved] = await rpc(page, "supplyflow.issue", "read", [[shortage]], { fields: ["state", "return_picking_id"] });
    expect(resolved.state).toBe("accepted");
    expect(resolved.return_picking_id).toBe(false);
    await authenticateApi(page.request, "warehouse");
    const cancelled = await makeIssue("damage");
    await openRecord(page, "supplyflow_office.action_issues", cancelled);
    await clickWorkflow(page, "supplyflow.issue", "action_cancel", "Cancel issue", { confirm: true });
    const [record] = await rpc(page, "supplyflow.issue", "read", [[cancelled]], { fields: ["state"] });
    expect(record.state).toBe("cancelled");
    const reviewCancellation = await makeIssue("damage");
    await rpc(page, "supplyflow.issue", "action_submit", [[reviewCancellation]]);
    await authenticateApi(page.request, "approver");
    await openRecord(page, "supplyflow_office.action_issues", reviewCancellation);
    await clickWorkflow(page, "supplyflow.issue", "action_cancel", "Cancel issue", { confirm: true });
    const [reviewCancelled] = await rpc(page, "supplyflow.issue", "read", [[reviewCancellation]], { fields: ["state"] });
    expect(reviewCancelled.state).toBe("cancelled");
});

test("separate HTTP sessions cannot create duplicate RFQs or excess returns", async ({ baseURL }) => {
    const contexts = await Promise.all(Array.from({ length: 4 }, () => apiRequest.newContext({ baseURL })));
    const [admin, buyer, reviewerOne, reviewerTwo] = contexts.map((request) => ({ request }));
    try {
        await authenticateApi(admin.request, "admin");
        await authenticateApi(buyer.request, "buyer");
        await authenticateApi(reviewerOne.request, "approver");
        await authenticateApi(reviewerTwo.request, "approver");
        const index = await trainingIndex(admin);
        const id = await rpc(buyer, "supplyflow.request", "create", [{
            vendor_id: index.vendor, warehouse_id: index.warehouse_main,
            purpose: "[Concurrency test] One RFQ across separate sessions",
            line_ids: [[0, 0, { product_id: index.product, product_qty: 1, price_estimated: 45000 }]],
        }]);
        await rpc(buyer, "supplyflow.request", "action_submit", [[id]]);
        await rpc(reviewerOne, "supplyflow.request", "action_approve", [[id]]);
        const results = await Promise.allSettled([
            rpc(reviewerOne, "supplyflow.request", "action_create_rfq", [[id]]),
            rpc(reviewerTwo, "supplyflow.request", "action_create_rfq", [[id]]),
        ]);
        expect(results.some((result) => result.status === "fulfilled")).toBe(true);
        const [record] = await rpc(reviewerOne, "supplyflow.request", "read", [[id]], { fields: ["name", "purchase_order_id"] });
        const orders = await rpc(reviewerOne, "purchase.order", "search_count", [[['origin', '=', record.name]]]);
        expect(orders).toBe(1);
        for (const result of results.filter((entry) => entry.status === "fulfilled")) expect(result.value.res_id).toBe(record.purchase_order_id[0]);

        const [source] = await rpc(admin, "stock.move", "search_read", [[['picking_id', '=', index.receipt], ['product_id', '=', index.product]]], { fields: ["id", "quantity", "product_uom"] });
        const existing = await rpc(admin, "stock.move", "search_read", [[['origin_returned_move_id', '=', source.id], ['state', '!=', 'cancel']]], { fields: ["state", "quantity", "product_uom_qty"] });
        const remaining = source.quantity - existing.reduce((total, move) => total + (move.state === "done" ? move.quantity : move.product_uom_qty), 0);
        expect(remaining).toBeGreaterThan(2);
        const quantity = Math.floor(remaining / 2) + 1;
        const issues = [];
        for (let number = 0; number < 2; number++) {
            const issue = await rpc(buyer, "supplyflow.issue", "create", [{
                picking_id: index.receipt, reason: "damage", description: `[Concurrency test] Competing supplier return ${number + 1}`,
                resolver_id: index.approver, line_ids: [[0, 0, { move_id: source.id, affected_qty: quantity }]],
            }]);
            await rpc(buyer, "supplyflow.issue", "action_submit", [[issue]]);
            await rpc(reviewerOne, "supplyflow.issue", "action_approve", [[issue]]);
            issues.push(issue);
        }
        const returnResults = await Promise.allSettled([
            rpc(reviewerOne, "supplyflow.issue", "action_create_return", [[issues[0]]]),
            rpc(reviewerTwo, "supplyflow.issue", "action_create_return", [[issues[1]]]),
        ]);
        expect(returnResults.filter((entry) => entry.status === "fulfilled")).toHaveLength(1);
        const cases = await rpc(reviewerOne, "supplyflow.issue", "read", [issues], { fields: ["state", "return_picking_id"] });
        expect(cases.filter((entry) => entry.return_picking_id)).toHaveLength(1);
        const created = cases.find((entry) => entry.return_picking_id).return_picking_id[0];
        // Release the test reservation so repeated verification does not consume training stock.
        await rpc(admin, "stock.picking", "action_cancel", [[created]]);
    } finally {
        await Promise.all(contexts.map((context) => context.dispose()));
    }
});
