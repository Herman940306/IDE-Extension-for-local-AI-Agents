/**
 * Code action provider for quick fixes and refactoring
 * Project Creator: Herman Swanepoel
 */

import * as vscode from 'vscode';
import { WebSocketClient } from '../services/WebSocketClient';
import { ModeToggle } from '../services/ModeToggle';

interface CodeActionRequest {
    file_path: string;
    language: string;
    range: { start: { line: number; character: number }; end: { line: number; character: number } };
    code: string;
    diagnostics?: vscode.Diagnostic[];
    action_type: 'refactor' | 'quickfix' | 'security' | 'test' | 'documentation';
}

interface AgentCodeAction {
    title: string;
    kind: string;
    edit?: vscode.WorkspaceEdit;
    command?: vscode.Command;
    isPreferred?: boolean;
    diagnostics?: vscode.Diagnostic[];
}

export class CodeActionProvider implements vscode.CodeActionProvider {
    private wsClient: WebSocketClient;
    private modeToggle: ModeToggle;
    private actionCache: Map<string, vscode.CodeAction[]> = new Map();
    private readonly CACHE_TTL = 10000; // 10 seconds
    
    // Statistics
    private actionsGenerated = 0;
    private actionsApplied = 0;
    private actionsPreviewed = 0;

    public static readonly providedCodeActionKinds = [
        vscode.CodeActionKind.QuickFix,
        vscode.CodeActionKind.Refactor,
        vscode.CodeActionKind.RefactorExtract,
        vscode.CodeActionKind.RefactorInline,
        vscode.CodeActionKind.RefactorRewrite,
        vscode.CodeActionKind.Source,
        vscode.CodeActionKind.SourceFixAll
    ];

    constructor(wsClient: WebSocketClient, modeToggle: ModeToggle) {
        this.wsClient = wsClient;
        this.modeToggle = modeToggle;
    }

    /**
     * Provide code actions for the given range
     */
    public async provideCodeActions(
        document: vscode.TextDocument,
        range: vscode.Range | vscode.Selection,
        context: vscode.CodeActionContext,
        token: vscode.CancellationToken
    ): Promise<vscode.CodeAction[] | undefined> {
        // Check if backend is connected
        if (!this.wsClient.isConnectedToBackend()) {
            return undefined;
        }

        // Generate cache key
        const cacheKey = this._generateCacheKey(document, range);
        
        // Check cache
        const cached = this._getFromCache(cacheKey);
        if (cached) {
            return cached;
        }

        const actions: vscode.CodeAction[] = [];

        // Add refactoring actions
        if (range.isEmpty || !range.isSingleLine) {
            actions.push(...await this._createRefactorActions(document, range, token));
        }

        // Add quick fix actions for diagnostics
        if (context.diagnostics && context.diagnostics.length > 0) {
            actions.push(...await this._createQuickFixActions(document, range, context.diagnostics, token));
        }

        // Add security fix actions
        actions.push(...await this._createSecurityActions(document, range, token));

        // Add test generation actions
        actions.push(...await this._createTestActions(document, range, token));

        // Add documentation actions
        actions.push(...await this._createDocumentationActions(document, range, token));

        // Cache the results
        if (actions.length > 0) {
            this._addToCache(cacheKey, actions);
            this.actionsGenerated += actions.length;
        }

        return actions.length > 0 ? actions : undefined;
    }

    /**
     * Create refactoring actions
     */
    private async _createRefactorActions(
        document: vscode.TextDocument,
        range: vscode.Range,
        token: vscode.CancellationToken
    ): Promise<vscode.CodeAction[]> {
        const actions: vscode.CodeAction[] = [];

        // Extract method/function
        if (!range.isEmpty) {
            const extractAction = new vscode.CodeAction(
                '🔧 Extract to Function',
                vscode.CodeActionKind.RefactorExtract
            );
            extractAction.command = {
                command: 'enterpriseAI.extractFunction',
                title: 'Extract Function',
                arguments: [document, range]
            };
            actions.push(extractAction);
        }

        // Simplify code
        const simplifyAction = new vscode.CodeAction(
            '✨ Simplify Code',
            vscode.CodeActionKind.RefactorRewrite
        );
        simplifyAction.command = {
            command: 'enterpriseAI.simplifyCode',
            title: 'Simplify Code',
            arguments: [document, range]
        };
        actions.push(simplifyAction);

        // Optimize performance
        const optimizeAction = new vscode.CodeAction(
            '⚡ Optimize Performance',
            vscode.CodeActionKind.RefactorRewrite
        );
        optimizeAction.command = {
            command: 'enterpriseAI.optimizeCode',
            title: 'Optimize Performance',
            arguments: [document, range]
        };
        actions.push(optimizeAction);

        // Add error handling
        const errorHandlingAction = new vscode.CodeAction(
            '🛡️ Add Error Handling',
            vscode.CodeActionKind.Refactor
        );
        errorHandlingAction.command = {
            command: 'enterpriseAI.addErrorHandling',
            title: 'Add Error Handling',
            arguments: [document, range]
        };
        actions.push(errorHandlingAction);

        return actions;
    }

