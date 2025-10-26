import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
    testDir: './tests',
    timeout: 30_000,
    expect: { timeout: 10_000 },
    retries: 0,
    fullyParallel: true,
    use: {
        baseURL: 'http://127.0.0.1:5288',
        trace: 'on-first-retry',
        headless: true,
    },
    webServer: {
        command: 'npm run dev',
        url: 'http://127.0.0.1:5288',
        reuseExistingServer: true,
        timeout: 60_000,
    },
    projects: [
        {
            name: 'chromium',
            use: { ...devices['Desktop Chrome'] },
        },
        // You can enable more browsers if needed
        // { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
        // { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    ],
});
