#!/usr/bin/env python3
"""
quantitative_analysis.py

Counts how many times each PLAYER exhibited each SOCIAL DYNAMIC
by scanning analysis JSONs produced by card_sort.py (files like *.social.json).

Attribution:
- For each finding in report["found"]:
  - If its label OR parent_label matches a requested dynamic,
    we try to attribute the finding to player(s) by inspecting each span:
      • primary: spans[].quote   (robust name detection, not just "Name:")
      • fallback: spans[].where  (same detection)
  - We credit each player at most ONCE per finding per dynamic.

Run examples:

  # interactive names & dynamics prompts; default dir "analyses"
  python3 quantitative_analysis.py

  # explicit lists
  python3 quantitative_analysis.py \
    --records-dir analyses --glob "*.social.json" \
    --names "Sarah, Anika, Derek" \
    --dynamics "persuasion, framing_or_spin, deception"

  # multiple input dirs, recursive search, CSV audit
  python3 quantitative_analysis.py \
    --records-dir analyses --records-dir game_records/analyses \
    --recursive --emit-attributions analyses/attributions.csv \
    --names-file names.txt --dynamics-file dynamics.txt

Notes:
- Dynamics are matched case-insensitively against both label and parent_label,
  normalized by lowercasing and replacing spaces with underscores.
- Use --strict to require an explicit "Name:"-style prefix; default is lenient.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

# --------------------------- Input utils ---------------------------

def _split_csv(s: str) -> List[str]:
    return [x.strip() for x in s.split(",") if x.strip()]

def _load_list_file(path: Optional[str]) -> List[str]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        print(f"[warn] list file not found: {p}", file=sys.stderr)
        return []
    return [line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]

def _ensure_list(name: str, provided: List[str]) -> List[str]:
    if provided:
        return provided
    try:
        val = input(f"Enter comma-separated {name}: ").strip()
    except EOFError:
        val = ""
    items = _split_csv(val)
    if not items:
        print(f"[error] No {name} provided.", file=sys.stderr)
        sys.exit(2)
    return items

# --------------------------- Name handling ---------------------------

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip()).lower()

def _alias_set(name: str) -> Set[str]:
    """
    Build a small set of aliases for a player:
      - full name
      - first token (e.g., "Sarah" from "Sarah R.")
      - first+last initial (e.g., "Sarah R")
      - without dots/hyphens
    """
    base = name.strip()
    tokens = [t for t in re.split(r"\s+", base) if t]
    aliases = {base, base.replace(".", ""), base.replace("-", " ")}
    if tokens:
        first = tokens[0]
        aliases.add(first)
        if len(tokens) >= 2:
            last = tokens[-1]
            last_initial = re.sub(r"[^\w]", "", last[:1])
            aliases.add(f"{first} {last_initial}")
            aliases.add(f"{first}{last_initial}")
    # normalized lowercase variants
    aliases |= {_norm(a) for a in list(aliases)}
    return aliases

def build_candidate_map(names: List[str]) -> Tuple[Dict[str, str], Dict[str, Set[str]]]:
    """
    Returns:
      - canonical map lowercased name -> canonical name
      - alias map canonical name -> set of lowercase aliases
    """
    canon_map: Dict[str, str] = {}
    alias_map: Dict[str, Set[str]] = {}
    for n in names:
        canon = re.sub(r"\s+", " ", n.strip())
        if not canon:
            continue
        lc = _norm(canon)
        if lc not in canon_map:
            canon_map[lc] = canon
            alias_map[canon] = set()
            for a in _alias_set(canon):
                alias_map[canon].add(_norm(a))
    return canon_map, alias_map

# --------------------------- Dynamics handling ---------------------------

def normalize_dynamic(d: str) -> str:
    return d.strip().lower().replace(" ", "_")

# --------------------------- Speaker detection ---------------------------

# Strict "Name:" at start, allowing bullets/spaces:  - Name: text
STRICT_PREFIX_RE = re.compile(r"^\s*[-–•]?\s*([A-Za-z][A-Za-z0-9_. \-]{0,40})\s*[:：]\s")

def detect_speakers(text: str,
                    canon_map: Dict[str, str],
                    alias_map: Dict[str, Set[str]],
                    strict: bool = False) -> Set[str]:
    """
    Returns set of canonical player names detected in text.
    - strict=True: require "Name:" style prefix on first line
    - strict=False: also allow "Name —", "[Name]" or loose presence near start
    """
    if not text:
        return set()

    lines = text.splitlines()
    first = lines[0].strip()

    detected: Set[str] = set()

    # 1) Strict "Name:" on first line
    m = STRICT_PREFIX_RE.match(first)
    if m:
        raw = _norm(m.group(1))
        # exact lowercase match
        if raw in canon_map:
            detected.add(canon_map[raw])
            return detected  # unambiguous, return early
        # try to match any alias buckets
        for canon, aliases in alias_map.items():
            if raw in aliases:
                detected.add(canon)
                return detected

    if strict:
        return detected

    # 2) Semi-structured: "Name —" or "Name -"
    semi = re.match(r"^\s*[-–•]?\s*([A-Za-z][A-Za-z0-9_. \-]{0,40})\s*[–—-]\s+", first)
    if semi:
        raw = _norm(semi.group(1))
        if raw in canon_map:
            detected.add(canon_map[raw])
            return detected
        for canon, aliases in alias_map.items():
            if raw in aliases:
                detected.add(canon)
                return detected

    # 3) Bracketed "[Name]" at start
    br = re.match(r"^\s*\[([A-Za-z][A-Za-z0-9_. \-]{0,40})\]\s*", first)
    if br:
        raw = _norm(br.group(1))
        if raw in canon_map:
            detected.add(canon_map[raw])
            return detected
        for canon, aliases in alias_map.items():
            if raw in aliases:
                detected.add(canon)
                return detected

    # 4) Lenient: scan first ~40 chars for any alias token (avoid false matches later in text)
    head = first[:40].lower()
    for canon, aliases in alias_map.items():
        for a in aliases:
            a_clean = a.strip()
            if not a_clean:
                continue
            # word boundary-ish match
            if re.search(rf"\b{re.escape(a_clean)}\b", head):
                detected.add(canon)
                break

    return detected

# --------------------------- Counting core ---------------------------

def collect_counts(
    records_dirs: List[Path],
    glob_pat: str,
    target_names: List[str],
    target_dynamics: List[str],
    include_parent_label: bool,
    strict_names: bool,
    recursive: bool,
    debug: bool = False,
    emit_attrib_csv: Optional[Path] = None
) -> Tuple[Dict[Tuple[str, str], int], List[str], List[str], int]:
    """
    Walk *.social.json and count occurrences.
    Returns:
      counts[(name, dynamic)],
      canonical names in display order,
      canonical dynamics in display order,
      files_scanned
    """

    # Canonical names, maps, and alias buckets
    canonical_names: List[str] = []
    canon_map, alias_map = build_candidate_map(target_names)
    for lc, canon in canon_map.items():
        canonical_names.append(canon)
    canonical_names.sort(key=lambda s: s.lower())

    # Canonical dynamics
    dyns = [normalize_dynamic(d) for d in target_dynamics if d.strip()]
    # de-dup preserving order
    seen = set()
    canonical_dynamics: List[str] = []
    for d in dyns:
        if d not in seen:
            canonical_dynamics.append(d)
            seen.add(d)

    counts: Dict[Tuple[str, str], int] = {}
    files_scanned = 0

    # optional attribution audit
    attrib_lines: List[str] = []
    if emit_attrib_csv:
        attrib_lines.append("file,dynamic,name,phrase,evidence")

    # Gather files
    files: List[Path] = []
    for d in records_dirs:
        if recursive:
            files.extend(sorted(d.rglob(glob_pat)))
        else:
            files.extend(sorted(d.glob(glob_pat)))

    for fp in files:
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[warn] skip unreadable: {fp} ({e})", file=sys.stderr)
            continue

        if not isinstance(data, dict) or not isinstance(data.get("found"), list):
            # Not a social.json report
            continue

        files_scanned += 1
        findings: List[dict] = data["found"]

        for item in findings:
            # which dynamics does this finding match?
            labs: Set[str] = set()
            lab = normalize_dynamic(str(item.get("label", "")))
            if lab:
                labs.add(lab)
            if include_parent_label:
                parent = normalize_dynamic(str(item.get("parent_label", "")))
                if parent:
                    labs.add(parent)

            matched_dyns = [d for d in canonical_dynamics if d in labs]
            if not matched_dyns:
                continue

            spans = item.get("spans") or []
            if not isinstance(spans, list) or not spans:
                continue

            # attribute speakers (dedup per finding)
            speakers_for_finding: Set[str] = set()

            for sp in spans:
                quote = str(sp.get("quote", "") or "")
                where = str(sp.get("where", "") or "")

                # Try quote first, then where
                found = detect_speakers(quote, canon_map, alias_map, strict=strict_names)
                if not found and where:
                    found = detect_speakers(where, canon_map, alias_map, strict=strict_names)

                speakers_for_finding |= found

            if not speakers_for_finding:
                if debug:
                    print(f"[debug] No speaker match in {fp.name} for labs={labs}", file=sys.stderr)
                continue

            phrase = (item.get("phrase") or "").replace(",", ";")
            # credit each speaker once per matched dynamic
            for spk in speakers_for_finding:
                for dyn in matched_dyns:
                    counts[(spk, dyn)] = counts.get((spk, dyn), 0) + 1
                    if emit_attrib_csv:
                        # Evidence: prefer first span quote that mentioned this speaker
                        ev = ""
                        for sp in spans:
                            q = str(sp.get("quote", "") or "")
                            w = str(sp.get("where", "") or "")
                            if spk in detect_speakers(q, canon_map, alias_map, strict=strict_names) or \
                               (w and spk in detect_speakers(w, canon_map, alias_map, strict=strict_names)):
                                ev = (q or w).replace("\n", " ").replace(",", ";")
                                break
                        attrib_lines.append(f"{fp.name},{dyn},{spk},{phrase},{ev}")

    # write audit if requested
    if emit_attrib_csv:
        emit_attrib_csv.parent.mkdir(parents=True, exist_ok=True)
        emit_attrib_csv.write_text("\n".join(attrib_lines) + "\n", encoding="utf-8")
        print(f"[saved] attribution audit -> {emit_attrib_csv}")

    return counts, canonical_names, canonical_dynamics, files_scanned

# --------------------------- Output ---------------------------

def print_table(counts: Dict[Tuple[str, str], int], names: List[str], dynamics: List[str]) -> None:
    name_w = max(8, max((len(n) for n in names), default=0))
    dyn_w = [max(5, len(d)) for d in dynamics]

    header = ["Name".ljust(name_w)] + [d.rjust(w) for d, w in zip(dynamics, dyn_w)] + [" Total".rjust(7)]
    line_w = sum(len(h) for h in header) + 3 * (len(header) - 1)

    print(" | ".join(header))
    print("-" * line_w)

    for n in names:
        row = [n.ljust(name_w)]
        total = 0
        for d, w in zip(dynamics, dyn_w):
            v = counts.get((n, d), 0)
            total += v
            row.append(str(v).rjust(w))
        row.append(str(total).rjust(7))
        print(" | ".join(row))

    # column totals
    col_totals = []
    grand = 0
    for d in dynamics:
        t = sum(counts.get((n, d), 0) for n in names)
        grand += t
        col_totals.append(t)
    print("-" * line_w)
    footer = ["TOTAL".ljust(name_w)] + [str(t).rjust(w) for t, w in zip(col_totals, dyn_w)] + [str(grand).rjust(7)]
    print(" | ".join(footer))

def write_csv(counts: Dict[Tuple[str, str], int], names: List[str], dynamics: List[str], csv_path: Path) -> None:
    lines = []
    header = ["name"] + dynamics + ["total"]
    lines.append(",".join(header))
    for n in names:
        row = [n]
        total = 0
        for d in dynamics:
            v = counts.get((n, d), 0)
            total += v
            row.append(str(v))
        row.append(str(total))
        lines.append(",".join(row))
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[saved] CSV -> {csv_path}")

# --------------------------- CLI ---------------------------

def main():
    ap = argparse.ArgumentParser(description="Quantify social dynamics per player from *.social.json reports.")
    ap.add_argument("--records-dir", action="append", default=["analyses"],
                    help="Directory containing *.social.json; can be used multiple times")
    ap.add_argument("--glob", default="*.social.json", help="Glob pattern (default: *.social.json)")
    ap.add_argument("--recursive", action="store_true", help="Search directories recursively")
    ap.add_argument("--names", default=None, help="Comma-separated player names")
    ap.add_argument("--dynamics", default=None, help="Comma-separated dynamics (labels)")
    ap.add_argument("--names-file", default=None, help="File with one player name per line")
    ap.add_argument("--dynamics-file", default=None, help="File with one dynamic per line")
    ap.add_argument("--no-parent", action="store_true", help="Do NOT match parent_label (only label)")
    ap.add_argument("--strict", action="store_true", help="Require strict 'Name:' prefix in evidence")
    ap.add_argument("--debug", action="store_true", help="Print attribution misses")
    ap.add_argument("--out-csv", default="analyses/quant_summary.csv",
                help="Save summary CSV (default: analyses/quant_summary.csv)")
    ap.add_argument("--emit-attributions", default=None, help="Also save a per-attribution audit CSV here")
    args = ap.parse_args()
    args.out_csv = str(Path(args.out_csv).expanduser().resolve())

    # Build names list
    names = []
    names += _load_list_file(args.names_file)
    if args.names:
        names += _split_csv(args.names)
    names = _ensure_list("player names", names)

    # Build dynamics list
    dynamics = []
    dynamics += _load_list_file(args.dynamics_file)
    if args.dynamics:
        dynamics += _split_csv(args.dynamics)
    dynamics = _ensure_list("social dynamics (labels)", dynamics)

    dirs = [Path(d) for d in args.records_dir]

    attrib_csv = Path(args.emit_attributions) if args.emit_attributions else None

    counts, canon_names, canon_dynamics, scanned = collect_counts(
        records_dirs=dirs,
        glob_pat=args.glob,
        target_names=names,
        target_dynamics=dynamics,
        include_parent_label=(not args.no_parent),
        strict_names=args.strict,
        recursive=args.recursive,
        debug=args.debug,
        emit_attrib_csv=attrib_csv
    )

    if scanned == 0:
        print(f"[warn] No analysis files matched these inputs.")
        for d in dirs:
            print(f"  - {d}/{args.glob}{' (recursive)' if args.recursive else ''}")
        print("Hint: your outputs might be in game_records/analyses; try:")
        print("  --records-dir game_records/analyses")
        sys.exit(1)

    print_table(counts, canon_names, canon_dynamics)

    if args.out_csv:
        write_csv(counts, canon_names, canon_dynamics, Path(args.out_csv))

if __name__ == "__main__":
    main()
