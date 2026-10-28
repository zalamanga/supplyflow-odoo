import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
    testDir: "./tests/browser",
    fullyParallel: false,
    workers: 1,
    timeout: 240000,
    expect: { timeout: 30000 },
    use: {
        baseURL: process.env.SUPPLYFLOW_URL || "http://127.0.0.1:8070",
        channel: process.env.PLAYWRIGHT_CHANNEL || "msedge",
        trace: process.env.CI ? "retain-on-failure" : "off",
        screenshot: "only-on-failure",
        navigationTimeout: 90000,
        actionTimeout: 60000,
    },
    projects: [{ name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 960 } } }],
    reporter: [["list"], ["html", { open: "never" }]],
});
