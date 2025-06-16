from typing import List

from rag.db import PgVectorStore
from rag.embed import embed


class Retriever:
    def __init__(self, store: PgVectorStore, k: int = 3):
        self.store, self.k = store, k

    def query(self, q: str) -> List[str]:
        qv = embed([q])
        hits = self.store.search(qv, self.k)
        return [txt for txt, _ in hits]
