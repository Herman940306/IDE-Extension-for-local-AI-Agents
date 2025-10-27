# Aura AI Assistant - VS Code Extension

![AuraIA Logo](images/AuraIA_logo.jpg)

**Project Creator:** Herman Swanepoel

## Features

- ✅ Code Generation
- ✅ Code Refactoring
- ✅ Code Explanation
- ✅ Bug Fixing
- ✅ Real-time Backend Connection

## Setup

```bash
cd extension
npm install
npm run compile
```

To enable live TypeScript rebuilds during development:

```bash
npm run watch
```

## Development

1. Open in VS Code
2. Press F5 to debug
3. Test commands in new window

## Commands

- `Aura: Generate Code` - Generate code from description
- `Aura: Refactor Code` - Refactor selected code
- `Aura: Explain Code` - Explain selected code
- `Aura: Fix Bugs` - Fix bugs in current file

## Requirements

- Backend running: <http://127.0.0.1:8001>
- WebSocket: `ws://127.0.0.1:8001/ws`

## Documentation

- Project Overview: [docs/overview.md](../docs/overview.md)
- Product Requirements (PRD): [AuraIA_PRD.md](../AuraIA IDE Vision and Roadmap/AuraIA_PRD.md)

## Packaging

- `npm run package` builds the extension and produces a `.vsix` file in the `extension` directory using the local `vsce` binary.
- `npm run package:publish` publishes directly to the VS Code Marketplace. Set the `VSCE_PAT` environment variable to a Personal Access Token with the **Marketplace** publish scope before running this command.
- Both commands run `npm run compile` first, ensuring the TypeScript output is up to date.

## Accessibility

- Status bar items announce connection state and suggestion statistics through screen readers.
- Agent status tree items expose descriptive labels for status, task counts, success rate, and last activity timestamps.

## Privacy & Telemetry

- Telemetry is **disabled by default**. The extension respects a privacy-first posture.
- Enable or disable anonymous productivity metrics from VS Code Settings via `enterpriseAI.privacy.allowTelemetry` or run the command `Aura: Toggle Telemetry` from the Command Palette.
- When disabled, analytics data is neither collected nor stored; toggling the setting immediately clears the in-memory trackers.
