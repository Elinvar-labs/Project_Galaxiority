# DEVOXXGENIE.md

## Project Guidelines

### Build Commands

- **Build:** `uv sync`
- **Test:** `uv run tests.py`
- **Single Test:** `uv run tests.py --tests ClassName.methodName`
- **Clean:** `rmdir /s /q .venv`
- **Run:** `uv run game.py`

### Code Style

- **Formatting:** Use IDE or checkstyle for formatting
- **Naming:**
  - Use camelCase for variables, methods, and fields
  - Use PascalCase for classes and interfaces
  - Use SCREAMING_SNAKE_CASE for constants
- **Documentation:** Use JavaDoc for documentation
- **Imports:** Organize imports and avoid wildcard imports
- **Exception Handling:** Prefer specific exceptions and document throws

