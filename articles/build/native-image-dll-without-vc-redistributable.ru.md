---
title: "DLL, собранной GraalVM native-image, по-прежнему нужен Visual C++ Redistributable"
area: build
tags: [graalvm, native-image, windows, windows-dll, msvc, crt, linker]
symptoms:
  - "`VCRUNTIME140.dll was not found` на машине без Visual C++ Redistributable"
  - "Код выхода `0xC0000135`, когда приложение загружает библиотеку"
  - "`dumpbin /dependents` показывает `VCRUNTIME140.dll` и `api-ms-win-crt-*.dll`"
  - "`LNK4098: defaultlib 'MSVCRT' conflicts with use of other libs`"
  - "`LNK2019: unresolved external symbol __imp_getenv`"
updated: 2026-10
---

# DLL, собранной GraalVM native-image, по-прежнему нужен Visual C++ Redistributable

[English](native-image-dll-without-vc-redistributable.md) | **Русский**

Библиотека или исполняемый файл, собранные GraalVM native-image под Windows, зависят от DLL среды выполнения C, и на
целевой машине нужен Visual C++ Redistributable. Перевести их на статический CRT (`/MT`) не удаётся: линковка падает.
То же происходит с любым модулем, в который линкуются статические библиотеки, скомпилированные с `/MD`, например
`.lib` стороннего поставщика.

