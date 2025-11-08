import { strict as assert } from "assert";
import * as vscode from "vscode";
import { OllamaService } from "../services/OllamaService";
import { OllamaModelsTreeProvider } from "../ui/OllamaModelsTreeProvider";

// Mock fetch success
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(global as any).fetch = async (_url: string) => ({ ok: true, json: async () => ({ models: [{ name: "test:1", model: "test:1" }] }) });

// Mock config
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(global as any).vscode = vscode;

describe.skip("OllamaModelsTreeProvider", () => {
    it("returns a model item", async () => {
        const svc = new OllamaService();
        const provider = new OllamaModelsTreeProvider(svc);
        const children = await provider.getChildren();
        assert.equal(children.length, 1);
        assert.equal(children[0].label, "test:1");
    });
});
