/**
 * Code Action Provider for AI-powered quick fixes
 * Project Creator: Herman Swanepoel
 */

import * as vscode from 'vscode';
import { WebSocketClient } from '../services/WebSocketClient';

interface CodeActionRequest {
    file_path: string;
    language: string;
    code: string;
    diagnostics: Array<{
        message: string;
        severity: string;
        range: { start: { line: number; character: number }; end: { line: number; character: number } };
    }>;
    action_type: 'refactor' | 'security' | 'test' | 'fix' | 'optimize';
}

interface CodeActionResponse {
    actions: Array<{
        title: string;
        description: string;
        kind: string;
        edits: Array<{
            range: { start: { line: number; character: number }; end: { line: number; character: number } };
            new_text: string;
        }>;
        confidence: number;
        reasoning?: string;
    }>;
}

interface UndoState {
    document: vscode.Uri;
    edits: vscode.TextEdit[];
    timestamp: number;
}

export class AICodeActionProvider implements vscode.CodeActionProvider {
    private wsClient: WebSocketClient;
    private undoStack: UndoState[] = [];
    private readonly MAX_UNDO_STACK = 50;

    public static readonly providedCodeActionKinds = [
        vscode.CodeActionKind.QuickFix,
        vscode.CodeActionKind.Refactor,
        vscode.CodeActionKind.RefactorExtract,
        vscode.CodeActionKind.RefactorInline,
        vscode.CodeActionKind.RefactorRewrite,
        vscode.CodeActionKind.Source,
        vscode.CodeActionKind.SourceFixAll
    ];

    constructor(wsClient: WebSocketClient) {
        this.wsClient = wsClient;
    }

    /**
     * Provide code actions for the given document and range
     */
    public async provideCodeActions(
        document: vscode.TextDocument,
        range: vscode.Range | vscode.Selection,
        context: vscode.CodeActionContext,
        token: vscode.CancellationToken
    ): Promise<vscode.CodeAction[]> {
        // Check if backend is connected
        if (!this.wsClient.isConnectedToBackend()) {
            return [];
        }

        const actions: vscode.CodeAction[] = [];

        // Add refactoring actions
        if (range.isEmpty === false) {
            actions.push(...this._createRefactorActions(document, range));
        }

        // Add security fix actions
        actions.push(...this._createSecurityActions(document, range, context));

        // Add test generation actions
        actions.push(...this._createTestActions(document, range));

        // Add optimization actions
        actions.push(...this._createOptimizationActions(document, range));

        // Add diagnostic fix actions
        if (context.diagnostics.length > 0) {
            actions.push(...await this._createDiagnosticFixActions(document, range, context));
        }

        return actions;
    }

    /**
     * Create refactoring actions
     */
    private _createRefactorActions(
        document: vscode.TextDocument,
        range: vscode.Range
    ): vscode.CodeAction[] {
        const actions: vscode.CodeAction[] = [];

        // Extract method/function
        const extractAction = new vscode.CodeAction(
            '🤖 AI: Extract to Function',
            vscode.CodeActionKind.RefactorExtract
        );
        extractAction.command = {
            command: 'enterpriseAI.extractFunction',
            title: 'Extract to Function',
            arguments: [document, range]
        };
        actions.push(extractAction);

        // Simplify code
        const simplifyAction = new vscode.CodeAction(
            '🤖 AI: Simplify Code',
            vscode.CodeActionKind.RefactorRewrite
        );
        simplifyAction.command = {
            command: 'enterpriseAI.simplifyCode',
            title: 'Simplify Code',
            arguments: [document, range]
        };
        actions.push(simplifyAction);

        // Improve naming
        const namingAction = new vscode.CodeAction(
            '🤖 AI: Improve Naming',
            vscode.CodeActionKind.Refactor
        );
        namingAction.command = {
            command: 'enterpriseAI.improveNaming',
            title: 'Improve Naming',
            arguments: [document, range]
        };
        actions.push(namingAction);

        return actions;
    }

    /**
     * Create security fix actions
     */
    private _createSecurityActions(
        document: vscode.TextDocument,
        range: vscode.Range,
        context: vscode.CodeActionContext
    ): vscode.CodeAction[] {
        const actions: vscode.CodeAction[] = [];

        // Check for security-related diagnostics
        const hasSecurityIssues = context.diagnostics.some(d =>
            d.message.toLowerCase().includes('security') ||
            d.message.toLowerCase().includes('vulnerability') ||
            d.message.toLowerCase().includes('injection')
        );

        if (hasSecurityIssues || range.isEmpty === false) {
            const securityAction = new vscode.CodeAction(
                '🛡️ AI: Find & Fix Security Issues',
                vscode.CodeActionKind.QuickFix
            );
            securityAction.command = {
                command: 'enterpriseAI.findSecurityIssues',
                title: 'Find Security Issues',
                arguments: [document, range]
            };
            actions.push(securityAction);
        }

        return actions;
    }

