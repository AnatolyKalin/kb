---
title: "CMake молча отбрасывает функциональный макрос из target_compile_definitions"
area: build
tags: [cmake, gcc, clang, msvc, macro, deprecation, werror]
symptoms:
  - "`target_compile_definitions(tgt PRIVATE \"MACRO(arg)=\")` не действует: определения нет в командной строке компилятора"
  - "Сборка падает с `-Werror` на предупреждениях об устаревании, которые должен был убрать заранее заданный пустой макрос"
  - "`warning: -Wdeprecated-declarations` или `C4996` в цели, где задан макрос устаревания"
updated: 2026-11
---

# CMake молча отбрасывает функциональный макрос из target_compile_definitions

[English](cmake-drops-function-like-macro-definitions.md) | **Русский**

Определение вида `NAME(arg)=`, переданное в `target_compile_definitions` или `COMPILE_DEFINITIONS`, не доходит до
компилятора, а сборка не объясняет причину. Больнее всего, когда макрос должен что-то отключить: обёртка на C++ над
C SDK, чьи заголовки помечают функции макросом устаревания, при сборке с `-Werror`.

Проверено с CMake 3.2x, GCC и Clang на Linux, с предкомпилированным заголовком и без него; MSVC `cl` на Windows, по
документации. См. [«Как тестировать»](#как-тестировать).

## Симптомы

- В командной строке компиляции (`compile_commands.json`, `cmake --build . -v`) нет `-DNAME(arg)=` вовсе.
- Предупреждения об устаревании остаются, а с `-Werror` сборка падает. Без определения срабатывает собственный
  `#define` заголовка, как будто строки в `CMakeLists.txt` нет.
- О причине намекает лишь предупреждение на этапе конфигурации, которое легко потерять в длинном журнале.

## Причины

1. **CMake не поддерживает функциональные определения в `COMPILE_DEFINITIONS`.** В документации свойства сказано:
   «Function-style definitions are not supported»
   ([COMPILE_DEFINITIONS](https://cmake.org/cmake/help/latest/prop_tgt/COMPILE_DEFINITIONS.html)). Запись пропадает из
   командной строки, `target_compile_definitions` не исключение.
2. **Заголовок использует `#ifndef`.** Типичный заголовок SDK:
   `#ifndef MYSDK_DEPRECATED` / `#define MYSDK_DEPRECATED(msg) __attribute__((deprecated(msg)))` (или
   `__declspec(deprecated(msg))` в MSVC). Пустое предопределение его остановило бы, но не приходит.
3. **MSVC `cl` вообще не умеет задавать функциональный макрос через `/D`**
   ([/D](https://learn.microsoft.com/en-us/cpp/build/reference/d-preprocessor-definitions)): параметр принимает
   `name[=value]`, списка параметров макроса там нет.

## Рецепт

1. **GCC, Clang: передать сырым параметром компилятора.** Параметры не фильтруются так, как определения:

   ```cmake
   target_compile_options(tgt PRIVATE "-DMYSDK_DEPRECATED(message)=")
   ```

2. **MSVC: отключить предупреждение, а не макрос.** C4996 это предупреждение об устаревании:

   ```cmake
   target_compile_options(tgt PRIVATE /wd4996)
   ```

   Побочный эффект: скрываются все C4996 этой цели, в том числе не связанные с SDK (`strcpy` и подобные). Держите
   параметр на единственной цели, которая включает заголовки SDK.

3. **Ветку выбирать по компилятору, а не по платформе.** `MSVC` и `WIN32` истинны и для `clang-cl`, а `/wd4996` не
   заглушает `-Wdeprecated-declarations` Clang:

   ```cmake
   if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
       target_compile_options(tgt PRIVATE /wd4996)
   else() # GNU, Clang, AppleClang
       target_compile_options(tgt PRIVATE "-DMYSDK_DEPRECATED(message)=")
   endif()
   ```

   Для `clang-cl` (ID `Clang`, вариант оболочки `MSVC`) форму проверьте отдельно: см.
   [«Открытые вопросы»](#открытые-вопросы).

## Как тестировать

- Сконфигурировать с `-DCMAKE_EXPORT_COMPILE_COMMANDS=ON` и найти определение в `compile_commands.json`, либо
  запустить `cmake --build . -v` и прочитать строку компиляции.
- Красная проверка: маленький проект с заголовком такой формы, устаревшей функцией, вызванной из исходника, и
  `-Werror`. С `target_compile_definitions` сборка падает; с `target_compile_options` проходит; уберите параметр, и
  снова падает. Прогнать с предкомпилированным заголовком и без него.

## Чек-лист ревью

- [ ] Ни одна запись `target_compile_definitions` или `COMPILE_DEFINITIONS` не содержит `(`; поиск по
      `"[A-Za-z_]+\(`.
- [ ] Нужное определение видно в `compile_commands.json`, а не только в `CMakeLists.txt`.
- [ ] Ветка по компилятору использует `CMAKE_CXX_COMPILER_ID`, а не `MSVC` или `WIN32`.
- [ ] `/wd4996` задан на единственной цели, которой он нужен.

## Где встречалось

- **Обёртка на C++ над C SDK**: SDK помечает свои C-функции макросом устаревания, обёртка собирается с `-Werror` и
  вызывает их намеренно. Предопределение макроса через `target_compile_definitions` ничего не изменило; сырой параметр
  `-D` исправил GCC и Clang, `/wd4996` исправил MSVC.

## Открытые вопросы

- `clang-cl`: доходит ли `/D"NAME(arg)="` или `/clang:-DNAME(arg)=` до оболочки Clang целым и в каком виде
  кавычек его передаёт CMake. Не запускалось; проверьте отдельно.
- Другие версии CMake: поведение описано в документации как ограничение, но версии, кроме 3.2x, не запускались.
