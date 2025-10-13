/**
 * AuraIA - AI Assistant Interface
 * Project Creator: Herman Swanepoel
 */

import { useEffect, useState } from 'react';
import './App.css';
import { wsService } from './services/websocket';

interface Message {
    role: 'user' | 'assistant';
    content: string;
    timestamp: number;
}

function App() {
    const [connected, setConnected] = useState(false);
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    useEffect(() => {
        wsService.connect()
            .then(() => {
                setConnected(true);
                wsService.on('agent_response', (payload) => {
                    setMessages(prev => [...prev, {
                        role: 'assistant',
                        content: payload.reasoning || 'Response received',
                        timestamp: Date.now()
                    }]);
                    setIsLoading(false);
                });
            })
            .catch(() => setConnected(false));

        return () => wsService.disconnect();
    }, []);

    const handleSend = () => {
        if (!input.trim() || !connected) return;

        setMessages(prev => [...prev, {
            role: 'user',
            content: input,
            timestamp: Date.now()
        }]);

        wsService.sendTask({
            id: `task-${Date.now()}`,
            type: 'code_generation',
            context: {
                description: input
            }
        });

        setInput('');
        setIsLoading(true);
    };

    return (
        <div className="app">
            <aside className="sidebar">
                <div className="sidebar-header">
                    <button className="new-chat-btn">
                        <span>+</span> New chat
                    </button>
                </div>
                <div className="chat-history">
                    {messages.length > 0 && (
                        <div className="chat-item active">
                            {messages[0]?.content.substring(0, 30)}...
                        </div>
                    )}
                </div>
                <div className="sidebar-footer">
                    <div className="user-info">
                        <div className="avatar">HS</div>
                        <span>Herman Swanepoel</span>
                    </div>
                </div>
            </aside>

            <main className="main-content">
                <header className="header">
                    <h1>AuraIA</h1>
                    <div className="status">
                        {connected ? '🟢 Connected' : '🔴 Disconnected'}
                    </div>
                </header>

                <div className="chat-container">
                    {messages.length === 0 ? (
                        <div className="welcome">
                            <h2>Ready when you are.</h2>
                        </div>
                    ) : (
                        <div className="messages">
                            {messages.map((msg, i) => (
                                <div key={i} className={`message ${msg.role}`}>
                                    <div className="message-avatar">
                                        {msg.role === 'user' ? 'HS' : 'AI'}
                                    </div>
                                    <div className="message-content">
                                        {msg.content}
                                    </div>
                                </div>
                            ))}
                            {isLoading && (
                                <div className="message assistant">
                                    <div className="message-avatar">AI</div>
                                    <div className="message-content">
                                        <div className="typing">●●●</div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                <div className="input-container">
                    <div className="input-wrapper">
                        <button className="attach-btn">+</button>
                        <input
                            type="text"
                            placeholder="Ask anything"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                            disabled={!connected}
                        />
                        <button className="voice-btn">🎤</button>
                        <button
                            className="send-btn"
                            onClick={handleSend}
                            disabled={!connected || !input.trim()}
                        >
                            ↑
                        </button>
                    </div>
                </div>
            </main>
        </div>
    );
}

export default App;
