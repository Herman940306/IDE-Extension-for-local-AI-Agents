/**
 * WebSocket Service for Real-time Communication
 * Project Creator: Herman Swanepoel
 */

const WS_BASE_URL = 'ws://127.0.0.1:8001/ws';

export class WebSocketService {
    private ws: WebSocket | null = null;
    private clientId: string;
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private messageHandlers: Map<string, (payload: any) => void> = new Map();

    constructor(clientId?: string) {
        this.clientId = clientId || `web-${Date.now()}`;
    }

    connect(): Promise<void> {
        return new Promise((resolve, reject) => {
            this.ws = new WebSocket(`${WS_BASE_URL}/${this.clientId}`);

            this.ws.onopen = () => {
                console.log('✅ Connected to backend');
                this.reconnectAttempts = 0;
                resolve();
            };

            this.ws.onmessage = (event) => {
                const message = JSON.parse(event.data);
                this.handleMessage(message);
            };

            this.ws.onerror = (error) => {
                console.error('❌ WebSocket error:', error);
                reject(error);
            };

            this.ws.onclose = () => {
                console.log('🔌 Disconnected from backend');
                this.attemptReconnect();
            };
        });
    }

    private attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => {
                console.log(`🔄 Reconnect attempt ${this.reconnectAttempts}`);
                this.connect();
            }, 5000);
        }
    }

    on(messageType: string, handler: (payload: any) => void) {
        this.messageHandlers.set(messageType, handler);
    }

    private handleMessage(message: any) {
        const handler = this.messageHandlers.get(message.type);
        if (handler) {
            handler(message.payload);
        }
    }

    sendTask(task: any) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'task_request',
                payload: task
            }));
        }
    }

    ping() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'ping',
                payload: {}
            }));
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
    }
}

export const wsService = new WebSocketService();
