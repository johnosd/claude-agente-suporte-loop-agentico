# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run all tests
pytest

# Run the agent with built-in test scenarios
python app/agent.py

# Install dependencies
pip install -r requirements.txt
```

Requires `ANTHROPIC_API_KEY` environment variable (loaded via `python-dotenv`).

## Architecture

This project implements an **agentic loop** pattern using the Claude API for a customer support use case.

### Agentic Loop (`app/agent.py`)

The core loop in `run_agent(user_message)` works as follows:

1. Send the user message to Claude with tool definitions
2. Check `response.stop_reason`:
   - `"end_turn"` → extract text content and return
   - `"tool_use"` → execute the requested tool, append the result to `messages`, and loop back to step 1

### Tools

Three mock customer support tools are defined inline in `agent.py`:
- `get_customer` — retrieves customer info by ID
- `lookup_order` — retrieves order details by order number
- `process_refund` — marks an order as refunded

The tool definitions (JSON schema) and their implementations (Python functions) are both in `agent.py`. Claude decides which tool(s) to call based on the conversation.

### Model

Uses `claude-opus-4-5` with `max_tokens=1024`.
