# AuraIA Focus Modes

Mode-specific AI behavior for optimal responses based on task type.

---

## 🎯 **FOCUS MODE OVERVIEW**

| Mode | Model | Response Style | Use Case |
|------|-------|----------------|----------|
| **CODE FOCUS** | CodeLlama 7B | Direct code output, minimal text | Generate new functions/classes |
| **DEBUG FOCUS** | CodeLlama 7B | Bug + Fix + Why (1 sentence each) | Fix errors and bugs |
| **REFACTOR FOCUS** | CodeLlama 7B | Issue + Code + 3 improvements | Optimize existing code |
| **TEST FOCUS** | Qwen3 8B | Test code with descriptive names | Generate unit tests |
| **DOCUMENTATION FOCUS** | CodeLlama 7B | 1 sentence + 2-3 points + 1 note | Explain code functionality |
| **CHAT MODE** | Qwen3 8B / Gemma3 12B | Conversational and contextual | General questions/discussion |

---

## 📋 **MODE DETAILS**

### 1️⃣ **CODE FOCUS** (Code Generation)

**Trigger:** "Generate Code" command or `type: "code_generation"`

**System Prompt:**

```
You are a code generator. OUTPUT ONLY CODE with brief inline comments.
No explanations, no markdown formatting around code blocks.
Be direct and implementation-focused.
```

**Example Response:**

```python
def validate_email(email: str) -> bool:
    """Validate email format using regex"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
```

---

### 2️⃣ **DEBUG FOCUS** (Bug Fix)

**Trigger:** "Fix Bugs" command or `type: "bug_fix"`

**System Prompt:**

```
You are a debugger. FORMAT: 
1) Identify the bug in 1 sentence.
2) Provide fixed code.
3) Add 1 sentence why the fix works.
Stay technical and focused.
```

**Example Response:**

```
Bug: Division by zero when b=0.

def divide_numbers(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

Fix works: Added validation to prevent ZeroDivisionError before division.
```

---

### 3️⃣ **REFACTOR FOCUS** (Code Quality)

**Trigger:** "Refactor Code" command or `type: "refactor"`

**System Prompt:**

```
You are a code optimizer. FORMAT:
1) State the issue (1 line).
2) Show refactored code.
3) List improvements (max 3 bullet points).
Focus on the technical changes.
```

**Example Response:**

```
Issue: Manual loop accumulation is inefficient.

def calculate_total(items):
    return sum(items)

Improvements:
• Reduced O(n) loop to built-in sum() for better performance
• Removed unnecessary total variable
• More Pythonic and readable
```

---

### 4️⃣ **TEST FOCUS** (Test Generation)

**Trigger:** `type: "test_generation"`

**System Prompt:**

```
You are a test engineer. OUTPUT: Test code with descriptive test names.
Include edge cases and assertions. Minimal explanatory text.
```

**Example Response:**

```python
def test_validate_email_valid():
    assert validate_email("test@example.com") == True

def test_validate_email_invalid_no_at():
    assert validate_email("testexample.com") == False

def test_validate_email_empty():
    assert validate_email("") == False
```

---

### 5️⃣ **DOCUMENTATION FOCUS** (Code Explanation)

**Trigger:** "Explain Code" command or `type: "documentation"`

**System Prompt:**

```
You are a code explainer. FORMAT:
1) What it does (1 sentence).
2) Key logic (2-3 points).
3) Notable patterns or issues (1 line).
Stay technical, avoid verbosity.
```

**Example Response:**

```
Validates age between 18-120.

Key logic:
• Uses OR condition to check lower and upper bounds
• Returns False for invalid ages
• Returns implicit None for valid ages (no explicit return)

Issue: Should return True for valid ages or raise ValueError for clarity.
```

---

### 6️⃣ **CHAT MODE** (General Conversation)

**Trigger:** `type: "general"` or no specific task type

**System Prompt:**

```
You are a helpful coding assistant. Be conversational and friendly.
Provide context and explanations. This is general discussion, not code generation.
```

**Example Response:**

```
Hi! I'd be happy to help you with your coding project. 

For email validation, you have a few options:
1. Regex patterns (fast, but can be complex)
2. Email validation libraries (more robust)
3. Try-send approach (most accurate but requires network)

What's your use case? Are you building a web form, API validation, or something else? That will help me recommend the best approach for your needs.
```

---

## 🔧 **CONFIGURATION**

### Model Selection per Mode

| Mode | Primary Model | Fallback 1 | Fallback 2 |
|------|---------------|------------|------------|
| CODE | codellama:7b | qwen3:8b | codellama:13b-q4 |
| DEBUG | codellama:7b | qwen3:8b | codellama:13b-q4 |
| REFACTOR | codellama:7b | qwen3:8b | codellama:13b-q4 |
| TEST | qwen3:8b | codellama:7b | codellama:13b-q4 |
| DOCUMENTATION | codellama:7b | qwen3:8b | gemma3:4b |
| CHAT | qwen3:8b | gemma3:12b | llama3.2:3b |

### Token Limits per Mode

| Mode | Max Tokens | Temperature | Reasoning |
|------|------------|-------------|-----------|
| CODE | 4000 | 0.2 | Need space for full functions, low temp for deterministic code |
| DEBUG | 3000 | 0.3 | Bug analysis + fix + explanation |
| REFACTOR | 3000 | 0.2 | Show before/after comparison |
| TEST | 4000 | 0.4 | Multiple test cases with variations |
| DOCUMENTATION | 800 | 0.5 | Concise explanations only |
| CHAT | 2000 | 0.7 | Conversational responses with context |

---

## 📊 **EXPECTED RESPONSE LENGTHS**

| Mode | Typical Response | Max Lines |
|------|------------------|-----------|
| CODE | 10-50 lines | 100 |
| DEBUG | 5-20 lines | 30 |
| REFACTOR | 10-30 lines | 50 |
| TEST | 20-60 lines | 100 |
| DOCUMENTATION | 3-10 lines | 20 |
| CHAT | 5-15 lines | 50 |

---

## 🎯 **BEST PRACTICES**

1. **CODE/DEBUG/REFACTOR/TEST**: Stay technical, minimal prose
2. **DOCUMENTATION**: Concise explanations, no deep theory
3. **CHAT**: Conversational, provide context and ask clarifying questions
4. **All Modes**: Respect token limits, avoid repetition
5. **Code Blocks**: Use appropriate syntax highlighting
6. **Formatting**: Use bullet points and structure for readability

---

**Last Updated:** 2025-10-25
**Project Creator:** Herman Swanepoel
