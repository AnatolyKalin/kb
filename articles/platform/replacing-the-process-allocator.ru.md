---
title: "Аллокатор процесса заменён, а нативная библиотека всё ещё ходит в старый malloc"
area: platform
tags: [malloc, mimalloc, performance, linux, windows, macos, windows-dll, graalvm]
symptoms:
  - "mimalloc подключён, но в профиле под кадрами библиотеки по-прежнему системный `malloc`"
  - "`mimalloc-redirect.dll seems to be initialized after ucrtbase.dll`"
  - "`standard malloc is _not_ redirected!`"
  - "Процесс не запускается: `0xC0000135`, не найдена `mimalloc-redirect.dll`"
  - "`LD_PRELOAD` или `DYLD_INSERT_LIBRARIES` ни на что не влияют"
  - "Порча кучи во `free` указателя, выделенного другим модулем"
updated: 2026-10
---

# Аллокатор процесса заменён, а нативная библиотека всё ещё ходит в старый malloc

[English](replacing-the-process-allocator.md) | **Русский**

Приложение подменяет `malloc` на весь процесс (здесь mimalloc; jemalloc, tcmalloc и прочие устроены так же), чтобы
ускорить нативную библиотеку, которая много выделяет: GraalVM native image, JNI-библиотеку, C-библиотеку с массой
мелких строк. Подмена действует на исполняемый файл, но не на каждый модуль процесса, и об этом никто не сообщает.

