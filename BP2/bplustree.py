from dataclasses import dataclass, field
from typing import List, Optional, Any, Iterator, Tuple
import bisect

LEAF_CAPACITY = 4
INTERNAL_CAPACITY = 3

@dataclass
class LeafEntry:
    key: Any
    ids: List[int]

@dataclass
class BNode:
    keys: List[Any]
    entries: List[LeafEntry] = field(default_factory=list)
    children: List["BNode"] = field(default_factory=list)
    isLeaf: bool = False
    next_leaf: Optional["BNode"] = None

class BPlusTree:
    def __init__(self, root: Optional[BNode] = None):
        self.root = root

    def getAllData(self):
        out = []
        def dfs(node):
            if node.isLeaf:
                for e in node.entries:
                    for id in e.ids:
                        out.append((e.key, id))
            else:
                for child in node.children:
                    dfs(child)
        if self.root:
            dfs(self.root)
        return out

    @staticmethod
    def groupDataById(pairs):
        pairs.sort(key=lambda x: (x[0], x[1]))
        out, key, ids = [], None, []
        for k, id in pairs:
            if k != key:
                if key is not None:
                    out.append((key, ids))
                key, ids = k, [id]
            else:
                if not ids or ids[-1] != id:
                    ids.append(id)
        if key is not None:
            out.append((key, ids))
        return out

    @staticmethod
    def findFirst(keys, key):
        low, high = 0, len(keys)
        while low < high:
            mid = (low + high) // 2
            if keys[mid] < key:
                low = mid + 1
            else:
                high = mid
        return low

    @classmethod
    def buildInternal(cls, children: List[BNode]) -> List[BNode]:
        nodes = []
        for i in range(0, len(children), INTERNAL_CAPACITY):
            chunk = children[i:i+INTERNAL_CAPACITY]
            delim = [child.keys[0] for child in chunk[1:]]
            nodes.append(BNode(keys=delim, children=chunk, isLeaf=False))
        return nodes

    @classmethod
    def bulkLoad(cls, pairs):
        if not pairs:
            return cls(None)
        grouped = cls.groupDataById(pairs)
        leaves = []
        for i in range(0, len(grouped), LEAF_CAPACITY):
            chunk = grouped[i:i+LEAF_CAPACITY]
            keys = [k for k, _ in chunk]
            entries = [LeafEntry(key=k, ids=ids) for k, ids in chunk]
            leaves.append(BNode(keys=keys, entries=entries, isLeaf=True))
        for i in range(len(leaves) - 1):
            leaves[i].next_leaf = leaves[i + 1]
        if len(leaves) == 1:
            return cls(leaves[0])
        level = leaves
        while len(level) > 1:
            level = cls.buildInternal(level)
        return cls(level[0])

    def find(self, key) -> List[int]:
        node = self.root
        if node is None:
            return []
        while not node.isLeaf:
            i = self.findFirst(node.keys, key)
            node = node.children[i]
        i = self.findFirst(node.keys, key)
        if i < len(node.keys) and node.keys[i] == key:
            return node.entries[i].ids
        return []

    def insertRecursive(self, node, key, value):
        if node.isLeaf:
            i = self.findFirst(node.keys, key)
            if i < len(node.keys) and node.keys[i] == key:
                ids = node.entries[i].ids
                pos = bisect.bisect_left(ids, value)
                if pos == len(ids) or ids[pos] != value:
                    ids.insert(pos, value)
                    return (None, None, True)
                return (None, None, False)
            node.keys.insert(i, key)
            node.entries.insert(i, LeafEntry(key=key, ids=[value]))
            if len(node.keys) <= LEAF_CAPACITY:
                return (None, None, True)
            mid = (len(node.keys) + 1) // 2
            right = BNode(keys=node.keys[mid:], entries=node.entries[mid:], isLeaf=True, next_leaf=node.next_leaf)
            node.keys = node.keys[:mid]
            node.entries = node.entries[:mid]
            node.next_leaf = right
            return (right.keys[0], right, True)
        i = self.findFirst(node.keys, key)
        promoted, right, inserted_new = self.insertRecursive(node.children[i], key, value)
        if promoted is None:
            return (None, None, inserted_new)
        node.keys.insert(i, promoted)
        node.children.insert(i+1, right)
        if len(node.keys) <= INTERNAL_CAPACITY - 1:
            return (None, None, inserted_new)
        mid = len(node.keys) // 2
        promote_key = node.keys[mid]
        right = BNode(keys=node.keys[mid+1:], children=node.children[mid+1:], isLeaf=False)
        node.keys = node.keys[:mid]
        node.children = node.children[:mid+1]
        return (promote_key, right, inserted_new)

    def insert(self, key, value) -> bool:
        if self.root is None:
            self.root = BNode(keys=[key], entries=[LeafEntry(key=key, ids=[value])], isLeaf=True)
            return True
        promoted, right, inserted_new = self.insertRecursive(self.root, key, value)
        if promoted is not None:
            self.root = BNode(keys=[promoted], children=[self.root, right], isLeaf=False)
        return inserted_new

    def delete(self, key, value) -> bool:
        node = self.root
        if node is None:
            return False
        while not node.isLeaf:
            i = self.findFirst(node.keys, key)
            node = node.children[i]
        i = self.findFirst(node.keys, key)
        if i >= len(node.keys) or node.keys[i] != key:
            return False
        ids = node.entries[i].ids
        pos = bisect.bisect_left(ids, value)
        if pos >= len(ids) or ids[pos] != value:
            return False
        ids.pop(pos)
        if not ids:
            del node.keys[i]
            del node.entries[i]
        return True

    def items(self) -> Iterator[Tuple[Any, List[int]]]:
        node = self.root
        if node is None:
            return
        while not node.isLeaf:
            node = node.children[0]
        while node:
            for e in node.entries:
                yield e.key, list(e.ids)
            node = node.next_leaf
