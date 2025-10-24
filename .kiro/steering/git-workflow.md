---
inclusion: always
priority: critical
---

# Git Workflow Rules

## Branch Protection Rules

### CRITICAL: Never Push Directly to Main

**You MUST follow these rules for ALL Git operations:**

1. **Default Branch Behavior:**
   - ALWAYS work on feature branches by default
   - NEVER push directly to `main` branch unless explicitly requested
   - Create feature branches with descriptive names based on the task/feature

2. **Branch Naming Convention:**
   - Format: `feature/[task-name]` or `feature/SP-XXX-[description]`
   - Examples:
     - `feature/enterprise-ai-integration`
     - `feature/SP-001-autonomous-config`
     - `feature/mcp-server-setup`

3. **Automatic Branch Creation:**
   - When starting new work, automatically create and switch to a feature branch
   - Use the current task or feature name for the branch
   - Format: `git checkout -b feature/[descriptive-name]`

4. **Push Behavior:**
   - ALWAYS push to the current feature branch
   - Command: `git push origin [current-branch-name]`
   - NEVER use `git push origin main` unless user explicitly says "push to main"

5. **Main Branch Protection:**
   - Only push to `main` when user explicitly requests:
     - "push to main"
     - "merge to main"
     - "deploy to main"
   - Otherwise, ALWAYS assume feature branch workflow

6. **Commit and Push Workflow:**

   ```bash
   # Standard workflow (ALWAYS use this unless told otherwise)
   git checkout -b feature/[task-name]  # Create feature branch if needed
   git add -A
   git commit -m "SP-XXX: descriptive message"
   git push origin feature/[task-name]  # Push to feature branch
   ```

7. **Exception Handling:**
   - If user says "push to main" → Push to main branch
   - If user says "merge to main" → Merge current branch to main and push
   - Otherwise → ALWAYS use feature branch

## Enforcement

This rule is **MANDATORY** and **ALWAYS ACTIVE**.

Violation of this rule (pushing to main without explicit permission) is considered a critical error.

---

**Rule Created By:** Herman Swanepoel
**Date:** 2025-01-13
**Version:** 1.0
