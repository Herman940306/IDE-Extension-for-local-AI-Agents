/**
 * Setup Wizard - Initial configuration wizard
 *
 * Guides users through essential configuration:
 * - Backend connection
 * - LLM provider selection
 * - Privacy preferences
 * - Accessibility settings
 *
 * Project Creator: Herman Swanepoel
 */

import * as vscode from "vscode";

export interface SetupStep {
  id: string;
  title: string;
  description: string;
  fields: SetupField[];
}

export interface SetupField {
  id: string;
  type: "text" | "select" | "checkbox" | "number";
  label: string;
  placeholder?: string;
  defaultValue?: any;
  options?: SelectOption[];
  helpText?: string;
  required: boolean;
}

export interface SelectOption {
  value: string;
  label: string;
  description?: string;
}

export interface ValidationResult {
  isValid: boolean;
  errors: ValidationError[];
}

export interface ValidationError {
  fieldId: string;
  message: string;
}

export interface SetupConfiguration {
  backendUrl: string;
  backendPort: number;
  llmProvider: "ollama" | "lmstudio" | "cloud";
  telemetryEnabled: boolean;
  cloudFallbackEnabled: boolean;
  screenReaderEnabled: boolean;
  keyboardShortcutsEnabled: boolean;
}

export class SetupWizard {
  public static currentPanel: SetupWizard | undefined;
  private readonly panel: vscode.WebviewPanel;
  private disposables: vscode.Disposable[] = [];
  private currentStepIndex: number = 0;
  private steps: SetupStep[];
  private configuration: Partial<SetupConfiguration> = {};

  private onNextEmitter = new vscode.EventEmitter<number>();
  private onPreviousEmitter = new vscode.EventEmitter<number>();
  private onCompleteEmitter = new vscode.EventEmitter<SetupConfiguration>();
  private onValidateEmitter = new vscode.EventEmitter<{
    step: number;
    data: any;
  }>();

  public readonly onNext = this.onNextEmitter.event;
  public readonly onPrevious = this.onPreviousEmitter.event;
  public readonly onComplete = this.onCompleteEmitter.event;
  public readonly onValidate = this.onValidateEmitter.event;

  private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
    this.panel = panel;
    this.steps = this.getSetupSteps();

    // Set up panel content
    this.updateWebviewContent(extensionUri);

    // Handle messages from webview
    this.panel.webview.onDidReceiveMessage(
      (message) => this.handleMessage(message),
      null,
      this.disposables,
    );

