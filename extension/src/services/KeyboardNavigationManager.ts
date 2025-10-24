/**
 * Keyboard Navigation Manager
 *
 * Provides comprehensive keyboard navigation support for all extension features
 * Ensures WCAG 2.1 AA compliance for keyboard accessibility
 *
 * Project Creator: Herman Swanepoel
 */

import * as vscode from "vscode";

export interface KeyboardShortcut {
  key: string;
  command: string;
  when?: string;
  description: string;
  category: string;
}

export class KeyboardNavigationManager {
  private shortcuts: Map<string, KeyboardShortcut> = new Map();
  private navigationHistory: string[] = [];
  private currentFocusIndex: number = -1;

  constructor(private context: vscode.ExtensionContext) {
    this.registerDefaultShortcuts();
    this.setupNavigationCommands();
  }

  private registerDefaultShortcuts(): void {
    const shortcuts: KeyboardShortcut[] = [
      // Mode Toggle
      {
        key: "ctrl+shift+m",
        command: "enterpriseAI.toggleMode",
        description: "Toggle Offline/Online Mode",
        category: "Mode",
      },
      // Agent Commands
      {
        key: "ctrl+shift+t",
        command: "enterpriseAI.generateTests",
        description: "Generate Tests for Current File",
        category: "Agent",
      },
      {
        key: "ctrl+shift+r",
        command: "enterpriseAI.refactorSelection",
        description: "Refactor Selection",
        category: "Agent",
      },
      {
        key: "ctrl+shift+e",
        command: "enterpriseAI.explainCode",
        description: "Explain Code",
        category: "Agent",
      },
      {
        key: "ctrl+shift+s",
        command: "enterpriseAI.findSecurityIssues",
        description: "Find Security Issues",
        category: "Agent",
      },
      {
        key: "ctrl+shift+d",
        command: "enterpriseAI.generateDocumentation",
        description: "Generate Documentation",
        category: "Agent",
      },
      // Navigation
      {
        key: "ctrl+shift+a",
        command: "enterpriseAI.startAgentDiscussion",
        description: "Start Agent Discussion",
        category: "Navigation",
      },
      {
        key: "ctrl+shift+v",
        command: "enterpriseAI.viewAnalytics",
        description: "View Analytics Dashboard",
        category: "Navigation",
      },
      // Accessibility
      {
        key: "ctrl+shift+alt+a",
        command: "enterpriseAI.accessibility.showSettings",
        description: "Show Accessibility Settings",
        category: "Accessibility",
      },
      {
        key: "ctrl+shift+alt+h",
        command: "enterpriseAI.accessibility.showHelp",
        description: "Show Keyboard Shortcuts Help",
        category: "Accessibility",
      },
      // Quick Actions
      {
        key: "ctrl+shift+i",
        command: "enterpriseAI.reindexCodebase",
        description: "Reindex Codebase",
        category: "Quick Actions",
      },
    ];

    shortcuts.forEach((shortcut) => {
      this.shortcuts.set(shortcut.command, shortcut);
    });
  }

  private setupNavigationCommands(): void {
    // Show keyboard shortcuts help
    this.context.subscriptions.push(
      vscode.commands.registerCommand(
        "enterpriseAI.accessibility.showHelp",
        () => this.showKeyboardHelp(),
      ),
    );

    // Navigate forward in history
    this.context.subscriptions.push(
      vscode.commands.registerCommand("enterpriseAI.navigation.forward", () =>
        this.navigateForward(),
      ),
    );

    // Navigate backward in history
    this.context.subscriptions.push(
      vscode.commands.registerCommand("enterpriseAI.navigation.backward", () =>
        this.navigateBackward(),
      ),
    );

    // Focus next element
    this.context.subscriptions.push(
      vscode.commands.registerCommand("enterpriseAI.navigation.focusNext", () =>
        this.focusNext(),
      ),
    );

    // Focus previous element
    this.context.subscriptions.push(
      vscode.commands.registerCommand(
        "enterpriseAI.navigation.focusPrevious",
        () => this.focusPrevious(),
      ),
    );
  }

