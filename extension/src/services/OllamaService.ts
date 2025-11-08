// Lightweight service; avoids hard dependency on VS Code for testability.
// Tries to lazily require vscode if running inside the extension host.
// Fall back to default base URL when not available (e.g., unit tests).

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let vscodeRef: any = undefined;
try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    vscodeRef = require("vscode");
} catch {
    // Running in tests outside VS Code host.
}

type OllamaTag = {
    name: string;
    model: string;
    modified?: string;
    size?: number;
};

export interface PullProgress {
    status?: string;
    digest?: string;
    total?: number;
    completed?: number;
    error?: string;
}

export class OllamaService {
    private explicitBase?: string;
    constructor(explicitBase?: string) {
        this.explicitBase = explicitBase;
    }

    private getBase(): string {
        if (this.explicitBase) {
            return this.explicitBase.replace(/\/$/, "");
        }
        try {
            if (vscodeRef) {
                const cfg = vscodeRef.workspace.getConfiguration("aura");
                const url = (cfg.get("ollama.url", "http://127.0.0.1:11434") as string) || "http://127.0.0.1:11434";
                return url.replace(/\/$/, "");
            }
        } catch {
            // ignore
        }
        return "http://127.0.0.1:11434";
    }

    async listModels(): Promise<OllamaTag[]> {
        const url = this.getBase() + "/api/tags";
        const maxRetries = 3;
        let attempt = 0;
        while (true) {
            try {
                const res = await (globalThis as any).fetch(url, { headers: { Accept: "application/json" } } as any);
                if (!res?.ok) throw new Error(`HTTP ${res?.status}`);
                const data = await res.json();
                return Array.isArray(data?.models) ? data.models : [];
            } catch (e) {
                attempt++;
                if (attempt > maxRetries) throw e;
                const backoff = 200 * Math.pow(2, attempt - 1) + Math.random() * 80;
                await new Promise(r => setTimeout(r, backoff));
            }
        }
    }

    async pullModel(name: string, onProgress?: (status: string, prog?: PullProgress) => void): Promise<void> {
        const url = this.getBase() + "/api/pull";
        const res = await (globalThis as any).fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json", Accept: "application/json" },
            body: JSON.stringify({ name, stream: true }),
        } as any);
        if (!res?.ok) {
            const text = res && res.text ? await res.text() : "";
            throw new Error(`Pull failed: HTTP ${res?.status} ${text}`);
        }
        if (!(res as any).body || !(res as any).body.getReader) {
            const data = await res.json();
            if (onProgress) onProgress(data?.status || "completed");
            return;
        }
        const reader = (res as any).body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let done = false;
        while (!done) {
            const { value, done: d } = await reader.read();
            done = d;
            if (value) {
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split(/\n/);
                buffer = lines.pop() || "";
                for (const line of lines) {
                    const t = line.trim();
                    if (!t) continue;
                    try {
                        const obj: PullProgress = JSON.parse(t);
                        if (onProgress) onProgress(obj.status || "pulling", obj);
                    } catch {
                        // ignore
                    }
                }
            }
        }
        if (buffer.trim()) {
            try {
                const obj: PullProgress = JSON.parse(buffer.trim());
                if (onProgress) onProgress(obj.status || "completed", obj);
            } catch {
                // ignore
            }
        }
    }

    async deleteModel(name: string): Promise<void> {
        const url = this.getBase() + "/api/delete";
        const res = await (globalThis as any).fetch(url, {
            method: "DELETE",
            headers: { "Content-Type": "application/json", Accept: "application/json" },
            body: JSON.stringify({ name }),
        } as any);
        if (!res?.ok) {
            const text = res && res.text ? await res.text() : "";
            throw new Error(`Delete failed: HTTP ${res?.status} ${text}`);
        }
    }

    async generate(model: string, prompt: string): Promise<string> {
        const url = this.getBase() + "/api/generate";
        const res = await (globalThis as any).fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json", Accept: "application/json" },
            body: JSON.stringify({ model, prompt, stream: false }),
        } as any);
        if (!res?.ok) {
            const text = res && res.text ? await res.text() : "";
            throw new Error(`Generate failed: HTTP ${res?.status} ${text}`);
        }
        const data = await res.json();
        return data?.response || "";
    }
}