    /**
     * Create quick fix actions for diagnostics
     */
    private async _createQuickFixActions(
        document: vscode.TextDocument,
        range: vscode.Range,
        diagnostics: readonly vscode.Diagnostic[],
        token: vscode.CancellationToken
    ): Promise<vscode.CodeAction[]> {
        const actions: vscode.CodeAction[] = [];

        for (const diagnostic of diagnostics) {
            // AI-powered fix
            const fixAction = new vscode.CodeAction(
                `🤖 AI Fix: ${diagnostic.message}`,
                vscode.CodeActionKind.QuickFix
            );
            fixAction.diagnostics = [diagnostic];
            fixAction.isPreferred = true;
            fixAction.command = {
                command: 'enterpriseAI.fixDiagnostic',
                title: 'Fix with AI',
                arguments: [document, diagnostic]
            };
            actions.push(fixAction);
        }

        // Fix all issues
        if (diagnostics.length > 1) {
            const fixAllAction = new vscode.CodeAction(
                `🔧 Fix All Issues (${diagnostics.length})`,
                vscode.CodeActionKind.SourceFixAll
            );
            fixAllAction.command = {
                command: 'enterpriseAI.fixAllDiagnostics',
                title: 'Fix All',
                arguments: [document, diagnostics]
            };
            actions.push(fixAllAction);
        }

        return actions;
    }

    /**
     * Create security fix actions
     */
    private async _createSecurityActions(
        document: vscode.TextDocument,
        range: vscode.Range,
        token: vscode.CancellationToken
    ): Promise<vscode.CodeAction[]> {
        const actions: vscode.CodeAction[] = [];

        // Security scan
        const scanAction = new vscode.CodeAction(
            '🔒 Scan for Security Issues',
            vscode.CodeActionKind.Source
        );
        scanAction.command = {
            command: 'enterpriseAI.scanSecurity',
            title: 'Security Scan',
            arguments: [document, range]
        };
        actions.push(scanAction);

        return actions;
    }

    /**
     * Create test generation actions
     */
    private async _createTestActions(
        document: vscode.TextDocument,
        range: vscode.Range,
        token: vscode.CancellationToken
    ): Promise<vscode.CodeAction[]> {
        const actions: vscode.CodeAction[] = [];

        // Generate unit tests
        const testAction = new vscode.CodeAction(
            '🧪 Generate Unit Tests',
            vscode.CodeActionKind.Source
        );
        testAction.command = {
            command: 'enterpriseAI.generateTests',
            title: 'Generate Tests',
            arguments: [document, range]
        };
        actions.push(testAction);

        return actions;
    }

    /**
     * Create documentation actions
     */
    private async _createDocumentationActions(
        document: vscode.TextDocument,
        range: vscode.Range,
        token: vscode.CancellationToken
    ): Promise<vscode.CodeAction[]> {
        const actions: vscode.CodeAction[] = [];

        // Generate documentation
        const docAction = new vscode.CodeAction(
            '📝 Generate Documentation',
            vscode.CodeActionKind.Source
        );
        docAction.command = {
            command: 'enterpriseAI.generateDocumentation',
            title: 'Generate Documentation',
            arguments: [document, range]
        };
        actions.push(docAction);

        // Add JSDoc/docstring
        const docstringAction = new vscode.CodeAction(
            '📄 Add Docstring',
            vscode.CodeActionKind.Source
        );
        docstringAction.command = {
            command: 'enterpriseAI.addDocstring',
            title: 'Add Docstring',
            arguments: [document, range]
        };
        actions.push(docstringAction);

        return actions;
    }

