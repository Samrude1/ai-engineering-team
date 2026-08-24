# Environment Variables & Secrets Context

This document tracks all environment variables required by this project. AI agents should update this document whenever a new external service, API key, or configuration setting is introduced.

**Security Warning**: NEVER store actual secrets, passwords, or API keys in this file. This document only describes the *keys* and their *purpose*, so developers know how to configure their `.env` files.

## Required Environment Variables

| Variable Name | Required | Purpose | Example Value (DO NOT USE REAL SECRETS) |
| :--- | :--- | :--- | :--- |
| `OPENROUTER_API_KEY` | Yes | OpenRouter API Key for agent LLM inference | `sk-or-v1-xxxxxxxxxxxx` |
| `LEAD_MODEL` | No | LLM model for Engineering Lead Architect | `openrouter/anthropic/claude-opus-4.5` |
| `ENGINEER_MODEL` | No | LLM model for Developer and QA agents | `openrouter/anthropic/claude-sonnet-4.5` |
| `WRITER_MODEL` | No | LLM model for Documentation Writer agent | `openrouter/openai/gpt-4o` |
| `GRADIO_AUTH_USER` | No | Basic auth username for Gradio web interface | `admin` |
| `GRADIO_AUTH_PASSWORD` | No | Basic auth password for Gradio web interface | `strong_random_password` |
| `GRADIO_SERVER_NAME` | No | Host IP interface to bind Gradio server | `127.0.0.1` |
| `GRADIO_SERVER_PORT` | No | Port number to bind Gradio server | `7860` |

---

*(Note: When setting up a new project, use this list to create your `.env.local` or configure your CI/CD environment.)*
