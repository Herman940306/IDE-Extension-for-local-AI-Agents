import { expect, test, type Page } from '@playwright/test';

type ChatMessage = {
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
};

type ChatSeed = {
  id: string;
  title: string;
  messages: ChatMessage[];
  timestamp: number;
};

type OpenAppOptions = {
  beforeNavigate?: () => Promise<void> | void;
  seedChats?: () => ChatSeed[];
  resetChats?: boolean;
};

const fixturePath = 'tests/fixtures/sample-attachment.txt';

const messageInputRole = /Ask anything|Backend unavailable|Connecting/;

const waitForConnection = async (page: Page) => {
  await expect(page.getByText('🟢 Connected')).toBeVisible({ timeout: 15_000 });
};

const openApp = async (page: Page, options: OpenAppOptions = {}) => {
  if (options.beforeNavigate) {
    await options.beforeNavigate();
  }

  const seededChats = options.seedChats?.();
  const shouldReset = options.resetChats ?? true;

  await page.addInitScript(({ chats, reset }) => {
    const storageKey = 'auraIA_chats';
    const sessionMarker = '__auraInitChatReset';

    if (Array.isArray(chats)) {
      window.localStorage.setItem(storageKey, JSON.stringify(chats));
      window.sessionStorage.setItem(sessionMarker, '1');
      return;
    }

    if (reset && !window.sessionStorage.getItem(sessionMarker)) {
      window.localStorage.removeItem(storageKey);
      window.sessionStorage.setItem(sessionMarker, '1');
    }
  }, { chats: seededChats, reset: shouldReset });

  await page.goto('/');
  await waitForConnection(page);
};

const getInput = (page: Page) => page.getByRole('textbox', { name: messageInputRole });

