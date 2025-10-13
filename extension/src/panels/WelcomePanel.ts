/**
 * Welcome Panel - First screen in onboarding flow
 * 
 * Displays welcome message, feature highlights, and action buttons
 * 
 * Project Creator: Herman Swanepoel
 */

import * as vscode from 'vscode';

export interface FeatureHighlight {
  icon: string;
  title: string;
  description: string;
}

export interface WelcomeAction {
  label: string;
  command: string;
  primary: boolean;
}

export interface WelcomeContent {
  title: string;
  description: string;
  features: FeatureHighlight[];
  actions: WelcomeAction[];
}

export class WelcomePanel {
  public static currentPanel: WelcomePanel | undefined;
  private readonly panel: vscode.WebviewPanel;
  private disposables: vscode.Disposable[] = [];

  private onGetStartedEmitter = new vscode.EventEmitter<void>();
  private onSkipTourEmitter = new vscode.EventEmitter<void>();

  public readonly onGetStarted = this.onGetStartedEmitter.event;
  public readonly onSkipTour = this.onSkipTourEmitter.event;

  private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
    this.panel = panel;

    // Set up panel content
    this.panel.webview.html = this.getWebviewContent(extensionUri);

    // Handle messages from webview
    this.panel.webview.onDidReceiveMessage(
      message => this.handleMessage(message),
      null,
      this.disposables
    );

