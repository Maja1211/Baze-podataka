from typing import Any, List, Tuple, Optional

def read_schema_from_txt(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]
    if not lines:
        raise ValueError("Prazan schema.txt")
    if len(lines) == 1 and "," in lines[0]:
        return [p.strip() for p in lines[0].split(",")]
    if lines[0].lower().startswith("columns:"):
        return [p.strip() for p in lines[0].split(":", 1)[1].split(",")]
    return lines

def _parse_value(x: str) -> Any:
    return int(x) if x.isdigit() else x

def parse_conditions(tokens: List[str]) -> Tuple[List[Tuple[str, Any]], List[str]]:
    preds: List[Tuple[str, Any]] = []
    ops: List[str] = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t.upper() in ("AND", "OR"):
            ops.append(t.upper())
            i += 1
            continue
        if "=" in t:
            col, val = t.split("=", 1)
            preds.append((col, _parse_value(val)))
            i += 1
            continue
        if i + 2 < len(tokens) and tokens[i+1] == "=":
            col = tokens[i]
            val = tokens[i+2]
            preds.append((col, _parse_value(val)))
            i += 3
            continue
        i += 1
    return preds, ops

def _parse_assignments(tokens: List[str]) -> dict:
    row = {}
    for t in tokens:
        if "=" in t:
            k, v = t.split("=", 1)
            row[k] = _parse_value(v)
    return row

def run_queries_from_txt(ft, path: str) -> None:
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            tokens = line.split()
            cmd = tokens[0].upper()

            if cmd == "INSERT":
                row = _parse_assignments(tokens[1:])
                if not row:
                    print("INSERT -> nema vrednosti")
                    continue
                ft.insert(row)
                rid = row.get("ID", None)
                print(f"INSERT -> ubačen red (ID={rid if rid is not None else ft.next_id-1})")
                continue

            use_index = True
            if len(tokens) > 1 and tokens[1].lower().startswith("use_index="):
                use_index = tokens[1].split("=", 1)[1] in ("1","true","True")
                tokens = [tokens[0]] + tokens[2:]

            where_pos = None
            agg_pos = None
            for i, t in enumerate(tokens):
                if t.upper() == "WHERE": where_pos = i
                if t.upper() == "AGG":   agg_pos = i

            from typing import Tuple as _T
            preds: List[Tuple[str, Any]] = []
            ops: List[str] = []
            agg: Optional[_T[str, str]] = None

            if where_pos is not None:
                cond_tokens = tokens[where_pos + 1: agg_pos if agg_pos is not None else None]
                preds, ops = parse_conditions(cond_tokens)

            if agg_pos is not None:
                if len(tokens) >= agg_pos + 3:
                    func = tokens[agg_pos + 1].upper()
                    fact_col = tokens[agg_pos + 2]
                    agg = (func, fact_col)
                else:
                    raise ValueError("Pogrešan AGG format (AGG FUNC FactCol)")

            if cmd == "SELECT":
                res = ft.select(preds, ops, agg, use_index)
                if agg is None:
                    print(f"SELECT -> {len(res)} redova")
                    for r in res[:3]:
                        print("  ", r)
                    if len(res) > 3:
                        print("  ...")
                else:
                    print(f"SELECT AGG={agg[0]}({agg[1]}) -> {res}")
            elif cmd == "DELETE":
                removed = ft.delete(preds, ops)
                print(f"DELETE -> uklonjeno {removed} redova")
            else:
                print(f"Nepoznata komanda: {cmd}")
