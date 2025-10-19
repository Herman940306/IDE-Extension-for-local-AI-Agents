/**
 * WebSocket Service for Real-time Communication
 * Project Creator: Herman Swanepoel
 */

const envUrlList =
    import.meta.env.VITE_BACKEND_WS_URLS?.toString() || import.meta.env.VITE_BACKEND_WS_URL?.toString();

const DEFAULT_ENDPOINTS = ['ws://127.0.0.1:8001/ws', 'ws://127.0.0.1:8000/ws'];

const parseEndpoints = (raw?: string): string[] => {
    if (!raw) {
        return [];
    }

    return raw
        .split(',')
        .map((entry) => entry.trim())
        .filter(Boolean);
};

const WS_ENDPOINTS = (() => {
    const parsed = parseEndpoints(envUrlList);
    return parsed.length > 0 ? parsed : DEFAULT_ENDPOINTS;
})();

export class WebSocketService {
    private ws: WebSocket | null = null;
    private clientId: string;
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private messageHandlers: Map<string, (payload: any) => void> = new Map();
    private connectionHandlers: Set<(connected: boolean) => void> = new Set();
    private shouldReconnect = true;
    private endpoints: string[] = WS_ENDPOINTS;
    private endpointIndex = 0;

    constructor(clientId?: string) {
        this.clientId = clientId || `web-${Date.now()}`;
    }

    connect(): Promise<void> {
        this.shouldReconnect = true;
        return new Promise((resolve, reject) => {
            this.createWebSocket(resolve, reject);
        });
    }

    subscribeConnectionChange(handler: (connected: boolean) => void) {
        this.connectionHandlers.add(handler);
    }

    unsubscribeConnectionChange(handler: (connected: boolean) => void) {
        this.connectionHandlers.delete(handler);
    }

    private notifyConnectionStatus(connected: boolean) {
        for (const handler of this.connectionHandlers) {
            try {
                handler(connected);
            } catch (error) {
                console.error('❌ Connection handler error:', error);
            }
        }
    }

    private createWebSocket(resolve?: () => void, reject?: (reason?: unknown) => void) {
        try {
            const baseUrl = this.endpoints[this.endpointIndex];
            console.log('🔌 Connecting to:', `${baseUrl}/${this.clientId}`);
            this.ws = new WebSocket(`${baseUrl}/${this.clientId}`);
        } catch (error) {
            console.error('❌ Failed to create WebSocket:', error);
            reject?.(error);
            return;
        }

        this.ws.onopen = () => {
            console.log('✅ Connected to backend');
            this.reconnectAttempts = 0;
            this.shouldReconnect = true;
            this.notifyConnectionStatus(true);
            resolve?.();
        };

        this.ws.onmessage = (event) => {
            console.log('📨 Received:', event.data);
            const message = JSON.parse(event.data);
            this.handleMessage(message);
        };

        this.ws.onerror = (error) => {
            console.error('❌ WebSocket error:', error);
            if (this.ws && this.ws.readyState !== WebSocket.OPEN) {
                // Close the socket to trigger onclose and retry on the next endpoint
                this.ws.close();
                reject?.(error);
            }
        };

        this.ws.onclose = (event) => {
            console.log('🔌 Disconnected from backend', event.code, event.reason);
            this.ws = null;
            this.notifyConnectionStatus(false);

            if (!this.shouldReconnect) {
                return;
            }

            if (event.code === 1006 || !event.wasClean) {
                this.advanceEndpoint();
            }

            this.attemptReconnect();
        };
    }

    private attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => {
                console.log(`🔄 Reconnect attempt ${this.reconnectAttempts}`);
                this.createWebSocket();
            }, 5000);
        }
    }

    private advanceEndpoint() {
        if (this.endpoints.length <= 1) {
            return;
        }

        this.endpointIndex = (this.endpointIndex + 1) % this.endpoints.length;
        console.log('🌐 Switching WebSocket endpoint to:', this.endpoints[this.endpointIndex]);
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
            console.log('📤 Sending to backend:', task);
            const messageType = task?.type || 'task_request';
            const payload = Object.prototype.hasOwnProperty.call(task, 'payload')
                ? task.payload
                : task;

            this.ws.send(
                JSON.stringify({
                    type: messageType,
                    payload
                })
            );
        } else {
            console.error('❌ WebSocket not connected');
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
        this.shouldReconnect = false;
        if (this.ws) {
            const ws = this.ws;
            this.ws = null;
            ws.close();
        }
        this.notifyConnectionStatus(false);
        this.reconnectAttempts = 0;
    }
}

export const wsService = new WebSocketService();
