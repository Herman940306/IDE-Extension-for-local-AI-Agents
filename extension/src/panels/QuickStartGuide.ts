/**
 * Quick Start Guide - Reference documentation
 *
 * Provides searchable quick start guide with common tasks and shortcuts
 *
 * Project Creator: Herman Swanepoel
 */

import * as vscode from "vscode";

export interface GuideSection {
  id: string;
  title: string;
  content: string;
  subsections?: GuideSection[];
  keywords: string[];
}

export interface SearchResult {
  section: GuideSection;
  relevance: number;
  matchedKeywords: string[];
}

export class QuickStartGuide {
  public static currentPanel: QuickStartGuide | undefined;
  private readonly panel: vscode.WebviewPanel;
  private disposables: vscode.Disposable[] = [];
  private sections: GuideSection[];
  private currentSection?: string;

  private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
    this.panel = panel;
    this.sections = this.getGuideSections();

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
   * Create or show the quick start guide
   */
  public static createOrShow(
    extensionUri: vscode.Uri,
    section?: string,
  ): QuickStartGuide {
    const column = vscode.ViewColumn.One;

    // If panel already exists, show it
    if (QuickStartGuide.currentPanel) {
      QuickStartGuide.currentPanel.panel.reveal(column);
      if (section) {
        QuickStartGuide.currentPanel.navigate(section);
      }
      return QuickStartGuide.currentPanel;
    }

    // Create new panel
    const panel = vscode.window.createWebviewPanel(
      "enterpriseAI.quickStart",
      "Quick Start Guide",
      column,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [vscode.Uri.joinPath(extensionUri, "media")],
      },
    );

