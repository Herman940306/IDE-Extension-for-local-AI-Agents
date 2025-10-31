<!-- Placeholder: ANTHROPIC_API_KEY not set. Skipping doc rewrite. -->
# AuraIA Documentation Overview

Welcome to AuraIA. This overview points you to the most important documents and quick-starts.

## What is AuraIA?

AuraIA is a privacy-first, multi-agent coding partner for VS Code. It combines a fast System 1 triage with a deep System 2 verifier, and specialized engines for coding, conversation, and long-term context.

- Summary: See the root README for a concise overview.
- Product Requirements: The full vision and architecture live in the PRD.

## Quick Start

- Backend: Use the VS Code Task "Python: Run API (Uvicorn)" to start FastAPI on <http://127.0.0.1:8001>.
- Frontend: `cd frontend && npm run dev` (default <http://127.0.0.1:5288>).
- Extension: `cd extension && npm install && npm run compile`, then press F5 in VS Code to launch the extension host.

## Key Architecture

- System 1 (qwen3:8b): fast routing and quick responses.
- Code Engine (codellama:7b): code generation and refactors.
- System 2 (deepseek-r1:8b): verification and deeper reasoning.
- Conversational Agent (gemma3:12b): user-facing tone/persona.
- Context Engine (nomic-embed-text): embeddings and semantic recall.

## Links

- PRD: ../AuraIA IDE Vision and Roadmap/AuraIA_PRD.md
- Backend API Reference: backend/README.md (if present)
- Extension Guide: extension/README.md
- Troubleshooting: HOW_TO_RUN.md, DOCKER_SETUP_GUIDE.md
