/**
 * AuraIA - AI Assistant Interface
 * Project Creator: Herman Swanepoel
 */

import { useEffect, useMemo, useRef, useState } from "react";
import "./App.css";
import "./brand.css";
import { wsService, type ConnectionState } from "./services/websocket";
import type {
  ClientMessageMap,
  ConnectionEstablishedPayload,
  ErrorPayload,
  ModeChangedPayload,
  TaskAcknowledgedPayload,
  TaskSessionResultPayload,
} from "./types/websocket";

interface Message {
  role: "user" | "assistant";
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
  const [connectionState, setConnectionState] =
    useState<ConnectionState>("connecting");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [chatHistory, setChatHistory] = useState<ChatSession[]>([]);
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [mode, setMode] = useState<"local" | "cloud">("local");
  const [interactionMode, setInteractionMode] = useState<"agent" | "chat" | "edit">("chat");
  const [isListening, setIsListening] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const [banner, setBanner] = useState<{
    type: "info" | "error" | "warning";
    message: string;
  } | null>(null);
  const [lastPingAt, setLastPingAt] = useState<number | null>(null);
  const currentChatIdRef = useRef<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const connected = connectionState === "connected";

  useEffect(() => {
    currentChatIdRef.current = currentChatId;
  }, [currentChatId]);

  useEffect(() => {
    // Load chat history from localStorage
    const saved = localStorage.getItem("auraIA_chats");
    if (saved) {
      setChatHistory(JSON.parse(saved));
    }

    const handleConnectionChange = (state: ConnectionState) => {
      setConnectionState(state);
      if (state !== "connected") {
        setIsLoading(false);
      }

      if (state === "connecting") {
        setBanner({ type: "info", message: "Connecting to AuraIA backend…" });
      } else if (state === "disconnected") {
        setBanner({
          type: "error",
          message: "Connection lost. Attempting to reconnect…",
        });
      }
    };

    const handleConnectionEstablished = (
      payload: ConnectionEstablishedPayload,
    ) => {
      setBanner({ type: "info", message: payload.message });
    };

    const handleTaskAcknowledged = (payload: TaskAcknowledgedPayload) => {
      setBanner({ type: "info", message: payload.message });
    };

    const handleAgentResponse = (payload: TaskSessionResultPayload) => {
      // Extract actual suggestions from the response
      let content = "";
      
      if (payload.responses && payload.responses.length > 0) {
        // Get all suggestions from responses
        const suggestions = payload.responses
          .filter(r => r.response?.suggestions && r.response.suggestions.length > 0)
          .flatMap(r => r.response.suggestions);
        
        if (suggestions.length > 0) {
          content = suggestions
            .map(s => `${s.description || ''}\n\`\`\`\n${s.code || ''}\n\`\`\``)
            .join('\n\n');
        }
      }
      
      // Fallback to reasoning/summary if no suggestions
      if (!content) {
        content = payload.reasoning || payload.summary || "Response received";
      }
      
      const newMsg = {
        role: "assistant" as const,
        content: content,
        timestamp: Date.now(),
      };

      setMessages((prev) => {
        const updated = [...prev, newMsg];
        saveCurrentChat(updated);
        return updated;
      });
      setIsLoading(false);
    };

    const handleError = (payload: ErrorPayload) => {
      setBanner({ type: "error", message: payload.message });
      setIsLoading(false);
    };

    const handleModeChanged = (payload: ModeChangedPayload) => {
      const normalizedMode = payload.mode === "cloud" ? "cloud" : "local";
      setMode(normalizedMode);
      setBanner({ type: "info", message: payload.message });
    };

    const handlePong = () => {
      setLastPingAt(Date.now());
    };

    wsService.subscribeConnectionChange(handleConnectionChange);
    wsService.on("connection_established", handleConnectionEstablished);
    wsService.on("task_acknowledged", handleTaskAcknowledged);
    wsService.on("agent_response", handleAgentResponse);
    wsService.on("error", handleError);
    wsService.on("mode_changed", handleModeChanged);
    wsService.on("pong", handlePong);

    wsService.connect().catch(() => setConnectionState("disconnected"));

    return () => {
      wsService.unsubscribeConnectionChange(handleConnectionChange);
      wsService.off("connection_established", handleConnectionEstablished);
      wsService.off("task_acknowledged", handleTaskAcknowledged);
      wsService.off("agent_response", handleAgentResponse);
      wsService.off("error", handleError);
      wsService.off("mode_changed", handleModeChanged);
      wsService.off("pong", handlePong);
      wsService.disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!banner) {
      return;
    }
    const timer = window.setTimeout(() => setBanner(null), 5000);
    return () => window.clearTimeout(timer);
  }, [banner]);

