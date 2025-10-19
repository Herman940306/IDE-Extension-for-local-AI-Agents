/**
 * Analytics Service for productivity tracking
 * Project Creator: Herman Swanepoel
 */

import * as vscode from 'vscode';

interface SuggestionEvent {
    timestamp: number;
    type: 'inline' | 'code_action' | 'discussion';
    accepted: boolean;
    confidence: number;
    agentName?: string;
    language?: string;
}

interface AgentMetrics {
    agentName: string;
    totalSuggestions: number;
    acceptedSuggestions: number;
    rejectedSuggestions: number;
    acceptanceRate: number;
    averageConfidence: number;
    lastUsed: number;
}

interface ProductivityMetrics {
    totalSuggestions: number;
    acceptedSuggestions: number;
    rejectedSuggestions: number;
    acceptanceRate: number;
    suggestionsByLanguage: Record<string, number>;
    suggestionsByType: Record<string, number>;
    suggestionsByHour: Record<number, number>;
    mostProductiveHours: number[];
}

interface WorkflowPattern {
    pattern: string;
    frequency: number;
    lastOccurrence: number;
    suggestion?: string;
}

interface CacheEntry {
    data: any;
    timestamp: number;
}

export class AnalyticsService {
    private context: vscode.ExtensionContext;
    private events: SuggestionEvent[] = [];
    private readonly MAX_EVENTS = 10000;
    private readonly RETENTION_DAYS = 90;
    private enabled: boolean = false;

