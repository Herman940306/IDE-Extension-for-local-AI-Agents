const assert = require('assert').strict;
// Minimal vscode stub for TreeItem and ThemeIcon
require('mock-require')('vscode', {
    ThemeIcon: class ThemeIcon { constructor(id) { this.id = id; } },
    TreeItemCollapsibleState: { None: 0, Collapsed: 1, Expanded: 2 },
    EventEmitter: class EventEmitter { constructor() { this.listeners = []; this.event = (cb) => { this.listeners.push(cb); }; } fire() { this.listeners.forEach(cb => cb()); } },
    TreeItem: class TreeItem {
        constructor(label, state) { this.label = label; this.collapsibleState = state; this.contextValue = ''; this.iconPath = undefined; this.description = ''; this.tooltip = ''; }
    }
});
const { OllamaModelsTreeProvider } = require('../out/ui/OllamaModelsTreeProvider.js');
const { OllamaService } = require('../out/services/OllamaService.js');

// Mock fetch to return models with sizes
global.fetch = async () => ({
    ok: true,
    json: async () => ({
        models: [
            { name: 'modelA:1', model: 'modelA:1', size: 1024 * 1024 * 512 },
            { name: 'modelB:1', model: 'modelB:1', size: 1024 * 50 }
        ]
    })
});

describe('OllamaModelsTreeProvider (CJS)', () => {
    it('maps models to tree items', async () => {
        const svc = new OllamaService('http://localhost:11434');
        const provider = new OllamaModelsTreeProvider(svc);
        const items = await provider.getChildren();
        assert.ok(Array.isArray(items));
        assert.ok(items.length >= 1);
        assert.equal(typeof items[0].label, 'string');
    });
});