Проверено с mimalloc v3.6.0 на Ubuntu 24.04 (gcc 13, glibc 2.39) и Windows 11 (MSVC 19.42); см.
[«Как тестировать»](#как-тестировать).

## Симптомы

- Аллокатор подключён, программа работает, а ускорения нет; в профиле под кадрами библиотеки по-прежнему системный
  аллокатор (`ucrtbase!malloc`, `RtlAllocateHeap`, `_int_malloc` из glibc).
- Windows, с `MIMALLOC_VERBOSE=1`:
  `mimalloc-redirect: error: mimalloc-redirect.dll seems to be initialized after ucrtbase.dll` и
  `warning: standard malloc is _not_ redirected! -- using regular malloc/free`.
- Windows: процесс не запускается, код выхода `0xC0000135` (не найдена DLL).
- `LD_PRELOAD` (Linux) или `DYLD_INSERT_LIBRARIES` (macOS) ничего не меняют.
- Падение или порча кучи во `free`, когда указатель, выделенный одним модулем, освобождает другой.

## Причины

Подмена происходит на одном уровне, и модуль, который через этот уровень не проходит, остаётся при своём аллокаторе.

1. **Linux: подстановка символов динамическим загрузчиком.** `LD_PRELOAD` (или `malloc`, определённый в исполняемом
   файле) стоит первым в глобальной области поиска символов, поэтому его получает каждая разделяемая библиотека,
   вызывающая `malloc`
   ([glibc: Replacing malloc](https://sourceware.org/glibc/manual/latest/html_node/Replacing-malloc.html)).
   Мимо проходят:
   - статически слинкованный исполняемый файл (`-static`): нет динамического загрузчика, который учёл бы
     `LD_PRELOAD`;
   - библиотека, загруженная через `dlopen(..., RTLD_DEEPBIND)`: она ищет `malloc` сначала в собственных
     зависимостях (libc);
   - режим secure execution (set-user-ID, set-group-ID): пути предзагрузки со слешами игнорируются
     ([ld.so(8)](https://man7.org/linux/man-pages/man8/ld.so.8.html)).
2. **Windows: правка CRT-библиотеки.** `mimalloc-redirect.dll` перенаправляет функции выделения памяти в
   `ucrtbase.dll` — C-рантайме в виде DLL; для этого нужен CRT в виде DLL (`/MD`) и `mimalloc.dll` первой в импорте
   исполняемого файла ([README mimalloc](https://github.com/microsoft/mimalloc/blob/v3.6.0/readme.md#L537-L575)).
   Мимо проходят:
   - модуль со статическим CRT (`/MT`): у каждой копии CRT своя куча
     ([Microsoft Learn](https://learn.microsoft.com/en-us/cpp/c-runtime-library/potential-errors-passing-crt-objects-across-dll-boundaries));
     исполняемый файл с `/MT` тоже остаётся при своей куче, хотя его DLL с `/MD` перенаправляются;
   - любой процесс, где другая DLL импортируется раньше `mimalloc.dll`: она первой загружает `ucrtbase.dll`, и
     перенаправление отступает. Порядок импорта повторяет порядок библиотек в командной строке линковщика;
   - отсутствующая `mimalloc-redirect.dll`: `mimalloc.dll` её импортирует, поэтому загрузчик ищет её ещё и в текущем
     каталоге и в `PATH` и берёт **любую** найденную копию (другой продукт может поставлять свою версию) — либо процесс
     не запускается;
   - `MIMALLOC_DISABLE_REDIRECT=1` в окружении.
3. **macOS: вставка через dyld и malloc zones.** `DYLD_INSERT_LIBRARIES` загружает библиотеку первой, а mimalloc
   регистрирует себя зоной malloc по умолчанию
   ([alloc-override-zone.c](https://github.com/microsoft/mimalloc/blob/v3.6.0/src/prim/osx/alloc-override-zone.c#L458-L470)).
   dyld игнорирует переменные `DYLD_*` для двоичных файлов под защитой System Integrity Protection
   ([dyld(1)](https://keith.github.io/xcode-man-pages/dyld.1.html)) и, по словам Apple, для приложений с Hardened
   Runtime без права
   [`com.apple.security.cs.allow-dyld-environment-variables`](https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.security.cs.allow-dyld-environment-variables).

Смешение аллокаторов хуже упущенного ускорения: память, выделенная одним аллокатором и освобождённая другим, портит
кучу. Безопасно оставить при своём аллокаторе можно только библиотеку, чья память не пересекает её границу.

## Рецепт

**Linux.**

1. Попробовать: `LD_PRELOAD=/path/to/libmimalloc.so ./app`.
2. Поставлять: слинковать mimalloc с исполняемым файлом, чтобы не нужна была переменная окружения. `malloc`,
   определённый в исполняемом файле, подменяет его для всех разделяемых библиотек так же, как `LD_PRELOAD`:

   ```sh
   gcc -o app main.c /path/to/mimalloc.o -lthirdparty -lpthread   # или -lmimalloc в начале командной строки
   ```

3. Оставить исполняемый файл динамическим (без `-static`) и не загружать с `RTLD_DEEPBIND` библиотеку, чья память
   пересекает её границу.

**Windows.**

1. Собрать исполняемый файл и все DLL, которые нужно перенаправить, с CRT в виде DLL (`/MD`).
2. Поставить `mimalloc.dll.lib` **первой** в командной строке линковщика и оставить ссылку на mimalloc, чтобы
   линковщик не выбросил импорт (`/INCLUDE:mi_version` или вызов `mi_version()` в `main`):

   ```bat
   cl /MD main.c mimalloc.dll.lib thirdparty.lib /link /INCLUDE:mi_version
   ```

3. Положить рядом с исполняемым файлом `mimalloc.dll` и `mimalloc-redirect.dll` одной версии.
4. Проверить порядок импорта: `minject -l app.exe` (из
   [каталога `bin`](https://github.com/microsoft/mimalloc/tree/v3.6.0/bin) mimalloc) должен показать
   `0: mimalloc.dll`; `minject` умеет и исправить порядок в готовом исполняемом файле.
5. DLL со статическим CRT остаётся на своей куче; если её память пересекает границу, освобождать её должна эта же DLL.

**macOS** (здесь не проверено, см. [«Открытые вопросы»](#открытые-вопросы)):
`DYLD_INSERT_LIBRARIES=/path/to/libmimalloc.dylib` работает только для двоичных файлов, которые dyld не защищает;
поставляемое приложение линкует mimalloc.

## Как тестировать

Спросить сам аллокатор, чья это память. Проверка ищет mimalloc во время выполнения, поэтому один и тот же двоичный
файл работает и с ним, и без него:

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

- Linux: запустить с `MIMALLOC_VERBOSE=1`; строка `mimalloc: process init` показывает, что mimalloc вообще стартовал.
- Windows: `MIMALLOC_VERBOSE=1` печатает `mimalloc: malloc is redirected.` или ошибку выше. Чтобы поймать чужую копию,
  выведите путь загруженной `mimalloc-redirect.dll`
  (`GetModuleFileNameA(GetModuleHandleA("mimalloc-redirect.dll"), ...)`).
- Красные проверки, в каждой для библиотеки должно напечататься "system": Linux — `dlopen` с `RTLD_DEEPBIND`,
  исполняемый файл с `-static`; Windows — библиотека импорта стороннего модуля раньше `mimalloc.dll.lib`, библиотека,
  собранная с `/MT`, `MIMALLOC_DISABLE_REDIRECT=1`.
- На Linux `mimalloc.o` скрывает свои функции от `dlsym`; когда он вшит в исполняемый файл, объявите
  `mi_is_in_heap_region` слабым символом.

## Чек-лист для ревью

- [ ] Исполняемый файл и все библиотеки, чьи выделения важны, используют CRT в виде DLL (Windows), а исполняемый файл
      динамический (Linux).
- [ ] `mimalloc.dll` — первый импорт исполняемого файла (`minject -l`).
- [ ] Рядом с `mimalloc.dll` лежит `mimalloc-redirect.dll` той же версии.
- [ ] Никакого `RTLD_DEEPBIND` для библиотек, чья память пересекает их границу.
- [ ] Память, пересекающая границу модуля, освобождается модулем, который её выделил, или общим для обоих
      аллокатором.
- [ ] Тест проверяет, что память библиотеки приходит из подменённого аллокатора (`mi_is_in_heap_region`), на каждой
      ОС релиза.

## Где встречалось

- **GraalVM native image**: неуправляемая память идёт в `malloc` C-рантайма
  ([`UnmanagedMemorySupportImpl`](https://github.com/oracle/graal/blob/092eca6772a74d4ce501d5656f61cfb26745ce73/substratevm/src/com.oracle.svm.core/src/com/oracle/svm/core/memory/UnmanagedMemorySupportImpl.java#L55-L61)),
  поэтому подмена покрывает библиотеку native image, если та использует CRT в виде DLL. Проверено на DLL
  [dxfeed-graal-native-sdk](https://github.com/dxFeed/dxfeed-graal-native-sdk): строка, которую возвращает библиотека,
  приходит из mimalloc, когда исполняемый файл линкует `mimalloc.dll` первой. При доставке рыночных событий из этой
  библиотеки в C++-приложение mimalloc сэкономил на Linux около 10 % процессорного времени на событие. Сборка такой
  библиотеки со статическим CRT осталась бы на системной куче.
- **mimalloc**: перенаправление инициализируется после `ucrtbase.dll` из-за порядка импорта:
  [microsoft/mimalloc#668](https://github.com/microsoft/mimalloc/issues/668); подмена внутри DLL, которую приложение
  загружает динамически: [microsoft/mimalloc#820](https://github.com/microsoft/mimalloc/issues/820); падения при
  освобождении памяти других DLL под подменой:
  [microsoft/mimalloc#261](https://github.com/microsoft/mimalloc/issues/261),
  [microsoft/mimalloc#1128](https://github.com/microsoft/mimalloc/issues/1128); macOS, `free` подменён, а `malloc`
  нет: [microsoft/mimalloc#1350](https://github.com/microsoft/mimalloc/issues/1350).

## Открытые вопросы

- macOS не запускалась: `DYLD_INSERT_LIBRARIES`, Hardened Runtime и линковка mimalloc в приложение.
- Режим secure execution на Linux не запускался.
- Оставляет ли CMake `mimalloc` первым в импорте, если он стоит первым в `target_link_libraries`, а другие цели тянут
  свои зависимости: не проверено; тест собирался командной строкой `cl`.
- Библиотека native image, собранная со статическим CRT, не запускалась; ожидание (системная куча) выведено из случая
  с `/MT`.
- Windows на ARM64 (`mimalloc-redirect-arm64.dll`, `-arm64ec`) не запускалась.
