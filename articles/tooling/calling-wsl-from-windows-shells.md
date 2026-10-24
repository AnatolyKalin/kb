---
title: "A command run in WSL from Git Bash or PowerShell arrives mangled"
area: tooling
tags: [wsl, git-bash, msys2, powershell, windows, shell, quoting, line-endings, python]
symptoms:
  - "`ls: cannot access 'C:/Program Files/Git/home/...'`: a Linux path became a Windows path"
  - "A variable in `wsl -- bash -c '...'` is empty"
  - "`;`, `<`, `>`, `\\` in the arguments of `wsl` act as shell syntax"
  - "`$'\\r': command not found` in a script from a Windows checkout"
  - "`python3` prints `Python ` and exits with code 9009"
updated: 2026-10
---

# A command run in WSL from Git Bash or PowerShell arrives mangled

**English** | [Русский](calling-wsl-from-windows-shells.ru.md)

Scripts on Windows that build or test on Linux through `wsl.exe`: CI helpers, agents, one-liners in a terminal. Each
layer between the Windows shell and the Linux program rewrites the command line in its own way.

Examples and links: [Seen in](#seen-in).

## Symptoms

- `ls: cannot access 'C:/Program Files/Git/home/user/src'`: the Linux path `/home/user/src` was rewritten.
- `wsl -- bash -c 'X=1; echo "[$X]"'` prints `[]`; a variable set or passed for the inner `bash` is empty.
- `wsl -- printf '[%s]\n' 'a;b'` prints `[a]n` and `b: command not found`: `;` split the command and `\n` lost its
  backslash.
- `$'\r': command not found`, or `cannot access '/some/path'$'\r'`, for a script that works on Linux.
- `python3 --version` prints `Python ` and exits with 9009; `py -3` works.

## Causes

1. **Git Bash converts arguments that look like POSIX paths.** The MSYS2 runtime under Git Bash rewrites arguments
   such as `/home/x` or `/mnt/c` into Windows paths (`C:/Program Files/Git/home/x`) when it starts a program that is
   not an MSYS program, and `wsl.exe` is not one.
2. **`wsl.exe` hands the command to the default Linux shell.** `wsl <command>` and `wsl -- <command>` do not run the
   command directly: they build one command line and pass it to the user's shell (`$SHELL -c`). Arguments with spaces
   are kept whole, but `$`, `;`, `<`, `>`, `|`, `\` and globs are parsed a second time, so `$X` is expanded by the
   outer shell, where it is not set. `wsl -e` (`--exec`) runs the program without that shell.
3. **PowerShell expands `$X` in double quotes itself.** Single quotes protect `$X` from PowerShell, not from cause 2.
4. **Windows environment variables do not reach WSL** unless they are listed in `WSLENV`.
5. **CRLF line endings.** A checkout with `core.autocrlf=true` gives scripts with `\r\n`; bash reads `\r` as part of
   the last word of every line.
6. **`python3` is an App Execution Alias.** `%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe` is a zero-length stub
   that opens the Microsoft Store; it comes first in `PATH` unless the alias is turned off.

## Recipe

1. **Turn off the path conversion for the call** in Git Bash: `MSYS_NO_PATHCONV=1` (Git for Windows), or
   `MSYS2_ARG_CONV_EXCL='*'` (MSYS2). For a single argument, a double leading slash also works: `//home/x`.
2. **Use `wsl -e` for anything with shell syntax**, and a script file for anything longer than one line. Pass the
   values as arguments or with `env`, not by text substitution:

   ```bash
   # Git Bash: the script reads $SDK; nothing is parsed twice.
   MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -e env SDK=/opt/sdk bash /mnt/c/src/ci/build.sh
   ```

   ```powershell
   wsl -d Ubuntu-24.04 -e bash -c 'X=1; echo "[$X]"'   # [1]
   wsl -d Ubuntu-24.04 -- bash -c 'X=1; echo "[$X]"'   # []  ($X expanded by the default shell)
   ```

3. **Pass Windows variables with `WSLENV`** when a script needs them (`WSLENV=SDK/p` also converts a Windows path
   into a Linux one).
4. **Keep shell scripts in LF**: `*.sh text eol=lf` in `.gitattributes`.
5. **Build on the Linux file system**: copy or `rsync` the sources to `~/...`; builds on `/mnt/c` are much slower.
6. **Call Python as `py -3`** in Windows scripts, or turn off the `python.exe` / `python3.exe` aliases in Settings ›
   Apps › Advanced app settings › App execution aliases.

## How to test

Each line is a red check; observed on Windows 11, WSL 3.0.3 (kernel 6.18), Git for Windows 2.55, PowerShell 7.6.

| Command | Result |
|---|---|
| `wsl -d Ubuntu-24.04 -- ls -d /home` (Git Bash) | `cannot access 'C:/Program Files/Git/home'` |
| `MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- ls -d /home` | `/home` |
| `wsl -d Ubuntu-24.04 -- ls -d //home` (Git Bash) | `/home` |
| `wsl -- bash -c 'X=1; echo "[$X]"'` (Git Bash or PowerShell) | `[]` |
| `wsl -e bash -c 'X=1; echo "[$X]"'` | `[1]` |
| `wsl -- env S=abc bash -c 'echo "[$S]"'` | `[]` |
| `wsl -e env S=abc bash -c 'echo "[$S]"'` | `[abc]` |
| `wsl -- printf '[%s]\n' 'a b' c` | `[a b]n[c]n`: spaces kept, `\` lost |
| `FOO=bar wsl -e printenv FOO` / with `WSLENV=FOO` | exit 1 / `bar` |
| `bash crlf.sh` with `ls /x\r\n` | `cannot access '/x'$'\r'` |
| `python3 --version` (PowerShell) | `Python `, exit code 9009 |

## Review checklist

- [ ] `wsl` with shell syntax in the arguments uses `-e`, or runs a script file.
- [ ] Git Bash calls with Linux paths set `MSYS_NO_PATHCONV=1`.
- [ ] No `$VAR` of the Linux side inside a `wsl -- ...` command line.
- [ ] `.gitattributes` keeps `*.sh` in LF.
- [ ] Windows scripts call `py -3`, not `python3`.

## Seen in

- **A C++ SDK build on Windows and WSL**: a verification script was started from Git Bash with
  `wsl -- bash -c '... $S ...'`; `$S` was empty, and `/home/...` arguments became `C:/Program Files/Git/home/...`.
  Fixed with `MSYS_NO_PATHCONV=1`, a script file and `env`.
- **Git for Windows** added `MSYS_NO_PATHCONV` because the conversion broke arguments of Windows programs; its release
  notes show `/usr/bin/bash.exe` turned into `C:\Program Files\Git\usr\bin\bash.exe`:
  [release notes](https://github.com/git-for-windows/build-extra/blob/main/ReleaseNotes.md),
  [the change](https://github.com/git-for-windows/msys2-runtime/pull/11).

## Sources

- Path conversion in MSYS2 and `MSYS2_ARG_CONV_EXCL`:
  [MSYS2, Filesystem Paths](https://www.msys2.org/docs/filesystem-paths/).
- `wsl --help`: `--exec, -e` runs the command without the default Linux shell; `--` passes the rest of the command
  line as is (to that shell).
- `WSLENV` and the performance of `/mnt/c`:
  [Working across Windows and Linux file systems](https://learn.microsoft.com/en-us/windows/wsl/filesystems).
- `eol=lf`: [gitattributes](https://git-scm.com/docs/gitattributes).
- App execution aliases and the `py` launcher: [Using Python on Windows](https://docs.python.org/3/using/windows.html).
- How PowerShell passes arguments to native programs, `$PSNativeCommandArgumentPassing`:
  [about_Preference_Variables](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_preference_variables).

## Open questions

- Whether the default shell of the distribution (zsh, fish) changes which characters are parsed again in cause 2: only
  bash was tested.
