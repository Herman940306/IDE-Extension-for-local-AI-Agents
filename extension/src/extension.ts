/**
 * Aura AI Assistant Extension
 * Project Creator: Herman Swanepoel
 */

import * as vscode from "vscode";
import { AnalyticsService } from "./services/AnalyticsService";
import { BackendService } from "./services/backendService";
import { RankingService } from "./services/RankingService";
import { OllamaService } from "./services/OllamaService";
import { RankingSettingsPanel } from "./panels/RankingSettingsPanel";
import { GithubRankingTreeProvider } from "./ui/GithubRankingTreeProvider";
import { OllamaModelsTreeProvider } from "./ui/OllamaModelsTreeProvider";

let backendService: BackendService;
let statusBarItem: vscode.StatusBarItem;
let healthStatusItem: vscode.StatusBarItem;
let ollamaStatusItem: vscode.StatusBarItem;
let analyticsService: AnalyticsService | undefined;
let rankingService: RankingService;
let rankingTree: GithubRankingTreeProvider;
let ollamaTree: OllamaModelsTreeProvider;
let ollamaService: OllamaService;

export async function activate(context: vscode.ExtensionContext) {
  console.log("🚀 Aura AI Assistant activating...");

  // Status bar - create first
  statusBarItem = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Right,
    100,
  );
  statusBarItem.text = "$(sync~spin) Aura AI: Connecting...";
  statusBarItem.tooltip = "Connecting to backend...";
  statusBarItem.show();
  context.subscriptions.push(statusBarItem);
  vscode.commands.registerCommand("aura.ollama.runInference", async () => {
    try {
      const cfg = vscode.workspace.getConfiguration("aura");
      let model = cfg.get<string>("ollama.activeModel", "");
      if (!model) {
        const models = await ollamaService.listModels();
        if (!models.length) {
          vscode.window.showWarningMessage("No models installed. Pull a model first.");
          return;
        }
        const pick = await vscode.window.showQuickPick(models.map(m => ({ label: m.name || m.model })), { placeHolder: "Select model to use" });
        if (!pick) return;
        model = pick.label;
        await cfg.update("ollama.activeModel", model, vscode.ConfigurationTarget.Global);
      }
      const prompt = await vscode.window.showInputBox({ prompt: `Enter prompt for ${model}` });
      if (!prompt) return;
      const output = vscode.window.createOutputChannel("Ollama Inference");
      output.clear();
      output.appendLine(`# Model: ${model}`);
      output.appendLine(`> ${prompt}`);
      output.appendLine("");
      await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: `Running inference on ${model}...` }, async () => {
        const text = await ollamaService.generate(model!, prompt);
        output.appendLine(text || "(empty response)");
      });
      output.show(true);
    } catch (e: any) {
      vscode.window.showErrorMessage(`Inference failed: ${e?.message || e}`);
    }
  }),

    // Health status bar (lower priority number -> left, so use 99 just left of main)
    healthStatusItem = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Right,
      99,
    );
  healthStatusItem.text = "$(pulse) Health: ?";
  healthStatusItem.tooltip = "Aura backend health unknown";
  healthStatusItem.command = "aura.checkHealth";
  healthStatusItem.show();
  context.subscriptions.push(healthStatusItem);

  backendService = new BackendService();
  analyticsService = new AnalyticsService(context);
  rankingService = new RankingService(context);
  ollamaService = new OllamaService();
  rankingTree = new GithubRankingTreeProvider();
  ollamaTree = new OllamaModelsTreeProvider(ollamaService);
  const treeView = vscode.window.createTreeView("auraGithubRanking", {
    treeDataProvider: rankingTree,
    showCollapseAll: false,
  });
  context.subscriptions.push(treeView);
  const ollamaView = vscode.window.createTreeView("auraOllamaModels", {
    treeDataProvider: ollamaTree,
    showCollapseAll: false,
  });
  context.subscriptions.push(ollamaView);

  // Ollama status bar (just left of health)
  ollamaStatusItem = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Right,
    98,
  );
  ollamaStatusItem.text = "$(package) Ollama: ?";
  ollamaStatusItem.tooltip = "Ollama status unknown";
  ollamaStatusItem.command = "aura.ollama.listModels";
  ollamaStatusItem.show();
  context.subscriptions.push(ollamaStatusItem);

  try {
    await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: "Connecting to Aura AI backend...",
        cancellable: false,
      },
      async () => {
        await backendService.connect();
      }
    );

    statusBarItem.text = "$(check) Aura AI: Connected";
    statusBarItem.tooltip = "Connected to backend - Ready to assist!";
    vscode.window.showInformationMessage("✅ Aura AI Assistant is ready!");
    console.log("✅ Aura AI Assistant activated successfully");
    // Initial health check
    void refreshHealthStatus();
    void refreshOllamaStatus();
  } catch (error) {
    statusBarItem.text = "$(error) Aura AI: Disconnected";
    statusBarItem.tooltip = "Failed to connect to backend. Click to troubleshoot.";
    statusBarItem.command = "aura.showConnectionHelp";

    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error("❌ Failed to connect to Aura AI backend:", errorMessage);

    vscode.window.showErrorMessage(
      "Failed to connect to Aura AI backend. Please check:\n" +
      "1. Backend is running (check Debug Console)\n" +
      "2. Ollama service is running\n" +
      "3. Configuration in Settings",
      "Show Setup Guide"
    ).then(selection => {
      if (selection === "Show Setup Guide") {
        vscode.env.openExternal(vscode.Uri.parse("https://github.com/Herman940306/IDE-Extension-for-local-AI-Agents#setup"));
      }
    });
  }

  const telemetryCommand = vscode.commands.registerCommand(
    "enterpriseAI.toggleTelemetry",
    async () => {
      if (!analyticsService) {
        return;
      }

      const newValue = !analyticsService.isEnabled();
      await analyticsService.setEnabled(newValue);

      vscode.window.showInformationMessage(
        newValue
          ? "Aura AI telemetry enabled. Anonymous usage metrics will be recorded."
          : "Aura AI telemetry disabled. No anonymous usage metrics will be recorded.",
      );
    },
  );

  const configListener = vscode.workspace.onDidChangeConfiguration((event) => {
    if (
      !analyticsService ||
      !event.affectsConfiguration("enterpriseAI.privacy.allowTelemetry")
    ) {
      return;
    }

    const config = vscode.workspace.getConfiguration("enterpriseAI");
    const enabled = config.get<boolean>("privacy.allowTelemetry", false);

    if (enabled === analyticsService.isEnabled()) {
      return;
    }

    void analyticsService.setEnabled(enabled, { persist: false });
  });

  context.subscriptions.push(telemetryCommand, configListener);

  // Commands
  context.subscriptions.push(
    vscode.commands.registerCommand("aura.generateCode", generateCode),
    vscode.commands.registerCommand("aura.refactorCode", refactorCode),
    vscode.commands.registerCommand("aura.explainCode", explainCode),
    vscode.commands.registerCommand("aura.fixBugs", fixBugs),
    vscode.commands.registerCommand("aura.showConnectionHelp", showConnectionHelp),
    vscode.commands.registerCommand("aura.rankGithubRepos", async () => {
      const cfg = vscode.workspace.getConfiguration("aura");
      const defaultQuery = cfg.get<string>("ranking.defaultQuery", "bug fix performance");
      const query = await vscode.window.showInputBox({
        prompt: "Enter ranking query for your GitHub repositories",
        value: defaultQuery,
      });
      if (!query) return;
      const results = await rankingService.rankRepos(query);
      rankingTree.refresh(results);
      await vscode.commands.executeCommand("workbench.view.explorer");
      await vscode.commands.executeCommand("aura.openGithubRankingView");
    }),
    vscode.commands.registerCommand("aura.rankGithubAll", async () => {
      const cfg = vscode.workspace.getConfiguration("aura");
      const defaultQuery = cfg.get<string>("ranking.defaultQuery", "bug fix performance");
      const query = await vscode.window.showInputBox({
        prompt: "Enter ranking query for repos + issues/PRs",
        value: defaultQuery,
      });
      if (!query) return;
      const results = await rankingService.rankAll(query);
      rankingTree.refresh(results);
      await vscode.commands.executeCommand("workbench.view.explorer");
      await vscode.commands.executeCommand("aura.openGithubRankingView");
    }),
    vscode.commands.registerCommand("aura.openGithubRankingView", async () => {
      await vscode.commands.executeCommand("workbench.view.explorer");
      await vscode.commands.executeCommand("workbench.viewsService.openView", "auraGithubRanking", true);
    }),
    vscode.commands.registerCommand("aura.openRankingSettings", async () => {
      RankingSettingsPanel.createOrShow(context.extensionUri);
    }),
    vscode.commands.registerCommand("aura.checkHealth", async () => {
      await vscode.window.withProgress(
        { location: vscode.ProgressLocation.Window, title: "Aura: Checking health" },
        async () => {
          await refreshHealthStatus(true);
        }
      );
    }),
    vscode.commands.registerCommand("aura.ollama.listModels", async () => {
      try {
        const models = await ollamaService.listModels();
        if (!models.length) {
          vscode.window.showInformationMessage("No models found on Ollama.");
          return;
        }
        const pick = await vscode.window.showQuickPick(models.map(m => ({
          label: m.name || m.model,
          description: m.model,
        })), { placeHolder: "Installed Ollama models" });
        if (pick) {
          vscode.window.showInformationMessage(`Selected model: ${pick.label}`);
        }
        ollamaTree.refresh();
        void refreshOllamaStatus();
      } catch (e: any) {
        vscode.window.showErrorMessage(`Failed to list models: ${e?.message || e}`);
      }
    }),
    vscode.commands.registerCommand("aura.ollama.pullModel", async () => {
      const name = await vscode.window.showInputBox({ prompt: "Enter model to pull (e.g., llama3.1:8b)" });
      if (!name) return;
      try {
        await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: `Pulling ${name}...` }, async (progress) => {
          let lastPercent = 0;
          await ollamaService.pullModel(name, (status, prog) => {
            statusBarItem.text = `$(sync~spin) Pull ${name}`;
            if (prog && prog.total && prog.completed !== undefined) {
              const pct = Math.floor((prog.completed / prog.total) * 100);
              if (pct !== lastPercent) {
                progress.report({ message: `${status} ${pct}%`, increment: pct - lastPercent });
                lastPercent = pct;
              }
              statusBarItem.tooltip = `${status} ${pct}%`;
            } else {
              statusBarItem.tooltip = status;
            }
          });
        });
        statusBarItem.text = "$(check) Aura AI: Connected";
        vscode.window.showInformationMessage(`Model pulled: ${name}`);
        ollamaTree.refresh();
        void refreshOllamaStatus();
        // Persist active model
        const cfg = vscode.workspace.getConfiguration("aura");
        await cfg.update("ollama.activeModel", name, vscode.ConfigurationTarget.Global);
      } catch (e: any) {
        vscode.window.showErrorMessage(`Failed to pull model: ${e?.message || e}`);
      }
    }),
    vscode.commands.registerCommand("aura.ollama.deleteModel", async () => {
      try {
        const models = await ollamaService.listModels();
        if (!models.length) {
          vscode.window.showInformationMessage("No models available to delete.");
          return;
        }
        const pick = await vscode.window.showQuickPick(models.map(m => ({
          label: m.name || m.model,
          description: m.model,
        })), { placeHolder: "Select a model to delete" });
        if (!pick) return;
        const confirm = await vscode.window.showWarningMessage(`Delete model '${pick.label}'?`, { modal: true }, "Delete");
        if (confirm === "Delete") {
          await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: `Deleting ${pick.label}...` }, async () => {
            await ollamaService.deleteModel(pick.label);
          });
          vscode.window.showInformationMessage(`Deleted model: ${pick.label}`);
          ollamaTree.refresh();
          void refreshOllamaStatus();
          const cfg = vscode.workspace.getConfiguration("aura");
          const active = cfg.get<string>("ollama.activeModel", "");
          if (active === pick.label) {
            await cfg.update("ollama.activeModel", "", vscode.ConfigurationTarget.Global);
            vscode.window.showInformationMessage("Active model cleared (deleted). Select a new one.");
          }
        }
      } catch (e: any) {
        vscode.window.showErrorMessage(`Failed to delete model: ${e?.message || e}`);
      }
    }),
    vscode.commands.registerCommand("aura.ollama.refreshModels", async () => {
      ollamaTree.refresh();
      void refreshOllamaStatus();
    }),
    vscode.commands.registerCommand("aura.ollama.setActiveModel", async () => {
      try {
        const models = await ollamaService.listModels();
        if (!models.length) {
          vscode.window.showInformationMessage("No models installed to activate.");
          return;
        }
        const pick = await vscode.window.showQuickPick(models.map(m => ({ label: m.name || m.model })), { placeHolder: "Select active model" });
        if (!pick) return;
        const cfg = vscode.workspace.getConfiguration("aura");
        await cfg.update("ollama.activeModel", pick.label, vscode.ConfigurationTarget.Global);
        vscode.window.showInformationMessage(`Active model set: ${pick.label}`);
        void refreshOllamaStatus();
      } catch (e: any) {
        vscode.window.showErrorMessage(`Failed to set active model: ${e?.message || e}`);
      }
    }),
  );

  // Periodic health refresh every 60s (silent)
  const interval = setInterval(() => {
    void refreshHealthStatus();
    void refreshOllamaStatus();
  }, 60000);
  context.subscriptions.push({ dispose: () => clearInterval(interval) });
}

