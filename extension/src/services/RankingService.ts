import * as vscode from "vscode";
// Using global fetch available in recent VS Code extension runtimes

export type RepoItem = {
  type: "repo";
  repo: {
    name: string;
    full_name: string;
    private: boolean;
    html_url: string;
    description?: string;
    stargazers_count?: number;
    forks_count?: number;
    updated_at?: string;
  };
  score: number;
  norm_score?: number;
};

export type IssueItem = {
  type: "issue";
  repo: RepoItem["repo"];
  issue: {
    number: number;
    title: string;
    body?: string;
    html_url: string;
    comments?: number;
    state?: string;
    updated_at?: string;
  };
  score: number;
  norm_score?: number;
};

export type PrItem = {
  type: "pr";
  repo: RepoItem["repo"];
  pr: {
    number: number;
    title: string;
    body?: string;
    html_url: string;
    comments?: number;
    state?: string;
    updated_at?: string;
  };
  score: number;
  norm_score?: number;
};

export type RankingItem = RepoItem | IssueItem | PrItem;

export type RankOptions = {
  visibility?: "public" | "private";
  limit?: number;
  include?: string[];
  exclude?: string[];
  top?: number;
  itemsPerRepo?: number;
  sinceISO?: string; // when ranking all
  ultraMode?: "disabled" | "mock" | "local" | "backend";
};

/**
 * RankingService abstracts transport for fetching ranking results.
 * We keep transport pluggable so we can route via backend proxy or MCP bridge later.
 */
export class RankingService {
  constructor(private readonly context: vscode.ExtensionContext) { }

  private makeTraceId(): string {
    const rand = Math.random().toString(36).slice(2, 10);
    const ts = Date.now().toString(36);
    return `aura-${ts}-${rand}`;
  }

  private resolveConfig(options?: Partial<RankOptions>): Required<RankOptions> {
    const cfg = vscode.workspace.getConfiguration("aura");
    const itemsPerRepo = options?.itemsPerRepo ?? cfg.get<number>("ranking.itemsPerRepo", 20);
    const sinceDays = cfg.get<number>("ranking.sinceDays", 30);
    const sinceISO = options?.sinceISO ?? new Date(Date.now() - sinceDays * 86400000)
      .toISOString()
      .replace(/\.\d{3}Z$/, "Z");
    const ultraMode = options?.ultraMode ?? cfg.get<string>("ranking.ultraMode", "local");
    return {
      visibility: options?.visibility,
      limit: options?.limit ?? 25,
      include: options?.include ?? [],
      exclude: options?.exclude ?? [],
      top: options?.top ?? 25,
      itemsPerRepo,
      sinceISO,
      ultraMode: (ultraMode as any) || "local",
    } as Required<RankOptions>;
  }

  async rankRepos(query: string, options?: Partial<RankOptions>): Promise<RepoItem[]> {
    const cfg = this.resolveConfig(options);
    const endpoint = this.getBackendUrl() + "/mcp/github/rank_repos";
    const health = await this.ensureHealthy();
    if (!health.ok) {
      return [];
    }
    try {
      const data = await this.postJson<any>(endpoint, {
        query,
        visibility: cfg.visibility,
        limit: cfg.limit,
        include: cfg.include.length ? cfg.include : undefined,
        exclude: cfg.exclude.length ? cfg.exclude : undefined,
        top: cfg.top,
        ultraMode: cfg.ultraMode,
      });
      const ranking = Array.isArray(data.ranking) ? data.ranking : [];
      // Map generic entries { repo, score, norm_score? }
      return ranking
        .filter((r: any) => r.repo)
        .map(
          (r: any): RepoItem => ({
            type: "repo",
            repo: r.repo,
            score: Number(r.score) || 0,
            norm_score: typeof r.norm_score === "number" ? r.norm_score : undefined,
          })
        );
    } catch (e: any) {
      vscode.window.showErrorMessage(
        `Ranking repos failed: ${e?.message || String(e)} (endpoint: ${endpoint})`
      );
      return [];
    }
  }

