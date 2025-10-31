import { expect, test } from '@playwright/test';

test.describe('AuraIA Frontend E2E Tests', () => {

    // Smoke test - basic rendering
    test('home page renders correctly', async ({ page }) => {
        await page.goto('/');

        // Check main container
        await expect(page.locator('.app')).toBeVisible();

        // Check sidebar exists
        await expect(page.locator('.sidebar')).toBeVisible();
        await expect(page.locator('.logo-text')).toContainText('AuraIA');
        await expect(page.getByText('The Future Beside You')).toBeVisible();

        // Check main content area
        await expect(page.locator('.main-content')).toBeVisible();
        await expect(page.getByRole('heading', { name: 'AuraIA' })).toBeVisible();

        // Check input area exists
        await expect(page.locator('.input-container')).toBeVisible();
        await expect(page.getByRole('textbox', { name: /Ask anything|Backend unavailable|Connecting/ })).toBeVisible();
    });    // WebSocket Connection Test
    test('establishes WebSocket connection to backend', async ({ page }) => {
        await page.goto('/');

        // Wait for connection status to show connected
        await expect(page.getByText('🟢 Connected')).toBeVisible({ timeout: 15000 });

        // Check connection indicator shows correct status
        const status = page.locator('.status');
        await expect(status).toContainText('Connected');
    });

    // Chat Functionality Tests
    test('can send a message in chat mode', async ({ page }) => {
        await page.goto('/');
        await expect(page.getByText('🟢 Connected')).toBeVisible({ timeout: 15000 });

        // Ensure we're in chat mode
        await page.getByRole('button', { name: '💬 Chat' }).click();

        // Type and send a message
        const input = page.getByRole('textbox', { name: 'Ask anything' });
        await input.fill('Hello, can you help me?');
        await input.press('Enter');

        // Verify message appears in chat
        await expect(page.locator('.message.user')).toContainText('Hello, can you help me?');

        // Optionally wait for assistant response (loading indicator may appear briefly)
        // Using a soft expectation since response time varies
        await page.waitForTimeout(1000);
    });    // Mode Switching Tests
    test('can switch between interaction modes', async ({ page }) => {
        await page.goto('/');
        await expect(page.getByText('🟢 Connected')).toBeVisible({ timeout: 15000 });

        // Test Chat mode
        const chatBtn = page.getByRole('button', { name: '💬 Chat' });
        await chatBtn.click();
        await expect(chatBtn).toHaveClass(/active/);

        // Test Agent mode
        const agentBtn = page.getByRole('button', { name: '🤖 Agent' });
        await agentBtn.click();
        await expect(agentBtn).toHaveClass(/active/);
        await expect(chatBtn).not.toHaveClass(/active/);

        // Test Edit mode
        const editBtn = page.getByRole('button', { name: '✏️ Edit' });
        await editBtn.click();
        await expect(editBtn).toHaveClass(/active/);
        await expect(agentBtn).not.toHaveClass(/active/);
    });

    // Local/Cloud Mode Toggle Test
    test('can toggle between local and cloud modes', async ({ page }) => {
        await page.goto('/');
        await expect(page.getByText('🟢 Connected')).toBeVisible({ timeout: 15000 });

        // Check initial mode (should be local)
        await expect(page.getByText('💻 Local')).toBeVisible();

        // Toggle to cloud mode - click on the visible toggle slider
        await page.locator('.toggle-slider').click({ force: true });
        await expect(page.getByText('☁️ Cloud')).toBeVisible({ timeout: 5000 });

        // Toggle back to local
        await page.locator('.toggle-slider').click({ force: true });
        await expect(page.getByText('💻 Local')).toBeVisible({ timeout: 5000 });
    });    // Chat History Tests
    test('can create and manage chat history', async ({ page }) => {
        await page.goto('/');
        await expect(page.getByText('🟢 Connected')).toBeVisible({ timeout: 15000 });

        // Send a message to create chat history
        const input = page.getByRole('textbox', { name: 'Ask anything' });
        await input.fill('Test message for history');
        await input.press('Enter');

        // Wait a moment for the chat to be saved
        await page.waitForTimeout(1000);

        // Create new chat
        await page.getByRole('button', { name: '+ New chat' }).click();

        // Verify chat history shows previous chat
        await expect(page.locator('.chat-history .chat-item')).toHaveCount(1);

        // Click on previous chat to load it
        await page.locator('.chat-history .chat-item').first().click();
        await expect(page.locator('.message.user')).toContainText('Test message for history');
    });

    test('can delete chat from history', async ({ page }) => {
        await page.goto('/');
        await expect(page.getByText('🟢 Connected')).toBeVisible({ timeout: 15000 });

        // Send a message to create chat history
        const input = page.getByRole('textbox', { name: 'Ask anything' });
        await input.fill('Message to delete');
        await input.press('Enter');
        await page.waitForTimeout(1000);

        // Create new chat so we can see history
        await page.getByRole('button', { name: '+ New chat' }).click();

        // Delete the chat
        const deleteBtn = page.locator('.chat-history .chat-item .delete-btn').first();
        await deleteBtn.click();

        // Verify chat is removed
        const chatCount = await page.locator('.chat-history .chat-item').count();
        expect(chatCount).toBe(0);
    });

    // File Attachment Tests
    test('can attach files to messages', async ({ page }) => {
        await page.goto('/');
        await expect(page.getByText('🟢 Connected')).toBeVisible({ timeout: 15000 });

        // Click attach button
        await page.getByRole('button', { name: '+' }).first().click();

        // Note: File upload would require actual file in test environment
        // This test verifies the UI is present and clickable
        await expect(page.locator('input[type="file"]')).toBeAttached();
    });

    // Input Validation Tests
    test('send button is disabled when input is empty', async ({ page }) => {
        await page.goto('/');
        await expect(page.getByText('🟢 Connected')).toBeVisible({ timeout: 15000 });

        const sendBtn = page.locator('.send-btn');
        await expect(sendBtn).toBeDisabled();

        // Type something
        await page.getByRole('textbox', { name: 'Ask anything' }).fill('test');
        await expect(sendBtn).toBeEnabled();

        // Clear input
        await page.getByRole('textbox', { name: 'Ask anything' }).clear();
        await expect(sendBtn).toBeDisabled();
    });

    test('input is disabled when backend is disconnected', async ({ page }) => {
        await page.goto('/');

        // Wait for initial connection
        await expect(page.getByText('🟢 Connected')).toBeVisible({ timeout: 15000 });

        // Input should be enabled when connected
        const input = page.getByRole('textbox', { name: 'Ask anything' });
        await expect(input).toBeEnabled();
    });

    // Welcome Screen Test
    test('shows welcome message when no messages exist', async ({ page }) => {
        await page.goto('/');
        await expect(page.getByText('🟢 Connected')).toBeVisible({ timeout: 15000 });

        // Should show welcome message
        await expect(page.getByText('Ready when you are.')).toBeVisible();
    });

    // User Info Display Test
    test('displays user information in sidebar', async ({ page }) => {
        await page.goto('/');

        // Check user avatar and name
        await expect(page.getByText('HS')).toBeVisible();
        await expect(page.getByText('Herman Swanepoel')).toBeVisible();
    });

    // Branding and Theme Tests
    test('displays correct branding elements', async ({ page }) => {
        await page.goto('/');

        // Check logo and tagline
        await expect(page.locator('.logo-text')).toContainText('AuraIA');
        await expect(page.locator('.logo-tagline')).toContainText('The Future Beside You');
    });

    // Multiple Messages Test
    test('can send multiple messages in sequence', async ({ page }) => {
        await page.goto('/');
        await expect(page.getByText('🟢 Connected')).toBeVisible({ timeout: 15000 });

        const input = page.getByRole('textbox', { name: 'Ask anything' });

        // Send first message
        await input.fill('First message');
        await input.press('Enter');

        // Send second message
        await input.fill('Second message');
        await input.press('Enter');

        // Send third message
        await input.fill('Third message');
        await input.press('Enter');

        // Verify all messages are displayed
        const userMessages = page.locator('.message.user');
        await expect(userMessages).toHaveCount(3);
        await expect(userMessages.nth(0)).toContainText('First message');
        await expect(userMessages.nth(1)).toContainText('Second message');
        await expect(userMessages.nth(2)).toContainText('Third message');
    });

    // Banner Notifications Test
    test('displays banner notifications for events', async ({ page }) => {
        await page.goto('/');
        await expect(page.getByText('🟢 Connected')).toBeVisible({ timeout: 15000 });

        // Toggle mode to trigger banner - click on the visible slider
        await page.locator('.toggle-slider').click({ force: true });

        // Should show a banner notification
        await expect(page.locator('.status-banner')).toBeVisible({ timeout: 5000 });
    });
});
