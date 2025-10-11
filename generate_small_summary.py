#!/usr/bin/env python3
"""
Generate a compact summary CSV from a large analysis CSV:

- Computes the grand total from the last column ("Total Occurrences").
- Keeps only the last row for each Main Category whose count is >= threshold% of the grand total.
- Appends a blank line and a "Grand Total" row at the end.

Usage:
  python generate_small_summary.py \
    --input restructured_social_dynamics_analysis.csv \
    --output small_summary.csv \
    --threshold_pct 1.0

Defaults:
  input:   restructured_social_dynamics_analysis.csv
  output:  small_summary.csv
  threshold_pct: 1.0 (i.e., >= 1%)
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import List, Optional


def increase_csv_field_limit() -> None:
    """Increase the CSV field size limit to handle very large quoted fields."""
    max_int = sys.maxsize
    while True:
        try:
            csv.field_size_limit(max_int)
            break
        except OverflowError:
            max_int = int(max_int / 10)


def read_rows(path: Path) -> List[List[str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.reader(f))


def write_rows(path: Path, rows: List[List[str]], append_blank_line_before_last: bool = True) -> None:
    from io import StringIO

    buffer = StringIO()
    writer = csv.writer(buffer)

    if not rows:
        path.write_text("", encoding="utf-8")
        return

    # Header
    writer.writerow(rows[0])

    # Body (excluding header and last line)
    for row in rows[1:-1]:
        writer.writerow(row)

    # Optional blank line before the final row
    if append_blank_line_before_last:
        buffer.write("\n")

    # Final row
    writer.writerow(rows[-1])

    path.write_text(buffer.getvalue(), encoding="utf-8")


def find_last_nonempty_row(rows: List[List[str]]) -> Optional[List[str]]:
    for row in reversed(rows):
        if row and any(cell.strip() for cell in row):
            return row
    return None


def parse_int_safely(value: str) -> Optional[int]:
    value = value.strip()
    if value == "":
        return None
    try:
        return int(value)
    except ValueError:
        try:
            return int(float(value))
        except Exception:
            return None


def build_small_summary(
    source_rows: List[List[str]],
    threshold_pct: float,
) -> List[List[str]]:
    if not source_rows:
        raise ValueError("Input CSV is empty")

    header = source_rows[0]
    last_col_index = len(header) - 1

    # Compute grand total by summing the last column across all data rows
    grand_total = 0
    for row in source_rows[1:]:
        if not row or len(row) <= last_col_index:
            continue
        value = parse_int_safely(str(row[last_col_index]).strip())
        if value is None:
            continue
        grand_total += value

    threshold_value = grand_total * (threshold_pct / 100.0)

    # Collect the last row for each contiguous Main Category block and track definitions
    category_last_rows: List[List[str]] = []
    category_definitions: dict[str, str] = {}
    previous_main_category: Optional[str] = None
    previous_row: Optional[List[str]] = None

    for row in source_rows[1:]:
        if not row or len(row) <= last_col_index:
            continue
        main_category = row[0].strip()
        if main_category == "":
            continue
        
        # Store definition from first occurrence of each category
        if main_category not in category_definitions and len(row) > 2:
            category_definitions[main_category] = row[2].strip()
        
        if previous_main_category is not None and main_category != previous_main_category:
            if previous_row is not None:
                category_last_rows.append(previous_row)
        previous_main_category = main_category
        previous_row = row

    if previous_row is not None:
        category_last_rows.append(previous_row)

    # Filter rows where Total Occurrences >= threshold and update definitions
    kept_rows: List[List[str]] = []
    for row in category_last_rows:
        value_str = row[last_col_index].strip()
        count_value = parse_int_safely(value_str)
        if count_value is None:
            continue
        if count_value >= threshold_value:
            # Update the definition column with the main category definition
            main_category = row[0].strip()
            if main_category in category_definitions and len(row) > 2:
                row[2] = category_definitions[main_category]
            kept_rows.append(row)

    # Construct grand total row
    grand_total_row: List[str] = [""] * len(header)
    if len(grand_total_row) > 0:
        grand_total_row[0] = "Grand Total"
    grand_total_row[last_col_index] = str(grand_total)

    # Output rows: header, kept rows, grand total row (blank line is inserted at write time)
    return [header] + kept_rows + [grand_total_row]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a compact summary CSV from a large analysis CSV.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("restructured_social_dynamics_analysis.csv"),
        help="Path to the input CSV (default: restructured_social_dynamics_analysis.csv)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("small_summary.csv"),
        help="Path to the output CSV (default: small_summary.csv)",
    )
    parser.add_argument(
        "--threshold_pct",
        type=float,
        default=1.0,
        help="Keep categories with Total Occurrences >= this percent of grand total (default: 1.0)",
    )

    args = parser.parse_args()

    increase_csv_field_limit()

    rows = read_rows(args.input)
    out_rows = build_small_summary(rows, threshold_pct=args.threshold_pct)
    write_rows(args.output, out_rows, append_blank_line_before_last=True)

    # Simple stdout confirmation
    header = out_rows[0]
    last_col_index = len(header) - 1
    grand_total_row = out_rows[-1]
    grand_total_value = grand_total_row[last_col_index]
    kept_count = max(0, len(out_rows) - 2)  # exclude header and grand total
    print(
        f"Grand total: {grand_total_value}; kept {kept_count} categories (>= {args.threshold_pct}% threshold)\n"
        f"Written to: {args.output}"
    )


if __name__ == "__main__":
    main()