---
title: "Статическая библиотека линкуется только с одним CRT: LNK2038, LNK4098, LNK2005 в приложении"
area: build
tags: [windows, msvc, crt, linker, static-library, graalvm, native-image]
symptoms:
  - "`LNK2038: mismatch detected for 'RuntimeLibrary'`"
  - "`LNK2038: mismatch detected for '_ITERATOR_DEBUG_LEVEL'`"
  - "`LNK4098: defaultlib 'LIBCMT' conflicts with use of other libs`"
  - "`LNK2005: deflate already defined` при линковке сторонней статической библиотеки"
  - "`LNK4099: PDB 'vc140.pdb' was not found`"
  - "Исполняемый файл приложения экспортирует функции статической библиотеки"
updated: 2026-10
---

# Статическая библиотека линкуется только с одним CRT: LNK2038, LNK4098, LNK2005 в приложении

[English](static-library-for-any-msvc-runtime.md) | **Русский**

Статическая библиотека для MSVC (`.lib`) собрана с одним вариантом среды выполнения C, а её пользователи собирают с
`/MT`, `/MTd`, `/MD` или `/MDd`. С другим вариантом линковка падает или затягивает два CRT сразу. Сторонний код внутри
библиотеки (zlib, вспомогательные функции JNI) конфликтует с собственными копиями приложения, исполняемый файл
экспортирует API библиотеки, а `/DEBUG` предупреждает о PDB, которую никто не поставлял. Типично для готовых
объектов: SDK поставщика, статическая библиотека GraalVM native-image.

