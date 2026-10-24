---
title: "A GraalVM native-image DLL still needs the Visual C++ Redistributable"
area: build
tags: [graalvm, native-image, windows, windows-dll, msvc, crt, linker]
symptoms:
  - "`VCRUNTIME140.dll was not found` on a machine without the Visual C++ Redistributable"
  - "Exit code `0xC0000135` when the application loads the library"
  - "`dumpbin /dependents` shows `VCRUNTIME140.dll` and `api-ms-win-crt-*.dll`"
  - "`LNK4098: defaultlib 'MSVCRT' conflicts with use of other libs`"
  - "`LNK2019: unresolved external symbol __imp_getenv`"
updated: 2026-10
---

# A GraalVM native-image DLL still needs the Visual C++ Redistributable

**English** | [Русский](native-image-dll-without-vc-redistributable.ru.md)

A library or an executable built by GraalVM native-image on Windows depends on the C runtime DLLs, so it needs the
Visual C++ Redistributable on the target machine. Switching it to the static C runtime (`/MT`) fails at link time. The
same happens with any module that links static libraries compiled with `/MD`, for example a vendor `.lib`.

Verified with GraalVM CE 25.4.4.1.1 and MSVC 19.42 (VS 2022) on Windows 11; see [How to test](#how-to-test).

## Symptoms

- On a clean machine: `The code execution cannot proceed because VCRUNTIME140.dll was not found`, or exit code
  `0xC0000135` (a DLL was not found) when the application loads the library.
- `dumpbin /dependents` lists `VCRUNTIME140.dll` (and `VCRUNTIME140_1.dll` with C++ exceptions) and
  `api-ms-win-crt-*.dll`.
- An attempt to link with the static CRT:

  ```text
  LINK : warning LNK4098: defaultlib 'MSVCRT' conflicts with use of other libs; use /NODEFAULTLIB:library
  LINK : warning LNK4217: symbol 'free' defined in 'libucrt.lib(free.obj)' is imported by 'vendor.lib(vendor.obj)'
  vendor.lib(vendor.obj) : error LNK2019: unresolved external symbol __imp_getenv referenced in function ...
  ```

## Causes

1. **native-image links with `/MD`.** `WindowsCCLinkerInvocation` passes `/MD` for executables and `/MD /LD` for
   shared libraries, with `/MT` commented out and the reason in the code: "Must use /MD in order to link with JDK
   native libraries built that way"
   ([CCLinkerInvocation.java](https://github.com/oracle/graal/blob/092eca6772a74d4ce501d5656f61cfb26745ce73/substratevm/src/com.oracle.svm.hosted/src/com/oracle/svm/hosted/image/CCLinkerInvocation.java#L560-L569)).
   `/MD` means the CRT as DLLs: `vcruntime140.dll` from the Redistributable and the Universal CRT
   ([CRT library features](https://learn.microsoft.com/en-us/cpp/c-runtime-library/crt-library-features)).
2. **Objects compiled with `/MD` call the CRT through import pointers.** With `/MD` the CRT headers declare functions
   `__declspec(dllimport)`, so the object calls `getenv` through the pointer `__imp_getenv`, which only the import
   library of the CRT DLL defines
   ([Importing with dllimport](https://learn.microsoft.com/en-us/cpp/build/importing-into-an-application-using-declspec-dllimport)).
   The static JDK libraries in GraalVM (`lib\static\windows-amd64`) are such objects. The static CRT (`libucrt.lib`,
   `libvcruntime.lib`, `libcmt.lib`) defines `getenv`, but not `__imp_getenv`.
3. **The linker fills only some of the pointers.** When the function is already linked from the static CRT for other
   code, the linker builds the pointer itself and warns with
   [LNK4217](https://learn.microsoft.com/en-us/cpp/error-messages/tool-errors/linker-tools-warning-lnk4217) or
   [LNK4286](https://learn.microsoft.com/en-us/cpp/error-messages/tool-errors/linker-tools-warning-lnk4286). A function
   that only the `/MD` objects call stays unresolved: LNK2019 `__imp_<name>`.

There is no official native-image option for a static CRT in a DLL. An open proposal,
[oracle/graal#14683](https://github.com/oracle/graal/issues/14683) with
[PR #14685](https://github.com/oracle/graal/pull/14685), adds `-H:+StaticVCRuntime` for executables only: static
vcruntime, dynamic Universal CRT.

## Recipe

1. **List the CRT functions the `/MD` objects take through pointers.** These are the undefined `__imp_` symbols of
   those libraries (`dumpbin /symbols`) that the import libraries of the dynamic CRT export (`dumpbin /exports` of
   `ucrt.lib`, `vcruntime.lib`, `msvcrt.lib`). Include the POSIX names: `__imp_strdup` points at `_strdup`.
2. **Define each pointer in an object of your own (a shim), compiled with `/MT`.** There the headers declare the
   functions without `dllimport`, so `&getenv` is the function of the static CRT:

   ```c
   #include <stdlib.h>
   #include <string.h>

   void *__imp_getenv = (void *)&getenv;
   void *__imp__strdup = (void *)&_strdup;
   void *__imp_strdup = (void *)&_strdup;   // the POSIX name
   ```

   With 100 and more functions a generated assembly file is easier: it needs no headers and no prototypes.

   ```asm
   EXTRN getenv:PROC
   PUBLIC __imp_getenv
   .data
   ALIGN 8
   __imp_getenv DQ getenv
   END
   ```

3. **Link with the static CRT instead of the dynamic one.** For native-image, pass the options through
   `-H:NativeLinkerOption`; it already adds `/NODEFAULTLIB:LIBCMT`, which drops only the default library, so
   `libcmt.lib` is named explicitly:

   ```text
   -H:NativeLinkerOption=/NODEFAULTLIB:MSVCRT
   -H:NativeLinkerOption=/NODEFAULTLIB:vcruntime.lib
   -H:NativeLinkerOption=/NODEFAULTLIB:ucrt.lib
   -H:NativeLinkerOption=libcmt.lib
   -H:NativeLinkerOption=libvcruntime.lib
   -H:NativeLinkerOption=libucrt.lib
   -H:NativeLinkerOption=C:\path\to\crt_shim.obj
   ```

4. **Regenerate the list when the toolchain changes.** Another GraalVM or a vendor library may call new functions; a
   missing one fails the link with LNK2019, it never brings the CRT DLL back silently.
5. **Mind the boundary.** The module now has its own copy of the CRT: its own heap, `errno`, locale, file handles and
   environment
   ([Microsoft Learn](https://learn.microsoft.com/en-us/cpp/c-runtime-library/potential-errors-passing-crt-objects-across-dll-boundaries)).
   Memory it returns must be freed by its own functions, and the application's `_putenv` after loading is not seen by
   its `getenv`. An allocator replaced through the CRT DLL (mimalloc, see
   [the article on allocators](../platform/replacing-the-process-allocator.md)) does not reach it either.

## How to test

- `dumpbin /dependents` of the module: only system DLLs (`KERNEL32.dll` and the like), no `VCRUNTIME140*.dll`, no
  `api-ms-win-crt-*.dll`. The Universal CRT is part of Windows 10 and later
  ([UCRT deployment](https://learn.microsoft.com/en-us/cpp/windows/universal-crt-deployment)), but a `/MT` module does
  not import it at all.
- Run the application on a machine or in a Windows container without the Redistributable: on a developer machine the
  installed Redistributable hides a DLL that the module loads at run time with `LoadLibrary`.
- A minimal reproduction: a static library compiled with `/MD` that calls `getenv`, `_strdup` and `free`, and a `/MT`
  DLL that calls it. Linked as is: LNK4098, LNK4217 for `free`, LNK2019 for `__imp_getenv` and `__imp__strdup`. With
  the static CRT options and the shim: exit 0, the DLL imports `KERNEL32.dll` only.
- Red check: drop the shim object from the link; it must fail with LNK2019 `__imp_*`.

## Review checklist

- [ ] `dumpbin /dependents` of the shipped module shows no `VCRUNTIME140*.dll` and no `api-ms-win-crt-*.dll`.
- [ ] The shim is generated from the libraries of the build, not kept by hand, and the build fails on LNK2019.
- [ ] Memory, `FILE *` and other CRT objects never cross the module boundary; the API frees what it allocates.
- [ ] A test runs the module on a machine or in a container without the Redistributable.

## Seen in

- **dxfeed-graal-native-sdk**: a GraalVM native-image DLL for C and C++ applications; the build profile
  `windowsStaticRuntime` generates the shim
  ([New-CrtShim.ps1](https://github.com/dxFeed/dxfeed-graal-native-sdk/blob/v3.11.0/scripts/windows-static-runtime/New-CrtShim.ps1),
  173 functions of 47 JDK libraries with GraalVM 25.4.4.1.1) and links the image with the options above
  ([pom.xml](https://github.com/dxFeed/dxfeed-graal-native-sdk/blob/v3.11.0/pom.xml#L734-L754)). The DLL imports only
  system DLLs; the build checks this and runs a `/MT` client
  ([Test-StaticRuntime.ps1](https://github.com/dxFeed/dxfeed-graal-native-sdk/blob/v3.11.0/scripts/windows-static-runtime/Test-StaticRuntime.ps1)).
- **GraalVM**: the request for executables without the Redistributable,
  [oracle/graal#14683](https://github.com/oracle/graal/issues/14683) and
  [PR #14685](https://github.com/oracle/graal/pull/14685); an older one,
  [oracle/graal#1762](https://github.com/oracle/graal/issues/1762).

## Open questions

- The hybrid CRT for a DLL (static vcruntime, Universal CRT as a DLL, as
  [PR #14685](https://github.com/oracle/graal/pull/14685) does for executables and the
  [Windows App SDK](https://github.com/microsoft/WindowsAppSDK/blob/main/docs/Coding-Guidelines/HybridCRT.md)
  describes) was not tried; it would keep one heap with JDK libraries loaded at run time.
- Windows on ARM64 was not run.
- JDK DLLs that an image loads at run time (AWT and the like) are built with `/MD` and bring the CRT DLLs back; not
  covered.