Проверено с GraalVM CE 25.4.4.1.1 и MSVC 19.42 (VS 2022) на Windows 11; см. [«Как тестировать»](#как-тестировать).

## Симптомы

- На чистой машине: `The code execution cannot proceed because VCRUNTIME140.dll was not found` или код выхода
  `0xC0000135` (не найдена DLL), когда приложение загружает библиотеку.
- `dumpbin /dependents` перечисляет `VCRUNTIME140.dll` (и `VCRUNTIME140_1.dll`, если есть исключения C++) и
  `api-ms-win-crt-*.dll`.
- Попытка слинковать со статическим CRT:

  ```text
  LINK : warning LNK4098: defaultlib 'MSVCRT' conflicts with use of other libs; use /NODEFAULTLIB:library
  LINK : warning LNK4217: symbol 'free' defined in 'libucrt.lib(free.obj)' is imported by 'vendor.lib(vendor.obj)'
  vendor.lib(vendor.obj) : error LNK2019: unresolved external symbol __imp_getenv referenced in function ...
  ```

## Причины

1. **native-image линкует с `/MD`.** `WindowsCCLinkerInvocation` передаёт `/MD` для исполняемых файлов и `/MD /LD`
   для разделяемых библиотек; `/MT` закомментирован, причина записана в коде: «Must use /MD in order to link with JDK
   native libraries built that way»
   ([CCLinkerInvocation.java](https://github.com/oracle/graal/blob/092eca6772a74d4ce501d5656f61cfb26745ce73/substratevm/src/com.oracle.svm.hosted/src/com/oracle/svm/hosted/image/CCLinkerInvocation.java#L560-L569)).
   `/MD` означает CRT в виде DLL: `vcruntime140.dll` из Redistributable и Universal CRT
   ([CRT library features](https://learn.microsoft.com/en-us/cpp/c-runtime-library/crt-library-features)).
2. **Объекты, скомпилированные с `/MD`, вызывают CRT через указатели импорта.** При `/MD` заголовки CRT объявляют
   функции с `__declspec(dllimport)`, и объект вызывает `getenv` через указатель `__imp_getenv`, который определяет
   только библиотека импорта DLL CRT
   ([Importing with dllimport](https://learn.microsoft.com/en-us/cpp/build/importing-into-an-application-using-declspec-dllimport)).
   Статические библиотеки JDK в GraalVM (`lib\static\windows-amd64`) — как раз такие объекты. Статический CRT
   (`libucrt.lib`, `libvcruntime.lib`, `libcmt.lib`) определяет `getenv`, но не `__imp_getenv`.
3. **Линковщик заполняет лишь часть указателей.** Если функция уже прилинкована из статического CRT ради другого
   кода, линковщик сам строит указатель и предупреждает
   [LNK4217](https://learn.microsoft.com/en-us/cpp/error-messages/tool-errors/linker-tools-warning-lnk4217) или
   [LNK4286](https://learn.microsoft.com/en-us/cpp/error-messages/tool-errors/linker-tools-warning-lnk4286). Функция,
   которую вызывают только объекты с `/MD`, остаётся неразрешённой: LNK2019 `__imp_<name>`.

Официальной опции native-image для статического CRT в DLL нет. Открытое предложение
[oracle/graal#14683](https://github.com/oracle/graal/issues/14683) с
[PR #14685](https://github.com/oracle/graal/pull/14685) добавляет `-H:+StaticVCRuntime` только для исполняемых
файлов: статический vcruntime и Universal CRT в виде DLL.

## Рецепт

1. **Перечислите функции CRT, которые объекты с `/MD` берут через указатели.** Это неопределённые символы `__imp_`
   этих библиотек (`dumpbin /symbols`), которые экспортируют библиотеки импорта динамического CRT (`dumpbin /exports`
   для `ucrt.lib`, `vcruntime.lib`, `msvcrt.lib`). Не забудьте POSIX-имена: `__imp_strdup` указывает на `_strdup`.
2. **Определите каждый указатель в собственном объекте-прокладке (shim), скомпилированном с `/MT`.** Там
   заголовки объявляют функции без `dllimport`, и `&getenv` — это функция статического CRT:

   ```c
   #include <stdlib.h>
   #include <string.h>

   void *__imp_getenv = (void *)&getenv;
   void *__imp__strdup = (void *)&_strdup;
   void *__imp_strdup = (void *)&_strdup;   // the POSIX name
   ```

   Когда функций сотня и больше, проще генерировать файл на ассемблере: ему не нужны ни заголовки, ни прототипы.

   ```asm
   EXTRN getenv:PROC
   PUBLIC __imp_getenv
   .data
   ALIGN 8
   __imp_getenv DQ getenv
   END
   ```

3. **Линкуйте со статическим CRT вместо динамического.** Для native-image опции передаются через
   `-H:NativeLinkerOption`; native-image и так добавляет `/NODEFAULTLIB:LIBCMT`, а эта опция убирает лишь библиотеку
   по умолчанию, поэтому `libcmt.lib` указывается явно:

   ```text
   -H:NativeLinkerOption=/NODEFAULTLIB:MSVCRT
   -H:NativeLinkerOption=/NODEFAULTLIB:vcruntime.lib
   -H:NativeLinkerOption=/NODEFAULTLIB:ucrt.lib
   -H:NativeLinkerOption=libcmt.lib
   -H:NativeLinkerOption=libvcruntime.lib
   -H:NativeLinkerOption=libucrt.lib
   -H:NativeLinkerOption=C:\path\to\crt_shim.obj
   ```

4. **Перегенерируйте список при смене инструментов.** Другой GraalVM или библиотека поставщика могут вызывать новые
   функции; недостающая роняет линковку с LNK2019 и никогда не возвращает DLL CRT молча.
5. **Следите за границей модуля.** Теперь у модуля своя копия CRT: своя куча, `errno`, локаль, файловые дескрипторы и
   окружение
   ([Microsoft Learn](https://learn.microsoft.com/en-us/cpp/c-runtime-library/potential-errors-passing-crt-objects-across-dll-boundaries)).
   Память, которую он возвращает, освобождают его же функции, а `_putenv` приложения после загрузки его `getenv` не
   увидит. Аллокатор, подменённый через DLL CRT (mimalloc, см.
   [статью об аллокаторах](../platform/replacing-the-process-allocator.ru.md)), до него тоже не дотягивается.

## Как тестировать

- `dumpbin /dependents` модуля: только системные DLL (`KERNEL32.dll` и подобные), ни `VCRUNTIME140*.dll`, ни
  `api-ms-win-crt-*.dll`. Universal CRT входит в Windows 10 и новее
  ([UCRT deployment](https://learn.microsoft.com/en-us/cpp/windows/universal-crt-deployment)), но модуль с `/MT` его
  вовсе не импортирует.
- Запустите приложение на машине или в контейнере Windows без Redistributable: на машине разработчика установленный
  Redistributable скрывает DLL, которую модуль загружает во время работы через `LoadLibrary`.
- Минимальное воспроизведение: статическая библиотека с `/MD`, вызывающая `getenv`, `_strdup` и `free`, и DLL с `/MT`,
  вызывающая её. Как есть: LNK4098, LNK4217 для `free`, LNK2019 для `__imp_getenv` и `__imp__strdup`. С опциями
  статического CRT и прокладкой: код выхода 0, DLL импортирует только `KERNEL32.dll`.
- Красная проверка: уберите объект-прокладку из линковки; она должна упасть с LNK2019 `__imp_*`.

## Чек-лист для ревью

- [ ] `dumpbin /dependents` поставляемого модуля не показывает ни `VCRUNTIME140*.dll`, ни `api-ms-win-crt-*.dll`.
- [ ] Прокладка генерируется из библиотек сборки, а не ведётся вручную, и сборка падает на LNK2019.
- [ ] Память, `FILE *` и прочие объекты CRT не пересекают границу модуля; API освобождает то, что выделил.
- [ ] Тест запускает модуль на машине или в контейнере без Redistributable.

## Где встречалось

- **dxfeed-graal-native-sdk**: DLL GraalVM native-image для приложений на C и C++; профиль сборки
  `windowsStaticRuntime` генерирует прокладку
  ([New-CrtShim.ps1](https://github.com/dxFeed/dxfeed-graal-native-sdk/blob/v3.11.0/scripts/windows-static-runtime/New-CrtShim.ps1),
  173 функции из 47 библиотек JDK для GraalVM 25.4.4.1.1) и линкует образ с опциями выше
  ([pom.xml](https://github.com/dxFeed/dxfeed-graal-native-sdk/blob/v3.11.0/pom.xml#L734-L754)). DLL импортирует только
  системные DLL; сборка это проверяет и запускает клиент с `/MT`
  ([Test-StaticRuntime.ps1](https://github.com/dxFeed/dxfeed-graal-native-sdk/blob/v3.11.0/scripts/windows-static-runtime/Test-StaticRuntime.ps1)).
- **GraalVM**: запрос на исполняемые файлы без Redistributable —
  [oracle/graal#14683](https://github.com/oracle/graal/issues/14683) и
  [PR #14685](https://github.com/oracle/graal/pull/14685); запрос постарше —
  [oracle/graal#1762](https://github.com/oracle/graal/issues/1762).

## Открытые вопросы

- Гибридный CRT для DLL (статический vcruntime и Universal CRT в виде DLL, как
  [PR #14685](https://github.com/oracle/graal/pull/14685) делает для исполняемых файлов и как описывает
  [Windows App SDK](https://github.com/microsoft/WindowsAppSDK/blob/main/docs/Coding-Guidelines/HybridCRT.md)) не
  пробовался; он сохранил бы одну кучу с библиотеками JDK, загружаемыми во время работы.
- Windows на ARM64 не проверялась.
- DLL JDK, которые образ загружает во время работы (AWT и подобные), собраны с `/MD` и возвращают DLL CRT; не
  рассматривалось.