    QuickStartGuide.currentPanel = new QuickStartGuide(panel, extensionUri);
    if (section) {
      QuickStartGuide.currentPanel.navigate(section);
    }
    return QuickStartGuide.currentPanel;
  }

  /**
   * Show the guide
   */
  public async show(section?: string): Promise<void> {
    if (section) {
      this.navigate(section);
    }
    this.panel.reveal();
  }

  /**
   * Hide the guide
   */
  public hide(): void {
    this.panel.dispose();
  }

  /**
   * Navigate to a section
   */
  public navigate(sectionId: string): void {
    this.currentSection = sectionId;
    this.panel.webview.postMessage({
      command: "navigateToSection",
      sectionId,
    });
  }

  /**
   * Search guide content
   */
  public async search(query: string): Promise<SearchResult[]> {
    const results: SearchResult[] = [];
    const lowerQuery = query.toLowerCase();

    const searchSection = (section: GuideSection): void => {
      const matchedKeywords: string[] = [];
      let relevance = 0;

      // Check title
      if (section.title.toLowerCase().includes(lowerQuery)) {
        relevance += 10;
      }

      // Check content
      if (section.content.toLowerCase().includes(lowerQuery)) {
        relevance += 5;
      }

      // Check keywords
      section.keywords.forEach((keyword) => {
        if (keyword.toLowerCase().includes(lowerQuery)) {
          matchedKeywords.push(keyword);
          relevance += 3;
        }
      });

      if (relevance > 0) {
        results.push({
          section,
          relevance,
          matchedKeywords,
        });
      }

      // Search subsections
      section.subsections?.forEach(searchSection);
    };

    this.sections.forEach(searchSection);

    // Sort by relevance
    return results.sort((a, b) => b.relevance - a.relevance);
  }

  /**
   * Dispose of resources
   */
  public dispose(): void {
    QuickStartGuide.currentPanel = undefined;
    this.panel.dispose();

    while (this.disposables.length) {
      const disposable = this.disposables.pop();
      if (disposable) {
        disposable.dispose();
      }
    }
  }

  /**
   * Handle messages from webview
   */
  private async handleMessage(message: any): Promise<void> {
    switch (message.command) {
      case "search":
        const results = await this.search(message.query);
        this.panel.webview.postMessage({
          command: "searchResults",
          results,
        });
        break;

      case "navigate":
        this.navigate(message.sectionId);
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
   * Get guide sections
   */
  private getGuideSections(): GuideSection[] {
    return [
      {
        id: "getting-started",
        title: "Getting Started",
        content: `
          <h2>Welcome to Enterprise AI Agents!</h2>
          <p>Follow this checklist to get started:</p>
          <ul>
            <li>✓ Complete the onboarding wizard</li>
            <li>✓ Configure your backend connection</li>
            <li>✓ Select your LLM provider</li>
            <li>✓ Try your first AI-assisted code suggestion</li>
            <li>✓ Explore the agent discussion panel</li>
          </ul>
        `,
        keywords: ["start", "begin", "setup", "configure"],
      },
      {
        id: "common-tasks",
        title: "Common Tasks",
        content: `
          <h2>Common Tasks</h2>
          
          <h3>Get Code Suggestions</h3>
          <p>Start typing in any file, and AI suggestions will appear automatically. Press <kbd>Tab</kbd> to accept.</p>
          
          <h3>Ask Agents for Help</h3>
          <p>Open the command palette (<kbd>Ctrl+Shift+P</kbd>) and search for "Ask AI Agents".</p>
          
          <h3>Review Code</h3>
          <p>Select code and use the command "Review Selected Code" to get AI feedback.</p>
          
          <h3>Generate Tests</h3>
          <p>Right-click on a function and select "Generate Tests" from the context menu.</p>
          
          <h3>Switch Modes</h3>
          <p>Click the mode indicator in the status bar to toggle between Offline and Online modes.</p>
        `,
        keywords: ["tasks", "how to", "suggestions", "help", "review", "test"],
      },
      {
        id: "keyboard-shortcuts",
        title: "Keyboard Shortcuts",
        content: `
          <h2>Keyboard Shortcuts</h2>
          <table>
            <tr>
              <th>Action</th>
              <th>Shortcut</th>
            </tr>
            <tr>
              <td>Accept Suggestion</td>
              <td><kbd>Tab</kbd></td>
            </tr>
            <tr>
              <td>Reject Suggestion</td>
              <td><kbd>Esc</kbd></td>
            </tr>
            <tr>
              <td>Ask AI Agents</td>
              <td><kbd>Ctrl+Shift+A</kbd></td>
            </tr>
            <tr>
              <td>Toggle Mode</td>
              <td><kbd>Ctrl+Shift+M</kbd></td>
            </tr>
            <tr>
              <td>Open Agent Discussion</td>
              <td><kbd>Ctrl+Shift+D</kbd></td>
            </tr>
            <tr>
              <td>Open Analytics</td>
              <td><kbd>Ctrl+Shift+Y</kbd></td>
            </tr>
          </table>
        `,
        keywords: ["shortcuts", "keyboard", "keys", "hotkeys"],
      },
      {
        id: "troubleshooting",
        title: "Troubleshooting",
        content: `
          <h2>Troubleshooting</h2>
          
          <h3>Backend Connection Failed</h3>
          <p><strong>Problem:</strong> Cannot connect to AI backend.</p>
          <p><strong>Solution:</strong></p>
          <ul>
            <li>Verify the backend is running</li>
            <li>Check the URL and port in settings</li>
            <li>Ensure no firewall is blocking the connection</li>
            <li>Try restarting VS Code</li>
          </ul>
          
          <h3>No Suggestions Appearing</h3>
          <p><strong>Problem:</strong> AI suggestions not showing up.</p>
          <p><strong>Solution:</strong></p>
          <ul>
            <li>Check that you're in Online or Offline mode (not disabled)</li>
            <li>Verify your LLM provider is configured correctly</li>
            <li>Check the output panel for errors</li>
            <li>Try reloading the window</li>
          </ul>
          
          <h3>Slow Performance</h3>
          <p><strong>Problem:</strong> Extension is slow or unresponsive.</p>
          <p><strong>Solution:</strong></p>
          <ul>
            <li>Check if your local LLM has sufficient resources</li>
            <li>Consider using a smaller model</li>
            <li>Close unnecessary files and extensions</li>
            <li>Check the analytics dashboard for performance metrics</li>
          </ul>
        `,
        keywords: ["troubleshoot", "problem", "error", "fix", "help", "issue"],
      },
      {
        id: "documentation",
        title: "Full Documentation",
        content: `
          <h2>Full Documentation</h2>
          <p>For comprehensive documentation, visit:</p>
          <ul>
            <li><a href="https://docs.example.com">Official Documentation</a></li>
            <li><a href="https://docs.example.com/api">API Reference</a></li>
            <li><a href="https://github.com/example/repo">GitHub Repository</a></li>
            <li><a href="https://discord.gg/example">Community Discord</a></li>
          </ul>
        `,
        keywords: ["docs", "documentation", "reference", "manual"],
      },
    ];
  }

  /**
   * Get webview HTML content
   */
  private getWebviewContent(): string {
    const sectionsHtml = this.sections
      .map(
        (section) => `
      <section id="${section.id}" class="guide-section">
        ${section.content}
      </section>
    `,
      )
      .join("");

    const navHtml = this.sections
      .map(
        (section) => `
      <li>
        <a href="#${section.id}" onclick="navigateToSection('${section.id}'); return false;">
          ${section.title}
        </a>
      </li>
    `,
      )
      .join("");

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline';">
  <title>Quick Start Guide</title>
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
      line-height: 1.6;
    }

    .container {
      display: flex;
      height: 100vh;
    }

    .sidebar {
      width: 250px;
      background-color: var(--vscode-sideBar-background);
      border-right: 1px solid var(--vscode-panel-border);
      padding: 1rem;
      overflow-y: auto;
    }

    .search-box {
      width: 100%;
      padding: 0.5rem;
      margin-bottom: 1rem;
      font-family: var(--vscode-font-family);
      font-size: var(--vscode-font-size);
      color: var(--vscode-input-foreground);
      background-color: var(--vscode-input-background);
      border: 1px solid var(--vscode-input-border);
      border-radius: 2px;
    }

    .search-box:focus {
      outline: 1px solid var(--vscode-focusBorder);
    }

    .nav-list {
      list-style: none;
    }

    .nav-list li {
      margin-bottom: 0.5rem;
    }

    .nav-list a {
      color: var(--vscode-textLink-foreground);
      text-decoration: none;
      display: block;
      padding: 0.5rem;
      border-radius: 2px;
    }

    .nav-list a:hover {
      background-color: var(--vscode-list-hoverBackground);
    }

    .nav-list a:focus {
      outline: 2px solid var(--vscode-focusBorder);
      outline-offset: -2px;
    }

    .content {
      flex: 1;
      padding: 2rem;
      overflow-y: auto;
    }

    .guide-section {
      margin-bottom: 3rem;
    }

    h2 {
      font-size: 1.8rem;
      margin-bottom: 1rem;
      color: var(--vscode-foreground);
    }

    h3 {
      font-size: 1.3rem;
      margin-top: 1.5rem;
      margin-bottom: 0.75rem;
      color: var(--vscode-foreground);
    }

    p {
      margin-bottom: 1rem;
    }

    ul, ol {
      margin-left: 2rem;
      margin-bottom: 1rem;
    }

    li {
      margin-bottom: 0.5rem;
    }

    kbd {
      display: inline-block;
      padding: 0.2rem 0.4rem;
      font-family: var(--vscode-editor-font-family);
      font-size: 0.9em;
      background-color: var(--vscode-editor-inactiveSelectionBackground);
      border: 1px solid var(--vscode-panel-border);
      border-radius: 3px;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 1rem;
    }

    th, td {
      padding: 0.75rem;
      text-align: left;
      border: 1px solid var(--vscode-panel-border);
    }

    th {
      background-color: var(--vscode-editor-inactiveSelectionBackground);
      font-weight: 600;
    }

    a {
      color: var(--vscode-textLink-foreground);
    }

    a:hover {
      text-decoration: underline;
    }

    @media (max-width: 768px) {
      .container {
        flex-direction: column;
      }

      .sidebar {
        width: 100%;
        border-right: none;
        border-bottom: 1px solid var(--vscode-panel-border);
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <nav class="sidebar" role="navigation" aria-label="Guide navigation">
      <input 
        type="search" 
        class="search-box" 
        placeholder="Search guide..."
        aria-label="Search guide"
        oninput="handleSearch(this.value)"
      />
      <ul class="nav-list">
        ${navHtml}
      </ul>
    </nav>

    <main class="content" role="main">
      ${sectionsHtml}
    </main>
  </div>

  <script>
    const vscode = acquireVsCodeApi();

    function navigateToSection(sectionId) {
      const section = document.getElementById(sectionId);
      if (section) {
        section.scrollIntoView({ behavior: 'smooth' });
      }
      vscode.postMessage({
        command: 'navigate',
        sectionId
      });
    }

    let searchTimeout;
    function handleSearch(query) {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        if (query.trim()) {
          vscode.postMessage({
            command: 'search',
            query
          });
        }
      }, 300);
    }

    // Handle messages from extension
    window.addEventListener('message', event => {
      const message = event.data;
      
      if (message.command === 'navigateToSection') {
        navigateToSection(message.sectionId);
      } else if (message.command === 'searchResults') {
        // Handle search results (could highlight matches)
        console.log('Search results:', message.results);
      }
    });
  </script>
</body>
</html>`;
  }
}
