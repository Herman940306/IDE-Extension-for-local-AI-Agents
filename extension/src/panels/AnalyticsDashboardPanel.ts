/**
 * Analytics Dashboard Panel - Productivity insights and metrics
 * Project Creator: Herman Swanepoel
 */

import * as vscode from 'vscode';
import { AnalyticsService } from '../services/AnalyticsService';

export class AnalyticsDashboardPanel {
    public static currentPanel: AnalyticsDashboardPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private _disposables: vscode.Disposable[] = [];
    private analyticsService: AnalyticsService;

    public static createOrShow(extensionUri: vscode.Uri, analyticsService: AnalyticsService) {
        const column = vscode.ViewColumn.Two;

        // If we already have a panel, show it
        if (AnalyticsDashboardPanel.currentPanel) {
            AnalyticsDashboardPanel.currentPanel._panel.reveal(column);
            return;
        }

        // Otherwise, create a new panel
        const panel = vscode.window.createWebviewPanel(
            'analyticsDashboard',
            'AI Analytics Dashboard',
            column,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: [extensionUri]
            }
        );

        AnalyticsDashboardPanel.currentPanel = new AnalyticsDashboardPanel(
            panel,
            extensionUri,
            analyticsService
        );
    }

    private constructor(
        panel: vscode.WebviewPanel,
        _extensionUri: vscode.Uri,
        analyticsService: AnalyticsService
    ) {
        this._panel = panel;
        this.analyticsService = analyticsService;

        // Set the webview's initial html content
        this._update();

        // Listen for when the panel is disposed
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);

        // Handle messages from the webview
        this._panel.webview.onDidReceiveMessage(
            message => {
                switch (message.command) {
                    case 'refresh':
                        this._update();
                        break;
                    case 'export':
                        this._exportData();
                        break;
                    case 'clear':
                        this._clearData();
                        break;
                }
            },
            null,
            this._disposables
        );
    }

    /**
     * Update the webview content
     */
    private _update() {
        this._panel.webview.html = this._getHtmlForWebview();
    }

    /**
     * Export analytics data
     */
    private async _exportData() {
        const data = this.analyticsService.exportData();
        const doc = await vscode.workspace.openTextDocument({
            content: data,
            language: 'json'
        });
        await vscode.window.showTextDocument(doc);
    }

    /**
     * Clear analytics data
     */
    private async _clearData() {
        const choice = await vscode.window.showWarningMessage(
            'Are you sure you want to clear all analytics data?',
            { modal: true },
            'Clear',
            'Cancel'
        );

        if (choice === 'Clear') {
            await this.analyticsService.clearData();
            this._update();
            vscode.window.showInformationMessage('Analytics data cleared');
        }
    }

    /**
     * Get HTML content for webview
     */
    private _getHtmlForWebview() {
        const summary = this.analyticsService.getSummary();
        const rates = this.analyticsService.getSuggestionRates();
        const agentMetrics = this.analyticsService.getAgentMetrics();
        const patterns = this.analyticsService.analyzeWorkflowPatterns();
        const timeSeriesData = this.analyticsService.getTimeSeriesData(7);
        const languageDistribution = this.analyticsService.getLanguageDistribution();
        const hourlyActivity = this.analyticsService.getHourlyActivity();

        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Analytics Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: var(--vscode-font-family);
            font-size: var(--vscode-font-size);
            color: var(--vscode-foreground);
            background-color: var(--vscode-editor-background);
            padding: 20px;
            line-height: 1.6;
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid var(--vscode-panel-border);
        }

        h1 {
            font-size: 2em;
            font-weight: 600;
        }

        .actions {
            display: flex;
            gap: 10px;
        }

        button {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9em;
            font-weight: 600;
            transition: opacity 0.2s;
        }

        button:hover {
            opacity: 0.8;
        }

        button.primary {
            background-color: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
        }

        button.secondary {
            background-color: var(--vscode-button-secondaryBackground);
            color: var(--vscode-button-secondaryForeground);
        }

        .summary-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .card {
            background-color: var(--vscode-editor-inactiveSelectionBackground);
            border-radius: 8px;
            padding: 20px;
            border-left: 4px solid var(--vscode-textLink-foreground);
        }

        .card-title {
            font-size: 0.9em;
            color: var(--vscode-descriptionForeground);
            margin-bottom: 10px;
        }

        .card-value {
            font-size: 2em;
            font-weight: 700;
            color: var(--vscode-textLink-foreground);
        }

        .card-subtitle {
            font-size: 0.85em;
            color: var(--vscode-descriptionForeground);
            margin-top: 5px;
        }

        .section {
            margin-bottom: 40px;
        }

        .section-title {
            font-size: 1.5em;
            font-weight: 600;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .chart-container {
            background-color: var(--vscode-editor-inactiveSelectionBackground);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }

        .chart-wrapper {
            position: relative;
            height: 300px;
        }

        .agent-list {
            display: grid;
            gap: 15px;
            role: list;
        }

        .agent-item {
            background-color: var(--vscode-editor-inactiveSelectionBackground);
            border-radius: 8px;
            padding: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            outline: none;
        }

        .agent-item:focus {
            outline: 2px solid var(--vscode-focusBorder);
            outline-offset: 2px;
        }

        .agent-info {
            flex: 1;
        }

        .agent-name {
            font-weight: 600;
            font-size: 1.1em;
            margin-bottom: 5px;
        }

        .agent-stats {
            display: flex;
            gap: 20px;
            font-size: 0.9em;
            color: var(--vscode-descriptionForeground);
        }

        .agent-rate {
            font-size: 1.5em;
            font-weight: 700;
            color: var(--vscode-testing-iconPassed);
        }

        .pattern-list {
            display: grid;
            gap: 15px;
            role: list;
        }

        .pattern-item {
            background-color: var(--vscode-editor-inactiveSelectionBackground);
            border-radius: 8px;
            padding: 15px;
            border-left: 4px solid var(--vscode-testing-iconQueued);
            outline: none;
        }

        .pattern-item:focus {
            outline: 2px solid var(--vscode-focusBorder);
            outline-offset: 2px;
        }

        .pattern-title {
            font-weight: 600;
            margin-bottom: 5px;
        }

        .pattern-suggestion {
            color: var(--vscode-descriptionForeground);
            font-size: 0.9em;
            margin-top: 5px;
        }

        .grid-2 {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
        }

        @media (max-width: 900px) {
            .grid-2 {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 AI Analytics Dashboard</h1>
        <div class="actions">
            <button class="primary" onclick="refresh()" aria-label="Refresh analytics data">🔄 Refresh</button>
            <button class="secondary" onclick="exportData()" aria-label="Export analytics data as JSON">📥 Export</button>
            <button class="secondary" onclick="clearData()" aria-label="Clear all analytics data">🗑️ Clear</button>
        </div>
    </div>

    <!-- Summary Cards -->
    <div class="summary-cards">
        <div class="card">
            <div class="card-title">Total Suggestions</div>
            <div class="card-value">${summary.totalSuggestions}</div>
            <div class="card-subtitle">All time</div>
        </div>
        <div class="card">
            <div class="card-title">Acceptance Rate</div>
            <div class="card-value">${Math.round(summary.acceptanceRate * 100)}%</div>
            <div class="card-subtitle">${rates.accepted} accepted / ${rates.rejected} rejected</div>
        </div>
        <div class="card">
            <div class="card-title">Top Agent</div>
            <div class="card-value" style="font-size: 1.2em;">${summary.topAgent}</div>
            <div class="card-subtitle">Most effective</div>
        </div>
        <div class="card">
            <div class="card-title">Top Language</div>
            <div class="card-value" style="font-size: 1.2em;">${summary.topLanguage}</div>
            <div class="card-subtitle">Most used</div>
        </div>
        <div class="card">
            <div class="card-title">Peak Hour</div>
            <div class="card-value">${summary.mostProductiveHour}:00</div>
            <div class="card-subtitle">Most productive</div>
        </div>
    </div>

    <!-- Charts -->
    <div class="grid-2">
        <!-- Time Series Chart -->
        <div class="section">
            <div class="section-title">📈 Suggestion Trends (7 Days)</div>
            <div class="chart-container">
                <div class="chart-wrapper">
                    <canvas id="timeSeriesChart" role="img" aria-label="Line chart showing accepted and rejected suggestion trends over the past 7 days"></canvas>
                </div>
            </div>
        </div>

        <!-- Language Distribution -->
        <div class="section">
            <div class="section-title">💻 Language Distribution</div>
            <div class="chart-container">
                <div class="chart-wrapper">
                    <canvas id="languageChart" role="img" aria-label="Doughnut chart showing distribution of programming languages used"></canvas>
                </div>
            </div>
        </div>
    </div>

    <!-- Hourly Activity Heatmap -->
    <div class="section">
        <div class="section-title">🕐 Hourly Activity</div>
        <div class="chart-container">
            <div class="chart-wrapper">
                <canvas id="hourlyChart" role="img" aria-label="Bar chart showing hourly activity distribution throughout the day"></canvas>
            </div>
        </div>
    </div>

    <!-- Agent Effectiveness -->
    <div class="section">
        <div class="section-title">🤖 Agent Effectiveness</div>
        <div class="agent-list">
            ${agentMetrics.map(agent => `
                <div class="agent-item" role="listitem" tabindex="0" aria-label="${agent.agentName} agent with ${Math.round(agent.acceptanceRate * 100)}% acceptance rate">
                    <div class="agent-info">
                        <div class="agent-name">${agent.agentName}</div>
                        <div class="agent-stats">
                            <span>Total: ${agent.totalSuggestions}</span>
                            <span>Accepted: ${agent.acceptedSuggestions}</span>
                            <span>Confidence: ${Math.round(agent.averageConfidence * 100)}%</span>
                        </div>
                    </div>
                    <div class="agent-rate">${Math.round(agent.acceptanceRate * 100)}%</div>
                </div>
            `).join('')}
        </div>
    </div>

    <!-- Workflow Patterns -->
    <div class="section">
        <div class="section-title">💡 Workflow Insights</div>
        <div class="pattern-list">
            ${patterns.map(pattern => `
                <div class="pattern-item" role="listitem" tabindex="0" aria-label="${pattern.pattern} pattern with frequency ${pattern.frequency}">
                    <div class="pattern-title">${pattern.pattern}</div>
                    <div>Frequency: ${pattern.frequency}</div>
                    ${pattern.suggestion ? `<div class="pattern-suggestion">💡 ${pattern.suggestion}</div>` : ''}
                </div>
            `).join('')}
        </div>
    </div>

    <script>
        const vscode = acquireVsCodeApi();

        function refresh() {
            vscode.postMessage({ command: 'refresh' });
        }

        function exportData() {
            vscode.postMessage({ command: 'export' });
        }

        function clearData() {
            vscode.postMessage({ command: 'clear' });
        }

        // Time Series Chart
        const timeSeriesCtx = document.getElementById('timeSeriesChart').getContext('2d');
        new Chart(timeSeriesCtx, {
            type: 'line',
            data: {
                labels: ${JSON.stringify(timeSeriesData.labels)},
                datasets: [
                    {
                        label: 'Accepted',
                        data: ${JSON.stringify(timeSeriesData.accepted)},
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.4
                    },
                    {
                        label: 'Rejected',
                        data: ${JSON.stringify(timeSeriesData.rejected)},
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { color: 'var(--vscode-foreground)' }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { color: 'var(--vscode-foreground)' },
                        grid: { color: 'rgba(128, 128, 128, 0.2)' }
                    },
                    x: {
                        ticks: { color: 'var(--vscode-foreground)' },
                        grid: { color: 'rgba(128, 128, 128, 0.2)' }
                    }
                }
            }
        });

        // Language Distribution Chart
        const languageCtx = document.getElementById('languageChart').getContext('2d');
        new Chart(languageCtx, {
            type: 'doughnut',
            data: {
                labels: ${JSON.stringify(languageDistribution.map(l => l.language))},
                datasets: [{
                    data: ${JSON.stringify(languageDistribution.map(l => l.count))},
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.8)',
                        'rgba(54, 162, 235, 0.8)',
                        'rgba(255, 206, 86, 0.8)',
                        'rgba(75, 192, 192, 0.8)',
                        'rgba(153, 102, 255, 0.8)',
                        'rgba(255, 159, 64, 0.8)'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { color: 'var(--vscode-foreground)' }
                    }
                }
            }
        });

        // Hourly Activity Chart
        const hourlyCtx = document.getElementById('hourlyChart').getContext('2d');
        new Chart(hourlyCtx, {
            type: 'bar',
            data: {
                labels: ${JSON.stringify(hourlyActivity.map(h => `${h.hour}:00`))},
                datasets: [{
                    label: 'Suggestions',
                    data: ${JSON.stringify(hourlyActivity.map(h => h.count))},
                    backgroundColor: 'rgba(54, 162, 235, 0.8)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { color: 'var(--vscode-foreground)' }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { color: 'var(--vscode-foreground)' },
                        grid: { color: 'rgba(128, 128, 128, 0.2)' }
                    },
                    x: {
                        ticks: { color: 'var(--vscode-foreground)', maxRotation: 45, minRotation: 45 },
                        grid: { color: 'rgba(128, 128, 128, 0.2)' }
                    }
                }
            }
        });
    </script>
</body>
</html>`;
    }

    /**
     * Dispose panel
     */
    public dispose() {
        AnalyticsDashboardPanel.currentPanel = undefined;

        // Clean up resources
        this._panel.dispose();

        while (this._disposables.length) {
            const disposable = this._disposables.pop();
            if (disposable) {
                disposable.dispose();
            }
        }
    }
}
