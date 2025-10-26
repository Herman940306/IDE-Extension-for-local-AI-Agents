"""
Test file for AuraIA Extension Demo
Created: 2025-10-25

This file contains sample code to test all extension features:
1. Generate Code
2. Refactor Code
3. Explain Code
4. Fix Bugs
"""


# Example 1: Code that needs refactoring
def calculate_total(items):
    """Calculate total of items - needs optimization"""
    total = 0
    for item in items:
        total = total + item
    return total


# Example 2: Code with potential bugs
def divide_numbers(a, b):
    """Divide two numbers - has a bug!"""
    result = a / b  # What if b is 0?
    return result


# Example 3: Complex code that needs explanation
def fibonacci(n):
    """Generate fibonacci sequence"""
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]
    else:
        fib = [0, 1]
        for i in range(2, n):
            fib.append(fib[i - 1] + fib[i - 2])
        return fib


# Example 4: Nested loops (bad performance)
def find_duplicates(list1, list2):
    """Find duplicates between two lists - inefficient!"""
    duplicates = []
    for item1 in list1:
        for item2 in list2:
            if item1 == item2:
                duplicates.append(item1)
    return duplicates


# Example 5: Poor variable naming
def proc(x, y, z):
    """Process some data - unclear naming"""
    a = x + y
    b = a * z
    c = b / 2
    return c


# Example 6: No error handling
def read_file(filename):
    """Read file contents - missing error handling"""
    file = open(filename, "r")
    content = file.read()
    file.close()
    return content


# Example 7: String concatenation in loop
def build_message(words):
    """Build message from words - inefficient string concat"""
    message = ""
    for word in words:
        message = message + word + " "
    return message


# Example 8: Missing type hints
def process_user_data(name, age, email):
    """Process user data - missing type hints"""
    user = {"name": name, "age": age, "email": email}
    return user


# Example 9: Long function that does too much
def validate_and_save_user(name, email, age, password):
    """Validate and save user - does too many things"""
    # Validate name
    if len(name) < 2:
        return False

    # Validate email
    if "@" not in email:
        return False

    # Validate age
    if age < 18 or age > 120:
        return False

    # Validate password
    if len(password) < 8:
        return False

    # Save to database
    user_data = {"name": name, "email": email, "age": age, "password": password}

    # Would save to database here
    print(f"User saved: {user_data}")
    return True


# Example 10: SQL injection vulnerability
def get_user_by_email(email):
    """Get user by email - SQL INJECTION RISK!"""
    query = f"SELECT * FROM users WHERE email = '{email}'"
    # This is vulnerable to SQL injection!
    return query


"""
=== TESTING INSTRUCTIONS ===

1. **Generate Code Test:**
   - Place cursor at line 100 below
   - Run: Ctrl+Shift+P → "Aura AI: Generate Code"
   - Enter: "Create a function to validate email addresses with regex"

2. **Refactor Code Test:**
   - Select lines 12-17 (calculate_total function)
   - Run: Ctrl+Shift+P → "Aura AI: Refactor Code"
   - Watch for line count feedback!

3. **Explain Code Test:**
   - Select lines 28-38 (fibonacci function)
   - Run: Ctrl+Shift+P → "Aura AI: Explain Code"
   - See progress indicator!

4. **Fix Bugs Test:**
   - Select lines 21-25 (divide_numbers function)
   - Run: Ctrl+Shift+P → "Aura AI: Fix Bugs"
   - Should detect division by zero!

5. **Multiple Issues Test:**
   - Select lines 98-109 (get_user_by_email function)
   - Run: Ctrl+Shift+P → "Aura AI: Fix Bugs"
   - Should detect SQL injection vulnerability!

=== Expected UI Enhancements ===
✅ Emoji feedback (🤖, ✨, 🔧, 📖, 🐛)
✅ Progress notifications
✅ Line count in messages
✅ Input validation
✅ Status bar updates
✅ Better error messages

"""

# Line 100 - Place cursor here for "Generate Code" test
