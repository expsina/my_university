#!/usr/bin/env python3
"""
Сборка практической работы: markdown -> docx с титульным листом.

Тело документа собирает pandoc, титульник заполняется из title_template.docx
(поля вида {{ topic }}) и вставляется первой страницей.

Данные титульника собираются из нескольких источников (поздний важнее раннего):
  1. titlepage.yaml рядом со скриптом          (общее: институт, кафедра, группа)
  2. titlepage.yaml в папках выше документа    (на курс: дисциплина, преподаватель)
  3. блок titlepage в YAML-шапке самого .md    (на работу)
Номер работы, если не задан, берётся из имени файла (pr3.md -> 3), год - текущий.

    python3 build_pr.py pr3.md                 # -> pr3.docx
    python3 build_pr.py pr3.md -o out.docx
    python3 build_pr.py pr3.md --no-title

Нужно: pip install docxtpl docxcompose pyyaml
Файлы reference.docx, gost.lua, title_template.docx, titlepage.yaml ищутся рядом со скриптом.
"""
import argparse
import datetime
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docxcompose.composer import Composer
from docxtpl import DocxTemplate

HERE = Path(__file__).resolve().parent
REFERENCE = HERE / "reference.docx"
LUA = HERE / "gost.lua"
TEMPLATE = HERE / "title_template.docx"
CONFIG_NAME = "titlepage.yaml"
STYLE_PREFIX = "TP"   # префикс стилей титульника, чтобы они не мешали основному тексту

def load_yaml(path: Path) -> dict:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as e:
        print(f"Не удалось прочитать {path}: {e}", file=sys.stderr)
        return {}


def read_frontmatter_titlepage(md_path: Path) -> dict:
    text = md_path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n(?:---|\.\.\.)\s*\n", text, re.S)
    if not m:
        return {}
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        sys.exit(f"Ошибка в YAML-шапке {md_path.name}: {e}")
    return dict(meta.get("titlepage") or {})


def collect_context(md_path: Path) -> tuple[dict, bool]:
    """Возвращает (контекст, есть_ли_вообще_данные_для_титульника)."""
    ctx: dict = {}
    sources = []
    base = HERE / CONFIG_NAME
    if base.exists():
        sources.append(base)
    # папки выше документа: от самой дальней к ближайшей
    seen = {base.resolve()} if base.exists() else set()
    chain = []
    for d in md_path.parent.parents:
        f = d / CONFIG_NAME
        if f.exists() and f.resolve() not in seen:
            chain.append(f)
            seen.add(f.resolve())
    own = md_path.parent / CONFIG_NAME
    if own.exists() and own.resolve() not in seen:
        chain.insert(0, own)
    sources += list(reversed(chain))
    for f in sources:
        ctx.update(load_yaml(f))
    front = read_frontmatter_titlepage(md_path)
    ctx.update(front)
    ctx.setdefault("year", datetime.date.today().year)
    if "number" not in ctx:
        m = re.search(r"(\d+)", md_path.stem)
        if m:
            ctx["number"] = int(m.group(1))
    return ctx, bool(front or sources)


def run_pandoc(md_path: Path, out_path: Path) -> None:
    text = md_path.read_text(encoding="utf-8")
    cmd = ["pandoc", md_path.name]
    # mermaid-filter должен идти ДО lua-фильтра
    if re.search(r"```\s*\{?\.?mermaid", text):
        if not shutil.which("mermaid-filter"):
            sys.exit("В документе есть mermaid, но mermaid-filter не найден.")
        cmd += ["-F", "mermaid-filter"]
    if LUA.exists():
        cmd += ["--lua-filter", str(LUA)]
    if REFERENCE.exists():
        cmd += ["--reference-doc", str(REFERENCE)]
    cmd += ["-o", str(out_path)]
    # cwd = папка документа, чтобы относительные пути к картинкам работали
    subprocess.run(cmd, check=True, cwd=md_path.parent)


def fill_title(context: dict, out_path: Path) -> None:
    if not TEMPLATE.exists():
        sys.exit(f"Нет шаблона титульника: {TEMPLATE}")
    tpl = DocxTemplate(str(TEMPLATE))
    missing = sorted(tpl.get_undeclared_template_variables() - set(context))
    if missing:
        print("Внимание: не заданы поля титульника: " + ", ".join(missing),
              file=sys.stderr)
    tpl.render(context, autoescape=True)
    tpl.save(str(out_path))


