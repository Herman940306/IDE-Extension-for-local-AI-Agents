import * as vscode from "vscode";
import { RankingItem } from "../services/RankingService";

export class GithubRankingTreeProvider implements vscode.TreeDataProvider<RankingNode> {
    private _onDidChangeTreeData: vscode.EventEmitter<RankingNode | undefined | void> = new vscode.EventEmitter<RankingNode | undefined | void>();
    readonly onDidChangeTreeData: vscode.Event<RankingNode | undefined | void> = this._onDidChangeTreeData.event;

    private results: RankingItem[] = [];

    refresh(results?: RankingItem[]): void {
        if (results) {
            this.results = results;
        }
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: RankingNode): vscode.TreeItem {
        return element;
    }

    getChildren(element?: RankingNode): Thenable<RankingNode[]> {
        if (!this.results || this.results.length === 0) {
            const empty = new RankingNode(
                "No results. Run 'Aura: Rank GitHub Repos' to populate.",
                vscode.TreeItemCollapsibleState.None
            );
            empty.iconPath = new vscode.ThemeIcon("search-stop");
            empty.tooltip = new vscode.MarkdownString("No results. Use the command palette to run ranking.");
            return Promise.resolve([empty]);
        }

        if (!element) {
            // top level: show all results flat, with type prefixed
            const nodes = this.results.map((item) => toNode(item));
            return Promise.resolve(nodes);
        }

        return Promise.resolve([]);
    }
}

function toNode(item: RankingItem): RankingNode {
    if (item.type === "repo") {
        const label = `${item.repo.full_name}`;
        const descriptionParts: string[] = [];
        if (typeof item.norm_score === "number") descriptionParts.push(`score: ${item.norm_score.toFixed(1)}`);
        else descriptionParts.push(`score: ${item.score.toFixed(2)}`);
        const node = new RankingNode(label, vscode.TreeItemCollapsibleState.None);
        node.description = descriptionParts.join(" · ");
        node.tooltip = new vscode.MarkdownString(
            `Repo: **${item.repo.full_name}**\n\n${item.repo.description || "(no description)"}`
        );
        node.iconPath = new vscode.ThemeIcon("repo");
        node.command = {
            command: "vscode.open",
            title: "Open Repository",
            arguments: [vscode.Uri.parse(item.repo.html_url)],
        };
        return node;
    } else if (item.type === "issue") {
        const label = `#${item.issue.number} ${item.issue.title}`;
        const node = new RankingNode(label, vscode.TreeItemCollapsibleState.None);
        const score = typeof item.norm_score === "number" ? item.norm_score : item.score;
        node.description = `${item.repo.full_name} · score: ${score.toFixed(1)}`;
        node.tooltip = new vscode.MarkdownString(
            `Issue in ${item.repo.full_name}: **${item.issue.title}**\n\n${(item.issue.body || "").slice(0, 400)}`
        );
        node.iconPath = new vscode.ThemeIcon("issues");
        node.command = {
            command: "vscode.open",
            title: "Open Issue",
            arguments: [vscode.Uri.parse(item.issue.html_url)],
        };
        return node;
    } else {
        const label = `#${item.pr.number} ${item.pr.title}`;
        const node = new RankingNode(label, vscode.TreeItemCollapsibleState.None);
        const score = typeof item.norm_score === "number" ? item.norm_score : item.score;
        node.description = `${item.repo.full_name} · score: ${score.toFixed(1)}`;
        node.tooltip = new vscode.MarkdownString(
            `PR in ${item.repo.full_name}: **${item.pr.title}**\n\n${(item.pr.body || "").slice(0, 400)}`
        );
        node.iconPath = new vscode.ThemeIcon("git-pull-request");
        node.command = {
            command: "vscode.open",
            title: "Open Pull Request",
            arguments: [vscode.Uri.parse(item.pr.html_url)],
        };
        return node;
    }
}

export class RankingNode extends vscode.TreeItem {
    constructor(
        label: string | vscode.TreeItemLabel,
        collapsibleState: vscode.TreeItemCollapsibleState
    ) {
        super(label, collapsibleState);
        this.contextValue = "auraRankingItem";
    }
}
