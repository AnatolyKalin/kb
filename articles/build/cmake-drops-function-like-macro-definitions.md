---
title: "CMake silently drops a function-like macro from target_compile_definitions"
area: build
tags: [cmake, gcc, clang, msvc, macro, deprecation, werror]
symptoms:
  - "`target_compile_definitions(tgt PRIVATE \"MACRO(arg)=\")` has no effect: the definition is not on the compiler command line"
  - "`-Werror` fails the build on deprecation warnings that a predefined empty macro should remove"
  - "`warning: -Wdeprecated-declarations` or `C4996` in a target that predefines the deprecation macro"
updated: 2026-11
---

# CMake silently drops a function-like macro from target_compile_definitions

**English** | [Русский](cmake-drops-function-like-macro-definitions.ru.md)

A definition such as `NAME(arg)=` given to `target_compile_definitions` or `COMPILE_DEFINITIONS` never reaches the
compiler, and the build does not say why. It hurts most when the macro is meant to switch something off: a C++ wrapper
over a C SDK whose headers mark functions with a deprecation macro, built with `-Werror`.

Verified with CMake 3.2x, GCC and Clang on Linux, with and without a precompiled header; MSVC `cl` on Windows by its
documentation. See [How to test](#how-to-test).

## Symptoms

- The compile command line (`compile_commands.json`, `cmake --build . -v`) has no `-DNAME(arg)=` at all.
- The deprecation warnings stay, and with `-Werror` the build fails. Without the definition the header's own
  `#define` wins, as if the line in `CMakeLists.txt` were absent.
- Only a configure-time warning hints at the cause, and it is easy to miss in a long log.

## Causes

1. **CMake does not support function-style definitions in `COMPILE_DEFINITIONS`.** The property documentation says:
   "Function-style definitions are not supported"
   ([COMPILE_DEFINITIONS](https://cmake.org/cmake/help/latest/prop_tgt/COMPILE_DEFINITIONS.html)). The entry is
   dropped from the command line, `target_compile_definitions` included.
2. **The header uses `#ifndef`.** A typical SDK header is
   `#ifndef MYSDK_DEPRECATED` / `#define MYSDK_DEPRECATED(msg) __attribute__((deprecated(msg)))` (or
   `__declspec(deprecated(msg))` on MSVC). An empty predefinition would stop it, but it never arrives.
3. **MSVC `cl` cannot define a function-like macro with `/D` at all**
   ([/D](https://learn.microsoft.com/en-us/cpp/build/reference/d-preprocessor-definitions)): the option takes
   `name[=value]`, with no parameter list.

## Recipe

1. **GCC, Clang: pass it as a raw compiler option.** Options are not filtered the way definitions are:

   ```cmake
   target_compile_options(tgt PRIVATE "-DMYSDK_DEPRECATED(message)=")
   ```

2. **MSVC: disable the warning instead of the macro.** C4996 is the deprecation warning:

   ```cmake
   target_compile_options(tgt PRIVATE /wd4996)
   ```

   Side effect: every C4996 in that target is hidden, also the ones unrelated to the SDK (`strcpy` and the like). Keep
   the option on the one target that includes the SDK headers.

3. **Choose the branch by the compiler, not by the platform.** `MSVC` and `WIN32` are true for `clang-cl` too, and
   `/wd4996` does not silence Clang's `-Wdeprecated-declarations`:

   ```cmake
   if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
       target_compile_options(tgt PRIVATE /wd4996)
   else() # GNU, Clang, AppleClang
       target_compile_options(tgt PRIVATE "-DMYSDK_DEPRECATED(message)=")
   endif()
   ```

   For `clang-cl` (ID `Clang`, frontend variant `MSVC`) check the form separately: see
   [Open questions](#open-questions).

## How to test

- Configure with `-DCMAKE_EXPORT_COMPILE_COMMANDS=ON` and look for the definition in `compile_commands.json`, or run
  `cmake --build . -v` and read the compile line.
- Red check: a small project with a header of the shape above, a deprecated function called from a source file and
  `-Werror`. With `target_compile_definitions` the build fails; with `target_compile_options` it passes; remove the
  option and it fails again. Run it with and without a precompiled header.

## Review checklist

- [ ] No `target_compile_definitions` or `COMPILE_DEFINITIONS` entry contains `(`; grep for `"[A-Za-z_]+\(`.
- [ ] A definition that must exist is seen in `compile_commands.json`, not only in `CMakeLists.txt`.
- [ ] The compiler branch uses `CMAKE_CXX_COMPILER_ID`, not `MSVC` or `WIN32`.
- [ ] `/wd4996` is set on the one target that needs it.

## Seen in

- **A C++ wrapper over a C SDK**: the SDK marks its C functions with a deprecation macro, the wrapper is built with
  `-Werror` and calls them on purpose. Predefining the macro through `target_compile_definitions` changed nothing; the
  raw `-D` option fixed GCC and Clang, `/wd4996` MSVC.

## Open questions

- `clang-cl`: whether `/D"NAME(arg)="` or `/clang:-DNAME(arg)=` reaches the Clang frontend intact and in what quoting
  CMake passes it. Not run; check it separately.
- Other CMake versions: the behaviour is documented as a limitation, but versions other than 3.2x were not run.