async function showConnectionHelp() {
  const config = vscode.workspace.getConfiguration("aura");
  const websocketUrl = config.get<string>("backend.websocket", "ws://127.0.0.1:8001/ws");
  const httpUrl = config.get<string>("backend.url", "http://127.0.0.1:8001");

  const message = `🔧 **Aura AI Connection Troubleshooting**

**Current Configuration:**
- WebSocket: ${websocketUrl}
- HTTP API: ${httpUrl}

**Checklist:**
1. ✅ Backend running? Check terminal for "Uvicorn running on http://127.0.0.1:8001"
2. ✅ Ollama running? Open terminal: \`curl http://localhost:11434/api/tags\`
3. ✅ Correct URL? Check Settings > Aura > Backend

**Quick Fix:**
Press F5 to reload the extension after starting services.`;

  const selection = await vscode.window.showInformationMessage(
    message,
    { modal: true },
    "Open Settings",
    "Reload Extension",
    "Test Backend"
  );

  if (selection === "Open Settings") {
    vscode.commands.executeCommand("workbench.action.openSettings", "aura.backend");
  } else if (selection === "Reload Extension") {
    vscode.commands.executeCommand("workbench.action.reloadWindow");
  } else if (selection === "Test Backend") {
    vscode.env.openExternal(vscode.Uri.parse(httpUrl));
  }
}

