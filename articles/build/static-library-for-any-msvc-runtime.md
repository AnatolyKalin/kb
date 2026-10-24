---
title: "A static library links only with one C runtime: LNK2038, LNK4098, LNK2005 in the application"
area: build
tags: [windows, msvc, crt, linker, static-library, graalvm, native-image]
symptoms:
  - "`LNK2038: mismatch detected for 'RuntimeLibrary'`"
  - "`LNK2038: mismatch detected for '_ITERATOR_DEBUG_LEVEL'`"
  - "`LNK4098: defaultlib 'LIBCMT' conflicts with use of other libs`"
  - "`LNK2005: deflate already defined` when linking a third-party static library"
  - "`LNK4099: PDB 'vc140.pdb' was not found`"
  - "The application's executable exports the functions of a static library"
updated: 2026-10
---

# A static library links only with one C runtime: LNK2038, LNK4098, LNK2005 in the application

**English** | [Русский](static-library-for-any-msvc-runtime.ru.md)

A static library for MSVC (`.lib`) is built with one C runtime option, while its users build with `/MT`, `/MTd`, `/MD`
or `/MDd`. With a different option the link fails, or it pulls in two C runtimes. Third-party code inside the library
(zlib, JNI helpers) clashes with the application's own copies, the executable exports the library's API, and `/DEBUG`
warns about a PDB that nobody shipped. Typical for prebuilt objects: a vendor SDK, a GraalVM native-image static
library.

