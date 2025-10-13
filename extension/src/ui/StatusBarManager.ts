/**
 * Status Bar Manager - AI Agent Status Display
 * Project Creator: Herman Swanepoel
 */

import * as vscode from 'vscode';
import { InlineSuggestionProvider } from '../providers/InlineSuggestionProvider';
import { WebSocketClient } from '../services/WebSocketClient';

export class StatusBarManager {
    private statusBarItem: vscode.StatusBarItem;
    private suggestionStatsItem: vscode.StatusBarItem;
    private wsClient: WebSocketClient;
    private inlineSuggestionProvider: InlineSuggestionProvider | null = null;
    private updateInterval: NodeJS.Timeout | null = null;

    constructor(wsClient: WebSocketClient) {
        this.wsClient = wsClient;

        // Create main status bar item (left side)
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Left,
            100
        );
        this.statusBarItem.command = 'enterpriseAI.showQuickActions';
        this.statusBarItem.tooltip = 'Enterprise AI Agents - Click for quick actions';

        // Create suggestion stats item (right side)
        this.suggestionStatsItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            100
        );
        this.suggestionStatsItem.command = 'enterpriseAI.viewSuggestionStats';
        this.suggestionStatsItem.tooltip = 'AI Suggestion Statistics';

        // Initialize
        this.updateStatus();
        this.updateSuggestionStats();

        // Update every 5 seconds
        this.updateInterval = setInterval(() => {
            this.updateStatus();
            this.updateSuggestionStats();
        }, 5000);

        // Listen for backend connection changes
        this.wsClient.on('connected', () => {
            this.updateStatus();
        });

        this.wsClient.on('disconnected', () => {
            this.updateStatus();
        });

        // Show items
        this.statusBarItem.show();
        this.suggestionStatsItem.show();
    }

    /**
     * Set inline suggestion provider for stats
     */
    public setInlineSuggestionProvider(provider: InlineSuggestionProvider) {
        this.inlineSuggestionProvider = provider;
        this.updateSuggestionStats();
    }

    /**
     * Update main status
     */
    private updateStatus() {
        const isConnected = this.wsClient.isConnectedToBackend();

        if (isConnected) {
            this.statusBarItem.text = '$(robot) AI Agents';
            this.statusBarItem.backgroundColor = undefined;
            this.statusBarItem.color = new vscode.ThemeColor('statusBarItem.prominentForeground');
        } else {
            this.statusBarItem.text = '$(robot) AI Agents (Offline)';
            this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
            this.statusBarItem.color = new vscode.ThemeColor('statusBarItem.warningForeground');
        }
    }

    /**
     * Update suggestion statistics
     */
    private updateSuggestionStats() {
        if (!this.inlineSuggestionProvider) {
            this.suggestionStatsItem.text = '$(lightbulb) --';
            return;
        }

        const stats = this.inlineSuggestionProvider.getStatistics();
        const acceptanceRate = Math.round(stats.acceptanceRate * 100);

        if (stats.generated === 0) {
            this.suggestionStatsItem.text = '$(lightbulb) No suggestions yet';
        } else {
            this.suggestionStatsItem.text = `$(lightbulb) ${stats.accepted}/${stats.generated} (${acceptanceRate}%)`;
        }

        this.suggestionStatsItem.tooltip =
            `AI Suggestions\n` +
            `Generated: ${stats.generated}\n` +
            `Accepted: ${stats.accepted}\n` +
            `Rejected: ${stats.rejected}\n` +
            `Acceptance Rate: ${acceptanceRate}%\n` +
            `Cache Hit Rate: ${Math.round(stats.cacheHitRate * 100)}%`;
    }

    /**
     * Show quick actions menu
     */
    public async showQuickActions() {
        const items: vscode.QuickPickItem[] = [
            {
                label: '$(comment-discussion) Start Agent Discussion',
                description: 'Collaborate with multiple AI agents',
                detail: 'Get input from specialized agents on your code'
            },
            {
                label: '$(beaker) Generate Tests',
                description: 'Create unit tests for current file',
                detail: 'AI-powered test generation'
            },
            {
                label: '$(wand) Refactor Selection',
                description: 'Improve selected code',
                detail: 'Get refactoring suggestions'
            },
            {
                label: '$(shield) Find Security Issues',
                description: 'Scan for vulnerabilities',
                detail: 'Security analysis and fixes'
            },
            {
                label: '$(book) Generate Documentation',
                description: 'Create docs for your code',
                detail: 'Automated documentation generation'
            },
            {
                label: '$(zap) Optimize Code',
                description: 'Improve performance',
                detail: 'AI-powered optimization'
            },
            {
                label: '$(history) Rollback Last Action',
                description: 'Undo last AI change',
                detail: 'Restore previous state'
            },
            {
                label: '$(graph) View Analytics',
                description: 'See productivity insights',
                detail: 'Track AI effectiveness'
            },
            {
                label: '$(refresh) Reindex Codebase',
                description: 'Update code embeddings',
                detail: 'Refresh AI context'
            }
        ];

        const selected = await vscode.window.showQuickPick(items, {
            placeHolder: 'Select an AI action',
            matchOnDescription: true,
            matchOnDetail: true
        });

        if (selected) {
            switch (selected.label) {
                case '$(comment-discussion) Start Agent Discussion':
                    vscode.commands.executeCommand('enterpriseAI.startAgentDiscussion');
                    break;
                case '$(beaker) Generate Tests':
                    vscode.commands.executeCommand('enterpriseAI.generateTests');
                    break;
                case '$(wand) Refactor Selection':
                    vscode.commands.executeCommand('enterpriseAI.refactorSelection');
                    break;
                case '$(shield) Find Security Issues':
                    vscode.commands.executeCommand('enterpriseAI.findSecurityIssues');
                    break;
                case '$(book) Generate Documentation':
                    vscode.commands.executeCommand('enterpriseAI.generateDocumentation');
                    break;
                case '$(zap) Optimize Code':
                    vscode.commands.executeCommand('enterpriseAI.optimizeCode');
                    break;
                case '$(history) Rollback Last Action':
                    vscode.commands.executeCommand('enterpriseAI.rollbackAction');
                    break;
                case '$(graph) View Analytics':
                    vscode.commands.executeCommand('enterpriseAI.viewAnalytics');
                    break;
                case '$(refresh) Reindex Codebase':
                    vscode.commands.executeCommand('enterpriseAI.reindexCodebase');
                    break;
            }
        }
    }

    /**
     * Dispose resources
     */
    public dispose() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        this.statusBarItem.dispose();
        this.suggestionStatsItem.dispose();
    }
}
