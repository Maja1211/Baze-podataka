import csv, re
from typing import Any, Dict, List, Optional, Set, Tuple
from lsm_index import LSMIndex

class FactTable:
    def __init__(self, schema: List[str]):
        self.schema = schema
        self.data: Dict[int, Dict[str, Any]] = {}
        self.next_id = 0
        self.indexes: Dict[str, LSMIndex] = {}
        self._create_indexes_from_schema()

    def _create_indexes_from_schema(self) -> None:
        for col in self.schema:
            if re.fullmatch(r"D\d+", col):
                self.indexes[col] = LSMIndex(column=col, base_capacity=1000, max_total=13000)

    @staticmethod
    def _maybe_int(x: Any):
        if isinstance(x, str) and x.isdigit():
            return int(x)
        return x

    @classmethod
    def load_from_csv(cls, path: str, schema: Optional[List[str]] = None) -> "FactTable":
        if schema is None:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                schema = reader.fieldnames or []
        ft = cls(schema)
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                r = {k: cls._maybe_int(v) for k, v in r.items()}
                ft.insert(r)
        return ft

    def insert(self, row: Dict[str, Any]) -> None:
        rid = row.get("ID", self.next_id)
        row["ID"] = rid
        self.data[rid] = row
        for col, idx in self.indexes.items():
            key = row.get(col)
            if key is not None:
                idx.insert(key, rid)
        if rid >= self.next_id:
            self.next_id = rid + 1

    def _ids_indexed(self, preds: List[Tuple[str, Any]], ops: Optional[List[str]]) -> Set[int]:
        if not preds:
            return set(self.data.keys())
        sets: List[Set[int]] = []
        for col, val in preds:
            if col in self.indexes:
                s = self.indexes[col].search(val)
            else:
                s = {rid for rid, row in self.data.items() if row.get(col) == val}
            sets.append(s)
        out = sets[0].copy()
        if ops:
            for op, s in zip(ops, sets[1:]):
                if op.upper() == "AND":
                    out &= s
                elif op.upper() == "OR":
                    out |= s
                else:
                    raise ValueError(f"Nepoznata logička operacija: {op}")
        return out

    def _ids_scan(self, preds: List[Tuple[str, Any]], ops: Optional[List[str]]) -> Set[int]:
        if not preds:
            return set(self.data.keys())
        sets: List[Set[int]] = []
        for col, val in preds:
            s = {rid for rid, row in self.data.items() if row.get(col) == val}
            sets.append(s)
        out = sets[0].copy()
        if ops:
            for op, s in zip(ops, sets[1:]):
                if op.upper() == "AND":
                    out &= s
                elif op.upper() == "OR":
                    out |= s
                else:
                    raise ValueError(f"Nepoznata logička operacija: {op}")
        return out

    def delete(self, preds: List[Tuple[str, Any]], ops: Optional[List[str]] = None) -> int:
        target = self._ids_indexed(preds, ops)
        removed = 0
        to_remove = []
        for rid in target:
            if rid in self.data:
                to_remove.append((rid, self.data[rid]))
        for rid, row in to_remove:
            del self.data[rid]
            removed += 1
            for col, idx in self.indexes.items():
                key = row.get(col)
                if key is not None:
                    idx.delete(key, rid)
        return removed

    def select(self,
               preds: Optional[List[Tuple[str, Any]]] = None,
               ops: Optional[List[str]] = None,
               aggregate: Optional[Tuple[str, str]] = None,
               use_index: bool = True):
        preds = preds or []

        for c, _ in preds:
            if not re.fullmatch(r"D\d+", c):
                raise ValueError("Uslovi u WHERE moraju biti nad D* kolonama (indeksiranim)")

        if aggregate is not None:
            func, col = aggregate
            if not re.fullmatch(r"Fact\d+", col):
                raise ValueError("Agregatne funkcije se moraju primenjivati nad Fact* kolonama")


        ids = self._ids_indexed(preds, ops) if use_index else self._ids_scan(preds, ops)
        rows = [self.data[rid] for rid in ids if rid in self.data]

        if not aggregate:
            return rows

        func, col = aggregate
        vals = [r[col] for r in rows if col in r]
        if not vals:
            return None
        func = func.upper()
        if func == "MIN":   return min(vals)
        if func == "MAX":   return max(vals)
        if func == "SUM":   return sum(vals)
        if func == "COUNT": return len(vals)
        if func == "AVG":   return sum(vals) / len(vals)
        raise ValueError(f"Nepoznata agregatna funkcija: {func}")

    def print_level_sizes(self) -> None:
        print("\nPregled popunjenosti LSM indeksa:")
        for col, idx in self.indexes.items():
            print(f"\nKolona {col}:")
            for level, size in enumerate(idx.level_sizes()):
                print(f"  • Nivo L{level} → {size} zapisa")
