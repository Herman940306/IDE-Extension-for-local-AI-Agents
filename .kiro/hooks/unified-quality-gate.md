# 🎯 Unified Quality Gate Hook v4.0

**Version:** 4.0
**Created:** 2025-10-13
**Creator:** Herman Swanepoel
**Integration:** UNIFIED_MASTER_FRAMEWORK_v3.md

---

## 🎛️ Hook Configuration

**Trigger Events:**

- On file save (auto)
- Pre-commit (auto)
- Manual execution (button)

**Execution Mode:** Blocking for CRITICAL checks, async for optional

**Framework Integration:** Reads module state from `UNIFIED_MASTER_FRAMEWORK_v3.md`

---

## 🔥 CORE CHECKS (Always Run - Blocking)

### 1. Error Detection (CRITICAL)

**Purpose:** Catch syntax, type, import, and linting errors before they break the build

**Checks:**

- Python: syntax errors, type hints, import resolution, PEP-8 compliance
- TypeScript: compilation errors, type checking, import resolution
- JavaScript: syntax errors, ESLint rules

**Action on Failure:** BLOCK commit/save, display errors, require fix

**Command Simulation:**

```bash
# Python
python -m py_compile {file}
mypy {file} --strict
flake8 {file}

# TypeScript
tsc --noEmit {file}

# JavaScript
eslint {file}
```

---

### 2. Sprint Alignment (CRITICAL)

**Purpose:** Ensure changes align with current sprint tasks

**Checks:**

- Read current sprint from `UNIFIED_MASTER_FRAMEWORK_v3.md`
- Validate file changes against active tasks in `tasks.md`
- Check if modified files are part of current sprint scope

**Action on Failure:** WARN user, require confirmation to proceed

**Validation Logic:**

```
IF file in current_sprint_scope:
  ✅ PASS
ELSE:
  ⚠️ WARN: "File not in current sprint scope. Proceed? (y/n)"
```

---

## 🧩 OPTIONAL CHECKS (Module-Aware)

### 3. Auto Test (HIGH Priority)

**Enabled When:** Godmode OR DevOps modules active

**Checks:**

- Run unit tests for modified files
- Check test coverage (target: >80%)
- Validate test pass rate (target: 100%)

**Commands:**

```bash
# Python
pytest tests/test_{filename}.py -v --cov

# TypeScript/JavaScript
npm test -- {filename}.test.ts
```

**Action on Failure:** WARN, display failed tests, suggest fixes

---

### 4. Accessibility Check (HIGH Priority)

**Enabled When:** CurrentSprintFocus module active

**Checks:**

- WCAG 2.1 AA compliance
- Semantic HTML structure
- ARIA labels and roles
- Keyboard navigation support
- Color contrast ratios

**Tools:**

- axe-core for React components
- pa11y for static analysis

**Action on Failure:** WARN, list accessibility issues with severity

---

### 5. Code Quality Review (MEDIUM Priority)

**Enabled When:** Godmode OR AuraIA Strategic modules active

**Checks:**

- Code complexity (cyclomatic complexity < 10)
- Code duplication detection
- Function length (< 50 lines recommended)
- Proper error handling
- Documentation completeness

**Tools:**

- radon (Python complexity)
- jscpd (duplication detection)

**Action on Failure:** INFO, suggest refactoring opportunities

---

### 6. Security Scan (MEDIUM Priority)

**Enabled When:** DevOps module active

**Checks:**

- Dependency vulnerabilities (npm audit, safety)
- Hardcoded secrets detection
- SQL injection patterns
- XSS vulnerabilities
- Insecure API calls

**Tools:**

- bandit (Python security)
- npm audit (Node.js)
- trufflehog (secrets detection)

**Action on Failure:** BLOCK on critical, WARN on medium/low

---

### 7. Performance Check (LOW Priority)

**Enabled When:** DevOps OR Godmode modules active

**Checks:**

- Bundle size analysis
- Render performance (React components)
- Database query optimization
- Memory leak detection
- API response time validation

**Action on Failure:** INFO, suggest optimizations

---

### 8. AI Linter (MEDIUM Priority)

**Enabled When:** Godmode module active

**Purpose:** AI-augmented code review using AURA-DEV OMNIDEV reasoning

**Checks:**

- Suggest React.memo for expensive components
- Identify missing error boundaries
- Recommend code modularization
- Detect anti-patterns
- Suggest performance optimizations
- Identify test coverage gaps

**Action on Failure:** INFO, provide AI suggestions

---

## 🤖 AI-AUGMENTED GODMODE ANALYSIS

When Godmode module is enabled, provide enhanced recommendations:

### Architecture Suggestions:

- Component composition improvements
- State management optimization
- API design enhancements
- Database schema refinements

### Performance Optimizations:

- Memoization opportunities
- Lazy loading candidates
- Bundle splitting recommendations
- Caching strategies

### Security Enhancements:

- Input validation gaps
- Authentication flow improvements
- Authorization boundary checks
- Data sanitization recommendations

### Maintainability:

- Refactoring opportunities
- Documentation gaps
- Test coverage improvements
- Code smell detection

---

## 📊 REPORTING FORMAT

### Execution Summary:

```
🎯 Hook Execution Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CRITICAL ✅ Error Detection: No errors found
CRITICAL ✅ Sprint Alignment: Task 18 aligned

HIGH     ✅ Auto Test: 12/12 passed (coverage: 87%)
HIGH     ⚠️  Accessibility Check: 2 issues found
         └─ Missing ARIA label on button (line 45)
         └─ Color contrast ratio 3.2:1 (needs 4.5:1)

MEDIUM   💡 AI Linter: 1 suggestion
         └─ Consider React.memo for ExpensiveComponent (line 120)

MEDIUM   ✅ Code Quality: Complexity score 7/10
MEDIUM   ⬜ Security Scan: Disabled (DevOps module inactive)

LOW      ⬜ Performance Check: Disabled

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Action Required:
   • Fix 2 accessibility issues before commit
   • Review AI suggestion for performance optimization

✅ Safe to commit after addressing ⚠️ items
```