    // Predictive caching
    private cache: Map<string, CacheEntry> = new Map();
    private readonly CACHE_TTL = 5 * 60 * 1000; // 5 minutes
    private readonly CACHE_KEYS = {
        SUMMARY: 'summary',
        RATES: 'rates',
        AGENT_METRICS: 'agent_metrics',
        PRODUCTIVITY: 'productivity',
        PATTERNS: 'patterns',
        TIME_SERIES: 'time_series',
        LANGUAGE_DIST: 'language_dist',
        HOURLY: 'hourly'
    };

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
        this.loadEvents();
        this.refreshConfiguration();
        this.startCacheCleanup();
    }

    /**
     * Check if user has opted out of analytics
     */
    public refreshConfiguration() {
        const config = vscode.workspace.getConfiguration('enterpriseAI');
        const allowTelemetry = config.get<boolean>('privacy.allowTelemetry', false);

        if (!allowTelemetry && this.events.length > 0) {
            this.events = [];
            this.invalidateCache();
            void this.saveEvents();
        }

        this.enabled = allowTelemetry;
    }

    /**
     * Track a suggestion event
     */
    public trackSuggestion(event: Omit<SuggestionEvent, 'timestamp'>) {
        if (!this.enabled) {
            return;
        }

        const fullEvent: SuggestionEvent = {
            ...event,
            timestamp: Date.now()
        };

        this.events.push(fullEvent);

        // Limit event storage
        if (this.events.length > this.MAX_EVENTS) {
            this.events = this.events.slice(-this.MAX_EVENTS);
        }

        // Clean old events
        this.cleanOldEvents();

        // Invalidate cache on new data
        this.invalidateCache();

        // Save to storage
        this.saveEvents();
    }

    /**
     * Get suggestion acceptance/rejection rates (with caching)
     */
    public getSuggestionRates(): {
        total: number;
        accepted: number;
        rejected: number;
        acceptanceRate: number;
    } {
        const cached = this.getFromCache<{
            total: number;
            accepted: number;
            rejected: number;
            acceptanceRate: number;
        }>(this.CACHE_KEYS.RATES);
        if (cached) {
            return cached;
        }

        const total = this.events.length;
        const accepted = this.events.filter(e => e.accepted).length;
        const rejected = total - accepted;
        const acceptanceRate = total > 0 ? accepted / total : 0;

        const result = {
            total,
            accepted,
            rejected,
            acceptanceRate
        };

        this.setCache(this.CACHE_KEYS.RATES, result);
        return result;
    }

    /**
     * Get agent effectiveness metrics (with caching)
     */
    public getAgentMetrics(): AgentMetrics[] {
        const cached = this.getFromCache<AgentMetrics[]>(this.CACHE_KEYS.AGENT_METRICS);
        if (cached) {
            return cached;
        }

        const result = this.computeAgentMetrics();
        this.setCache(this.CACHE_KEYS.AGENT_METRICS, result);
        return result;
    }

    /**
     * Compute agent effectiveness metrics
     */
    private computeAgentMetrics(): AgentMetrics[] {
        const agentMap = new Map<string, {
            total: number;
            accepted: number;
            confidenceSum: number;
            lastUsed: number;
        }>();

        // Aggregate by agent
        for (const event of this.events) {
            const agentName = event.agentName || 'Unknown';

            if (!agentMap.has(agentName)) {
                agentMap.set(agentName, {
                    total: 0,
                    accepted: 0,
                    confidenceSum: 0,
                    lastUsed: 0
                });
            }

            const metrics = agentMap.get(agentName)!;
            metrics.total++;
            if (event.accepted) {
                metrics.accepted++;
            }
            metrics.confidenceSum += event.confidence;
            metrics.lastUsed = Math.max(metrics.lastUsed, event.timestamp);
        }

        // Convert to array
        const result: AgentMetrics[] = [];
        for (const [agentName, data] of agentMap.entries()) {
            result.push({
                agentName,
                totalSuggestions: data.total,
                acceptedSuggestions: data.accepted,
                rejectedSuggestions: data.total - data.accepted,
                acceptanceRate: data.total > 0 ? data.accepted / data.total : 0,
                averageConfidence: data.total > 0 ? data.confidenceSum / data.total : 0,
                lastUsed: data.lastUsed
            });
        }

        // Sort by total suggestions
        result.sort((a, b) => b.totalSuggestions - a.totalSuggestions);

        return result;
    }

    /**
     * Get productivity metrics
     */
    public getProductivityMetrics(): ProductivityMetrics {
        const rates = this.getSuggestionRates();

        const suggestionsByLanguage: Record<string, number> = {};
        const suggestionsByType: Record<string, number> = {};
        const suggestionsByHour: Record<number, number> = {};

        for (const event of this.events) {
            // By language
            if (event.language) {
                suggestionsByLanguage[event.language] = (suggestionsByLanguage[event.language] || 0) + 1;
            }

            // By type
            suggestionsByType[event.type] = (suggestionsByType[event.type] || 0) + 1;

            // By hour
            const hour = new Date(event.timestamp).getHours();
            suggestionsByHour[hour] = (suggestionsByHour[hour] || 0) + 1;
        }

        // Find most productive hours (top 3)
        const hourEntries = Object.entries(suggestionsByHour)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 3);
        const mostProductiveHours = hourEntries.map(([hour]) => parseInt(hour));

        return {
            totalSuggestions: rates.total,
            acceptedSuggestions: rates.accepted,
            rejectedSuggestions: rates.rejected,
            acceptanceRate: rates.acceptanceRate,
            suggestionsByLanguage,
            suggestionsByType,
            suggestionsByHour,
            mostProductiveHours
        };
    }

    /**
     * Analyze workflow patterns
     */
    public analyzeWorkflowPatterns(): WorkflowPattern[] {
        const patterns: WorkflowPattern[] = [];

        // Pattern 1: High rejection rate
        const rates = this.getSuggestionRates();
        if (rates.acceptanceRate < 0.5 && rates.total > 10) {
            patterns.push({
                pattern: 'Low acceptance rate',
                frequency: rates.rejected,
                lastOccurrence: Date.now(),
                suggestion: 'Consider adjusting AI settings or providing more context for better suggestions'
            });
        }

        // Pattern 2: Specific language dominance
        const metrics = this.getProductivityMetrics();
        const topLanguage = Object.entries(metrics.suggestionsByLanguage)
            .sort((a, b) => b[1] - a[1])[0];

        if (topLanguage && topLanguage[1] > rates.total * 0.7) {
            patterns.push({
                pattern: `Heavy ${topLanguage[0]} usage`,
                frequency: topLanguage[1],
                lastOccurrence: Date.now(),
                suggestion: `Consider enabling language-specific optimizations for ${topLanguage[0]}`
            });
        }

        // Pattern 3: Time-based patterns
        if (metrics.mostProductiveHours.length > 0) {
            const hour = metrics.mostProductiveHours[0];
            patterns.push({
                pattern: 'Peak productivity hours',
                frequency: metrics.suggestionsByHour[hour] || 0,
                lastOccurrence: Date.now(),
                suggestion: `Your most productive hour is ${hour}:00. Consider scheduling complex tasks during this time.`
            });
        }

        // Pattern 4: Agent effectiveness
        const agentMetrics = this.getAgentMetrics();
        const topAgent = agentMetrics[0];
        if (topAgent && topAgent.acceptanceRate > 0.8) {
            patterns.push({
                pattern: 'Highly effective agent',
                frequency: topAgent.acceptedSuggestions,
                lastOccurrence: topAgent.lastUsed,
                suggestion: `${topAgent.agentName} has ${Math.round(topAgent.acceptanceRate * 100)}% acceptance rate. Consider using it more often.`
            });
        }

        return patterns;
    }

    /**
     * Get time-series data for charts
     */
    public getTimeSeriesData(days: number = 7): {
        labels: string[];
        accepted: number[];
        rejected: number[];
    } {
        const now = Date.now();
        const dayMs = 24 * 60 * 60 * 1000;
        const startTime = now - (days * dayMs);

        const labels: string[] = [];
        const accepted: number[] = [];
        const rejected: number[] = [];

        for (let i = 0; i < days; i++) {
            const dayStart = startTime + (i * dayMs);
            const dayEnd = dayStart + dayMs;

            const dayEvents = this.events.filter(e =>
                e.timestamp >= dayStart && e.timestamp < dayEnd
            );

            const dayAccepted = dayEvents.filter(e => e.accepted).length;
            const dayRejected = dayEvents.length - dayAccepted;

            const date = new Date(dayStart);
            labels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
            accepted.push(dayAccepted);
            rejected.push(dayRejected);
        }

        return { labels, accepted, rejected };
    }

    /**
     * Get language distribution for pie chart
     */
    public getLanguageDistribution(): { language: string; count: number; percentage: number }[] {
        const metrics = this.getProductivityMetrics();
        const total = metrics.totalSuggestions;

        return Object.entries(metrics.suggestionsByLanguage)
            .map(([language, count]) => ({
                language,
                count,
                percentage: total > 0 ? (count / total) * 100 : 0
            }))
            .sort((a, b) => b.count - a.count);
    }

    /**
     * Get hourly activity heatmap data
     */
    public getHourlyActivity(): { hour: number; count: number }[] {
        const metrics = this.getProductivityMetrics();

        const result: { hour: number; count: number }[] = [];
        for (let hour = 0; hour < 24; hour++) {
            result.push({
                hour,
                count: metrics.suggestionsByHour[hour] || 0
            });
        }

        return result;
    }

    /**
     * Export analytics data
     */
    public exportData(): string {
        const data = {
            exportDate: new Date().toISOString(),
            suggestionRates: this.getSuggestionRates(),
            agentMetrics: this.getAgentMetrics(),
            productivityMetrics: this.getProductivityMetrics(),
            workflowPatterns: this.analyzeWorkflowPatterns(),
            timeSeriesData: this.getTimeSeriesData(30),
            languageDistribution: this.getLanguageDistribution(),
            hourlyActivity: this.getHourlyActivity()
        };

        return JSON.stringify(data, null, 2);
    }

    /**
     * Clear all analytics data
     */
    public async clearData() {
        this.events = [];
        await this.saveEvents();
    }

    /**
     * Enable/disable analytics
     */
    public async setEnabled(enabled: boolean, options: { persist?: boolean } = {}) {
        this.enabled = enabled;

        if (!enabled) {
            this.events = [];
            this.invalidateCache();
            await this.saveEvents();
        }

        if (options.persist === false) {
            return;
        }

        // Update configuration
        const config = vscode.workspace.getConfiguration('enterpriseAI');
        await config.update('privacy.allowTelemetry', enabled, vscode.ConfigurationTarget.Global);
    }

    /**
     * Check if analytics is enabled
     */
    public isEnabled(): boolean {
        return this.enabled;
    }

    /**
     * Clean old events based on retention policy
     */
    private cleanOldEvents() {
        const retentionMs = this.RETENTION_DAYS * 24 * 60 * 60 * 1000;
        const cutoffTime = Date.now() - retentionMs;

        this.events = this.events.filter(e => e.timestamp >= cutoffTime);
    }

    /**
     * Load events from storage
     */
    private loadEvents() {
        const stored = this.context.globalState.get<SuggestionEvent[]>('analyticsEvents', []);
        this.events = stored;
        this.cleanOldEvents();
    }

    /**
     * Save events to storage
     */
    private async saveEvents() {
        await this.context.globalState.update('analyticsEvents', this.events);
    }

    /**
     * Get summary statistics (with caching)
     */
    public getSummary(): {
        totalSuggestions: number;
        acceptanceRate: number;
        topAgent: string;
        topLanguage: string;
        mostProductiveHour: number;
    } {
        const cached = this.getFromCache<{
            totalSuggestions: number;
            acceptanceRate: number;
            topAgent: string;
            topLanguage: string;
            mostProductiveHour: number;
        }>(this.CACHE_KEYS.SUMMARY);
        if (cached) {
            return cached;
        }

        const rates = this.getSuggestionRates();
        const agentMetrics = this.getAgentMetrics();
        const productivity = this.getProductivityMetrics();
        const langDist = this.getLanguageDistribution();

        const result = {
            totalSuggestions: rates.total,
            acceptanceRate: rates.acceptanceRate,
            topAgent: agentMetrics[0]?.agentName || 'N/A',
            topLanguage: langDist[0]?.language || 'N/A',
            mostProductiveHour: productivity.mostProductiveHours[0] || 0
        };

        this.setCache(this.CACHE_KEYS.SUMMARY, result);
        return result;
    }

    /**
     * Get data from cache if valid
     */
    private getFromCache<T>(key: string): T | undefined {
        const entry = this.cache.get(key);
        if (!entry) {
            return undefined;
        }

        const age = Date.now() - entry.timestamp;
        if (age > this.CACHE_TTL) {
            this.cache.delete(key);
            return undefined;
        }

        return entry.data as T;
    }

    /**
     * Set data in cache
     */
    private setCache<T>(key: string, data: T): void {
        this.cache.set(key, {
            data,
            timestamp: Date.now()
        });
    }

    /**
     * Invalidate all cache entries
     */
    private invalidateCache(): void {
        this.cache.clear();
    }

    /**
     * Start periodic cache cleanup
     */
    private startCacheCleanup(): void {
        setInterval(() => {
            const now = Date.now();
            for (const [key, entry] of this.cache.entries()) {
                if (now - entry.timestamp > this.CACHE_TTL) {
                    this.cache.delete(key);
                }
            }
        }, 60000); // Clean every minute
    }

    /**
     * Dispose resources
     */
    public async dispose() {
        await this.saveEvents();
        this.cache.clear();
    }
}
