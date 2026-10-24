---
title: "Backslashes disappear from code written through a shell"
area: tooling
tags: [shell, bash, git-bash, msys2, windows, quoting, escaping, heredoc, sed, python, agents]
symptoms:
  - "`missing terminating ' character`: a char literal `'\\\\'` was written as `'\\'`"
  - "`unknown escape sequence: '\\d'`: a regex `\"\\\\d\"` was written as `\"\\d\"`"
  - "A quoted heredoc `<<'EOF'` still loses every second backslash"
  - "`\\n` turns into `n`, a path `C:\\x\\y` into `C:xy`"
updated: 2026-10
---

# Backslashes disappear from code written through a shell

**English** | [Русский](backslashes-lost-on-the-way-through-a-shell.ru.md)

Source code, regular expressions and Windows paths written to a file or passed as a command through a shell: by a
script, an AI agent's shell tool, or a one-liner. Every layer on the way may treat `\` as an escape character and
eat one of two.

Examples and links: [Seen in](#seen-in).

## Symptoms

- `if (c == '\\')` arrives as `if (c == '\')`: `missing terminating ' character`, the build fails.
- `std::regex("\\d")` arrives as `std::regex("\d")`: only a warning, `unknown escape sequence: '\d'`, and the
  pattern now matches the letter `d`.
- A heredoc with a quoted delimiter (`<<'EOF'`), which bash never touches, still loses every second backslash.
- `\n` in a format turns into `n`; `C:\x\y` turns into `C:xy`.

## Causes

1. **Git Bash parses its own Windows command line.** A Windows program that starts Git Bash as
   `bash.exe -c "<script>"` passes the script as one quoted argument. The MSYS2 runtime splits the command line
   itself and turns `\\` into `\` inside a quoted argument, before bash sees the script; so a quoted heredoc does not
   help. An argument without spaces is not quoted and arrives intact. Programs that follow the Microsoft rules
   (`wsl.exe`, `python.exe`) keep `\\`. This hits:
   - shell tools of AI agents on Windows that run commands through Git Bash (seen with the Bash tool of Claude Code:
     the Write, Edit and PowerShell tools of the same agent keep the bytes);
   - `subprocess.run(["bash", "-c", script])` in Python, `& bash.exe -c "..."` in PowerShell.
2. **Bash itself treats `\` as an escape in many places:**
   - an unquoted heredoc (`<<EOF`) and double quotes: `\\` → `\`;
   - `echo -e` and the format string of `printf`: `\\` → `\`, `\n` → newline;
   - `read` without `-r`: `\\` → `\`, a single `\` is removed;
   - the replacement of `sed s/…/…/`: `\\` → `\`, and a variable expanded into it is parsed the same way;
   - an unquoted Windows path: `C:\x\y` → `C:xy`.
3. **A string literal of another language on the way.** Code wrapped into a Python, JSON or C string to be written
   out loses one level: `"\\d"` in a Python string is `\d`. Layers multiply: a Python script inside
   `bash -c "..."` started from Windows halves the backslashes twice.
4. **`wsl -- <command>` parses the command a second time** in the default Linux shell: see
   [A command run in WSL from Git Bash or PowerShell arrives mangled](calling-wsl-from-windows-shells.md).

## Recipe

1. **Write code with a file tool, not through a shell**: an editor, the agent's file write and edit tools, or a
   script that copies a file. An AI agent on Windows must not write text with `\` through its Git Bash tool, even
   with `<<'EOF'`.
2. **When a shell is the only way, keep the text out of the command line.** Put the script into a file and run
   `bash script.sh`; inside it, use a quoted heredoc, `printf '%s\n' "$text"` and `read -r`:

   ```bash
   # In a script file: the text is copied byte for byte.
   cat > test.cpp <<'EOF'
   CHECK(getExchangesByPattern("\\d") == "0123456789");
   EOF
   ```

3. **From a Windows program, pass Git Bash a file, not a script text**: `subprocess.run(["bash", "script.sh"])`.
4. **In Python, use raw strings or read the text from a file**: `r"\\d"` keeps both backslashes.
5. **In `sed`, do not expand text into the replacement**; use a file tool or a script that replaces literally
   (`str.replace` in Python).
6. **Write Windows paths with forward slashes** (`C:/x/y`): Windows programs, Git Bash and `wslpath` accept them.
7. **Check the written file**: `grep -n '\\' file` shows every line with a backslash; compare it with the source
   before building.

## How to test

Each line prints what `if (c == '\\') re("\\d");` became; observed on Windows 11, Git for Windows 2.55 (bash 5.3),
PowerShell 7.6, WSL 3.0.3 with Ubuntu 24.04 (bash 5.2, GNU sed 4.9). Run the bash lines from a script file, not
from a command line, or the first cause hides the others.

| Where | Result |
|---|---|
| PowerShell: `& bash.exe -c "printf '[%s]\n' 'A\\B'"` (Git Bash) | `[A\B]` |
| PowerShell: `& bash.exe -c '…' x 'A\\B'` (argument without spaces) | `[A\\B]` |
| PowerShell: `& bash.exe -c '…' x 'A\\B C'` (argument with spaces) | `[A\B C]` |
| Python: `subprocess.run([bash, "-c", '…', "x", r"A\\B C"])` (Git Bash) | `[A\B C]` |
| PowerShell: `wsl -d Ubuntu-24.04 -e bash -c "printf '[%s]\n' 'A\\B'"` | `[A\\B]` |
| bash: `cat <<EOF` | `if (c == '\') re("\d");` |
| bash: `cat <<'EOF'` | `if (c == '\\') re("\\d");` |
| bash: `echo -e "$src"`, `printf "$src"` | `if (c == '\') re("\d");` |
| bash: `printf '%s' "$src"` | `if (c == '\\') re("\\d");` |
| bash: `read line` / `read -r line` | `'\'`, `"\d"` / unchanged |
| bash: `sed "s/X/$src/"` | `if (c == '\') re("\d");` |
| bash: `wslpath C:\x\y` / `wslpath 'C:\x\y'` | `C:xy` / `/mnt/c/x/y` |
| g++ 13 on `c == '\'` / on `"\d"` | `error: missing terminating ' character` / `warning: unknown escape sequence: '\d'` |

## Review checklist

- [ ] Files with `\` (C/C++ literals, regexes, Windows paths, JSON) are written by a file tool, not through a shell.
- [ ] No script text with `\` is passed to Git Bash as `bash -c "..."` from a Windows program.
- [ ] Heredocs that carry code use a quoted delimiter (`<<'EOF'`), and they live in script files.
- [ ] `read` has `-r`; text goes through `printf '%s'`, never through `echo -e` or a `printf` format.
- [ ] Every line with `\` in the written file was compared with the source.

## Seen in

- **A C++ SDK on Windows**: an AI agent added a test with `cat >> test.cpp <<'EOF'` through its Git Bash tool;
  `"\\d"` arrived as `"\d"`, which the compiler only warned about. A source file edited by a Python script passed
  the same way got `'\'` instead of `'\\'` and failed to build. Both lines were fixed with the agent's file edit
  tool.

## Sources

- How Windows programs split a command line (backslashes are special only before `"`):
  [Parsing C++ command-line arguments](https://learn.microsoft.com/en-us/cpp/cpp/main-function-command-line-args#parsing-c-command-line-arguments).
- Here documents, quoting, `read -r`, `echo -e`, `printf`:
  [Bash Reference Manual](https://www.gnu.org/software/bash/manual/bash.html).
- Backslashes in the replacement of `s`:
  [GNU sed, The "s" Command](https://www.gnu.org/software/sed/manual/sed.html#The-_0022s_0022-Command).
- Escape sequences and raw strings in Python:
  [Lexical analysis](https://docs.python.org/3/reference/lexical_analysis.html#escape-sequences).

## Open questions

- The rule of the MSYS2 runtime is observed, not read in its source: `\\` → `\` inside a quoted argument, `\\`
  intact in an unquoted one. Whether runs of three backslashes or a backslash before `"` follow the Microsoft
  rules was not tested.
