import * as vscode from "vscode";
import { OllamaService } from "../services/OllamaService";

export class OllamaModelsTreeProvider implements vscode.TreeDataProvider<vscode.TreeItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<void> = new vscode.EventEmitter<void>();
    readonly onDidChangeTreeData: vscode.Event<void> = this._onDidChangeTreeData.event;

    constructor(private readonly ollama: OllamaService) { }

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: vscode.TreeItem): vscode.TreeItem {
        return element;
    }

    async getChildren(): Promise<vscode.TreeItem[]> {
        try {
            const models = await this.ollama.listModels();
            if (!models.length) {
                const empty = new vscode.TreeItem("No models installed", vscode.TreeItemCollapsibleState.None);
                empty.description = "Use Pull to add models";
                empty.iconPath = new vscode.ThemeIcon("info");
                empty.contextValue = "ollamaEmpty";
                return [empty];
            }
            const fmt = (n?: number) => {
                if (!n || n <= 0) return undefined;
                const units = ["B", "KB", "MB", "GB", "TB"]; let u = 0; let v = n;
                while (v >= 1024 && u < units.length - 1) { v /= 1024; u++; }
                return `${v.toFixed(1)} ${units[u]}`;
            };
            return models.map(m => {
                const label = m.name || m.model;
                const item = new vscode.TreeItem(label, vscode.TreeItemCollapsibleState.None);
                const size = fmt(m.size);
                const descParts: string[] = [];
                if (m.model !== label) descParts.push(m.model);
                if (size) descParts.push(size);
                item.description = descParts.join(" • ") || undefined;
                item.iconPath = new vscode.ThemeIcon("package");
                item.tooltip = `${label}${m.modified ? `\nModified: ${m.modified}` : ""}${size ? `\nSize: ${size}` : ""}`;
                item.contextValue = "ollamaModel";
                return item;
            });
        } catch (e: any) {
            const err = new vscode.TreeItem("Ollama not reachable", vscode.TreeItemCollapsibleState.None);
            err.tooltip = e?.message || String(e);
            err.iconPath = new vscode.ThemeIcon("error");
            err.contextValue = "ollamaError";
            return [err];
        }
    }
}