    // Handle panel disposal
    this.panel.onDidDispose(() => this.dispose(), null, this.disposables);
  }

  /**
   * Create or show the setup wizard
   */
  public static createOrShow(extensionUri: vscode.Uri): SetupWizard {
    const column = vscode.ViewColumn.One;

    // If panel already exists, show it
    if (SetupWizard.currentPanel) {
      SetupWizard.currentPanel.panel.reveal(column);
      return SetupWizard.currentPanel;
    }

    // Create new panel
    const panel = vscode.window.createWebviewPanel(
      "enterpriseAI.setup",
      "Setup Wizard",
      column,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [vscode.Uri.joinPath(extensionUri, "media")],
      },
    );

    SetupWizard.currentPanel = new SetupWizard(panel, extensionUri);
    return SetupWizard.currentPanel;
  }

  /**
   * Show the setup wizard at a specific step
   */
  public async show(stepIndex?: number): Promise<void> {
    if (
      stepIndex !== undefined &&
      stepIndex >= 0 &&
      stepIndex < this.steps.length
    ) {
      this.currentStepIndex = stepIndex;
      this.updateWebviewContent(this.panel.webview.options as any);
    }
    this.panel.reveal();
  }

  /**
   * Hide the setup wizard
   */
  public hide(): void {
    this.panel.dispose();
  }

  /**
   * Navigate to next step
   */
  public async next(): Promise<void> {
    if (this.currentStepIndex < this.steps.length - 1) {
      this.currentStepIndex++;
      this.updateWebviewContent(this.panel.webview.options as any);
      this.onNextEmitter.fire(this.currentStepIndex);
    }
  }

  /**
   * Navigate to previous step
   */
  public async previous(): Promise<void> {
    if (this.currentStepIndex > 0) {
      this.currentStepIndex--;
      this.updateWebviewContent(this.panel.webview.options as any);
      this.onPreviousEmitter.fire(this.currentStepIndex);
    }
  }

  /**
   * Complete the setup
   */
  public async complete(): Promise<void> {
    this.onCompleteEmitter.fire(this.configuration as SetupConfiguration);
  }

  /**
   * Validate current step
   */
  public async validateStep(data: any): Promise<ValidationResult> {
    const currentStep = this.steps[this.currentStepIndex];
    const errors: ValidationError[] = [];

    for (const field of currentStep.fields) {
      const value = data[field.id];

      // Required field validation
      if (
        field.required &&
        (value === undefined || value === null || value === "")
      ) {
        errors.push({
          fieldId: field.id,
          message: `${field.label} is required`,
        });
        continue;
      }

      // Type-specific validation
      if (value !== undefined && value !== null && value !== "") {
        switch (field.id) {
          case "backendUrl":
            if (!this.isValidUrl(value)) {
              errors.push({
                fieldId: field.id,
                message: "Please enter a valid URL (e.g., http://localhost)",
              });
            }
            break;

          case "backendPort":
            if (!this.isValidPort(value)) {
              errors.push({
                fieldId: field.id,
                message: "Port must be between 1 and 65535",
              });
            }
            break;
        }
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
    };
  }

  /**
   * Validate URL format
   */
  private isValidUrl(url: string): boolean {
    try {
      const parsed = new URL(url);
      return ["http:", "https:"].includes(parsed.protocol);
    } catch {
      return false;
    }
  }

  /**
   * Validate port number
   */
  private isValidPort(port: any): boolean {
    const num = Number(port);
    return Number.isInteger(num) && num >= 1 && num <= 65535;
  }

  /**
   * Dispose of the panel and clean up resources
   */
  public dispose(): void {
    SetupWizard.currentPanel = undefined;

    // Dispose of panel
    this.panel.dispose();

    // Dispose of event emitters
    this.onNextEmitter.dispose();
    this.onPreviousEmitter.dispose();
    this.onCompleteEmitter.dispose();
    this.onValidateEmitter.dispose();

    // Dispose of all disposables
    while (this.disposables.length) {
      const disposable = this.disposables.pop();
      if (disposable) {
        disposable.dispose();
      }
    }
  }

  /**
   * Handle messages from the webview
   */
  private async handleMessage(message: any): Promise<void> {
    switch (message.command) {
      case "next":
        // Validate before proceeding
        const validation = await this.validateStep(message.data);
        if (validation.isValid) {
          // Save data
          Object.assign(this.configuration, message.data);
          await this.next();
        } else {
          // Send validation errors back to webview
          this.panel.webview.postMessage({
            command: "validationErrors",
            errors: validation.errors,
          });
        }
        break;

      case "previous":
        await this.previous();
        break;

      case "complete":
        // Validate final step
        const finalValidation = await this.validateStep(message.data);
        if (finalValidation.isValid) {
          Object.assign(this.configuration, message.data);
          await this.complete();
        } else {
          this.panel.webview.postMessage({
            command: "validationErrors",
            errors: finalValidation.errors,
          });
        }
        break;

      case "testConnection":
        // Emit event for connection testing
        this.onValidateEmitter.fire({
          step: this.currentStepIndex,
          data: message.data,
        });
        break;
    }
  }

  /**
   * Update webview content
   */
  private updateWebviewContent(extensionUri: any): void {
    this.panel.webview.html = this.getWebviewContent();
  }

  /**
   * Get setup steps
   */
  private getSetupSteps(): SetupStep[] {
    return [
      {
        id: "backend",
        title: "Backend Connection",
        description: "Configure connection to the AI backend server",
        fields: [
          {
            id: "backendUrl",
            type: "text",
            label: "Backend URL",
            placeholder: "http://localhost",
            defaultValue: "http://localhost",
            helpText: "The URL where your AI backend is running",
            required: true,
          },
          {
            id: "backendPort",
            type: "number",
            label: "Backend Port",
            placeholder: "8000",
            defaultValue: 8000,
            helpText: "The port number for the backend server",
            required: true,
          },
        ],
      },
      {
        id: "llm",
        title: "LLM Provider",
        description: "Choose your preferred language model provider",
        fields: [
          {
            id: "llmProvider",
            type: "select",
            label: "LLM Provider",
            defaultValue: "ollama",
            options: [
              {
                value: "ollama",
                label: "Ollama",
                description:
                  "Run models locally with Ollama (recommended for privacy)",
              },
              {
                value: "lmstudio",
                label: "LM Studio",
                description: "Use LM Studio for local model inference",
              },
              {
                value: "cloud",
                label: "Cloud Provider",
                description: "Use cloud-based LLMs (OpenAI, Anthropic, etc.)",
              },
            ],
            helpText: "Select how you want to run AI models",
            required: true,
          },
        ],
      },
      {
        id: "privacy",
        title: "Privacy Preferences",
        description: "Configure your privacy and data sharing preferences",
        fields: [
          {
            id: "cloudFallbackEnabled",
            type: "checkbox",
            label: "Enable cloud fallback",
            defaultValue: false,
            helpText:
              "Allow fallback to cloud LLMs if local models are unavailable",
            required: false,
          },
          {
            id: "telemetryEnabled",
            type: "checkbox",
            label: "Enable telemetry",
            defaultValue: false,
            helpText:
              "Help improve the extension by sending anonymous usage data",
            required: false,
          },
        ],
      },
      {
        id: "accessibility",
        title: "Accessibility",
        description: "Configure accessibility features",
        fields: [
          {
            id: "screenReaderEnabled",
            type: "checkbox",
            label: "Enable screen reader support",
            defaultValue: false,
            helpText: "Optimize for screen reader usage",
            required: false,
          },
          {
            id: "keyboardShortcutsEnabled",
            type: "checkbox",
            label: "Enable keyboard shortcuts",
            defaultValue: true,
            helpText: "Use keyboard shortcuts for quick access",
            required: false,
          },
        ],
      },
    ];
  }

  /**
   * Get the webview HTML content
   */
  private getWebviewContent(): string {
    const currentStep = this.steps[this.currentStepIndex];
    const stepNumber = this.currentStepIndex + 1;
    const totalSteps = this.steps.length;
    const isFirstStep = this.currentStepIndex === 0;
    const isLastStep = this.currentStepIndex === this.steps.length - 1;

    // Generate form fields HTML
    const fieldsHtml = currentStep.fields
      .map((field) => {
        const savedValue =
          (this.configuration as any)[field.id] ?? field.defaultValue;

        switch (field.type) {
          case "text":
          case "number":
            return `
            <div class="field">
              <label for="${field.id}">
                ${field.label}${field.required ? ' <span class="required">*</span>' : ""}
              </label>
              <input 
                type="${field.type}" 
                id="${field.id}" 
                name="${field.id}"
                placeholder="${field.placeholder || ""}"
                value="${savedValue || ""}"
                ${field.required ? "required" : ""}
                aria-describedby="${field.id}-help ${field.id}-error"
              />
              ${field.helpText ? `<p class="help-text" id="${field.id}-help">${field.helpText}</p>` : ""}
              <p class="error-text" id="${field.id}-error" role="alert" aria-live="polite"></p>
            </div>
          `;

          case "select":
            return `
            <div class="field">
              <label for="${field.id}">
                ${field.label}${field.required ? ' <span class="required">*</span>' : ""}
              </label>
              <select 
                id="${field.id}" 
                name="${field.id}"
                ${field.required ? "required" : ""}
                aria-describedby="${field.id}-help ${field.id}-error"
              >
                ${field.options
                  ?.map(
                    (opt) => `
                  <option value="${opt.value}" ${savedValue === opt.value ? "selected" : ""}>
                    ${opt.label}
                  </option>
                `,
                  )
                  .join("")}
              </select>
              ${field.helpText ? `<p class="help-text" id="${field.id}-help">${field.helpText}</p>` : ""}
              <p class="error-text" id="${field.id}-error" role="alert" aria-live="polite"></p>
            </div>
          `;

          case "checkbox":
            return `
            <div class="field checkbox-field">
              <label>
                <input 
                  type="checkbox" 
                  id="${field.id}" 
                  name="${field.id}"
                  ${savedValue ? "checked" : ""}
                  aria-describedby="${field.id}-help"
                />
                <span>${field.label}</span>
              </label>
              ${field.helpText ? `<p class="help-text" id="${field.id}-help">${field.helpText}</p>` : ""}
            </div>
          `;

          default:
            return "";
        }
      })
      .join("");

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline';">
  <title>Setup Wizard - Step ${stepNumber} of ${totalSteps}</title>
  <style>
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: var(--vscode-font-family);
      font-size: var(--vscode-font-size);
      color: var(--vscode-foreground);
      background-color: var(--vscode-editor-background);
      padding: 2rem;
      line-height: 1.6;
    }

    .container {
      max-width: 600px;
      margin: 0 auto;
    }

    .progress-bar {
      width: 100%;
      height: 4px;
      background-color: var(--vscode-editor-inactiveSelectionBackground);
      border-radius: 2px;
      margin-bottom: 2rem;
    }

    .progress-fill {
      height: 100%;
      background-color: var(--vscode-progressBar-background);
      transition: width 0.3s ease;
      width: ${(stepNumber / totalSteps) * 100}%;
    }

    .step-indicator {
      text-align: center;
      color: var(--vscode-descriptionForeground);
      font-size: 0.9rem;
      margin-bottom: 2rem;
    }

    .header {
      margin-bottom: 2rem;
    }

    h1 {
      font-size: 1.8rem;
      font-weight: 600;
      margin-bottom: 0.5rem;
    }

    .description {
      color: var(--vscode-descriptionForeground);
      font-size: 1rem;
    }

    .form {
      margin-bottom: 2rem;
    }

    .field {
      margin-bottom: 1.5rem;
    }

    label {
      display: block;
      font-weight: 500;
      margin-bottom: 0.5rem;
      color: var(--vscode-foreground);
    }

    .required {
      color: var(--vscode-errorForeground);
    }

    input[type="text"],
    input[type="number"],
    select {
      width: 100%;
      padding: 0.5rem;
      font-family: var(--vscode-font-family);
      font-size: var(--vscode-font-size);
      color: var(--vscode-input-foreground);
      background-color: var(--vscode-input-background);
      border: 1px solid var(--vscode-input-border);
      border-radius: 2px;
    }

    input:focus,
    select:focus {
      outline: 1px solid var(--vscode-focusBorder);
      outline-offset: -1px;
    }

    .checkbox-field label {
      display: flex;
      align-items: flex-start;
      gap: 0.5rem;
      cursor: pointer;
    }

    input[type="checkbox"] {
      margin-top: 0.25rem;
      cursor: pointer;
    }

    .help-text {
      font-size: 0.85rem;
      color: var(--vscode-descriptionForeground);
      margin-top: 0.25rem;
    }

    .error-text {
      font-size: 0.85rem;
      color: var(--vscode-errorForeground);
      margin-top: 0.25rem;
      display: none;
    }

    .error-text.visible {
      display: block;
    }

    .navigation {
      display: flex;
      justify-content: space-between;
      gap: 1rem;
      margin-top: 2rem;
    }

    button {
      padding: 0.75rem 1.5rem;
      font-size: 1rem;
      font-family: var(--vscode-font-family);
      border: none;
      border-radius: 4px;
      cursor: pointer;
      transition: opacity 0.2s;
    }

    button:hover:not(:disabled) {
      opacity: 0.9;
    }

    button:focus {
      outline: 2px solid var(--vscode-focusBorder);
      outline-offset: 2px;
    }

    button:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .primary-button {
      background-color: var(--vscode-button-background);
      color: var(--vscode-button-foreground);
    }

    .secondary-button {
      background-color: var(--vscode-button-secondaryBackground);
      color: var(--vscode-button-secondaryForeground);
    }

    .test-button {
      margin-top: 1rem;
      background-color: var(--vscode-button-secondaryBackground);
      color: var(--vscode-button-secondaryForeground);
    }

    @media (prefers-reduced-motion: reduce) {
      * {
        animation: none !important;
        transition: none !important;
      }
    }

    @media (max-width: 600px) {
      body {
        padding: 1rem;
      }

      .navigation {
        flex-direction: column;
      }

      button {
        width: 100%;
      }
    }
  </style>
</head>
<body>
  <div class="container" role="main">
    <div class="progress-bar" role="progressbar" aria-valuenow="${stepNumber}" aria-valuemin="1" aria-valuemax="${totalSteps}">
      <div class="progress-fill"></div>
    </div>

    <div class="step-indicator" aria-live="polite">
      Step ${stepNumber} of ${totalSteps}
    </div>

    <div class="header">
      <h1>${currentStep.title}</h1>
      <p class="description">${currentStep.description}</p>
    </div>

    <form class="form" id="setupForm" onsubmit="return false;">
      ${fieldsHtml}
      
      ${
        currentStep.id === "backend"
          ? `
        <button type="button" class="test-button" onclick="testConnection()">
          Test Connection
        </button>
      `
          : ""
      }
    </form>

    <div class="navigation">
      <button 
        class="secondary-button" 
        onclick="handlePrevious()"
        ${isFirstStep ? "disabled" : ""}
      >
        ← Previous
      </button>
      <button 
        class="primary-button" 
        onclick="handleNext()"
      >
        ${isLastStep ? "Complete Setup" : "Next →"}
      </button>
    </div>
  </div>

  <script>
    const vscode = acquireVsCodeApi();

    function getFormData() {
      const form = document.getElementById('setupForm');
      const formData = new FormData(form);
      const data = {};
      
      for (const [key, value] of formData.entries()) {
        const input = form.elements[key];
        if (input.type === 'checkbox') {
          data[key] = input.checked;
        } else if (input.type === 'number') {
          data[key] = parseInt(value, 10);
        } else {
          data[key] = value;
        }
      }
      
      return data;
    }

    function handleNext() {
      const data = getFormData();
      const isLastStep = ${isLastStep};
      
      vscode.postMessage({
        command: isLastStep ? 'complete' : 'next',
        data
      });
    }

    function handlePrevious() {
      vscode.postMessage({ command: 'previous' });
    }

    function testConnection() {
      const data = getFormData();
      vscode.postMessage({
        command: 'testConnection',
        data
      });
    }

    // Handle validation errors from extension
    window.addEventListener('message', event => {
      const message = event.data;
      
      if (message.command === 'validationErrors') {
        // Clear previous errors
        document.querySelectorAll('.error-text').forEach(el => {
          el.classList.remove('visible');
          el.textContent = '';
        });
        
        // Show new errors
        message.errors.forEach(error => {
          const errorEl = document.getElementById(error.fieldId + '-error');
          if (errorEl) {
            errorEl.textContent = error.message;
            errorEl.classList.add('visible');
          }
        });
      }
    });

    // Announce to screen readers
    const announcement = document.createElement('div');
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', 'polite');
    announcement.style.position = 'absolute';
    announcement.style.left = '-10000px';
    announcement.textContent = 'Setup wizard step ${stepNumber} of ${totalSteps}: ${currentStep.title}';
    document.body.appendChild(announcement);
  </script>
</body>
</html>`;
  }
}
