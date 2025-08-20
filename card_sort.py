#!/usr/bin/env python3
# Run: python3 card_sort.py
"""
Batch analysis of game_records with Qwen (via LLMClientOllama).
Finds social dynamics (persuasion, opinion leadership, deception, etc.),
return reasoning, and accumulate newly discovered 'phrases' across files.

Outputs:
- game_records/analyses/<file>.social.json  (strict JSON with findings)
- game_records/analyses/<file>.social.md    (summary)
- game_records/analyses/dynamics_state.json (running dictionary of phrases)
"""

import os
import re
import json
import time
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Use your uploaded client wrapper
from llm_client_ollama import LLMClientOllama


# ----------------------------- Config / Prompt -----------------------------

DEFAULT_TAXONOMY = [
    "persuasion",
    "opinion_leadership",
    "deception",
    "gaslighting",
    "appeal_to_authority",
    "bandwagoning",
    "vote_whipping",
    "coalition_building",
    "threat_or_intimidation",
    "norm_enforcement",
    "framing_or_spin",
    "information_withholding",
    "other"
]

SYSTEM_PROMPT = (
    "You are a rigorous social-dynamics analyst. "
    "You must output ONLY a single valid JSON object that conforms exactly to the requested schema. "
    "No prose outside JSON."
)

def build_user_instruction(
    base_prompt: str,
    taxonomy: List[str],
    known_phrases: List[str],
    filename: str,
    file_content: str
) -> str:
    """
    Build the user message sent to Qwen. We ask for a strict JSON-only response
    so we can parse reliably.
    """
    taxonomy_str = ", ".join(taxonomy)
    known_str = ", ".join(sorted(set(known_phrases))) if known_phrases else "(none)"

    return f"""{base_prompt}

TASK:
Detect social dynamics present in the provided file. Use the taxonomy:
[{taxonomy_str}]
You may also name additional dynamics as needed.

KNOWN_DYNAMIC_PHRASES (from earlier files in this batch): [{known_str}]

REQUIREMENTS:
1) When you claim a dynamic is present, provide succinct reasoning that references exact evidence
   (quotes/snippets and, if present, line numbers or timestamps).
2) Identify any 'new' phrases that are NOT in KNOWN_DYNAMIC_PHRASES (e.g., "vote whipping", "appeal to authority").
3) Output ONLY a single JSON object with this exact schema:
{{
  "file": "<string - file name>",
  "found": [
    {{
      "label": "<one of taxonomy or 'other'>",
      "phrase": "<short human-readable phrase for the dynamic>",
      "spans": [
        {{"quote": "<short quote>", "where": "<line range / timestamp / section if available>"}}
      ],
      "reasoning": "<2-4 sentences explaining why the evidence indicates this dynamic>"
    }}
  ],
  "new_phrases": ["<subset of found[].phrase that are not in KNOWN_DYNAMIC_PHRASES>"],
  "summary": "<<=120 word concise summary of the social dynamics in this file>"
}}

FILE NAME:
{filename}

FILE CONTENT (may be truncated):
{file_content}
"""


# ----------------------------- I/O Helpers --------------------------------

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
            return json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"phrases": {}}  # { phrase: {"first_seen": "file", "count": int} }

