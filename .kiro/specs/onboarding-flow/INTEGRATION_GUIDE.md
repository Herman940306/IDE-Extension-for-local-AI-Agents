# Onboarding Flow - Integration Guide

**Project Creator:** Herman Swanepoel
**Version:** 1.0
**Last Updated:** 2025-10-13

---

## Quick Start Integration

### Step 1: Update package.json

Add commands to your `package.json`:

```json
{
  "contributes": {
    "commands": [
      {
        "command": "enterpriseAI.startOnboarding",
        "title": "Enterprise AI: Start Onboarding",
        "category": "Enterprise AI"
      },
      {
        "command": "enterpriseAI.restartOnboarding",
        "title": "Enterprise AI: Restart Onboarding",
        "category": "Enterprise AI"
      },
      {
        "command": "enterpriseAI.skipOnboarding",
        "title": "Enterprise AI: Skip Onboarding",
        "category": "Enterprise AI"
      },
      {
        "command": "enterpriseAI.resumeOnboarding",
        "title": "Enterprise AI: Resume Onboarding",
        "category": "Enterprise AI"
      },
      {
        "command": "enterpriseAI.openQuickStartGuide",
        "title": "Enterprise AI: Open Quick Start Guide",
        "category": "Enterprise AI"
      }
    ],
    "configuration": {
      "title": "Enterprise AI Agents",
      "properties": {
        "enterpriseAI.backend.url": {
          "type": "string",
          "default": "http://localhost",
          "description": "Backend server URL"
        },
        "enterpriseAI.backend.port": {
          "type": "number",
          "default": 8000,
          "description": "Backend server port"
        },
        "enterpriseAI.llm.provider": {
          "type": "string",
          "enum": ["ollama", "lmstudio", "cloud"],
          "default": "ollama",
          "description": "LLM provider"
        },
        "enterpriseAI.privacy.telemetry": {
          "type": "boolean",
          "default": false,
          "description": "Enable anonymous telemetry"
        },
        "enterpriseAI.privacy.cloudFallback": {
          "type": "boolean",
          "default": false,
          "description": "Enable cloud fallback"
        },
        "enterpriseAI.accessibility.screenReader": {
          "type": "boolean",
          "default": false,
          "description": "Enable screen reader optimizations"
        },
        "enterpriseAI.accessibility.keyboardShortcuts": {
          "type": "boolean",
          "default": true,
          "description": "Enable keyboard shortcuts"
        }
      }
    }
  }
}
```

### Step 2: Update extension.ts

Integrate onboarding into your extension activation:

```typescript
import * as vscode from "vscode";
import { OnboardingManager } from "./services/OnboardingManager";
import { registerOnboardingCommands } from "./commands/onboardingCommands";

let onboardingManager: OnboardingManager;

export async function activate(context: vscode.ExtensionContext) {
  console.log("Enterprise AI Agents extension activating...");

  try {
    // Initialize onboarding manager
    onboardingManager = new OnboardingManager(context);
    await onboardingManager.initialize();

    // Register onboarding commands
    registerOnboardingCommands(context, onboardingManager);

    // Handle activation (show onboarding for first-time users)
    await onboardingManager.handleActivation();

    console.log("Enterprise AI Agents extension activated successfully");
  } catch (error) {
    console.error("Failed to activate extension:", error);
    vscode.window.showErrorMessage(`Extension activation failed: ${error}`);
  }
}

export function deactivate() {
  if (onboardingManager) {
    onboardingManager.dispose();
  }
}
```

### Step 3: Create Media Directory (Optional)

If you want to add custom icons or images:

```bash
mkdir -p extension/media
# Add your logo, icons, screenshots here
```

---

## Advanced Integration

### Custom Skill Level Handling

Adapt tour content based on skill level:

```typescript
// In your extension code
const skillLevel = onboardingManager.getState().skillLevel;

if (skillLevel === "beginner") {
  // Show detailed tooltips
  await onboardingManager.showTooltip("detailed-help");
} else if (skillLevel === "advanced") {
  // Skip basic tooltips
  console.log("Advanced user - minimal guidance");
}
```

### Analytics Integration

Send onboarding analytics to your backend:

```typescript
// After onboarding completes
const analytics = onboardingManager.exportAnalytics();

// Send to your analytics service
await fetch("https://your-backend/analytics", {
  method: "POST",
  body: JSON.stringify(analytics),
});
```

### Custom Tooltips

Register custom tooltips for your features:

```typescript
// After onboarding completes
onboardingManager.registerTooltips();

// Show tooltip when user first uses a feature
await onboardingManager.showTooltip("your-feature-id");
```

### Backend Connection Testing

Implement actual connection testing:

```typescript
// In OnboardingManager.handleConnectionTest()
import { WebSocketClient } from './WebSocketClient';

private async handleConnectionTest(data: any): Promise<void> {
  try {
    const { backendUrl, backendPort } = data;
    const client = new WebSocketClient(backendUrl, backendPort);

    await client.connect();
    await client.ping();

    vscode.window.showInformationMessage('✓ Connection successful!');
  } catch (error) {
    vscode.window.showErrorMessage(
      `Connection failed: ${error}. Please check your configuration.`
    );
  }
}
```

---

## Testing Your Integration

### Manual Testing Checklist

1. **First-Time User Flow**

   ```bash
   # Clear workspace state to simulate first-time user
   # In VS Code: Developer: Clear Workspace State
   ```

   - [ ] Welcome screen appears on activation
   - [ ] Skill level selection works
   - [ ] "Get Started" proceeds to tour
   - [ ] "Skip Tour" skips onboarding

2. **Tour Flow**
   - [ ] All 5 steps display correctly
   - [ ] Next/Previous navigation works
   - [ ] Progress indicator updates
   - [ ] Keyboard navigation (arrows) works
   - [ ] "Skip Tour" works at any step

3. **Setup Wizard**
   - [ ] All 4 steps display correctly
   - [ ] Form validation works
   - [ ] Invalid URL shows error
   - [ ] Invalid port shows error
   - [ ] "Test Connection" button works
   - [ ] Configuration saves to VS Code settings

4. **Quick Start Guide**
   - [ ] Opens from completion message
   - [ ] Opens from command palette
   - [ ] Search functionality works
   - [ ] Navigation works
   - [ ] All sections display correctly

5. **State Persistence**
   - [ ] Close VS Code during onboarding
   - [ ] Reopen - should offer to resume
   - [ ] Complete onboarding
   - [ ] Reopen - should not show onboarding

6. **Commands**
   - [ ] `Start Onboarding` works
   - [ ] `Restart Onboarding` works (with confirmation)
   - [ ] `Skip Onboarding` works
   - [ ] `Resume Onboarding` works
   - [ ] `Open Quick Start Guide` works

7. **Accessibility**
   - [ ] Tab navigation works throughout
   - [ ] Enter/Space activates buttons
   - [ ] Escape dismisses panels
   - [ ] Screen reader announces content
   - [ ] High contrast mode looks good
   - [ ] Focus indicators visible

---

## Troubleshooting

### Issue: Onboarding doesn't start

**Symptoms:** Extension activates but no welcome screen

**Solutions:**

1. Check console for errors
2. Verify OnboardingManager initialized
3. Check workspace state: `context.workspaceState.get('enterpriseAI.onboarding.state')`
4. Clear workspace state and retry

### Issue: Webview not displaying

**Symptoms:** Blank panel or error

**Solutions:**

1. Check Content Security Policy in webview HTML
2. Verify `enableScripts: true` in webview options
3. Check browser console in webview (Developer: Open Webview Developer Tools)
4. Verify extension URI is correct

### Issue: State not persisting

**Symptoms:** Onboarding restarts every time

**Solutions:**

1. Check workspace state storage permissions
2. Verify `saveState()` is being called
3. Check for errors in console during save
4. Verify state schema matches

### Issue: Commands not appearing

**Symptoms:** Commands not in command palette

**Solutions:**

1. Verify `package.json` has command definitions
2. Check `registerOnboardingCommands()` is called
3. Reload window after changes
4. Check extension is activated

---

## Performance Optimization

### Lazy Loading

Webviews are created on-demand:

- Welcome panel: Created on first activation
- Tour panel: Created when user clicks "Get Started"
- Setup wizard: Created after tour completion
- Quick start guide: Created when requested