    /**
     * Create test generation actions
     */
    private _createTestActions(
        document: vscode.TextDocument,
        range: vscode.Range
    ): vscode.CodeAction[] {
        const actions: vscode.CodeAction[] = [];

        // Generate unit tests
        const testAction = new vscode.CodeAction(
            '🧪 AI: Generate Unit Tests',
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
     * Create optimization actions
     */
    private _createOptimizationActions(
        document: vscode.TextDocument,
        range: vscode.Range
    ): vscode.CodeAction[] {
        const actions: vscode.CodeAction[] = [];

        if (range.isEmpty === false) {
            const optimizeAction = new vscode.CodeAction(
                '⚡ AI: Optimize Performance',
                vscode.CodeActionKind.RefactorRewrite
            );
            optimizeAction.command = {
                command: 'enterpriseAI.optimizeCode',
                title: 'Optimize Code',
                arguments: [document, range]
            };
            actions.push(optimizeAction);
        }

        return actions;
    }

    /**
     * Create diagnostic fix actions
     */
    private async _createDiagnosticFixActions(
        document: vscode.TextDocument,
        range: vscode.Range,
        context: vscode.CodeActionContext
    ): Promise<vscode.CodeAction[]> {
        const actions: vscode.CodeAction[] = [];

        // Group diagnostics by type
        const errors = context.diagnostics.filter(d => d.severity === vscode.DiagnosticSeverity.Error);
        const warnings = context.diagnostics.filter(d => d.severity === vscode.DiagnosticSeverity.Warning);

        if (errors.length > 0) {
            const fixErrorsAction = new vscode.CodeAction(
                `🔧 AI: Fix ${errors.length} Error${errors.length > 1 ? 's' : ''}`,
                vscode.CodeActionKind.QuickFix
            );
            fixErrorsAction.command = {
                command: 'enterpriseAI.fixDiagnostics',
                title: 'Fix Errors',
                arguments: [document, errors, 'error']
            };
            fixErrorsAction.isPreferred = true;
            actions.push(fixErrorsAction);
        }

        if (warnings.length > 0) {
            const fixWarningsAction = new vscode.CodeAction(
                `⚠️ AI: Fix ${warnings.length} Warning${warnings.length > 1 ? 's' : ''}`,
                vscode.CodeActionKind.QuickFix
            );
            fixWarningsAction.command = {
                command: 'enterpriseAI.fixDiagnostics',
                title: 'Fix Warnings',
                arguments: [document, warnings, 'warning']
            };
            actions.push(fixWarningsAction);
        }

        // Fix all
        if (context.diagnostics.length > 0) {
            const fixAllAction = new vscode.CodeAction(
                '🔧 AI: Fix All Issues',
                vscode.CodeActionKind.SourceFixAll
            );
            fixAllAction.command = {
                command: 'enterpriseAI.fixDiagnostics',
                title: 'Fix All',
                arguments: [document, context.diagnostics, 'all']
            };
            actions.push(fixAllAction);
        }

        return actions;
    }

    /**
     * Apply code action with preview
     */
    public async applyCodeAction(
        document: vscode.TextDocument,
        actionType: string,
        range?: vscode.Range,
        diagnostics?: vscode.Diagnostic[]
    ): Promise<boolean> {
        try {
            // Show progress
            return await vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: 'AI Agent Processing...',
                cancellable: true
            }, async (progress, token) => {
                progress.report({ message: 'Analyzing code...' });

                // Get code to analyze
                const code = range
                    ? document.getText(range)
                    : document.getText();

                // Create request
                const request: CodeActionRequest = {
                    file_path: document.fileName,
                    language: document.languageId,
                    code,
                    diagnostics: diagnostics?.map(d => ({
                        message: d.message,
                        severity: this._getSeverityString(d.severity),
                        range: {
                            start: { line: d.range.start.line, character: d.range.start.character },
                            end: { line: d.range.end.line, character: d.range.end.character }
                        }
                    })) || [],
                    action_type: this._getActionType(actionType)
                };

                progress.report({ message: 'Generating fixes...' });

                // Send request to backend
                const response = await this.wsClient.sendWithResponse(
                    'code_action',
                    request,
                    30000
                ) as CodeActionResponse;

                if (!response || !response.actions || response.actions.length === 0) {
                    vscode.window.showInformationMessage('No AI suggestions available for this code.');
                    return false;
                }

                progress.report({ message: 'Preparing preview...' });

                // Show preview and get user confirmation
                const action = await this._showActionPreview(document, response.actions);

                if (!action) {
                    return false;
                }

                progress.report({ message: 'Applying changes...' });

                // Apply the action
                const success = await this._applyEdits(document, action.edits);

                if (success) {
                    vscode.window.showInformationMessage(
                        `✅ ${action.title} applied successfully!`
                    );
                }

                return success;
            });
        } catch (error) {
            vscode.window.showErrorMessage(`Failed to apply code action: ${error}`);
            return false;
        }
    }

