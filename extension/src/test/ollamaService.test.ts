// eslint-disable-next-line @typescript-eslint/no-var-requires
const assert = require("assert").strict;
// eslint-disable-next-line @typescript-eslint/no-var-requires
const mockRequire = require("mock-require");

// No need to stub vscode now; service falls back gracefully.
// eslint-disable-next-line @typescript-eslint/no-var-requires
const { OllamaService } = require("../services/OllamaService");

describe("OllamaService", () => {
    it("lists models from /api/tags", async () => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (global as any).fetch = async (_url: string) => ({ ok: true, json: async () => ({ models: [{ name: "llama3.1:8b", model: "llama3.1:8b" }] }) });
        const svc = new OllamaService("http://localhost:11434");
        const models = await svc.listModels();
        assert.equal(models.length, 1);
        assert.equal(models[0].name, "llama3.1:8b");
    });

    it("throws on non-ok response", async () => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (global as any).fetch = async (_url: string) => ({ ok: false, status: 500 });
        const svc = new OllamaService("http://localhost:11434");
        await assert.rejects(() => svc.listModels());
    });
});