def save_state(state_path: Path, state: Dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ----------------------------- Parsing Helpers ----------------------------

def parse_strict_json(s: str) -> Dict[str, Any]:
    """
    Try to parse a response that SHOULD be a single JSON object.
    If model accidentally includes stray text, salvage the first {...} block.
    """
    s = s.strip()
    try:
        return json.loads(s)
    except Exception:
        # salvage first JSON object
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            payload = s[start:end+1]
            return json.loads(payload)
        raise


def to_markdown(report: Dict[str, Any]) -> str:
    lines = []
    lines.append(f"# Social Dynamics Report — {report.get('file','')}\n")
    if "summary" in report:
        lines.append(f"**Summary:** {report['summary']}\n")
    if "found" in report and report["found"]:
        lines.append("## Findings\n")
        for item in report["found"]:
            label = item.get("label","")
            phrase = item.get("phrase","")
            reasoning = item.get("reasoning","")
            lines.append(f"### {phrase}  _({label})_")
            if item.get("spans"):
                for sp in item["spans"]:
                    q = sp.get("quote","").replace("\n"," ")
                    where = sp.get("where","")
                    lines.append(f"- Evidence: “{q}”  ({where})")
            if reasoning:
                lines.append(f"- Reasoning: {reasoning}")
            lines.append("")
    if "new_phrases" in report and report["new_phrases"]:
        lines.append("## New Phrases Added")
        for p in report["new_phrases"]:
            lines.append(f"- {p}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


# ----------------------------- Main Batch ---------------------------------

def main():
    ap = argparse.ArgumentParser(description="Detect social dynamics across game_records with Qwen via Ollama.")
    ap.add_argument("--model", default=os.environ.get("OLLAMA_MODEL", "qwen3"),
                    help="Ollama model name (e.g., qwen3, qwen2.5:7b-instruct)")
    ap.add_argument("--records-dir", default="game_records", help="Input directory")
    ap.add_argument("--glob", default="*.json", help="Glob pattern within records-dir")
    ap.add_argument("--out-dir", default="game_records/analyses", help="Output directory for per-file results")
    ap.add_argument("--state", default="game_records/analyses/dynamics_state.json",
                    help="Path to running dictionary of discovered phrases")
    ap.add_argument("--prompt", default=None, help="Inline base prompt (optional)")
    ap.add_argument("--prompt-file", default=None, help="File containing base prompt (overrides --prompt)")
    ap.add_argument("--max-chars", type=int, default=250_000, help="Max chars per input file (truncates middle)")
    ap.add_argument("--sleep", type=float, default=0.0, help="Sleep between requests (seconds)")
    args = ap.parse_args()

    rec_dir = Path(args.records_dir)
    out_dir = Path(args.out_dir)
    state_path = Path(args.state)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not rec_dir.exists():
        print(f"[err] Records dir not found: {rec_dir}")
        raise SystemExit(2)

    files = sorted(rec_dir.glob(args.glob))
    if not files:
        print(f"[warn] No files matched {rec_dir}/{args.glob}")
        return

    # Load base prompt
    if args.prompt_file:
        base_prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    elif args.prompt:
        base_prompt = args.prompt
    else:
        base_prompt = (
            "Analyze the file for social dynamics relevant to multi-agent conversations, "
            "including persuasion, leadership, deception, coalition-building, and related tactics."
        )

    # Load running state (phrases dictionary)
    state = load_state(state_path)
    known_phrases_dict: Dict[str, Dict[str, Any]] = state.get("phrases", {})
    known_phrases_list: List[str] = list(known_phrases_dict.keys())

    # Init your Ollama client
    client = LLMClientOllama()

    print(f"[info] Model: {args.model}")
    print(f"[info] Known phrases at start: {len(known_phrases_list)}")
    print(f"[info] Processing {len(files)} file(s) from {rec_dir}")

    for idx, fpath in enumerate(files, start=1):
        rel = fpath.relative_to(rec_dir)
        print(f"\n[{idx}/{len(files)}] {rel}")

        content = read_text(fpath, args.max_chars)
        user_msg = build_user_instruction(
            base_prompt=base_prompt,
            taxonomy=DEFAULT_TAXONOMY,
            known_phrases=known_phrases_list,
            filename=str(rel),
            file_content=content,
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]

        try:
            reply, _meta = client.chat(messages, model=args.model)
        except Exception as e:
            print(f"[err] Request failed: {e}")
            reply = '{"file": "%s", "found": [], "new_phrases": [], "summary": "Request failed."}' % rel

        # Parse strict JSON
        try:
            report = parse_strict_json(reply)
        except Exception as e:
            print(f"[err] Could not parse JSON. Saving raw reply. {e}")
            report = {"file": str(rel), "found": [], "new_phrases": [], "summary": "Unparseable response."}

        # Update running dictionary with phrases from 'found'
        found_items = report.get("found", []) or []
        for item in found_items:
            phrase = (item.get("phrase") or "").strip()
            if not phrase:
                continue
            entry = known_phrases_dict.get(phrase)
            if entry is None:
                known_phrases_dict[phrase] = {"first_seen": str(rel), "count": 1}
                print(f"  [new] {phrase}")
            else:
                entry["count"] = int(entry.get("count", 0)) + 1

        # Capture 'new_phrases' explicitly (sanity/log)
        new_list = report.get("new_phrases", []) or []
        for phrase in new_list:
            phrase = (phrase or "").strip()
            if phrase and phrase not in known_phrases_dict:
                known_phrases_dict[phrase] = {"first_seen": str(rel), "count": 1}
                print(f"  [new] {phrase}")

        # Persist per-file outputs
        json_out = out_dir / f"{fpath.stem}.social.json"
        md_out = out_dir / f"{fpath.stem}.social.md"
        write_text(json_out, json.dumps(report, indent=2))
        write_text(md_out, to_markdown(report))
        print(f"  [saved] {json_out.name}, {md_out.name}")

        # Refresh the list fed to the *next* file
        known_phrases_list = list(known_phrases_dict.keys())

        # Persist state after each file (so you can stop/resume)
        state["phrases"] = known_phrases_dict
        save_state(state_path, state)

        if args.sleep > 0:
            time.sleep(args.sleep)

    print(f"\n[done] Processed {len(files)} files.")
    print(f"[info] Total known phrases: {len(known_phrases_dict)}")
    print(f"[info] State saved -> {state_path}")

if __name__ == "__main__":
    main()
