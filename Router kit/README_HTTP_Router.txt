AuralA HTTP Router Kit - README

Quick start:
1. Unzip this package in your project root.
2. Ensure Ollama CLI is installed and models are pulled.
3. Run: python setup.py
4. The system will install dependencies and launch the HTTP router on port 5050.
5. Point your IDE listener to http://localhost:3000/notify (or let the installer detect it).

Endpoints:
POST /route  -> JSON {task_type, prompt, context}
GET  /metrics -> model performance metrics
POST /autotune -> approve auto-tuning
POST /notify -> internal receiver (used by router to receive notifications)