### Severity Levels:

- **CRITICAL (🔴):** BLOCKS commit, must fix
- **HIGH (🟡):** WARNS, strongly recommended to fix
- **MEDIUM (🔵):** INFO, suggested improvements
- **LOW (⚪):** OPTIONAL, nice-to-have enhancements

---

## 🔧 CONFIGURATION

### Module Detection:

Reads checkbox state from `UNIFIED_MASTER_FRAMEWORK_v3.md`:

```markdown
- [x] **Godmode Developer** → Enable Auto Test, AI Linter, Code Quality
- [x] **DevOps Master Mode** → Enable Security Scan, Performance Check
- [x] **Current Sprint Focus** → Enable Accessibility Check
- [x] **AuraIA Strategic Guidelines** → Enable Code Quality Review
```

### Execution Flow:

1. Read module states from framework
2. Run CRITICAL checks (blocking)
3. Run enabled optional checks (async)
4. Aggregate results
5. Generate structured report
6. Block/warn/inform based on severity

### Performance Optimization:

- Parallel execution of independent checks
- Cache results for unchanged files
- Incremental analysis for large codebases
- Skip checks for excluded file patterns

---

## 🎯 USAGE EXAMPLES

### Manual Trigger:

```
User: "Run quality gate on current file"
Hook: Executes all enabled checks, displays report
```

### Auto-Trigger on Save:

```
User: Saves file
Hook: Runs in background, shows notification if issues found
```

### Pre-Commit Hook:

```
User: git commit -m "message"
Hook: Blocks commit if CRITICAL issues found
```

### Batch Mode:

```
User: "Run quality gate on all Task 5 files"
Hook: Analyzes all 7 services, generates comprehensive report
```

---

## 🚀 INTEGRATION WITH KIRO WORKFLOW

### Git Integration:

- Respects git-workflow rules (feature branch protection)
- Validates commit messages format
- Checks for uncommitted changes

### Sprint Integration:

- Reads current sprint from framework
- Validates task alignment
- Updates task status on successful checks

### MCP Integration:

- Logs all checks to MCP for learning
- Uses MCP predictions for proactive suggestions
- Feeds results back to improve orchestration

### AURA-DEV OMNIDEV Integration:

**GODMODE Architecture Enforcement:**

- **Zero Technical Debt:** Validates modular, maintainable, evolvable code structure
- **Security by Design:** Enforces least privilege, encryption, compliance-first patterns
- **Automation Over Manual Labor:** Ensures all workflows are automated end-to-end
- **Observability Is Law:** Validates measurable, monitorable, self-healing systems
- **AI-Augmented Engineering:** Integrates AI copilots and automation in delivery
- **Global Scalability First:** Checks for multi-region, low latency, high fault tolerance design

**Omnidev Intelligence Stack Validation:**

- Architecture patterns: DDD, Clean Architecture, Hexagonal, CQRS, Event-Driven
- Backend standards: Node.js, FastAPI, Spring, NestJS, Go, .NET Core, Rust, Java
- Frontend standards: React, Next.js, Svelte, Vue, Angular
- DevOps compliance: Kubernetes, Docker, Terraform, ArgoCD, GitHub Actions
- MLOps standards: MLflow, Kubeflow, Hugging Face, LangChain
- Data architecture: PostgreSQL, MongoDB, Redis, Kafka, Spark
- Security compliance: OWASP, Zero Trust, Vault, KMS, SOPS, IAM, TLS, JWT, SAST/DAST
- Cloud readiness: AWS, Azure, GCP, Cloudflare, hybrid/edge deployment

**Omnidev Response Framework Integration:**
When Godmode module is active, validates code against:

1. System Overview completeness
2. Architecture & Stack Selection appropriateness
3. DevOps & Infrastructure Plan readiness
4. Code & Implementation Strategy quality
5. Security & Compliance adherence
6. Performance & Reliability metrics
7. Scaling & Evolution Path clarity
8. Documentation & Collaboration standards
9. Action Plan feasibility

**Operating Laws Enforcement:**

- ✅ Validates correctness, performance, and compliance
- ✅ Flags ambiguity requiring clarification
- ✅ Presents trade-offs between approaches
- ✅ Blocks insecure defaults or hardcoded secrets
- ✅ Enforces enterprise-grade quality and scalability
- ✅ Simulates entire engineering department review

---

## 📝 MAINTENANCE

### Weekly:

- Review false positives
- Update rule thresholds
- Sync with framework changes

### Per Sprint:

- Adjust checks based on sprint focus
- Update accessibility requirements
- Refine AI linter patterns

### Monthly:

- Performance optimization
- Tool version updates
- Rule effectiveness analysis

---

## 🔒 COMPLIANCE & SECURITY

### Enterprise Standards:

- Follows AURA-DEV OMNIDEV principles
- Enforces zero technical debt policy
- Maintains security-by-design approach

### Audit Trail:

- Logs all check results
- Tracks override decisions
- Maintains compliance history

### Privacy:

- No sensitive data in logs
- Local execution only
- Encrypted result storage

---

**Project Creator:** Herman Swanepoel
**Document Version:** 4.0
**Last Updated:** 2025-10-13
**Framework Integration:** UNIFIED_MASTER_FRAMEWORK_v3.md
