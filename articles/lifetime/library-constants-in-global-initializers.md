---
title: "Library constants are empty or crash in global initializers and destructors of user code"
area: lifetime
tags: [c++, static-initialization, static-destruction, constinit, constexpr, static-library, msvc, sanitizers]
symptoms:
  - "A library constant is empty or zero in the initializer of a global variable"
  - "A crash before `main()` when a global variable calls a library function"
  - "`pure virtual function call` in the destructor of a global variable at exit"
  - "It fails with the static library and works with the shared one"
  - "ASan: `initialization-order-fiasco`"
updated: 2026-10
---

# Library constants are empty or crash in global initializers and destructors of user code

**English** | [Русский](library-constants-in-global-initializers.ru.md)

A C++ library with public constants of class type (`static const CandleType MINUTE;` defined in a `.cpp`) or maps of
constants, and user code that has global variables: singletons, registries, configuration, test fixtures.

Examples and links: [Seen in](#seen-in).

## Symptoms

- In the initializer of a global variable, `Lib::CONSTANT.getName()` returns an empty string, `parse("h")` finds
  nothing or crashes; the same call in `main()` works.
- It fails with the static library and works with the shared one, or changes with the link order.
- At exit, the destructor of a global variable that uses a constant crashes: `pure virtual function call` (MSVC
  R6025, libstdc++ `pure virtual method called`) or a read of freed memory.
- ASan with `check_initialization_order=1` reports `initialization-order-fiasco`.

## Causes

1. **The order of dynamic initialization across translation units is unspecified.** A constant whose constructor is
   not `constexpr` (a `std::string` member, a `std::function`, a map) is initialized dynamically, and the translation
   unit of the user can go first. With a static library the objects of the archive are just more translation units of
   the executable. A shared library is usually initialized by the loader before the code that depends on it, so the
   problem hides there.
2. **Before its dynamic initialization the object is all zeros.** For `std::string` that is not even a valid empty
   string: reading it can crash, not only return `""`.
3. **Destruction goes in the reverse order of construction.** A global of the user constructed before the constant
   is destroyed after it. During destruction, and in practice after it, the virtual table of the object is that of
   the base class, so a virtual call ends in a pure virtual call. A constant with a non-trivial destructor
   (`std::string`, `std::shared_ptr`, a virtual destructor) is destroyed at exit even when its initialization is
   constant.
4. **A constant copied from another constant is dynamic.** `DEFAULT = LAST` reads a variable, and a `constinit` (not
   `constexpr`) variable is not usable in constant expressions. GCC 13 accepted such a read, Clang 18 and MSVC 19.42
   rejected it: a build that is green only on GCC proves nothing.

## Recipe

1. **Make the constants constant-initialized, and let the compiler check it.** Literal types (`std::string_view`
   on a literal instead of `std::string`), `constexpr` constructors, and `constinit` on the definition: the build
   fails if the initialization is not constant. The declarations in the headers and the names can stay as they are.

   ```cpp
   // header
   class CandleType {
       std::string_view name_;
   public:
       constexpr explicit CandleType(std::string_view name) noexcept : name_(name) {}
       static const CandleType MINUTE;
   };

   // .cpp
   constinit const CandleType CandleType::MINUTE{"m"};
   static_assert(std::is_trivially_destructible_v<CandleType>);
   ```

2. **Make them trivially destructible**: no virtual destructor, no `std::string` or `std::shared_ptr` members. Then
   nothing runs for them at exit, and a destructor of user code can still use them. A base class that must stay
   polymorphic gets a protected non-virtual destructor, and the derived classes are `final`.
3. **Build derived constants from the same literals** through a `constexpr` factory, not by copying another constant.
4. **Registries of constants: `constinit std::array` plus `std::span`** instead of `std::unordered_map`; a linear
   search over a few dozen entries is fast enough.
5. **What cannot be constant** (heap, handles of a runtime): construct it on first use in a function-local static,
   and if it is used at exit, never destroy it (`static T &x = *new T(...)`, `absl::NoDestructor`). A lazy handle: a
   function pointer plus `std::once_flag` instead of `std::function`.
6. **MSVC and DLL exports**: an explicit specialization of a static data member of a class template is a definition,
   so it cannot be `__declspec(dllimport)` (C2491). Declare such constants in each derived class instead of in the
   template.

## What it costs

- Getters that returned `const std::string &` return `std::string` or `std::string_view`: the ABI changes, and a
  `const std::string &` member that stored the result dangles.
- Keys that become `static constexpr char[]` compare by pointer with a `const char *`, and `KEY + "x"` no longer
  compiles.
- Maps of constants change their type: code that names `std::unordered_map<...>` breaks.

## How to test

- A test executable whose global initializers read every constant and call the functions that use them (`parse`,
  `valueOf`), linked with the static library. Print the name before reading, so a crash names the constant, and
  compare with the values read in `main()`.
- The same for destructors: a global whose destructor reads the constants.
- ASan on Linux: `ASAN_OPTIONS=check_initialization_order=1:strict_init_order=1`.
- Build with Clang and MSVC, not only with GCC (cause 4).
- The red check: return one constant to `std::string` or drop `constinit`; the test or the build fails.

## Review checklist

- [ ] A new public constant is a literal type with a `constexpr` constructor and a `constinit` definition.
- [ ] `static_assert(std::is_trivially_destructible_v<T>)` for the types of the constants.
- [ ] No constant is copied from another constant.
- [ ] No `std::string`, `std::function`, map or `std::shared_ptr` at namespace scope on the path of `parse`/`valueOf`.
- [ ] The static-initialization test covers the new constant.

## Seen in

- **dxFeed Graal C++ API**: `CandleType::parse("h")` in the initializer of a global variable crashed with the static
  library; a virtual call on a candle attribute constant in a global destructor could call a pure virtual function.
  The constants became `constinit` literal types, the maps `ConstantMap` over arrays, the attributes trivially
  destructible; a static-initialization test reads all of them from global initializers:
  [#143](https://github.com/dxFeed/dxfeed-graal-cxx-api/pull/143),
  [#144](https://github.com/dxFeed/dxfeed-graal-cxx-api/pull/144).
- **btop**: a global in one source file is initialized from a global of another one; the program crashes before
  `main()` in about half of the builds, depending on the compiler and the linker (Clang, mold):
  [aristocratos/btop#1748](https://github.com/aristocratos/btop/issues/1748).
- **GCC**: with `-flto`, an `extern const std::string` from another translation unit was initialized after a static
  class member that read it. The report was closed as invalid: the order across translation units is unspecified, so
  a compiler option may change it: [GCC bug 105876](https://gcc.gnu.org/bugzilla/show_bug.cgi?id=105876).

## Sources

- [Static initialization order fiasco](https://en.cppreference.com/w/cpp/language/siof),
  [initialization](https://en.cppreference.com/w/cpp/language/initialization),
  [`constinit`](https://en.cppreference.com/w/cpp/language/constinit) (cppreference);
  [P1143, `constinit`](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2019/p1143r2.html).
- Usable in constant expressions:
  [[expr.const]](https://eel.is/c++draft/expr.const#def:usable_in_constant_expressions).
- [isocpp FAQ: the static initialization order fiasco and construct on first use](https://isocpp.org/wiki/faq/ctors#static-init-order).
- Guidelines: [Abseil Tip of the Week #140, Constants: Safe Idioms](https://abseil.io/tips/140);
  [Google C++ Style Guide, Static and Global Variables](https://google.github.io/styleguide/cppguide.html#Static_and_Global_Variables);
  [LLVM, Do not use Static Constructors](https://llvm.org/docs/CodingStandards.html#do-not-use-static-constructors);
  [Chromium, Static initializers](https://chromium.googlesource.com/chromium/src/+/main/docs/static_initializers.md).
- [AddressSanitizer: InitializationOrderFiasco](https://github.com/google/sanitizers/wiki/AddressSanitizerInitializationOrderFiasco)
  (`check_initialization_order`, `strict_init_order`).

## Open questions

- Whether GCC accepting a read of a `constinit` variable in a constant expression is a known bug: no report
  found.

- Whether a shared library is always initialized before its dependents on macOS with two-level namespaces and lazy
  binding: only Linux and Windows were tested.
