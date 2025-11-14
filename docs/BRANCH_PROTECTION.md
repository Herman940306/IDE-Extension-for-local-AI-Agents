# Branch Protection Rules

This document describes the branch protection rules configured for the `main` branch of this repository.

## Overview

Branch protection rules help ensure code quality and maintain repository integrity by:
- Requiring code reviews before merging
- Ensuring all tests pass before code is merged
- Preventing accidental force pushes or branch deletion
- Requiring conversations to be resolved before merging

## Configuration File

The branch protection rules are defined in `.github/settings.yml`. This configuration can be applied:

1. **Automatically** - Using the [Probot Settings](https://github.com/probot/settings) GitHub App
2. **Manually** - Via GitHub's web interface (Settings → Branches → Branch protection rules)
3. **Via API** - Using GitHub's REST API for branch protection

## Main Branch Protection Rules

The `main` branch has the following protections:

### Required Pull Request Reviews
- ✅ **At least 1 approval required** before merging
- ✅ **Dismiss stale reviews** when new commits are pushed
- ✅ **Require conversation resolution** before merging

### Required Status Checks
All of the following CI checks must pass before merging:
- ✅ **Backend Lint & Config Checks** - Code formatting and linting
- ✅ **Backend Tests (with coverage gate)** - Unit tests with 60% coverage requirement
- ✅ **Extension Build & Package** - VS Code extension compilation and packaging
- ✅ **Backend Docker Build** - Docker image build validation
- ✅ **mypy (backend)** - Python type checking
- ✅ **Gitleaks Secret Scan** - Security scanning for exposed secrets

### Additional Protections
- ❌ **No force pushes** - Prevents rewriting history on main
- ❌ **No branch deletion** - Prevents accidental deletion of main branch
- ✅ **Branches must be up to date** - Requires branches to be current with main before merging

## Applying the Configuration

### Option 1: Using Probot Settings App (Recommended)

1. Install the [Probot Settings](https://github.com/apps/settings) app to your repository
2. The app will automatically sync the `.github/settings.yml` configuration
3. Any changes to the settings file will be automatically applied

### Option 2: Manual Configuration via GitHub UI

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Branches**
3. Click **Add branch protection rule**
4. Set "Branch name pattern" to `main`
5. Configure the following options:
   - ✅ Require a pull request before merging
     - Required approvals: 1
     - Dismiss stale pull request approvals when new commits are pushed
   - ✅ Require status checks to pass before merging
     - Require branches to be up to date before merging
     - Add status checks:
       - `Backend Lint & Config Checks`
       - `Backend Tests (with coverage gate)`
       - `Extension Build & Package`
       - `Backend Docker Build`
       - `mypy (backend)`
       - `Gitleaks Secret Scan`
   - ✅ Require conversation resolution before merging
   - ❌ Do not allow bypassing the above settings (uncheck "Do not allow bypassing...")
   - ❌ Do not allow force pushes
   - ❌ Do not allow deletions
6. Click **Create** or **Save changes**

### Option 3: Using GitHub CLI

```bash
# Install GitHub CLI if not already installed
# See: https://cli.github.com/

# Apply branch protection rules
gh api repos/{owner}/{repo}/branches/main/protection \
  --method PUT \
  --input .github/branch-protection.json
```

### Option 4: Using GitHub REST API

Use the [Update Branch Protection](https://docs.github.com/en/rest/branches/branch-protection) API endpoint:

```bash
curl -X PUT \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  https://api.github.com/repos/Herman940306/IDE-Extension-for-local-AI-Agents/branches/main/protection \
  -d @.github/branch-protection.json
```

## Workflow Integration

The branch protection rules are designed to work with the existing GitHub Actions workflows:

- **ci.yml** - Main CI pipeline with backend lint, tests, extension build, and Docker build
- **typecheck.yml** - Python type checking with mypy
- **secret-scan.yml** - Security scanning with Gitleaks
- **confidentiality-guard.yml** - Additional security checks
- **release.yml** - Release automation (triggered after merge)

## Benefits

These branch protection rules provide:

1. **Code Quality** - Ensures all code is reviewed and tested before merging
2. **Security** - Prevents merging code with exposed secrets or security issues
3. **Stability** - Maintains a stable main branch by requiring all checks to pass
4. **Collaboration** - Encourages discussion and resolution of issues through required reviews
5. **History Integrity** - Prevents force pushes that could rewrite history

## Exceptions and Overrides

- Repository administrators can bypass these rules if "Enforce for administrators" is disabled
- For emergency fixes, administrators should still follow the standard process when possible
- Feature branches (feat/*) do not have the same restrictions, allowing more flexible development

## Troubleshooting

### Status checks not appearing
- Ensure the workflow has run at least once on the main branch
- Check that the job names in `.github/settings.yml` match exactly with the workflow job names

### Unable to merge despite passing checks
- Ensure all required conversations are resolved
- Verify the branch is up to date with main
- Check that all required reviewers have approved

### Need to make emergency changes
- Contact a repository administrator
- Consider if the change can wait for proper review
- If absolutely necessary, administrators can temporarily disable protection

## Maintenance

This configuration should be reviewed and updated when:
- New CI workflows are added
- Existing workflow job names change
- Security or quality requirements evolve
- Team size or structure changes

## References

- [GitHub Branch Protection Documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [Probot Settings App](https://github.com/probot/settings)
- [GitHub REST API - Branch Protection](https://docs.github.com/en/rest/branches/branch-protection)
