/**
 * Workspace Manager for multi-workspace support
 * Project Creator: Herman Swanepoel
 */

import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';

interface WorkspaceConfig {
    id: string;
    name: string;
    path: string;
    description?: string;
    strengths?: string[];
    agentSettings?: {
        [agentName: string]: {
            enabled: boolean;
            priority?: number;
            customSettings?: Record<string, any>;
        };
    };
    lastAccessed: number;
    metadata?: Record<string, any>;
}

interface WorkspaceState {
    openFiles: string[];
    activeFile?: string;
    cursorPosition?: { line: number; character: number };
    viewState?: any;
}

export class WorkspaceManager {
    private workspaces: Map<string, WorkspaceConfig> = new Map();
    private workspaceStates: Map<string, WorkspaceState> = new Map();
    private currentWorkspaceId: string | null = null;
    private context: vscode.ExtensionContext;
    private readonly CONFIG_FILE = '.vscode/ai-agents-workspace.json';

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
        this.initialize();
    }

    /**
     * Initialize workspace manager
     */
    private async initialize() {
        // Load saved workspaces from global state
        const savedWorkspaces = this.context.globalState.get<Record<string, WorkspaceConfig>>('workspaces', {});
        for (const [id, config] of Object.entries(savedWorkspaces)) {
            this.workspaces.set(id, config);
        }

        // Load workspace states
        const savedStates = this.context.globalState.get<Record<string, WorkspaceState>>('workspaceStates', {});
        for (const [id, state] of Object.entries(savedStates)) {
            this.workspaceStates.set(id, state);
        }

        // Detect and register current workspace
        await this.detectAndRegisterCurrentWorkspace();

        // Watch for workspace changes
        vscode.workspace.onDidChangeWorkspaceFolders(() => {
            this.detectAndRegisterCurrentWorkspace();
        });
    }

    /**
     * Detect and register current workspace
     */
    private async detectAndRegisterCurrentWorkspace() {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders || workspaceFolders.length === 0) {
            return;
        }

        const workspaceFolder = workspaceFolders[0];
        const workspacePath = workspaceFolder.uri.fsPath;
        const workspaceId = this.generateWorkspaceId(workspacePath);

        // Check if workspace is already registered
        if (!this.workspaces.has(workspaceId)) {
            // Load configuration from workspace file
            const config = await this.loadWorkspaceConfig(workspacePath);

            const workspaceConfig: WorkspaceConfig = {
                id: workspaceId,
                name: config?.name || workspaceFolder.name,
                path: workspacePath,
                description: config?.description,
                strengths: config?.strengths,
                agentSettings: config?.agentSettings,
                lastAccessed: Date.now(),
                metadata: config?.metadata
            };

            this.workspaces.set(workspaceId, workspaceConfig);
            await this.saveWorkspaces();
        }

        // Set as current workspace
        this.currentWorkspaceId = workspaceId;

        // Update last accessed time
        const workspace = this.workspaces.get(workspaceId);
        if (workspace) {
            workspace.lastAccessed = Date.now();
            await this.saveWorkspaces();
        }
    }

    /**
     * Load workspace configuration from file
     */
    private async loadWorkspaceConfig(workspacePath: string): Promise<Partial<WorkspaceConfig> | null> {
        const configPath = path.join(workspacePath, this.CONFIG_FILE);

        try {
            if (fs.existsSync(configPath)) {
                const content = fs.readFileSync(configPath, 'utf-8');
                return JSON.parse(content);
            }
        } catch (error) {
            console.error('Failed to load workspace config:', error);
        }

        return null;
    }

    /**
     * Save workspace configuration to file
     */
    public async saveWorkspaceConfig(workspaceId: string, config: Partial<WorkspaceConfig>): Promise<boolean> {
        const workspace = this.workspaces.get(workspaceId);
        if (!workspace) {
            return false;
        }

        const configPath = path.join(workspace.path, this.CONFIG_FILE);

        try {
            // Ensure .vscode directory exists
            const vscodePath = path.join(workspace.path, '.vscode');
            if (!fs.existsSync(vscodePath)) {
                fs.mkdirSync(vscodePath, { recursive: true });
            }

            // Write configuration
            fs.writeFileSync(configPath, JSON.stringify(config, null, 2), 'utf-8');

            // Update in-memory config
            Object.assign(workspace, config);
            await this.saveWorkspaces();

            return true;
        } catch (error) {
            console.error('Failed to save workspace config:', error);
            return false;
        }
    }

    /**
     * Generate workspace ID from path
     */
    private generateWorkspaceId(workspacePath: string): string {
        // Use a hash of the path as ID
        return Buffer.from(workspacePath).toString('base64').replace(/[^a-zA-Z0-9]/g, '');
    }

    /**
     * Get current workspace
     */
    public getCurrentWorkspace(): WorkspaceConfig | null {
        if (!this.currentWorkspaceId) {
            return null;
        }
        return this.workspaces.get(this.currentWorkspaceId) || null;
    }

    /**
     * Get all workspaces
     */
    public getAllWorkspaces(): WorkspaceConfig[] {
        return Array.from(this.workspaces.values())
            .sort((a, b) => b.lastAccessed - a.lastAccessed);
    }

    /**
     * Switch to a different workspace
     */
    public async switchWorkspace(workspaceId: string): Promise<boolean> {
        const workspace = this.workspaces.get(workspaceId);
        if (!workspace) {
            vscode.window.showErrorMessage('Workspace not found');
            return false;
        }

        try {
            // Save current workspace state
            if (this.currentWorkspaceId) {
                await this.saveCurrentWorkspaceState();
            }

            // Open the workspace
            const uri = vscode.Uri.file(workspace.path);
            await vscode.commands.executeCommand('vscode.openFolder', uri, false);

            // Restore workspace state (will happen after workspace opens)
            // Note: State restoration happens in the new workspace instance

            return true;
        } catch (error) {
            vscode.window.showErrorMessage(`Failed to switch workspace: ${error}`);
            return false;
        }
    }

    /**
     * Save current workspace state
     */
    private async saveCurrentWorkspaceState() {
        if (!this.currentWorkspaceId) {
            return;
        }

        const state: WorkspaceState = {
            openFiles: [],
            activeFile: undefined,
            cursorPosition: undefined
        };

        // Get open files
        const openEditors = vscode.window.visibleTextEditors;
        state.openFiles = openEditors.map(editor => editor.document.uri.fsPath);

        // Get active file and cursor position
        const activeEditor = vscode.window.activeTextEditor;
        if (activeEditor) {
            state.activeFile = activeEditor.document.uri.fsPath;
            state.cursorPosition = {
                line: activeEditor.selection.active.line,
                character: activeEditor.selection.active.character
            };
        }

        this.workspaceStates.set(this.currentWorkspaceId, state);
        await this.saveWorkspaceStates();
    }

    /**
     * Restore workspace state
     */
    public async restoreWorkspaceState(workspaceId: string) {
        const state = this.workspaceStates.get(workspaceId);
        if (!state) {
            return;
        }

        try {
            // Reopen files
            for (const filePath of state.openFiles) {
                try {
                    const uri = vscode.Uri.file(filePath);
                    await vscode.window.showTextDocument(uri, { preview: false });
                } catch (error) {
                    console.error(`Failed to open file: ${filePath}`, error);
                }
            }

            // Restore active file and cursor position
            if (state.activeFile && state.cursorPosition) {
                try {
                    const uri = vscode.Uri.file(state.activeFile);
                    const document = await vscode.workspace.openTextDocument(uri);
                    const editor = await vscode.window.showTextDocument(document);

                    const position = new vscode.Position(
                        state.cursorPosition.line,
                        state.cursorPosition.character
                    );
                    editor.selection = new vscode.Selection(position, position);
                    editor.revealRange(new vscode.Range(position, position));
                } catch (error) {
                    console.error('Failed to restore cursor position', error);
                }
            }
        } catch (error) {
            console.error('Failed to restore workspace state:', error);
        }
    }

    /**
     * Get workspace-specific agent settings
     */
    public getAgentSettings(workspaceId?: string): Record<string, any> | null {
        const id = workspaceId || this.currentWorkspaceId;
        if (!id) {
            return null;
        }

        const workspace = this.workspaces.get(id);
        return workspace?.agentSettings || null;
    }

    /**
     * Update workspace-specific agent settings
     */
    public async updateAgentSettings(
        agentName: string,
        settings: { enabled: boolean; priority?: number; customSettings?: Record<string, any> },
        workspaceId?: string
    ): Promise<boolean> {
        const id = workspaceId || this.currentWorkspaceId;
        if (!id) {
            return false;
        }

        const workspace = this.workspaces.get(id);
        if (!workspace) {
            return false;
        }

        if (!workspace.agentSettings) {
            workspace.agentSettings = {};
        }

        workspace.agentSettings[agentName] = settings;

        await this.saveWorkspaces();
        await this.saveWorkspaceConfig(id, { agentSettings: workspace.agentSettings });

        return true;
    }

    /**
     * Update workspace metadata
     */
    public async updateWorkspaceMetadata(
        metadata: { name?: string; description?: string; strengths?: string[] },
        workspaceId?: string
    ): Promise<boolean> {
        const id = workspaceId || this.currentWorkspaceId;
        if (!id) {
            return false;
        }

        const workspace = this.workspaces.get(id);
        if (!workspace) {
            return false;
        }

        if (metadata.name) workspace.name = metadata.name;
        if (metadata.description) workspace.description = metadata.description;
        if (metadata.strengths) workspace.strengths = metadata.strengths;

        await this.saveWorkspaces();
        await this.saveWorkspaceConfig(id, metadata);

        return true;
    }

    /**
     * Show workspace quick-switch UI
     */
    public async showWorkspaceSwitcher() {
        const workspaces = this.getAllWorkspaces();

        if (workspaces.length === 0) {
            vscode.window.showInformationMessage('No workspaces registered');
            return;
        }

        const items = workspaces.map(ws => ({
            label: ws.name,
            description: ws.path,
            detail: ws.description || `Last accessed: ${new Date(ws.lastAccessed).toLocaleString()}`,
            workspace: ws
        }));

        const selected = await vscode.window.showQuickPick(items, {
            placeHolder: 'Select a workspace to switch to',
            matchOnDescription: true,
            matchOnDetail: true
        });

        if (selected) {
            await this.switchWorkspace(selected.workspace.id);
        }
    }

    /**
     * Remove workspace from registry
     */
    public async removeWorkspace(workspaceId: string): Promise<boolean> {
        if (this.workspaces.has(workspaceId)) {
            this.workspaces.delete(workspaceId);
            this.workspaceStates.delete(workspaceId);

            await this.saveWorkspaces();
            await this.saveWorkspaceStates();

            return true;
        }
        return false;
    }

    /**
     * Save workspaces to global state
     */
    private async saveWorkspaces() {
        const workspacesObj: Record<string, WorkspaceConfig> = {};
        for (const [id, config] of this.workspaces.entries()) {
            workspacesObj[id] = config;
        }
        await this.context.globalState.update('workspaces', workspacesObj);
    }

    /**
     * Save workspace states to global state
     */
    private async saveWorkspaceStates() {
        const statesObj: Record<string, WorkspaceState> = {};
        for (const [id, state] of this.workspaceStates.entries()) {
            statesObj[id] = state;
        }
        await this.context.globalState.update('workspaceStates', statesObj);
    }

    /**
     * Get workspace statistics
     */
    public getWorkspaceStats(workspaceId?: string): {
        totalWorkspaces: number;
        currentWorkspace: string | null;
        lastAccessed: number | null;
    } {
        return {
            totalWorkspaces: this.workspaces.size,
            currentWorkspace: this.currentWorkspaceId,
            lastAccessed: this.currentWorkspaceId
                ? this.workspaces.get(this.currentWorkspaceId)?.lastAccessed || null
                : null
        };
    }

    /**
     * Dispose resources
     */
    public async dispose() {
        // Save current state before disposing
        if (this.currentWorkspaceId) {
            await this.saveCurrentWorkspaceState();
        }
        await this.saveWorkspaces();
        await this.saveWorkspaceStates();
    }
}