    // Handle panel disposal
    this.panel.onDidDispose(() => this.dispose(), null, this.disposables);
  }

  /**
   * Create or show the welcome panel
   */
  public static createOrShow(extensionUri: vscode.Uri): WelcomePanel {
    const column = vscode.ViewColumn.One;

    // If panel already exists, show it
    if (WelcomePanel.currentPanel) {
      WelcomePanel.currentPanel.panel.reveal(column);
      return WelcomePanel.currentPanel;
    }

    // Create new panel
    const panel = vscode.window.createWebviewPanel(
      'enterpriseAI.welcome',
      'Welcome to Enterprise AI Agents',
      column,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'media')]
      }
    );

    WelcomePanel.currentPanel = new WelcomePanel(panel, extensionUri);
    return WelcomePanel.currentPanel;
  }

  /**
   * Show the welcome panel
   */
  public async show(): Promise<void> {
    this.panel.reveal();
  }

  /**
   * Hide the welcome panel
   */
  public hide(): void {
    this.panel.dispose();
  }

  /**
   * Dispose of the panel and clean up resources
   */
  public dispose(): void {
    WelcomePanel.currentPanel = undefined;

    // Dispose of panel
    this.panel.dispose();

    // Dispose of event emitters
    this.onGetStartedEmitter.dispose();
    this.onSkipTourEmitter.dispose();

    // Dispose of all disposables
    while (this.disposables.length) {
      const disposable = this.disposables.pop();
      if (disposable) {
        disposable.dispose();
      }
    }
  }

  private skillLevel: 'beginner' | 'intermediate' | 'advanced' = 'beginner';

  /**
   * Get selected skill level
   */
  public getSkillLevel(): 'beginner' | 'intermediate' | 'advanced' {
    return this.skillLevel;
  }

  /**
   * Handle messages from the webview
   */
  private handleMessage(message: any): void {
    switch (message.command) {
      case 'getStarted':
        this.skillLevel = message.skillLevel || 'beginner';
        this.onGetStartedEmitter.fire();
        break;
      case 'skipTour':
        this.onSkipTourEmitter.fire();
        break;
      case 'openDocumentation':
        vscode.env.openExternal(vscode.Uri.parse('https://docs.example.com'));
        break;
    }
  }

  /**
   * Get the webview HTML content
   */
  private getWebviewContent(extensionUri: vscode.Uri): string {
    const content = this.getWelcomeContent();

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline';">
  <title>Welcome to Enterprise AI Agents</title>
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
    }

    .container {
      max-width: 800px;
      margin: 0 auto;
    }

    .header {
      text-align: center;
      margin-bottom: 3rem;
    }

    .logo {
      font-size: 3rem;
      margin-bottom: 1rem;
    }

    h1 {
      font-size: 2rem;
      font-weight: 600;
      margin-bottom: 1rem;
      color: var(--vscode-foreground);
    }

    .description {
      font-size: 1.1rem;
      color: var(--vscode-descriptionForeground);
      margin-bottom: 2rem;
    }

    .features {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 1.5rem;
      margin-bottom: 3rem;
    }

    .feature {
      padding: 1.5rem;
      background-color: var(--vscode-editor-inactiveSelectionBackground);
      border-radius: 8px;
      border: 1px solid var(--vscode-panel-border);
    }

    .feature:focus {
      outline: 2px solid var(--vscode-focusBorder);
      outline-offset: 2px;
    }

    .feature-icon {
      font-size: 2rem;
      margin-bottom: 0.5rem;
    }

    .feature-title {
      font-size: 1.1rem;
      font-weight: 600;
      margin-bottom: 0.5rem;
      color: var(--vscode-foreground);
    }

    .feature-description {
      font-size: 0.95rem;
      color: var(--vscode-descriptionForeground);
    }

    .actions {
      display: flex;
      gap: 1rem;
      justify-content: center;
      flex-wrap: wrap;
      margin-bottom: 2rem;
    }

    button {
      padding: 0.75rem 2rem;
      font-size: 1rem;
      font-family: var(--vscode-font-family);
      border: none;
      border-radius: 4px;
      cursor: pointer;
      transition: opacity 0.2s;
    }

    button:hover {
      opacity: 0.9;
    }

    button:focus {
      outline: 2px solid var(--vscode-focusBorder);
      outline-offset: 2px;
    }

    button:active {
      opacity: 0.8;
    }

    .primary-button {
      background-color: var(--vscode-button-background);
      color: var(--vscode-button-foreground);
    }

    .primary-button:hover {
      background-color: var(--vscode-button-hoverBackground);
    }

    .secondary-button {
      background-color: var(--vscode-button-secondaryBackground);
      color: var(--vscode-button-secondaryForeground);
    }

    .secondary-button:hover {
      background-color: var(--vscode-button-secondaryHoverBackground);
    }

    .footer {
      text-align: center;
      margin-top: 2rem;
    }

    .footer a {
      color: var(--vscode-textLink-foreground);
      text-decoration: none;
    }

    .footer a:hover {
      text-decoration: underline;
    }

    .footer a:focus {
      outline: 2px solid var(--vscode-focusBorder);
      outline-offset: 2px;
    }

    .skill-level {
      margin: 2rem 0;
      text-align: center;
    }

    .skill-level h3 {
      font-size: 1.2rem;
      margin-bottom: 1rem;
    }

    .skill-options {
      display: flex;
      gap: 1rem;
      justify-content: center;
      flex-wrap: wrap;
    }

    .skill-option {
      cursor: pointer;
    }

    .skill-option input[type="radio"] {
      position: absolute;
      opacity: 0;
    }

    .skill-card {
      padding: 1rem;
      border: 2px solid var(--vscode-panel-border);
      border-radius: 8px;
      background-color: var(--vscode-editor-inactiveSelectionBackground);
      transition: all 0.2s;
      min-width: 200px;
    }

    .skill-option input:checked + .skill-card {
      border-color: var(--vscode-focusBorder);
      background-color: var(--vscode-list-activeSelectionBackground);
    }

    .skill-option:hover .skill-card {
      border-color: var(--vscode-focusBorder);
    }

    .skill-card strong {
      display: block;
      margin-bottom: 0.5rem;
      font-size: 1.1rem;
    }

    .skill-card p {
      font-size: 0.9rem;
      color: var(--vscode-descriptionForeground);
    }

    /* High contrast mode support */
    @media (prefers-contrast: high) {
      .feature {
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
    }

    /* Responsive design */
    @media (max-width: 600px) {
      body {
        padding: 1rem;
      }

      .features {
        grid-template-columns: 1fr;
      }

      .actions {
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
    <div class="header">
      <div class="logo" role="img" aria-label="Enterprise AI Agents Logo">🤖</div>
      <h1>${content.title}</h1>
      <p class="description">${content.description}</p>
    </div>

    <div class="features" role="list" aria-label="Key Features">
      ${content.features.map(feature => `
        <div class="feature" role="listitem" tabindex="0">
          <div class="feature-icon" role="img" aria-label="${feature.title} icon">${feature.icon}</div>
          <h2 class="feature-title">${feature.title}</h2>
          <p class="feature-description">${feature.description}</p>
        </div>
      `).join('')}
    </div>

    <div class="skill-level" role="group" aria-label="Select your skill level">
      <h3>Select Your Experience Level</h3>
      <div class="skill-options">
        <label class="skill-option">
          <input type="radio" name="skillLevel" value="beginner" checked />
          <div class="skill-card">
            <strong>Beginner</strong>
            <p>New to AI-assisted coding. Show me detailed explanations.</p>
          </div>
        </label>
        <label class="skill-option">
          <input type="radio" name="skillLevel" value="intermediate" />
          <div class="skill-card">
            <strong>Intermediate</strong>
            <p>Familiar with AI tools. Show me concise guidance.</p>
          </div>
        </label>
        <label class="skill-option">
          <input type="radio" name="skillLevel" value="advanced" />
          <div class="skill-card">
            <strong>Advanced</strong>
            <p>Experienced user. Focus on configuration.</p>
          </div>
        </label>
      </div>
    </div>

    <div class="actions" role="group" aria-label="Onboarding Actions">
      ${content.actions.map(action => `
        <button 
          class="${action.primary ? 'primary-button' : 'secondary-button'}"
          onclick="handleAction('${action.command}')"
          aria-label="${action.label}"
        >
          ${action.label}
        </button>
      `).join('')}
    </div>

    <div class="footer">
      <a href="#" onclick="handleAction('openDocumentation')" aria-label="View full documentation">
        View Full Documentation
      </a>
    </div>
  </div>

  <script>
    const vscode = acquireVsCodeApi();

    function handleAction(command) {
      const skillLevel = document.querySelector('input[name="skillLevel"]:checked')?.value || 'beginner';
      vscode.postMessage({ command, skillLevel });
    }

    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        vscode.postMessage({ command: 'skipTour' });
      }
    });

    // Announce to screen readers
    const announcement = document.createElement('div');
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', 'polite');
    announcement.style.position = 'absolute';
    announcement.style.left = '-10000px';
    announcement.textContent = 'Welcome screen loaded. Press Tab to navigate, Enter to activate buttons, or Escape to skip.';
    document.body.appendChild(announcement);
  </script>
