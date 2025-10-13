/**
 * Backend Service - WebSocket Communication
 * Project Creator: Herman Swanepoel
 */

import * as vscode from 'vscode';
import * as WebSocket from 'ws';

export class BackendService {
    private ws: WebSocket | null = null;
    private readonly baseUrl = 'ws://127.0.0.1:8001/ws';
    private clientId: string;
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;

    constructor() {
        this.clientId = `vscode-${Date.now()}`;
    }

    connect(): Promise<void> {
        return new Promise((resolve, reject) => {
            this.ws = new WebSocket(`${this.baseUrl}/${this.clientId}`);

            this.ws.on('open', () => {
                console.log('Connected to backend');
                this.reconnectAttempts = 0;
                resolve();
            });

            this.ws.on('message', (data) => {
                const message = JSON.parse(data.toString());
                this.handleMessage(message);
            });

            this.ws.on('error', (error) => {
                console.error('WebSocket error:', error);
                reject(error);
            });

            this.ws.on('close', () => {
                console.log('Disconnected from backend');
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
            this.ws.send(JSON.stringify({
                type: 'task_request',
                payload: task
            }));
        } else {
            vscode.window.showErrorMessage('Not connected to backend');
        }
    }

    private handleMessage(message: any) {
        switch (message.type) {
            case 'connection_established':
                console.log('Connection established:', message.payload);
                break;
            case 'task_acknowledged':
                vscode.window.showInformationMessage('Task received by backend');
                break;
            case 'agent_response':
                this.handleAgentResponse(message.payload);
                break;
            case 'error':
                vscode.window.showErrorMessage(message.payload.message);
                break;
        }
    }

    private handleAgentResponse(payload: any) {
        vscode.window.showInformationMessage(`Agent response: ${payload.reasoning}`);
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
    }
}
