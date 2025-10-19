from typing import Any, List, Set, Iterator, Tuple
from bplustree import BPlusTree


class LSMLevel:

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.tree = BPlusTree()
        self.size = 0

    def insert(self, key: Any, row_id: int) -> None:
        inserted = self.tree.insert(key, row_id)
        if inserted:
            self.size += 1

    def delete(self, key: Any, row_id: int) -> None:
        existed_here = row_id in set(self.tree.find(key))
        if existed_here and self.tree.delete(key, row_id):
            self.size = max(0, self.size - 1)

    def search(self, key: Any) -> Set[int]:
        return set(self.tree.find(key))

    def items(self) -> Iterator[Tuple[Any, Set[int]]]:
        for k, ids in self.tree.items():
            yield k, set(ids)


class LSMIndex:
    def __init__(self, column: str, base_capacity: int = 1000, max_total: int = 13000):
        self.column = column
        self.levels: List[LSMLevel] = []
        cap, total = base_capacity, 0
        while total < max_total:
            self.levels.append(LSMLevel(capacity=cap))
            total += cap
            cap *= 3


    def insert(self, key: Any, row_id: int) -> None:
        l0 = self.levels[0]

        if l0.size >= l0.capacity:
            self._merge_level(0)

        l0.insert(key, row_id)

    def delete(self, key: Any, row_id: int) -> None:
        for lvl in self.levels:
            lvl.delete(key, row_id)

    def search(self, key: Any) -> Set[int]:
        out: Set[int] = set()
        for lvl in self.levels:
            out |= lvl.search(key)
        return out

    def level_sizes(self) -> List[int]:
        return [lvl.size for lvl in self.levels]


    def _merge_level(self, i: int) -> None:

        if i + 1 >= len(self.levels):
            return

        src, dst = self.levels[i], self.levels[i + 1]

        merged_pairs: List[Tuple[Any, int]] = []
        count = 0
        for k, ids in src.items():
            for rid in ids:
                merged_pairs.append((k, rid))
                count += 1
                if count >= src.capacity:
                    break
            if count >= src.capacity:
                break

        if not merged_pairs:
            return

        for k, ids in dst.items():
            for rid in ids:
                merged_pairs.append((k, rid))

        new_tree = BPlusTree.bulkLoad(merged_pairs)
        new_size = sum(len(ids) for _, ids in new_tree.items())

        self.levels[i + 1].tree = new_tree
        self.levels[i + 1].size = new_size
        self.levels[i].tree = BPlusTree()
        self.levels[i].size = 0

        if self.levels[i + 1].size >= self.levels[i + 1].capacity:
            self._merge_level(i + 1)
