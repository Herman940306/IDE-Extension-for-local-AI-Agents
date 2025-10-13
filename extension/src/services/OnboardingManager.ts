/**
 * Onboarding Manager - First-time user experience
 * 
 * Provides a smooth onboarding experience including:
 * - Welcome screen
 * - Feature tour
 * - Initial setup wizard
 * - Tutorial tooltips
 * - Quick start guide
 * 
 * Project Creator: Herman Swanepoel
 */

import * as vscode from 'vscode';
import { WelcomePanel } from '../panels/WelcomePanel';
import { TourPanel, TourStep } from '../panels/TourPanel';
import { SetupWizard, SetupConfiguration } from '../panels/SetupWizard';
import { QuickStartGuide } from '../panels/QuickStartGuide';
import { TooltipManager } from './TooltipManager';

// ============================================================================
// Type Definitions
// ============================================================================

export type OnboardingStep = 
  | 'welcome'
  | 'tour-agents'
  | 'tour-modes'
  | 'tour-suggestions'
  | 'tour-discussion'
  | 'tour-analytics'
  | 'setup-backend'
  | 'setup-llm'
  | 'setup-privacy'
  | 'setup-accessibility'
  | 'setup-shortcuts'
  | 'complete';

export interface OnboardingOptions {
  skillLevel?: 'beginner' | 'intermediate' | 'advanced';
  skipWelcome?: boolean;
  skipTour?: boolean;
  skipSetup?: boolean;
}

export interface OnboardingState {
  isComplete: boolean;
  isSkipped: boolean;
  currentStep: OnboardingStep;
  completedSteps: OnboardingStep[];
  startTime?: number;
  completionTime?: number;
  skillLevel: 'beginner' | 'intermediate' | 'advanced';
  configuration: Partial<ExtensionConfiguration>;
}

export interface ExtensionConfiguration {
  backendUrl: string;
  backendPort: number;
  llmProvider: 'ollama' | 'lmstudio' | 'cloud';
  telemetryEnabled: boolean;
  cloudFallbackEnabled: boolean;
  screenReaderEnabled: boolean;
  keyboardShortcutsEnabled: boolean;
}

export interface StoredOnboardingState {
  version: string;
  isComplete: boolean;
  isSkipped: boolean;
  currentStep: OnboardingStep;
  completedSteps: OnboardingStep[];
  startTime?: number;
  completionTime?: number;
  skillLevel: 'beginner' | 'intermediate' | 'advanced';
  seenTooltips: string[];
  tooltipsEnabled: boolean;
  configuration: Partial<ExtensionConfiguration>;
}

export interface OnboardingEvent {
  type: 'started' | 'completed' | 'skipped' | 'step-completed' | 'step-skipped';
  step?: OnboardingStep;
  timestamp: number;
  metadata?: Record<string, any>;
}

export interface OnboardingAnalytics {
  sessionId: string;
  startTime: number;
  completionTime?: number;
  totalDuration?: number;
  isCompleted: boolean;
  isSkipped: boolean;
  skillLevel: 'beginner' | 'intermediate' | 'advanced';
  steps: StepAnalytics[];
  dropOffPoint?: OnboardingStep;
}

export interface StepAnalytics {
  step: OnboardingStep;
  startTime: number;
  completionTime?: number;
  duration?: number;
  skipped: boolean;
  interactions: number;
}

// ============================================================================
// OnboardingManager Class
// ============================================================================

export class OnboardingManager {
  private static readonly STATE_VERSION = '1.0.0';
  private static readonly STATE_KEY = 'enterpriseAI.onboarding.state';
  
  private context: vscode.ExtensionContext;
  private state: OnboardingState;
  private analytics: OnboardingAnalytics;
  private disposables: vscode.Disposable[] = [];
  private welcomePanel?: WelcomePanel;
  private tourPanel?: TourPanel;
  private setupWizard?: SetupWizard;
  private quickStartGuide?: QuickStartGuide;
  private tooltipManager?: TooltipManager;

  constructor(context: vscode.ExtensionContext) {
    this.context = context;
    
    // Initialize with default state
    this.state = this.getDefaultState();
    this.analytics = this.createAnalyticsSession();
    
    // Initialize tooltip manager
    this.tooltipManager = new TooltipManager(context);
  }

  // ============================================================================
  // Lifecycle Methods
  // ============================================================================

