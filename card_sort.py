#!/usr/bin/env python3
# card_sort.py — BotC-aware analyzer (Qwen via Ollama) with invented-label support
# Run: python3 card_sort.py
"""
Per input file:
- <out-dir>/<file>.social.json   (strict JSON findings)
- <out-dir>/<file>.social.md     (human summary)
- <out-dir>/<file>.raw.txt       (raw model reply)
- <out-dir>/<file>.repair#.raw.txt  (repair attempts, if any)
State (persisted):
- <state>: keeps 'phrases', 'labels' (taxonomy buckets), and 'custom_labels' (invented)
"""

import os, re, json, time, argparse, ast, random
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from llm_client_ollama import LLMClientOllama

# ----------------------- Taxonomy (extended) -----------------------

DEFAULT_TAXONOMY = [
    "persuasion","opinion_leadership","deception","gaslighting",
    "appeal_to_authority","bandwagoning","vote_whipping","coalition_building",
    "threat_or_intimidation","norm_enforcement","framing_or_spin",
    "information_withholding","role_claiming","counter_claiming","tunneling",
    "vote_parking","bussing","pocketing","scapegoating","deflection",
    "straw_manning","appeal_to_emotion","evidence_based_argument",
    "coordination_signaling","hedging","meta_reference","other"
]
ALLOWED_LABELS = set(DEFAULT_TAXONOMY)

# Words/phrases that indicate BOTC roles/mechanics (disallowed as labels)
ROLE_WORDS = {
    "imp","demon","minion","fortune teller","empath","undertaker","slayer","chef",
    "poisoner","monk","ravenkeeper","mayor","butler","village","townsfolk","outsider",
    "execution","nomination","vote count","night kill","policy","red herring"
}

# Heuristic mapper: mechanic-ish label strings → best taxonomy bucket
LABEL_KEYWORD_MAP = [
    (("imp identification","imp suspect","red herring","demon read"), "framing_or_spin"),
    (("fortune teller","empath read","undertaker info","hard info","claim result"), "evidence_based_argument"),
    (("role claim","hard claim","soft claim","claiming"), "role_claiming"),
    (("counterclaim","cc","counter claim"), "counter_claiming"),
    (("policy execute","policy vote","norms"), "norm_enforcement"),
    (("leader","shepherd","follow me"), "opinion_leadership"),
    (("wagon","pile on","sheeping"), "bandwagoning"),
    (("pressure vote","whip votes","lock votes"), "vote_whipping"),
    (("plan","coordination","vote order","nom order"), "coordination_signaling"),
    (("bus","throw under bus"), "bussing"),
    (("park vote","parked vote"), "vote_parking"),
    (("pocket","buddy"), "pocketing"),
    (("scapegoat","pin blame"), "scapegoating"),
    (("deflect","whatabout","change subject"), "deflection"),
    (("strawman","misrepresent"), "straw_manning"),
    (("appeal to emotion","fear monger"), "appeal_to_emotion"),
    (("hedge","ambivalent","non-committal"), "hedging"),
    (("meta","previous game"), "meta_reference"),
    (("lie","fake","fabricate"), "deception"),
    (("gaslight","misremember"), "gaslighting"),
    (("appeal to expert","authority"), "appeal_to_authority"),
    (("coalition","ally","townblock"), "coalition_building"),
    (("threat","intimidate","ultimatum"), "threat_or_intimidation"),
]

SYSTEM_PROMPT = (
    "You are a rigorous social-dynamics analyst. "
    "Return ONLY one valid JSON object. No prose, no code fences."
)
RAW_SUFFIX = ".raw.txt"

# ----------------------- Prompt builder -----------------------

