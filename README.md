# Rakes and recipes

**English** | [Русский](README.ru.md)

Notes on recurring engineering problems: symptoms, causes, a verified recipe, how to test, a review checklist and
where else the problem has been seen. One article covers one class of problems. How to write one and how
translations work: [CONTRIBUTING.md](CONTRIBUTING.md); the template: [_template.md](_template.md).

## How to find an article

- By area, by symptom or by tag: the index below. It is generated from the front matter of the articles by
  `python3 tools/gen_index.py`; do not edit it by hand.
- By the text of an error or a log line: GitHub search in this repository (press `/` on the repository page), since
  the symptoms in the articles quote the key lines.
- Articles live in `articles/<area>/`; the areas are listed in [CONTRIBUTING.md](CONTRIBUTING.md#areas).

## Index

<!-- index:start -->

### By area

#### Lifetime: exit, destruction order, object ownership

- [Library constants are empty or crash in global initializers and destructors of user code](articles/lifetime/library-constants-in-global-initializers.md)
- [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md)

#### Platform: Windows, Linux, macOS specifics

- [The process allocator is replaced, but a native library still uses the old malloc](articles/platform/replacing-the-process-allocator.md)

#### Tooling: shells, WSL, git, GitHub, editors

- [A command run in WSL from Git Bash or PowerShell arrives mangled](articles/tooling/calling-wsl-from-windows-shells.md)

### By symptom

- A callback runs after the library objects are destroyed — [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md)
- A crash at exit on Windows: `0xc0000409` / `0xC0000005` — [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md)
- A crash before `main()` when a global variable calls a library function — [Library constants are empty or crash in global initializers and destructors of user code](articles/lifetime/library-constants-in-global-initializers.md)
- A hang or a crash in `DLL_PROCESS_DETACH` — [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md)
- A library constant is empty or zero in the initializer of a global variable — [Library constants are empty or crash in global initializers and destructors of user code](articles/lifetime/library-constants-in-global-initializers.md)
- A variable in `wsl -- bash -c '...'` is empty — [A command run in WSL from Git Bash or PowerShell arrives mangled](articles/tooling/calling-wsl-from-windows-shells.md)
- ASan: `initialization-order-fiasco` — [Library constants are empty or crash in global initializers and destructors of user code](articles/lifetime/library-constants-in-global-initializers.md)
- Heap corruption in `free` of a pointer that another module allocated — [The process allocator is replaced, but a native library still uses the old malloc](articles/platform/replacing-the-process-allocator.md)
- heap-use-after-free or a data race at exit under ASan / TSan — [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md)
- `;`, `<`, `>`, `\` in the arguments of `wsl` act as shell syntax — [A command run in WSL from Git Bash or PowerShell arrives mangled](articles/tooling/calling-wsl-from-windows-shells.md)
- It fails with the static library and works with the shared one — [Library constants are empty or crash in global initializers and destructors of user code](articles/lifetime/library-constants-in-global-initializers.md)
- `LD_PRELOAD` or `DYLD_INSERT_LIBRARIES` has no effect — [The process allocator is replaced, but a native library still uses the old malloc](articles/platform/replacing-the-process-allocator.md)
- `ls: cannot access 'C:/Program Files/Git/home/...'`: a Linux path became a Windows path — [A command run in WSL from Git Bash or PowerShell arrives mangled](articles/tooling/calling-wsl-from-windows-shells.md)
- mimalloc is plugged in, but the profile still shows the system `malloc` in a library's frames — [The process allocator is replaced, but a native library still uses the old malloc](articles/platform/replacing-the-process-allocator.md)
- `mimalloc-redirect.dll seems to be initialized after ucrtbase.dll` — [The process allocator is replaced, but a native library still uses the old malloc](articles/platform/replacing-the-process-allocator.md)
- `pure virtual function call` in the destructor of a global variable at exit — [Library constants are empty or crash in global initializers and destructors of user code](articles/lifetime/library-constants-in-global-initializers.md)
- `python3` prints `Python ` and exits with code 9009 — [A command run in WSL from Git Bash or PowerShell arrives mangled](articles/tooling/calling-wsl-from-windows-shells.md)
- `$'\r': command not found` in a script from a Windows checkout — [A command run in WSL from Git Bash or PowerShell arrives mangled](articles/tooling/calling-wsl-from-windows-shells.md)
- `standard malloc is _not_ redirected!` — [The process allocator is replaced, but a native library still uses the old malloc](articles/platform/replacing-the-process-allocator.md)
- The process does not start: `0xC0000135`, `mimalloc-redirect.dll` was not found — [The process allocator is replaced, but a native library still uses the old malloc](articles/platform/replacing-the-process-allocator.md)
- The process hangs at exit after `return` from `main()` — [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md)

### By tag

- `c++`: [Library constants are empty or crash in global initializers and destructors of user code](articles/lifetime/library-constants-in-global-initializers.md); [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md)
- `callbacks`: [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md)
- `constexpr`: [Library constants are empty or crash in global initializers and destructors of user code](articles/lifetime/library-constants-in-global-initializers.md)
- `constinit`: [Library constants are empty or crash in global initializers and destructors of user code](articles/lifetime/library-constants-in-global-initializers.md)
- `exit`: [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md)
- `git-bash`: [A command run in WSL from Git Bash or PowerShell arrives mangled](articles/tooling/calling-wsl-from-windows-shells.md)
- `graalvm`: [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md); [The process allocator is replaced, but a native library still uses the old malloc](articles/platform/replacing-the-process-allocator.md)
- `jni`: [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md)
- `lifetime`: [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md)
- `line-endings`: [A command run in WSL from Git Bash or PowerShell arrives mangled](articles/tooling/calling-wsl-from-windows-shells.md)
- `linux`: [The process allocator is replaced, but a native library still uses the old malloc](articles/platform/replacing-the-process-allocator.md)
- `macos`: [The process allocator is replaced, but a native library still uses the old malloc](articles/platform/replacing-the-process-allocator.md)
- `malloc`: [The process allocator is replaced, but a native library still uses the old malloc](articles/platform/replacing-the-process-allocator.md)
- `mimalloc`: [The process allocator is replaced, but a native library still uses the old malloc](articles/platform/replacing-the-process-allocator.md)
- `msvc`: [Library constants are empty or crash in global initializers and destructors of user code](articles/lifetime/library-constants-in-global-initializers.md)
- `msys2`: [A command run in WSL from Git Bash or PowerShell arrives mangled](articles/tooling/calling-wsl-from-windows-shells.md)
- `performance`: [The process allocator is replaced, but a native library still uses the old malloc](articles/platform/replacing-the-process-allocator.md)
- `powershell`: [A command run in WSL from Git Bash or PowerShell arrives mangled](articles/tooling/calling-wsl-from-windows-shells.md)
- `python`: [A command run in WSL from Git Bash or PowerShell arrives mangled](articles/tooling/calling-wsl-from-windows-shells.md)
- `quoting`: [A command run in WSL from Git Bash or PowerShell arrives mangled](articles/tooling/calling-wsl-from-windows-shells.md)
- `sanitizers`: [Library constants are empty or crash in global initializers and destructors of user code](articles/lifetime/library-constants-in-global-initializers.md); [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md)
- `shell`: [A command run in WSL from Git Bash or PowerShell arrives mangled](articles/tooling/calling-wsl-from-windows-shells.md)
- `static-destruction`: [Library constants are empty or crash in global initializers and destructors of user code](articles/lifetime/library-constants-in-global-initializers.md)
- `static-initialization`: [Library constants are empty or crash in global initializers and destructors of user code](articles/lifetime/library-constants-in-global-initializers.md)
- `static-library`: [Library constants are empty or crash in global initializers and destructors of user code](articles/lifetime/library-constants-in-global-initializers.md)
- `threads`: [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md)
- `windows`: [The process allocator is replaced, but a native library still uses the old malloc](articles/platform/replacing-the-process-allocator.md); [A command run in WSL from Git Bash or PowerShell arrives mangled](articles/tooling/calling-wsl-from-windows-shells.md)
- `windows-dll`: [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md); [The process allocator is replaced, but a native library still uses the old malloc](articles/platform/replacing-the-process-allocator.md)
- `wsl`: [A command run in WSL from Git Bash or PowerShell arrives mangled](articles/tooling/calling-wsl-from-windows-shells.md)

<!-- index:end -->

## License

The texts are licensed under [Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSE).
