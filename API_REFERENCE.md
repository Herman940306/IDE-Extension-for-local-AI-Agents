# API Reference

**Project Creator:** Herman Swanepoel  
**Base URL:** http://127.0.0.1:8001  
**Version:** 1.0.0

---

## REST Endpoints

### GET /

**Description:** Get API information

**Response:**
```json
{
  "service": "Enterprise AI Agents API",
  "version": "1.0.0",
  "creator": "Herman Swanepoel",
  "status": "running",
  "docs": "/docs",
  "redoc": "/redoc",
  "health": "/health"
}
```

**Status Codes:**
- `200` - Success

---

### GET /health

**Description:** Health check with component status

**Response:**
```json
{
  "status": "healthy",
  "service": "backend",
  "connections": 0,
  "components": {
    "redis": "disabled",
    "cache": {
      "enabled": false,
      "hits": 0,
      "misses": 0,
      "hit_rate": 0.0
    }
  }
}
```

**Status Values:**
- `healthy` - All systems operational
- `degraded` - Partial functionality
- `unhealthy` - Critical failure

**Status Codes:**
- `200` - Success

---

### GET /docs

**Description:** Interactive API documentation (Swagger UI)

**Response:** HTML page

---

### GET /redoc

**Description:** API documentation (ReDoc)

**Response:** HTML page

---

## WebSocket Endpoint

### WS /ws/{client_id}

**Description:** Real-time bidirectional communication

**Parameters:**
- `client_id` (path) - Unique client identifier

**Connection:**
```javascript
const ws = new WebSocket('ws://127.0.0.1:8001/ws/client-123');
```

---

## WebSocket Messages

### Client → Server

#### Ping

**Purpose:** Keep-alive / latency check

```json
{
  "type": "ping",
  "payload": {}
}
```

**Response:** Pong message

---

#### Task Request

**Purpose:** Request AI agent task execution

```json
{
  "type": "task_request",
  "payload": {
    "id": "task-123",
    "type": "code_generation",
    "context": {
      "language": "python",
      "file_path": "main.py",
      "description": "Create a function"
    },
    "priority": "high"
  }
}
```

**Response:** Task acknowledged + Agent response

---

#### Mode Change

**Purpose:** Switch between online/offline modes

```json
{
  "type": "mode_change",
  "payload": {
    "mode": "online"
  }
}
```

**Modes:**
- `online` - Full AI features
- `offline` - Local only

**Response:** Mode changed confirmation

---

### Server → Client

#### Connection Established

**Sent:** On successful WebSocket connection

```json
{
  "type": "connection_established",
  "payload": {
    "client_id": "client-123",
    "message": "Connected to Enterprise AI Agents Backend",
    "timestamp": 1697234567.89
  }
}
```

---

#### Pong

**Sent:** Response to ping

```json
{
  "type": "pong",
  "payload": {
    "timestamp": 1697234567.89
  }
}
```

---

#### Task Acknowledged

**Sent:** Task received and queued

```json
{
  "type": "task_acknowledged",
  "payload": {
    "task_id": "task-123",
    "status": "received",
    "message": "Task received and queued for processing"
  }
}
```

---

#### Agent Response

**Sent:** AI agent completed task

```json
{
  "type": "agent_response",
  "payload": {
    "task_id": "task-123",
    "agent_id": "mock_agent",
    "agent_name": "Mock Agent",
    "suggestions": [],
    "confidence": 0.0,
    "reasoning": "Agent orchestration not yet implemented"
  }
}
```

---

#### Mode Changed

**Sent:** Mode change confirmed

```json
{
  "type": "mode_changed",
  "payload": {
    "mode": "online",
    "message": "Mode changed to online",
    "timestamp": 1697234567.89
  }
}
```

---

#### Error

**Sent:** Error occurred

```json
{
  "type": "error",
  "payload": {
    "message": "Invalid message format",
    "details": "Validation error details"
  }
}
```

---

## Error Responses

### Standard Error Format

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "correlation_id": "abc-123-def-456",
    "timestamp": "2025-10-13T22:11:12Z"
  }
}
```

### Error Codes

- `INTERNAL_ERROR` - Unexpected server error
- `VALIDATION_ERROR` - Invalid request data
- `RATE_LIMIT_EXCEEDED` - Too many requests
- `CIRCUIT_BREAKER_OPEN` - Service unavailable

### HTTP Status Codes

- `200` - Success
- `400` - Bad Request
- `404` - Not Found
- `429` - Too Many Requests
- `500` - Internal Server Error
- `503` - Service Unavailable

---

## Headers

### Request Headers

**Optional:**
- `X-Correlation-ID` - Request tracking ID

### Response Headers

**Always:**
- `X-Correlation-ID` - Request tracking ID

**Rate Limiting:**
- `Retry-After` - Seconds until retry allowed

---

## Rate Limiting

**Default Limits:**
- 60 requests per minute per client
- Burst size: 10 requests

**Headers:**
- `X-RateLimit-Limit` - Max requests
- `X-RateLimit-Remaining` - Remaining requests
- `X-RateLimit-Reset` - Reset timestamp

---

## Examples

### cURL

**Health Check:**
```bash
curl http://127.0.0.1:8001/health
```

**API Info:**
```bash
curl http://127.0.0.1:8001/
```

### Python

**Health Check:**
```python
import requests

response = requests.get('http://127.0.0.1:8001/health')
print(response.json())
```

**WebSocket:**
```python
import asyncio
import websockets
import json

async def connect():
    uri = "ws://127.0.0.1:8001/ws/python-client"
    async with websockets.connect(uri) as ws:
        # Send ping
        await ws.send(json.dumps({
            "type": "ping",
            "payload": {}
        }))
        
        # Receive pong
        response = await ws.recv()
        print(json.loads(response))

asyncio.run(connect())
```

### JavaScript

**WebSocket:**
```javascript
const ws = new WebSocket('ws://127.0.0.1:8001/ws/js-client');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'ping',
    payload: {}
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};
```

---

**Status:** ✅ API Active  
**Documentation:** http://127.0.0.1:8001/docs
