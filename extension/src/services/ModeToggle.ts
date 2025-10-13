/**
 * Mode toggle for offline/online mode switching
 * Project Creator: Herman Swanepoel
 */

import * as vscode from 'vscode';

export enum OperationMode {
    OFFLINE = 'offline',
    ONLINE = 'online'
}

export interface ModeChangeEvent {
    mode: OperationMode;
    previousMode: OperationMode;
    timestamp: number;
}

export class ModeToggle {
    private statusBarItem: vscode.StatusBarItem;
    private currentMode: OperationMode;
    private modeChangeCallbacks: Array<(event: ModeChangeEvent) => void> = [];
    private context: vscode.ExtensionContext;

    // Visual styling
    private readonly OFFLINE_COLOR = '#00FFFF'; // Neon blue
    private readonly ONLINE_COLOR = '#00FF00';  // Neon green
    private readonly OFFLINE_ICON = '$(shield)';
    private readonly ONLINE_ICON = '$(cloud)';

    constructor(context: vscode.ExtensionContext, defaultMode: OperationMode = OperationMode.OFFLINE) {
        this.context = context;
        this.currentMode = this._loadPersistedMode() || defaultMode;

        // Create status bar item
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            1000 // High priority
        );

        this.statusBarItem.command = 'enterpriseAI.toggleMode';
        this.updateStatusBar();
        this.statusBarItem.show();

        // Register command
        context.subscriptions.push(
            vscode.commands.registerCommand('enterpriseAI.toggleMode', () => this.toggleMode())
        );

        context.subscriptions.push(this.statusBarItem);
    }

    /**
     * Get current operation mode
     */
    public getCurrentMode(): OperationMode {
        return this.currentMode;
    }

    /**
     * Check if in offline mode
     */
    public isOffline(): boolean {
        return this.currentMode === OperationMode.OFFLINE;
    }

    /**
     * Check if in online mode
     */
    public isOnline(): boolean {
        return this.currentMode === OperationMode.ONLINE;
    }

    /**
     * Set operation mode
     */
    public async setMode(mode: OperationMode): Promise<void> {
        if (mode === this.currentMode) {
            return;
        }

        const previousMode = this.currentMode;
        this.currentMode = mode;

        // Persist mode
        await this._persistMode(mode);

        // Update UI
        this.updateStatusBar();

        // Show notification
        this._showModeChangeNotification(mode);

        // Notify callbacks
        const event: ModeChangeEvent = {
            mode,
            previousMode,
            timestamp: Date.now()
        };

        for (const callback of this.modeChangeCallbacks) {
            try {
                callback(event);
            } catch (error) {
                console.error('Mode change callback error:', error);
            }
        }
    }

    /**
     * Switch to offline mode
     */
    public async switchToOffline(): Promise<void> {
        await this.setMode(OperationMode.OFFLINE);
    }

    /**
     * Switch to online mode
     */
    public async switchToOnline(): Promise<void> {
        await this.setMode(OperationMode.ONLINE);
    }

    /**
     * Toggle between offline and online modes
     */
    public async toggleMode(): Promise<void> {
        const newMode = this.isOffline() ? OperationMode.ONLINE : OperationMode.OFFLINE;
        await this.setMode(newMode);
    }

    /**
     * Register callback for mode changes
     */
    public onModeChange(callback: (event: ModeChangeEvent) => void): vscode.Disposable {
        this.modeChangeCallbacks.push(callback);

        return new vscode.Disposable(() => {
            const index = this.modeChangeCallbacks.indexOf(callback);
            if (index > -1) {
                this.modeChangeCallbacks.splice(index, 1);
            }
        });
    }

    /**
     * Update status bar appearance
     */
    private updateStatusBar(): void {
        if (this.isOffline()) {
            this.statusBarItem.text = `${this.OFFLINE_ICON} LOCAL MODE`;
            this.statusBarItem.tooltip = 'Offline Mode: All operations run locally (Click to switch to Online)';
            this.statusBarItem.backgroundColor = undefined;
            // Apply neon blue color via CSS
            this.statusBarItem.color = this.OFFLINE_COLOR;
        } else {
            this.statusBarItem.text = `${this.ONLINE_ICON} CLOUD MODE`;
            this.statusBarItem.tooltip = 'Online Mode: Cloud LLM fallback enabled (Click to switch to Offline)';
            this.statusBarItem.backgroundColor = undefined;
            // Apply neon green color via CSS
            this.statusBarItem.color = this.ONLINE_COLOR;
        }
    }

    /**
     * Show mode change notification
     */
    private _showModeChangeNotification(mode: OperationMode): void {
        const message = mode === OperationMode.OFFLINE
            ? '🔒 Switched to LOCAL MODE - All operations run locally'
            : '☁️ Switched to CLOUD MODE - Cloud LLM fallback enabled';

        const detail = mode === OperationMode.OFFLINE
            ? 'Maximum privacy. No data sent to cloud.'
            : 'Cloud APIs enabled. Data may be sent to cloud providers.';

        vscode.window.showInformationMessage(`${message}\n${detail}`);
    }

    /**
     * Load persisted mode from workspace state
     */
    private _loadPersistedMode(): OperationMode | undefined {
        const persistedMode = this.context.workspaceState.get<string>('enterpriseAI.operationMode');
        
        if (persistedMode === OperationMode.OFFLINE || persistedMode === OperationMode.ONLINE) {
            return persistedMode as OperationMode;
        }

        return undefined;
    }

    /**
     * Persist mode to workspace state
     */
    private async _persistMode(mode: OperationMode): Promise<void> {
        await this.context.workspaceState.update('enterpriseAI.operationMode', mode);
    }

    /**
     * Get mode information
     */
    public getModeInfo(): {
        mode: OperationMode;
        isOffline: boolean;
        isOnline: boolean;
        description: string;
        privacyLevel: string;
    } {
        return {
            mode: this.currentMode,
            isOffline: this.isOffline(),
            isOnline: this.isOnline(),
            description: this._getModeDescription(),
            privacyLevel: this.isOffline() ? 'maximum' : 'standard'
        };
    }

    /**
     * Get human-readable mode description
     */
    private _getModeDescription(): string {
        if (this.isOffline()) {
            return 'All operations run locally. Maximum privacy. No data sent to cloud.';
        } else {
            return 'Cloud LLM fallback enabled. Data may be sent to cloud providers.';
        }
    }

    /**
     * Dispose resources
     */
    public dispose(): void {
        this.statusBarItem.dispose();
        this.modeChangeCallbacks = [];
    }
}