async function generateCode() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showWarningMessage("⚠️ No active editor found. Please open a file first.");
    return;
  }

  const description = await vscode.window.showInputBox({
    prompt: "Describe the code you want to generate",
    placeHolder: "e.g., Create a function to sort an array",
    validateInput: (value) => {
      if (!value || value.trim().length === 0) {
        return "Description cannot be empty";
      }
      return null;
    },
  });

  if (!description) {
    return;
  }

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: "🤖 Aura AI",
      cancellable: true,
    },
    async (progress, token) => {
      progress.report({ message: "Generating code..." });

      try {
        backendService.sendTask({
          id: `task-${Date.now()}`,
          type: "code_generation",
          description: description,
          content: "",
          context: {
            language: editor.document.languageId,
            file_path: editor.document.fileName,
          },
        });

        progress.report({ increment: 100, message: "Task sent successfully!" });
        updateStatusBar("✅ Aura AI", "Code generation in progress");

        setTimeout(() => {
          vscode.window.showInformationMessage("✨ Code generation task submitted to Aura AI");
        }, 500);
      } catch (error) {
        vscode.window.showErrorMessage(`❌ Failed to send task: ${error}`);
        updateStatusBar("❌ Aura AI", "Task failed");
      }
    }
  );
}

async function refactorCode() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showWarningMessage("⚠️ No active editor found. Please open a file first.");
    return;
  }

  const selection = editor.document.getText(editor.selection);
  if (!selection || selection.trim().length === 0) {
    vscode.window.showWarningMessage("⚠️ Please select code to refactor");
    return;
  }

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: "🤖 Aura AI",
      cancellable: false,
    },
    async (progress) => {
      progress.report({ message: "Analyzing code for refactoring..." });

      try {
        backendService.sendTask({
          id: `task-${Date.now()}`,
          type: "refactor",
          description: "Refactor the selected code to improve quality and maintainability",
          content: selection,
          context: {
            language: editor.document.languageId,
            file_path: editor.document.fileName,
            selection_lines: {
              start: editor.selection.start.line,
              end: editor.selection.end.line,
            },
          },
        });

        progress.report({ increment: 100, message: "Refactoring task sent!" });
        updateStatusBar("✅ Aura AI", "Refactoring in progress");

        setTimeout(() => {
          vscode.window.showInformationMessage(`🔧 Analyzing ${selection.split('\n').length} lines for refactoring`);
        }, 500);
      } catch (error) {
        vscode.window.showErrorMessage(`❌ Failed to send refactoring task: ${error}`);
        updateStatusBar("❌ Aura AI", "Task failed");
      }
    }
  );
}

