/**
 * Main Application Component
 * Project Creator: Herman Swanepoel
 */

import { useEffect, useState } from 'react';
import { apiService } from './services/api';
import { wsService } from './services/websocket';

function App() {
    const [health, setHealth] = useState<any>(null);
    const [connected, setConnected] = useState(false);
    const [messages, setMessages] = useState<any[]>([]);

    useEffect(() => {
        // Check health
        apiService.getHealth().then(setHealth);

        // Connect WebSocket
        wsService.connect().then(() => {
            setConnected(true);

            // Setup message handlers
            wsService.on('connection_established', (payload) => {
                console.log('Connection established:', payload);
                addMessage('Connected', payload);
            });

            wsService.on('pong', (payload) => {
                addMessage('Pong', payload);
            });

            wsService.on('agent_response', (payload) => {
                addMessage('Agent Response', payload);
            });
        });

        return () => {
            wsService.disconnect();
        };
    }, []);

    const addMessage = (type: string, payload: any) => {
        setMessages(prev => [...prev, { type, payload, timestamp: Date.now() }]);
    };

    const handlePing = () => {
        wsService.ping();
    };

    const handleSendTask = () => {
        wsService.sendTask({
            id: `task-${Date.now()}`,
            type: 'code_generation',
            context: {
                language: 'python',
                description: 'Test task from frontend'
            }
        });
    };

    return (
        <div style={{ padding: '20px', fontFamily: 'Arial' }}>
            <h1>🚀 Enterprise AI Agents Frontend</h1>
            <p>Project Creator: Herman Swanepoel</p>

            <div style={{ marginTop: '20px' }}>
                <h2>Backend Status</h2>
                {health && (
                    <pre style={{ background: '#f5f5f5', padding: '10px' }}>
                        {JSON.stringify(health, null, 2)}
                    </pre>
                )}
            </div>

            <div style={{ marginTop: '20px' }}>
                <h2>WebSocket Connection</h2>
                <p>Status: {connected ? '✅ Connected' : '❌ Disconnected'}</p>
                <button onClick={handlePing} disabled={!connected}>
                    Send Ping
                </button>
                <button onClick={handleSendTask} disabled={!connected} style={{ marginLeft: '10px' }}>
                    Send Test Task
                </button>
            </div>

            <div style={{ marginTop: '20px' }}>
                <h2>Messages</h2>
                <div style={{ maxHeight: '300px', overflow: 'auto', background: '#f5f5f5', padding: '10px' }}>
                    {messages.map((msg, i) => (
                        <div key={i} style={{ marginBottom: '10px', borderBottom: '1px solid #ddd', paddingBottom: '10px' }}>
                            <strong>{msg.type}</strong>
                            <pre style={{ fontSize: '12px' }}>{JSON.stringify(msg.payload, null, 2)}</pre>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

export default App;
