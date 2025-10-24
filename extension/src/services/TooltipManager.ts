/**
 * Tooltip Manager - Contextual help system
 *
 * Displays contextual tooltips for first-time feature usage
 *
 * Project Creator: Herman Swanepoel
 */

import * as vscode from "vscode";

export interface TooltipDefinition {
  id: string;
  title: string;
  description: string;
  shortcut?: string;
  position: "top" | "bottom" | "left" | "right";
  trigger: "hover" | "focus" | "manual";
  dismissible: boolean;
}

export interface TooltipState {
  seenTooltips: Set<string>;
  enabled: boolean;
}

export class TooltipManager {
  private static readonly STATE_KEY = "enterpriseAI.tooltips.state";

  private context: vscode.ExtensionContext;
  private tooltips: Map<string, TooltipDefinition> = new Map();
  private state: TooltipState;
  private disposables: vscode.Disposable[] = [];

  constructor(context: vscode.ExtensionContext) {
    this.context = context;
    this.state = this.loadState();
  }

  /**
   * Initialize the tooltip manager
   */
  public async initialize(): Promise<void> {
    console.log("[TooltipManager] Initialized");
  }

  /**
   * Register a tooltip
   */
  public register(tooltip: TooltipDefinition): void {
    this.tooltips.set(tooltip.id, tooltip);
    console.log(`[TooltipManager] Registered tooltip: ${tooltip.id}`);
  }

  /**
   * Show a tooltip
   */
  public async show(tooltipId: string, target?: any): Promise<void> {
    if (!this.state.enabled) {
      return;
    }

    if (this.state.seenTooltips.has(tooltipId)) {
      return;
    }

    const tooltip = this.tooltips.get(tooltipId);
    if (!tooltip) {
      console.warn(`[TooltipManager] Tooltip not found: ${tooltipId}`);
      return;
    }

    // Show as information message with actions
    const actions = ["Got it"];
    if (tooltip.dismissible) {
      actions.push("Don't show again");
    }

    const message = tooltip.shortcut
      ? `${tooltip.description} (${tooltip.shortcut})`
      : tooltip.description;

    const result = await vscode.window.showInformationMessage(
      `💡 ${tooltip.title}: ${message}`,
      ...actions,
    );

    if (result === "Got it") {
      this.markAsSeen(tooltipId);
    } else if (result === "Don't show again") {
      this.setEnabled(false);
    }
  }

  /**
   * Dismiss a specific tooltip
   */
  public dismiss(tooltipId: string): void {
    this.markAsSeen(tooltipId);
  }

  /**
   * Dismiss all tooltips
   */
  public dismissAll(): void {
    this.tooltips.forEach((_, id) => {
      this.markAsSeen(id);
    });
  }

  /**
   * Mark tooltip as seen
   */
  public markAsSeen(tooltipId: string): void {
    this.state.seenTooltips.add(tooltipId);
    this.saveState();
  }

  /**
   * Check if tooltips are enabled
   */
  public isEnabled(): boolean {
    return this.state.enabled;
  }

  /**
   * Enable or disable tooltips
   */
  public setEnabled(enabled: boolean): void {
    this.state.enabled = enabled;
    this.saveState();
    console.log(
      `[TooltipManager] Tooltips ${enabled ? "enabled" : "disabled"}`,
    );
  }

  /**
   * Load state from storage
   */
  private loadState(): TooltipState {
    const stored = this.context.workspaceState.get<any>(
      TooltipManager.STATE_KEY,
    );

    return {
      seenTooltips: new Set(stored?.seenTooltips || []),
      enabled: stored?.enabled !== false,
    };
  }

  /**
   * Save state to storage
   */
  private saveState(): void {
    this.context.workspaceState.update(TooltipManager.STATE_KEY, {
      seenTooltips: Array.from(this.state.seenTooltips),
      enabled: this.state.enabled,
    });
  }

  /**
   * Dispose of resources
   */
  public dispose(): void {
    this.disposables.forEach((d) => d.dispose());
    this.disposables = [];
  }
}