### Memory Management

All panels properly dispose resources:

```typescript
// Automatic cleanup on panel close
panel.onDidDispose(() => this.dispose());

// Manual cleanup
if (this.welcomePanel) {
  this.welcomePanel.hide(); // Triggers disposal
}
```

### State Persistence

State saves asynchronously to avoid blocking:

```typescript
// Non-blocking save
await this.saveState(); // Runs in background
```

---

## Security Best Practices

### Content Security Policy

All webviews use strict CSP:

```html
<meta
  http-equiv="Content-Security-Policy"
  content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline';"
/>
```

### Input Validation

All user inputs are validated:

- URLs: Must be valid HTTP/HTTPS
- Ports: Must be 1-65535
- Required fields: Cannot be empty

### Data Privacy

- No PII collected
- Telemetry opt-in only
- Local-first storage
- Configuration in VS Code settings (user-controlled)

---

## Deployment Checklist

Before deploying to production:

- [ ] All commands registered in package.json
- [ ] Configuration schema defined
- [ ] Extension activation tested
- [ ] First-time user flow tested
- [ ] Resume flow tested
- [ ] All accessibility features tested
- [ ] Error handling tested
- [ ] Performance benchmarked
- [ ] Documentation complete
- [ ] README updated with onboarding info

---

## Monitoring & Analytics

### Key Metrics to Track

1. **Completion Rate**

   ```typescript
   const rate = onboardingManager.getCompletionRate();
   // Target: > 90%
   ```

2. **Time to Complete**

   ```typescript
   const timeMs = onboardingManager.getTimeSpent();
   // Target: < 5 minutes (300,000ms)
   ```

3. **Drop-off Points**

   ```typescript
   const analytics = onboardingManager.exportAnalytics();
   const dropOff = analytics.dropOffPoint;
   // Identify where users abandon
   ```

4. **Skip Rate**
   ```typescript
   const isSkipped = onboardingManager.isSkipped();
   // Target: < 10%
   ```

### Analytics Events

The system tracks these events:

- `onboarding.started` - User begins onboarding
- `onboarding.completed` - User completes onboarding
- `onboarding.skipped` - User skips onboarding
- `step-completed` - User completes a step
- `step-skipped` - User skips a step

---

## Future Enhancements

### Planned Features

1. **Video Tutorials** (Phase 2)
   - Embed video in tour steps
   - Record custom walkthroughs

2. **Interactive Playground** (Phase 2)
   - Sandbox environment
   - Try features safely

3. **Personalized Recommendations** (Phase 2)
   - AI-driven feature suggestions
   - Based on usage patterns

4. **Multi-Language Support** (Phase 2)
   - i18n framework
   - Community translations

5. **Gamification** (Phase 2)
   - Badges for completion
   - Achievement system

### Extension Points

The system is designed for easy extension:

```typescript
// Add new tour step
const newStep: TourStep = {
  id: "tour-new-feature",
  title: "New Feature",
  description: "Description",
  icon: "🎉",
  content: "HTML content",
};

// Add new setup step
const newSetupStep: SetupStep = {
  id: "setup-new",
  title: "New Configuration",
  description: "Configure new feature",
  fields: [
    /* fields */
  ],
};

// Add new tooltip
tooltipManager.register({
  id: "new-feature-tip",
  title: "New Feature",
  description: "How to use it",
  shortcut: "Ctrl+Shift+N",
  position: "bottom",
  trigger: "hover",
  dismissible: true,
});
```

---

## Support & Resources

### Documentation

- [Implementation Guide](./IMPLEMENTATION.md)
- [Requirements](./requirements.md)
- [Design Document](./design.md)
- [Task List](./tasks.md)

### Getting Help

- GitHub Issues: [repository URL]
- Discord Community: [discord URL]
- Email Support: [email]

### Contributing

- Fork the repository
- Create feature branch
- Submit pull request
- Follow code style guidelines

---

## License

[Your License Here]

---

**Project Creator:** Herman Swanepoel
**Document Version:** 1.0
**Last Updated:** 2025-10-13

**Status:** ✅ Production Ready
