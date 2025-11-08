/**
 * Tour Panel - Interactive feature tour
 *
 * Guides users through key features with step-by-step navigation
 *
 * Project Creator: Herman Swanepoel
 */

import * as vscode from "vscode";

export interface TourStep {
  id: string;
  title: string;
  description: string;
  icon: string;
  content: string;
  duration?: number;
}

export class TourPanel {
  public static currentPanel: TourPanel | undefined;
  private readonly panel: vscode.WebviewPanel;
  private disposables: vscode.Disposable[] = [];
  private currentStepIndex: number = 0;
  private steps: TourStep[];

  private onNextEmitter = new vscode.EventEmitter<number>();
  private onPreviousEmitter = new vscode.EventEmitter<number>();
  private onSkipEmitter = new vscode.EventEmitter<void>();
  private onCompleteEmitter = new vscode.EventEmitter<void>();

  public readonly onNext = this.onNextEmitter.event;
  public readonly onPrevious = this.onPreviousEmitter.event;
  public readonly onSkip = this.onSkipEmitter.event;
  public readonly onComplete = this.onCompleteEmitter.event;

  private constructor(
    panel: vscode.WebviewPanel,
    extensionUri: vscode.Uri,
    steps: TourStep[],
  ) {
    this.panel = panel;
    this.steps = steps;

    // Set up panel content
    this.updateWebviewContent(extensionUri);

    // Handle messages from webview
    this.panel.webview.onDidReceiveMessage(
      (message) => this.handleMessage(message),
      null,
      this.disposables,
    );

    // Handle panel disposal
    this.panel.onDidDispose(() => this.dispose(), null, this.disposables);
  }

  /**
   * Create or show the tour panel
   */
  public static createOrShow(
    extensionUri: vscode.Uri,
    steps: TourStep[],
  ): TourPanel {
    const column = vscode.ViewColumn.One;

    // If panel already exists, show it
    if (TourPanel.currentPanel) {
      TourPanel.currentPanel.panel.reveal(column);
      return TourPanel.currentPanel;
    }

    // Create new panel
    const panel = vscode.window.createWebviewPanel(
      "enterpriseAI.tour",
      "Feature Tour",
      column,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [vscode.Uri.joinPath(extensionUri, "media")],
      },
    );

