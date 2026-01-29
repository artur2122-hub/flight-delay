from pathlib import Path
import argparse
import duckdb



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default = "flight_delay.duckdb")
    ap.add_argument("--dir", default="sql")
    args = ap.parse_args()

    sql_dir = Path(args.dir)
    files = sorted([p for p in sql_dir.glob("*.sql") if p.name != "debuq.sql"])

    if not files:
        raise FileNotFoundError(f"No .sql files found in {sql_dir.resolve()}")
    
    con = duckdb.connect(args.db)

    for p in files:
        sql = p.read_text(encoding = "utf-8")
        con.execute(sql)
        print(f"Ran: {p}")

    con.close()
    print("Done.")

if __name__ == "__main__":
    main()