async function explainCode() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showWarningMessage("⚠️ No active editor found. Please open a file first.");
    return;
  }

  const selection = editor.document.getText(editor.selection);
  if (!selection || selection.trim().length === 0) {
    vscode.window.showWarningMessage("⚠️ Please select code to explain");
    return;
  }

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: "🤖 Aura AI",
      cancellable: false,
    },
    async (progress) => {
      progress.report({ message: "Analyzing code..." });

      try {
        backendService.sendTask({
          id: `task-${Date.now()}`,
          type: "documentation",
          description: "Explain the selected code in detail",
          content: selection,
          context: {
            language: editor.document.languageId,
            file_path: editor.document.fileName,
            selection_lines: {
              start: editor.selection.start.line,
              end: editor.selection.end.line,
            },
          },
        });

        progress.report({ increment: 100, message: "Explanation request sent!" });
        updateStatusBar("✅ Aura AI", "Analyzing code");

        setTimeout(() => {
          vscode.window.showInformationMessage(`📖 Generating explanation for ${selection.split('\n').length} lines of code`);
        }, 500);
      } catch (error) {
        vscode.window.showErrorMessage(`❌ Failed to send explanation task: ${error}`);
        updateStatusBar("❌ Aura AI", "Task failed");
      }
    }
  );
}