def isolate_styles(doc: Document) -> None:
    """Делает стили титульника независимыми: переименовывает их с префиксом и
    убирает признак «по умолчанию», чтобы при склейке они не затронули стили
    основного текста (Normal, Heading 1 и т.д.)."""
    styles_el = doc.styles.element
    body = doc.element.body
    by_id = {st.get(qn("w:styleId")): st for st in styles_el.findall(qn("w:style"))}

    used = {el.get(qn("w:val")) for tag in ("w:pStyle", "w:rStyle", "w:tblStyle")
            for el in body.iter(qn(tag))}
    default_ids = {}
    for sid, st in by_id.items():
        if st.get(qn("w:default")) == "1":
            default_ids[st.get(qn("w:type"))] = sid
    used |= set(default_ids.values())

    keep, todo = set(), list(used)
    while todo:
        sid = todo.pop()
        if sid in keep or sid not in by_id:
            continue
        keep.add(sid)
        for tag in ("w:basedOn", "w:next", "w:link"):
            ref = by_id[sid].find(qn(tag))
            if ref is not None:
                todo.append(ref.get(qn("w:val")))

    for sid, st in by_id.items():
        if sid not in keep:
            styles_el.remove(st)
            continue
        st.set(qn("w:styleId"), STYLE_PREFIX + sid)
        if qn("w:default") in st.attrib:
            del st.attrib[qn("w:default")]
        name = st.find(qn("w:name"))
        if name is not None:
            name.set(qn("w:val"), f"{STYLE_PREFIX} {name.get(qn('w:val'))}")
        for tag in ("w:aliases",):
            for el in st.findall(qn(tag)):
                st.remove(el)
        for tag in ("w:basedOn", "w:next", "w:link"):
            ref = st.find(qn(tag))
            if ref is not None:
                if ref.get(qn("w:val")) in keep:
                    ref.set(qn("w:val"), STYLE_PREFIX + ref.get(qn("w:val")))
                else:
                    st.remove(ref)

    def rename(tag):
        for el in body.iter(qn(tag)):
            el.set(qn("w:val"), STYLE_PREFIX + el.get(qn("w:val")))
    for tag in ("w:pStyle", "w:rStyle", "w:tblStyle"):
        rename(tag)

    # абзацы и таблицы без явного стиля жили на стиле «по умолчанию» титульника
    def ensure(parent_tag, pr_tag, style_tag, type_name, insert_at_start=True):
        sid = default_ids.get(type_name)
        if sid is None or sid not in keep:
            return
        for el in body.iter(qn(parent_tag)):
            pr = el.find(qn(pr_tag))
            if pr is None:
                pr = OxmlElement(pr_tag)
                el.insert(0, pr)
            if pr.find(qn(style_tag)) is None:
                st = OxmlElement(style_tag)
                st.set(qn("w:val"), STYLE_PREFIX + sid)
                pr.insert(0, st)
    ensure("w:p", "w:pPr", "w:pStyle", "paragraph")
    ensure("w:tbl", "w:tblPr", "w:tblStyle", "table")


def set_page_break_before(el) -> bool:
    if el.tag != qn("w:p"):
        return False
    ppr = el.find(qn("w:pPr"))
    if ppr is None:
        ppr = OxmlElement("w:pPr")
        el.insert(0, ppr)
    if ppr.find(qn("w:pageBreakBefore")) is not None:
        return True
    pb = OxmlElement("w:pageBreakBefore")
    idx = 0
    for i, child in enumerate(ppr):
        if child.tag in (qn("w:pStyle"), qn("w:keepNext"), qn("w:keepLines")):
            idx = i + 1
    ppr.insert(idx, pb)
    return True


def merge(title_path: Path, body_path: Path, out_path: Path) -> None:
    """Основной документ остаётся «хозяином» (его стили, поля, нумерация
    страниц); титульник дописывается в конец и переносится в начало."""
    title = Document(str(title_path))
    isolate_styles(title)

    master = Document(str(body_path))
    body_el = master.element.body
    content = lambda: [e for e in body_el if e.tag != qn("w:sectPr")]
    before = content()
    composer = Composer(master)
    composer.append(title)
    new = content()[len(before):]

    def is_blank(e):
        return (e.tag == qn("w:p")
                and not "".join(e.itertext()).strip()
                and e.find(".//" + qn("w:drawing")) is None
                and e.find(".//" + qn("w:pict")) is None
                and e.find(".//" + qn("w:sectPr")) is None)

    # пустые абзацы в конце титульника только вытолкнут разрыв на лишнюю страницу
    while new and is_blank(new[-1]):
        body_el.remove(new.pop())

    if before:
        first = before[0]
        for e in new:
            first.addprevious(e)
        # разрыв страницы - на первом настоящем абзаце основного текста
        # (перед ним pandoc может поставить закладки bookmarkStart)
        target = next((e for e in before if e.tag == qn("w:p")), None)
        if target is not None:
            set_page_break_before(target)
        else:
            br = OxmlElement("w:p")
            r = OxmlElement("w:r")
            b = OxmlElement("w:br")
            b.set(qn("w:type"), "page")
            r.append(b)
            br.append(r)
            first.addprevious(br)

    doc = composer.doc
    # Титульный лист считается первой страницей, но номер на нём не ставится
    doc.sections[0].different_first_page_header_footer = True
    doc.save(str(out_path))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("md", type=Path)
    ap.add_argument("-o", "--output", type=Path)
    ap.add_argument("--no-title", action="store_true", help="собрать без титульника")
    args = ap.parse_args()

    md = args.md.resolve()
    out = (args.output or md.with_suffix(".docx")).resolve()

    with tempfile.TemporaryDirectory() as tmp:
        body = Path(tmp) / "body.docx"
        run_pandoc(md, body)
        context, has_data = collect_context(md)
        if args.no_title or not has_data:
            if not args.no_title:
                print("Нет данных для титульника, собираю без него.", file=sys.stderr)
            shutil.copy(body, out)
        else:
            title = Path(tmp) / "title.docx"
            fill_title(context, title)
            merge(title, body, out)
    print(f"Готово: {out}")


if __name__ == "__main__":
    main()
