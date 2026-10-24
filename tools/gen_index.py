#!/usr/bin/env python3
"""Builds the index in README.md and its translations from the front matter of the articles, and checks the repository.

Usage:
    python3 tools/gen_index.py           # rewrite the index sections of the READMEs
    python3 tools/gen_index.py --check   # fail if an index is stale or a check below fails

Checks: front matter fields, the area folder, translations (all languages, or `translation: pending`), the same area
and tags in every translation, the title equal to the H1, relative links pointing to existing files.

Only the standard library is used. The front matter is a small subset of YAML: `key: value`, `key: [a, b]` and
`key:` followed by `  - item` lines; values may be in double quotes.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"
CONFIG = json.loads((Path(__file__).resolve().parent / "kb.json").read_text(encoding="utf-8"))
MAIN = CONFIG["main_language"]
LANGUAGES = list(CONFIG["languages"])
AREAS = CONFIG["areas"]

INDEX_START = "<!-- index:start -->"
INDEX_END = "<!-- index:end -->"
REQUIRED = ("title", "area", "tags", "symptoms", "updated")
TAG_RE = re.compile(r"^[a-z0-9][a-z0-9+#.-]*$")
UPDATED_RE = re.compile(r"^\d{4}-\d{2}$")
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


@dataclass
class Version:
    path: Path
    lang: str
    meta: dict
    h1: str


@dataclass
class Article:
    area_dir: str
    name: str
    versions: dict = field(default_factory=dict)

    def version(self, lang):
        """The version in `lang`, or the main one, or any one."""
        return self.versions.get(lang) or self.versions.get(MAIN) or next(iter(self.versions.values()))


def unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return json.loads(value)
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    return value


def parse_front_matter(text, errors, where):
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        errors.append(f"{where}: no front matter (the file must start with a '---' line)")
        return {}, text
    try:
        end = lines.index("---", 1)
    except ValueError:
        errors.append(f"{where}: the front matter is not closed with a '---' line")
        return {}, text
    meta = {}
    key = None
    for number, line in enumerate(lines[1:end], start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = re.match(r"^\s+-\s+(.*)$", line)
        if item and key is not None and isinstance(meta[key], list):
            meta[key].append(unquote(item.group(1)))
            continue
        pair = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if not pair:
            errors.append(f"{where}:{number}: cannot parse front matter line: {line!r}")
            continue
        key, value = pair.group(1), pair.group(2).strip()
        if not value:
            meta[key] = []
        elif value.startswith("[") and value.endswith("]"):
            meta[key] = [unquote(v) for v in value[1:-1].split(",") if v.strip()]
        else:
            meta[key] = unquote(value)
    return meta, "\n".join(lines[end + 1:])


def split_name(path):
    """`name.ru.md` -> (`name`, `ru`), `name.md` -> (`name`, main language)."""
    stem = path.name[:-len(".md")]
    base, dot, lang = stem.rpartition(".")
    if dot and lang in LANGUAGES:
        return base, lang
    return stem, MAIN


def load_articles(errors):
    articles = {}
    for path in sorted(ARTICLES.rglob("*.md")):
        where = path.relative_to(ROOT).as_posix()
        relative = path.relative_to(ARTICLES).parts
        if len(relative) != 2:
            errors.append(f"{where}: an article must be at articles/<area>/<name>.md")
            continue
        name, lang = split_name(path)
        text = path.read_text(encoding="utf-8")
        meta, body = parse_front_matter(text, errors, where)
        h1 = next((line[2:].strip() for line in body.splitlines() if line.startswith("# ")), "")
        article = articles.setdefault((relative[0], name), Article(relative[0], name))
        article.versions[lang] = Version(path, lang, meta, h1)
    return list(articles.values())


def check_articles(articles, errors):
    for article in articles:
        for version in article.versions.values():
            where = version.path.relative_to(ROOT).as_posix()
            meta = version.meta
            missing = [key for key in REQUIRED if not meta.get(key)]
            if missing:
                errors.append(f"{where}: missing front matter fields: {', '.join(missing)}")
                continue
            if meta["area"] not in AREAS:
                errors.append(f"{where}: unknown area {meta['area']!r}, known: {', '.join(AREAS)}")
            elif meta["area"] != article.area_dir:
                errors.append(f"{where}: area {meta['area']!r} does not match the folder {article.area_dir!r}")
            if not isinstance(meta["tags"], list) or not isinstance(meta["symptoms"], list):
                errors.append(f"{where}: tags and symptoms must be lists")
                continue
            bad_tags = [tag for tag in meta["tags"] if not TAG_RE.match(tag)]
            if bad_tags:
                errors.append(f"{where}: tags must be lowercase, no spaces: {', '.join(bad_tags)}")
            if not UPDATED_RE.match(meta["updated"]):
                errors.append(f"{where}: updated must be YYYY-MM, not {meta['updated']!r}")
            if version.h1 != meta["title"]:
                errors.append(f"{where}: the H1 {version.h1!r} differs from the title {meta['title']!r}")

        main = article.versions.get(MAIN)
        where = f"articles/{article.area_dir}/{article.name}"
        pending = any(v.meta.get("translation") == "pending" for v in article.versions.values())
        absent = [lang for lang in LANGUAGES if lang not in article.versions]
        if absent and not pending:
            errors.append(f"{where}: no translation into {', '.join(absent)}; translate it or set "
                          f"'translation: pending' in the front matter")
        if main:
            for version in article.versions.values():
                for key in ("area", "tags"):
                    if version.meta.get(key) != main.meta.get(key):
                        errors.append(f"{version.path.relative_to(ROOT).as_posix()}: {key} differs from the "
                                      f"{MAIN} version")


def strip_code(text):
    """Removes fenced code blocks and inline code, so that links in examples are not checked."""
    text = re.sub(r"^(```|~~~).*?^\1", "", text, flags=re.S | re.M)
    return re.sub(r"`[^`\n]*`", "", text)


def check_links(errors):
    for path in sorted(ROOT.rglob("*.md")):
        relative = path.relative_to(ROOT)
        if relative.parts[0].startswith(".") or path.name.startswith("_"):
            continue  # .git, .github; templates hold placeholder links
        for target in LINK_RE.findall(strip_code(path.read_text(encoding="utf-8"))):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("#"):
                continue  # external links and anchors in the same file
            file_part = target.split("#", 1)[0]
            if not (path.parent / file_part).exists():
                errors.append(f"{relative.as_posix()}: broken link {target!r}")


def link(article, lang, readme):
    version = article.version(lang)
    href = version.path.relative_to(readme.parent).as_posix()
    text = f"[{version.meta.get('title', article.name)}]({href})"
    if version.lang != lang:
        text += f" ({version.lang}, {CONFIG['text'][lang]['not_translated']})"
    return text


def sort_key(text):
    return re.sub(r"^[^0-9A-Za-zА-Яа-яЁё]+", "", text).casefold()


def build_index(articles, lang, readme):
    words = CONFIG["text"][lang]
    lines = [f"### {words['by_area']}", ""]
    for area, titles in AREAS.items():
        in_area = [a for a in articles if a.area_dir == area]
        if not in_area:
            continue
        lines += [f"#### {titles[lang]}", ""]
        in_area.sort(key=lambda a: sort_key(a.version(lang).meta.get("title", a.name)))
        lines += [f"- {link(a, lang, readme)}" for a in in_area]
        lines.append("")

    symptoms = sorted(((symptom, a) for a in articles for symptom in a.version(lang).meta.get("symptoms", [])),
                      key=lambda pair: sort_key(pair[0]))
    lines += [f"### {words['by_symptom']}", ""]
    lines += [f"- {symptom} — {link(a, lang, readme)}" for symptom, a in symptoms]
    lines.append("")

    tags = {}
    for article in articles:
        for tag in article.version(lang).meta.get("tags", []):
            tags.setdefault(tag, []).append(article)
    lines += [f"### {words['by_tag']}", ""]
    for tag in sorted(tags):
        lines.append(f"- `{tag}`: " + "; ".join(link(a, lang, readme) for a in tags[tag]))
    return "\n".join(lines).rstrip("\n")


def readme_path(lang):
    return ROOT / ("README.md" if lang == MAIN else f"README.{lang}.md")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="only check, do not write")
    args = parser.parse_args()

    errors = []
    articles = load_articles(errors)
    check_articles(articles, errors)

    for lang in LANGUAGES:
        readme = readme_path(lang)
        if not readme.exists():
            errors.append(f"{readme.name}: missing")
            continue
        text = readme.read_text(encoding="utf-8")
        start, end = text.find(INDEX_START), text.find(INDEX_END)
        if start < 0 or end < start:
            errors.append(f"{readme.name}: no {INDEX_START} ... {INDEX_END} block")
            continue
        updated = (text[:start + len(INDEX_START)] + "\n\n" + build_index(articles, lang, readme) + "\n\n"
                   + text[end:])
        if updated != text:
            if args.check:
                errors.append(f"{readme.name}: the index is stale; run python3 tools/gen_index.py")
            else:
                readme.write_text(updated, encoding="utf-8", newline="\n")
                print(f"updated {readme.name}")

    check_links(errors)

    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
