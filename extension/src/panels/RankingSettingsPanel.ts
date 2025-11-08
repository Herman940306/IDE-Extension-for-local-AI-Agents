import * as vscode from "vscode";

export class RankingSettingsPanel {
    public static currentPanel: RankingSettingsPanel | undefined;
    private readonly panel: vscode.WebviewPanel;
    private disposables: vscode.Disposable[] = [];

    private constructor(panel: vscode.WebviewPanel, _extensionUri: vscode.Uri) {
        this.panel = panel;
        this.panel.webview.options = { enableScripts: true };
        this.render();

        this.panel.onDidDispose(() => this.dispose(), null, this.disposables);
        this.panel.webview.onDidReceiveMessage(async (msg) => {
            if (msg?.type === "save") {
                const cfg = vscode.workspace.getConfiguration("aura");
                await cfg.update("ranking.defaultQuery", msg.payload.defaultQuery, vscode.ConfigurationTarget.Global);
                await cfg.update("ranking.itemsPerRepo", Number(msg.payload.itemsPerRepo), vscode.ConfigurationTarget.Global);
                await cfg.update("ranking.sinceDays", Number(msg.payload.sinceDays), vscode.ConfigurationTarget.Global);
                await cfg.update("ranking.ultraMode", msg.payload.ultraMode, vscode.ConfigurationTarget.Global);
                vscode.window.showInformationMessage("Ranking settings saved.");
            }
            if (msg?.type === "load") {
                const cfg = vscode.workspace.getConfiguration("aura");
                const payload = {
                    defaultQuery: cfg.get<string>("ranking.defaultQuery", "bug fix performance"),
                    itemsPerRepo: cfg.get<number>("ranking.itemsPerRepo", 20),
                    sinceDays: cfg.get<number>("ranking.sinceDays", 30),
                    ultraMode: cfg.get<string>("ranking.ultraMode", "local"),
                };
                this.panel.webview.postMessage({ type: "state", payload });
            }
        }, null, this.disposables);
    }

    public static createOrShow(extensionUri: vscode.Uri) {
        const column = vscode.window.activeTextEditor?.viewColumn;
        if (RankingSettingsPanel.currentPanel) {
            RankingSettingsPanel.currentPanel.panel.reveal(column);
            RankingSettingsPanel.currentPanel.render();
            return;
        }
        const panel = vscode.window.createWebviewPanel(
            "auraRankingSettings",
            "Aura: Ranking Settings",
            column ?? vscode.ViewColumn.One,
            { enableScripts: true }
        );
        RankingSettingsPanel.currentPanel = new RankingSettingsPanel(panel, extensionUri);
    }

    private render() {
        this.panel.webview.html = this.getHtml();
    }

    private getHtml(): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Aura Ranking Settings</title>
  <style>
    body { font-family: var(--vscode-font-family); color: var(--vscode-foreground); background: var(--vscode-editor-background); padding: 16px; }
    h1 { font-size: 1.2rem; margin-bottom: 12px; }
    .field { margin-bottom: 12px; }
    label { display:block; margin-bottom: 4px; color: var(--vscode-descriptionForeground); }
    input, select { width: 100%; padding: 6px 8px; background: var(--vscode-input-background); color: var(--vscode-input-foreground); border: 1px solid var(--vscode-input-border); border-radius: 4px; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .actions { margin-top: 16px; display: flex; gap: 8px; }
    button { background: var(--vscode-button-background); color: var(--vscode-button-foreground); border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer; }
    button.secondary { background: var(--vscode-button-secondaryBackground); color: var(--vscode-button-secondaryForeground); }
  </style>
</head>
<body>
  <h1>Ranking Filters</h1>
  <div class="field">
    <label for="defaultQuery">Default Query</label>
    <input id="defaultQuery" type="text" placeholder="bug fix performance" />
  </div>
  <div class="row">
    <div class="field">
      <label for="itemsPerRepo">Items Per Repo</label>
      <input id="itemsPerRepo" type="number" min="1" max="200" />
    </div>
    <div class="field">
      <label for="sinceDays">Since (days)</label>
      <input id="sinceDays" type="number" min="1" max="365" />
    </div>
  </div>
  <div class="field">
    <label for="ultraMode">ULTRA Mode</label>
    <select id="ultraMode">
      <option value="disabled">disabled</option>
      <option value="mock">mock</option>
      <option value="local">local</option>
      <option value="backend">backend</option>
    </select>
  </div>
  <div class="actions">
    <button id="save">Save</button>
    <button id="reload" class="secondary">Reload</button>
  </div>

  <script>
    const vscode = acquireVsCodeApi();
    const els = {
      defaultQuery: document.getElementById('defaultQuery'),
      itemsPerRepo: document.getElementById('itemsPerRepo'),
      sinceDays: document.getElementById('sinceDays'),
      ultraMode: document.getElementById('ultraMode'),
      save: document.getElementById('save'),
      reload: document.getElementById('reload'),
    };

    function load() {
      vscode.postMessage({ type: 'load' });
    }

    window.addEventListener('message', event => {
      const msg = event.data;
      if (msg?.type === 'state') {
        const s = msg.payload || {};
        els.defaultQuery.value = s.defaultQuery || '';
        els.itemsPerRepo.value = String(s.itemsPerRepo ?? 20);
        els.sinceDays.value = String(s.sinceDays ?? 30);
        els.ultraMode.value = s.ultraMode || 'local';
      }
    });

    els.save.addEventListener('click', () => {
      vscode.postMessage({ type: 'save', payload: {
        defaultQuery: els.defaultQuery.value,
        itemsPerRepo: Number(els.itemsPerRepo.value),
        sinceDays: Number(els.sinceDays.value),
        ultraMode: els.ultraMode.value,
      }});
    });
    els.reload.addEventListener('click', load);
    load();
  </script>
</body>
</html>`;
    }

    public dispose() {
        RankingSettingsPanel.currentPanel = undefined;
        this.panel.dispose();
        while (this.disposables.length) {
            const d = this.disposables.pop();
            d?.dispose();
        }
    }
}
