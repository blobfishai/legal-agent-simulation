#!/usr/bin/env python3
"""Seeded entity mutation for Harvey LAB tasks.

Produces structurally identical variants of a LAB task by consistently
substituting named entities (companies, people, places, acronyms, domains)
across every document (.docx/.xlsx/.eml/.txt) and the task.json itself,
while leaving all numbers, dates, and defined terms untouched so the
grading rubric's arithmetic still holds.

The substitution map is derived deterministically from --seed, so the same
seed always yields the same variant. Entities are declared per task in an
entities.json config:

    [
      {"type": "company", "name": "Cascade Millworks",
       "fragments": ["Cascade", "Millworks"], "domain": "cascademillworks.com"},
      {"type": "acronym_company", "name": "Pacific Coast Timber Holdings",
       "acronym": "PCTH", "fragments": ["Pacific Coast Timber"],
       "domain": "pacificcoasttimber.com"},
      {"type": "person", "name": "Margaret Yun"},
      {"type": "place", "name": "Oregon"}
    ]

DOCX handling works on the raw OOXML XML of every w:t-bearing part
(document, headers, footers, footnotes, endnotes, comments): text is
replaced inside <w:t> spans; if an entity is split across runs, the
affected paragraph's runs are merged (text moved into the first run) —
formatting boundaries collapse only in paragraphs that actually changed.
All other zip members are copied byte-identical.

Usage:
    python3 research/lab_mutate.py \
        --task banking-finance/identify-issues-in-compliance-certificate \
        --entities research/mutation-configs/<task>/entities.json \
        --seed 1 --out research/mutations
"""
from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "research" / "repos" / "harveyai@harvey-labs"

# Name banks for deterministic replacement generation. Synthetic only, per
# harvey-labs CONTRIBUTING.md ground rules.
COMPANY_HEADS = [
    "Juniper", "Blue Ridge", "Silverbirch", "Kestrel", "Alderpoint",
    "Stonegate", "Hollis", "Merribrook", "Larchmont", "Douglas Fork",
    "Timberline", "Oakhaven", "Redcedar", "Granite Bay", "Wolfcreek",
]
COMPANY_TAILS = {
    "company": ["Sawmills", "Forest Products", "Woodworks", "Timberworks", "Millcraft"],
    "holdings": ["Capital Holdings", "Timber Holdings", "Resource Holdings", "Industrial Holdings"],
    "partners": ["Partners", "Equity Partners", "Growth Partners", "Capital Partners"],
    "target": ["Lumber Co", "Plywood Co", "Veneer Co", "Panel Co"],
    "accounting": ["Accounting Group", "Audit Group"],
    "advisory": ["Advisory", "Advisors"],
    "products": ["Panel Products", "Board Products", "Timber Products"],
}
FIRST_NAMES_F = ["Alicia", "Priya", "Carmen", "Ingrid", "Elena", "Naomi", "Fatima", "Mireille"]
FIRST_NAMES_M = ["Marcus", "Theo", "Rashid", "Victor", "Owen", "Daniel", "Anders"]
LAST_NAMES = [
    "Calloway", "Bram", "Osei", "Lindqvist", "Marchetti", "Duval",
    "Hartwell", "Nakata", "Reyes", "Kovacs", "Whitcombe", "Ferro",
]
PLACES = ["Washington", "Idaho", "Montana", "Vermont", "Maine", "Georgia"]


