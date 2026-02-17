#!/usr/bin/env python3
"""Prepare curation inputs for the daily AI news workflow.

This script does two things:
1) Filters each raw markdown file so only entries whose publication date exactly
   matches the target date remain.
2) Builds a "recent headlines" file from the previous N daily reports to help
   avoid cross-day duplicates during curation.
"""

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import re
from dataclasses import dataclass


ENTRY_HEADER_RE = re.compile(r"^(?P<prefix>\s*#{2,3}\s*)(?P<num>\d+)\.\s*(?P<title>.+?)\s*$")
TABLE_DATE_RE = re.compile(r"^\s*\|\s*(?:Published|Date|公開日|日付)\s*\|\s*(?P<value>.+?)\s*\|\s*$")
BULLET_DATE_RE = re.compile(r"^\s*[-*]\s*\*\*(?:Published|Date|公開日|日付)\*\*:\s*(?P<value>.+?)\s*$")
PLAIN_DATE_RE = re.compile(r"^\s*(?:Published|Date|公開日|日付)\s*[:：]\s*(?P<value>.+?)\s*$")

ISO_DATE_RE = re.compile(r"(?<!\d)(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})(?!\d)")
JP_DATE_RE = re.compile(r"(?<!\d)(20\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日")

REPORT_HEADLINE_RE = re.compile(r"^\s*#{2,3}\s*\d+\.\s*(?P<title>.+?)\s*$")

FULLWIDTH_MAP = str.maketrans("０１２３４５６７８９／－．：", "0123456789/-.:")


@dataclass
class Entry:
    prefix: str
    title: str
    lines: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare raw files for curation.")
    parser.add_argument("--target-date", required=True, help="Target date in YYYY-MM-DD format.")
    parser.add_argument("--raw-dir", default="raw", help="Directory that stores raw category markdown files.")
    parser.add_argument("--news-dir", default="news", help="Directory that stores final daily reports.")
    parser.add_argument("--lookback-days", type=int, default=3, help="How many prior days to inspect.")
    parser.add_argument(
        "--recent-headlines-file",
        default="_recent_headlines.md",
        help="Output filename (inside raw-dir) for prior headlines.",
    )
    return parser.parse_args()


def normalize_date_text(value: str) -> str:
    return value.translate(FULLWIDTH_MAP).strip()


def parse_date(value: str) -> str | None:
    normalized = normalize_date_text(value)
    for pattern in (ISO_DATE_RE, JP_DATE_RE):
        match = pattern.search(normalized)
        if not match:
            continue
        year, month, day = (int(part) for part in match.groups())
        try:
            return dt.date(year, month, day).isoformat()
        except ValueError:
            return None
    return None


def split_entries(lines: list[str]) -> tuple[list[str], list[Entry]]:
    start_indexes: list[int] = []
    for index, line in enumerate(lines):
        if ENTRY_HEADER_RE.match(line.rstrip("\n")):
            start_indexes.append(index)

    if not start_indexes:
        return lines, []

    preamble = lines[: start_indexes[0]]
    entries: list[Entry] = []

    for idx, start in enumerate(start_indexes):
        end = start_indexes[idx + 1] if idx + 1 < len(start_indexes) else len(lines)
        chunk = lines[start:end]
        header = ENTRY_HEADER_RE.match(chunk[0].rstrip("\n"))
        if not header:
            continue
        entries.append(
            Entry(
                prefix=header.group("prefix"),
                title=header.group("title").strip(),
                lines=chunk,
            )
        )

    return preamble, entries


def extract_entry_date(entry: Entry) -> str | None:
    for line in entry.lines:
        stripped = line.rstrip("\n")
        for pattern in (TABLE_DATE_RE, BULLET_DATE_RE, PLAIN_DATE_RE):
            match = pattern.match(stripped)
            if not match:
                continue
            return parse_date(match.group("value"))
    return None