  const saveCurrentChat = (msgs: Message[]) => {
    if (msgs.length === 0) return;

    const existingChatId = currentChatIdRef.current || currentChatId;
    const chatId = existingChatId || `chat-${Date.now()}`;
    const title = msgs[0]?.content.substring(0, 30) + "..." || "New Chat";

    setChatHistory((prev) => {
      const existing = prev.find((c) => c.id === chatId);
      const updated = existing
        ? prev.map((c) =>
            c.id === chatId ? { ...c, messages: msgs, title } : c,
          )
        : [
            ...prev,
            { id: chatId, title, messages: msgs, timestamp: Date.now() },
          ];

      localStorage.setItem("auraIA_chats", JSON.stringify(updated));
      return updated;
    });

    if (!existingChatId) {
      setCurrentChatId(chatId);
      currentChatIdRef.current = chatId;
    }
  };

  const startNewChat = () => {
    setMessages([]);
    setCurrentChatId(null);
    setInput("");
  };

  const loadChat = (chatId: string) => {
    const chat = chatHistory.find((c) => c.id === chatId);
    if (chat) {
      setMessages(chat.messages);
      setCurrentChatId(chatId);
    }
  };

  const deleteChat = (chatId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setChatHistory((prev) => {
      const updated = prev.filter((c) => c.id !== chatId);
      localStorage.setItem("auraIA_chats", JSON.stringify(updated));
      return updated;
    });
    if (currentChatId === chatId) {
      startNewChat();
    }
  };

  const toggleMode = () => {
    const newMode = mode === "local" ? "cloud" : "local";
    setMode(newMode);
    console.log("🔄 Switching mode to:", newMode);

    if (connected) {
      wsService.changeMode(newMode);
    }
  };