  /**
   * Show keyboard shortcuts help
   */
  public async showKeyboardHelp(): Promise<void> {
    const categories = this.groupShortcutsByCategory();

    interface ShortcutItem extends vscode.QuickPickItem {
      shortcut?: KeyboardShortcut;
    }

    const items: ShortcutItem[] = [];
    for (const [category, shortcuts] of categories.entries()) {
      items.push({
        label: `$(folder) ${category}`,
        kind: vscode.QuickPickItemKind.Separator,
      });

      shortcuts.forEach((shortcut) => {
        items.push({
          label: `$(keyboard) ${shortcut.key}`,
          description: shortcut.description,
          detail: `Command: ${shortcut.command}`,
          shortcut: shortcut,
        });
      });
    }

    const selected = await vscode.window.showQuickPick(items, {
      placeHolder: "Keyboard Shortcuts - Press Enter to execute command",
      title: "Enterprise AI - Keyboard Shortcuts",
      matchOnDescription: true,
      matchOnDetail: true,
    });

    if (selected && selected.shortcut) {
      await vscode.commands.executeCommand(selected.shortcut.command);
    }
  }

  private groupShortcutsByCategory(): Map<string, KeyboardShortcut[]> {
    const categories = new Map<string, KeyboardShortcut[]>();

    this.shortcuts.forEach((shortcut) => {
      if (!categories.has(shortcut.category)) {
        categories.set(shortcut.category, []);
      }
      categories.get(shortcut.category)!.push(shortcut);
    });

    return categories;
  }

  /**
   * Add command to navigation history
   */
  public addToHistory(command: string): void {
    this.navigationHistory.push(command);
    this.currentFocusIndex = this.navigationHistory.length - 1;

    // Limit history size
    if (this.navigationHistory.length > 50) {
      this.navigationHistory.shift();
      this.currentFocusIndex--;
    }
  }

  /**
   * Navigate forward in history
   */
  private async navigateForward(): Promise<void> {
    if (this.currentFocusIndex < this.navigationHistory.length - 1) {
      this.currentFocusIndex++;
      const command = this.navigationHistory[this.currentFocusIndex];
      await vscode.commands.executeCommand(command);
    } else {
      vscode.window.showInformationMessage("No forward navigation available");
    }
  }

  /**
   * Navigate backward in history
   */
  private async navigateBackward(): Promise<void> {
    if (this.currentFocusIndex > 0) {
      this.currentFocusIndex--;
      const command = this.navigationHistory[this.currentFocusIndex];
      await vscode.commands.executeCommand(command);
    } else {
      vscode.window.showInformationMessage("No backward navigation available");
    }
  }

  /**
   * Focus next element (for custom UI)
   */
  private focusNext(): void {
    // Emit event for custom UI components
    vscode.commands.executeCommand("workbench.action.focusNextPart");
  }

  /**
   * Focus previous element (for custom UI)
   */
  private focusPrevious(): void {
    // Emit event for custom UI components
    vscode.commands.executeCommand("workbench.action.focusPreviousPart");
  }

  /**
   * Get shortcut for command
   */
  public getShortcut(command: string): KeyboardShortcut | undefined {
    return this.shortcuts.get(command);
  }

  /**
   * Get all shortcuts
   */
  public getAllShortcuts(): KeyboardShortcut[] {
    return Array.from(this.shortcuts.values());
  }

  /**
   * Register custom shortcut
   */
  public registerShortcut(shortcut: KeyboardShortcut): void {
    this.shortcuts.set(shortcut.command, shortcut);
  }

  /**
   * Get keyboard shortcut description for accessibility
   */
  public getAccessibleDescription(command: string): string {
    const shortcut = this.shortcuts.get(command);
    if (shortcut) {
      return `${shortcut.description}. Keyboard shortcut: ${shortcut.key}`;
    }
    return `Execute ${command}`;
  }

  /**
   * Dispose resources
   */
  public dispose(): void {
    this.shortcuts.clear();
    this.navigationHistory = [];
  }
}
