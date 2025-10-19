/**
 * WebSocket Service for Real-time Communication
 * Project Creator: Herman Swanepoel
 */

import type {
    ClientMessage,
    ClientMessageMap,
    ClientMessageType,
    ServerMessage,
    ServerMessageMap,
    ServerMessageType
} from '../types/websocket';

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

export type ConnectionState = 'connecting' | 'connected' | 'disconnected';

export class WebSocketService {
    private ws: WebSocket | null = null;
    private clientId: string;
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private messageHandlers: Map<ServerMessageType, Set<(payload: ServerMessageMap[ServerMessageType]) => void>> =
        new Map();
    private connectionHandlers: Set<(state: ConnectionState) => void> = new Set();
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

    subscribeConnectionChange(handler: (state: ConnectionState) => void) {
        this.connectionHandlers.add(handler);
    }

    unsubscribeConnectionChange(handler: (state: ConnectionState) => void) {
        this.connectionHandlers.delete(handler);
    }

    private notifyConnectionStatus(state: ConnectionState) {
        for (const handler of this.connectionHandlers) {
            try {
                handler(state);
            } catch (error) {
                console.error('❌ Connection handler error:', error);
            }
        }
    }

    private createWebSocket(resolve?: () => void, reject?: (reason?: unknown) => void) {
        this.notifyConnectionStatus('connecting');

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
            this.notifyConnectionStatus('connected');
            resolve?.();
        };

        this.ws.onmessage = (event) => {
            console.log('📨 Received:', event.data);
            try {
                const message = JSON.parse(event.data);
                this.handleMessage(message);
            } catch (error) {
                console.error('❌ Failed to parse WebSocket message', error);
            }
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
            this.notifyConnectionStatus('disconnected');

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

    on<K extends ServerMessageType>(messageType: K, handler: (payload: ServerMessageMap[K]) => void) {
        if (!this.messageHandlers.has(messageType)) {
            this.messageHandlers.set(messageType, new Set());
        }
        this.messageHandlers.get(messageType)!.add(handler as never);
    }

    off<K extends ServerMessageType>(messageType: K, handler: (payload: ServerMessageMap[K]) => void) {
        this.messageHandlers.get(messageType)?.delete(handler as never);
    }

    private handleMessage(raw: unknown) {
        if (!raw || typeof raw !== 'object' || !('type' in raw)) {
            console.warn('⚠️ Received malformed WebSocket message', raw);
            return;
        }

        const { type, payload } = raw as ServerMessage;

        const handlers = this.messageHandlers.get(type);
        if (!handlers || handlers.size === 0) {
            console.warn('⚠️ No handler registered for message type', type);
            return;
        }

        for (const handler of handlers) {
            try {
                handler(payload as never);
            } catch (error) {
                console.error(`❌ Handler error for message type ${type}`, error);
            }
        }
    }

    private sendMessage<K extends ClientMessageType>(message: ClientMessage<K>) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            console.error('❌ WebSocket not connected');
            return;
        }

        console.log('📤 Sending to backend:', message);
        this.ws.send(JSON.stringify(message));
    }

    sendTask(payload: ClientMessageMap['task_request']) {
        this.sendMessage({ type: 'task_request', payload });
    }

    ping() {
        this.sendMessage({ type: 'ping', payload: {} });
    }

    changeMode(newMode: string) {
        this.sendMessage({ type: 'mode_change', payload: { mode: newMode } });
    }

    disconnect() {
        this.shouldReconnect = false;
        if (this.ws) {
            const ws = this.ws;
            this.ws = null;
            ws.close();
        }
        this.notifyConnectionStatus('disconnected');
        this.reconnectAttempts = 0;
    }
}

export const wsService = new WebSocketService();