  const handleFileAttach = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    setAttachedFiles(prev => [...prev, ...files]);
    setBanner({ type: "info", message: `${files.length} file(s) attached` });
  };

  const removeFile = (index: number) => {
    setAttachedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const toggleVoiceInput = () => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      setBanner({ type: "error", message: "Voice input not supported in this browser" });
      return;
    }

    if (isListening) {
      setIsListening(false);
      setBanner({ type: "info", message: "Voice input stopped" });
    } else {
      setIsListening(true);
      setBanner({ type: "info", message: "Listening... Speak now" });
      
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      
      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        setInput(prev => prev + (prev ? ' ' : '') + transcript);
        setIsListening(false);
      };
      
      recognition.onerror = () => {
        setIsListening(false);
        setBanner({ type: "error", message: "Voice input error" });
      };
      
      recognition.onend = () => {
        setIsListening(false);
      };
      
      recognition.start();
    }
  };

  const handleSend = () => {
    if (!input.trim() || !connected) return;

    const newMsg = {
      role: "user" as const,
      content: input,
      timestamp: Date.now(),
    };

    setMessages((prev) => {
      const updated = [...prev, newMsg];
      saveCurrentChat(updated);
      return updated;
    });

    // Determine task type based on interaction mode
    let taskType = "code_generation";
    if (interactionMode === "agent") {
      taskType = "code_generation";
    } else if (interactionMode === "edit") {
      taskType = "refactor";
    } else {
      taskType = "documentation";
    }

    const payload: ClientMessageMap["task_request"] = {
      id: `task-${Date.now()}`,
      type: taskType,
      description: input,
      content: input,
      context: {
        description: input,
        mode,
        interaction_mode: interactionMode,
        files: attachedFiles.map(f => f.name),
      },
      mode,
      metadata: {
        source: "frontend",
        attached_files: attachedFiles.length,
      },
    };

    wsService.sendTask(payload);

    setInput("");
    setAttachedFiles([]);
    setIsLoading(true);
  };

  const connectionLabel = useMemo(() => {
    switch (connectionState) {
      case "connected":
        return "🟢 Connected";
      case "connecting":
        return "🟡 Connecting…";
      default:
        return "🔴 Disconnected";
    }
  }, [connectionState]);

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-header">
          {/* Logo */}
          <div className="logo-container">
            <div className="logo-text">AuraIA</div>
            <div className="logo-tagline">The Future Beside You</div>
          </div>
          
          <button className="new-chat-btn" onClick={startNewChat}>
            <span>+</span> New chat
          </button>
        </div>
        <div className="chat-history">
          {chatHistory.length === 0 ? (
            <div
              style={{
                padding: "20px",
                textAlign: "center",
                color: "#8e8e8e",
                fontSize: "14px",
              }}
            >
              No chat history yet
            </div>
          ) : (
            chatHistory
              .sort((a, b) => b.timestamp - a.timestamp)
              .map((chat) => (
                <div
                  key={chat.id}
                  className={`chat-item ${currentChatId === chat.id ? "active" : ""}`}
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
            <div className="mode-selector">
              <button
                className={`mode-btn ${interactionMode === "chat" ? "active" : ""}`}
                onClick={() => setInteractionMode("chat")}
                title="Chat mode - conversational AI"
              >
                💬 Chat
              </button>
              <button
                className={`mode-btn ${interactionMode === "agent" ? "active" : ""}`}
                onClick={() => setInteractionMode("agent")}
                title="Agent mode - code generation"
              >
                🤖 Agent
              </button>
              <button
                className={`mode-btn ${interactionMode === "edit" ? "active" : ""}`}
                onClick={() => setInteractionMode("edit")}
                title="Edit mode - refactoring"
              >
                ✏️ Edit
              </button>
            </div>
            <div className={`status status-${connectionState}`}>
              {connectionLabel}
              {lastPingAt && connected ? (
                <span className="status-latency" title="Last heartbeat">
                  • {new Date(lastPingAt).toLocaleTimeString()}
                </span>
              ) : null}
            </div>
            <div className="mode-toggle">
              <span style={{ fontSize: "14px", marginRight: "8px" }}>
                {mode === "local" ? "💻 Local" : "☁️ Cloud"}
              </span>
              <label className="toggle-switch">
                <input
                  type="checkbox"
                  checked={mode === "cloud"}
                  onChange={toggleMode}
                />
                <span className="toggle-slider"></span>
              </label>
            </div>
          </div>
        </header>

        {banner ? (
          <div className={`status-banner status-${banner.type}`} role="status">
            {banner.message}
          </div>
        ) : null}

        <div className="chat-container">
          {!connected ? (
            <div className="connection-placeholder" role="alert">
              <h2>
                {connectionState === "connecting"
                  ? "Connecting…"
                  : "Unable to reach backend"}
              </h2>
              <p>
                We will keep retrying automatically. Please check your backend
                status.
              </p>
            </div>
          ) : messages.length === 0 ? (
            <div className="welcome">
              <h2>Ready when you are.</h2>
            </div>
          ) : (
            <div className="messages">
              {messages.map((msg, i) => (
                <div key={i} className={`message ${msg.role}`}>
                  <div className="message-avatar">
                    {msg.role === "user" ? "HS" : "AI"}
                  </div>
                  <div className="message-content">{msg.content}</div>
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
          {attachedFiles.length > 0 && (
            <div className="attached-files">
              {attachedFiles.map((file, i) => (
                <div key={i} className="file-chip">
                  📎 {file.name}
                  <button onClick={() => removeFile(i)} className="remove-file">×</button>
                </div>
              ))}
            </div>
          )}
          <div className="input-wrapper">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              style={{ display: 'none' }}
              multiple
            />
            <button 
              className="attach-btn" 
              onClick={handleFileAttach}
              title="Attach files"
            >
              +
            </button>
            <input
              type="text"
              placeholder={
                connected
                  ? "Ask anything"
                  : connectionState === "connecting"
                    ? "Connecting to backend…"
                    : "Backend unavailable"
              }
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && handleSend()}
            />
            <button 
              className={`voice-btn ${isListening ? 'listening' : ''}`}
              onClick={toggleVoiceInput}
              title={isListening ? "Stop listening" : "Start voice input"}
            >
              {isListening ? '⏹️' : '🎤'}
            </button>
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
