#!/bin/bash
echo "🚀 AI Agents Integration System - Code Quality Automation"
echo "========================================================="

# Enable new linters
echo "📦 Enabling new linters..."
echo "y" | trunk upgrade

# Auto-fix formatting
echo "🔧 Auto-fixing formatting..."
trunk fmt --all

# Auto-fix linting where possible
echo "🔍 Auto-fixing linting..."
trunk check --fix --all

# Remove trailing whitespace
echo "✂️ Removing trailing whitespace..."
find . -type f \( -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.json" -o -name "*.yml" -o -name "*.yaml" -o -name "*.md" -o -name "*.sh" -o -name "*.ps1" -o -name "*.bat" \) -exec sed -i 's/[[:space:]]*$//' {} \;

# Fix carriage returns
echo "🔄 Fixing carriage returns..."
find . -name "*.sh" -exec dos2unix {} \; 2>/dev/null || echo "dos2unix not available, using sed..."
find . -name "*.sh" -exec sed -i 's/\r$//' {} \;

echo "🎉 Cleanup completed!"
