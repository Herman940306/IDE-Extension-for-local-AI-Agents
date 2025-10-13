# VS Code Extension Development Guide

**Project Creator:** Herman Swanepoel  
**Backend:** http://127.0.0.1:8001

---

## Quick Start

### 1. Create Extension

```bash
npm install -g yo generator-code
yo code
```

**Select:**
- New Extension (TypeScript)
- Name: aura-ai-assistant
- Identifier: aura-ai
- Description: Enterprise AI Agents for VS Code

---

### 2. Install Dependencies

```bash
cd aura-ai-assistant
npm install ws
npm install @types/ws --save-dev
npm install axios
```

---

### 3. Project Structure

```
aura-ai-assistant/
├── src/
│   ├── extension.ts          # Main entry point
│   ├── services/
│   │   ├── backendService.ts # WebSocket connection
│   │   └── taskService.ts    # Task management
│   ├── commands/
│   │   ├── generateCode.ts   # Code generation
│   │   └── refactorCode.ts   # Code refactoring
│   └── ui/
│       ├── statusBar.ts      # Status bar item
│       └── webview.ts        # Webview panel
├── package.json
└── tsconfig.json
```

---

## Implementation

### Backend Service

```typescript
// src/services/backendService.ts
import * as WebSocket from 'ws';
import * as vscode from 'vscode';

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
                vscode.window.showInformationMessage('✅ Connected to AI Backend');
                resolve();
            });

            this.ws.on('message', (data) => {
                const message = JSON.parse(data.toString());
                this.handleMessage(message);
            });

            this.ws.on('error', (error) => {
                console.error('WebSocket error:', error);
                vscode.window.showErrorMessage(`Backend error: ${error.message}`);
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
        } else {
            vscode.window.showWarningMessage('❌ Backend disconnected');
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
            case 'pong':
                console.log('Pong received');
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
        // Handle AI agent response
        console.log('Agent response:', payload);
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
    }
}
```

---

### Extension Activation

```typescript
// src/extension.ts
import * as vscode from 'vscode';
import { BackendService } from './services/backendService';

let backendService: BackendService;

export async function activate(context: vscode.ExtensionContext) {
    console.log('Aura AI Assistant activated');

    // Initialize backend service
    backendService = new BackendService();
    
    try {
        await backendService.connect();
    } catch (error) {
        vscode.window.showErrorMessage('Failed to connect to backend');
    }

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('aura.generateCode', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showWarningMessage('No active editor');
                return;
            }

            const description = await vscode.window.showInputBox({
                prompt: 'Describe the code you want to generate',
                placeHolder: 'e.g., Create a function to sort an array'
            });

            if (description) {
                backendService.sendTask({
                    id: `task-${Date.now()}`,
                    type: 'code_generation',
                    context: {
                        language: editor.document.languageId,
                        file_path: editor.document.fileName,
                        description: description
                    }
                });
            }
        })
    );

    // Status bar
    const statusBarItem = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Right,
        100
    );
    statusBarItem.text = '$(zap) Aura AI';
    statusBarItem.tooltip = 'Aura AI Assistant';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);
}

export function deactivate() {
    if (backendService) {
        backendService.disconnect();
    }
}
```

---

### Package Configuration

```json
// package.json
{
  "name": "aura-ai-assistant",
  "displayName": "Aura AI Assistant",
  "description": "Enterprise AI Agents for VS Code",
  "version": "1.0.0",
  "engines": {
    "vscode": "^1.80.0"
  },
  "categories": [
    "Programming Languages",
    "Machine Learning",
    "Other"
  ],
  "activationEvents": [
    "onStartupFinished"
  ],
  "main": "./out/extension.js",
  "contributes": {
    "commands": [
      {
        "command": "aura.generateCode",
        "title": "Aura: Generate Code"
      },
      {
        "command": "aura.refactorCode",
        "title": "Aura: Refactor Code"
      }
    ],
    "configuration": {
      "title": "Aura AI",
      "properties": {
        "aura.backend.url": {
          "type": "string",
          "default": "http://127.0.0.1:8001",
          "description": "Backend API URL"
        },
        "aura.backend.websocket": {
          "type": "string",
          "default": "ws://127.0.0.1:8001/ws",
          "description": "Backend WebSocket URL"
        }
      }
    }
  },
  "scripts": {
    "vscode:prepublish": "npm run compile",
    "compile": "tsc -p ./",
    "watch": "tsc -watch -p ./",
    "pretest": "npm run compile"
  },
  "devDependencies": {
    "@types/vscode": "^1.80.0",
    "@types/node": "^18.x",
    "@types/ws": "^8.5.0",
    "typescript": "^5.0.0"
  },
  "dependencies": {
    "ws": "^8.14.0",
    "axios": "^1.5.0"
  }
}
```

---

## Development Workflow

### 1. Start Backend

```bash
cd backend
python run.py
```

### 2. Start Extension Development

```bash
cd aura-ai-assistant
npm install
npm run watch
```

### 3. Debug Extension

- Press `F5` in VS Code
- New VS Code window opens
- Test commands in Command Palette

---

## Testing

### Manual Testing

1. Open Command Palette (`Ctrl+Shift+P`)
2. Run `Aura: Generate Code`
3. Enter description
4. Check backend logs for task

### Automated Testing

```typescript
// src/test/extension.test.ts
import * as assert from 'assert';
import * as vscode from 'vscode';

suite('Extension Test Suite', () => {
    test('Extension should be present', () => {
        assert.ok(vscode.extensions.getExtension('aura-ai'));
    });

    test('Commands should be registered', async () => {
        const commands = await vscode.commands.getCommands();
        assert.ok(commands.includes('aura.generateCode'));
    });
});
```

---

## Publishing

### 1. Package Extension

```bash
npm install -g @vscode/vsce
vsce package
```

### 2. Publish to Marketplace

```bash
vsce publish
```

---

## Next Steps

1. ✅ Backend running
2. ✅ WebSocket protocol defined
3. ✅ Extension structure created
4. ⏳ Implement AI features
5. ⏳ Add UI components
6. ⏳ Test & publish

---

**Backend:** ✅ Running  
**API:** ✅ Documented  
**Extension:** Ready to build