def filter_raw_file(path: pathlib.Path, target_date: str) -> tuple[int, int, int, int]:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    preamble, entries = split_entries(lines)

    if not entries:
        return (0, 0, 0, 0)

    kept: list[Entry] = []
    removed_missing_date = 0
    removed_wrong_date = 0

    for entry in entries:
        entry_date = extract_entry_date(entry)
        if entry_date is None:
            removed_missing_date += 1
            continue
        if entry_date != target_date:
            removed_wrong_date += 1
            continue
        kept.append(entry)

    output_lines: list[str] = list(preamble)
    if output_lines and output_lines[-1].strip():
        output_lines.append("\n")

    for index, entry in enumerate(kept, start=1):
        output_lines.append(f"{entry.prefix}{index}. {entry.title}\n")
        output_lines.extend(entry.lines[1:])

    path.write_text("".join(output_lines), encoding="utf-8")

    return (len(entries), len(kept), removed_missing_date, removed_wrong_date)


def iter_recent_report_paths(news_dir: pathlib.Path, target_date: str, lookback_days: int):
    target = dt.date.fromisoformat(target_date)
    for offset in range(1, lookback_days + 1):
        current = target - dt.timedelta(days=offset)
        report_path = news_dir / current.strftime("%Y-%m") / f"{current.isoformat()}.md"
        yield report_path


def collect_recent_headlines(news_dir: pathlib.Path, target_date: str, lookback_days: int) -> tuple[list[pathlib.Path], list[str]]:
    source_reports: list[pathlib.Path] = []
    headlines: list[str] = []
    seen: set[str] = set()

    for report_path in iter_recent_report_paths(news_dir, target_date, lookback_days):
        if not report_path.exists():
            continue
        source_reports.append(report_path)
        for line in report_path.read_text(encoding="utf-8").splitlines():
            match = REPORT_HEADLINE_RE.match(line)
            if not match:
                continue
            headline = match.group("title").strip()
            key = re.sub(r"\s+", " ", headline).casefold()
            if key in seen:
                continue
            seen.add(key)
            headlines.append(headline)

    return source_reports, headlines


def write_recent_headlines_file(
    output_path: pathlib.Path,
    target_date: str,
    lookback_days: int,
    source_reports: list[pathlib.Path],
    headlines: list[str],
) -> None:
    lines: list[str] = [
        "# Prior headlines for duplicate suppression\n",
        f"- target_date: {target_date}\n",
        f"- lookback_days: {lookback_days}\n",
        "\n",
        "## source_reports\n",
    ]

    if source_reports:
        for report_path in source_reports:
            lines.append(f"- {report_path.as_posix()}\n")
    else:
        lines.append("- none\n")

    lines.append("\n## headlines\n")
    if headlines:
        for headline in headlines:
            lines.append(f"- {headline}\n")
    else:
        lines.append("- none\n")

    output_path.write_text("".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()

    # Validate input date format early.
    dt.date.fromisoformat(args.target_date)

    raw_dir = pathlib.Path(args.raw_dir)
    news_dir = pathlib.Path(args.news_dir)
    recent_headlines_path = raw_dir / args.recent_headlines_file

    raw_dir.mkdir(parents=True, exist_ok=True)

    total_entries = 0
    total_kept = 0
    total_missing_date = 0
    total_wrong_date = 0
    processed_files = 0

    for raw_file in sorted(raw_dir.glob("*.md")):
        if raw_file.name == recent_headlines_path.name:
            continue
        entries, kept, missing_date, wrong_date = filter_raw_file(raw_file, args.target_date)
        processed_files += 1
        total_entries += entries
        total_kept += kept
        total_missing_date += missing_date
        total_wrong_date += wrong_date

    source_reports, headlines = collect_recent_headlines(news_dir, args.target_date, args.lookback_days)
    write_recent_headlines_file(
        output_path=recent_headlines_path,
        target_date=args.target_date,
        lookback_days=args.lookback_days,
        source_reports=source_reports,
        headlines=headlines,
    )

    print("Prepared curation inputs.")
    print(f"raw files scanned: {processed_files}")
    print(f"entries scanned: {total_entries}")
    print(f"entries kept for {args.target_date}: {total_kept}")
    print(f"entries removed (missing date): {total_missing_date}")
    print(f"entries removed (date mismatch): {total_wrong_date}")
    print(f"prior reports found: {len(source_reports)}")
    print(f"prior headlines extracted: {len(headlines)}")
    print(f"recent headlines file: {recent_headlines_path.as_posix()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
