/**
 * Agent Status Tree Provider for Sidebar
 * Project Creator: Herman Swanepoel
 */

import * as vscode from 'vscode';
import { WebSocketClient } from '../services/WebSocketClient';

interface AgentStatus {
    id: string;
    name: string;
    status: 'active' | 'idle' | 'error' | 'offline';
    lastActivity?: number;
    tasksCompleted?: number;
    successRate?: number;
}

export class AgentStatusTreeProvider implements vscode.TreeDataProvider<AgentTreeItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<AgentTreeItem | undefined | null | void> = new vscode.EventEmitter<AgentTreeItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<AgentTreeItem | undefined | null | void> = this._onDidChangeTreeData.event;

    private agents: Map<string, AgentStatus> = new Map();
    private wsClient: WebSocketClient;

    constructor(wsClient: WebSocketClient) {
        this.wsClient = wsClient;

        // Initialize default agents
        this.agents.set('refactor', {
            id: 'refactor',
            name: 'Refactor Agent',
            status: 'idle',
            tasksCompleted: 0,
            successRate: 0
        });

        this.agents.set('test', {
            id: 'test',
            name: 'Test Agent',
            status: 'idle',
            tasksCompleted: 0,
            successRate: 0
        });

        this.agents.set('bug', {
            id: 'bug',
            name: 'Bug Agent',
            status: 'idle',
            tasksCompleted: 0,
            successRate: 0
        });

        this.agents.set('doc', {
            id: 'doc',
            name: 'Doc Agent',
            status: 'idle',
            tasksCompleted: 0,
            successRate: 0
        });

        this.agents.set('orchestrator', {
            id: 'orchestrator',
            name: 'Orchestrator',
            status: 'idle',
            tasksCompleted: 0,
            successRate: 0
        });

        // Listen for agent status updates from backend
        this.wsClient.on('agent_status_update', (payload: any) => {
            this.updateAgentStatus(payload);
        });

        // Request initial status
        this.refreshAgentStatus();
    }

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    async refreshAgentStatus(): Promise<void> {
        try {
            const response = await this.wsClient.sendWithResponse('get_agent_status', {}, 5000);
            if (response && response.agents) {
                for (const agent of response.agents) {
                    this.updateAgentStatus(agent);
                }
            }
        } catch (error) {
            console.error('Failed to refresh agent status:', error);
        }
    }

    updateAgentStatus(agentData: any): void {
        const agent = this.agents.get(agentData.id);
        if (agent) {
            agent.status = agentData.status || agent.status;
            agent.lastActivity = agentData.last_activity || agent.lastActivity;
            agent.tasksCompleted = agentData.tasks_completed || agent.tasksCompleted;
            agent.successRate = agentData.success_rate || agent.successRate;
            this.refresh();
        }
    }

    getTreeItem(element: AgentTreeItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: AgentTreeItem): Thenable<AgentTreeItem[]> {
        if (!element) {
            // Root level - show all agents
            const items: AgentTreeItem[] = [];
            
            for (const [id, agent] of this.agents) {
                items.push(new AgentTreeItem(
                    agent.name,
                    agent.status,
                    vscode.TreeItemCollapsibleState.Collapsed,
                    {
                        command: 'enterpriseAI.showAgentDetails',
                        title: 'Show Agent Details',
                        arguments: [agent]
                    }
                ));
            }

            return Promise.resolve(items);
        } else {
            // Show agent details
            const agentId = element.label?.toString().toLowerCase().replace(' agent', '').replace(' ', '_');
            const agent = Array.from(this.agents.values()).find(a => 
                a.name.toLowerCase() === element.label?.toString().toLowerCase()
            );

            if (!agent) {
                return Promise.resolve([]);
            }

            const details: AgentTreeItem[] = [
                new AgentTreeItem(
                    `Status: ${agent.status}`,
                    agent.status,
                    vscode.TreeItemCollapsibleState.None
                ),
                new AgentTreeItem(
                    `Tasks Completed: ${agent.tasksCompleted || 0}`,
                    agent.status,
                    vscode.TreeItemCollapsibleState.None
                ),
                new AgentTreeItem(
                    `Success Rate: ${Math.round((agent.successRate || 0) * 100)}%`,
                    agent.status,
                    vscode.TreeItemCollapsibleState.None
                )
            ];

            if (agent.lastActivity) {
                const lastActivityTime = new Date(agent.lastActivity).toLocaleTimeString();
                details.push(new AgentTreeItem(
                    `Last Activity: ${lastActivityTime}`,
                    agent.status,
                    vscode.TreeItemCollapsibleState.None
                ));
            }

            return Promise.resolve(details);
        }
    }
}

class AgentTreeItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        private status: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly command?: vscode.Command
    ) {
        super(label, collapsibleState);

        this.tooltip = `${this.label}`;
        this.iconPath = this.getIcon(status);
    }

    private getIcon(status: string): vscode.ThemeIcon {
        switch (status) {
            case 'active':
                return new vscode.ThemeIcon('loading~spin', new vscode.ThemeColor('testing.iconPassed'));
            case 'idle':
                return new vscode.ThemeIcon('circle-outline', new vscode.ThemeColor('testing.iconQueued'));
            case 'error':
                return new vscode.ThemeIcon('error', new vscode.ThemeColor('testing.iconFailed'));
            case 'offline':
                return new vscode.ThemeIcon('circle-slash', new vscode.ThemeColor('descriptionForeground'));
            default:
                return new vscode.ThemeIcon('circle-outline');
        }
    }

    contextValue = 'agent';
}
