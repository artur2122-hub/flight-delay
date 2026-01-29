from __future__ import annotations

import argparse
from pathlib import Path


import duckdb

def main()-> None:
    parser = argparse.ArgumentParser(description = "Ingest Local VRA CSV into DuckDB")
    parser.add_argument(
        '--csv',
        required = True,
        help = "Path to VRA_YYYYMM.csv (ex: data/raw/VRA_202511.csv)",
    )
    parser.add_argument(
        "--db",
        default = "flight_delay.duckdb",
        help = "DuckDB database file",
    )

    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    con = duckdb.connect(args.db)

    con.execute("""
        CREATE OR REPLACE TEMP TABLE tmp_month AS
        SELECT * FROM read_csv_auto(?, normalize_names = True, all_varchar = True)
        """, [str(csv_path)],
    )

    con.execute("CREATE TABLE IF NOT EXISTS raw_vra AS SELECT * FROM tmp_month WHERE 1=0")
    con.execute("INSERT INTO raw_vra SELECT * FROM tmp_month")

    row_count = con.execute("SELECT COUNT(*) FROM raw_vra").fetchone()[0]
    columns = con.execute("DESCRIBE raw_vra").fetchall()

    print(f"Loaded. raw_vra raw_count: {row_count}\n")
    print("Columns (name,type):")
    for name, dtype, *_ in columns:
        print(f"- {name}: {dtype}")
    con.close()

if __name__ == "__main__":
    main()