async function fixBugs() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showWarningMessage("⚠️ No active editor found. Please open a file first.");
    return;
  }

  const selection = editor.document.getText(editor.selection);
  if (!selection || selection.trim().length === 0) {
    vscode.window.showWarningMessage("⚠️ Please select code to analyze for bugs");
    return;
  }

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: "🤖 Aura AI",
      cancellable: false,
    },
    async (progress) => {
      progress.report({ message: "Scanning for bugs..." });

      try {
        backendService.sendTask({
          id: `task-${Date.now()}`,
          type: "bug_fix",
          description: "Analyze and fix bugs in the selected code",
          content: selection,
          context: {
            language: editor.document.languageId,
            file_path: editor.document.fileName,
            selection_lines: {
              start: editor.selection.start.line,
              end: editor.selection.end.line,
            },
          },
        });

        progress.report({ increment: 100, message: "Bug analysis started!" });
        updateStatusBar("✅ Aura AI", "Analyzing bugs");

        setTimeout(() => {
          vscode.window.showInformationMessage(`🐛 Scanning ${selection.split('\n').length} lines for potential bugs`);
        }, 500);
      } catch (error) {
        vscode.window.showErrorMessage(`❌ Failed to send bug fix task: ${error}`);
        updateStatusBar("❌ Aura AI", "Task failed");
      }
    }
  );
}

function updateStatusBar(text: string, tooltip: string) {
  if (statusBarItem) {
    statusBarItem.text = text;
    statusBarItem.tooltip = tooltip;
  }
}

