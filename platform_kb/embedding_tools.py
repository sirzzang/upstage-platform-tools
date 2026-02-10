"""문서 청킹(Chunking) + Upstage Embedding API 호출 모듈.

RAG 파이프라인에서 문서를 벡터 DB에 저장하기 전 단계를 담당한다:
  1. 청킹: 긴 문서를 의미 단위의 작은 조각(chunk)으로 분할
  2. 임베딩: 각 청크를 Upstage Embedding API로 4096차원 벡터로 변환

왜 청킹이 필요한가?
  - LLM 컨텍스트 윈도우에 크기 제한이 있어 문서 전체를 넣을 수 없다.
  - 임베딩 모델은 짧은 텍스트일수록 의미를 더 정확히 포착한다.
  - 검색 시 문서 전체가 아닌 관련 부분만 정확히 찾아낼 수 있다.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.client import client

# ── 청킹 설정 ──────────────────────────────────────────────
# 청크 최대 길이 (글자 수 기준).
# 너무 크면 임베딩 정확도가 떨어지고, 너무 작으면 문맥이 유실된다.
# 500자는 마크다운 문서의 한 섹션이 대체로 들어가는 적당한 크기.
MAX_CHUNK_LENGTH = 500


# ── 문서 청킹 ──────────────────────────────────────────────


def chunk_document(text: str, file_name: str) -> list[dict]:
    """마크다운 문서를 섹션 기준으로 청킹합니다.

    전략:
    1. ## 헤딩 기준으로 섹션 분할
    2. 각 섹션이 MAX_CHUNK_LENGTH 초과 시 단락(\n\n) 기준으로 재분할
    3. 각 청크에 file_name + section 메타데이터 부착 → 나중에 출처 추적에 활용

    Returns:
        [{"text": "청크 본문", "metadata": {"file_name": ..., "section": ...}}, ...]
    """
    # 마크다운 ## 헤딩 직전 위치에서 분할 (lookahead 정규식)
    # (?=^## ) : "## "로 시작하는 줄 직전을 분할 지점으로 인식
    # 예: "## Overview\n..." → ["## Overview\n...", "## Symptoms\n...", ...]
    sections = re.split(r"(?=^## )", text, flags=re.MULTILINE)

    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue

        # 섹션 제목 추출
        lines = section.split("\n", 1)
        title_line = lines[0].strip()
        if title_line.startswith("## "):
            section_title = title_line[3:].strip()
        elif title_line.startswith("# "):
            section_title = title_line[2:].strip()
        else:
            section_title = title_line[:50]

        # 섹션이 짧으면 그대로 하나의 청크
        if len(section) <= MAX_CHUNK_LENGTH:
            chunks.append(
                {
                    "text": section,
                    "metadata": {
                        "file_name": file_name,
                        "section": section_title,
                    },
                }
            )
        else:
            # 긴 섹션은 단락 단위로 재분할
            sub_chunks = _split_long_text(section, MAX_CHUNK_LENGTH)
            for i, sub in enumerate(sub_chunks):
                chunks.append(
                    {
                        "text": sub,
                        "metadata": {
                            "file_name": file_name,
                            "section": f"{section_title} (part {i + 1})",
                        },
                    }
                )

    return chunks


def _split_long_text(text: str, max_len: int) -> list[str]:
    """긴 텍스트를 단락(\n\n) 기준으로 분할하되, max_len을 넘지 않도록.

    그리디(greedy) 방식: 현재 청크에 다음 단락을 추가했을 때
    max_len을 초과하면 현재 청크를 확정하고 새 청크를 시작한다.
    """
    paragraphs = text.split("\n\n")
    result = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # 현재 청크 + 다음 단락이 max_len을 초과하면 → 현재 청크 확정
        if current and len(current) + len(para) + 2 > max_len:
            result.append(current.strip())
            current = para
        else:
            # 아직 여유가 있으면 단락을 이어붙임
            current = f"{current}\n\n{para}" if current else para

    # 마지막 남은 텍스트 처리
    if current.strip():
        result.append(current.strip())

    return result


# ── Upstage Embedding API 호출 ─────────────────────────────
#
# Upstage는 비대칭(asymmetric) 임베딩 모델을 제공한다:
#   - embedding-passage : 저장할 문서(긴 텍스트)용
#   - embedding-query   : 검색 쿼리(짧은 질문)용
#
# 왜 모델이 두 개인가?
#   질문("CrashLoopBackOff 대응법?")과 문서("## Diagnosis Steps\n...")는
#   텍스트 길이와 문체가 다르다. 각각에 최적화된 모델을 쓰면
#   질문↔문서 간 의미 매칭 정확도가 단일 모델 대비 높아진다.
#
# 두 모델은 동일한 4096차원 벡터 공간을 공유하므로
# cosine similarity로 query↔passage 간 유사도를 직접 비교할 수 있다.


def embed_chunks(chunks: list[dict]) -> list[list[float]]:
    """청크 텍스트 목록을 passage 모델로 임베딩합니다 (배치).

    Returns:
        4096차원 임베딩 벡터 리스트 (chunks와 1:1 대응)
    """
    texts = [c["text"] for c in chunks]
    if not texts:
        return []

    # [Upstage API] Embeddings (passage)
    # - model: "embedding-passage" — 문서 저장 전용 임베딩 모델
    # - input: 텍스트 리스트를 배치로 전달 (한 번의 API 호출로 다수 청크 처리)
    # - 반환값: 각 텍스트에 대응하는 4096차원 float 벡터
    response = client.embeddings.create(
        model="embedding-passage",
        input=texts,
    )
    return [d.embedding for d in response.data]


def embed_query(query: str) -> list[float]:
    """검색 쿼리를 query 모델로 임베딩합니다.

    Returns:
        4096차원 임베딩 벡터 (단일)
    """
    # [Upstage API] Embeddings (query)
    # - model: "embedding-query" — 검색 쿼리 전용 임베딩 모델
    # - input: 단건 문자열 (사용자의 질문)
    # - passage 모델과 동일한 벡터 공간을 공유하므로
    #   cosine similarity로 query↔passage 간 유사도를 직접 비교할 수 있다
    response = client.embeddings.create(
        model="embedding-query",
        input=query,
    )
    return response.data[0].embedding
