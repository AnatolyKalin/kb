---
title: "The process allocator is replaced, but a native library still uses the old malloc"
area: platform
tags: [malloc, mimalloc, performance, linux, windows, macos, windows-dll, graalvm]
symptoms:
  - "mimalloc is plugged in, but the profile still shows the system `malloc` in a library's frames"
  - "`mimalloc-redirect.dll seems to be initialized after ucrtbase.dll`"
  - "`standard malloc is _not_ redirected!`"
  - "The process does not start: `0xC0000135`, `mimalloc-redirect.dll` was not found"
  - "`LD_PRELOAD` or `DYLD_INSERT_LIBRARIES` has no effect"
  - "Heap corruption in `free` of a pointer that another module allocated"
updated: 2026-10
---

# The process allocator is replaced, but a native library still uses the old malloc

**English** | [Русский](replacing-the-process-allocator.ru.md)

An application replaces `malloc` for the whole process (mimalloc here; jemalloc, tcmalloc and others work the same
way) to speed up a native library that allocates a lot: a GraalVM native image, a JNI library, a C library with many
small strings. The replacement works for the executable, but not for every module in the process, and nothing says so.

Measured with mimalloc v3.6.0 on Ubuntu 24.04 (gcc 13, glibc 2.39) and Windows 11 (MSVC 19.42); see
[How to test](#how-to-test).

## Symptoms

- The allocator is plugged in, the program runs, but there is no speed-up; the profile still shows the system allocator
  (`ucrtbase!malloc`, `RtlAllocateHeap`, glibc `_int_malloc`) under the library's frames.
- Windows, with `MIMALLOC_VERBOSE=1`:
  `mimalloc-redirect: error: mimalloc-redirect.dll seems to be initialized after ucrtbase.dll` and
  `warning: standard malloc is _not_ redirected! -- using regular malloc/free`.
- Windows: the process does not start, exit code `0xC0000135` (a DLL was not found).
- `LD_PRELOAD` (Linux) or `DYLD_INSERT_LIBRARIES` (macOS) changes nothing.
- A crash or heap corruption in `free` when a pointer allocated by one module is freed by another.

## Causes

The replacement happens at one level, and a module that does not go through that level keeps its own allocator.

1. **Linux: symbol interposition by the dynamic loader.** `LD_PRELOAD` (or a `malloc` defined in the executable) comes
   first in the global symbol scope, so every shared library that calls `malloc` gets it
   ([glibc: Replacing malloc](https://sourceware.org/glibc/manual/latest/html_node/Replacing-malloc.html)). It misses:
   - a statically linked executable (`-static`): there is no dynamic loader to act on `LD_PRELOAD`;
   - a library loaded with `dlopen(..., RTLD_DEEPBIND)`: it resolves `malloc` in its own dependencies (libc) first;
   - secure-execution mode (set-user-ID, set-group-ID): preload paths with slashes are ignored
     ([ld.so(8)](https://man7.org/linux/man-pages/man8/ld.so.8.html)).
2. **Windows: patching the CRT DLL.** `mimalloc-redirect.dll` redirects the allocation functions of `ucrtbase.dll`, the
   C runtime as a DLL; this needs the CRT as a DLL (`/MD`) and `mimalloc.dll` first in the imports of the executable
   ([mimalloc README](https://github.com/microsoft/mimalloc/blob/v3.6.0/readme.md#L537-L575)). It misses:
   - a module with a static CRT (`/MT`): every copy of the CRT has its own heap
     ([Microsoft Learn](https://learn.microsoft.com/en-us/cpp/c-runtime-library/potential-errors-passing-crt-objects-across-dll-boundaries));
     an executable with `/MT` keeps its own heap too, while its `/MD` DLLs are redirected;
   - any process where another DLL is imported before `mimalloc.dll`: that DLL loads `ucrtbase.dll` first, and the
     redirection gives up. The import order follows the order of the libraries on the link line;
   - a missing `mimalloc-redirect.dll`: `mimalloc.dll` imports it, so the loader also searches the current directory
     and `PATH` and takes **any** copy it finds there (another product may ship its own version), or the process does
     not start;
   - `MIMALLOC_DISABLE_REDIRECT=1` in the environment.
3. **macOS: dyld insertion and malloc zones.** `DYLD_INSERT_LIBRARIES` loads the library first, and mimalloc registers
   itself as the default malloc zone
   ([alloc-override-zone.c](https://github.com/microsoft/mimalloc/blob/v3.6.0/src/prim/osx/alloc-override-zone.c#L458-L470)).
   dyld ignores `DYLD_*` variables for binaries protected by System Integrity Protection
   ([dyld(1)](https://keith.github.io/xcode-man-pages/dyld.1.html)) and, according to Apple, for apps with the Hardened
   Runtime unless they have the entitlement
   [`com.apple.security.cs.allow-dyld-environment-variables`](https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.security.cs.allow-dyld-environment-variables).

Mixed allocators are worse than a missed speed-up: memory allocated by one allocator and freed by the other corrupts
the heap. Only a library whose memory never crosses its boundary can be left on its own allocator safely.

## Recipe

**Linux.**

1. To try it: `LD_PRELOAD=/path/to/libmimalloc.so ./app`.
2. To ship it: link mimalloc into the executable, so that no environment variable is needed. A `malloc` defined in the
   executable interposes for every shared library as `LD_PRELOAD` does:

   ```sh
   gcc -o app main.c /path/to/mimalloc.o -lthirdparty -lpthread   # or -lmimalloc early on the link line
   ```

3. Keep the executable dynamic (no `-static`), and do not load with `RTLD_DEEPBIND` a library whose memory crosses its
   boundary.

**Windows.**

1. Build the executable and every DLL that should be redirected with the CRT as a DLL (`/MD`).
2. Put `mimalloc.dll.lib` **first** on the link line and keep a reference to mimalloc, so that the linker does not drop
   the import (`/INCLUDE:mi_version` or a call to `mi_version()` in `main`):

   ```bat
   cl /MD main.c mimalloc.dll.lib thirdparty.lib /link /INCLUDE:mi_version
   ```

3. Ship `mimalloc.dll` and `mimalloc-redirect.dll` of the same version next to the executable.
4. Check the import order: `minject -l app.exe` (from the
   [`bin` folder](https://github.com/microsoft/mimalloc/tree/v3.6.0/bin) of mimalloc) must show `0: mimalloc.dll`;
   `minject` can also fix the order of an existing executable.
5. A DLL with a static CRT stays on its own heap; if its memory crosses its boundary, it must be freed by that DLL.

**macOS** (not verified here, see [Open questions](#open-questions)): `DYLD_INSERT_LIBRARIES=/path/to/libmimalloc.dylib`
works only for binaries that dyld does not protect; a shipped app links mimalloc instead.

## How to test

Ask the allocator itself whose memory a pointer is. The check looks mimalloc up at run time, so the same binary runs
with and without it:

```c
typedef bool (*in_heap_t)(const void *pointer);

#ifdef _WIN32
HMODULE module = GetModuleHandleA("mimalloc.dll");
in_heap_t inHeap = module != NULL ? (in_heap_t)GetProcAddress(module, "mi_is_in_heap_region") : NULL;
#else
in_heap_t inHeap = (in_heap_t)dlsym(RTLD_DEFAULT, "mi_is_in_heap_region");
#endif

void *pointer = thirdparty_allocate(64);   // memory that the library allocated with its malloc
printf("library malloc: %s\n", inHeap != NULL && inHeap(pointer) ? "mimalloc" : "system");
```

- Linux: run with `MIMALLOC_VERBOSE=1`; the line `mimalloc: process init` shows that mimalloc started at all.
- Windows: `MIMALLOC_VERBOSE=1` prints `mimalloc: malloc is redirected.` or the error above. Print the path of the
  loaded `mimalloc-redirect.dll` (`GetModuleFileNameA(GetModuleHandleA("mimalloc-redirect.dll"), ...)`) to catch a
  foreign copy.
- Red checks, each of which must print "system" for the library: Linux — `dlopen` with `RTLD_DEEPBIND`, a `-static`
  executable; Windows — the third-party import library before `mimalloc.dll.lib`, the library built with `/MT`,
  `MIMALLOC_DISABLE_REDIRECT=1`.
- On Linux, `mimalloc.o` hides its functions from `dlsym`; when it is linked into the executable, declare
  `mi_is_in_heap_region` as a weak symbol instead.

## Review checklist

- [ ] The executable and every library whose allocations matter use the CRT as a DLL (Windows) and the executable is
      dynamic (Linux).
- [ ] `mimalloc.dll` is the first import of the executable (`minject -l`).
- [ ] `mimalloc-redirect.dll` of the same version ships next to `mimalloc.dll`.
- [ ] No `RTLD_DEEPBIND` for libraries whose memory crosses their boundary.
- [ ] Memory that crosses a module boundary is freed by the module that allocated it, or by an allocator both share.
- [ ] A test asserts that the library's memory comes from the replaced allocator (`mi_is_in_heap_region`), on every OS
      of the release.

## Seen in

- **GraalVM native image**: unmanaged memory goes to the C runtime `malloc`
  ([`UnmanagedMemorySupportImpl`](https://github.com/oracle/graal/blob/092eca6772a74d4ce501d5656f61cfb26745ce73/substratevm/src/com.oracle.svm.core/src/com/oracle/svm/core/memory/UnmanagedMemorySupportImpl.java#L55-L61)),
  so the replacement covers a native-image library when it uses the CRT as a DLL. Checked with the DLL of
  [dxfeed-graal-native-sdk](https://github.com/dxFeed/dxfeed-graal-native-sdk): a string that the library returns comes
  from mimalloc when the executable links `mimalloc.dll` first. In the delivery of market events from that library to
  a C++ application, mimalloc saved about 10 % of the CPU per event on Linux. A build of such a library with a static
  CRT would keep the system heap.
- **mimalloc**: the redirect initialized after `ucrtbase.dll` because of the import order:
  [microsoft/mimalloc#668](https://github.com/microsoft/mimalloc/issues/668); the override inside a DLL that the
  application loads dynamically: [microsoft/mimalloc#820](https://github.com/microsoft/mimalloc/issues/820); crashes
  when freeing memory of other DLLs under the override:
  [microsoft/mimalloc#261](https://github.com/microsoft/mimalloc/issues/261),
  [microsoft/mimalloc#1128](https://github.com/microsoft/mimalloc/issues/1128); macOS, `free` interposed but `malloc`
  not: [microsoft/mimalloc#1350](https://github.com/microsoft/mimalloc/issues/1350).

## Open questions

- macOS was not run: `DYLD_INSERT_LIBRARIES`, the Hardened Runtime and linking mimalloc into an app.
- Linux secure-execution mode was not run.
- Whether CMake keeps `mimalloc` first in the imports when it is listed first in `target_link_libraries` and other
  targets bring their own dependencies: not checked; the test used the `cl` command line.
- A native-image library built with a static CRT was not run; the expectation (system heap) comes from the `/MT` case.
- Windows on ARM64 (`mimalloc-redirect-arm64.dll`, `-arm64ec`) was not run.