def build_user_instruction(base_prompt: str,
                           taxonomy: List[str],
                           known_labels: List[str],
                           known_phrases: List[str],
                           filename: str,
                           file_content: str) -> str:
    taxonomy_str = ", ".join(taxonomy)
    labels_str  = ", ".join(known_labels) if known_labels else "(none)"
    phrases_str = ", ".join(sorted(set(known_phrases))) if known_phrases else "(none)"
    return f"""{base_prompt}

ONLY analyze: MODE, PLAYERS, WINNER, [DAY] Nominee/Votes, [DAY] TABLE TALK.

TAXONOMY:
[{taxonomy_str}]

KNOWN_DYNAMIC_LABELS (hints): [{labels_str}]
KNOWN_DYNAMIC_PHRASES (hints): [{phrases_str}]

LABEL RULES:
- Prefer a label from the TAXONOMY.
- If none fits, you MAY invent a concise (1–3 words), game-agnostic social-dynamics label
  (no role names like Imp/Slayer/etc.; no mechanics like 'execution' or 'night kill').
- When you invent a label, also provide 'parent_label' as the closest TAXONOMY bucket.

REQUIREMENTS:
1) Provide evidence quotes with where-refs when possible.
2) Return ONLY this JSON (no fences, no comments):

{{
  "file": "<string — file name>",
  "found": [
    {{
      "label": "<taxonomy OR invented label>",
      "parent_label": "<taxonomy bucket if label is invented, else repeat the taxonomy label>",
      "phrase": "<short human-readable phrase>",
      "spans": [{{"quote": "<short quote>", "where": "<line/timestamp/section>"}}],
      "reasoning": "<2–4 sentences tying evidence to the label>"
    }}
  ],
  "new_phrases": ["<subset of found[].phrase not in KNOWN_DYNAMIC_PHRASES>"],
  "summary": "<<=120 words concise summary>"
}}

FILE NAME:
{filename}

FILE CONTENT DIGEST:
{file_content}
"""

# ----------------------- JSON parsing utils -----------------------

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)
_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")
_SMART_QUOTES = {ord("“"): '"', ord("”"): '"', ord("’"): "'", ord("‘"): "'"}

def _extract_balanced_object(s: str) -> Optional[str]:
    s = s.strip()
    if not s:
        return None
    s = _CODE_FENCE_RE.sub("", s)
    i = s.find("{")
    if i == -1:
        return None
    depth = 0; in_str = False; esc = False; quote = None
    for j in range(i, len(s)):
        ch = s[j]
        if in_str:
            if esc: esc = False
            elif ch == "\\": esc = True
            elif ch == quote: in_str = False
        else:
            if ch in ('"', "'"): in_str = True; quote = ch
            elif ch == "{": depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return s[i:j+1]
    return None

def _common_fixes(payload: str) -> str:
    t = payload.translate(_SMART_QUOTES)
    t = _CODE_FENCE_RE.sub("", t)
    t = _TRAILING_COMMA_RE.sub(r"\1", t)
    t = re.sub(r'\bTrue\b', 'true', t)
    t = re.sub(r'\bFalse\b', 'false', t)
    t = re.sub(r'\bNone\b', 'null', t)
    return t

def parse_strict_json_or_repair(s: str) -> Tuple[Optional[Dict[str, Any]], str]:
    raw = s.strip()
    try:
        return json.loads(raw), "parsed: direct json"
    except Exception:
        pass
    payload = _extract_balanced_object(raw)
    if not payload:
        return None, "parse fail: no balanced {…} found"
    fixed = _common_fixes(payload)
    try:
        return json.loads(fixed), "parsed: fixed json"
    except Exception:
        pass
    try:
        obj = ast.literal_eval(fixed)
        return json.loads(json.dumps(obj)), "parsed: via ast.literal_eval"
    except Exception:
        return None, "parse fail: unrecoverable"

def schema_snippet() -> str:
    return (
        '{ "file": "...", "found": [ { "label": "...", "parent_label": "...", "phrase": "...", '
        '"spans": [ { "quote": "...", "where": "..." } ], "reasoning": "..." } ], '
        '"new_phrases": ["..."], "summary": "..." }'
    )

# ----------------------- File I/O -----------------------

def read_text(path: Path, max_chars: int) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"[ERROR READING FILE: {e}]"
    if max_chars and len(text) > max_chars:
        half = max_chars // 2
        return text[:half] + "\n...\n[TRUNCATED]\n...\n" + text[-half:]
    return text

def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def load_state(state_path: Path) -> Dict[str, Any]:
    if state_path.exists():
        try:
            obj = json.loads(state_path.read_text(encoding="utf-8"))
            obj.setdefault("phrases", {})
            obj.setdefault("labels", {})         # taxonomy buckets
            obj.setdefault("custom_labels", {})  # invented: {label: {parent, count, first_seen}}
            return obj
        except Exception:
            pass
    return {"phrases": {}, "labels": {}, "custom_labels": {}}

