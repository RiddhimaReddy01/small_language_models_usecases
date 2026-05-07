# Claude Code Coding Standards

Use this file as the default coding standard for all generated, edited, or reviewed code.

The goal is to produce code that is clean, readable, maintainable, reliable, and easy for a new engineer to understand.

---

## 1. Core Principles

- Write code that is simple before it is clever.
- Prefer readable, direct solutions over abstract or over-engineered designs.
- Do not create stubs, placeholders, fake implementations, or TODO-only functions unless explicitly requested.
- Code should be functional, complete, and runnable as-is whenever possible.
- Optimize for correctness, clarity, maintainability, and reliability.
- Avoid unnecessary complexity, premature abstraction, and speculative features.

---

## 2. Code Structure and Modularity

- Each function should have one clear responsibility.
- Keep functions small and focused, ideally around 20–30 lines when practical.
- Avoid deep nesting. Prefer guard clauses and early returns.
- Keep branching logic explicit and readable.
- Prefer composition over inheritance.
- Avoid large “god functions” that perform validation, transformation, business logic, and I/O together.
- Split code into clear layers when relevant:
  - validation
  - transformation
  - business logic
  - persistence or I/O
  - presentation or API layer

---

## 3. Meaningful Naming

- Use names that explain intent, not implementation trivia.
- Prefer descriptive names over short names.
- Avoid vague names such as `data`, `temp`, `result`, `thing`, `stuff`, or `obj` unless the context is obvious.
- Function names should describe actions, for example:
  - `validate_customer_record`
  - `calculate_monthly_revenue`
  - `load_transactions_from_csv`
- Boolean names should read naturally:
  - `is_valid`
  - `has_missing_values`
  - `should_retry`
- Constants should be named clearly and not hidden as magic numbers.

---

## 4. Defensive Programming

- Validate all external inputs, including user input, files, API responses, database results, and environment variables.
- Fail fast when required inputs are missing or invalid.
- Use explicit checks for edge cases.
- Do not assume data is clean.
- Handle empty inputs, null values, malformed records, duplicate records, invalid types, and out-of-range values.
- Make assumptions explicit in code or documentation.
- Avoid silent failures.

---

## 5. Error Handling and Logging

- Raise clear, specific exceptions when something fails.
- Do not swallow exceptions without handling them meaningfully.
- Error messages should explain what failed and why.
- Include useful context in errors and logs, such as IDs, file paths, input sizes, or operation names.
- Use structured logging where appropriate.
- Use log levels consistently:
  - `debug` for diagnostic details
  - `info` for normal operational milestones
  - `warning` for recoverable issues
  - `error` for failures that require attention
- Never log secrets, passwords, API keys, tokens, or sensitive personal data.

---

## 6. Input Validation

- Validate inputs at system boundaries.
- Check required fields explicitly.
- Check data types before processing when data comes from unreliable sources.
- Normalize inputs when needed, but do not hide destructive transformations.
- Use schema validation where appropriate.
- In Python, consider `pydantic`, dataclasses, or explicit validation functions when useful.
- Prefer clear validation errors over downstream crashes.

---

## 7. Type Safety

- Use type hints for function arguments and return values.
- Avoid ambiguous types such as `Any` unless there is a strong reason.
- Prefer precise types:
  - `list[str]` instead of `list`
  - `dict[str, int]` instead of `dict`
  - custom dataclasses or models for structured data
- Function signatures should make inputs and outputs obvious.
- Do not return inconsistent types from the same function.
- Avoid returning `None` unless it is intentional and documented.

---

## 8. Testing Standards

- Code should be designed to be testable.
- Write unit-testable functions with clear inputs and outputs.
- Avoid hardcoded external dependencies inside core logic.
- Use dependency injection for databases, APIs, clients, and file paths when practical.
- Tests should cover:
  - normal cases
  - edge cases
  - invalid inputs
  - failure cases
- Avoid tests that depend on fragile timing, external services, or hidden state.
- Prefer deterministic tests.

---

## 9. Documentation and Comments

- Use docstrings for non-trivial functions, classes, and modules.
- A good docstring should explain:
  - what the function does
  - important inputs
  - returned output
  - important edge cases or assumptions
