/**
 * Agent Discussion Panel - Multi-agent collaboration UI
 * Project Creator: Herman Swanepoel
 */

import * as vscode from "vscode";
import { WebSocketClient } from "../services/WebSocketClient";

interface AgentMessage {
  agent_id: string;
  agent_name: string;
  message: string;
  vote?: "approve" | "approve_with_changes" | "reject";
  timestamp: number;
  confidence?: number;
  reasoning?: string;
}

interface Discussion {
  id: string;
  task_id: string;
  title: string;
  messages: AgentMessage[];
  status: "active" | "resolved" | "cancelled";
  created_at: number;
}

export class AgentDiscussionPanel {
  public static currentPanel: AgentDiscussionPanel | undefined;
  private readonly _panel: vscode.WebviewPanel;
  private _disposables: vscode.Disposable[] = [];
  private wsClient: WebSocketClient;
  private currentDiscussion: Discussion | null = null;
  private conversationHistory: Map<string, Discussion> = new Map();

  public static createOrShow(
    extensionUri: vscode.Uri,
    wsClient: WebSocketClient,
  ) {
    const column = vscode.window.activeTextEditor
      ? vscode.window.activeTextEditor.viewColumn
      : undefined;

    // If we already have a panel, show it
    if (AgentDiscussionPanel.currentPanel) {
      AgentDiscussionPanel.currentPanel._panel.reveal(column);
      return;
    }

    // Otherwise, create a new panel
    const panel = vscode.window.createWebviewPanel(
      "agentDiscussion",
      "Agent Discussion",
      column || vscode.ViewColumn.Two,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [extensionUri],
      },
    );

