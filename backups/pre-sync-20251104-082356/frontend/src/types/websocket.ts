/**
 * Shared WebSocket contract types matching backend/src/main.py payloads.
 * Project Creator: Herman Swanepoel
 */

export type ServerMessageType =
  | "connection_established"
  | "task_acknowledged"
  | "agent_response"
  | "error"
  | "mode_changed"
  | "pong";

export interface ConnectionEstablishedPayload {
  client_id: string;
  message: string;
  timestamp: number;
}

export interface TaskAcknowledgedPayload {
  task_id: string;
  status: string;
  received_at: number;
  message: string;
}

export interface AgentSuggestionPayload {
  id: string;
  code: string;
  description: string;
  confidence: string;
  diff?: string;
  applicable_range?: Record<string, unknown>;
}

export interface AgentResponsePayload {
  agent_id: string;
  agent_name: string;
  suggestions: AgentSuggestionPayload[];
  confidence: number;
  reasoning: string;
  metadata: Record<string, unknown>;
}

export interface AgentRunResultPayload {
  response: AgentResponsePayload;
  duration_ms: number;
  escalated: boolean;
}

export interface TaskSessionResultPayload {
  task_id: string;
  status: string;
  summary: string;
  reasoning: string;
  responses: AgentRunResultPayload[];
  metrics: Record<string, unknown>;
  errors: string[];
}

export interface ErrorPayload {
  message: string;
  details?: string;
  correlation_id?: string;
}

export interface ModeChangedPayload {
  mode: string;
  message: string;
  timestamp: number;
}

export type PongPayload = {
  timestamp?: number;
};

export type ServerMessageMap = {
  connection_established: ConnectionEstablishedPayload;
  task_acknowledged: TaskAcknowledgedPayload;
  agent_response: TaskSessionResultPayload;
  error: ErrorPayload;
  mode_changed: ModeChangedPayload;
  pong: PongPayload;
};

export type ServerMessage<K extends ServerMessageType = ServerMessageType> = {
  [T in ServerMessageType]: {
    type: T;
    payload: ServerMessageMap[T];
  };
}[K];

export type ClientMessageType = "task_request" | "ping" | "mode_change";

export interface TaskRequestPayload {
  id: string;
  type: string;
  description: string;
  content?: string;
  context?: Record<string, unknown>;
  mode?: string;
  metadata?: Record<string, unknown>;
}

export interface ClientMessageMap {
  task_request: TaskRequestPayload;
  ping: Record<string, never> | { timestamp?: number };
  mode_change: { mode: string };
}

export type ClientMessage<K extends ClientMessageType = ClientMessageType> = {
  type: K;
  payload: ClientMessageMap[K];
};
