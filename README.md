# Rakes and recipes

**English** | [Русский](README.ru.md)

Notes on recurring engineering problems: symptoms, causes, a verified recipe, how to test, a review checklist and
where else the problem has been seen. One article covers one class of problems. How to write one and how
translations work: [CONTRIBUTING.md](CONTRIBUTING.md); the template: [_template.md](_template.md).

## Articles

| Article | About | Tags | Languages |
|---|---|---|---|
| [Process exit when a library owns runtime threads that call back into user code](native-runtime-exit-and-callbacks.md) | A hang or use-after-free at exit, `atexit` vs static destruction order, Windows DLL, waiting for callbacks in progress | `c++` `exit` `callbacks` `windows-dll` `graalvm` `jni` | en, [ru](native-runtime-exit-and-callbacks.ru.md) |

## License

The texts are licensed under [Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSE).