def save_state(state_path: Path, state: Dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

# ----------------------- BotC digest builders -----------------------

def _safe(obj, key, default=None):
    try:
        return obj.get(key, default)
    except Exception:
        return default

def build_botc_digest(data: dict, max_lines_per_day: int = 12, max_chars_per_line: int = 240) -> str:
    mode = _safe(data, "mode", "")
    winner = _safe(data, "winner", "")
    players = _safe(data, "players", [])
    names = [p.get("name", "") for p in players]

    out = []
    out.append(f"MODE: {mode}")
    out.append(f"PLAYERS: {', '.join(names)}")
    out.append(f"WINNER: {winner}")
    out.append("")

    for d in _safe(data, "days", []):
        day_no = _safe(d, "day_number", "?")
        nominee = _safe(d, "nominee", None)
        votes = _safe(d, "votes", {})
        if nominee or votes:
            out.append(f"[DAY {day_no}] Nominee: {nominee}")
            if votes:
                vs = ", ".join(f"{k}={v}" for k, v in votes.items())
                out.append(f"[DAY {day_no}] Votes: {vs}")
            out.append("")

    talks = _safe(data, "table_talk", [])
    talks_by_day: Dict[Any, List[dict]] = {}
    for t in talks:
        dn = _safe(t, "day_number", "?")
        talks_by_day.setdefault(dn, []).append(t)

    for dn in sorted(talks_by_day, key=lambda x: (isinstance(x, int), x)):
        out.append(f"[DAY {dn}] TABLE TALK:")
        lines = talks_by_day[dn][:max_lines_per_day]
        for t in lines:
            sp = _safe(t, "speaker", "?")
            tx = _safe(t, "text", "")
            if len(tx) > max_chars_per_line:
                tx = tx[:max_chars_per_line] + " …"
            out.append(f"- {sp}: {tx}")
        out.append("")

    return "\n".join(out).strip()

def build_digest_for_file(path: Path, max_chars: int, max_lines_per_day: int, max_chars_per_line: int) -> str:
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and ("players" in data or "days" in data or "table_talk" in data):
                return build_botc_digest(data, max_lines_per_day=max_lines_per_day, max_chars_per_line=max_chars_per_line)
        except Exception:
            pass
        return read_text(path, max_chars)
    return read_text(path, max_chars)

# ----------------------- Invented-label sanitation -----------------------

def _looks_roleish(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in ROLE_WORDS)

def _looks_valid_invented(text: str) -> bool:
    t = (text or "").strip()
    if not t or _looks_roleish(t):
        return False
    words = [w for w in re.split(r"\s+", t) if w]
    if not (1 <= len(words) <= 3):
        return False
    if any(re.search(r"[^a-zA-Z\- ]", w) for w in words):
        return False
    return True

def _map_by_keywords(label: str) -> str:
    lab = (label or "").lower()
    for keys, target in LABEL_KEYWORD_MAP:
        if any(k in lab for k in keys):
            return target
    return "other"

def _closest_parent_label(item: dict) -> str:
    parent = (item.get("parent_label") or "").strip().lower()
    if parent in ALLOWED_LABELS:
        return parent
    return _map_by_keywords(item.get("label") or "")

def sanitize_and_collect_custom(report: dict, allow_invented: bool) -> Tuple[dict, List[Tuple[str, str]]]:
    """
    Ensures each found[].label is acceptable.
    Returns (cleaned_report, custom_pairs[(invented_label, parent_label), ...])
    """
    custom = []
    found = report.get("found") or []
    for item in found:
        lab = (item.get("label") or "").strip()
        if not lab:
            item["label"] = "other"
            item["parent_label"] = "other"
            continue

        if lab.lower() in ALLOWED_LABELS:
            item["label"] = lab.lower()
            parent = (item.get("parent_label") or "").strip().lower()
            item["parent_label"] = item["label"] if parent not in ALLOWED_LABELS else parent
            continue

        # Not in taxonomy → consider as invented
        if allow_invented and _looks_valid_invented(lab):
            parent = _closest_parent_label(item)
            item["parent_label"] = parent
            custom.append((lab, parent))
        else:
            # Role/mechanic-ish OR invention not allowed → collapse to taxonomy
            anchor = _map_by_keywords(lab)
            item["parent_label"] = anchor
            item["label"] = anchor
    return report, custom

# ----------------------- Markdown render -----------------------

def to_markdown(report: Dict[str, Any]) -> str:
    lines = [f"# Social Dynamics Report — {report.get('file','')}\n"]
    if "summary" in report:
        lines.append(f"**Summary:** {report['summary']}\n")
    if report.get("found"):
        lines.append("## Findings\n")
        for item in report["found"]:
            label = item.get("label","")
            parent = item.get("parent_label","")
            phrase = item.get("phrase","")
            reasoning = item.get("reasoning","")
            # Show invented labels clearly if they differ from parent
            heading = f"{phrase}  _({label})_" if (label == parent or label in ALLOWED_LABELS) else f"{phrase}  _({label} → {parent})_"
            lines.append(f"### {heading}")
            for sp in (item.get("spans") or []):
                q = (sp.get("quote","") or "").replace("\n"," ")
                where = sp.get("where","")
                lines.append(f"- Evidence: “{q}”  ({where})")
            if reasoning:
                lines.append(f"- Reasoning: {reasoning}")
            lines.append("")
    if report.get("new_phrases"):
        lines.append("## New Phrases Added")
        for p in report["new_phrases"]:
            lines.append(f"- {p}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"

# ----------------------- Known list helpers -----------------------

def top_k_phrases(phrases: Dict[str, Dict[str, Any]], k: int) -> List[str]:
    items = [(ph, int(meta.get("count", 1))) for ph, meta in phrases.items()]
    items.sort(key=lambda kv: (-kv[1], kv[0].lower()))
    return [ph for ph, _ in items[:max(0, k)]]

def top_k_labels(labels: Dict[str, Dict[str, Any]], k: int) -> List[str]:
    items = []
    for lab, meta in labels.items():
        if lab not in ALLOWED_LABELS:  # guard
            continue
        cnt = int(meta.get("count", 1))
        items.append((lab, cnt))
    items.sort(key=lambda kv: (-kv[1], kv[0].lower()))
    return [lab for lab, _ in items[:max(0, k)]]

def top_k_custom_labels(custom: Dict[str, Dict[str, Any]], k: int, threshold: int) -> List[str]:
    items = [(lab, int(meta.get("count", 0))) for lab, meta in custom.items() if int(meta.get("count", 0)) >= threshold]
    items.sort(key=lambda kv: (-kv[1], kv[0].lower()))
    return [lab for lab, _ in items[:max(0, k)]]

# ----------------------- Chat helpers -----------------------

def chat_once(client: LLMClientOllama, model: str, system: str, user: str, *,
              temperature: float, seed: Optional[int], force_json: bool) -> str:
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": user}]
    options = {"temperature": float(temperature)}
    if seed is not None:
        options["seed"] = int(seed)
    if force_json:
        options["format"] = "json"
    try:
        reply, _meta = client.chat(messages, model=model, options=options)  # if wrapper supports options
    except TypeError:
        reply, _meta = client.chat(messages, model=model)  # fallback
    return reply or ""

def repair_json_with_model(client: LLMClientOllama, model: str, raw_reply: str, schema_hint: str, *,
                           temperature: float, seed: Optional[int]) -> str:
    repair_user = (
        "Your previous reply was NOT valid JSON.\n"
        "Rewrite it as ONE valid JSON object according to this schema:\n\n"
        f"{schema_hint}\n\n"
        "Do NOT include code fences, comments, or extra text. JSON only.\n\n"
        "Here is your previous reply to repair (truncate if necessary):\n"
        f"{raw_reply[:6000]}"
    )
    return chat_once(client, model, "Return ONLY JSON. No prose.", repair_user,
                     temperature=temperature, seed=seed, force_json=True)

# ----------------------- Main -----------------------

def main():
    ap = argparse.ArgumentParser(description="Detect social dynamics with taxonomy + invented labels (Qwen via Ollama).")
    ap.add_argument("--model", default=os.environ.get("OLLAMA_MODEL", "qwen3"),
                    help="Ollama model name (e.g., qwen3, qwen2.5:7b-instruct)")
    ap.add_argument("--records-dir", default="game_records", help="Input directory")
    ap.add_argument("--glob", default="*.json", help="Glob pattern within records-dir")
    ap.add_argument("--out-dir", default="analyses", help="Output directory")
    ap.add_argument("--state", default=None,
                    help="Path to running dictionary; default=<out-dir>/dynamics_state.json")
    ap.add_argument("--prompt", default=None, help="Inline base prompt (optional)")
    ap.add_argument("--prompt-file", default=None, help="File containing base prompt (overrides --prompt)")
    ap.add_argument("--max-chars", type=int, default=60_000, help="Max chars per input file (truncate middle)")
    ap.add_argument("--max-talk-lines", type=int, default=12, help="Max table-talk lines per day in digest")
    ap.add_argument("--max-line-chars", type=int, default=240, help="Max chars per talk line in digest")
    ap.add_argument("--sleep", type=float, default=0.0, help="Seconds to sleep between requests")
    ap.add_argument("--retries", type=int, default=1, help="Repair attempts on invalid JSON")
    # Consistency controls:
    ap.add_argument("--temperature", type=float, default=0.1, help="Sampling temperature")
    ap.add_argument("--seed", type=int, default=0, help="Deterministic seed; -1 disables")
    ap.add_argument("--force-json", action="store_true", help="Ask Ollama to enforce format=json (if supported)")
    ap.add_argument("--memory-scope", choices=["frozen","accumulate","none"], default="frozen",
                    help="frozen: same hints per file; accumulate: grow after each file; none: no hints")
    ap.add_argument("--max-known", type=int, default=24, help="Max phrases to feed as hints")
    ap.add_argument("--max-labels", type=int, default=8, help="Max taxonomy labels to feed as hints")
    # Invented label controls:
    ap.add_argument("--allow-invented", action="store_true",
                    help="Allow invented (concise, game-agnostic) labels with parent_label anchor")
    ap.add_argument("--invented-threshold", type=int, default=2,
                    help="Min count before a custom label is hinted back")
    ap.add_argument("--max-custom-labels", type=int, default=12,
                    help="Max custom labels to include as hints")
    ap.add_argument("--include-custom-in-prompts", action="store_true",
                    help="Include mature custom labels as hints (after threshold)")
    args = ap.parse_args()

    if args.state is None:
        args.state = str(Path(args.out_dir) / "dynamics_state.json")

    if args.seed >= 0:
        random.seed(args.seed)

    rec_dir = Path(args.records_dir); out_dir = Path(args.out_dir); state_path = Path(args.state)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(rec_dir.glob(args.glob))
    if not files:
        print(f"[warn] No files matched {rec_dir}/{args.glob}")
        return

    # Base prompt
    if args.prompt_file:
        base_prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    elif args.prompt:
        base_prompt = args.prompt
    else:
        base_prompt = ("Analyze the digest for social dynamics in multi-agent play "
                       "(persuasion, leadership, deception, coalitions, etc.).")

    # State
    state = load_state(state_path)
    known_phrases: Dict[str, Dict[str, Any]]  = state.get("phrases", {})
    known_labels_map: Dict[str, Dict[str, Any]] = state.get("labels", {})
    custom_labels: Dict[str, Dict[str, Any]] = state.get("custom_labels", {})

    # Build frozen hints if needed
    if args.memory_scope == "none":
        frozen_known_phrases: List[str] = []
        frozen_known_labels: List[str] = []
        frozen_custom_labels: List[str] = []
    else:
        frozen_known_phrases = top_k_phrases(known_phrases, args.max_known)
        frozen_known_labels = top_k_labels(known_labels_map, args.max_labels)
        frozen_custom_labels = top_k_custom_labels(custom_labels, args.max_custom_labels, args.invented_threshold)

    client = LLMClientOllama()

    print(f"[info] Model: {args.model}")
    print(f"[info] Memory scope: {args.memory_scope} | allow-invented={args.allow_invented}")
    print(f"[info] Known phrases: {len(known_phrases)} | labels: {len(known_labels_map)} | custom: {len(custom_labels)}")
    print(f"[info] Output -> {out_dir} | State -> {state_path}")
    print(f"[info] Processing {len(files)} file(s)")

    for idx, fpath in enumerate(files, start=1):
        rel = fpath.relative_to(rec_dir)
        print(f"\n[{idx}/{len(files)}] {rel}")

        content = build_digest_for_file(
            fpath,
            max_chars=args.max_chars,
            max_lines_per_day=args.max_talk_lines,
            max_chars_per_line=args.max_line_chars,
        )

        # Hints for this file
        if args.memory_scope == "accumulate":
            known_list_now   = top_k_phrases(known_phrases, args.max_known)
            labels_now       = top_k_labels(known_labels_map, args.max_labels)
            custom_now       = top_k_custom_labels(custom_labels, args.max_custom_labels, args.invented_threshold)
        else:
            known_list_now   = list(frozen_known_phrases)
            labels_now       = list(frozen_known_labels)
            custom_now       = list(frozen_custom_labels)

        if args.include_custom_in_prompts:
            labels_now = labels_now + custom_now  # taxonomy first, then mature custom labels

        user_msg = build_user_instruction(
            base_prompt, DEFAULT_TAXONOMY,
            labels_now, known_list_now,
            str(rel), content
        )

        seed_val = None if args.seed < 0 else args.seed
        raw = chat_once(client, args.model, SYSTEM_PROMPT, user_msg,
                        temperature=args.temperature, seed=seed_val, force_json=args.force_json)
        write_text(out_dir / f"{fpath.stem}{RAW_SUFFIX}", raw)

        report, note = parse_strict_json_or_repair(raw)

        # Repair loop
        tries = 0
        while report is None and tries < max(0, args.retries):
            tries += 1
            raw = repair_json_with_model(client, args.model, raw, schema_snippet(),
                                         temperature=max(0.05, args.temperature - 0.05),
                                         seed=seed_val)
            write_text(out_dir / f"{fpath.stem}.repair{tries}{RAW_SUFFIX}", raw)
            report, note = parse_strict_json_or_repair(raw)

        if report is None:
            print(f"  [warn] Unparseable even after {tries} repair attempt(s) — saving stub.")
            report = {"file": str(rel), "found": [], "new_phrases": [], "summary": "Unparseable response."}

        # Sanitize + collect invented labels (if enabled)
        report, custom_pairs = sanitize_and_collect_custom(report, allow_invented=args.allow_invented)

        # ---- Update state from report ----
        # 1) phrases + taxonomy label buckets
        for item in (report.get("found") or []):
            parent = (item.get("parent_label") or item.get("label") or "other").lower()
            if parent not in ALLOWED_LABELS:
                parent = _map_by_keywords(parent)

            phrase = (item.get("phrase") or "").strip()
            if phrase:
                # flat phrase counts
                if phrase not in known_phrases:
                    known_phrases[phrase] = {"first_seen": str(rel), "count": 1}
                    print(f"  [new phrase] {phrase}")
                else:
                    known_phrases[phrase]["count"] = int(known_phrases[phrase].get("count", 0)) + 1

                # taxonomy bucket
                bucket = known_labels_map.setdefault(parent, {"phrases": {}, "count": 0})
                bucket["count"] = int(bucket.get("count", 0)) + 1
                phm = bucket["phrases"].get(phrase, {"first_seen": str(rel), "count": 0})
                phm["count"] += 1
                bucket["phrases"][phrase] = phm

        # 2) record invented label counts
        for lab, parent in custom_pairs:
            meta = custom_labels.setdefault(lab, {"parent": parent, "count": 0, "first_seen": str(rel)})
            meta["parent"] = parent
            meta["count"] = int(meta.get("count", 0)) + 1

        # 3) 'new_phrases' (no label) → flat + under 'other'
        for phrase in (report.get("new_phrases") or []):
            phrase = (phrase or "").strip()
            if not phrase:
                continue
            if phrase not in known_phrases:
                known_phrases[phrase] = {"first_seen": str(rel), "count": 1}
                print(f"  [new phrase] {phrase}")
            else:
                known_phrases[phrase]["count"] = int(known_phrases[phrase].get("count", 0)) + 1
            ob = known_labels_map.setdefault("other", {"phrases": {}, "count": 0})
            ob["count"] = int(ob.get("count", 0)) + 1
            phm = ob["phrases"].get(phrase, {"first_seen": str(rel), "count": 0})
            phm["count"] += 1
            ob["phrases"][phrase] = phm

        # Persist per-file
        json_out = out_dir / f"{fpath.stem}.social.json"
        md_out = out_dir / f"{fpath.stem}.social.md"
        write_text(json_out, json.dumps(report, indent=2))
        write_text(md_out, to_markdown(report))
        print(f"  [saved] {json_out.name}, {md_out.name}  ({note})")

        # Save state
        state["phrases"]       = known_phrases
        state["labels"]        = known_labels_map
        state["custom_labels"] = custom_labels
        save_state(state_path, state)

        if args.sleep > 0:
            time.sleep(args.sleep)

    print(f"\n[done] Processed {len(files)} file(s).")
    print(f"[info] phrases: {len(known_phrases)} | labels: {len(known_labels_map)} | custom: {len(custom_labels)}")
    print(f"[info] State saved -> {state_path}")

if __name__ == "__main__":
    main()