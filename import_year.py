"""Import Texas divorce TXT files or official DSHS ZIP archives into SQLite."""
from __future__ import annotations

import argparse
import csv
import io
import itertools
import shlex
import sqlite3
import zipfile
from pathlib import Path
from typing import Iterator

FIELDS = [
    "file_number", "petitioner", "petitioner_age", "respondent", "respondent_age",
    "children_under_18", "marriage_date", "dissolution_date", "county_code", "county_name",
]

# Column starts for the fixed-width DSHS layouts used in these year ranges.
FIXED_WIDTH_LAYOUTS = {
    range(1998, 2002): [0, 13, 45, 57, 89, 101, 123, 138, 153, 174],
    range(2002, 2004): [0, 11, 41, 49, 81, 89, 96, 111, 126, 134],
    range(2004, 2009): [0, 8, 39, 47, 79, 87, 95, 111, 127, 135],
    range(2009, 2011): [0, 7, 39, 42, 74, 77, 80, 91, 102, 106],
}


def clean(values: list[str]) -> tuple[str, ...]:
    return tuple(value.strip().strip('"') for value in (values + [""] * 10)[:10])


def fixed_width(line: str, year: int) -> tuple[str, ...]:
    starts = next((columns for years, columns in FIXED_WIDTH_LAYOUTS.items() if year in years), None)
    if starts is None:
        raise ValueError(f"No fixed-width layout is defined for {year}.")
    return clean([line[starts[i]:starts[i + 1] if i + 1 < len(starts) else None] for i in range(len(starts))])


def parse_lines(lines: Iterator[str], year: int) -> Iterator[tuple[str, ...]]:
    first = next(lines, None)
    if first is None:
        return

    # 2015 onward uses the documented asterisk-delimited layout with a header.
    if "*" in first:
        reader = csv.reader(itertools.chain([first], lines), delimiter="*")
        next(reader, None)
        for row in reader:
            if row:
                yield clean(row)
        return

    # 1968–1997 and 2011 use a ten-column tab-delimited layout.
    if "\t" in first:
        reader = csv.reader(itertools.chain([first], lines), delimiter="\t")
        if "SFN" in first or "File Number" in first:
            next(reader, None)
        for row in reader:
            if row:
                yield clean(row)
        return

    # 2012–2014 use whitespace-separated records with quoted names.  2014 adds
    # husband/wife race columns, which are intentionally omitted from this schema.
    if year in (2012, 2013, 2014):
        for line in lines:
            # POSIX mode treats apostrophes in real names (for example, O'GEAL)
            # as unmatched quote marks.  Non-POSIX mode preserves them.
            row = shlex.split(line, posix=False)
            if year == 2014:
                if len(row) >= 12:
                    yield clean([row[0], row[1], row[2], row[4], row[5], row[7], row[8], row[9], row[10], row[11]])
            elif len(row) >= 10:
                yield clean(row[:10])
        return

    # 1998–2010 are DSHS fixed-width records without headers.
    yield fixed_width(first, year)
    for line in lines:
        if line.strip():
            yield fixed_width(line, year)


def source_members(source: Path) -> Iterator[tuple[str, io.TextIOBase]]:
    if source.suffix.lower() != ".zip":
        yield source.name, source.open("r", encoding="latin1", newline="")
        return
    archive = zipfile.ZipFile(source)
    for member in archive.infolist():
        if not member.is_dir() and member.filename.lower().endswith((".txt", ".csv")):
            yield member.filename, io.TextIOWrapper(archive.open(member), encoding="latin1", newline="")


def import_file(source: Path, database: Path, year: str) -> int:
    year_number = int(year)
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database)
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS divorces (
            id INTEGER PRIMARY KEY,
            source_year TEXT NOT NULL,
            file_number TEXT, petitioner TEXT, petitioner_age TEXT,
            respondent TEXT, respondent_age TEXT, children_under_18 TEXT,
            marriage_date TEXT, dissolution_date TEXT, county_code TEXT, county_name TEXT,
            UNIQUE(source_year, file_number, petitioner, respondent, dissolution_date, county_code)
        );
        CREATE INDEX IF NOT EXISTS idx_divorces_year ON divorces(source_year);
        CREATE INDEX IF NOT EXISTS idx_divorces_county ON divorces(county_name);
        CREATE INDEX IF NOT EXISTS idx_divorces_petitioner ON divorces(petitioner);
        CREATE INDEX IF NOT EXISTS idx_divorces_respondent ON divorces(respondent);
        CREATE INDEX IF NOT EXISTS idx_divorces_file_number ON divorces(file_number);
    """)
    before = connection.total_changes
    sql = f"INSERT OR IGNORE INTO divorces (source_year, {', '.join(FIELDS)}) VALUES ({', '.join(['?'] * 11)})"
    for _member, handle in source_members(source):
        with handle:
            rows = ((year, *row) for row in parse_lines(iter(handle), year_number))
            connection.executemany(sql, rows)
    connection.commit()
    inserted = connection.total_changes - before
    connection.close()
    return inserted


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--year", required=True)
    parser.add_argument("--database", type=Path, default=Path("data/texas_divorces.sqlite3"))
    args = parser.parse_args()
    print(f"Imported {import_file(args.source, args.database, args.year):,} records.")