async function refreshHealthStatus(forceToast = false) {
  if (!rankingService || !healthStatusItem) return;
  try {
    const start = Date.now();
    const res = await rankingService.checkHealth({ silent: !forceToast, force: true });
    const ms = Date.now() - start;
    const cfg = vscode.workspace.getConfiguration("aura");
    const ultra = cfg.get<string>("ranking.ultraMode", "local");
    if (res.ok) {
      healthStatusItem.text = `$(heart) OK ${ms}ms • ${ultra}`;
      healthStatusItem.tooltip = (res.details || "Aura backend healthy") + `\nLatency: ${ms}ms\nULTRA Mode: ${ultra}\nTrace: ${res.traceId}`;
    } else {
      healthStatusItem.text = `$(error) Fail ${ms}ms • ${ultra}`;
      healthStatusItem.tooltip = (res.details || "Aura backend not reachable") + `\nLatency: ${ms}ms\nULTRA Mode: ${ultra}\nTrace: ${res.traceId}`;
    }
  } catch (e: any) {
    const cfg = vscode.workspace.getConfiguration("aura");
    const ultra = cfg.get<string>("ranking.ultraMode", "local");
    healthStatusItem.text = `$(error) Err • ${ultra}`;
    healthStatusItem.tooltip = (e?.message || "Health check error") + `\nULTRA Mode: ${ultra}`;
  }
}

export function deactivate() {
  if (backendService) {
    backendService.disconnect();
  }

  if (analyticsService) {
    analyticsService.dispose();
    analyticsService = undefined;
  }
}

async function refreshOllamaStatus() {
  try {
    const models = await ollamaService.listModels();
    const count = models.length;
    const names = models.slice(0, 5).map(m => m.name || m.model).join(", ");
    const cfg = vscode.workspace.getConfiguration("aura");
    const active = cfg.get<string>("ollama.activeModel", "");
    // Sum sizes for total installed footprint
    let total = 0;
    for (const m of models) total += (m.size || 0);
    const fmt = (n: number) => {
      const units = ["B", "KB", "MB", "GB", "TB"]; let u = 0; let v = n;
      while (v >= 1024 && u < units.length - 1) { v /= 1024; u++; }
      return `${v.toFixed(1)} ${units[u]}`;
    };
    // Attempt to determine free disk space using configured modelsPath
    let freeInfo = "";
    try {
      const modelsPath = cfg.get<string>("ollama.modelsPath", "");
      const path = await getModelsPath(modelsPath);
      const disk = await getDiskFree(path);
      if (disk) freeInfo = `\nDisk: ${fmt(disk.free)} free of ${fmt(disk.size)}`;
    } catch { /* ignore */ }

    ollamaStatusItem.text = `$(package) Ollama: ${count}${active ? ' • ' + active : ''}`;
    const baseTooltip = (count ? `Installed models (${count}):\n${names}${count > 5 ? "\n…" : ""}` : "No models installed") + (active ? `\nActive: ${active}` : "");
    ollamaStatusItem.tooltip = `${baseTooltip}\nTotal installed: ${fmt(total)}${freeInfo}`;
  } catch (e: any) {
    ollamaStatusItem.text = "$(error) Ollama";
    ollamaStatusItem.tooltip = e?.message || "Ollama not reachable";
  }
}

async function getModelsPath(configured: string): Promise<string> {
  if (configured && configured.trim().length > 0) return configured;
  const isWin = process.platform === 'win32';
  const home = process.env.USERPROFILE || process.env.HOME || '';
  return isWin ? `${home}\\.ollama\\models` : `${home}/.ollama/models`;
}

async function getDiskFree(modelsPath: string): Promise<{ free: number; size: number } | undefined> {
  try {
    // Dynamically require to keep extension lean
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const checkDiskSpace = require('check-disk-space').default || require('check-disk-space');
    // Resolve drive root
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const path = require('path');
    const root = path.parse(modelsPath).root || modelsPath;
    const info = await checkDiskSpace(root);
    return { free: info.free, size: info.size };
  } catch {
    return undefined;
  }
}
