const assert = require('assert').strict;
const { OllamaService } = require('../out/services/OllamaService.js');

describe('OllamaService (CJS)', () => {
    it('lists models from /api/tags', async () => {
        global.fetch = async () => ({ ok: true, json: async () => ({ models: [{ name: 'llama3.1:8b', model: 'llama3.1:8b' }] }) });
        const svc = new OllamaService('http://localhost:11434');
        const models = await svc.listModels();
        assert.equal(models.length, 1);
        assert.equal(models[0].name, 'llama3.1:8b');
    });

    it('throws on non-ok response', async () => {
        global.fetch = async () => ({ ok: false, status: 500 });
        const svc = new OllamaService('http://localhost:11434');
        await assert.rejects(() => svc.listModels());
    });
});
