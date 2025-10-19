import os
import argparse
from fact_table import FactTable
from query_io import read_schema_from_txt, run_queries_from_txt


DATA = "data_large.csv"
SCHEMA = "schema.txt"
QUERIES = "queries.txt"


def load_table(data_path: str, schema_path: str | None):
    if schema_path and os.path.exists(schema_path):
        schema = read_schema_from_txt(schema_path)
        return FactTable.load_from_csv(data_path, schema=schema)
    return FactTable.load_from_csv(data_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LSM Index – Projekat BP2")
    parser.add_argument("--data", default=DATA, help="Putanja do CSV fajla (default: data.csv)")
    parser.add_argument("--schema", default=SCHEMA, help="Putanja do schema.txt (opciono)")
    parser.add_argument("--queries", default=QUERIES, help="Putanja do queries.txt (opciono)")
    parser.add_argument("--no-index", action="store_true", help="Pokretanje demo moda bez indeksa")
    args = parser.parse_args()

    print("Učitavanje podataka iz", args.data)

    ft = load_table(args.data, args.schema if os.path.exists(args.schema) else None)

    print("Ukupno redova:", len(ft.select()))
    ft.print_level_sizes()

    if os.path.exists(args.queries):
        print("Izvršavanje upita iz", args.queries)

        run_queries_from_txt(ft, args.queries)

        print("Stanje nakon izvršavanja upita")


        print("Posle queries.txt -> ukupno redova:", len(ft.select()))
        ft.print_level_sizes()

    else:
        use_index = not args.no_index
        print("\n[DEMO MOD] Pokretanje nekoliko osnovnih operacija...\n")

        res = ft.select(preds=[("D1", "x1"), ("D2", "y1")],
                        ops=["AND"], use_index=use_index)
        print(f"SELECT D1=x1 AND D2=y1 (use_index={use_index}) -> {len(res)} redova")

        s = ft.select(preds=[("D1", "x1")],
                      aggregate=("SUM", "Fact1"), use_index=use_index)
        print(f"SUM(Fact1) WHERE D1=x1 (use_index={use_index}): {s}")

        ft.delete([("D1", "x1")])
        print(f"Nakon DELETE D1=x1:")
        print("   Sa indeksom:", len(ft.select([("D1", "x1")], use_index=True)))
        print("   Bez indeksa:", len(ft.select([("D1", "x1")], use_index=False)))

