/**
 * Inline suggestion provider for real-time code completions
 * Project Creator: Herman Swanepoel
 */

import * as vscode from 'vscode';
import { WebSocketClient } from '../services/WebSocketClient';
import { ModeToggle } from '../services/ModeToggle';

interface SuggestionRequest {
    file_path: string;
    language: string;
    cursor_position: { line: number; character: number };
    surrounding_code: string;
    selected_text?: string;
}

interface AgentSuggestion {
    code: string;
    description: string;
    confidence: number;
    reasoning?: string;
}

interface SuggestionCache {
    key: string;
    suggestions: vscode.InlineCompletionItem[];
    timestamp: number;
}

export class InlineSuggestionProvider implements vscode.InlineCompletionItemProvider {
    private wsClient: WebSocketClient;
    private modeToggle: ModeToggle;
    private debounceTimer: NodeJS.Timeout | null = null;
    private readonly DEBOUNCE_DELAY = 200; // ms
    private cache: Map<string, SuggestionCache> = new Map();
    private readonly CACHE_TTL = 5000; // 5 seconds
    private pendingRequests: Map<string, Promise<vscode.InlineCompletionItem[]>> = new Map();
    
    // Statistics
    private suggestionsGenerated = 0;
    private suggestionsAccepted = 0;
    private suggestionsRejected = 0;
    private cacheHits = 0;
    private cacheMisses = 0;

    constructor(wsClient: WebSocketClient, modeToggle: ModeToggle) {
        this.wsClient = wsClient;
        this.modeToggle = modeToggle;
    }

    /**
     * Provide inline completion items
     */
    async provideInlineCompletionItems(
        document: vscode.TextDocument,
        position: vscode.Position,
        context: vscode.InlineCompletionContext,
        token: vscode.CancellationToken
    ): Promise<vscode.InlineCompletionItem[] | vscode.InlineCompletionList | null> {
        // Check if backend is connected
        if (!this.wsClient.isConnectedToBackend()) {
            return null;
        }

        // Generate cache key
        const cacheKey = this._generateCacheKey(document, position);

        // Check cache first
        const cached = this._getFromCache(cacheKey);
        if (cached) {
            this.cacheHits++;
            return cached;
        }

        this.cacheMisses++;

        // Check if there's already a pending request for this position
        const pending = this.pendingRequests.get(cacheKey);
        if (pending) {
            return pending;
        }

        // Create new request promise
        const requestPromise = this._fetchSuggestions(document, position, token);
        this.pendingRequests.set(cacheKey, requestPromise);

        try {
            const suggestions = await requestPromise;
            
            // Cache the result
            if (suggestions.length > 0) {
                this._addToCache(cacheKey, suggestions);
            }

            return suggestions;
        } finally {
            this.pendingRequests.delete(cacheKey);
        }
    }

    /**
     * Fetch suggestions from backend
     */
    private async _fetchSuggestions(
        document: vscode.TextDocument,
        position: vscode.Position,
        token: vscode.CancellationToken
    ): Promise<vscode.InlineCompletionItem[]> {
        return new Promise((resolve) => {
            // Debounce to avoid excessive requests
            if (this.debounceTimer) {
                clearTimeout(this.debounceTimer);
            }

            this.debounceTimer = setTimeout(async () => {
                // Check if cancelled
                if (token.isCancellationRequested) {
                    resolve([]);
                    return;
                }

                try {
                    // Get surrounding code
                    const surroundingCode = this._getSurroundingCode(document, position);

                    // Create request
                    const request: SuggestionRequest = {
                        file_path: document.fileName,
                        language: document.languageId,
                        cursor_position: {
                            line: position.line,
                            character: position.character
                        },
                        surrounding_code: surroundingCode
                    };

                    // Send request to backend
                    const response = await this.wsClient.sendWithResponse('inline_suggestion', request, 5000);

                    if (response && response.suggestions) {
                        const suggestions = this._convertToInlineCompletions(
                            response.suggestions,
                            position
                        );
                        
                        this.suggestionsGenerated += suggestions.length;
                        resolve(suggestions);
                    } else {
                        resolve([]);
                    }
                } catch (error) {
                    console.error('Failed to fetch suggestions:', error);
                    resolve([]);
                }
            }, this.DEBOUNCE_DELAY);
        });
    }

    /**
     * Convert agent suggestions to VS Code inline completions
     */
    private _convertToInlineCompletions(
        suggestions: AgentSuggestion[],
        position: vscode.Position
    ): vscode.InlineCompletionItem[] {
        return suggestions.map((suggestion, index) => {
            const item = new vscode.InlineCompletionItem(
                suggestion.code,
                new vscode.Range(position, position)
            );

            // Create command to track acceptance
            item.command = {
                command: 'enterpriseAI.suggestionAccepted',
                title: 'Track Suggestion Acceptance',
                arguments: [suggestion, index]
            };

            return item;
        });
    }

