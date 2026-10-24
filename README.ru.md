# Грабли и рецепты

[English](README.md) | **Русский**

Заметки о повторяющихся инженерных проблемах: симптомы, причины, проверенный рецепт, как тестировать, чек-лист для
ревью и где ещё это встречалось. Одна статья — один класс задач. Как писать и как устроены переводы —
[CONTRIBUTING.ru.md](CONTRIBUTING.ru.md), шаблон — [_template.ru.md](_template.ru.md).

## Как найти статью

- По области, симптому или тегу — оглавление ниже. Его собирает `python3 tools/gen_index.py` из метаданных статей;
  руками не правится.
- По тексту ошибки или строке лога — поиск GitHub по этому репозиторию (клавиша `/` на странице репозитория): в
  симптомах статей приведены ключевые строки.
- Статьи лежат в `articles/<область>/`; список областей — в [CONTRIBUTING.ru.md](CONTRIBUTING.ru.md#области).

## Оглавление

<!-- index:start -->

### По областям

#### Время жизни: выход, порядок разрушения, владение объектами

- [Выход процесса, когда библиотека держит свои потоки и зовёт колбэки](articles/lifetime/native-runtime-exit-and-callbacks.ru.md)
- [Константы библиотеки пусты или роняют программу в инициализаторах и деструкторах глобальных объектов](articles/lifetime/library-constants-in-global-initializers.ru.md)

#### Платформы: особенности Windows, Linux, macOS

- [Аллокатор процесса заменён, а нативная библиотека всё ещё ходит в старый malloc](articles/platform/replacing-the-process-allocator.ru.md)

#### Инструменты: оболочки, WSL, git, GitHub, редакторы

- [Команда, запущенная в WSL из Git Bash или PowerShell, приходит искажённой](articles/tooling/calling-wsl-from-windows-shells.ru.md)

### По симптомам

- ASan: `initialization-order-fiasco` — [Константы библиотеки пусты или роняют программу в инициализаторах и деструкторах глобальных объектов](articles/lifetime/library-constants-in-global-initializers.ru.md)
- heap-use-after-free или гонка на выходе под ASan / TSan — [Выход процесса, когда библиотека держит свои потоки и зовёт колбэки](articles/lifetime/native-runtime-exit-and-callbacks.ru.md)
- `LD_PRELOAD` или `DYLD_INSERT_LIBRARIES` ни на что не влияют — [Аллокатор процесса заменён, а нативная библиотека всё ещё ходит в старый malloc](articles/platform/replacing-the-process-allocator.ru.md)
- `ls: cannot access 'C:/Program Files/Git/home/...'`: путь Linux превратился в путь Windows — [Команда, запущенная в WSL из Git Bash или PowerShell, приходит искажённой](articles/tooling/calling-wsl-from-windows-shells.ru.md)
- mimalloc подключён, но в профиле под кадрами библиотеки по-прежнему системный `malloc` — [Аллокатор процесса заменён, а нативная библиотека всё ещё ходит в старый malloc](articles/platform/replacing-the-process-allocator.ru.md)
- `mimalloc-redirect.dll seems to be initialized after ucrtbase.dll` — [Аллокатор процесса заменён, а нативная библиотека всё ещё ходит в старый malloc](articles/platform/replacing-the-process-allocator.ru.md)
- `pure virtual function call` в деструкторе глобальной переменной на выходе — [Константы библиотеки пусты или роняют программу в инициализаторах и деструкторах глобальных объектов](articles/lifetime/library-constants-in-global-initializers.ru.md)
- `python3` печатает `Python ` и выходит с кодом 9009 — [Команда, запущенная в WSL из Git Bash или PowerShell, приходит искажённой](articles/tooling/calling-wsl-from-windows-shells.ru.md)
- `$'\r': command not found` в скрипте из checkout на Windows — [Команда, запущенная в WSL из Git Bash или PowerShell, приходит искажённой](articles/tooling/calling-wsl-from-windows-shells.ru.md)
- `standard malloc is _not_ redirected!` — [Аллокатор процесса заменён, а нативная библиотека всё ещё ходит в старый malloc](articles/platform/replacing-the-process-allocator.ru.md)
- `;`, `<`, `>`, `\` в аргументах `wsl` работают как синтаксис оболочки — [Команда, запущенная в WSL из Git Bash или PowerShell, приходит искажённой](articles/tooling/calling-wsl-from-windows-shells.ru.md)
- Зависание или падение в `DLL_PROCESS_DETACH` — [Выход процесса, когда библиотека держит свои потоки и зовёт колбэки](articles/lifetime/native-runtime-exit-and-callbacks.ru.md)
- Колбэк приходит после разрушения объектов библиотеки — [Выход процесса, когда библиотека держит свои потоки и зовёт колбэки](articles/lifetime/native-runtime-exit-and-callbacks.ru.md)
- Константа библиотеки пуста или равна нулю в инициализаторе глобальной переменной — [Константы библиотеки пусты или роняют программу в инициализаторах и деструкторах глобальных объектов](articles/lifetime/library-constants-in-global-initializers.ru.md)
- Падает со статической библиотекой и работает с динамической — [Константы библиотеки пусты или роняют программу в инициализаторах и деструкторах глобальных объектов](articles/lifetime/library-constants-in-global-initializers.ru.md)
- Падение до `main()`, когда глобальная переменная вызывает функцию библиотеки — [Константы библиотеки пусты или роняют программу в инициализаторах и деструкторах глобальных объектов](articles/lifetime/library-constants-in-global-initializers.ru.md)
- Падение на выходе под Windows: `0xc0000409` / `0xC0000005` — [Выход процесса, когда библиотека держит свои потоки и зовёт колбэки](articles/lifetime/native-runtime-exit-and-callbacks.ru.md)
- Переменная в `wsl -- bash -c '...'` пуста — [Команда, запущенная в WSL из Git Bash или PowerShell, приходит искажённой](articles/tooling/calling-wsl-from-windows-shells.ru.md)
- Порча кучи во `free` указателя, выделенного другим модулем — [Аллокатор процесса заменён, а нативная библиотека всё ещё ходит в старый malloc](articles/platform/replacing-the-process-allocator.ru.md)
- Процесс висит на выходе после `return` из `main()` — [Выход процесса, когда библиотека держит свои потоки и зовёт колбэки](articles/lifetime/native-runtime-exit-and-callbacks.ru.md)
- Процесс не запускается: `0xC0000135`, не найдена `mimalloc-redirect.dll` — [Аллокатор процесса заменён, а нативная библиотека всё ещё ходит в старый malloc](articles/platform/replacing-the-process-allocator.ru.md)

### По тегам

- `c++`: [Константы библиотеки пусты или роняют программу в инициализаторах и деструкторах глобальных объектов](articles/lifetime/library-constants-in-global-initializers.ru.md); [Выход процесса, когда библиотека держит свои потоки и зовёт колбэки](articles/lifetime/native-runtime-exit-and-callbacks.ru.md)
- `callbacks`: [Выход процесса, когда библиотека держит свои потоки и зовёт колбэки](articles/lifetime/native-runtime-exit-and-callbacks.ru.md)
- `constexpr`: [Константы библиотеки пусты или роняют программу в инициализаторах и деструкторах глобальных объектов](articles/lifetime/library-constants-in-global-initializers.ru.md)
- `constinit`: [Константы библиотеки пусты или роняют программу в инициализаторах и деструкторах глобальных объектов](articles/lifetime/library-constants-in-global-initializers.ru.md)
- `exit`: [Выход процесса, когда библиотека держит свои потоки и зовёт колбэки](articles/lifetime/native-runtime-exit-and-callbacks.ru.md)
- `git-bash`: [Команда, запущенная в WSL из Git Bash или PowerShell, приходит искажённой](articles/tooling/calling-wsl-from-windows-shells.ru.md)
- `graalvm`: [Выход процесса, когда библиотека держит свои потоки и зовёт колбэки](articles/lifetime/native-runtime-exit-and-callbacks.ru.md); [Аллокатор процесса заменён, а нативная библиотека всё ещё ходит в старый malloc](articles/platform/replacing-the-process-allocator.ru.md)
- `jni`: [Выход процесса, когда библиотека держит свои потоки и зовёт колбэки](articles/lifetime/native-runtime-exit-and-callbacks.ru.md)
- `lifetime`: [Выход процесса, когда библиотека держит свои потоки и зовёт колбэки](articles/lifetime/native-runtime-exit-and-callbacks.ru.md)
- `line-endings`: [Команда, запущенная в WSL из Git Bash или PowerShell, приходит искажённой](articles/tooling/calling-wsl-from-windows-shells.ru.md)
- `linux`: [Аллокатор процесса заменён, а нативная библиотека всё ещё ходит в старый malloc](articles/platform/replacing-the-process-allocator.ru.md)
- `macos`: [Аллокатор процесса заменён, а нативная библиотека всё ещё ходит в старый malloc](articles/platform/replacing-the-process-allocator.ru.md)
- `malloc`: [Аллокатор процесса заменён, а нативная библиотека всё ещё ходит в старый malloc](articles/platform/replacing-the-process-allocator.ru.md)
- `mimalloc`: [Аллокатор процесса заменён, а нативная библиотека всё ещё ходит в старый malloc](articles/platform/replacing-the-process-allocator.ru.md)
- `msvc`: [Константы библиотеки пусты или роняют программу в инициализаторах и деструкторах глобальных объектов](articles/lifetime/library-constants-in-global-initializers.ru.md)
- `msys2`: [Команда, запущенная в WSL из Git Bash или PowerShell, приходит искажённой](articles/tooling/calling-wsl-from-windows-shells.ru.md)
- `performance`: [Аллокатор процесса заменён, а нативная библиотека всё ещё ходит в старый malloc](articles/platform/replacing-the-process-allocator.ru.md)
- `powershell`: [Команда, запущенная в WSL из Git Bash или PowerShell, приходит искажённой](articles/tooling/calling-wsl-from-windows-shells.ru.md)
- `python`: [Команда, запущенная в WSL из Git Bash или PowerShell, приходит искажённой](articles/tooling/calling-wsl-from-windows-shells.ru.md)
- `quoting`: [Команда, запущенная в WSL из Git Bash или PowerShell, приходит искажённой](articles/tooling/calling-wsl-from-windows-shells.ru.md)
- `sanitizers`: [Константы библиотеки пусты или роняют программу в инициализаторах и деструкторах глобальных объектов](articles/lifetime/library-constants-in-global-initializers.ru.md); [Выход процесса, когда библиотека держит свои потоки и зовёт колбэки](articles/lifetime/native-runtime-exit-and-callbacks.ru.md)
- `shell`: [Команда, запущенная в WSL из Git Bash или PowerShell, приходит искажённой](articles/tooling/calling-wsl-from-windows-shells.ru.md)
- `static-destruction`: [Константы библиотеки пусты или роняют программу в инициализаторах и деструкторах глобальных объектов](articles/lifetime/library-constants-in-global-initializers.ru.md)
- `static-initialization`: [Константы библиотеки пусты или роняют программу в инициализаторах и деструкторах глобальных объектов](articles/lifetime/library-constants-in-global-initializers.ru.md)
- `static-library`: [Константы библиотеки пусты или роняют программу в инициализаторах и деструкторах глобальных объектов](articles/lifetime/library-constants-in-global-initializers.ru.md)
- `threads`: [Выход процесса, когда библиотека держит свои потоки и зовёт колбэки](articles/lifetime/native-runtime-exit-and-callbacks.ru.md)
- `windows`: [Аллокатор процесса заменён, а нативная библиотека всё ещё ходит в старый malloc](articles/platform/replacing-the-process-allocator.ru.md); [Команда, запущенная в WSL из Git Bash или PowerShell, приходит искажённой](articles/tooling/calling-wsl-from-windows-shells.ru.md)
- `windows-dll`: [Выход процесса, когда библиотека держит свои потоки и зовёт колбэки](articles/lifetime/native-runtime-exit-and-callbacks.ru.md); [Аллокатор процесса заменён, а нативная библиотека всё ещё ходит в старый malloc](articles/platform/replacing-the-process-allocator.ru.md)
- `wsl`: [Команда, запущенная в WSL из Git Bash или PowerShell, приходит искажённой](articles/tooling/calling-wsl-from-windows-shells.ru.md)

<!-- index:end -->

## Лицензия

Тексты распространяются под лицензией [Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSE).
