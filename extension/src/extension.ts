/**
 * Aura AI Assistant Extension
 * Project Creator: Herman Swanepoel
 */

import * as vscode from "vscode";
import { AnalyticsService } from "./services/AnalyticsService";
import { BackendService } from "./services/backendService";

let backendService: BackendService;
let statusBarItem: vscode.StatusBarItem;
let analyticsService: AnalyticsService | undefined;

export async function activate(context: vscode.ExtensionContext) {
  console.log("Aura AI Assistant activated");

  backendService = new BackendService();
  analyticsService = new AnalyticsService(context);

  try {
    await backendService.connect();
    updateStatusBar("✅ Aura AI", "Connected to backend");
  } catch (error) {
    updateStatusBar("❌ Aura AI", "Backend disconnected");
    vscode.window.showErrorMessage("Failed to connect to Aura AI backend");
  }

  // Status bar
  statusBarItem = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Right,
    100,
  );
  statusBarItem.show();
  context.subscriptions.push(statusBarItem);

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
  );
}

async function generateCode() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showWarningMessage("No active editor");
    return;
  }

  const description = await vscode.window.showInputBox({
    prompt: "Describe the code you want to generate",
    placeHolder: "e.g., Create a function to sort an array",
  });

  if (description) {
    backendService.sendTask({
      id: `task-${Date.now()}`,
      type: "code_generation",
      context: {
        language: editor.document.languageId,
        file_path: editor.document.fileName,
        description,
      },
    });
    vscode.window.showInformationMessage("Task sent to AI backend");
  }
}

async function refactorCode() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) return;

  const selection = editor.document.getText(editor.selection);
  if (!selection) {
    vscode.window.showWarningMessage("Please select code to refactor");
    return;
  }

  backendService.sendTask({
    id: `task-${Date.now()}`,
    type: "refactoring",
    context: {
      language: editor.document.languageId,
      code: selection,
    },
  });
}

async function explainCode() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) return;

  const selection = editor.document.getText(editor.selection);
  if (!selection) {
    vscode.window.showWarningMessage("Please select code to explain");
    return;
  }

  backendService.sendTask({
    id: `task-${Date.now()}`,
    type: "explanation",
    context: {
      language: editor.document.languageId,
      code: selection,
    },
  });
}

async function fixBugs() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) return;

  backendService.sendTask({
    id: `task-${Date.now()}`,
    type: "bug_fixing",
    context: {
      language: editor.document.languageId,
      file_path: editor.document.fileName,
      code: editor.document.getText(),
    },
  });
}

function updateStatusBar(text: string, tooltip: string) {
  if (statusBarItem) {
    statusBarItem.text = text;
    statusBarItem.tooltip = tooltip;
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