    /**
     * Show action preview and get user selection
     */
    private async _showActionPreview(
        document: vscode.TextDocument,
        actions: CodeActionResponse['actions']
    ): Promise<CodeActionResponse['actions'][0] | undefined> {
        // If only one action, show it directly
        if (actions.length === 1) {
            const action = actions[0];
            const preview = this._generatePreviewText(action);

            const choice = await vscode.window.showInformationMessage(
                `${action.title}\n\nConfidence: ${Math.round(action.confidence * 100)}%\n${action.reasoning || ''}`,
                { modal: true, detail: preview },
                'Apply',
                'Cancel'
            );

            return choice === 'Apply' ? action : undefined;
        }

        // Multiple actions - let user choose
        const items = actions.map(action => ({
            label: action.title,
            description: `Confidence: ${Math.round(action.confidence * 100)}%`,
            detail: action.reasoning,
            action
        }));

        const selected = await vscode.window.showQuickPick(items, {
            placeHolder: 'Select an AI suggestion to preview',
            matchOnDescription: true,
            matchOnDetail: true
        });

        if (!selected) {
            return undefined;
        }

        // Show preview for selected action
        const preview = this._generatePreviewText(selected.action);
        const choice = await vscode.window.showInformationMessage(
            `Preview: ${selected.action.title}`,
            { modal: true, detail: preview },
            'Apply',
            'Cancel'
        );

        return choice === 'Apply' ? selected.action : undefined;
    }

    /**
     * Generate preview text for action
     */
    private _generatePreviewText(action: CodeActionResponse['actions'][0]): string {
        let preview = 'Changes:\n\n';

        action.edits.forEach((edit, index) => {
            preview += `${index + 1}. Line ${edit.range.start.line + 1}:\n`;
            preview += `   ${edit.new_text}\n\n`;
        });

        return preview;
    }

    /**
     * Apply edits to document
     */
    private async _applyEdits(
        document: vscode.TextDocument,
        edits: CodeActionResponse['actions'][0]['edits']
    ): Promise<boolean> {
        const workspaceEdit = new vscode.WorkspaceEdit();
        const textEdits: vscode.TextEdit[] = [];

        // Convert to VS Code edits
        for (const edit of edits) {
            const range = new vscode.Range(
                new vscode.Position(edit.range.start.line, edit.range.start.character),
                new vscode.Position(edit.range.end.line, edit.range.end.character)
            );

            const textEdit = vscode.TextEdit.replace(range, edit.new_text);
            textEdits.push(textEdit);
            workspaceEdit.replace(document.uri, range, edit.new_text);
        }

        // Save undo state
        this._saveUndoState(document.uri, textEdits);

        // Apply edits
        const success = await vscode.workspace.applyEdit(workspaceEdit);

        if (success) {
            // Save document
            await document.save();
        }

        return success;
    }

    /**
     * Save undo state
     */
    private _saveUndoState(documentUri: vscode.Uri, edits: vscode.TextEdit[]): void {
        this.undoStack.push({
            document: documentUri,
            edits,
            timestamp: Date.now()
        });

        // Limit stack size
        if (this.undoStack.length > this.MAX_UNDO_STACK) {
            this.undoStack.shift();
        }
    }

    /**
     * Rollback last action
     */
    public async rollbackLastAction(): Promise<boolean> {
        if (this.undoStack.length === 0) {
            vscode.window.showInformationMessage('No actions to rollback.');
            return false;
        }

        const lastState = this.undoStack.pop();
        if (!lastState) {
            return false;
        }

        try {
            const document = await vscode.workspace.openTextDocument(lastState.document);

            // Use VS Code's built-in undo
            const editor = await vscode.window.showTextDocument(document);
            await vscode.commands.executeCommand('undo');

            vscode.window.showInformationMessage('✅ Action rolled back successfully!');
            return true;
        } catch (error) {
            vscode.window.showErrorMessage(`Failed to rollback: ${error}`);
            return false;
        }
    }

    /**
     * Get severity string
     */
    private _getSeverityString(severity: vscode.DiagnosticSeverity | undefined): string {
        switch (severity) {
            case vscode.DiagnosticSeverity.Error:
                return 'error';
            case vscode.DiagnosticSeverity.Warning:
                return 'warning';
            case vscode.DiagnosticSeverity.Information:
                return 'info';
            case vscode.DiagnosticSeverity.Hint:
                return 'hint';
            default:
                return 'unknown';
        }
    }

    /**
     * Get action type from command
     */
    private _getActionType(actionType: string): CodeActionRequest['action_type'] {
        if (actionType.includes('security')) return 'security';
        if (actionType.includes('test')) return 'test';
        if (actionType.includes('optimize')) return 'optimize';
        if (actionType.includes('refactor') || actionType.includes('extract') || actionType.includes('simplify')) return 'refactor';
        return 'fix';
    }

    /**
     * Dispose resources
     */
    public dispose(): void {
        this.undoStack = [];
    }
}
