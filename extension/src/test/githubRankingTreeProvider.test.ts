import { strict as assert } from "assert";
import type * as vscode from "vscode";

// Mock vscode minimal API for tree tests
const Module = require("module");
const originalLoad = Module._load;
const mockVscode: Partial<typeof vscode> = {
    ThemeIcon: class { constructor(public id: string) { } },
    EventEmitter: class <T> {
        private listeners: ((e: T) => any)[] = [];
        event = (cb: (e: T) => any) => { this.listeners.push(cb); };
        fire(e: T) { for (const l of this.listeners) l(e); }
    } as any,
    MarkdownString: class { constructor(public value: string) { } },
} as any;
Module._load = function (request: string, parent: any, isMain: boolean) {
    if (request === "vscode") return mockVscode;
    return originalLoad.apply(this, arguments as any);
};

describe("GithubRankingTreeProvider", () => {
    let provider: any;
    before(async () => {
        const mod = await import("../ui/GithubRankingTreeProvider");
        provider = new mod.GithubRankingTreeProvider();
    });

    it("returns empty state node when no results", async () => {
        const children = await provider.getChildren();
        assert.equal(children.length, 1);
        assert.ok(children[0].label.toString().includes("No results"));
    });

    it("maps repo item to node", async () => {
        provider.refresh([
            {
                type: "repo",
                repo: { full_name: "owner/repo", html_url: "https://github.com/owner/repo", name: "repo", private: false },
                score: 0.5,
            },
        ]);
        const children = await provider.getChildren();
        assert.equal(children.length, 1);
        assert.equal(children[0].label, "owner/repo");
        assert.ok(String(children[0].description).includes("score"));
    });
});
