describe("AuraIA smoke test", () => {
    it("loads the home page root", () => {
        cy.visit("/");
        // Assert the application root renders something
        cy.get("#root", { timeout: 10000 }).should("exist");
        cy.get("#root").children().should("have.length.greaterThan", 0);
    });
});
