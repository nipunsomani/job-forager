# RULES.md - Operating Guardrails for AI Agents

These rules are hard constraints. Check them before every action.

## 1. No GitHub pushes without explicit permission

- Never run `git push` unless the user explicitly says "push to GitHub", "commit and push", or similar.
- Never assume a commit or push is implied by making changes.

## 2. No surface-level answers - deep research required

- If uncertain about anything, dig into the codebase, read source code, test APIs, and verify behavior with actual data.
- Find options, workarounds, and alternative approaches before recommending or implementing.
- Present findings to the user for review before acting. Never present a single option when multiple exist.
- Document the research path taken so the user can verify it.

## 3. No assumptions

- Never fill in gaps with personal defaults (locations, preferences, hardcoded lists, API keys, defaults).
- If a value is missing or ambiguous, ask the user. Do not guess.
- Never commit dictionaries, mappings, or allowlists with >5 items unless explicitly asked.
- Never assume a user's country, timezone, language, or platform preference.

## 4. No auto-fixes

- If something is broken, flag it explicitly and wait for user direction.
- Do not "fix" bugs, refactor code, or change behavior unless explicitly asked.
- Exception: If the user explicitly says "fix it" or "make it work", then proceed.

## 5. Do not break anything; do not touch anything not asked for

- Only modify files directly related to the user's request.
- Do not refactor adjacent code, update dependencies, or change formatting in unrelated files.
- Do not remove functionality, tests, or comments unless explicitly asked.
- Run the full test suite after any change. If tests break, revert and report.