</body>
</html>`;
  }

  /**
   * Get welcome content
   */
  private getWelcomeContent(): WelcomeContent {
    return {
      title: 'Welcome to Enterprise AI Agents',
      description: 'Your intelligent coding companion with privacy-first AI assistance, powered by multiple specialized agents working together.',
      features: [
        {
          icon: '🤖',
          title: 'Multi-Agent System',
          description: '6 specialized AI agents collaborate to provide expert assistance across different domains.'
        },
        {
          icon: '🔒',
          title: 'Privacy First',
          description: 'Run completely offline with local LLMs. Your code never leaves your machine.'
        },
        {
          icon: '⚡',
          title: 'Real-time Suggestions',
          description: 'Get intelligent code suggestions as you type, powered by context-aware AI.'
        },
        {
          icon: '💬',
          title: 'Agent Discussion',
          description: 'Watch agents collaborate and discuss solutions to complex problems.'
        },
        {
          icon: '📊',
          title: 'Analytics Dashboard',
          description: 'Track your productivity and see how AI assistance improves your workflow.'
        }
      ],
      actions: [
        {
          label: 'Get Started',
          command: 'getStarted',
          primary: true
        },
        {
          label: 'Skip Tour',
          command: 'skipTour',
          primary: false
        }
      ]
    };
  }
}