    AgentDiscussionPanel.currentPanel = new AgentDiscussionPanel(
      panel,
      extensionUri,
      wsClient,
    );
  }

  private constructor(
    panel: vscode.WebviewPanel,
    _extensionUri: vscode.Uri,
    wsClient: WebSocketClient,
  ) {
    this._panel = panel;
    this.wsClient = wsClient;

    // Set the webview's initial html content
    this._update();

    // Listen for when the panel is disposed
    this._panel.onDidDispose(() => this.dispose(), null, this._disposables);

    // Handle messages from the webview
    this._panel.webview.onDidReceiveMessage(
      (message) => {
        switch (message.command) {
          case "sendMessage":
            this._handleSendMessage(message.text);
            break;
          case "approveSuggestion":
            this._handleApproveSuggestion(message.messageId);
            break;
          case "rejectSuggestion":
            this._handleRejectSuggestion(message.messageId);
            break;
          case "closeDiscussion":
            this._handleCloseDiscussion();
            break;
        }
      },
      null,
      this._disposables,
    );

    // Listen for agent responses from backend
    this.wsClient.on("agent_discussion", (payload: any) => {
      this._handleAgentDiscussion(payload);
    });
  }

  /**
   * Start a new discussion
   */
  public startDiscussion(taskId: string, title: string) {
    this.currentDiscussion = {
      id: `discussion-${Date.now()}`,
      task_id: taskId,
      title,
      messages: [],
      status: "active",
      created_at: Date.now(),
    };

    // Save to history
    this.conversationHistory.set(
      this.currentDiscussion.id,
      this.currentDiscussion,
    );

    this._update();

    // Notify backend
    this.wsClient.send("start_discussion", {
      discussion_id: this.currentDiscussion.id,
      task_id: taskId,
      title,
    });
  }

  /**
   * Load a previous discussion from history
   */
  public loadDiscussion(discussionId: string) {
    const discussion = this.conversationHistory.get(discussionId);
    if (discussion) {
      this.currentDiscussion = discussion;
      this._update();
    }
  }

  /**
   * Get all conversation history
   */
  public getConversationHistory(): Discussion[] {
    return Array.from(this.conversationHistory.values());
  }

  /**
   * Clear conversation history
   */
  public clearHistory() {
    this.conversationHistory.clear();
  }

  /**
   * Handle sending a message
   */
  private async _handleSendMessage(text: string) {
    if (!this.currentDiscussion) {
      return;
    }

    // Add user message
    const userMessage: AgentMessage = {
      agent_id: "user",
      agent_name: "You",
      message: text,
      timestamp: Date.now(),
    };

    this.currentDiscussion.messages.push(userMessage);

    // Update history
    this.conversationHistory.set(
      this.currentDiscussion.id,
      this.currentDiscussion,
    );

    this._update();

    // Send to backend
    await this.wsClient.send("discussion_message", {
      discussion_id: this.currentDiscussion.id,
      message: text,
      timestamp: Date.now(),
    });
  }

  /**
   * Handle agent discussion from backend
   */
  private _handleAgentDiscussion(payload: any) {
    if (
      !this.currentDiscussion ||
      payload.discussion_id !== this.currentDiscussion.id
    ) {
      return;
    }

    // Add agent messages
    if (payload.agents && Array.isArray(payload.agents)) {
      for (const agent of payload.agents) {
        const agentMessage: AgentMessage = {
          agent_id: agent.agent_id,
          agent_name: agent.agent_name || agent.agent_id,
          message: agent.message,
          vote: agent.vote,
          timestamp: Date.now(),
          confidence: agent.confidence,
          reasoning: agent.reasoning,
        };

        this.currentDiscussion.messages.push(agentMessage);
      }

      // Update history
      this.conversationHistory.set(
        this.currentDiscussion.id,
        this.currentDiscussion,
      );

      this._update();
    }
  }

  /**
   * Handle approving a suggestion
   */
  private async _handleApproveSuggestion(messageId: string) {
    if (!this.currentDiscussion) {
      return;
    }

    await this.wsClient.send("approve_suggestion", {
      discussion_id: this.currentDiscussion.id,
      message_id: messageId,
      timestamp: Date.now(),
    });

    vscode.window.showInformationMessage("Suggestion approved");
  }

  /**
   * Handle rejecting a suggestion
   */
  private async _handleRejectSuggestion(messageId: string) {
    if (!this.currentDiscussion) {
      return;
    }

    await this.wsClient.send("reject_suggestion", {
      discussion_id: this.currentDiscussion.id,
      message_id: messageId,
      timestamp: Date.now(),
    });

    vscode.window.showInformationMessage("Suggestion rejected");
  }

  /**
   * Handle closing discussion
   */
  private _handleCloseDiscussion() {
    if (this.currentDiscussion) {
      this.currentDiscussion.status = "resolved";
      this.wsClient.send("close_discussion", {
        discussion_id: this.currentDiscussion.id,
        timestamp: Date.now(),
      });
    }

    this._panel.dispose();
  }

  /**
   * Update the webview content
   */
  private _update() {
    this._panel.title = this.currentDiscussion?.title || "Agent Discussion";
    this._panel.webview.html = this._getHtmlForWebview(this._panel.webview);
  }

  /**
   * Get HTML content for webview
   */
  private _getHtmlForWebview(_webview: vscode.Webview) {
    const messages = this.currentDiscussion?.messages || [];
    const isActive = this.currentDiscussion?.status === "active";

    const messagesHtml =
      messages.length === 0
        ? `<div class="empty-state">
                <div class="empty-state-icon">💬</div>
                <p>No messages yet. Start the conversation by asking a question or requesting agent input.</p>
            </div>`
        : messages
            .map(
              (msg, index) => `
                <div class="message ${msg.agent_id === "user" ? "user" : ""}">
                    <div class="message-header">
                        <div>
                            <span class="agent-icon">${msg.agent_id === "user" ? "👤" : "🤖"}</span>
                            <span class="agent-name">${this._escapeHtml(msg.agent_name)}</span>
                        </div>
                        <span class="timestamp">${new Date(msg.timestamp).toLocaleTimeString()}</span>
                    </div>
                    <div class="message-content">${this._escapeHtml(msg.message)}</div>
                    ${
                      msg.vote || msg.confidence || msg.reasoning
                        ? `
                        <div class="message-meta">
                            ${msg.vote ? `<span class="vote ${msg.vote}">${msg.vote.replace("_", " ").toUpperCase()}</span>` : ""}
                            ${msg.confidence ? `<span class="confidence">Confidence: ${Math.round(msg.confidence * 100)}%</span>` : ""}
                        </div>
                    `
                        : ""
                    }
                    ${msg.reasoning ? `<div class="message-content" style="font-style: italic; opacity: 0.8;">Reasoning: ${this._escapeHtml(msg.reasoning)}</div>` : ""}
                    ${
                      msg.agent_id !== "user" && isActive
                        ? `
                        <div class="message-actions">
                            <button class="approve" onclick="approveSuggestion('${msg.agent_id}-${index}')">✓ Approve</button>
                            <button class="reject" onclick="rejectSuggestion('${msg.agent_id}-${index}')">✗ Reject</button>
                        </div>
                    `
                        : ""
                    }
                </div>
            `,
            )
            .join("");

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent Discussion</title>
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
            padding: 20px;
            line-height: 1.6;
        }

        .header {
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid var(--vscode-panel-border);
        }

        .header h1 {
            font-size: 1.5em;
            margin-bottom: 10px;
        }

        .header .status {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
        }

        .status.active {
            background-color: var(--vscode-testing-iconPassed);
            color: var(--vscode-editor-background);
        }

        .status.resolved {
            background-color: var(--vscode-testing-iconQueued);
            color: var(--vscode-editor-background);
        }

        .messages-container {
            max-height: calc(100vh - 250px);
            overflow-y: auto;
            margin-bottom: 20px;
            padding-right: 10px;
        }

        .message {
            margin-bottom: 20px;
            padding: 15px;
            border-radius: 8px;
            background-color: var(--vscode-editor-inactiveSelectionBackground);
            border-left: 4px solid var(--vscode-textLink-foreground);
        }

        .message.user {
            border-left-color: var(--vscode-testing-iconPassed);
            background-color: var(--vscode-input-background);
        }

        .message-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }

        .agent-name {
            font-weight: 600;
            font-size: 1.1em;
        }

        .agent-icon {
            margin-right: 8px;
        }

        .timestamp {
            font-size: 0.85em;
            color: var(--vscode-descriptionForeground);
        }

        .message-content {
            margin: 10px 0;
            white-space: pre-wrap;
        }

        .message-meta {
            display: flex;
            gap: 15px;
            margin-top: 10px;
            font-size: 0.9em;
        }

        .vote {
            padding: 4px 10px;
            border-radius: 6px;
            font-weight: 600;
        }

        .vote.approve {
            background-color: var(--vscode-testing-iconPassed);
            color: var(--vscode-editor-background);
        }

        .vote.approve_with_changes {
            background-color: var(--vscode-testing-iconQueued);
            color: var(--vscode-editor-background);
        }

        .vote.reject {
            background-color: var(--vscode-testing-iconFailed);
            color: var(--vscode-editor-background);
        }

        .confidence {
            color: var(--vscode-descriptionForeground);
        }

        .message-actions {
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }

        button {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9em;
            font-weight: 600;
            transition: opacity 0.2s;
        }

        button:hover {
            opacity: 0.8;
        }

        button.approve {
            background-color: var(--vscode-testing-iconPassed);
            color: var(--vscode-editor-background);
        }

        button.reject {
            background-color: var(--vscode-testing-iconFailed);
            color: var(--vscode-editor-background);
        }

        .input-container {
            position: sticky;
            bottom: 0;
            background-color: var(--vscode-editor-background);
            padding: 15px 0;
            border-top: 1px solid var(--vscode-panel-border);
        }

        .input-row {
            display: flex;
            gap: 10px;
        }

        input[type="text"] {
            flex: 1;
            padding: 10px;
            border: 1px solid var(--vscode-input-border);
            background-color: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border-radius: 4px;
            font-size: 1em;
        }

        input[type="text"]:focus {
            outline: 1px solid var(--vscode-focusBorder);
        }

        button.send {
            background-color: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            padding: 10px 20px;
        }

        button.close {
            background-color: var(--vscode-button-secondaryBackground);
            color: var(--vscode-button-secondaryForeground);
            padding: 10px 20px;
        }

        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: var(--vscode-descriptionForeground);
        }

        .empty-state-icon {
            font-size: 3em;
            margin-bottom: 15px;
        }

        ::-webkit-scrollbar {
            width: 10px;
        }

        ::-webkit-scrollbar-track {
            background: var(--vscode-editor-background);
        }

        ::-webkit-scrollbar-thumb {
            background: var(--vscode-scrollbarSlider-background);
            border-radius: 5px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: var(--vscode-scrollbarSlider-hoverBackground);
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>${this._escapeHtml(this.currentDiscussion?.title || "Agent Discussion")}</h1>
        <span class="status ${this.currentDiscussion?.status || "active"}">${(this.currentDiscussion?.status || "active").toUpperCase()}</span>
    </div>

    <div class="messages-container" id="messagesContainer">
        ${messagesHtml}
    </div>

    ${
      isActive
        ? `
        <div class="input-container">
            <div class="input-row">
                <input type="text" id="messageInput" placeholder="Ask a question or provide feedback..." />
                <button class="send" onclick="sendMessage()">Send</button>
                <button class="close" onclick="closeDiscussion()">Close</button>
            </div>
        </div>
    `
        : ""
    }

    <script>
        const vscode = acquireVsCodeApi();

        function sendMessage() {
            const input = document.getElementById('messageInput');
            const text = input.value.trim();

            if (text) {
                vscode.postMessage({
                    command: 'sendMessage',
                    text: text
                });
                input.value = '';
            }
        }

        function approveSuggestion(messageId) {
            vscode.postMessage({
                command: 'approveSuggestion',
                messageId: messageId
            });
        }

        function rejectSuggestion(messageId) {
            vscode.postMessage({
                command: 'rejectSuggestion',
                messageId: messageId
            });
        }

        function closeDiscussion() {
            vscode.postMessage({
                command: 'closeDiscussion'
            });
        }

        // Handle Enter key in input
        document.getElementById('messageInput')?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });

        // Auto-scroll to bottom
        const container = document.getElementById('messagesContainer');
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    </script>
</body>
</html>`;
  }

  /**
   * Escape HTML to prevent XSS
   */
  private _escapeHtml(text: string): string {
    const map: { [key: string]: string } = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
    };
    return text.replace(/[&<>"']/g, (m) => map[m]);
  }

  /**
   * Dispose panel
   */
  public dispose() {
    AgentDiscussionPanel.currentPanel = undefined;

    // Clean up resources
    this._panel.dispose();

    while (this._disposables.length) {
      const disposable = this._disposables.pop();
      if (disposable) {
        disposable.dispose();
      }
    }
  }
}
