"""JSON 파일 기반 경량 벡터 저장소 모듈.

임베딩 벡터를 저장하고, 코사인 유사도 기반으로 유사 문서를 검색한다.

프로덕션에서는 Pinecone, Weaviate, ChromaDB, FAISS 등 전용 벡터 DB를 사용하지만,
이 프로젝트에서는 학습 목적으로 순수 Python + JSON 파일로 구현한다.

검색 방식:
  전수 비교(brute-force) — 모든 저장 벡터와 쿼리 벡터 간
  코사인 유사도를 계산하고 상위 N개를 반환한다.
  문서 수가 수만 건 이하일 때 충분히 빠르다.
"""

import json
import math
import os


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """두 벡터의 코사인 유사도를 계산한다.

    공식: cosine_similarity = (A · B) / (|A| × |B|)
      - 1에 가까울수록 의미가 유사
      - 0이면 무관
      - -1이면 반대 의미

    참고: Upstage 임베딩은 이미 L2 정규화(unit vector)되어 있으므로
    |A| = |B| = 1 이고, dot product만으로도 코사인 유사도와 동일하다.
    아래 코드는 범용성을 위해 정규화 미적용 벡터도 처리할 수 있도록
    명시적으로 norm을 계산한다.
    """
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class VectorStore:
    """JSON 파일 기반 벡터 저장소.

    ChromaDB가 Python 3.14와 호환되지 않아
    순수 Python으로 구현한 경량 벡터 스토어입니다.
    cosine similarity 기반 검색을 지원합니다.

    저장 구조 (store_data/index.json):
        [
            {
                "id": "doc_name_0",
                "text": "청크 원문 텍스트",
                "embedding": [0.012, -0.034, ...],  # 4096차원 float 벡터
                "metadata": {"doc_name": "...", "section": "..."}
            },
            ...
        ]
    """

    def __init__(self, persist_dir: str | None = None):
        # 저장 디렉토리 기본값: 이 파일과 같은 경로의 store_data/
        if persist_dir is None:
            persist_dir = os.path.join(os.path.dirname(__file__), "store_data")

        os.makedirs(persist_dir, exist_ok=True)
        self.persist_dir = persist_dir
        self.index_path = os.path.join(persist_dir, "index.json")
        # 시작 시 기존 인덱스 파일에서 데이터를 메모리로 로드
        self._data = self._load()

    def _load(self) -> list[dict]:
        """JSON 인덱스 파일에서 데이터를 로드합니다."""
        if os.path.isfile(self.index_path):
            with open(self.index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save(self):
        """데이터를 JSON 인덱스 파일에 저장합니다."""
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False)

    def add_documents(
        self,
        chunks: list[dict],
        embeddings: list[list[float]],
        doc_name: str,
    ) -> int:
        """청크 + 임베딩을 벡터 스토어에 저장합니다.

        Args:
            chunks: [{"text": ..., "metadata": {...}}, ...]
            embeddings: 각 청크에 대응하는 임베딩 벡터 리스트
            doc_name: 문서 고유 이름

        Returns:
            저장된 청크 수
        """
        # 같은 이름의 문서가 이미 있으면 먼저 삭제 (덮어쓰기 = upsert 동작)
        self.delete_document(doc_name)

        # 청크와 임베딩을 1:1로 묶어 저장
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            meta = dict(chunk.get("metadata", {}))
            meta["doc_name"] = doc_name  # 문서 단위 삭제/조회를 위한 식별자
            self._data.append(
                {
                    "id": f"{doc_name}_{i}",  # 고유 ID: 문서명_청크번호
                    "text": chunk["text"],     # 청크 원문 (검색 결과 표시용)
                    "embedding": emb,          # 4096차원 임베딩 벡터 (검색용)
                    "metadata": meta,          # 출처 정보 (doc_name, section 등)
                }
            )

        self._save()
        return len(chunks)

    def search(
        self, query_embedding: list[float], n_results: int = 5
    ) -> list[dict]:
        """쿼리 임베딩으로 유사 청크를 검색합니다.

        Returns:
            [{"text": ..., "metadata": {...}, "distance": float}, ...]
            distance는 1 - cosine_similarity (낮을수록 유사)
        """
        if not self._data:
            return []

        # 전수 비교(brute-force): 저장된 모든 청크와 쿼리 간 유사도 계산
        # 대규모 데이터에서는 FAISS, HNSW 등 ANN(Approximate Nearest Neighbor) 알고리즘을 사용
        scored = []
        for item in self._data:
            sim = _cosine_similarity(query_embedding, item["embedding"])
            # cosine distance = 1 - cosine similarity
            # distance가 0에 가까울수록 유사, 1에 가까울수록 비유사
            distance = 1.0 - sim
            scored.append(
                {
                    "text": item["text"],
                    "metadata": item["metadata"],
                    "distance": distance,
                }
            )

        # 거리 오름차순 (= 유사도 내림차순) 정렬 후 상위 N개 반환
        scored.sort(key=lambda x: x["distance"])
        return scored[:n_results]

    def list_documents(self) -> dict[str, int]:
        """저장된 문서별 청크 수를 반환합니다.

        Returns:
            {"doc_name": chunk_count, ...}
        """
        doc_counts: dict[str, int] = {}
        for item in self._data:
            name = item["metadata"].get("doc_name", "unknown")
            doc_counts[name] = doc_counts.get(name, 0) + 1
        return doc_counts

    def delete_document(self, doc_name: str) -> int:
        """특정 문서의 모든 청크를 삭제합니다.

        Returns:
            삭제된 청크 수
        """
        before = len(self._data)
        self._data = [
            item
            for item in self._data
            if item["metadata"].get("doc_name") != doc_name
        ]
        deleted = before - len(self._data)
        if deleted > 0:
            self._save()
        return deleted

    def reset(self):
        """벡터 스토어를 초기화합니다 (모든 데이터 삭제)."""
        self._data = []
        self._save()