    TourPanel.currentPanel = new TourPanel(panel, extensionUri, steps);
    return TourPanel.currentPanel;
  }

  /**
   * Show the tour panel at a specific step
   */
  public async show(stepIndex?: number): Promise<void> {
    if (
      stepIndex !== undefined &&
      stepIndex >= 0 &&
      stepIndex < this.steps.length
    ) {
      this.currentStepIndex = stepIndex;
      this.updateWebviewContent(this.panel.webview.options as any);
    }
    this.panel.reveal();
  }

  /**
   * Hide the tour panel
   */
  public hide(): void {
    this.panel.dispose();
  }

  /**
   * Navigate to next step
   */
  public async next(): Promise<void> {
    if (this.currentStepIndex < this.steps.length - 1) {
      this.currentStepIndex++;
      this.updateWebviewContent(this.panel.webview.options as any);
      this.onNextEmitter.fire(this.currentStepIndex);
    } else {
      // Tour complete
      this.onCompleteEmitter.fire();
    }
  }

  /**
   * Navigate to previous step
   */
  public async previous(): Promise<void> {
    if (this.currentStepIndex > 0) {
      this.currentStepIndex--;
      this.updateWebviewContent(this.panel.webview.options as any);
      this.onPreviousEmitter.fire(this.currentStepIndex);
    }
  }

  /**
   * Skip the tour
   */
  public async skip(): Promise<void> {
    this.onSkipEmitter.fire();
  }

  /**
   * Get current step index
   */
  public getCurrentStep(): number {
    return this.currentStepIndex;
  }

  /**
   * Get total number of steps
   */
  public getTotalSteps(): number {
    return this.steps.length;
  }

  /**
   * Dispose of the panel and clean up resources
   */
  public dispose(): void {
    TourPanel.currentPanel = undefined;

    // Dispose of panel
    this.panel.dispose();

    // Dispose of event emitters
    this.onNextEmitter.dispose();
    this.onPreviousEmitter.dispose();
    this.onSkipEmitter.dispose();
    this.onCompleteEmitter.dispose();

    // Dispose of all disposables
    while (this.disposables.length) {
      const disposable = this.disposables.pop();
      if (disposable) {
        disposable.dispose();
      }
    }
  }

  /**
   * Handle messages from the webview
   */
  private handleMessage(message: any): void {
    switch (message.command) {
      case "next":
        this.next();
        break;
      case "previous":
        this.previous();
        break;
      case "skip":
        this.skip();
        break;
    }
  }

  /**
   * Update webview content
   */
  private updateWebviewContent(extensionUri: any): void {
    this.panel.webview.html = this.getWebviewContent();
  }

  /**
   * Get the webview HTML content
   */
  private getWebviewContent(): string {
    const currentStep = this.steps[this.currentStepIndex];
    const stepNumber = this.currentStepIndex + 1;
    const totalSteps = this.steps.length;
    const isFirstStep = this.currentStepIndex === 0;
    const isLastStep = this.currentStepIndex === this.steps.length - 1;

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline';">
  <title>Feature Tour - Step ${stepNumber} of ${totalSteps}</title>
  <style>
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: var(--vscode-font-family);
      font-size: var(--vscode-font-size);
      color: var(--vscode-foreground);
      background-color: var(--vscode-editor-background);
      padding: 2rem;
      line-height: 1.6;
      overflow-x: hidden;
    }

    .container {
      max-width: 800px;
      margin: 0 auto;
    }

    .progress-bar {
      width: 100%;
      height: 4px;
      background-color: var(--vscode-editor-inactiveSelectionBackground);
      border-radius: 2px;
      margin-bottom: 2rem;
      overflow: hidden;
    }

    .progress-fill {
      height: 100%;
      background-color: var(--vscode-progressBar-background);
      transition: width 0.3s ease;
      width: ${(stepNumber / totalSteps) * 100}%;
    }

    .step-indicator {
      text-align: center;
      color: var(--vscode-descriptionForeground);
      font-size: 0.9rem;
      margin-bottom: 2rem;
    }

    .content {
      text-align: center;
      margin-bottom: 3rem;
    }

    .icon {
      font-size: 4rem;
      margin-bottom: 1.5rem;
      animation: fadeIn 0.5s ease;
    }

    .title {
      font-size: 2rem;
      font-weight: 600;
      margin-bottom: 1rem;
      color: var(--vscode-foreground);
      animation: fadeIn 0.5s ease 0.1s both;
    }

    .description {
      font-size: 1.1rem;
      color: var(--vscode-descriptionForeground);
      margin-bottom: 2rem;
      line-height: 1.8;
      animation: fadeIn 0.5s ease 0.2s both;
    }

    .feature-content {
      background-color: var(--vscode-editor-inactiveSelectionBackground);
      border: 1px solid var(--vscode-panel-border);
      border-radius: 8px;
      padding: 2rem;
      text-align: left;
      animation: fadeIn 0.5s ease 0.3s both;
    }

    .feature-content p {
      margin-bottom: 1rem;
      line-height: 1.8;
    }

    .feature-content p:last-child {
      margin-bottom: 0;
    }

    .navigation {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 1rem;
      margin-top: 3rem;
    }

    .nav-buttons {
      display: flex;
      gap: 1rem;
    }

    button {
      padding: 0.75rem 1.5rem;
      font-size: 1rem;
      font-family: var(--vscode-font-family);
      border: none;
      border-radius: 4px;
      cursor: pointer;
      transition: opacity 0.2s;
    }

    button:hover:not(:disabled) {
      opacity: 0.9;
    }

    button:focus {
      outline: 2px solid var(--vscode-focusBorder);
      outline-offset: 2px;
    }

    button:active:not(:disabled) {
      opacity: 0.8;
    }

    button:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .primary-button {
      background-color: var(--vscode-button-background);
      color: var(--vscode-button-foreground);
    }

    .primary-button:hover:not(:disabled) {
      background-color: var(--vscode-button-hoverBackground);
    }

    .secondary-button {
      background-color: var(--vscode-button-secondaryBackground);
      color: var(--vscode-button-secondaryForeground);
    }

    .secondary-button:hover:not(:disabled) {
      background-color: var(--vscode-button-secondaryHoverBackground);
    }

    .skip-button {
      background-color: transparent;
      color: var(--vscode-descriptionForeground);
      text-decoration: underline;
      padding: 0.75rem 1rem;
    }

    @keyframes fadeIn {
      from {
        opacity: 0;
        transform: translateY(10px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    /* High contrast mode support */
    @media (prefers-contrast: high) {
      .feature-content {
        border-width: 2px;
      }
      
      button {
        border: 2px solid currentColor;
      }
    }

    /* Reduced motion support */
    @media (prefers-reduced-motion: reduce) {
      * {
        animation: none !important;
        transition: none !important;
      }
      
      .progress-fill {
        transition: none;
      }
    }

    /* Responsive design */
    @media (max-width: 600px) {
      body {
        padding: 1rem;
      }

      .icon {
        font-size: 3rem;
      }

      .title {
        font-size: 1.5rem;
      }

      .description {
        font-size: 1rem;
      }

      .navigation {
        flex-direction: column;
      }

      .nav-buttons {
        width: 100%;
        flex-direction: column;
      }

      button {
        width: 100%;
      }
    }
  </style>
</head>
<body>
  <div class="container" role="main">
    <div class="progress-bar" role="progressbar" aria-valuenow="${stepNumber}" aria-valuemin="1" aria-valuemax="${totalSteps}" aria-label="Tour progress">
      <div class="progress-fill"></div>
    </div>

    <div class="step-indicator" aria-live="polite">
      Step ${stepNumber} of ${totalSteps}
    </div>

    <div class="content">
      <div class="icon" role="img" aria-label="${currentStep.title} icon">${currentStep.icon}</div>
      <h1 class="title">${currentStep.title}</h1>
      <p class="description">${currentStep.description}</p>
      
      <div class="feature-content">
        ${currentStep.content}
      </div>
    </div>

    <div class="navigation">
      <button 
        class="skip-button" 
        onclick="handleAction('skip')"
        aria-label="Skip tour"
      >
        Skip Tour
      </button>

      <div class="nav-buttons">
        <button 
          class="secondary-button" 
          onclick="handleAction('previous')"
          ${isFirstStep ? "disabled" : ""}
          aria-label="Previous step"
        >
          ← Previous
        </button>
        <button 
          class="primary-button" 
          onclick="handleAction('next')"
          aria-label="${isLastStep ? "Complete tour" : "Next step"}"
        >
          ${isLastStep ? "Complete Tour" : "Next →"}
        </button>
      </div>
    </div>
  </div>

  <script>
    const vscode = acquireVsCodeApi();

    function handleAction(command) {
      vscode.postMessage({ command });
    }

    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        vscode.postMessage({ command: 'skip' });
      } else if (e.key === 'ArrowRight' && !${isLastStep}) {
        vscode.postMessage({ command: 'next' });
      } else if (e.key === 'ArrowLeft' && !${isFirstStep}) {
        vscode.postMessage({ command: 'previous' });
      }
    });

    // Announce to screen readers
    const announcement = document.createElement('div');
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', 'polite');
    announcement.style.position = 'absolute';
    announcement.style.left = '-10000px';
    announcement.textContent = 'Step ${stepNumber} of ${totalSteps}: ${currentStep.title}. Use arrow keys to navigate, or press Escape to skip.';
    document.body.appendChild(announcement);
  </script>
</body>
</html>`;
  }
}
