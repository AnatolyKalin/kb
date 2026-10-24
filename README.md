# Rakes and recipes

**English** | [Русский](README.ru.md)

Notes on recurring engineering problems: symptoms, causes, a verified recipe, how to test, a review checklist and
where else the problem has been seen. One article covers one class of problems. How to write one and how
translations work: [CONTRIBUTING.md](CONTRIBUTING.md); the template: [_template.md](_template.md).

## How to find an article

- By area, by symptom or by tag: the index below. It is generated from the front matter of the articles by
  `python3 tools/gen_index.py`; do not edit it by hand.
- By the text of an error or a log line: GitHub search in this repository (press `/` on the repository page), since
  the symptoms in the articles quote the key lines.
- Articles live in `articles/<area>/`; the areas are listed in [CONTRIBUTING.md](CONTRIBUTING.md#areas).

## Index

<!-- index:start -->

### By area

#### Lifetime: exit, destruction order, object ownership

- [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md)

### By symptom

- A callback runs after the library objects are destroyed — [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md)
- A crash at exit on Windows: `0xc0000409` / `0xC0000005` — [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md)
- A hang or a crash in `DLL_PROCESS_DETACH` — [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md)
- heap-use-after-free or a data race at exit under ASan / TSan — [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md)
- The process hangs at exit after `return` from `main()` — [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md)

### By tag

- `c++`: [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md)
- `callbacks`: [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md)
- `exit`: [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md)
- `graalvm`: [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md)
- `jni`: [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md)
- `lifetime`: [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md)
- `sanitizers`: [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md)
- `threads`: [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md)
- `windows-dll`: [Process exit when a library owns runtime threads that call back into user code](articles/lifetime/native-runtime-exit-and-callbacks.md)

<!-- index:end -->

## License

The texts are licensed under [Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSE).
