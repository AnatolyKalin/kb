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

### По симптомам

- heap-use-after-free или гонка на выходе под ASan / TSan — [Выход процесса, когда библиотека держит свои потоки и зовёт колбэки](articles/lifetime/native-runtime-exit-and-callbacks.ru.md)
- Зависание или падение в `DLL_PROCESS_DETACH` — [Выход процесса, когда библиотека держит свои потоки и зовёт колбэки](articles/lifetime/native-runtime-exit-and-callbacks.ru.md)
- Колбэк приходит после разрушения объектов библиотеки — [Выход процесса, когда библиотека держит свои потоки и зовёт колбэки](articles/lifetime/native-runtime-exit-and-callbacks.ru.md)
- Падение на выходе под Windows: `0xc0000409` / `0xC0000005` — [Выход процесса, когда библиотека держит свои потоки и зовёт колбэки](articles/lifetime/native-runtime-exit-and-callbacks.ru.md)
- Процесс висит на выходе после `return` из `main()` — [Выход процесса, когда библиотека держит свои потоки и зовёт колбэки](articles/lifetime/native-runtime-exit-and-callbacks.ru.md)

### По тегам

- `c++`: [Выход процесса, когда библиотека держит свои потоки и зовёт колбэки](articles/lifetime/native-runtime-exit-and-callbacks.ru.md)
- `callbacks`: [Выход процесса, когда библиотека держит свои потоки и зовёт колбэки](articles/lifetime/native-runtime-exit-and-callbacks.ru.md)
- `exit`: [Выход процесса, когда библиотека держит свои потоки и зовёт колбэки](articles/lifetime/native-runtime-exit-and-callbacks.ru.md)
- `graalvm`: [Выход процесса, когда библиотека держит свои потоки и зовёт колбэки](articles/lifetime/native-runtime-exit-and-callbacks.ru.md)
- `jni`: [Выход процесса, когда библиотека держит свои потоки и зовёт колбэки](articles/lifetime/native-runtime-exit-and-callbacks.ru.md)
- `lifetime`: [Выход процесса, когда библиотека держит свои потоки и зовёт колбэки](articles/lifetime/native-runtime-exit-and-callbacks.ru.md)
- `sanitizers`: [Выход процесса, когда библиотека держит свои потоки и зовёт колбэки](articles/lifetime/native-runtime-exit-and-callbacks.ru.md)
- `threads`: [Выход процесса, когда библиотека держит свои потоки и зовёт колбэки](articles/lifetime/native-runtime-exit-and-callbacks.ru.md)
- `windows-dll`: [Выход процесса, когда библиотека держит свои потоки и зовёт колбэки](articles/lifetime/native-runtime-exit-and-callbacks.ru.md)

<!-- index:end -->

## Лицензия

Тексты распространяются под лицензией [Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSE).