def kebab(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def squash(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def acronym_of(s: str) -> str:
    return "".join(w[0] for w in s.split() if w[0].isupper()).upper()


def _pick(rng: random.Random, bank: list[str], used: set[str]) -> str:
    choices = [b for b in bank if b not in used]
    if not choices:
        raise SystemExit("name bank exhausted; extend the banks")
    choice = rng.choice(choices)
    used.add(choice)
    return choice


def build_replacement_map(entities: list[dict], seed: int,
                          corpus_text: str = "") -> list[tuple[str, str]]:
    """Return substitution pairs, longest source first.

    Bank entries whose distinctive words already occur in the source corpus
    are banned, so a replacement can never collide with (or merge into) an
    entity that exists in the original documents.
    """
    rng = random.Random(f"lab-mutate-v1:{seed}")
    corpus_words = set(re.findall(r"[a-z0-9]+", corpus_text.lower()))

    def clean(bank: list[str]) -> list[str]:
        return [b for b in bank
                if not any(w.lower() in corpus_words for w in b.split() if len(w) > 3)]

    heads, firsts_f, firsts_m, lasts, places = (
        clean(COMPANY_HEADS), clean(FIRST_NAMES_F), clean(FIRST_NAMES_M),
        clean(LAST_NAMES), clean(PLACES))
    used: set[str] = set()
    pairs: list[tuple[str, str]] = []

    for ent in entities:
        etype = ent["type"]
        old = ent["name"]
        if etype in ("company", "acronym_company"):
            role = ent.get("role", "company")
            if role == "lawfirm":
                # Law firms read as surname pairs, not "<Head> <PE-style tail>".
                new = f"{_pick(rng, lasts, used)} {_pick(rng, lasts, used)}"
            else:
                head = _pick(rng, heads, used)
                # Guard against doubled words like "Timberline Timber Holdings".
                tails = [t for t in COMPANY_TAILS[role]
                         if t.split()[0].lower() != head.split()[-1].lower()]
                new = f"{head} {rng.choice(tails or COMPANY_TAILS[role])}"
            pairs.append((old, new))
            old_words, new_words = old.split(), new.split()
            # Shortened compound forms: map every multi-word prefix of the old
            # name to the aligned prefix of the new name, so prose like
            # "Whitfield Lumber" tracks the renamed "<X> Plywood Co" correctly.
            for k in range(2, len(old_words)):
                keep = len(new_words) - (len(old_words) - k)
                pairs.append((" ".join(old_words[:k]),
                              " ".join(new_words[: max(1, keep)])))
            for frag in ent.get("fragments", []):
                if frag == old:
                    continue
                frag_words = frag.split()
                if old_words[: len(frag_words)] == frag_words:
                    keep = len(new_words) - (len(old_words) - len(frag_words))
                    nfrag = " ".join(new_words[: max(1, keep)])
                elif old_words[-len(frag_words):] == frag_words:
                    keep = len(new_words) - (len(old_words) - len(frag_words))
                    nfrag = " ".join(new_words[-max(1, keep):])
                else:
                    raise SystemExit(f"fragment {frag!r} is not a prefix/suffix of {old!r}")
                pairs.append((frag, nfrag))
            if etype == "acronym_company":
                pairs.append((ent["acronym"], acronym_of(new)))
            if ent.get("domain"):
                pairs.append((ent["domain"], squash(new) + ".com"))
        elif etype == "person":
            first, last = old.split(" ", 1)
            # Pronoun-aware: surviving "her"/"his" in prose must still fit.
            pron = ent.get("pronouns")
            bank = (firsts_f if pron == "she"
                    else firsts_m if pron == "he"
                    else firsts_f + firsts_m)
            nfirst = _pick(rng, bank, used)
            nlast = _pick(rng, lasts, used)
            pairs.append((old, f"{nfirst} {nlast}"))
            pairs.append((first, nfirst))
            pairs.append((last, nlast))
            # email local part: first-initial + last, e.g. myun -> acalloway
            pairs.append(((first[0] + last).lower(), (nfirst[0] + nlast).lower()))
        elif etype == "place":
            pairs.append((old, _pick(rng, places, used)))
        else:
            raise SystemExit(f"unknown entity type: {etype}")

    # Derived case variants for every pair, then sort longest-first so
    # "Cascade Millworks" wins before bare "Cascade".
    expanded: dict[str, str] = {}
    for old, new in pairs:
        for o, n in ((old, new), (old.lower(), new.lower()),
                     (old.upper(), new.upper()), (kebab(old), kebab(new)),
                     (squash(old), squash(new))):
            expanded.setdefault(o, n)
    return sorted(expanded.items(), key=lambda kv: -len(kv[0]))


def replace_text(text: str, pairs: list[tuple[str, str]]) -> str:
    # Alphanumeric-boundary replacement: "Yun" must not match inside
    # "Yunnan", but "cascademillworks" must still match in
    # "cascademillworks.com" and kebab forms inside longer file names.
    for old, new in pairs:
        if old in text:
            text = re.sub(
                r"(?<![A-Za-z0-9])" + re.escape(old) + r"(?![A-Za-z0-9])",
                new.replace("\\", r"\\"), text)
    return text


WT_RE = re.compile(r"(<w:t(?:\s[^>]*)?>)(.*?)(</w:t>)", re.DOTALL)
WP_RE = re.compile(r"<w:p[ >].*?</w:p>", re.DOTALL)


def xml_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def xml_unescape(s: str) -> str:
    return (s.replace("&lt;", "<").replace("&gt;", ">")
             .replace("&quot;", '"').replace("&apos;", "'").replace("&amp;", "&"))


def mutate_docx_xml(xml: str, pairs: list[tuple[str, str]]) -> str:
    # Pass 1: replace within individual <w:t> spans.
    def sub_wt(m: re.Match) -> str:
        inner = xml_unescape(m.group(2))
        return m.group(1) + xml_escape(replace_text(inner, pairs)) + m.group(3)

    xml = WT_RE.sub(sub_wt, xml)

    # Pass 2: entities split across runs — merge the paragraph's run text.
    def fix_paragraph(m: re.Match) -> str:
        para = m.group(0)
        wts = WT_RE.findall(para)
        joined = "".join(xml_unescape(t[1]) for t in wts)
        replaced = replace_text(joined, pairs)
        if replaced == joined:
            return para
        first = True

        def redistribute(mm: re.Match) -> str:
            nonlocal first
            if first:
                first = False
                open_tag = mm.group(1)
                if 'xml:space' not in open_tag:
                    open_tag = open_tag[:-1] + ' xml:space="preserve">'
                return open_tag + xml_escape(replaced) + mm.group(3)
            return mm.group(1) + mm.group(3)

        return WT_RE.sub(redistribute, para)

    return WP_RE.sub(fix_paragraph, xml)


def mutate_docx(src: Path, dst: Path, pairs: list[tuple[str, str]]) -> None:
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if re.fullmatch(r"word/(document|header\d*|footer\d*|footnotes|endnotes|comments)\.xml",
                            info.filename):
                data = mutate_docx_xml(data.decode("utf-8"), pairs).encode("utf-8")
            zout.writestr(info, data)


def mutate_xlsx(src: Path, dst: Path, pairs: list[tuple[str, str]]) -> None:
    import openpyxl

    wb = openpyxl.load_workbook(src)
    for ws in wb.worksheets:
        new_title = replace_text(ws.title, pairs)
        if new_title != ws.title:
            ws.title = new_title
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str):
                    replaced = replace_text(cell.value, pairs)
                    if replaced != cell.value:
                        cell.value = replaced
    wb.save(dst)


def mutate_plain(src: Path, dst: Path, pairs: list[tuple[str, str]]) -> None:
    dst.write_text(replace_text(src.read_text(encoding="utf-8", errors="replace"), pairs),
                   encoding="utf-8")


def mutate_eml(src: Path, dst: Path, pairs: list[tuple[str, str]]) -> None:
    # Bodies are quoted-printable: raw text replacement would miss entities
    # split by soft line breaks, so decode -> replace -> re-encode.
    from email import message_from_binary_file, policy

    with src.open("rb") as fh:
        msg = message_from_binary_file(fh, policy=policy.default)
    for header in ("From", "To", "Cc", "Bcc", "Subject"):
        if msg[header]:
            msg.replace_header(header, replace_text(str(msg[header]), pairs))
    for part in msg.walk():
        if part.get_content_maintype() == "text":
            part.set_content(replace_text(part.get_content(), pairs),
                             subtype=part.get_content_subtype())
    dst.write_bytes(msg.as_bytes())


def extract_all_text(path: Path) -> str:
    """Best-effort text of any produced file, for residual scanning."""
    ext = path.suffix.lower()
    if ext == ".docx":
        chunks = []
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if name.endswith(".xml"):
                    chunks.append(re.sub(r"<[^>]+>", " ", z.read(name).decode("utf-8", "replace")))
        return xml_unescape(" ".join(chunks))
    if ext == ".xlsx":
        import openpyxl
        wb = openpyxl.load_workbook(path)
        vals = [ws.title for ws in wb.worksheets]
        for ws in wb.worksheets:
            for row in ws.iter_rows():
                vals.extend(str(c.value) for c in row if c.value is not None)
        return "\n".join(vals)
    if ext == ".eml":
        from email import message_from_binary_file, policy
        with path.open("rb") as fh:
            msg = message_from_binary_file(fh, policy=policy.default)
        chunks = [f"{k}: {v}" for k, v in msg.items()]
        chunks.extend(part.get_content() for part in msg.walk()
                      if part.get_content_maintype() == "text")
        return "\n".join(chunks)
    return path.read_text(encoding="utf-8", errors="replace")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True, help="area/slug relative to LAB tasks/")
    ap.add_argument("--entities", required=True, type=Path)
    ap.add_argument("--seed", required=True, type=int)
    ap.add_argument("--out", type=Path, default=ROOT / "research" / "mutations")
    args = ap.parse_args()

    task_dir = LAB / "tasks" / args.task
    task_json = task_dir / "task.json"
    if not task_json.is_file():
        raise SystemExit(f"no task.json at {task_json}")

    entities = json.loads(args.entities.read_text())
    docs = sorted(p for p in (task_dir / "documents").rglob("*") if p.is_file())
    corpus_text = "\n".join([task_json.read_text(encoding="utf-8")]
                            + [extract_all_text(p) for p in docs])
    pairs = build_replacement_map(entities, args.seed, corpus_text)

    out_dir = args.out / f"{args.task}__seed-{args.seed:03d}"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    (out_dir / "documents").mkdir(parents=True)

    # 1. task.json: substitute across every string value.
    task = json.loads(replace_text(task_json.read_text(encoding="utf-8"), pairs))
    task.setdefault("provenance", {})
    task["provenance"] = {
        "mutated_from": args.task,
        "mutation_seed": args.seed,
        "mutation_tool": "research/lab_mutate.py v1",
        "entity_count": len(entities),
    }
    (out_dir / "task.json").write_text(json.dumps(task, indent=2, ensure_ascii=False) + "\n",
                                       encoding="utf-8")

    # 2. documents: mutate by type, renaming files whose names carry entities.
    for src in docs:
        rel = src.relative_to(task_dir / "documents")
        rel = Path(*[replace_text(part, pairs) for part in rel.parts])
        dst = out_dir / "documents" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        ext = src.suffix.lower()
        if ext == ".docx":
            mutate_docx(src, dst, pairs)
        elif ext == ".xlsx":
            mutate_xlsx(src, dst, pairs)
        elif ext == ".eml":
            mutate_eml(src, dst, pairs)
        elif ext in (".txt", ".md", ".json"):
            mutate_plain(src, dst, pairs)
        else:
            shutil.copy2(src, dst)

    # 3. Validation: zero residual source-entity mentions anywhere in output.
    residual_terms = [old for old, _ in pairs if len(old) >= 4]
    problems: list[str] = []
    outputs = [out_dir / "task.json"] + sorted(
        p for p in (out_dir / "documents").rglob("*") if p.is_file())
    for path in outputs:
        text = extract_all_text(path).lower()
        for term in residual_terms:
            if term.lower() in text:
                problems.append(f"{path.relative_to(out_dir)}: residual '{term}'")
    # structural parity
    if len(outputs) - 1 != len(docs):
        problems.append(f"file count changed: {len(docs)} -> {len(outputs) - 1}")

    manifest = {
        "task": args.task,
        "seed": args.seed,
        "substitutions": dict(pairs),
        "files": [str(p.relative_to(out_dir)) for p in outputs],
        "problems": problems,
    }
    (out_dir / "mutation-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"wrote {out_dir} ({len(outputs)} files)")
    for old, new in pairs:
        print(f"  {old!r} -> {new!r}")
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print(" ", p)
        return 1
    print("validation: zero residual entity mentions; file count preserved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