  async rankAll(query: string, options?: Partial<RankOptions>): Promise<RankingItem[]> {
    const cfg = this.resolveConfig(options);
    const endpoint = this.getBackendUrl() + "/mcp/github/rank_all";
    const health = await this.ensureHealthy();
    if (!health.ok) {
      return [];
    }
    try {
      const data = await this.postJson<any>(endpoint, {
        query,
        visibility: cfg.visibility,
        limit: cfg.limit,
        include: cfg.include.length ? cfg.include : undefined,
        exclude: cfg.exclude.length ? cfg.exclude : undefined,
        top: cfg.top,
        items_per_repo: cfg.itemsPerRepo,
        since: cfg.sinceISO,
        ultraMode: cfg.ultraMode,
      });
      const ranking = Array.isArray(data.ranking) ? data.ranking : [];
      return ranking
        .filter((r: any) => r.type)
        .map((r: any): RankingItem => {
          const base = {
            score: Number(r.score) || 0,
            norm_score: typeof r.norm_score === "number" ? r.norm_score : undefined,
          } as any;
          if (r.type === "repo" && r.repo) {
            return { type: "repo", repo: r.repo, ...base } as RepoItem;
          }
          if (r.type === "issue" && r.issue && r.repo) {
            return { type: "issue", repo: r.repo, issue: r.issue, ...base } as IssueItem;
          }
          if (r.type === "pr" && r.pr && r.repo) {
            return { type: "pr", repo: r.repo, pr: r.pr, ...base } as PrItem;
          }
          return { type: "repo", repo: r.repo, ...base } as RepoItem; // fallback
        });
    } catch (e: any) {
      vscode.window.showErrorMessage(
        `Ranking all failed: ${e?.message || String(e)} (endpoint: ${endpoint})`
      );
      return [];
    }
  }

  private getBackendUrl(): string {
    const cfg = vscode.workspace.getConfiguration("aura");
    return cfg.get<string>("backend.url", "http://127.0.0.1:8001").replace(/\/$/, "");
  }

  private _healthChecked = false;
  private async ensureHealthy(): Promise<{ ok: boolean }> {
    const res = await this.checkHealth({ force: !this._healthChecked, silent: false });
    if (res.ok) {
      this._healthChecked = true;
    }
    return { ok: res.ok };
  }

  async checkHealth(options?: { force?: boolean; silent?: boolean }): Promise<{ ok: boolean; details?: string; traceId?: string }> {
    const base = this.getBackendUrl();
    const traceId = this.makeTraceId();
    try {
      const gh = await this.getJson<any>(base + "/mcp/github/health", { "X-Aura-Trace": traceId });
      if (!gh || gh.ok !== true) {
        const hint = gh?.message || "GitHub token not configured.";
        if (!options?.silent) {
          vscode.window.showErrorMessage(
            `Aura MCP GitHub not ready: ${hint} — Set env GITHUB_TOKEN and restart backend.`
          );
        }
        return { ok: false, details: hint, traceId };
      }
      await this.getJson<any>(base + "/mcp/health", { "X-Aura-Trace": traceId });
      return { ok: true, details: "Backend and MCP are healthy", traceId };
    } catch (e: any) {
      const msg = `Aura backend unreachable at ${base}.`;
      if (!options?.silent) {
        vscode.window.showErrorMessage(
          `${msg} Check Backend: Url setting or server status.`
        );
      }
      return { ok: false, details: msg, traceId };
    }
  }

  private async getJson<T = any>(endpoint: string, headers?: Record<string, string>): Promise<T> {
    return this.fetchWithRetry<T>(endpoint, { method: "GET", headers });
  }

  private async postJson<T = any>(endpoint: string, body: any, headers?: Record<string, string>): Promise<T> {
    const traceId = this.makeTraceId();
    const merged = { ...(headers || {}), "X-Aura-Trace": traceId };
    return this.fetchWithRetry<T>(endpoint, { method: "POST", body: JSON.stringify(body ?? {}), headers: merged });
  }

  private async fetchWithRetry<T>(endpoint: string, opts: { method: string; body?: any; headers?: Record<string, string> }, attempt = 0): Promise<T> {
    const maxRetries = 3;
    const baseDelay = 250;
    try {
      const res = await (globalThis as any).fetch(endpoint, {
        method: opts.method,
        headers: { "Content-Type": "application/json", Accept: "application/json", ...(opts.headers || {}), "X-Aura-Trace": opts.headers?.["X-Aura-Trace"] || this.makeTraceId() },
        body: opts.body,
      } as any);
      if (!res || !res.ok) {
        const status = res ? res.status : "no-response";
        const text = res && res.text ? await res.text() : "";
        throw new Error(`HTTP ${status}: ${text?.slice?.(0, 120) ?? ""}`);
      }
      return (await res.json()) as T;
    } catch (err) {
      if (attempt < maxRetries) {
        const delay = baseDelay * Math.pow(2, attempt) + Math.floor(Math.random() * 60);
        await new Promise(r => setTimeout(r, delay));
        return this.fetchWithRetry<T>(endpoint, opts, attempt + 1);
      }
      throw err;
    }
  }
}
