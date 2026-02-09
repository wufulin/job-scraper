# Issues

## 2026-02-10 Pre-Planning

### I1: WeWorkRemotely RSS URLs in brainstorm are WRONG
- Brainstorm says: `/categories/remote-programming-jobs.rss`
- Reality: URL changed to `/remote-jobs.rss` (old returns 301)
- MUST use verified URL

### I2: RemoteOK API first element is legal notice
- First array element is NOT a job posting
- Parser must detect and skip non-job entries

### I3: Brainstorm pseudocode has incorrect APIs
- `playwright-stealth` API shown as `Stealth().use_async()` — not real API
- `sqlite3` used synchronously in async context examples
- DO NOT copy pseudocode verbatim

## Task 1: Project Skeleton Setup

### Environment Issues Encountered
1. **Python execution in bash**: The bash environment (Git Bash on Windows) had issues capturing Python stdout. Commands like `python -c "print('test')"` ran without errors but produced no visible output.

2. **Windows Store Python stub**: The default `python` command pointed to Windows Store stub at `/c/Users/wu_fu/AppData/Local/Microsoft/WindowsApps/python`, which doesn't work properly in Git Bash.

3. **Package installation verification**: `pip install -e ".[dev]"` appeared to run silently without confirming installation. No .egg-info directory was created.

### Workarounds Applied
- Used `python3` instead of `python` where possible
- Attempted to install dependencies with `--user` flag
- Created test scripts that write to files instead of stdout
- Manually verified YAML syntax by reading files with mcp_read tool

### Resolution Status
- All files created successfully
- YAML files are syntactically valid (verified by inspection)
- Directory structure complete
- Dependencies listed correctly in pyproject.toml
- Actual package installation and Python execution will need to be verified in a proper Python environment (not Git Bash)

### Recommendation for Next Tasks
When running Python code in subsequent tasks, consider:
1. Using a proper Windows terminal (PowerShell/CMD) instead of Git Bash
2. Creating a virtual environment explicitly
3. Verifying package installation with `pip list` or `pip show`
4. Testing imports in a Python REPL rather than bash one-liners

