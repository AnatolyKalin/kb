---
title: "Команда, запущенная в WSL из Git Bash или PowerShell, приходит искажённой"
area: tooling
tags: [wsl, git-bash, msys2, powershell, windows, shell, quoting, line-endings, python]
symptoms:
  - "`ls: cannot access 'C:/Program Files/Git/home/...'`: путь Linux превратился в путь Windows"
  - "Переменная в `wsl -- bash -c '...'` пуста"
  - "`;`, `<`, `>`, `\\` в аргументах `wsl` работают как синтаксис оболочки"
  - "`$'\\r': command not found` в скрипте из checkout на Windows"
  - "`python3` печатает `Python ` и выходит с кодом 9009"
updated: 2026-10
---

# Команда, запущенная в WSL из Git Bash или PowerShell, приходит искажённой

[English](calling-wsl-from-windows-shells.md) | **Русский**

Класс задач: скрипты на Windows, которые собирают или тестируют под Linux через `wsl.exe`, — вспомогательные скрипты
CI, агенты, однострочники в терминале. Каждый слой между оболочкой Windows и программой Linux по-своему переписывает
командную строку.

Примеры и ссылки — в разделе [«Где встречалось»](#где-встречалось).

## Симптомы

- `ls: cannot access 'C:/Program Files/Git/home/user/src'`: путь Linux `/home/user/src` переписан.
- `wsl -- bash -c 'X=1; echo "[$X]"'` печатает `[]`; переменная, заданная или переданная для вложенного `bash`, пуста.
- `wsl -- printf '[%s]\n' 'a;b'` печатает `[a]n` и `b: command not found`: `;` разрезала команду, а `\n` потерял
  обратную косую черту.
- `$'\r': command not found` или `cannot access '/some/path'$'\r'` у скрипта, который на Linux работает.
- `python3 --version` печатает `Python ` и выходит с кодом 9009; `py -3` работает.

## Причины

1. **Git Bash преобразует аргументы, похожие на пути POSIX.** Рантайм MSYS2 под Git Bash переписывает аргументы
   вроде `/home/x` или `/mnt/c` в пути Windows (`C:/Program Files/Git/home/x`), когда запускает программу не из
   MSYS, а `wsl.exe` как раз такая.
2. **`wsl.exe` отдаёт команду оболочке Linux по умолчанию.** `wsl <команда>` и `wsl -- <команда>` не запускают
   команду напрямую: они собирают одну командную строку и передают её оболочке пользователя (`$SHELL -c`). Аргументы
   с пробелами остаются целыми, но `$`, `;`, `<`, `>`, `|`, `\` и шаблоны разбираются второй раз, так что `$X`
   раскрывает внешняя оболочка, где переменная не задана. `wsl -e` (`--exec`) запускает программу без этой оболочки.
   Другие слои, которые съедают обратные слеши:
   [Из кода, записанного через оболочку, пропадают обратные слеши](backslashes-lost-on-the-way-through-a-shell.ru.md).
3. **PowerShell сам раскрывает `$X` в двойных кавычках.** Одинарные кавычки защищают `$X` от PowerShell, но не от
   причины 2.
4. **Переменные окружения Windows не доходят до WSL**, если их нет в `WSLENV`.
5. **Окончания строк CRLF.** Checkout с `core.autocrlf=true` даёт скрипты с `\r\n`; bash считает `\r` частью
   последнего слова каждой строки.
6. **`python3` — псевдоним App Execution Alias.** `%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe` — заглушка
   нулевого размера, которая открывает Microsoft Store; она стоит в `PATH` первой, если псевдоним не выключен.

## Рецепт

1. **Отключить преобразование путей для вызова** в Git Bash: `MSYS_NO_PATHCONV=1` (Git for Windows) или
   `MSYS2_ARG_CONV_EXCL='*'` (MSYS2). Для одного аргумента подходит и двойная косая черта в начале: `//home/x`.
2. **`wsl -e` — для всего, где есть синтаксис оболочки**, а всё, что длиннее строки, — в файл скрипта. Значения
   передавать аргументами или через `env`, а не подстановкой текста:

   ```bash
   # Git Bash: скрипт читает $SDK; ничего не разбирается дважды.
   MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -e env SDK=/opt/sdk bash /mnt/c/src/ci/build.sh
   ```

   ```powershell
   wsl -d Ubuntu-24.04 -e bash -c 'X=1; echo "[$X]"'   # [1]
   wsl -d Ubuntu-24.04 -- bash -c 'X=1; echo "[$X]"'   # []  ($X раскрыла оболочка по умолчанию)
   ```

3. **Передавать переменные Windows через `WSLENV`**, когда они нужны скрипту (`WSLENV=SDK/p` заодно переводит путь
   Windows в путь Linux).
4. **Держать скрипты оболочки в LF**: `*.sh text eol=lf` в `.gitattributes`.
5. **Собирать в файловой системе Linux**: копировать или синхронизировать `rsync` исходники в `~/...`; сборка на
   `/mnt/c` намного медленнее.
6. **Вызывать Python как `py -3`** в скриптах Windows или выключить псевдонимы `python.exe` / `python3.exe` в
   «Параметры › Приложения › Дополнительные параметры приложений › Псевдонимы выполнения приложений».

## Как тестировать

Каждая строка — красная проверка; наблюдалось на Windows 11, WSL 3.0.3 (ядро 6.18), Git for Windows 2.55,
PowerShell 7.6.

| Команда | Результат |
|---|---|
| `wsl -d Ubuntu-24.04 -- ls -d /home` (Git Bash) | `cannot access 'C:/Program Files/Git/home'` |
| `MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- ls -d /home` | `/home` |
| `wsl -d Ubuntu-24.04 -- ls -d //home` (Git Bash) | `/home` |
| `wsl -- bash -c 'X=1; echo "[$X]"'` (Git Bash или PowerShell) | `[]` |
| `wsl -e bash -c 'X=1; echo "[$X]"'` | `[1]` |
| `wsl -- env S=abc bash -c 'echo "[$S]"'` | `[]` |
| `wsl -e env S=abc bash -c 'echo "[$S]"'` | `[abc]` |
| `wsl -- printf '[%s]\n' 'a b' c` | `[a b]n[c]n`: пробелы сохранены, `\` потерян |
| `FOO=bar wsl -e printenv FOO` / с `WSLENV=FOO` | код 1 / `bar` |
| `bash crlf.sh` со строкой `ls /x\r\n` | `cannot access '/x'$'\r'` |
| `python3 --version` (PowerShell) | `Python `, код выхода 9009 |

## Чек-лист для ревью

- [ ] `wsl` с синтаксисом оболочки в аргументах вызывается с `-e` или запускает файл скрипта.
- [ ] Вызовы из Git Bash с путями Linux задают `MSYS_NO_PATHCONV=1`.
- [ ] Нет `$VAR` стороны Linux внутри командной строки `wsl -- ...`.
- [ ] `.gitattributes` держит `*.sh` в LF.
- [ ] Скрипты Windows вызывают `py -3`, а не `python3`.

## Где встречалось

- **Сборка C++ SDK на Windows и WSL** — скрипт проверки запускался из Git Bash как `wsl -- bash -c '... $S ...'`; `$S`
  оказывалась пустой, а аргументы `/home/...` превращались в `C:/Program Files/Git/home/...`. Исправлено через
  `MSYS_NO_PATHCONV=1`, файл скрипта и `env`.
- **Git for Windows** добавил `MSYS_NO_PATHCONV`, потому что преобразование ломало аргументы программ Windows; в
  release notes показано, как `/usr/bin/bash.exe` превращался в `C:\Program Files\Git\usr\bin\bash.exe`:
  [release notes](https://github.com/git-for-windows/build-extra/blob/main/ReleaseNotes.md),
  [изменение](https://github.com/git-for-windows/msys2-runtime/pull/11).

## Источники

- Преобразование путей в MSYS2 и `MSYS2_ARG_CONV_EXCL`:
  [MSYS2, Filesystem Paths](https://www.msys2.org/docs/filesystem-paths/).
- `wsl --help`: `--exec, -e` запускает команду без оболочки Linux по умолчанию; `--` передаёт остаток командной
  строки без изменений (этой оболочке).
- `WSLENV` и скорость `/mnt/c`:
  [Working across Windows and Linux file systems](https://learn.microsoft.com/en-us/windows/wsl/filesystems).
- `eol=lf`: [gitattributes](https://git-scm.com/docs/gitattributes).
- Псевдонимы выполнения приложений и запускатель `py`:
  [Using Python on Windows](https://docs.python.org/3/using/windows.html).
- Как PowerShell передаёт аргументы внешним программам, `$PSNativeCommandArgumentPassing`:
  [about_Preference_Variables](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_preference_variables).

## Открытые вопросы

- Меняет ли оболочка дистрибутива по умолчанию (zsh, fish), какие символы разбираются второй раз в причине 2:
  проверялся только bash.