    /**
     * Get confidence badge text
     */
    private _getConfidenceBadge(confidence: number): string {
        if (confidence >= 0.8) {
            return '🟢 High';
        } else if (confidence >= 0.5) {
            return '🟡 Medium';
        } else {
            return '🔴 Low';
        }
    }

    /**
     * Get surrounding code context
     */
    private _getSurroundingCode(
        document: vscode.TextDocument,
        position: vscode.Position,
        contextLines: number = 10
    ): string {
        const startLine = Math.max(0, position.line - contextLines);
        const endLine = Math.min(document.lineCount - 1, position.line + contextLines);

        const range = new vscode.Range(
            new vscode.Position(startLine, 0),
            new vscode.Position(endLine, document.lineAt(endLine).text.length)
        );

        return document.getText(range);
    }

    /**
     * Generate cache key
     */
    private _generateCacheKey(document: vscode.TextDocument, position: vscode.Position): string {
        const lineText = document.lineAt(position.line).text;
        return `${document.fileName}:${position.line}:${position.character}:${lineText}`;
    }

    /**
     * Get suggestions from cache
     */
    private _getFromCache(key: string): vscode.InlineCompletionItem[] | null {
        const cached = this.cache.get(key);
        
        if (!cached) {
            return null;
        }

        // Check if expired
        if (Date.now() - cached.timestamp > this.CACHE_TTL) {
            this.cache.delete(key);
            return null;
        }

        return cached.suggestions;
    }

    /**
     * Add suggestions to cache
     */
    private _addToCache(key: string, suggestions: vscode.InlineCompletionItem[]): void {
        this.cache.set(key, {
            key,
            suggestions,
            timestamp: Date.now()
        });

        // Limit cache size
        if (this.cache.size > 100) {
            // Remove oldest entries
            const entries = Array.from(this.cache.entries());
            entries.sort((a, b) => a[1].timestamp - b[1].timestamp);
            
            for (let i = 0; i < 20; i++) {
                this.cache.delete(entries[i][0]);
            }
        }
    }

    /**
     * Clear cache
     */
    public clearCache(): void {
        this.cache.clear();
    }

    /**
     * Track suggestion acceptance
     */
    public trackAcceptance(suggestion: AgentSuggestion, index: number): void {
        this.suggestionsAccepted++;
        
        // Send feedback to backend
        this.wsClient.send('suggestion_feedback', {
            suggestion,
            index,
            accepted: true,
            timestamp: Date.now()
        }).catch(error => {
            console.error('Failed to send acceptance feedback:', error);
        });
    }

    /**
     * Track suggestion rejection
     */
    public trackRejection(suggestion: AgentSuggestion, index: number): void {
        this.suggestionsRejected++;
        
        // Send feedback to backend
        this.wsClient.send('suggestion_feedback', {
            suggestion,
            index,
            accepted: false,
            timestamp: Date.now()
        }).catch(error => {
            console.error('Failed to send rejection feedback:', error);
        });
    }

    /**
     * Request alternative suggestions
     */
    public async requestAlternatives(
        document: vscode.TextDocument,
        position: vscode.Position
    ): Promise<void> {
        // Clear cache for this position
        const cacheKey = this._generateCacheKey(document, position);
        this.cache.delete(cacheKey);

        // Trigger new suggestions
        const token = new vscode.CancellationTokenSource().token;
        await this._fetchSuggestions(document, position, token);
    }

    /**
     * Get statistics
     */
    public getStatistics(): {
        generated: number;
        accepted: number;
        rejected: number;
        acceptanceRate: number;
        cacheHits: number;
        cacheMisses: number;
        cacheHitRate: number;
    } {
        const total = this.suggestionsAccepted + this.suggestionsRejected;
        const acceptanceRate = total > 0 ? this.suggestionsAccepted / total : 0;
        
        const totalCacheRequests = this.cacheHits + this.cacheMisses;
        const cacheHitRate = totalCacheRequests > 0 ? this.cacheHits / totalCacheRequests : 0;

        return {
            generated: this.suggestionsGenerated,
            accepted: this.suggestionsAccepted,
            rejected: this.suggestionsRejected,
            acceptanceRate: Math.round(acceptanceRate * 100) / 100,
            cacheHits: this.cacheHits,
            cacheMisses: this.cacheMisses,
            cacheHitRate: Math.round(cacheHitRate * 100) / 100
        };
    }

    /**
     * Reset statistics
     */
    public resetStatistics(): void {
        this.suggestionsGenerated = 0;
        this.suggestionsAccepted = 0;
        this.suggestionsRejected = 0;
        this.cacheHits = 0;
        this.cacheMisses = 0;
    }

    /**
     * Dispose resources
     */
    public dispose(): void {
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }
        this.cache.clear();
        this.pendingRequests.clear();
    }
}