test.describe('AuraIA smoke coverage', () => {
  test('renders core layout and branding', async ({ page }) => {
    await openApp(page);

    await expect(page.locator('.app')).toBeVisible();
    await expect(page.locator('.sidebar')).toBeVisible();
    await expect(page.locator('.logo-text')).toContainText('AuraIA');
    await expect(page.locator('.logo-tagline')).toContainText('The Future Beside You');
    await expect(page.locator('.main-content')).toBeVisible();
    await expect(page.locator('.input-container')).toBeVisible();
    await expect(page.getByText('Herman Swanepoel')).toBeVisible();

    test.info().annotations.push({ type: 'status', description: 'Layout & branding verified' });
  });

  test('shows connection indicator once backend is reachable', async ({ page }) => {
    await openApp(page);

    const status = page.locator('.status');
    await expect(status).toContainText('Connected');

    test.info().annotations.push({ type: 'status', description: 'Backend connection indicator working' });
  });

  test('switches interaction modes between Chat, Agent, and Edit', async ({ page }) => {
    await openApp(page);

    const chatBtn = page.getByRole('button', { name: '💬 Chat' });
    const agentBtn = page.getByRole('button', { name: '🤖 Agent' });
    const editBtn = page.getByRole('button', { name: '✏️ Edit' });

    await chatBtn.click();
    await expect(chatBtn).toHaveClass(/active/);

    await agentBtn.click();
    await expect(agentBtn).toHaveClass(/active/);
    await expect(chatBtn).not.toHaveClass(/active/);

    await editBtn.click();
    await expect(editBtn).toHaveClass(/active/);
    await expect(agentBtn).not.toHaveClass(/active/);

    test.info().annotations.push({ type: 'status', description: 'Interaction mode buttons working' });
  });

  test('toggles between local and cloud modes and surfaces banner messages', async ({ page }) => {
    await openApp(page);

    const slider = page.locator('.toggle-slider');
    await expect(page.getByText('💻 Local')).toBeVisible();

    await slider.click({ force: true });
    await expect(page.getByText('☁️ Cloud')).toBeVisible({ timeout: 5_000 });
    await expect(page.locator('.status-banner')).toContainText(/Connected to Enterprise AI Agents Backend|Switched to|Already in/);

    await slider.click({ force: true });
    await expect(page.getByText('💻 Local')).toBeVisible({ timeout: 5_000 });

    test.info().annotations.push({ type: 'status', description: 'Local / cloud toggle verified' });
  });

  test('attaches a file, displays the attachment chip, and clears after sending', async ({ page }) => {
    await openApp(page);

    await page.locator('.attach-btn').click();
    await page.locator('input[type="file"]').setInputFiles(fixturePath);

    const chip = page.locator('.attached-files .file-chip');
    await expect(chip).toContainText('sample-attachment.txt');

    const input = getInput(page);
    await input.fill('Message with attachment');
    const sendBtn = page.locator('.send-btn');
    await sendBtn.click();

    await expect(page.locator('.message.user').last()).toContainText('Message with attachment');
    await expect(page.locator('.attached-files .file-chip')).toHaveCount(0);

    test.info().annotations.push({ type: 'status', description: 'Attachment upload and send path working' });
  });

  test('persists chat history across reloads', async ({ page }) => {
    await openApp(page);

    const message = `Persistent message ${Date.now()}`;
    const input = getInput(page);
    await input.fill(message);
    await input.press('Enter');

    await expect(page.locator('.message.user').last()).toContainText(message);

    await page.waitForFunction((expected) => {
      const chatsRaw = window.localStorage.getItem('auraIA_chats');
      if (!chatsRaw) return false;
      try {
        const chats = JSON.parse(chatsRaw) as Array<{ messages?: Array<{ content?: string }> }>;
        return chats.some((chat) => chat.messages?.some((m) => m.content === expected));
      } catch {
        return false;
      }
    }, message);

    await page.reload();
    await waitForConnection(page);

    const historyItem = page.locator('.chat-history .chat-item').first();
    await expect(historyItem).toBeVisible({ timeout: 10_000 });
    await historyItem.click();

    await expect(page.locator('.message.user').last()).toContainText(message);

    test.info().annotations.push({ type: 'status', description: 'Chat memory retained after reload' });
  });

  test('deletes chat entries from history', async ({ page }) => {
    await openApp(page);

    const input = getInput(page);
    await input.fill('Chat slated for deletion');
    await input.press('Enter');
    await page.getByRole('button', { name: '+ New chat' }).click();

    const deleteBtn = page.locator('.chat-history .chat-item .delete-btn').first();
    await deleteBtn.click();
    await expect(page.locator('.chat-history .chat-item')).toHaveCount(0);

    test.info().annotations.push({ type: 'status', description: 'Chat deletion workflow verified' });
  });

  test('renders long assistant feedback without truncation', async ({ page }) => {
    const longContent = (() => {
      const intro = 'This is a deliberately long assistant reply used to validate wrapping.';
      const lines = Array.from({ length: 30 }, (_, index) => `Line ${(index + 1).toString().padStart(2, '0')} of detailed guidance.`);
      const code = ['```', 'function sample() {', "  console.log('Line coverage check');", '}', '```'];
      const outro = 'Final summary line confirming the end of the message.';
      return [intro, ...lines, ...code, outro].join('\n');
    })();

    await openApp(page, {
      seedChats: () => [{
        id: 'chat-long-response',
        title: 'Long response validation',
        messages: [{ role: 'assistant', content: longContent, timestamp: Date.now() }],
        timestamp: Date.now(),
      }],
    });

    await page.locator('.chat-history .chat-item').first().click();

    const assistantMessage = page.locator('.message.assistant');
    await expect(assistantMessage).toContainText('Line 30 of detailed guidance.');
    await expect(assistantMessage.locator('pre code')).toContainText("console.log('Line coverage check');");
    await expect(assistantMessage).toContainText('Final summary line confirming the end of the message.');

    test.info().annotations.push({ type: 'status', description: 'Assistant feedback rendering intact' });
  });

  test('accepts voice input and surfaces listening banner', async ({ page }) => {
    await openApp(page, {
      beforeNavigate: async () => {
        await page.addInitScript(() => {
          class MockSpeechRecognition {
            continuous = false;
            interimResults = false;
            lang = 'en-US';
            onresult: ((event: unknown) => void) | null = null;
            onerror: ((event: unknown) => void) | null = null;
            onend: (() => void) | null = null;
            start() {
              // @ts-ignore - testing hook
              window.__mockSpeechStarted = true;
              setTimeout(() => {
                this.onresult?.({ results: [[{ transcript: 'voice prompt automation sample' }]] } as unknown);
                this.onend?.();
              }, 10);
            }
            stop() {
              this.onend?.();
            }
          }

          // @ts-expect-error - exposing mock globally for the app
          window.SpeechRecognition = MockSpeechRecognition;
          // @ts-expect-error - exposing mock globally for the app
          window.webkitSpeechRecognition = MockSpeechRecognition;
        });
      },
    });

    const voiceBtn = page.locator('.voice-btn');
    await voiceBtn.click();

    await expect(page.locator('.status-banner')).toContainText('Listening');
    await expect(getInput(page)).toHaveValue('voice prompt automation sample');

    test.info().annotations.push({ type: 'status', description: 'Voice prompt pipeline operating' });
  });

  test('supports sending multiple sequential messages in order', async ({ page }) => {
    await openApp(page);

    const input = getInput(page);
    await input.fill('First message');
    await input.press('Enter');
    await input.fill('Second message');
    await input.press('Enter');
    await input.fill('Third message');
    await input.press('Enter');

    const userMessages = page.locator('.message.user');
    await expect(userMessages).toHaveCount(3);
    await expect(userMessages.nth(0)).toContainText('First message');
    await expect(userMessages.nth(1)).toContainText('Second message');
    await expect(userMessages.nth(2)).toContainText('Third message');

    test.info().annotations.push({ type: 'status', description: 'Sequential messaging verified' });
  });

  test('resets chat state when starting a new chat', async ({ page }) => {
    await openApp(page);

    const input = getInput(page);
    await input.fill('Message before reset');
    await input.press('Enter');

    await page.getByRole('button', { name: '+ New chat' }).click();
    await expect(page.getByText('Ready when you are.')).toBeVisible();

    test.info().annotations.push({ type: 'status', description: 'New chat reset confirmed' });
  });

  test('shows banner notifications when mode changes', async ({ page }) => {
    await openApp(page);

    await page.locator('.toggle-slider').click({ force: true });
    await expect(page.locator('.status-banner')).toBeVisible({ timeout: 5_000 });
    await page.locator('.toggle-slider').click({ force: true });
    await expect(page.locator('.status-banner')).toBeVisible({ timeout: 5_000 });

    test.info().annotations.push({ type: 'status', description: 'Banner notifications verified' });
  });
});
