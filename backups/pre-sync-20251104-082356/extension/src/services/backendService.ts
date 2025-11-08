/**
 * Backend Service - WebSocket Communication
 * Project Creator: Herman Swanepoel
 */

import * as vscode from "vscode";
import WebSocket from "ws";

export class BackendService {
  private ws: WebSocket | null = null;
  private baseUrl: string;
  private clientId: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private outputChannel: vscode.OutputChannel;

  constructor() {
    // Get backend WebSocket URL from VS Code configuration
    const config = vscode.workspace.getConfiguration("aura");
    this.baseUrl = config.get<string>("backend.websocket", "ws://127.0.0.1:8001/ws");

    this.clientId = `vscode-${Date.now()}`;
    this.outputChannel = vscode.window.createOutputChannel("Aura AI Response");

    console.log(`[BackendService] Configured WebSocket URL: ${this.baseUrl}`);
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      console.log(`[BackendService] Attempting to connect to ${this.baseUrl}/${this.clientId}`);

      const socket = new WebSocket(`${this.baseUrl}/${this.clientId}`);
      this.ws = socket;

      const connectionTimeout = setTimeout(() => {
        socket.terminate();
        const error = new Error(`Connection timeout after 10 seconds. Is the backend running at ${this.baseUrl}?`);
        console.error("[BackendService]", error.message);
        reject(error);
      }, 10000);

      socket.on("open", () => {
        clearTimeout(connectionTimeout);
        console.log("[BackendService] ✅ Connected to backend successfully");
        this.reconnectAttempts = 0;
        resolve();
      });

      socket.on("message", (data) => {
        try {
          const message = JSON.parse(data.toString());
          this.handleMessage(message);
        } catch (error) {
          console.error("[BackendService] Failed to parse backend message", error);
        }
      });

      socket.on("error", (error) => {
        clearTimeout(connectionTimeout);
        console.error("[BackendService] ❌ WebSocket error:", error);
        vscode.window.showErrorMessage(
          `Failed to connect to Aura AI backend at ${this.baseUrl}. Please ensure:\n1. Backend is running (uvicorn)\n2. Ollama service is running\n3. WebSocket URL is correct in settings`
        );
        reject(error);
      });

      socket.on("close", () => {
        clearTimeout(connectionTimeout);
        console.log("[BackendService] 🔌 Disconnected from backend");
        this.attemptReconnect();
      });
    });
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        console.log(`Reconnect attempt ${this.reconnectAttempts}`);
        this.connect();
      }, 5000);
    }
  }

  sendTask(task: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          type: "task_request",
          payload: task,
        }),
      );
    } else {
      vscode.window.showErrorMessage("Not connected to backend");
    }
  }

  private handleMessage(message: any) {
    switch (message.type) {
      case "connection_established":
        console.log("Connection established:", message.payload);
        break;
      case "task_acknowledged":
        vscode.window.showInformationMessage("Task received by backend");
        break;
      case "agent_response":
        this.handleAgentResponse(message.payload);
        break;
      case "error":
        vscode.window.showErrorMessage(message.payload.message);
        break;
    }
  }

  private handleAgentResponse(payload: any) {
    console.log("Handling agent response:", JSON.stringify(payload, null, 2));

    // payload is TaskSessionResult
    const summary = payload.summary || payload.reasoning || "Task completed";

    // Extract suggestions from responses
    let suggestionText = "";
    if (payload.responses && payload.responses.length > 0) {
      const agentResponse = payload.responses[0].response;

      if (agentResponse.suggestions && agentResponse.suggestions.length > 0) {
        const suggestions = agentResponse.suggestions
          .map((s: any, i: number) => {
            const code = s.code || "";
            const desc = s.description || "";
            return `${i + 1}. ${desc}\n${code ? "```\n" + code + "\n```" : ""}`;
          })
          .join("\n\n");

        suggestionText = suggestions;
      }

      // Show detailed reasoning if available
      if (agentResponse.reasoning) {
        suggestionText += `\n\n**Reasoning:** ${agentResponse.reasoning}`;
      }
    }

    // Clear and populate output channel
    this.outputChannel.clear();
    this.outputChannel.appendLine("=".repeat(80));
    this.outputChannel.appendLine(`Task: ${payload.task_id || 'unknown'}`);
    this.outputChannel.appendLine(`Status: ${payload.status || 'completed'}`);
    this.outputChannel.appendLine("=".repeat(80));
    this.outputChannel.appendLine("");
    this.outputChannel.appendLine(summary);
    this.outputChannel.appendLine("");

    if (suggestionText) {
      this.outputChannel.appendLine("SUGGESTIONS:");
      this.outputChannel.appendLine("-".repeat(80));
      this.outputChannel.appendLine(suggestionText);
    } else {
      this.outputChannel.appendLine("(No specific suggestions generated)");
    }

    this.outputChannel.appendLine("");
    this.outputChannel.appendLine("=".repeat(80));

    // Show the output channel
    this.outputChannel.show(true);

    console.log("Output channel should be visible now");

    // Also show a notification
    vscode.window.showInformationMessage(
      "✅ Task completed! Check 'Aura AI Response' output.",
    );
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
    }
  }
}