Проверено с MSVC 19.42 (VS 2022) на Windows 11; см. [«Как тестировать»](#как-тестировать).

## Симптомы

```text
error LNK2038: mismatch detected for 'RuntimeLibrary': value 'MT_StaticRelease' doesn't match value
    'MD_DynamicRelease' in app.obj
warning LNK4098: defaultlib 'LIBCMT' conflicts with use of other libs; use /NODEFAULTLIB:library
error LNK2005: deflate already defined in app.obj
warning LNK4099: PDB '' was not found with 'mylib.lib(mylib.obj)' or at ''; linking object as if no debug info
```

- Несовпадение `_ITERATOR_DEBUG_LEVEL` между release-библиотекой и отладочным приложением (`/MTd`, `/MDd`).
- `dumpbin /exports app.exe` перечисляет функции библиотеки, а линковка кладёт рядом с исполняемым файлом `app.lib` и
  `app.exp`.

## Причины

1. **Каждый объект помнит свой CRT.** `/MT`, `/MD` и их отладочные варианты записывают в объект имя своей библиотеки
   CRT директивой `/DEFAULTLIB:LIBCMT`, `MSVCRT` и т. д.
   ([/MD, /MT](https://learn.microsoft.com/en-us/cpp/build/reference/md-mt-ld-use-run-time-library)); два разных имени
   в одной линковке дают
   [LNK4098](https://learn.microsoft.com/en-us/cpp/error-messages/tool-errors/linker-tools-warning-lnk4098). Заголовки
   CRT и C++ добавляют ещё и записи `/FAILIFMISMATCH` через
   [`#pragma detect_mismatch`](https://learn.microsoft.com/en-us/cpp/preprocessor/detect-mismatch): `RuntimeLibrary`,
   `_ITERATOR_DEBUG_LEVEL`, `_MSC_VER`; другое значение роняет линковку с
   [LNK2038](https://learn.microsoft.com/en-us/cpp/error-messages/tool-errors/linker-tools-error-lnk2038).
2. **Объекты, скомпилированные с `/MD`, вызывают CRT через указатели `__imp_`.** Они линкуются только с приложением на
   `/MD`; приложению на `/MT` недостаёт указателей (LNK2019 `__imp_<name>`), см.
   [статью о DLL native-image](native-image-dll-without-vc-redistributable.ru.md). Объекты, скомпилированные с `/MT`,
   вызывают функции напрямую, и такой вызов линкуется с любым CRT: при `/MD` он идёт через переходник импорта.
3. **Приложению виден каждый внешний символ библиотеки.** Внутренняя копия zlib или вспомогательных функций JNI
   конфликтует с копией приложения
   ([LNK2005](https://learn.microsoft.com/en-us/cpp/error-messages/tool-errors/linker-tools-error-lnk2005)).
4. **`__declspec(dllexport)` переживает статическую библиотеку.** В объекте остаётся директива `/EXPORT:`, и
   исполняемый файл, в который попал объект, экспортирует функцию.
5. **`/Zi` держит отладочную информацию в PDB сборки библиотеки.** Без этой PDB линковка приложения с `/DEBUG` даёт
   [LNK4099](https://learn.microsoft.com/en-us/cpp/error-messages/tool-errors/linker-tools-warning-lnk4099) и остаётся
   без отладочной информации библиотеки. `/Z7` кладёт её в сами объекты
   ([/Z7, /Zi](https://learn.microsoft.com/en-us/cpp/build/reference/z7-zi-zi-debug-information-format)).
6. **Линковщик не должен быть старше компилятора любого из входов.** Microsoft гарантирует двоичную совместимость,
   только если линковщик той же версии или новее, чем самый новый набор инструментов, собравший объект или библиотеку
   ([C++ binary compatibility](https://learn.microsoft.com/en-us/cpp/porting/binary-compat-2015-2017)).

## Рецепт

**Библиотека на C, которую вы компилируете сами: соберите её нейтральной.**

1. Компилируйте с `/Zl` (без имён библиотек по умолчанию в объектах,
   [/Zl](https://learn.microsoft.com/en-us/cpp/build/reference/zl-omit-default-library-name)) и `/Z7`, без
   `dllexport`, а внутренние функции делайте `static` или прячьте под префикс (как zlib с `Z_PREFIX`):

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

2. `dumpbin /directives` не должен ничего напечатать: ни `/DEFAULTLIB`, ни `/FAILIFMISMATCH`, ни `/EXPORT`. Такая
   библиотека линкуется с `/MT`, `/MTd`, `/MD` и `/MDd` и пользуется CRT приложения: одна куча, один `errno`.

**C++ со стандартной библиотекой так нейтральным не сделать.** `/Zl` убирает имена CRT, но заголовки C++ всё равно
записывают `RuntimeLibrary`, `_ITERATOR_DEBUG_LEVEL` и `/DEFAULTLIB:libcpmt`: раскладка типов `std::` у вариантов
разная. Поставляйте по библиотеке на вариант (release и debug, статический и динамический) или уберите C++ из
библиотеки и выставьте наружу C API.

**Готовые объекты, которые не перекомпилировать: перепишите библиотеку.** Штатного инструмента MSVC для этого нет;
нужен небольшой переписчик COFF, который проходит по каждому члену `.lib`:

1. Уберите директивы `/EXPORT:` и `/DEFAULTLIB:` библиотек CRT и C++ (`MSVCRT`, `LIBCMT`, `msvcprt`, `libcpmt` и их
   отладочные варианты).
2. Уберите `/FAILIFMISMATCH:RuntimeLibrary` и `_ITERATOR_DEBUG_LEVEL`. Это безопасно только для объектов на C;
   проверьте, что ни один объект на C++ не передаёт типы стандартной библиотеки через границу библиотеки. Записи вроде
   `_MSC_VER=1900` и `_CRT_STDIO_ISO_WIDE_SPECIFIERS=0` одинаковы у всех вариантов и могут остаться.
3. Добавьте префикс к каждому определённому внешнему символу, кроме публичного API. Оставьте имена, которые должны
   совпадать снаружи библиотеки: цели `/alternatename`, общие COMDAT-константы компилятора (`__real@`, `__xmm@`,
   строковые литералы `??_C@`) и встраиваемые функции заголовков CRT (`__local_stdio_*`).
4. Объектам, скомпилированным с `/MD`, нужны ещё указатели `__imp_` на вызываемые функции CRT: добавьте объект-прокладку
   (см. [статью о DLL native-image](native-image-dll-without-vc-redistributable.ru.md)) и снабдите её указатели тем же
   префиксом. Они остаются внутри библиотеки и указывают на обычные функции, поэтому линковщик привязывает их к тому
   CRT, с которым линкуется приложение.
5. Выбросьте отладочную информацию, ссылающуюся на непоставляемую PDB, или поставляйте PDB.
6. Укажите минимальный набор инструментов: тот, что у самого нового компилятора объектов.

## Как тестировать

- Матрица: слинкуйте тестовое приложение с `/MT`, `/MTd`, `/MD`, `/MDd`, каждое с `/DEBUG` и без. Приложение
  определяет те же имена, что и внутренности библиотеки (`deflate`, `inflate`, вспомогательную функцию JNI), и
  содержит файл на C++ с `std::vector`.
- Для каждой линковки: код выхода 0 и ни одного предупреждения; `dumpbin /exports app.exe` пуст; при `/MT` и `/MTd`
  `dumpbin /dependents` не показывает ни `VCRUNTIME140*.dll`, ни `ucrtbase*.dll`, ни `api-ms-win-crt-*.dll`; программа
  запускается.
- Красные проверки с библиотекой в исходном виде: `/MT` и собственный `deflate` приложения дают LNK2005; `/MD` даёт
  LNK2038 по `RuntimeLibrary` и LNK4098; `/DEBUG` даёт LNK4099; исполняемый файл экспортирует API. Без
  объекта-прокладки линковка падает с LNK2019 для указателей `__imp_` с префиксом.

## Чек-лист для ревью

- [ ] `dumpbin /directives` поставляемой библиотеки не показывает `/DEFAULTLIB` CRT, записей `RuntimeLibrary` и
      `_ITERATOR_DEBUG_LEVEL` и `/EXPORT`.
- [ ] Виден только публичный API: никаких внутренних имён без префикса (`dumpbin /symbols`, определённые `External`).
- [ ] Типы стандартной библиотеки C++ не пересекают границу библиотеки.
- [ ] Минимальный набор инструментов MSVC задокументирован.
- [ ] CI до публикации линкует и запускает матрицу из четырёх вариантов с `/DEBUG` и без.

## Где встречалось

- **dxfeed-graal-native-sdk**: статическая библиотека GraalVM native-image, переупакованная под любой CRT; с 3.10.0 в
  архивах `-static-lib`. Упаковщик собирает объект образа и статические библиотеки JDK
  ([New-StaticLibrary.ps1](https://github.com/dxFeed/dxfeed-graal-native-sdk/blob/v3.11.0/scripts/windows-static-runtime/New-StaticLibrary.ps1)),
  а переписчик COFF
  ([StaticLibrary.cs](https://github.com/dxFeed/dxfeed-graal-native-sdk/blob/v3.11.0/scripts/windows-static-runtime/StaticLibrary.cs))
  переименовывает 2 677 из 5 183 публичных символов, убирает 3 116 директив `/EXPORT` и 146 директив CRT и выбрасывает
  отладочную информацию 15 объектов, ссылающуюся на `vc140.pdb`. Сборка проверяет матрицу из четырёх вариантов
  ([Test-StaticLibrary.ps1](https://github.com/dxFeed/dxfeed-graal-native-sdk/blob/v3.11.0/scripts/windows-static-runtime/Test-StaticLibrary.ps1)).
  Библиотеки GraalVM внутри собраны MSVC 19.43, поэтому SDK требует Visual Studio 2022 17.13 или новее.
- **zlib** и **ICU** переименовывают свои символы для встраивания: `Z_PREFIX` в
  [zconf.h](https://github.com/madler/zlib/blob/v1.3.1/zconf.h), `urename.h` в
  [ICU](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/common/unicode/urename.h).

## Открытые вопросы

- Переписанная библиотека с кодом стандартной библиотеки C++ внутри слинковалась и заработала со всеми четырьмя
  вариантами в маленьком тесте, но затягивает статическую release-библиотеку C++ (`libcpmt`) в приложения на `/MD` и
  в отладочные; не рекомендуется, в масштабе не проверялось.
- Справится ли `llvm-objcopy` (`--prefix-symbols`, `--redefine-syms`) с переименованием в архивах COFF с
  `/alternatename` и COMDAT-символами: не пробовалось.
- Объекты, скомпилированные с `/GL` (генерация кода при линковке), — не COFF, и переписать их нельзя; не пробовалось.
- Более старый линковщик (14.42) слинковал здесь объекты 19.43 библиотеки GraalVM без ошибок; это за пределами
  документированной гарантии.
- Windows на ARM64 не проверялась.
