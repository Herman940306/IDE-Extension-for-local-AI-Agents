import { strict as assert } from "assert";
import type * as vscode from "vscode";

// Basic mock fetch implementation for tests
function mockFetch(responses: Record<string, any>) {
  (globalThis as any).fetch = async (url: string, opts: any) => {
    const key = String(url);
    if (key.includes("/mcp/github/health")) {
      return { ok: true, json: async () => ({ ok: true }), status: 200 };
    }
    if (key.includes("/mcp/health")) {
      return { ok: true, json: async () => ({ ok: true }), status: 200 };
    }
    if (responses[key]) {
      return { ok: true, json: async () => responses[key], status: 200 };
    }
    return { ok: false, json: async () => ({}), status: 404 };
  };
}

describe("RankingService", () => {
  let service: any;

  before(async () => {
    // Mock the 'vscode' module before importing RankingService
    const Module = require("module");
    const originalLoad = Module._load;
    const mockVscode: Partial<typeof vscode> = {
      workspace: {
        getConfiguration: () => ({ get: (_k: string, def: any) => def }),
      } as any,
      window: {
        showErrorMessage: (_msg: string) => { /* no-op in tests */ },
      } as any,
    };
    Module._load = function (request: string, parent: any, isMain: boolean) {
      if (request === "vscode") {
        return mockVscode;
      }
      return originalLoad.apply(this, arguments as any);
    };
    const mod = await import("../services/RankingService");
    service = new mod.RankingService({} as any);
  });

  it("rankRepos maps repo items", async () => {
    mockFetch({
      "http://127.0.0.1:8001/mcp/github/rank_repos": {
        ranking: [
          { repo: { full_name: "owner/repo", html_url: "https://github.com/owner/repo" }, score: 0.9 },
        ],
      },
    });
    const items = await service.rankRepos("test");
    assert.equal(items.length, 1);
    assert.equal(items[0].repo.full_name, "owner/repo");
  });

  it("rankAll maps mixed items", async () => {
    mockFetch({
      "http://127.0.0.1:8001/mcp/github/rank_all": {
        ranking: [
          { type: "repo", repo: { full_name: "a/b", html_url: "https://github.com/a/b" }, score: 1 },
          { type: "issue", repo: { full_name: "a/b", html_url: "https://github.com/a/b" }, issue: { number: 7, title: "Issue title", html_url: "https://github.com/a/b/issues/7" }, score: 0.7 },
        ],
      },
    });
    const items = await service.rankAll("test");
    assert.equal(items.length, 2);
    assert.equal(items[0].type, "repo");
    assert.equal(items[1].type, "issue");
  });
});
