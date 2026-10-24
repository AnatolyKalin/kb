---
title: "Process exit when a library owns runtime threads that call back into user code"
area: lifetime
tags: [c++, lifetime, exit, callbacks, threads, windows-dll, graalvm, jni, sanitizers]
symptoms:
  - "The process hangs at exit after `return` from `main()`"
  - "heap-use-after-free or a data race at exit under ASan / TSan"
  - "A crash at exit on Windows: `0xc0000409` / `0xC0000005`"
  - "A hang or a crash in `DLL_PROCESS_DETACH`"
  - "A callback runs after the library objects are destroyed"
updated: 2026-10
---

# Process exit when a library owns runtime threads that call back into user code

**English** | [Русский](native-runtime-exit-and-callbacks.ru.md)

A C/C++ library on top of a runtime with its own threads (GraalVM native image, JVM via JNI, .NET hosting, Python,
any engine with a thread pool), whose threads call user code (listeners, loggers, handlers).

Examples and links: [Seen in](#seen-in).

## Symptoms

- The process does not end after `return` from `main()` (hangs in a static destructor or an `atexit` handler).
- A crash at exit: heap-use-after-free (ASan), a data race (TSan), `0xc0000409` / `0xC0000005` on Windows.
- On Windows with a DLL: a hang or a crash in `DLL_PROCESS_DETACH`.
- It fails "sometimes", more often under load and under sanitizers.

## Causes (usually all at once)

1. **Runtime tear-down in a static destructor.** `graal_tear_down_isolate`, `DestroyJavaVM` and the like wait for all
   non-daemon runtime threads. A thread that holds an open connection never ends, so the exit hangs.
2. **Static registries are destroyed while callbacks still run.** The runtime threads live until the process ends,
   while the registries (id → object maps, managers, contexts) are ordinary statics. A callback lands in a destroyed
   object.
3. **Static destruction order.** `atexit` handlers and static destructors share one LIFO stack:
   - a static created **before** the handler is registered is destroyed **after** it runs;
   - a static created **after** (a lazy function-local static initialized later) is destroyed **before** it runs.
4. **A callback already in progress at exit.** A "we are exiting" flag stops new calls, but not the one already
   inside a listener.
5. **Windows DLL.** `atexit` inside a DLL writes to the module's table, not the process's: the handler runs at
   `DLL_PROCESS_DETACH`, **after** the executable's statics are destroyed and **after** the OS has killed the other
   threads (their counters and locks stay frozen).

## Recipe

1. **Do not tear the runtime down at exit.** The isolate/VM lives until the process ends; the OS ends its threads.
   Tear down only on an explicit call, and only if it does not wait for foreign threads.
2. **Immortal registries.** `static T &x = *new T{};` instead of `static T x;` for everything the callbacks touch.
   The leak at exit is expected (suppress it in LSan by function name).
3. **Flags in `constinit std::atomic`** (readable before dynamic initialization and after statics are destroyed):
   - `shuttingDown`: callbacks return at once;
   - `shutDown`: the library no longer enters the runtime (returns an error code or throws).
4. **A process-wide counter of callbacks in progress plus a wait with a timeout** (as the GraalVM SDK listener
   deactivation does, see [Seen in](#seen-in)):
   ```cpp
   // callback
   callbacksInProgress.fetch_add(1);            // the counter first...
   threadCallbacksInProgress++;                 // thread_local
   bool active = !shuttingDown.load();          // ...then the flag (seq_cst)
   // ... if (active) user(); ...
   threadCallbacksInProgress--; callbacksInProgress.fetch_sub(1);

   // exit handler
   shuttingDown.store(true);                    // the flag first...
   while (callbacksInProgress.load() > threadCallbacksInProgress && !timeout) sleep(1ms);  // ...then the counter
   ```
   - "Counter, then flag" in the callback and "flag, then counter" in the handler, all `seq_cst` (a Dekker-style
     handshake): either the callback sees the flag, or the handler sees the callback. `acquire/release` gives no such
     guarantee.
   - Do not wait for the calling thread's own callbacks (the `thread_local` counter): `exit()` or `shutdown()` may be
     called from a listener.
   - The timeout is mandatory: a listener may wait for a lock that the exiting thread holds.
   - Wrap it in an RAII guard (`CallbackScope`) and make it the first line of every callback.
5. **Register the handler on the library's first use** (when the runtime is created), not earlier: the user's
   statics created before that outlive the handler.
6. **Windows DLL (MSVC, `/MD`).** `_crt_atexit(onExit)` from `<corecrt_startup.h>` writes to the process-wide UCRT
   table, as `atexit` in an executable does. The handler runs in LIFO order with the executable's statics, while the
   threads are alive.
   - Pin the module: `GetModuleHandleExW(FROM_ADDRESS | PIN, ...)`, otherwise after `FreeLibrary` the table holds a
     dangling pointer.
   - Checked in the UCRT sources: `_crt_atexit` → the global `__acrt_atexit_table`, run only by `exit()`; the DLL's
     module table runs in `__scrt_dllmain_uninitialize_c` (detach).
   - A fallback handler: also `std::atexit(onDetach)` (flags only, no wait), registered **before** `_crt_atexit`. The
     global table is not run if the executable is built with `/MT` (it has its own `exit()`) or the process ends by
     `ExitProcess()`; without the fallback the flags are never set, and `thread_local` destructors call into the
     runtime at detach. In an executable both go to the same table, LIFO, so the main handler runs first.
   - MinGW and DLLs with the static CRT (`/MT`) cannot do this: the handler stays in `DLL_PROCESS_DETACH`. **Do not
     wait** there: a thread killed in the middle of a callback never decrements the counter, so every exit would wait
     for the whole timeout, under the loader lock. Detect it: the module of the address of an own variable
     (`GetModuleHandleExW(FROM_ADDRESS)`) ≠ `GetModuleHandleW(nullptr)` means a DLL.
   - The UCRT runs the exit table under `__acrt_exit_lock`, and `atexit` registration takes the same lock. A callback
     that first initializes a function-local static with a destructor during the wait blocks on the lock until the
     timeout (glibc releases its lock while a handler runs). Bounded by the timeout; note it in a comment.
7. **An explicit `shutdown()` is optional**, for a graceful close: flag → wait for callbacks → close the entities and
   wait for their threads → release the handles → `shutDown`. Serialize it with a mutex (also `*new`). Do not call it
   from a listener.

## What is left to the user

A static created **after** the library's first use is destroyed before the library's exit handler runs. If a listener
touches it, close the entities or call `shutdown()` before that. One line in the docs, no more.

## How to test

- Every scenario is a **separate process** (`main` returns; ctest catches a hang by its timeout and a crash by the
  exit code). Variants: static and shared library.
- Scenarios: an open entity without `close()`; a live connection (a local server in the test, no network); `close()`
  before exit; an explicit `shutdown()` and an API call after it; a callback after the handler; **a callback in
  progress at exit**.
- The detector is a static created before `main()` (destroyed after the library's handler):
  - "late callback": the call counter must not grow after the handler;
  - "callback in progress": the listener sets a `running` flag, sleeps 500 ms, clears the flag; `main` waits for
    `running` and returns; the detector's destructor calls `_Exit(6)` if `running == true`. Deterministic, with no
    race on whether the process managed to die.
- A red check for each mechanism separately: disable the wait and "in progress" fails; restore `std::atexit` in the
  DLL and both shared tests fail.
- Keep the connections in the tests explicitly open (`keepOpen` into an immortal vector): the wrapper's destructor
  calls `close()` itself and hides the scenario.
- POSIX: `signal(SIGPIPE, SIG_IGN)` in a test with a local server.

## Sanitizers

- **LSan**: immortal objects → a suppression by the function that creates them.
- **TSan**: runtime threads that have ended but were never joined (the tear-down used to join them) → `thread leak`.
  Suppress with `thread:<runtime module>` (matches the module name in the creation stack). An uninstrumented runtime →
  `called_from_lib:<module>`.

## Review checklist

- [ ] No runtime tear-down in static destructors or `atexit` handlers.
- [ ] Every object reachable from callbacks is immortal.
- [ ] Every callback starts with the flag check through the counter (RAII), with no check-then-use window.
- [ ] The exit handler waits for other threads' callbacks with a timeout, not for its own.
- [ ] DLL: the handler is in the process table, the module is pinned, a fallback handler at detach; no wait at
      detach; the MinGW / `/MT` limits are documented (in the release notes too, not only in the header).
- [ ] An RAII class in a public header is exported like its neighbours (a nested class does not inherit dllexport).
- [ ] The public API after shutdown: an exception or a clear failure, no call into the runtime; documented.
- [ ] Exit tests in separate processes, static + shared, with a red check.
- [ ] LSan/TSan suppressions carry a comment on why.

## Seen in

- **dxFeed Graal C++ API**: a hang at exit with a live connection, use-after-free of registries in callbacks; fixed
  as described here: [dxFeed/dxfeed-graal-cxx-api#158](https://github.com/dxFeed/dxfeed-graal-cxx-api/pull/158).
  The same "wait for calls in progress, except the own thread's" technique is used for listeners in
  [dxfeed-graal-native-sdk](https://github.com/dxFeed/dxfeed-graal-native-sdk) (`dxfg_NativeListener_deactivate`).
- **JNI**: `DestroyJavaVM` waits for all non-daemon threads before shutting the VM down; the same hang mechanism for
  any embedded JVM/GraalVM. [JNI Invocation API](https://docs.oracle.com/en/java/javase/21/docs/specs/jni/invocation.html).
- **CPython**: a thread that reacquired the GIL during interpreter finalization used to call `pthread_exit()`, which
  unwound C++ frames without cleanup: memory corruption, crashes, deadlocks. Since 3.14 such threads hang forever
  instead (at the cost of a possible deadlock if the thread holds a lock that finalization needs).
  [python/cpython#87135](https://github.com/python/cpython/issues/87135),
  [python/cpython#105805](https://github.com/python/cpython/pull/105805); daemon threads at subinterpreter
  finalization: [python/cpython#128639](https://github.com/python/cpython/issues/128639).
- **gRPC C++**: a crash after `return` from `main()`: gRPC core stayed initialized and its threads were alive while
  the C/C++ runtime destroyed the statics. [grpc/grpc#31045](https://github.com/grpc/grpc/issues/31045) (fixed in
  1.51.0, according to the reporter).
- **OpenSSL**: the `atexit` handler crashes if libcrypto/libssl are already unloaded; `OPENSSL_INIT_NO_ATEXIT`
  disables it, and the application calls `OPENSSL_cleanup()` itself.
  [OPENSSL_cleanup(3)](https://manpages.opensuse.org/Leap-15.6/openssl-1_1-doc/OPENSSL_cleanup.3ssl.en.html).
- **abseil / Chromium**: immortal statics as an idiom: `absl::NoDestructor` ("survives during program exit"),
  `base::NoDestructor` in Chromium.
  [no_destructor.h](https://github.com/abseil/abseil-cpp/blob/master/absl/base/no_destructor.h).
- **Google C++ Style Guide**: objects with static storage duration are forbidden unless they are trivially
  destructible. [Static and Global Variables](https://google.github.io/styleguide/cppguide.html#Static_and_Global_Variables).
- **Windows**: during process termination, entering an orphaned critical section kills the process; stop worker
  threads before `ExitProcess` and do nothing risky in `DllMain`.
  [Raymond Chen, "During process termination, the gates are now electrified"](https://devblogs.microsoft.com/oldnewthing/20100122-00/?p=15193).

## Platform sources

- `_crt_atexit` modifies the global exit table:
  [learn.microsoft.com: _crt_atexit](https://learn.microsoft.com/en-us/windows/win32/memory/crtatexit).
- `atexit` in a DLL runs after `DLL_PROCESS_DETACH`:
  [learn.microsoft.com: atexit](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/atexit?view=msvc-170).
- The UCRT runs its table under the exit lock (`onexit.cpp`, `exit.cpp` in the UCRT sources of the Windows SDK); the
  same is visible in the [ReactOS](https://doxygen.reactos.org/d2/d7c/onexit_8cpp_source.html) reimplementation.
- glibc releases `__exit_funcs_lock` while it calls each handler:
  [stdlib/exit.c](https://sourceware.org/git/?p=glibc.git;a=blob;f=stdlib/exit.c).

## Open questions

- Similar cases not checked against a primary source: Swift sourcekitd (background threads running during static
  destructors in `exit()`, SR-12668); a "pure virtual call" crash from a gRPC thread at exit in an Unreal plugin (the
  vendor could not reproduce it).
- Node-API `ThreadSafeFunction`: stop using it after `napi_closing`, join the threads in the finalizer; how it relates
  to exit hangs is not checked.