Verified with MSVC 19.42 (VS 2022) on Windows 11; see [How to test](#how-to-test).

## Symptoms

```text
error LNK2038: mismatch detected for 'RuntimeLibrary': value 'MT_StaticRelease' doesn't match value
    'MD_DynamicRelease' in app.obj
warning LNK4098: defaultlib 'LIBCMT' conflicts with use of other libs; use /NODEFAULTLIB:library
error LNK2005: deflate already defined in app.obj
warning LNK4099: PDB '' was not found with 'mylib.lib(mylib.obj)' or at ''; linking object as if no debug info
```

- `_ITERATOR_DEBUG_LEVEL` mismatches between a release library and a debug application (`/MTd`, `/MDd`).
- `dumpbin /exports app.exe` lists the library's functions, and the link writes `app.lib` and `app.exp` next to the
  executable.

## Causes

1. **Every object records its C runtime.** `/MT`, `/MD` and the debug variants put the name of their CRT library into
   the object as `/DEFAULTLIB:LIBCMT`, `MSVCRT` and so on
   ([/MD, /MT](https://learn.microsoft.com/en-us/cpp/build/reference/md-mt-ld-use-run-time-library)); two different
   names in one link give
   [LNK4098](https://learn.microsoft.com/en-us/cpp/error-messages/tool-errors/linker-tools-warning-lnk4098). The CRT
   and C++ headers also add `/FAILIFMISMATCH` records through
   [`#pragma detect_mismatch`](https://learn.microsoft.com/en-us/cpp/preprocessor/detect-mismatch): `RuntimeLibrary`,
   `_ITERATOR_DEBUG_LEVEL`, `_MSC_VER`; a different value fails the link with
   [LNK2038](https://learn.microsoft.com/en-us/cpp/error-messages/tool-errors/linker-tools-error-lnk2038).
2. **Objects compiled with `/MD` call the CRT through `__imp_` pointers.** They link with a `/MD` application only; a
   `/MT` application lacks the pointers (LNK2019 `__imp_<name>`), see
   [the article on the native-image DLL](native-image-dll-without-vc-redistributable.md). Objects compiled with `/MT`
   call the functions directly, and such a call links with either CRT: with `/MD` it goes through the import thunk.
3. **Every external symbol of the library is visible to the application.** An internal copy of zlib or of JNI
   helpers clashes with the application's
   ([LNK2005](https://learn.microsoft.com/en-us/cpp/error-messages/tool-errors/linker-tools-error-lnk2005)).
4. **`__declspec(dllexport)` survives in a static library.** It leaves an `/EXPORT:` directive in the object, so the
   executable that links the object exports the function.
5. **`/Zi` keeps the debug information in a PDB of the library's build.** Without that PDB the application's link with
   `/DEBUG` gives [LNK4099](https://learn.microsoft.com/en-us/cpp/error-messages/tool-errors/linker-tools-warning-lnk4099)
   and no debug information for the library. `/Z7` puts it into the objects
   ([/Z7, /Zi](https://learn.microsoft.com/en-us/cpp/build/reference/z7-zi-zi-debug-information-format)).
6. **The linker must not be older than the compiler of any input.** Microsoft guarantees binary compatibility only when
   the linker is the same version as, or newer than, the newest toolset that built an object or a library
   ([C++ binary compatibility](https://learn.microsoft.com/en-us/cpp/porting/binary-compat-2015-2017)).

## Recipe

**A C library you compile yourself: build it neutral.**

1. Compile with `/Zl` (no default library names in the objects,
   [/Zl](https://learn.microsoft.com/en-us/cpp/build/reference/zl-omit-default-library-name)) and `/Z7`, without
   `dllexport`, with internal functions `static` or under a prefix (as zlib does with `Z_PREFIX`):

   ```c
   #ifdef MYLIB_STATIC
   #    define MYLIB_API
   #else
   #    define MYLIB_API __declspec(dllexport)
   #endif
   ```

   ```bat
   cl /c /O2 /Zl /Z7 /DMYLIB_STATIC mylib.c
   lib /OUT:mylib.lib mylib.obj
   dumpbin /directives mylib.lib
   ```

2. `dumpbin /directives` must print nothing: no `/DEFAULTLIB`, `/FAILIFMISMATCH` or `/EXPORT`. Such a library links
   with `/MT`, `/MTd`, `/MD` and `/MDd` and uses the C runtime of the application: one heap, one `errno`.

**C++ with the standard library cannot be made neutral this way.** `/Zl` drops the CRT names, but the C++ headers still
write `RuntimeLibrary`, `_ITERATOR_DEBUG_LEVEL` and `/DEFAULTLIB:libcpmt`: the layout of `std::` types differs between
the flavours. Ship one library per flavour (release and debug, static and dynamic), or keep C++ out of the library and
expose a C API.

**Prebuilt objects you cannot recompile: rewrite the library.** No MSVC tool does this; it takes a small COFF rewriter
that goes over every member of the `.lib`:

1. Remove the `/EXPORT:` directives and the `/DEFAULTLIB:` of the CRT and C++ libraries (`MSVCRT`, `LIBCMT`, `msvcprt`,
   `libcpmt` and the debug ones).
2. Remove `/FAILIFMISMATCH:RuntimeLibrary` and `_ITERATOR_DEBUG_LEVEL`. This is safe for C objects only; check that no
   C++ object uses the standard library across the library boundary. Records like `_MSC_VER=1900` and
   `_CRT_STDIO_ISO_WIDE_SPECIFIERS=0` have the same value for every flavour and can stay.
3. Prefix every defined external symbol except the public API. Keep the names that must match outside the library: the
   targets of `/alternatename`, the compiler's shared COMDAT constants (`__real@`, `__xmm@`, `??_C@` string literals)
   and the inline functions of the CRT headers (`__local_stdio_*`).
4. Objects compiled with `/MD` also need the `__imp_` pointers of the CRT functions they call: add a shim object (see
   [the article on the native-image DLL](native-image-dll-without-vc-redistributable.md)) and prefix its pointers like
   the rest. They stay private to the library and point at the plain functions, so the linker binds them to whatever
   C runtime the application links.
5. Drop the debug information that refers to a PDB you do not ship, or ship the PDB.
6. State the minimum toolset: that of the newest compiler of the objects.

## How to test

- A matrix: link a test application with `/MT`, `/MTd`, `/MD`, `/MDd`, each with and without `/DEBUG`. The application
  defines the same names as the library's internals (`deflate`, `inflate`, a JNI helper) and has a C++ file with
  `std::vector`.
- For each link: exit code 0 and no warnings; `dumpbin /exports app.exe` is empty; with `/MT` and `/MTd`,
  `dumpbin /dependents` shows no `VCRUNTIME140*.dll`, `ucrtbase*.dll` or `api-ms-win-crt-*.dll`; the program runs.
- Red checks with the library as built originally: `/MT` and the application's `deflate` give LNK2005; `/MD` gives
  LNK2038 for `RuntimeLibrary` and LNK4098; `/DEBUG` gives LNK4099; the executable exports the API. Without the shim
  object, the link fails with LNK2019 for the prefixed `__imp_` pointers.

## Review checklist

- [ ] `dumpbin /directives` of the shipped library shows no CRT `/DEFAULTLIB`, no `RuntimeLibrary` or
      `_ITERATOR_DEBUG_LEVEL` records and no `/EXPORT`.
- [ ] Only the public API is visible: no unprefixed internal names (`dumpbin /symbols`, `External` and defined).
- [ ] No C++ standard library types cross the library boundary.
- [ ] The minimum MSVC toolset is documented.
- [ ] CI links and runs the four-flavour matrix with and without `/DEBUG` before publishing.

## Seen in

- **dxfeed-graal-native-sdk**: a GraalVM native-image static library repacked for any C runtime, since 3.10.0 in the
  `-static-lib` archives. The packer collects the image object and the JDK static libraries
  ([New-StaticLibrary.ps1](https://github.com/dxFeed/dxfeed-graal-native-sdk/blob/v3.11.0/scripts/windows-static-runtime/New-StaticLibrary.ps1)),
  and the COFF rewriter
  ([StaticLibrary.cs](https://github.com/dxFeed/dxfeed-graal-native-sdk/blob/v3.11.0/scripts/windows-static-runtime/StaticLibrary.cs))
  renames 2,677 of 5,183 public symbols, removes 3,116 `/EXPORT` and 146 CRT directives and drops the debug
  information of 15 objects that refer to `vc140.pdb`. The build checks the four-flavour matrix
  ([Test-StaticLibrary.ps1](https://github.com/dxFeed/dxfeed-graal-native-sdk/blob/v3.11.0/scripts/windows-static-runtime/Test-StaticLibrary.ps1)).
  The GraalVM libraries inside are built with MSVC 19.43, so the SDK asks for Visual Studio 2022 17.13 or newer.
- **zlib** and **ICU** rename their symbols for embedding: `Z_PREFIX` in
  [zconf.h](https://github.com/madler/zlib/blob/v1.3.1/zconf.h), `urename.h` in
  [ICU](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/common/unicode/urename.h).

## Open questions

- A rewritten library with C++ standard library code inside linked and ran with all four flavours in a small test,
  but it pulls the static release C++ library (`libcpmt`) into `/MD` and debug applications; not recommended, not
  verified at scale.
- Whether `llvm-objcopy` (`--prefix-symbols`, `--redefine-syms`) can do the renaming for COFF archives with
  `/alternatename` and COMDAT symbols: not tried.
- Objects compiled with `/GL` (link-time code generation) are not COFF and cannot be rewritten; not tried.
- An older linker (14.42) linked the 19.43 objects of the GraalVM library without errors here; this is outside the
  documented guarantee.
- Windows on ARM64 was not run.