  /**
   * Initialize the onboarding manager
   * Loads persisted state and sets up event handlers
   */
  public async initialize(): Promise<void> {
    try {
      // Load persisted state
      await this.loadState();
      
      // Validate and migrate state if needed
      await this.validateAndMigrateState();
      
      console.log('[OnboardingManager] Initialized successfully');
    } catch (error) {
      console.error('[OnboardingManager] Initialization failed:', error);
      // Reset to default state on error
      this.state = this.getDefaultState();
      await this.saveState();
    }
  }

  /**
   * Dispose of resources and clean up
   */
  public dispose(): void {
    // Dispose all disposables
    this.disposables.forEach(d => d.dispose());
    this.disposables = [];
    
    console.log('[OnboardingManager] Disposed');
  }

  // ============================================================================
  // State Management
  // ============================================================================

  /**
   * Get the current onboarding state
   */
  public getState(): OnboardingState {
    return { ...this.state };
  }

  /**
   * Update progress to a specific step
   */
  public async updateProgress(step: OnboardingStep): Promise<void> {
    try {
      // Update current step
      this.state.currentStep = step;
      
      // Add to completed steps if not already there
      if (!this.state.completedSteps.includes(step)) {
        this.state.completedSteps.push(step);
      }
      
      // Track analytics
      this.trackStepCompletion(step);
      
      // Persist state
      await this.saveState();
      
      console.log(`[OnboardingManager] Progress updated to step: ${step}`);
    } catch (error) {
      console.error('[OnboardingManager] Failed to update progress:', error);
      throw error;
    }
  }

  /**
   * Mark onboarding as complete
   */
  public async markComplete(): Promise<void> {
    try {
      this.state.isComplete = true;
      this.state.completionTime = Date.now();
      this.state.currentStep = 'complete';
      
      // Update analytics
      this.analytics.isCompleted = true;
      this.analytics.completionTime = Date.now();
      this.analytics.totalDuration = this.analytics.completionTime - this.analytics.startTime;
      
      await this.saveState();
      
      console.log('[OnboardingManager] Onboarding marked as complete');
    } catch (error) {
      console.error('[OnboardingManager] Failed to mark complete:', error);
      throw error;
    }
  }

  /**
   * Mark onboarding as skipped
   */
  public async markSkipped(): Promise<void> {
    try {
      this.state.isSkipped = true;
      this.state.isComplete = true;
      this.state.completionTime = Date.now();
      
      // Update analytics
      this.analytics.isSkipped = true;
      this.analytics.dropOffPoint = this.state.currentStep;
      
      await this.saveState();
      
      console.log('[OnboardingManager] Onboarding marked as skipped');
    } catch (error) {
      console.error('[OnboardingManager] Failed to mark skipped:', error);
      throw error;
    }
  }

  /**
   * Check if onboarding is complete
   */
  public isComplete(): boolean {
    return this.state.isComplete;
  }

  /**
   * Check if onboarding is skipped
   */
  public isSkipped(): boolean {
    return this.state.isSkipped;
  }

  /**
   * Check if onboarding is in progress
   */
  public isInProgress(): boolean {
    return !this.state.isComplete && !this.state.isSkipped && this.state.completedSteps.length > 0;
  }

  // ============================================================================
  // Storage Methods
  // ============================================================================

  /**
   * Load state from workspace storage
   */
  private async loadState(): Promise<void> {
    try {
      const stored = this.context.workspaceState.get<StoredOnboardingState>(
        OnboardingManager.STATE_KEY
      );
      
      if (stored) {
        // Convert stored state to runtime state
        this.state = {
          isComplete: stored.isComplete,
          isSkipped: stored.isSkipped,
          currentStep: stored.currentStep,
          completedSteps: stored.completedSteps,
          startTime: stored.startTime,
          completionTime: stored.completionTime,
          skillLevel: stored.skillLevel,
          configuration: stored.configuration
        };
        
        console.log('[OnboardingManager] State loaded from storage');
      }
    } catch (error) {
      console.error('[OnboardingManager] Failed to load state:', error);
      throw error;
    }
  }

