import fs from "node:fs";
import { test, expect } from "@playwright/test";
import { clickWorkflow, login, openAction, openRecord, trainingIndex } from "./helpers.js";

async function capture(page, name) {
    await expect(page.locator(".o_loading_indicator")).toBeHidden();
    await page.screenshot({ path: `docs/screenshots/${name}.png`, fullPage: true });
}

test("@capture real ERP screens", async ({ page }) => {
    await login(page);
    const index = await trainingIndex(page);
    fs.mkdirSync("docs/screenshots", { recursive: true });
    await openAction(page, "supplyflow_office.action_workspace");
    await expect(page.locator(".sf_metric")).toHaveCount(4);
    await capture(page, "01-operations");
    await openAction(page, "supplyflow_office.action_requests");
    await expect(page.locator(".o_data_row").first()).toBeVisible();
    await capture(page, "02-purchase-requests");
    await openRecord(page, "supplyflow_office.action_requests", index.request_approved);
    await expect(page.getByRole("button", { name: "Create RFQ", exact: true })).toBeVisible();
    await capture(page, "03-approved-request");
    await openRecord(page, "supplyflow_office.action_requests", index.request_received);
    await clickWorkflow(page, "supplyflow.request", "action_create_rfq", "Open RFQ");
    await expect(page.locator('.o_form_view .o_field_widget[name="partner_id"]')).toContainText("[Training] Paper supplier");
    await capture(page, "04-native-purchase");
    await openRecord(page, "supplyflow_office.action_issues", index.issue_approved);
    await expect(page.getByRole("button", { name: "Create return transfer", exact: true })).toBeVisible();
    await capture(page, "05-supplier-resolution");
    await openRecord(page, "stock.action_picking_tree_all", index.receipt);
    await expect(page.locator(".o_form_view")).toContainText("[Training] Paper supplier");
    await capture(page, "06-native-receipt");
    await openRecord(page, "sale.action_orders", index.sale);
    await expect(page.locator('.o_form_view .o_field_widget[name="order_line"]')).toBeVisible();
    await capture(page, "07-native-sale");
    await page.setViewportSize({ width: 390, height: 844 });
    await openAction(page, "supplyflow_office.action_workspace");
    await expect(page.getByRole("heading", { name: "Office distribution operations" })).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
    expect(overflow).toBe(false);
    await capture(page, "08-mobile-workspace");
});
