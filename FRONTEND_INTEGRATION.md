# Frontend Integration Guide

**Project Creator:** Herman Swanepoel  
**Backend:** http://127.0.0.1:8001

---

## VS Code Extension Integration

### 1. Backend Endpoints

**Base URL:** `http://127.0.0.1:8001`

**Key Endpoints:**
- `GET /` - API info
- `GET /health` - Health check
- `GET /docs` - Swagger UI
- `WS /ws/{client_id}` - WebSocket connection

---

## WebSocket Integration

### Connect to Backend

```typescript
const ws = new WebSocket('ws://127.0.0.1:8001/ws/client-123');

ws.onopen = () => {
  console.log('Connected to backend');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};

ws.send(JSON.stringify({
  type: 'ping',
  payload: {}
}));
```

---

## Message Types

### Client → Server

**Ping:**
```json
{
  "type": "ping",
  "payload": {}
}
```

**Task Request:**
```json
{
  "type": "task_request",
  "payload": {
    "id": "task-123",
    "type": "code_generation",
    "context": {
      "language": "python",
      "description": "Create a function"
    }
  }
}
```

**Mode Change:**
```json
{
  "type": "mode_change",
  "payload": {
    "mode": "online"
  }
}
```

---

### Server → Client

**Connection Established:**
```json
{
  "type": "connection_established",
  "payload": {
    "client_id": "client-123",
    "message": "Connected",
    "timestamp": 1234567890
  }
}
```

**Pong:**
```json
{
  "type": "pong",
  "payload": {
    "timestamp": 1234567890
  }
}
```

**Agent Response:**
```json
{
  "type": "agent_response",
  "payload": {
    "task_id": "task-123",
    "agent_id": "mock_agent",
    "suggestions": [],
    "confidence": 0.0
  }
}
```

---

## VS Code Extension Setup

### 1. Install Dependencies

```bash
npm install ws
npm install @types/ws --save-dev
```

### 2. Create Backend Service

```typescript
// src/services/backendService.ts
import * as WebSocket from 'ws';

export class BackendService {
  private ws: WebSocket | null = null;
  private readonly url = 'ws://127.0.0.1:8001/ws';
  
  connect(clientId: string) {
    this.ws = new WebSocket(`${this.url}/${clientId}`);
    
    this.ws.on('open', () => {
      console.log('Backend connected');
    });
    
    this.ws.on('message', (data) => {
      const message = JSON.parse(data.toString());
      this.handleMessage(message);
    });
  }
  
  sendTask(task: any) {
    this.ws?.send(JSON.stringify({
      type: 'task_request',
      payload: task
    }));
  }
  
  private handleMessage(message: any) {
    // Handle different message types
  }
}
```

### 3. Use in Extension

```typescript
// src/extension.ts
import { BackendService } from './services/backendService';

export function activate(context: vscode.ExtensionContext) {
  const backend = new BackendService();
  backend.connect('vscode-client-' + Date.now());
  
  // Register commands
  context.subscriptions.push(
    vscode.commands.registerCommand('aura.generateCode', () => {
      backend.sendTask({
        id: 'task-' + Date.now(),
        type: 'code_generation',
        context: {
          language: 'python',
          description: 'Generate function'
        }
      });
    })
  );
}
```

---

## Testing

### 1. Test WebSocket Connection

```bash
# Install wscat
npm install -g wscat

# Connect
wscat -c ws://127.0.0.1:8001/ws/test-client

# Send ping
{"type":"ping","payload":{}}
```

### 2. Test Health Endpoint

```bash
curl http://127.0.0.1:8001/health
```

---

## Configuration

### Extension Settings

```json
{
  "aura.backend.url": "http://127.0.0.1:8001",
  "aura.backend.websocket": "ws://127.0.0.1:8001/ws",
  "aura.backend.timeout": 30000
}
```

---

## Error Handling

```typescript
ws.on('error', (error) => {
  vscode.window.showErrorMessage(`Backend error: ${error.message}`);
});

ws.on('close', () => {
  vscode.window.showWarningMessage('Backend disconnected');
  // Attempt reconnect
});
```

---

**Backend Status:** ✅ Running  
**WebSocket:** ✅ Ready  
**Integration:** Ready for VS Code extension
