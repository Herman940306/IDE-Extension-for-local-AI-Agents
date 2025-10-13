/**
 * Enterprise AI Agents Integration - VS Code Extension
 * Project Creator: Herman Swanepoel
 */

import { v4 as uuidv4 } from 'uuid';
import * as vscode from 'vscode';
import { AgentDiscussionPanel } from './panels/AgentDiscussionPanel';
import { AICodeActionProvider } from './providers/CodeActionProvider';
import { InlineSuggestionProvider } from './providers/InlineSuggestionProvider';
import { AccessibilityManager } from './services/AccessibilityManager';
import { KeyboardNavigationManager } from './services/KeyboardNavigationManager';
import { ModeToggle, OperationMode } from './services/ModeToggle';
import { WebSocketClient } from './services/WebSocketClient';
import { AgentStatusTreeProvider } from './ui/AgentStatusTreeProvider';
import { StatusBarManager } from './ui/StatusBarManager';

let wsClient: WebSocketClient | null = null;
let accessibilityManager: AccessibilityManager | null = null;
let keyboardNavManager: KeyboardNavigationManager | null = null;
let modeToggle: ModeToggle | null = null;
let inlineSuggestionProvider: InlineSuggestionProvider | null = null;
let codeActionProvider: AICodeActionProvider | null = null;
let agentStatusProvider: AgentStatusTreeProvider | null = null;
let statusBarManager: StatusBarManager | null = null;

