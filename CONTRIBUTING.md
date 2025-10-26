# Contributing to AuraIA

Thank you for your interest in contributing to AuraIA! We welcome contributions from the community.

## 🤝 How to Contribute

### Reporting Bugs

- Use GitHub Issues
- Include reproduction steps
- Provide system info (OS, Node/Python versions)
- Include error logs if applicable

### Suggesting Features

- Open a GitHub Discussion first
- Explain the use case
- Consider if it fits the "local-first" philosophy

### Code Contributions

#### Getting Started

1. Fork the repository
2. Clone your fork
3. Create a feature branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test thoroughly
6. Commit with clear messages
7. Push and create a Pull Request

#### Development Setup

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For testing

# Frontend
cd frontend
npm install

# Extension
cd extension
npm install
```

## 📋 Code Standards

### Python (Backend)

- Follow PEP 8
- Use type hints
- Add docstrings for public functions
- Format with Black: `black backend --line-length=100`
- Lint with Flake8: `flake8 backend`
- Type check with mypy: `mypy backend/src`

### TypeScript (Frontend/Extension)

- Follow ESLint rules
- Use TypeScript strict mode
- Add JSDoc comments for public APIs
- Format with Prettier

### Git Commit Messages

```
feat: Add new feature
fix: Fix bug
docs: Update documentation
style: Code style changes
refactor: Code refactoring
test: Add or update tests
chore: Maintenance tasks
```

## 🧪 Testing

### Run Tests

```bash
# Backend
pytest backend/tests -v

# With coverage
pytest backend/tests --cov=backend/src --cov-report=html

# Frontend
cd frontend
npm test

# Extension
cd extension
npm test
```

### Writing Tests

- Add tests for new features
- Maintain >80% code coverage
- Use meaningful test names
- Mock external dependencies (LLM calls, etc.)

## 🎯 Pull Request Process

1. **Update Documentation** - README, docstrings, etc.
2. **Add Tests** - New code should have tests
3. **Run Linters** - `black`, `flake8`, `mypy`, `eslint`
4. **Update CHANGELOG.md** - Add entry for your changes
5. **Link Issues** - Reference related issues
6. **Request Review** - Tag maintainers

### PR Checklist

- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] All tests pass
- [ ] No merge conflicts

## 🏗️ Architecture Guidelines

### Adding New Agents

1. Extend `BaseAgent` in `backend/src/agents/base_agent.py`
2. Implement required methods
3. Register in `backend/src/core/container.py`
4. Add tests in `backend/tests/agents/`
5. Update documentation

### Adding New Models

1. Update `backend/src/config/settings.py`
2. Add model configuration
3. Update documentation
4. Test with different hardware profiles

### Frontend Components

1. Use functional React components
2. TypeScript for type safety
3. Keep components small and focused
4. Use CSS modules or styled-components

## 🛡️ Security

### Reporting Security Issues

**DO NOT** open public issues for security vulnerabilities.

Email: <security@auraia.dev> (or maintainer's private email)

### Security Best Practices

- Never commit API keys or secrets
- Sanitize user inputs
- Use prepared statements for database queries
- Keep dependencies updated

## 📄 Contributor License Agreement

By contributing to AuraIA, you agree that your contributions will be licensed under the MIT License (Community Edition).

For proprietary extensions, contributors may be asked to sign a CLA allowing dual-licensing.

## 🌟 Recognition

Contributors will be:

- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Given credit in documentation

## 💬 Communication

- **GitHub Issues** - Bug reports, feature requests
- **GitHub Discussions** - Questions, ideas, general discussion
- **Discord** - Real-time chat (coming soon)
- **Email** - For sensitive matters

## 📚 Resources

- [Architecture Documentation](ARCHITECTURE_V2_NEXTGEN.md)
- [Developer Guide](DEVELOPER_GUIDE.md)
- [Quick Start](QUICKSTART.md)
- [API Reference](API_REFERENCE.md)

## ❓ Questions?

Don't hesitate to ask! Open a GitHub Discussion or reach out to maintainers.

---

**Thank you for making AuraIA better! 🚀**

*The future is beside you.*
