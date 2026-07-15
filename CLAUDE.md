# CLAUDE.md – CzechLens Project

## Core Behavior
- Do not rush. Verify all output. Run tests before declaring done.
- Use plan mode aggressively – before writing code, output a plan in <thinking> tags.
- After implementing a feature, provide a validation checklist and wait for my confirmation.

## Extended Thinking
- You will be run with extended thinking enabled (set in API/UI). Use the available thinking budget to reason through complex steps.

## Parallel Workflow
- You handle planning and high‑level instructions.
- For long‑running tasks (crawling, batch AI), output a standalone Python/shell script. Do not attempt to run it in this conversation.

## Watch the Harness
- I (the human) will evaluate your output by running tests and checking results. You will not assume success until I confirm.

## Plan Mode Details
- For any non‑trivial task, first output:
  1. What you will build
  2. How you will test it
  3. What could go wrong
- Only after that, write code.

## Code Quality
- Include error handling for edge cases.
- Use retries with exponential backoff for external APIs.

## Output Format
- Use `<thinking>` tags for reasoning (these render fine in VS Code chat).
- Use fenced code blocks (` ``` `) for all code samples.
- **NEVER use `<validation_checklist>`, `<code>`, or any other custom XML wrapper tags.**
  They collapse into unreadable raw text in VS Code chat.
  Write validation steps as a plain Markdown bullet list instead, for example:
  - [ ] V4.1 Load extension — confirm no errors in chrome://extensions
  - [ ] V4.2 Press Space+T — overlay appears with subtitle text