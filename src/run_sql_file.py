from pathlib import Path
import argparse
import duckdb

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default = 'flight_delay.duckdb')
    ap.add_argument('--sql', required = True, help = 'Path to .sql file')
    args = ap.parse_args()

    sql_path = Path(args.sql)
    sql_text = sql_path.read_text(encoding = 'utf-8')

    con = duckdb.connect(args.db)
    con.execute(sql_text)
    con.close()

    print(f'Ran: {sql_path}')

if __name__ == '__main__':
    main()