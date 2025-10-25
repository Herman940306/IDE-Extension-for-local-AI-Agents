/**
 * Backend Service - WebSocket Communication
 * Project Creator: Herman Swanepoel
 */

import * as vscode from "vscode";
import WebSocket from "ws";

export class BackendService {
  private ws: WebSocket | null = null;
  private readonly baseUrl = "ws://127.0.0.1:8001/ws";
  private clientId: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private outputChannel: vscode.OutputChannel;

  constructor() {
    this.clientId = `vscode-${Date.now()}`;
    this.outputChannel = vscode.window.createOutputChannel("Aura AI Response");
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      const socket = new WebSocket(`${this.baseUrl}/${this.clientId}`);
      this.ws = socket;

      socket.on("open", () => {
        console.log("Connected to backend");
        this.reconnectAttempts = 0;
        resolve();
      });

      socket.on("message", (data) => {
        try {
          const message = JSON.parse(data.toString());
          this.handleMessage(message);
        } catch (error) {
          console.error("Failed to parse backend message", error);
        }
      });

      socket.on("error", (error) => {
        console.error("WebSocket error:", error);
        reject(error);
      });

      socket.on("close", () => {
        console.log("Disconnected from backend");
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
