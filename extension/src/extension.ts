/**
 * Enterprise AI Agents Integration - VS Code Extension
 * Project Creator: Herman Swanepoel
 */

import * as vscode from 'vscode';
import { WebSocketClient } from './services/WebSocketClient';
import { v4 as uuidv4 } from 'uuid';

let wsClient: WebSocketClient | null = null;

export function activate(context: vscode.ExtensionContext) {
    console.log('Enterprise AI Agents extension is now active!');
    console.log('Project Creator: Herman Swanepoel');

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

    wsClient.on('mode_changed', (payload) => {
        vscode.window.showInformationMessage(`Mode changed to: ${payload.mode}`);
    });

    const toggleModeCommand = vscode.commands.registerCommand(
        'enterpriseAI.toggleMode',
        () => {
            vscode.window.showInformationMessage('Mode toggle not yet implemented');
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
        () => {
            vscode.window.showInformationMessage('Find security issues not yet implemented');
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
        () => {
            vscode.window.showInformationMessage('Start agent discussion not yet implemented');
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
        toggleModeCommand,
        generateTestsCommand,
        refactorSelectionCommand,
        explainCodeCommand,
        findSecurityIssuesCommand,
        generateDocumentationCommand,
        startAgentDiscussionCommand,
        viewAnalyticsCommand,
        reindexCodebaseCommand
    );

    if (wsClient) {
        context.subscriptions.push({
            dispose: () => wsClient?.dispose()
        });
    }
}

export function deactivate() {
    console.log('Enterprise AI Agents extension is now deactivated');
    if (wsClient) {
        wsClient.disconnect();
    }
}