export function activate(context: vscode.ExtensionContext) {
    console.log('Enterprise AI Agents extension is now active!');
    console.log('Project Creator: Herman Swanepoel');

    // Initialize mode toggle (before other services)
    modeToggle = new ModeToggle(context, OperationMode.OFFLINE);

    // Initialize accessibility features
    accessibilityManager = new AccessibilityManager(context);
    keyboardNavManager = new KeyboardNavigationManager(context);

    accessibilityManager.announceToScreenReader(
        'Enterprise AI Agents extension activated. Press Ctrl+Shift+Alt+H for keyboard shortcuts.',
        'polite'
    );

    // Announce current mode
    const modeInfo = modeToggle.getModeInfo();
    accessibilityManager.announceToScreenReader(
        `Current mode: ${modeInfo.mode}. ${modeInfo.description}`,
        'polite'
    );

    const config = vscode.workspace.getConfiguration('enterpriseAI');
    const backendUrl = config.get<string>('backend.url', 'ws://localhost:8000');
    const clientId = context.globalState.get<string>('clientId') || uuidv4();

    context.globalState.update('clientId', clientId);

    wsClient = new WebSocketClient({
        url: backendUrl,
        clientId: clientId
    });

    wsClient.connect().catch(error => {
        vscode.window.showErrorMessage(`Failed to connect to backend: ${error.message}`);
    });

    wsClient.on('task_acknowledged', (payload) => {
        console.log('Task acknowledged:', payload);
    });

    wsClient.on('agent_response', (payload) => {
        console.log('Agent response received:', payload);
    });

    wsClient.on('mode_changed', (payload: any) => {
        vscode.window.showInformationMessage(`Mode changed to: ${payload.mode}`);
    });

    // Initialize providers
    inlineSuggestionProvider = new InlineSuggestionProvider(wsClient, modeToggle);
    codeActionProvider = new AICodeActionProvider(wsClient);
    agentStatusProvider = new AgentStatusTreeProvider(wsClient);

    // Initialize status bar manager
    statusBarManager = new StatusBarManager(wsClient);
    statusBarManager.setInlineSuggestionProvider(inlineSuggestionProvider);
    context.subscriptions.push(statusBarManager);

    // Register inline suggestion provider
    const inlineProvider = vscode.languages.registerInlineCompletionItemProvider(
        { pattern: '**' },
        inlineSuggestionProvider
    );
    context.subscriptions.push(inlineProvider);

    // Register code action provider
    const codeActionProviderRegistration = vscode.languages.registerCodeActionsProvider(
        { pattern: '**' },
        codeActionProvider,
        {
            providedCodeActionKinds: AICodeActionProvider.providedCodeActionKinds
        }
    );
    context.subscriptions.push(codeActionProviderRegistration);

    // Register agent status tree view
    const agentStatusTreeView = vscode.window.createTreeView('enterpriseAI.agentStatus', {
        treeDataProvider: agentStatusProvider,
        showCollapseAll: true
    });
    context.subscriptions.push(agentStatusTreeView);

    // Mode toggle is now handled by ModeToggle class
    // Register mode change callback to notify backend
    modeToggle.onModeChange(async (event) => {
        // Notify backend of mode change
        if (wsClient && wsClient.isConnectedToBackend()) {
            await wsClient.send('mode_change', {
                mode: event.mode,
                timestamp: event.timestamp
            });
        }

        // Announce to screen reader
        const modeInfo = modeToggle!.getModeInfo();
        accessibilityManager?.announceToScreenReader(
            `Switched to ${event.mode} mode. ${modeInfo.description}`,
            'assertive'
        );

        // Add to keyboard navigation history
        keyboardNavManager?.addToHistory('enterpriseAI.toggleMode');
    });

    // Suggestion tracking commands
    const suggestionAcceptedCommand = vscode.commands.registerCommand(
        'enterpriseAI.suggestionAccepted',
        (suggestion: any, index: number) => {
            inlineSuggestionProvider?.trackAcceptance(suggestion, index);
            accessibilityManager?.announceToScreenReader('Suggestion accepted', 'polite');
        }
    );

    const suggestionRejectedCommand = vscode.commands.registerCommand(
        'enterpriseAI.suggestionRejected',
        (suggestion: any, index: number) => {
            inlineSuggestionProvider?.trackRejection(suggestion, index);
            accessibilityManager?.announceToScreenReader('Suggestion rejected', 'polite');
        }
    );

    const requestAlternativesCommand = vscode.commands.registerCommand(
        'enterpriseAI.requestAlternatives',
        async () => {
            const editor = vscode.window.activeTextEditor;
            if (editor && inlineSuggestionProvider) {
                await inlineSuggestionProvider.requestAlternatives(
                    editor.document,
                    editor.selection.active
                );
                accessibilityManager?.announceToScreenReader('Requesting alternative suggestions', 'polite');
            }
        }
    );

    const viewSuggestionStatsCommand = vscode.commands.registerCommand(
        'enterpriseAI.viewSuggestionStats',
        () => {
            if (inlineSuggestionProvider) {
                const stats = inlineSuggestionProvider.getStatistics();
                vscode.window.showInformationMessage(
                    `Suggestions: ${stats.generated} generated, ${stats.accepted} accepted (${Math.round(stats.acceptanceRate * 100)}% rate), Cache: ${Math.round(stats.cacheHitRate * 100)}% hit rate`
                );
            }
        }
    );

    const showQuickActionsCommand = vscode.commands.registerCommand(
        'enterpriseAI.showQuickActions',
        () => {
            statusBarManager?.showQuickActions();
        }
    );

    // Code action commands
    const extractFunctionCommand = vscode.commands.registerCommand(
        'enterpriseAI.extractFunction',
        async (document: vscode.TextDocument, range: vscode.Range) => {
            await codeActionProvider?.applyCodeAction(document, 'extract_function', range);
        }
    );

    const simplifyCodeCommand = vscode.commands.registerCommand(
        'enterpriseAI.simplifyCode',
        async (document: vscode.TextDocument, range: vscode.Range) => {
            await codeActionProvider?.applyCodeAction(document, 'simplify', range);
        }
    );

    const optimizeCodeCommand = vscode.commands.registerCommand(
        'enterpriseAI.optimizeCode',
        async (document: vscode.TextDocument, range: vscode.Range) => {
            await codeActionProvider?.applyCodeAction(document, 'optimize', range);
        }
    );

    const improveNamingCommand = vscode.commands.registerCommand(
        'enterpriseAI.improveNaming',
        async (document: vscode.TextDocument, range: vscode.Range) => {
            await codeActionProvider?.applyCodeAction(document, 'improve_naming', range);
        }
    );

    const fixDiagnosticsCommand = vscode.commands.registerCommand(
        'enterpriseAI.fixDiagnostics',
        async (document: vscode.TextDocument, diagnostics: vscode.Diagnostic[], type: string) => {
            await codeActionProvider?.applyCodeAction(document, `fix_${type}`, undefined, diagnostics);
        }
    );

    const rollbackActionCommand = vscode.commands.registerCommand(
        'enterpriseAI.rollbackAction',
        async () => {
            const success = await codeActionProvider?.rollbackLastAction();
            if (success) {
                accessibilityManager?.announceToScreenReader('Action rolled back successfully', 'polite');
            }
        }
    );

    const accessibilitySettingsCommand = vscode.commands.registerCommand(
        'enterpriseAI.accessibility.showSettings',
        () => {
            accessibilityManager?.showSettings();
        }
    );

    const refreshAgentStatusCommand = vscode.commands.registerCommand(
        'enterpriseAI.refreshAgentStatus',
        () => {
            agentStatusProvider?.refreshAgentStatus();
            accessibilityManager?.announceToScreenReader('Refreshing agent status', 'polite');
        }
    );

    const showAgentDetailsCommand = vscode.commands.registerCommand(
        'enterpriseAI.showAgentDetails',
        (agent: any) => {
            vscode.window.showInformationMessage(
                `${agent.name}\nStatus: ${agent.status}\nTasks: ${agent.tasksCompleted || 0}\nSuccess Rate: ${Math.round((agent.successRate || 0) * 100)}%`
            );
        }
    );

    const generateTestsCommand = vscode.commands.registerCommand(
        'enterpriseAI.generateTests',
        () => {
            vscode.window.showInformationMessage('Generate tests not yet implemented');
        }
    );

    const refactorSelectionCommand = vscode.commands.registerCommand(
        'enterpriseAI.refactorSelection',
        () => {
            vscode.window.showInformationMessage('Refactor selection not yet implemented');
        }
    );

    const explainCodeCommand = vscode.commands.registerCommand(
        'enterpriseAI.explainCode',
        () => {
            vscode.window.showInformationMessage('Explain code not yet implemented');
        }
    );

    const findSecurityIssuesCommand = vscode.commands.registerCommand(
        'enterpriseAI.findSecurityIssues',
        async (document?: vscode.TextDocument, range?: vscode.Range) => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showWarningMessage('No active editor');
                return;
            }

            const doc = document || editor.document;
            const rng = range || editor.selection;

            await codeActionProvider?.applyCodeAction(doc, 'security', rng);
        }
    );

    const generateDocumentationCommand = vscode.commands.registerCommand(
        'enterpriseAI.generateDocumentation',
        () => {
            vscode.window.showInformationMessage('Generate documentation not yet implemented');
        }
    );

    const startAgentDiscussionCommand = vscode.commands.registerCommand(
        'enterpriseAI.startAgentDiscussion',
        async () => {
            if (!wsClient) {
                vscode.window.showErrorMessage('Backend not connected');
                return;
            }

            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showWarningMessage('No active editor');
                return;
            }

            // Prompt for discussion title
            const title = await vscode.window.showInputBox({
                prompt: 'Enter discussion title',
                placeHolder: 'e.g., "Refactor authentication logic"',
                value: `Discussion about ${editor.document.fileName.split('/').pop()}`
            });

            if (!title) {
                return;
            }

            // Create or show panel
            AgentDiscussionPanel.createOrShow(context.extensionUri, wsClient);

            // Start discussion with selected code or current file
            const selection = editor.selection;
            const taskId = `task-${Date.now()}`;

            if (AgentDiscussionPanel.currentPanel) {
                AgentDiscussionPanel.currentPanel.startDiscussion(taskId, title);
            }

            accessibilityManager?.announceToScreenReader(`Started agent discussion: ${title}`, 'polite');
        }
    );

    const viewAnalyticsCommand = vscode.commands.registerCommand(
        'enterpriseAI.viewAnalytics',
        () => {
            vscode.window.showInformationMessage('View analytics not yet implemented');
        }
    );

    const reindexCodebaseCommand = vscode.commands.registerCommand(
        'enterpriseAI.reindexCodebase',
        () => {
            vscode.window.showInformationMessage('Reindex codebase not yet implemented');
        }
    );

    context.subscriptions.push(
        suggestionAcceptedCommand,
        suggestionRejectedCommand,
        requestAlternativesCommand,
        viewSuggestionStatsCommand,
        showQuickActionsCommand,
        extractFunctionCommand,
        simplifyCodeCommand,
        optimizeCodeCommand,
        improveNamingCommand,
        fixDiagnosticsCommand,
        rollbackActionCommand,
        generateTestsCommand,
        refactorSelectionCommand,
        explainCodeCommand,
        findSecurityIssuesCommand,
        generateDocumentationCommand,
        startAgentDiscussionCommand,
        viewAnalyticsCommand,
        reindexCodebaseCommand,
        accessibilitySettingsCommand,
        refreshAgentStatusCommand,
        showAgentDetailsCommand
    );

    if (wsClient) {
        context.subscriptions.push({
            dispose: () => wsClient?.dispose()
        });
    }
}

export function deactivate() {
    console.log('Enterprise AI Agents extension is now deactivated');

    if (inlineSuggestionProvider) {
        inlineSuggestionProvider.dispose();
    }

    if (codeActionProvider) {
        codeActionProvider.dispose();
    }

    if (accessibilityManager) {
        accessibilityManager.announceToScreenReader('Enterprise AI Agents extension deactivated', 'polite');
        accessibilityManager.dispose();
    }

    if (keyboardNavManager) {
        keyboardNavManager.dispose();
    }

    if (modeToggle) {
        modeToggle.dispose();
    }

    if (statusBarManager) {
        statusBarManager.dispose();
    }

    if (wsClient) {
        wsClient.disconnect();
    }
}