- Do not over-comment obvious code.
- Use comments to explain why something is done, not what the syntax does.
- Keep documentation updated when code changes.

---

## 10. Performance Awareness

- Do not prematurely optimize.
- Avoid obviously inefficient code.
- Avoid unnecessary repeated computation.
- Avoid redundant loops over the same data when a single pass is clear.
- Use appropriate data structures.
- For data science or analytics code, prefer vectorized operations when they improve clarity and performance.
- Make performance tradeoffs explicit when relevant.

---

## 11. State and Side Effects

- Prefer pure functions for core logic when possible.
- Isolate side effects such as:
  - file reads and writes
  - database calls
  - API calls
  - environment variable access
  - logging-heavy orchestration
- Avoid hidden global state.
- Avoid mutating inputs unless explicitly documented.
- Make state transitions clear and traceable.

---

## 12. Consistency Rules

- Follow consistent naming conventions.
- For Python, use:
  - `snake_case` for variables and functions
  - `PascalCase` for classes
  - `UPPER_SNAKE_CASE` for constants
- Keep file and module structure consistent.
- Use one consistent error-handling pattern per project.
- Use one consistent formatting style per project.
- Do not mix unrelated architectural patterns without reason.

---

## 13. Security Basics

- Never hardcode secrets, passwords, tokens, or API keys.
- Read secrets from environment variables or a secure secrets manager.
- Treat all external input as untrusted.
- Sanitize file paths, SQL queries, shell commands, and user-provided strings.
- Avoid unsafe deserialization.
- Do not use `eval` or `exec` unless explicitly justified and isolated.
- Use parameterized queries for database access.
- Avoid exposing internal stack traces to end users.

---

## 14. Dependency Management

- Prefer the standard library when it is sufficient.
- Add external dependencies only when they provide clear value.
- Avoid adding heavy libraries for small tasks.
- Keep imports clean and organized.
- Remove unused imports and unused dependencies.
- Do not introduce a framework when a simple function or module is enough.

---

## 15. Anti-Patterns to Avoid

Avoid the following unless there is a strong and explicit reason:

- God functions
- Magic numbers
- Commented-out dead code
- Placeholder functions
- Fake implementations
- Excessive inheritance
- Overuse of classes where functions are simpler
- Premature generalization
- Deeply nested conditionals
- Silent exception handling
- Hidden global state
- Copy-pasted duplicate logic
- Unclear abbreviations
- Unnecessary cleverness

---

## 16. Output Quality Standard

When generating code:

- Provide complete code, not fragments, unless explicitly asked for a fragment.
- Include all required imports.
- Ensure the code can run as-is when possible.
- Do not leave missing pieces for the user to fill in.
- Do not use placeholders such as:
  - `pass`
  - `TODO`
  - `your_code_here`
  - `implement later`
  - fake API responses
- Include minimal example usage when the code is non-trivial.
- Include tests or testing guidance when relevant.
- Explain any assumptions briefly.

---

## 17. Formatting

- Use clean formatting and logical spacing.
- For Python, follow Black and PEP 8 style.
- Prefer line length around 88–100 characters.
- Keep imports at the top of the file.
- Group imports in this order:
  1. standard library
  2. third-party libraries
  3. local project imports
- Remove unused code.
- Remove unused imports.
- Keep files organized and readable.

---

## 18. Code Review Checklist

Before finalizing code, check:

- Can a new engineer understand this in less than two minutes?
- Is every function doing one clear thing?
- Are the names meaningful?
- Are edge cases handled?
- Are invalid inputs handled?
- Are errors explicit and useful?
- Is there duplicated logic?
- Is there unnecessary abstraction?
- Is there hidden state?
- Are there magic numbers that should be constants?
- Are there secrets or sensitive values exposed?
- Can this be tested easily?
- Does the code run as-is?

---

## 19. Preferred Implementation Style

Use this default style unless the project requires otherwise:

- Simple functions first.
- Classes only when they meaningfully group state and behavior.
- Clear validation before business logic.
- Small helper functions for repeated logic.
- Explicit return values.
- Clear exceptions.
- Minimal dependencies.
- Deterministic behavior.
- Readable code over clever code.

---

## 20. Final Rule

If there is a tradeoff, choose the option that makes the code easier to understand, safer to modify, and less likely to fail silently.