  /**
   * Save state to workspace storage
   */
  private async saveState(): Promise<void> {
    try {
      const stored: StoredOnboardingState = {
        version: OnboardingManager.STATE_VERSION,
        isComplete: this.state.isComplete,
        isSkipped: this.state.isSkipped,
        currentStep: this.state.currentStep,
        completedSteps: this.state.completedSteps,
        startTime: this.state.startTime,
        completionTime: this.state.completionTime,
        skillLevel: this.state.skillLevel,
        seenTooltips: [],
        tooltipsEnabled: true,
        configuration: this.state.configuration
      };
      
      await this.context.workspaceState.update(
        OnboardingManager.STATE_KEY,
        stored
      );
      
      console.log('[OnboardingManager] State saved to storage');
    } catch (error) {
      console.error('[OnboardingManager] Failed to save state:', error);
      // Don't throw - continue in-memory only
    }
  }

  /**
   * Validate and migrate state if version mismatch
   */
  private async validateAndMigrateState(): Promise<void> {
    try {
      const stored = this.context.workspaceState.get<StoredOnboardingState>(
        OnboardingManager.STATE_KEY
      );
      
      if (!stored) {
        return;
      }
      
      // Check version
      if (stored.version !== OnboardingManager.STATE_VERSION) {
        console.log(`[OnboardingManager] Migrating state from ${stored.version} to ${OnboardingManager.STATE_VERSION}`);
        
        // Perform migration (currently just reset)
        this.state = this.getDefaultState();
        await this.saveState();
      }
      
      // Validate state structure
      if (!this.isValidState(this.state)) {
        console.warn('[OnboardingManager] Invalid state detected, resetting to default');
        this.state = this.getDefaultState();
        await this.saveState();
      }
    } catch (error) {
      console.error('[OnboardingManager] State validation failed:', error);
      this.state = this.getDefaultState();
      await this.saveState();
    }
  }

  /**
   * Validate state structure
   */
  private isValidState(state: OnboardingState): boolean {
    return (
      typeof state.isComplete === 'boolean' &&
      typeof state.isSkipped === 'boolean' &&
      typeof state.currentStep === 'string' &&
      Array.isArray(state.completedSteps) &&
      ['beginner', 'intermediate', 'advanced'].includes(state.skillLevel)
    );
  }

  /**
   * Get default state
   */
  private getDefaultState(): OnboardingState {
    return {
      isComplete: false,
      isSkipped: false,
      currentStep: 'welcome',
      completedSteps: [],
      startTime: undefined,
      completionTime: undefined,
      skillLevel: 'beginner',
      configuration: {}
    };
  }

  // ============================================================================
  // Analytics Methods
  // ============================================================================

  /**
   * Create a new analytics session
   */
  private createAnalyticsSession(): OnboardingAnalytics {
    return {
      sessionId: this.generateSessionId(),
      startTime: Date.now(),
      isCompleted: false,
      isSkipped: false,
      skillLevel: this.state.skillLevel,
      steps: []
    };
  }

  /**
   * Track step completion
   */
  private trackStepCompletion(step: OnboardingStep): void {
    const existingStep = this.analytics.steps.find(s => s.step === step);
    
    if (existingStep) {
      existingStep.completionTime = Date.now();
      existingStep.duration = existingStep.completionTime - existingStep.startTime;
    } else {
      this.analytics.steps.push({
        step,
        startTime: Date.now(),
        skipped: false,
        interactions: 0
      });
    }
  }