    /**
     * Execute code action with AI
     */
    public async executeAction(
        document: vscode.TextDocument,
        range: vscode.Range,
        actionType: string
    ): Promise<void> {
        try {
            // Show progress
            await vscode.window.withProgress(
                {
                    location: vscode.ProgressLocation.Notification,
                    title: `AI Agent: ${actionType}`,
                    cancellable: true
                },
                async (progress, token) => {
                    progress.report({ message: 'Analyzing code...' });

                    // Get code
                    const code = document.getText(range);

                    // Create request
                    const request: CodeActionRequest = {
                        file_path: document.fileName,
                        language: document.languageId,
                        range: {
                            start: { line: range.start.line, character: range.start.character },
                            end: { line: range.end.line, character: range.end.character }
                        },
                        code,
                        action_type: this._mapActionType(actionType)
                    };

                    progress.report({ message: 'Generating suggestions...' });

                    // Send to backend
                    const response = await this.wsClient.sendWithResponse(
                        'code_action',
                        request,
                        30000 // 30 second timeout for complex actions
                    );

                    if (token.isCancellationRequested) {
                        return;
                    }

                    if (response && response.suggestions && response.suggestions.length > 0) {
                        progress.report({ message: 'Applying changes...' });
                        
                        // Show preview and apply
                        await this._showPreviewAndApply(document, range, response.suggestions);
                        
                        this.actionsApplied++;
                    } else {
                        vscode.window.showInformationMessage('No suggestions available');
                    }
                }
            );
        } catch (error) {
            vscode.window.showErrorMessage(`Failed to execute action: ${error}`);
        }
    }

    /**
     * Show preview and apply changes
     */
    private async _showPreviewAndApply(
        document: vscode.TextDocument,
        range: vscode.Range,
        suggestions: any[]
    ): Promise<void> {
        if (suggestions.length === 1) {
            // Single suggestion - show diff and apply
            const suggestion = suggestions[0];
            const applied = await this._applyEdit(document, range, suggestion.code);
            
            if (applied) {
                vscode.window.showInformationMessage(
                    `✅ Applied: ${suggestion.description}`
                );
            }
        } else {
            // Multiple suggestions - show quick pick
            const items = suggestions.map((s, i) => ({
                label: `$(lightbulb) ${s.description}`,
                description: `Confidence: ${Math.round(s.confidence * 100)}%`,
                detail: s.reasoning,
                suggestion: s,
                index: i
            }));

            const selected = await vscode.window.showQuickPick(items, {
                placeHolder: 'Select a suggestion to apply',
                matchOnDescription: true,
                matchOnDetail: true
            });

            if (selected) {
                this.actionsPreviewed++;
                const applied = await this._applyEdit(document, range, selected.suggestion.code);
                
                if (applied) {
                    vscode.window.showInformationMessage(
                        `✅ Applied: ${selected.suggestion.description}`
                    );
                }
            }
        }
    }

    /**
     * Apply edit to document
     */
    private async _applyEdit(
        document: vscode.TextDocument,
        range: vscode.Range,
        newCode: string
    ): Promise<boolean> {
        const edit = new vscode.WorkspaceEdit();
        edit.replace(document.uri, range, newCode);
        
        return await vscode.workspace.applyEdit(edit);
    }

    /**
     * Map action type to backend format
     */
    private _mapActionType(actionType: string): 'refactor' | 'quickfix' | 'security' | 'test' | 'documentation' {
        if (actionType.includes('refactor') || actionType.includes('extract') || actionType.includes('simplify') || actionType.includes('optimize')) {
            return 'refactor';
        } else if (actionType.includes('fix')) {
            return 'quickfix';
        } else if (actionType.includes('security')) {
            return 'security';
        } else if (actionType.includes('test')) {
            return 'test';
        } else if (actionType.includes('doc')) {
            return 'documentation';
        }
        return 'refactor';
    }

    /**
     * Generate cache key
     */
    private _generateCacheKey(document: vscode.TextDocument, range: vscode.Range): string {
        return `${document.fileName}:${range.start.line}:${range.start.character}:${range.end.line}:${range.end.character}`;
    }

    /**
     * Get from cache
     */
    private _getFromCache(key: string): vscode.CodeAction[] | null {
        const cached = this.actionCache.get(key);
        if (!cached) {
            return null;
        }
        return cached;
    }

    /**
     * Add to cache
     */
    private _addToCache(key: string, actions: vscode.CodeAction[]): void {
        this.actionCache.set(key, actions);

        // Auto-expire after TTL
        setTimeout(() => {
            this.actionCache.delete(key);
        }, this.CACHE_TTL);
    }

    /**
     * Clear cache
     */
    public clearCache(): void {
        this.actionCache.clear();
    }

    /**
     * Get statistics
     */
    public getStatistics(): {
        generated: number;
        applied: number;
        previewed: number;
        applicationRate: number;
    } {
        const applicationRate = this.actionsGenerated > 0 
            ? this.actionsApplied / this.actionsGenerated 
            : 0;

        return {
            generated: this.actionsGenerated,
            applied: this.actionsApplied,
            previewed: this.actionsPreviewed,
            applicationRate: Math.round(applicationRate * 100) / 100
        };
    }

    /**
     * Reset statistics
     */
    public resetStatistics(): void {
        this.actionsGenerated = 0;
        this.actionsApplied = 0;
        this.actionsPreviewed = 0;
    }
}
