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

interface ChatSession {
    id: string;
    title: string;
    messages: Message[];
    timestamp: number;
}

function App() {
    const [connected, setConnected] = useState(false);
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [chatHistory, setChatHistory] = useState<ChatSession[]>([]);
    const [currentChatId, setCurrentChatId] = useState<string | null>(null);
    const [mode, setMode] = useState<'local' | 'cloud'>('local');
    const [selectedModel, setSelectedModel] = useState('auto');

    useEffect(() => {
        // Load chat history from localStorage
        const saved = localStorage.getItem('auraIA_chats');
        if (saved) {
            setChatHistory(JSON.parse(saved));
        }

        wsService.connect()
            .then(() => {
                setConnected(true);
                wsService.on('agent_response', (payload) => {
                    const newMsg = {
                        role: 'assistant' as const,
                        content: payload.reasoning || 'Response received',
                        timestamp: Date.now()
                    };
                    setMessages(prev => {
                        const updated = [...prev, newMsg];
                        saveCurrentChat(updated);
                        return updated;
                    });
                    setIsLoading(false);
                });
            })
            .catch(() => setConnected(false));

        return () => wsService.disconnect();
    }, []);

    const saveCurrentChat = (msgs: Message[]) => {
        if (msgs.length === 0) return;

        const chatId = currentChatId || `chat-${Date.now()}`;
        const title = msgs[0]?.content.substring(0, 30) + '...' || 'New Chat';

        setChatHistory(prev => {
            const existing = prev.find(c => c.id === chatId);
            const updated = existing
                ? prev.map(c => c.id === chatId ? { ...c, messages: msgs, title } : c)
                : [...prev, { id: chatId, title, messages: msgs, timestamp: Date.now() }];

            localStorage.setItem('auraIA_chats', JSON.stringify(updated));
            return updated;
        });

        if (!currentChatId) setCurrentChatId(chatId);
    };

    const startNewChat = () => {
        setMessages([]);
        setCurrentChatId(null);
        setInput('');
    };

    const loadChat = (chatId: string) => {
        const chat = chatHistory.find(c => c.id === chatId);
        if (chat) {
            setMessages(chat.messages);
            setCurrentChatId(chatId);
        }
    };

    const deleteChat = (chatId: string, e: React.MouseEvent) => {
        e.stopPropagation();
        setChatHistory(prev => {
            const updated = prev.filter(c => c.id !== chatId);
            localStorage.setItem('auraIA_chats', JSON.stringify(updated));
            return updated;
        });
        if (currentChatId === chatId) {
            startNewChat();
        }
    };

    const toggleMode = () => {
        const newMode = mode === 'local' ? 'cloud' : 'local';
        setMode(newMode);
        console.log('🔄 Switching mode to:', newMode);

        if (wsService && connected) {
            wsService.sendTask({
                type: 'mode_change',
                payload: {
                    mode: newMode
                }
            });
        }
    };

    const handleSend = () => {
        if (!input.trim() || !connected) return;

        const newMsg = {
            role: 'user' as const,
            content: input,
            timestamp: Date.now()
        };

        setMessages(prev => {
            const updated = [...prev, newMsg];
            saveCurrentChat(updated);
            return updated;
        });

        wsService.sendTask({
            id: `task-${Date.now()}`,
            type: 'code_generation',
            context: {
                description: input,
                model: selectedModel
            }
        });

        setInput('');
        setIsLoading(true);
    };

    return (
        <div className="app">
            <aside className="sidebar">
                <div className="sidebar-header">
                    <button className="new-chat-btn" onClick={startNewChat}>
                        <span>+</span> New chat
                    </button>
                </div>
                <div className="chat-history">
                    {chatHistory.length === 0 ? (
                        <div style={{ padding: '20px', textAlign: 'center', color: '#8e8e8e', fontSize: '14px' }}>
                            No chat history yet
                        </div>
                    ) : (
                        chatHistory.sort((a, b) => b.timestamp - a.timestamp).map(chat => (
                            <div
                                key={chat.id}
                                className={`chat-item ${currentChatId === chat.id ? 'active' : ''}`}
                                onClick={() => loadChat(chat.id)}
                            >
                                <div style={{ flex: 1 }}>{chat.title}</div>
                                <button
                                    className="delete-btn"
                                    onClick={(e) => deleteChat(chat.id, e)}
                                    title="Delete chat"
                                >
                                    🗑️
                                </button>
                            </div>
                        ))
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
                    <div className="header-controls">
                        <div className="status">
                            {connected ? '🟢 Connected' : '🔴 Disconnected'}
                        </div>
                        <div className="mode-toggle">
                            <span style={{ fontSize: '14px', marginRight: '8px' }}>
                                {mode === 'local' ? '💻 Local' : '☁️ Cloud'}
                            </span>
                            <label className="toggle-switch">
                                <input
                                    type="checkbox"
                                    checked={mode === 'cloud'}
                                    onChange={toggleMode}
                                />
                                <span className="toggle-slider"></span>
                            </label>
                        </div>
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
