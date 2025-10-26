import { defineConfig } from "cypress";

export default defineConfig({
    e2e: {
        baseUrl: "http://127.0.0.1:3000",
        specPattern: "cypress/e2e/**/*.cy.{ts,tsx,js,jsx}",
        supportFile: "cypress/support/e2e.ts",
        screenshotOnRunFailure: true,
        video: false,
        setupNodeEvents(on, config) {
            // implement node event listeners here if needed
            return config;
        },
    },
});
