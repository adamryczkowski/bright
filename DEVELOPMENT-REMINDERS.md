# Development Reminders for bright Project

**Last Updated:** 2025-01-12

This document contains important reminders and guidelines for working on this project.

## General Development Guidelines

### Date Reference
- **Current Date:** 2025-01-12 (12th of January 2025)
- Always check if tools, libraries, and documentation are up-to-date

### Research and Verification

1. **Assume Tools and Libraries Have Changed**
   - Tools and libraries change substantially over time
   - Always do web research before using them
   - Never rely solely on training data for technical information

2. **Web Search Protocol**
   - Use browsermcp for web searches
   - Start with general web search (DuckDuckGo or Google) unless certain about specific source URL
   - Check at least **5 different sources** when researching
   - Provide links to sources actually used
   - Don't just look at search results page - follow the links
   - If a link fails, try again using different means
   - Don't open PDF files via web search; use pdf-reader-mcp instead

3. **When Information is Missing**
   - If completing the task requires information not available locally or on the web
   - Always ask the operator for missing information
   - Wait for the answer before proceeding

### Source Code Investigation

- For advanced knowledge of open-source tools/libraries
- Consider downloading source code from GitHub or other repository hosting
- Inspect source code to understand how it works

### Command Execution

1. **Interrupted Commands**
   - If "^C" appears in terminal, assume command was interrupted by operator
   - Don't assume interrupted commands were successful

2. **Complex Commands**
   - Never execute complex commands with quoted strings or conditionals directly
   - Either use simple commands OR
   - Write a generic script in the `scripts` folder with accompanying just action (if justfile exists)

### File Operations

1. **Listing Files**
   - Use `git ls-tree --name-only -r $(git rev-parse --abbrev-ref HEAD)` OR
   - Use `fd` command
   - List files before reading them

2. **Editing Files**
   - Try hard NOT to use command line to edit source files
   - Use dedicated tools available for file editing

### System-Specific Information

**Operating System:** Ubuntu 24.04 LTS

**Shell Aliases:**
- `alias cat=bat`
- Bat is interactive by default; use `cat --paging=never <file>` for non-interactive output

**Available Commands:**
- `rg` (ripgrep)
- `fd` (fd-find)
- `pipx`
- `cookiecutter`
- `just`
- `poetry`
- `pre-commit`
- `git`
- `bat` and its alias `cat`
- `mise` (mise-en-place)

### Python Project Specifics

- If `pyproject.toml` exists in project root, assume it's a poetry project
- Use `poetry run` for commands that should run in project environment

### Debugging

- For finding root causes of problems, consider using `mcp-pdb` MCP tool
- Interactive debugging can make work much easier

### Project Validation

- If project contains `validate` action in justfile
- Run `just validate` after making changes

### Documentation Formats

**Never assume knowledge of:**
- Asciidoc syntax - check: https://docs.asciidoctor.org/asciidoc/latest/syntax-quick-reference/
- Asciimath (stem) syntax - check: https://asciimath.org/
- Just syntax - check: https://just.system/man/en

### Pre-commit Integration

- When adding a tool to pre-commit
- Check tool documentation first
- Research how it integrates with pre-commit

### Git Operations

- Do NOT attempt to change git repository state
- Do NOT commit changes
- Repository state changes are operator's responsibility

### System Environment Issues

**If anything promised is missing:**
- Missing or wrong software environment
- Missing MCP tools
- Broken connection to resources
- Missing files

**Action:** Immediately inform the operator and wait for instructions
- Do NOT attempt to fix or circumvent the problem yourself
- Only fix if explicitly instructed to do so

### Testing

- Never disarm unit/integration/any tests directly or indirectly
- Don't add timeouts to tests that take too long
- Tests must remain functional

### Remote Linux System Work

**When working with remote Linux systems:**

1. **SSH Connection**
   - Use `ssh-server` with interactive sessions only
   - Use: `ssh_start_interactive_shell`, `ssh_send_input`, `ssh_read_output`
   - Never use: `ssh-connect` and `ssh_execute`

2. **Default Connection Parameters** (unless specified otherwise)
   - User: `adam`
   - Private key: `/home/adam/.ssh/id_ed25519`
   - No passphrase
   - Port: 22

3. **Command Execution**
   - Don't prefix commands with `bash` (bash is default handler)
   - Connections persist - subsequent commands run in same session
   - Environment variables and session state are preserved

4. **Command Complexity**
   - Every remote command must be simple and short
   - Avoid conditionals and nested quoting

5. **Destructive Commands**
   - Every command with potential side effects must be confirmed with operator first
   - Provide clear explanation of:
     - Rationale
     - Expected outcome
     - Possible risks

6. **Documentation**
   - Document every remote command in `remote-work-log.md`
   - Include: intention, input, output (stdout/stderr), interpretation

### Illustrations and Diagrams

**When making illustrations, diagrams, or graphical content:**

1. Follow instructions in `how-to-make-illustrations.txt`
2. If instructions are absent, stop and ask operator for guidance
3. Before starting illustration work:
   - Put instructions into TODO list
   - Keep them there for duration of illustration-making task
4. After completing illustration work:
   - Remove instructions from TODO list

### Git Paging

- `git diff` defaults to using a pager
- To disable paging: `git --no-pager diff`

## Project-Specific Notes

### Keyboard Backlight Support

- Project already supports discrete brightness levels via brightnessctl backend
- See [`docs/keyboard-backlight-3-level-adaptation-plan.md`](docs/keyboard-backlight-3-level-adaptation-plan.md) for details
- No code changes needed for 3-level keyboard support
- Configuration tuning may be desired for optimal behavior

### Testing Commands

```bash
# Validate project
just validate

# Test keyboard backlight
bright test-keyboard

# Run tests
just test
```

### Configuration

- User config: `~/.config/bright/config.toml`
- Example config: [`docs/config.toml.example`](docs/config.toml.example)
- State file: `~/.local/share/brightness_level`

---

**Remember:** These reminders exist to ensure high-quality, safe, and efficient development. Always refer back to this document when in doubt.
