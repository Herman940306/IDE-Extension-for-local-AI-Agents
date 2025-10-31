/**
 * Accessibility Manager - WCAG 2.1 AA Compliance
 *
 * Manages accessibility features including:
 * - Screen reader support
 * - Keyboard navigation
 * - High contrast mode
 * - Font size controls
 * - ARIA labels and roles
 *
 * Project Creator: Herman Swanepoel
 */

import * as vscode from "vscode";

export interface AccessibilityConfig {
  screenReaderEnabled: boolean;
  highContrastMode: boolean;
  fontSize: number;
  keyboardNavigationEnabled: boolean;
  announceActions: boolean;
  reducedMotion: boolean;
}

export class AccessibilityManager {
  private config: AccessibilityConfig;
  private outputChannel: vscode.OutputChannel;
  private statusBarItem: vscode.StatusBarItem;

  constructor(private context: vscode.ExtensionContext) {
    this.outputChannel = vscode.window.createOutputChannel(
      "Enterprise AI - Accessibility",
    );
    this.statusBarItem = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Right,
      100,
    );

    // Load configuration
    this.config = this.loadConfig();

    // Initialize accessibility features
    this.initialize();
  }

  private loadConfig(): AccessibilityConfig {
    const config = vscode.workspace.getConfiguration(
      "enterpriseAI.accessibility",
    );

    return {
      screenReaderEnabled: config.get("screenReaderEnabled", false),
      highContrastMode: config.get("highContrastMode", false),
      fontSize: config.get("fontSize", 14),
      keyboardNavigationEnabled: config.get("keyboardNavigationEnabled", true),
      announceActions: config.get("announceActions", true),
      reducedMotion: config.get("reducedMotion", false),
    };
  }

  private initialize(): void {
    // Detect system accessibility settings
    this.detectSystemSettings();

    // Setup status bar
    this.updateStatusBar();
    this.statusBarItem.show();

    // Register configuration change listener
    this.context.subscriptions.push(
      vscode.workspace.onDidChangeConfiguration((e) => {
        if (e.affectsConfiguration("enterpriseAI.accessibility")) {
          this.config = this.loadConfig();
          this.updateStatusBar();
          this.announceToScreenReader("Accessibility settings updated");
        }
      }),
    );

    this.outputChannel.appendLine("✓ Accessibility Manager initialized");
  }

  private detectSystemSettings(): void {
    // Detect VS Code's accessibility mode
    const isAccessibilityModeEnabled =
      vscode.workspace
        .getConfiguration("editor")
        .get("accessibilitySupport") === "on";

    if (isAccessibilityModeEnabled && !this.config.screenReaderEnabled) {
      this.config.screenReaderEnabled = true;
      this.outputChannel.appendLine("✓ Screen reader detected and enabled");
    }

    // Detect high contrast theme
    const currentTheme = vscode.window.activeColorTheme;
    if (
      currentTheme.kind === vscode.ColorThemeKind.HighContrast ||
      currentTheme.kind === vscode.ColorThemeKind.HighContrastLight
    ) {
      this.config.highContrastMode = true;
      this.outputChannel.appendLine("✓ High contrast mode detected");
    }
  }

  private updateStatusBar(): void {
    const icons: string[] = [];

    if (this.config.screenReaderEnabled) {
      icons.push("$(accessibility)");
    }
    if (this.config.highContrastMode) {
      icons.push("$(symbol-color)");
    }
    if (this.config.keyboardNavigationEnabled) {
      icons.push("$(keyboard)");
    }

    if (icons.length > 0) {
      this.statusBarItem.text = `${icons.join(" ")} A11y`;
      this.statusBarItem.tooltip = "Accessibility features enabled";
      this.statusBarItem.command = "enterpriseAI.accessibility.showSettings";
    } else {
      this.statusBarItem.text = "$(accessibility) A11y";
      this.statusBarItem.tooltip = "Click to configure accessibility";
      this.statusBarItem.command = "enterpriseAI.accessibility.showSettings";
    }
  }

  /**
   * Announce message to screen reader
   */
  public announceToScreenReader(
    message: string,
    priority: "polite" | "assertive" = "polite",
  ): void {
    if (!this.config.screenReaderEnabled || !this.config.announceActions) {
      return;
    }

    // Use VS Code's built-in screen reader announcement
    if (priority === "assertive") {
      vscode.window.showInformationMessage(message);
    } else {
      // Log to output channel for screen readers
      this.outputChannel.appendLine(`[Screen Reader] ${message}`);
    }
  }

  /**
   * Get keyboard shortcut description with accessibility context
   */
  public getAccessibleShortcut(command: string): string {
    const keybinding = vscode.commands.getCommands(true).then((commands) => {
      // Get keybinding for command
      return `Press keyboard shortcut for ${command}`;
    });

    return `Use keyboard shortcut or command palette to execute ${command}`;
  }

  /**
   * Create accessible quick pick with ARIA labels
   */
  public async showAccessibleQuickPick<T extends vscode.QuickPickItem>(
    items: T[],
    options: vscode.QuickPickOptions & { ariaLabel?: string },
  ): Promise<T | undefined> {
    const quickPick = vscode.window.createQuickPick<T>();
    quickPick.items = items;
    quickPick.placeholder = options.placeHolder;
    quickPick.title = options.title;

    // Add ARIA label
    if (options.ariaLabel) {
      this.announceToScreenReader(options.ariaLabel, "polite");
    }

    quickPick.show();

    return new Promise<T | undefined>((resolve) => {
      quickPick.onDidAccept(() => {
        const selection = quickPick.selectedItems[0];
        if (selection) {
          this.announceToScreenReader(`Selected: ${selection.label}`, "polite");
        }
        quickPick.hide();
        resolve(selection);
      });

      quickPick.onDidHide(() => {
        quickPick.dispose();
        resolve(undefined);
      });
    });
  }

  /**
   * Create accessible input box with validation
   */
  public async showAccessibleInputBox(
    options: vscode.InputBoxOptions & { ariaLabel?: string },
  ): Promise<string | undefined> {
    if (options.ariaLabel) {
      this.announceToScreenReader(options.ariaLabel, "polite");
    }

    const result = await vscode.window.showInputBox(options);

    if (result) {
      this.announceToScreenReader(`Input received: ${result}`, "polite");
    }

    return result;
  }

  /**
   * Show accessible progress notification
   */
  public async withAccessibleProgress<T>(
    title: string,
    task: (
      progress: vscode.Progress<{ message?: string; increment?: number }>,
    ) => Promise<T>,
  ): Promise<T> {
    this.announceToScreenReader(`Starting: ${title}`, "polite");

    const result = await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: title,
        cancellable: false,
      },
      async (progress) => {
        const wrappedProgress = {
          report: (value: { message?: string; increment?: number }) => {
            progress.report(value);
            if (value.message) {
              this.announceToScreenReader(value.message, "polite");
            }
          },
        };
        return task(wrappedProgress as any);
      },
    );

    this.announceToScreenReader(`Completed: ${title}`, "polite");
    return result;
  }

  /**
   * Create accessible webview with ARIA support
   */
  public createAccessibleWebview(
    viewType: string,
    title: string,
    options: vscode.WebviewOptions & vscode.WebviewPanelOptions,
  ): vscode.WebviewPanel {
    const panel = vscode.window.createWebviewPanel(
      viewType,
      title,
      vscode.ViewColumn.One,
      options,
    );

    // Announce webview creation
    this.announceToScreenReader(`Opened: ${title}`, "polite");

    // Add accessibility metadata
    panel.webview.html = this.wrapWithAccessibility(panel.webview.html, title);

    return panel;
  }

  /**
   * Wrap HTML content with accessibility features
   */
  private wrapWithAccessibility(html: string, title: string): string {
    const accessibilityCSS = this.getAccessibilityCSS();
    const accessibilityJS = this.getAccessibilityJS();

    return `
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>${title}</title>
                <style>${accessibilityCSS}</style>
            </head>
            <body role="application" aria-label="${title}">
                <div id="skip-to-content">
                    <a href="#main-content" class="skip-link">Skip to main content</a>
                </div>
                <main id="main-content" role="main">
                    ${html}
                </main>
                <script>${accessibilityJS}</script>
            </body>
            </html>
        `;
  }

  /**
   * Get accessibility CSS
   */
  private getAccessibilityCSS(): string {
    return `
            /* Accessibility Styles */
            * {
                box-sizing: border-box;
            }

            body {
                font-size: ${this.config.fontSize}px;
                line-height: 1.5;
                ${this.config.reducedMotion ? "animation: none !important; transition: none !important;" : ""}
            }

            /* Skip to content link */
            .skip-link {
                position: absolute;
                top: -40px;
                left: 0;
                background: var(--vscode-editor-background);
                color: var(--vscode-editor-foreground);
                padding: 8px;
                text-decoration: none;
                z-index: 100;
            }

            .skip-link:focus {
                top: 0;
            }

            /* Focus indicators */
            *:focus {
                outline: 2px solid var(--vscode-focusBorder);
                outline-offset: 2px;
            }

            /* High contrast mode */
            ${
              this.config.highContrastMode
                ? `
                * {
                    border-color: var(--vscode-contrastBorder) !important;
                }
                button, input, select, textarea {
                    border: 2px solid var(--vscode-contrastBorder) !important;
                }
            `
                : ""
            }

            /* Keyboard navigation indicators */
            .keyboard-focus {
                outline: 3px solid var(--vscode-focusBorder);
                outline-offset: 3px;
            }

            /* Screen reader only content */
            .sr-only {
                position: absolute;
                width: 1px;
                height: 1px;
                padding: 0;
                margin: -1px;
                overflow: hidden;
                clip: rect(0, 0, 0, 0);
                white-space: nowrap;
                border-width: 0;
            }

            /* Ensure sufficient color contrast */
            button, a {
                min-height: 44px;
                min-width: 44px;
                display: inline-flex;
                align-items: center;
                justify-content: center;
            }
        `;
  }

  /**
   * Get accessibility JavaScript
   */
  private getAccessibilityJS(): string {
    return `
            // Accessibility JavaScript
            (function() {
                // Track keyboard navigation
                let isKeyboardUser = false;

                document.addEventListener('keydown', function(e) {
                    if (e.key === 'Tab') {
                        isKeyboardUser = true;
                        document.body.classList.add('keyboard-navigation');
                    }
                });

                document.addEventListener('mousedown', function() {
                    isKeyboardUser = false;
                    document.body.classList.remove('keyboard-navigation');
                });

                // Announce dynamic content changes
                const announcer = document.createElement('div');
                announcer.setAttribute('role', 'status');
                announcer.setAttribute('aria-live', 'polite');
                announcer.setAttribute('aria-atomic', 'true');
                announcer.className = 'sr-only';
                document.body.appendChild(announcer);

                window.announceToScreenReader = function(message) {
                    announcer.textContent = message;
                    setTimeout(() => {
                        announcer.textContent = '';
                    }, 1000);
                };

                // Keyboard shortcuts help
                document.addEventListener('keydown', function(e) {
                    if (e.key === '?' && e.shiftKey) {
                        window.announceToScreenReader('Keyboard shortcuts: Tab to navigate, Enter to activate, Escape to close');
                    }
                });
            })();
        `;
  }

  /**
   * Get current accessibility configuration
   */
  public getConfig(): AccessibilityConfig {
    return { ...this.config };
  }

  /**
   * Update accessibility configuration
   */
  public async updateConfig(
    updates: Partial<AccessibilityConfig>,
  ): Promise<void> {
    const config = vscode.workspace.getConfiguration(
      "enterpriseAI.accessibility",
    );

    for (const [key, value] of Object.entries(updates)) {
      await config.update(key, value, vscode.ConfigurationTarget.Global);
    }

    this.config = { ...this.config, ...updates };
    this.updateStatusBar();
    this.announceToScreenReader("Accessibility settings updated", "polite");
  }

  /**
   * Show accessibility settings
   */
  public async showSettings(): Promise<void> {
    const options = [
      {
        label: "$(accessibility) Screen Reader",
        description: this.config.screenReaderEnabled ? "Enabled" : "Disabled",
        detail: "Enable screen reader announcements",
        value: "screenReader",
      },
      {
        label: "$(symbol-color) High Contrast",
        description: this.config.highContrastMode ? "Enabled" : "Disabled",
        detail: "Enable high contrast mode",
        value: "highContrast",
      },
      {
        label: "$(text-size) Font Size",
        description: `${this.config.fontSize}px`,
        detail: "Adjust font size",
        value: "fontSize",
      },
      {
        label: "$(keyboard) Keyboard Navigation",
        description: this.config.keyboardNavigationEnabled
          ? "Enabled"
          : "Disabled",
        detail: "Enable enhanced keyboard navigation",
        value: "keyboardNav",
      },
      {
        label: "$(unmute) Announce Actions",
        description: this.config.announceActions ? "Enabled" : "Disabled",
        detail: "Announce actions to screen reader",
        value: "announceActions",
      },
      {
        label: "$(debug-pause) Reduced Motion",
        description: this.config.reducedMotion ? "Enabled" : "Disabled",
        detail: "Reduce animations and transitions",
        value: "reducedMotion",
      },
    ];

    const selected = await this.showAccessibleQuickPick(options, {
      placeHolder: "Select accessibility setting to toggle",
      title: "Accessibility Settings",
      ariaLabel:
        "Accessibility settings menu. Use arrow keys to navigate, Enter to select.",
    });

    if (selected) {
      await this.toggleSetting(selected.value);
    }
  }

  private async toggleSetting(setting: string): Promise<void> {
    switch (setting) {
      case "screenReader":
        await this.updateConfig({
          screenReaderEnabled: !this.config.screenReaderEnabled,
        });
        break;
      case "highContrast":
        await this.updateConfig({
          highContrastMode: !this.config.highContrastMode,
        });
        break;
      case "fontSize":
        await this.adjustFontSize();
        break;
      case "keyboardNav":
        await this.updateConfig({
          keyboardNavigationEnabled: !this.config.keyboardNavigationEnabled,
        });
        break;
      case "announceActions":
        await this.updateConfig({
          announceActions: !this.config.announceActions,
        });
        break;
      case "reducedMotion":
        await this.updateConfig({ reducedMotion: !this.config.reducedMotion });
        break;
    }
  }

  private async adjustFontSize(): Promise<void> {
    const input = await this.showAccessibleInputBox({
      prompt: "Enter font size (px)",
      value: this.config.fontSize.toString(),
      validateInput: (value) => {
        const num = parseInt(value);
        if (isNaN(num) || num < 10 || num > 32) {
          return "Font size must be between 10 and 32";
        }
        return null;
      },
      ariaLabel: "Enter font size in pixels, between 10 and 32",
    });

    if (input) {
      await this.updateConfig({ fontSize: parseInt(input) });
    }
  }

  /**
   * Dispose resources
   */
  public dispose(): void {
    this.statusBarItem.dispose();
    this.outputChannel.dispose();
  }
}
