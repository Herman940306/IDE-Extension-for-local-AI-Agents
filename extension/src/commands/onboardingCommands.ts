/**
 * Onboarding Commands - VS Code command registration
 *
 * Registers all onboarding-related commands
 *
 * Project Creator: Herman Swanepoel
 */

import * as vscode from "vscode";
import { OnboardingManager } from "../services/OnboardingManager";

/**
 * Register all onboarding commands
 */
export function registerOnboardingCommands(
  context: vscode.ExtensionContext,
  onboardingManager: OnboardingManager,
): void {
  // Start onboarding command
  const startOnboarding = vscode.commands.registerCommand(
    "enterpriseAI.startOnboarding",
    async () => {
      try {
        await onboardingManager.startOnboarding();
      } catch (error) {
        vscode.window.showErrorMessage(`Failed to start onboarding: ${error}`);
      }
    },
  );

  // Restart onboarding command
  const restartOnboarding = vscode.commands.registerCommand(
    "enterpriseAI.restartOnboarding",
    async () => {
      try {
        const result = await vscode.window.showWarningMessage(
          "This will reset your onboarding progress. Continue?",
          "Yes",
          "No",
        );

        if (result === "Yes") {
          await onboardingManager.restartOnboarding();
        }
      } catch (error) {
        vscode.window.showErrorMessage(
          `Failed to restart onboarding: ${error}`,
        );
      }
    },
  );

  // Open quick start guide command
  const openQuickStartGuide = vscode.commands.registerCommand(
    "enterpriseAI.openQuickStartGuide",
    () => {
      try {
        onboardingManager.showQuickStartGuide();
      } catch (error) {
        vscode.window.showErrorMessage(
          `Failed to open quick start guide: ${error}`,
        );
      }
    },
  );

  // Skip onboarding command
  const skipOnboarding = vscode.commands.registerCommand(
    "enterpriseAI.skipOnboarding",
    async () => {
      try {
        await onboardingManager.skipOnboarding();
      } catch (error) {
        vscode.window.showErrorMessage(`Failed to skip onboarding: ${error}`);
      }
    },
  );

  // Resume onboarding command
  const resumeOnboarding = vscode.commands.registerCommand(
    "enterpriseAI.resumeOnboarding",
    async () => {
      try {
        await onboardingManager.resumeOnboarding();
      } catch (error) {
        vscode.window.showErrorMessage(`Failed to resume onboarding: ${error}`);
      }
    },
  );

  // Register all commands
  context.subscriptions.push(
    startOnboarding,
    restartOnboarding,
    openQuickStartGuide,
    skipOnboarding,
    resumeOnboarding,
  );

  console.log("[OnboardingCommands] All commands registered");
}