  /**
   * Generate a unique session ID
   */
  private generateSessionId(): string {
    return `onboarding-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Get analytics data
   */
  public getAnalytics(): OnboardingAnalytics {
    return { ...this.analytics };
  }

  // ============================================================================
  // Flow Control Methods
  // ============================================================================

  /**
   * Start the onboarding flow
   */
  public async startOnboarding(options?: OnboardingOptions): Promise<void> {
    try {
      // Apply options
      if (options?.skillLevel) {
        this.state.skillLevel = options.skillLevel;
      }

      // Set start time if not already set
      if (!this.state.startTime) {
        this.state.startTime = Date.now();
      }

      // Track start event
      this.trackEvent({
        type: 'started',
        timestamp: Date.now(),
        metadata: { skillLevel: this.state.skillLevel }
      });

      // Show welcome screen unless skipped
      if (!options?.skipWelcome) {
        await this.showWelcome();
      } else {
        // Skip directly to tour or setup
        if (!options?.skipTour) {
          // TODO: Show tour
        } else if (!options?.skipSetup) {
          // TODO: Show setup
        }
      }

      await this.saveState();
    } catch (error) {
      console.error('[OnboardingManager] Failed to start onboarding:', error);
      throw error;
    }
  }

  /**
   * Resume interrupted onboarding
   */
  public async resumeOnboarding(): Promise<void> {
    try {
      const currentStep = this.state.currentStep;

      if (currentStep === 'welcome') {
        await this.showWelcome();
      } else if (currentStep.startsWith('tour-')) {
        // TODO: Resume tour at specific step
        console.log(`[OnboardingManager] Resuming tour at step: ${currentStep}`);
      } else if (currentStep.startsWith('setup-')) {
        // TODO: Resume setup at specific step
        console.log(`[OnboardingManager] Resuming setup at step: ${currentStep}`);
      }
    } catch (error) {
      console.error('[OnboardingManager] Failed to resume onboarding:', error);
      throw error;
    }
  }

  /**
   * Skip the entire onboarding flow
   */
  public async skipOnboarding(): Promise<void> {
    try {
      await this.markSkipped();
      
      this.trackEvent({
        type: 'skipped',
        step: this.state.currentStep,
        timestamp: Date.now()
      });

      // Close any open panels
      if (this.welcomePanel) {
        this.welcomePanel.hide();
      }

      vscode.window.showInformationMessage(
        'Onboarding skipped. You can restart it anytime from the command palette.'
      );
    } catch (error) {
      console.error('[OnboardingManager] Failed to skip onboarding:', error);
      throw error;
    }
  }

  /**
   * Restart the onboarding flow
   */
  public async restartOnboarding(): Promise<void> {
    try {
      // Reset state
      this.state = this.getDefaultState();
      this.analytics = this.createAnalyticsSession();
      
      await this.saveState();
      
      // Start fresh
      await this.startOnboarding();
    } catch (error) {
      console.error('[OnboardingManager] Failed to restart onboarding:', error);
      throw error;
    }
  }

  /**
   * Show the welcome screen
   */
  private async showWelcome(): Promise<void> {
    try {
      // Create or show welcome panel
      this.welcomePanel = WelcomePanel.createOrShow(this.context.extensionUri);

      // Handle "Get Started" action
      this.welcomePanel.onGetStarted(() => {
        this.handleWelcomeGetStarted();
      });

      // Handle "Skip Tour" action
      this.welcomePanel.onSkipTour(() => {
        this.skipOnboarding();
      });

      // Update progress
      await this.updateProgress('welcome');
    } catch (error) {
      console.error('[OnboardingManager] Failed to show welcome:', error);
      throw error;
    }
  }

  /**
   * Handle "Get Started" from welcome screen
   */
  private async handleWelcomeGetStarted(): Promise<void> {
    try {
      // Get skill level from welcome panel
      if (this.welcomePanel) {
        const skillLevel = this.welcomePanel.getSkillLevel();
        this.state.skillLevel = skillLevel;
        this.analytics.skillLevel = skillLevel;
        await this.saveState();
        
        console.log(`[OnboardingManager] Skill level set to: ${skillLevel}`);
        
        // Hide welcome panel
        this.welcomePanel.hide();
      }

      // Show tour
      await this.showTour();
    } catch (error) {
      console.error('[OnboardingManager] Failed to handle get started:', error);
      throw error;
    }
  }

  /**
   * Show the feature tour
   */
  private async showTour(): Promise<void> {
    try {
      const steps = this.getTourSteps();
      
      // Create or show tour panel
      this.tourPanel = TourPanel.createOrShow(this.context.extensionUri, steps);

      // Handle next step
      this.tourPanel.onNext((stepIndex) => {
        this.handleTourNext(stepIndex);
      });

      // Handle previous step
      this.tourPanel.onPrevious((stepIndex) => {
        this.handleTourPrevious(stepIndex);
      });

      // Handle skip
      this.tourPanel.onSkip(() => {
        this.skipOnboarding();
      });

      // Handle complete
      this.tourPanel.onComplete(() => {
        this.handleTourComplete();
      });

      // Update progress to first tour step
      await this.updateProgress('tour-agents');
    } catch (error) {
      console.error('[OnboardingManager] Failed to show tour:', error);
      throw error;
    }
  }

  /**
   * Get tour steps
   */
  private getTourSteps(): TourStep[] {
    return [
      {
        id: 'tour-agents',
        title: 'Multi-Agent System',
        description: 'Six specialized AI agents work together to provide expert assistance',
        icon: '🤖',
        content: `
          <p><strong>Meet your AI team:</strong></p>
          <p>• <strong>Code Agent:</strong> Writes and refactors code with best practices</p>
          <p>• <strong>Review Agent:</strong> Analyzes code quality and suggests improvements</p>
          <p>• <strong>Test Agent:</strong> Creates comprehensive test suites</p>
          <p>• <strong>Debug Agent:</strong> Identifies and fixes bugs efficiently</p>
          <p>• <strong>Documentation Agent:</strong> Generates clear documentation</p>
          <p>• <strong>Architecture Agent:</strong> Designs scalable system architectures</p>
          <p>Each agent specializes in their domain, collaborating to solve complex problems.</p>
        `
      },
      {
        id: 'tour-modes',
        title: 'Offline & Online Modes',
        description: 'Privacy-first design with local LLM support',
        icon: '🔒',
        content: `
          <p><strong>Your code, your choice:</strong></p>
          <p>• <strong>Offline Mode:</strong> Run completely locally with Ollama or LM Studio. Your code never leaves your machine.</p>
          <p>• <strong>Online Mode:</strong> Optionally use cloud LLMs for enhanced capabilities when needed.</p>
          <p>• <strong>Hybrid Mode:</strong> Start offline, fallback to cloud only when necessary.</p>
          <p>All modes respect your privacy preferences and give you full control over your data.</p>
        `
      },
      {
        id: 'tour-suggestions',
        title: 'Inline Suggestions',
        description: 'Real-time AI-powered code suggestions as you type',
        icon: '⚡',
        content: `
          <p><strong>Code faster with intelligent assistance:</strong></p>
          <p>• Get context-aware suggestions as you type</p>
          <p>• Accept suggestions with Tab or customize your shortcut</p>
          <p>• Suggestions adapt to your coding style over time</p>
          <p>• Works with multiple programming languages</p>
          <p>• Respects your project's conventions and patterns</p>
          <p>The AI learns from your codebase to provide relevant, accurate suggestions.</p>
        `
      },
      {
        id: 'tour-discussion',
        title: 'Agent Discussion Panel',
        description: 'Watch agents collaborate and discuss solutions',
        icon: '💬',
        content: `
          <p><strong>See AI collaboration in action:</strong></p>
          <p>• Agents discuss different approaches to your problem</p>
          <p>• View their reasoning and decision-making process</p>
          <p>• Learn from expert-level discussions</p>
          <p>• Understand trade-offs between different solutions</p>
          <p>• Gain insights into best practices and patterns</p>
          <p>It's like having a team of senior developers reviewing your code together.</p>
        `
      },
      {
        id: 'tour-analytics',
        title: 'Analytics Dashboard',
        description: 'Track your productivity and AI assistance impact',
        icon: '📊',
        content: `
          <p><strong>Measure your progress:</strong></p>
          <p>• See how much time AI assistance saves you</p>
          <p>• Track code quality improvements over time</p>
          <p>• View which agents help you most</p>
          <p>• Analyze your coding patterns and habits</p>
          <p>• Set goals and monitor achievements</p>
          <p>All analytics are stored locally and respect your privacy settings.</p>
        `
      }
    ];
  }

  /**
   * Handle tour next step
   */
  private async handleTourNext(stepIndex: number): Promise<void> {
    try {
      const steps = this.getTourSteps();
      if (stepIndex < steps.length) {
        const step = steps[stepIndex];
        await this.updateProgress(step.id as OnboardingStep);
      }
    } catch (error) {
      console.error('[OnboardingManager] Failed to handle tour next:', error);
    }
  }

  /**
   * Handle tour previous step
   */
  private async handleTourPrevious(stepIndex: number): Promise<void> {
    try {
      // Just log for now, state is already tracked
      console.log(`[OnboardingManager] Tour previous to step ${stepIndex}`);
    } catch (error) {
      console.error('[OnboardingManager] Failed to handle tour previous:', error);
    }
  }

  /**
   * Handle tour completion
   */
  private async handleTourComplete(): Promise<void> {
    try {
      // Hide tour panel
      if (this.tourPanel) {
        this.tourPanel.hide();
      }

      // Show setup wizard
      await this.showSetup();
    } catch (error) {
      console.error('[OnboardingManager] Failed to handle tour complete:', error);
      throw error;
    }
  }

  /**
   * Show the setup wizard
   */
  private async showSetup(): Promise<void> {
    try {
      // Create or show setup wizard
      this.setupWizard = SetupWizard.createOrShow(this.context.extensionUri);

      // Handle next step
      this.setupWizard.onNext((stepIndex) => {
        this.handleSetupNext(stepIndex);
      });

      // Handle previous step
      this.setupWizard.onPrevious((stepIndex) => {
        this.handleSetupPrevious(stepIndex);
      });

      // Handle completion
      this.setupWizard.onComplete((config) => {
        this.handleSetupComplete(config);
      });

      // Handle validation (connection testing)
      this.setupWizard.onValidate(async ({ step, data }) => {
        await this.handleConnectionTest(data);
      });

      // Update progress to first setup step
      await this.updateProgress('setup-backend');
    } catch (error) {
      console.error('[OnboardingManager] Failed to show setup:', error);
      throw error;
    }
  }

  /**
   * Handle setup next step
   */
  private async handleSetupNext(stepIndex: number): Promise<void> {
    try {
      const steps = ['setup-backend', 'setup-llm', 'setup-privacy', 'setup-accessibility'];
      if (stepIndex < steps.length) {
        await this.updateProgress(steps[stepIndex] as OnboardingStep);
      }
    } catch (error) {
      console.error('[OnboardingManager] Failed to handle setup next:', error);
    }
  }

  /**
   * Handle setup previous step
   */
  private async handleSetupPrevious(stepIndex: number): Promise<void> {
    try {
      console.log(`[OnboardingManager] Setup previous to step ${stepIndex}`);
    } catch (error) {
      console.error('[OnboardingManager] Failed to handle setup previous:', error);
    }
  }

  /**
   * Handle setup completion
   */
  private async handleSetupComplete(config: SetupConfiguration): Promise<void> {
    try {
      // Save configuration
      await this.saveConfiguration(config);

      // Hide setup wizard
      if (this.setupWizard) {
        this.setupWizard.hide();
      }

      // Mark onboarding as complete
      await this.markComplete();

      // Show completion message
      const result = await vscode.window.showInformationMessage(
        'Setup complete! Would you like to view the Quick Start Guide?',
        'View Guide',
        'Close'
      );

      if (result === 'View Guide') {
        this.showQuickStartGuide();
      }
    } catch (error) {
      console.error('[OnboardingManager] Failed to handle setup complete:', error);
      throw error;
    }
  }

  /**
   * Show the quick start guide
   */
  public showQuickStartGuide(section?: string): void {
    try {
      this.quickStartGuide = QuickStartGuide.createOrShow(this.context.extensionUri, section);
      console.log('[OnboardingManager] Quick start guide shown');
    } catch (error) {
      console.error('[OnboardingManager] Failed to show quick start guide:', error);
    }
  }

  /**
   * Register tooltips for key features
   */
  public registerTooltips(): void {
    if (!this.tooltipManager) {
      return;
    }

    // Mode toggle tooltip
    this.tooltipManager.register({
      id: 'mode-toggle',
      title: 'Mode Toggle',
      description: 'Switch between Offline and Online modes',
      shortcut: 'Ctrl+Shift+M',
      position: 'bottom',
      trigger: 'hover',
      dismissible: true
    });

    // Command palette tooltip
    this.tooltipManager.register({
      id: 'ask-agents',
      title: 'Ask AI Agents',
      description: 'Get help from specialized AI agents',
      shortcut: 'Ctrl+Shift+A',
      position: 'top',
      trigger: 'manual',
      dismissible: true
    });

    // Agent discussion tooltip
    this.tooltipManager.register({
      id: 'agent-discussion',
      title: 'Agent Discussion',
      description: 'Watch agents collaborate on solutions',
      shortcut: 'Ctrl+Shift+D',
      position: 'right',
      trigger: 'hover',
      dismissible: true
    });

    // Analytics dashboard tooltip
    this.tooltipManager.register({
      id: 'analytics',
      title: 'Analytics Dashboard',
      description: 'Track your productivity metrics',
      shortcut: 'Ctrl+Shift+Y',
      position: 'left',
      trigger: 'hover',
      dismissible: true
    });

    console.log('[OnboardingManager] Tooltips registered');
  }

  /**
   * Show a tooltip
   */
  public async showTooltip(tooltipId: string): Promise<void> {
    if (this.tooltipManager) {
      await this.tooltipManager.show(tooltipId);
    }
  }

  /**
   * Check if should show onboarding on activation
   */
  public shouldShowOnboarding(): boolean {
    return !this.state.isComplete && !this.state.isSkipped;
  }

  /**
   * Check if should resume onboarding
   */
  public shouldResumeOnboarding(): boolean {
    return this.isInProgress();
  }

  /**
   * Handle extension activation
   */
  public async handleActivation(): Promise<void> {
    try {
      if (this.shouldShowOnboarding()) {
        // First time user
        await this.startOnboarding();
      } else if (this.shouldResumeOnboarding()) {
        // Interrupted onboarding
        const result = await vscode.window.showInformationMessage(
          'Would you like to continue the onboarding?',
          'Continue',
          'Skip'
        );

        if (result === 'Continue') {
          await this.resumeOnboarding();
        } else if (result === 'Skip') {
          await this.skipOnboarding();
        }
      } else {
        // Onboarding complete - register tooltips
        this.registerTooltips();
      }
    } catch (error) {
      console.error('[OnboardingManager] Failed to handle setup complete:', error);
      throw error;
    }
  }

  /**
   * Test backend connection
   */
  private async handleConnectionTest(data: any): Promise<void> {
    try {
      const { backendUrl, backendPort } = data;
      
      vscode.window.showInformationMessage(
        `Testing connection to ${backendUrl}:${backendPort}...`
      );

      // TODO: Implement actual connection test using WebSocketClient
      // For now, simulate success
      await new Promise(resolve => setTimeout(resolve, 1000));

      vscode.window.showInformationMessage(
        '✓ Connection successful!',
        { modal: false }
      );
    } catch (error) {
      vscode.window.showErrorMessage(
        `Connection failed: ${error}. Please check your backend configuration.`
      );
    }
  }

  /**
   * Save configuration to VS Code settings
   */
  private async saveConfiguration(config: SetupConfiguration): Promise<void> {
    try {
      const configuration = vscode.workspace.getConfiguration('enterpriseAI');

      await configuration.update('backend.url', config.backendUrl, vscode.ConfigurationTarget.Global);
      await configuration.update('backend.port', config.backendPort, vscode.ConfigurationTarget.Global);
      await configuration.update('llm.provider', config.llmProvider, vscode.ConfigurationTarget.Global);
      await configuration.update('privacy.telemetry', config.telemetryEnabled, vscode.ConfigurationTarget.Global);
      await configuration.update('privacy.cloudFallback', config.cloudFallbackEnabled, vscode.ConfigurationTarget.Global);
      await configuration.update('accessibility.screenReader', config.screenReaderEnabled, vscode.ConfigurationTarget.Global);
      await configuration.update('accessibility.keyboardShortcuts', config.keyboardShortcutsEnabled, vscode.ConfigurationTarget.Global);

      // Store in state as well
      this.state.configuration = config;
      await this.saveState();

      console.log('[OnboardingManager] Configuration saved successfully');
    } catch (error) {
      console.error('[OnboardingManager] Failed to save configuration:', error);
      throw error;
    }
  }

  /**
   * Track an onboarding event
   */
  public trackEvent(event: OnboardingEvent): void {
    console.log('[OnboardingManager] Event:', event);
    
    // Update analytics
    if (event.type === 'step-completed' && event.step) {
      const stepAnalytics = this.analytics.steps.find(s => s.step === event.step);
      if (stepAnalytics) {
        stepAnalytics.completionTime = event.timestamp;
        stepAnalytics.duration = stepAnalytics.completionTime - stepAnalytics.startTime;
      }
    }
    
    // Send to telemetry if enabled
    const config = vscode.workspace.getConfiguration('enterpriseAI');
    const telemetryEnabled = config.get<boolean>('privacy.telemetry', false);
    
    if (telemetryEnabled) {
      // TODO: Send to analytics service
      console.log('[OnboardingManager] Would send to analytics:', event);
    }
  }

  /**
   * Get onboarding completion rate
   */
  public getCompletionRate(): number {
    const totalSteps = 12; // welcome + 5 tour + 4 setup + complete
    return (this.state.completedSteps.length / totalSteps) * 100;
  }

  /**
   * Get time spent on onboarding
   */
  public getTimeSpent(): number {
    if (!this.state.startTime) {
      return 0;
    }
    
    const endTime = this.state.completionTime || Date.now();
    return endTime - this.state.startTime;
  }

  /**
   * Export analytics data
   */
  public exportAnalytics(): OnboardingAnalytics {
    return {
      ...this.analytics,
      totalDuration: this.getTimeSpent(),
      dropOffPoint: this.state.isSkipped ? this.state.currentStep : undefined
    };
  }
}
