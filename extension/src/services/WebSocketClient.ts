/**
 * WebSocket Client with auto-reconnection
 * Project Creator: Herman Swanepoel
 */

import * as vscode from "vscode";
import WebSocket from "ws";

export interface Message {
  type: string;
  payload: any;
}

export interface WebSocketConfig {
  url: string;
  clientId: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private config: WebSocketConfig;
  private reconnectAttempts = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private messageQueue: Message[] = [];
  private isConnected = false;
  private statusBarItem: vscode.StatusBarItem;
  private messageHandlers: Map<string, (payload: any) => void> = new Map();

  constructor(config: WebSocketConfig) {
    this.config = {
      reconnectInterval: 3000,
      maxReconnectAttempts: 10,
      ...config,
    };

    this.statusBarItem = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Left,
      100,
    );
    this.updateStatusBar("disconnected");
    this.statusBarItem.show();
  }

  public async connect(): Promise<void> {
    if (this.ws && this.isConnected) {
      console.log("Already connected");
      return;
    }

    try {
      this.updateStatusBar("connecting");
      const wsUrl = `${this.config.url}/ws/${this.config.clientId}`;

      this.ws = new WebSocket(wsUrl);

      this.ws.on("open", () => this.handleOpen());
      this.ws.on("message", (data: WebSocket.Data) => this.handleMessage(data));
      this.ws.on("error", (error: Error) => this.handleError(error));
      this.ws.on("close", () => this.handleClose());
    } catch (error) {
      console.error("Connection error:", error);
      this.scheduleReconnect();
    }
  }

  public disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.updateStatusBar("disconnected");
  }

  public async send(type: string, payload: any): Promise<void> {
    const message: Message = { type, payload };

    if (this.isConnected && this.ws) {
      try {
        this.ws.send(JSON.stringify(message));
      } catch (error) {
        console.error("Error sending message:", error);
        this.messageQueue.push(message);
      }
    } else {
      this.messageQueue.push(message);
      console.log("Message queued (not connected)");
    }
  }

  public async sendWithResponse(
    type: string,
    payload: any,
    timeout: number = 5000,
  ): Promise<any> {
    return new Promise((resolve, reject) => {
      if (!this.isConnected || !this.ws) {
        reject(new Error("Not connected to backend"));
        return;
      }

      const requestId = `${type}_${Date.now()}_${Math.random()}`;
      const message = {
        type,
        payload: {
          ...payload,
          request_id: requestId,
        },
      };

      // Set up response handler
      const responseHandler = (responsePayload: any) => {
        if (responsePayload.request_id === requestId) {
          clearTimeout(timeoutTimer);
          this.off(`${type}_response`);
          resolve(responsePayload);
        }
      };

      this.on(`${type}_response`, responseHandler);

      // Set timeout
      const timeoutTimer = setTimeout(() => {
        this.off(`${type}_response`);
        reject(new Error(`Request timeout after ${timeout}ms`));
      }, timeout);

      // Send request
      try {
        this.ws.send(JSON.stringify(message));
      } catch (error) {
        clearTimeout(timeoutTimer);
        this.off(`${type}_response`);
        reject(error);
      }
    });
  }

  public on(messageType: string, handler: (payload: unknown) => void): void {
    this.messageHandlers.set(messageType, handler);
  }

  public off(messageType: string): void {
    this.messageHandlers.delete(messageType);
  }

  public getStatus(): boolean {
    return this.isConnected;
  }

  public isConnectedToBackend(): boolean {
    return this.isConnected;
  }

  private handleOpen(): void {
    console.log("WebSocket connected");
    this.isConnected = true;
    this.reconnectAttempts = 0;
    this.updateStatusBar("connected");

    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      if (message) {
        this.send(message.type, message.payload);
      }
    }

    vscode.window.showInformationMessage(
      "✅ Connected to Enterprise AI Agents Backend",
    );
  }

  private handleMessage(data: WebSocket.Data): void {
    try {
      const message: Message = JSON.parse(data.toString());
      console.log("Received message:", message.type);

      const handler = this.messageHandlers.get(message.type);
      if (handler) {
        handler(message.payload);
      }

      if (message.type === "connection_established") {
        console.log("Connection established:", message.payload);
      } else if (message.type === "error") {
        vscode.window.showErrorMessage(
          `Backend Error: ${message.payload.message}`,
        );
      }
    } catch (error) {
      console.error("Error parsing message:", error);
    }
  }

  private handleError(error: Error): void {
    console.error("WebSocket error:", error);
    this.updateStatusBar("error");
  }

  private handleClose(): void {
    console.log("WebSocket closed");
    this.isConnected = false;
    this.updateStatusBar("disconnected");
    this.scheduleReconnect();
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= (this.config.maxReconnectAttempts || 10)) {
      vscode.window.showErrorMessage(
        "❌ Failed to connect to Enterprise AI Agents Backend after multiple attempts",
      );
      this.updateStatusBar("failed");
      return;
    }

    const delay = Math.min(
      (this.config.reconnectInterval || 3000) *
        Math.pow(2, this.reconnectAttempts),
      30000,
    );

    this.reconnectAttempts++;
    console.log(
      `Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`,
    );

    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }

  private updateStatusBar(
    status: "connected" | "connecting" | "disconnected" | "error" | "failed",
  ): void {
    const statusIcons = {
      connected: "$(check)",
      connecting: "$(sync~spin)",
      disconnected: "$(circle-slash)",
      error: "$(warning)",
      failed: "$(error)",
    };

    const statusColors = {
      connected: undefined,
      connecting: new vscode.ThemeColor("statusBarItem.warningBackground"),
      disconnected: new vscode.ThemeColor("statusBarItem.errorBackground"),
      error: new vscode.ThemeColor("statusBarItem.errorBackground"),
      failed: new vscode.ThemeColor("statusBarItem.errorBackground"),
    };

    this.statusBarItem.text = `${statusIcons[status]} AI Agents: ${status}`;
    this.statusBarItem.backgroundColor = statusColors[status];
    this.statusBarItem.tooltip = `Enterprise AI Agents Backend: ${status}`;
  }

  public dispose(): void {
    this.disconnect();
    this.statusBarItem.dispose();
  }
}
