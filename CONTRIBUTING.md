# How to write an article

**English** | [Русский](CONTRIBUTING.ru.md)

Informal rules. The goal: a year later, stepping on the same rake, you find the article by the symptom and fix the
problem by the recipe, without rereading the ticket history.

## What makes an article

- A class of problems, not a single bug: "process exit with runtime threads", not "a bug in function X".
- The cause was not obvious, or someone has already stepped on it twice.
- There is a verified recipe, or at least a verified explanation. Guesses go to "Open questions".

## Title and file

- The title names the symptom or the situation, the way people will search for it: "The process hangs at exit…",
  "A callback after close…". Not a ticket number, not a product name.
- The file name is `kebab-case` by topic, in English, with no dates or numbers:
  `native-runtime-exit-and-callbacks.md`.
- A new article gets a row in the table in `README.md` and in every translation of it.

## Languages and translations

- English is the main language: `<name>.md`. Translations sit next to it as `<name>.<lang>.md`, where `<lang>` is an
  ISO 639-1 code: `native-runtime-exit-and-callbacks.ru.md`.
- Every text (articles, `README`, `CONTRIBUTING`, the template) is kept in all the languages of the repository; now
  these are English and Russian.
- Bring an article in any language you like. We translate it into English and into the other languages; until then
  it is added as is, and the index marks the missing translations.
- A new language: translate `README`, `CONTRIBUTING` and the template, and as many articles as you can; add the
  language to the language line of every file and to the index.
- The versions say the same thing. When you change one, change the others in the same commit, or add a line under
  the title of each translation that is behind: "Behind the English version since YYYY-MM". If they differ, the
  English version is authoritative.
- Every file starts with a language line under the title: the current language in bold, the others as links.
- A translation keeps the structure, the code and the links; terms and identifiers stay as in the code.

## Structure

The template is [`_template.md`](_template.md). Skip a section if it has nothing to say:

1. **Introduction** (2–3 lines): which class of problems, where else it happens.
2. **Tags and the update date.**
3. **Symptoms**: what is visible from outside: a hang, an exit code, a sanitizer report, an error message (the key
   lines, so that search finds them).
4. **Causes**: the mechanism, point by point; if there are several, all of them.
5. **Recipe**: what to do, step by step; short code (5–20 lines), only the essence.
6. **How to test**: how to reproduce, and how to make a red check.
7. **Review checklist**: short `- [ ]` items.
8. **Seen in**: links to public issues, PRs, commits, docs; own cases and others'.
9. **Open questions**: what is not verified.

## Public

The repository is public. An article contains no:

- keys of internal trackers (Jira and the like), internal addresses, host names, paths on work machines;
- names of customers or people, code or logs from closed repositories;
- tokens, passwords, internal configuration.

Instead, link a public PR or commit if there is one, or retell the case without tying it to the project. If an
example cannot be shown, write a minimal one of your own.

## Links and others' code

- Every claim about someone else's behaviour (a C runtime, a VM, an OS) links to a primary source: the source code,
  docs, an issue. Mark what was not verified as a hypothesis.
- Do not copy others' code wholesale: link the line in the repository (a commit rather than a branch) and retell it; a
  quote is short, in quotation marks, with the source.
- An example from an open-source project: the project, a link, 2–3 sentences: the symptom, the cause, the fix.

## Style

- Terms and identifiers as in the code (`atexit`, `DLL_PROCESS_DETACH`).
- Short and to the point: lists rather than paragraphs, no story of how the bug was hunted.
- Markdown without HTML; lines up to 120 characters; code blocks with a language (` ```cpp `).
- When you update an article, change its "Updated" date in every language.

## License

By contributing you agree that your contribution, including translations, is licensed under [CC BY 4.0](LICENSE).
