import base64
import json
import os
import sys

import requests as http_requests
from openai import OpenAI
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from iac_doc_intel.schemas import CLASSIFICATION_SCHEMA, EXTRACTION_SCHEMAS

load_dotenv()

# Document AI 전용 v2 클라이언트
# document-classify, information-extract 모델은 v2 API에서만 동작
client = OpenAI(
    api_key=os.environ["UPSTAGE_API_KEY"],
    base_url="https://api.upstage.ai/v2",
)


def classify_document(file_path: str, tracker=None) -> str:
    """문서 유형을 분류합니다 (document-classify API)."""
    if not os.path.isfile(file_path):
        return f"[오류] 파일이 존재하지 않습니다: {file_path}"

    try:
        with open(file_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()

        # [Upstage API] Document Classification
        # PDF/이미지를 IaC 문서 유형(terraform/kubernetes/ansible)으로 분류
        response = client.chat.completions.create(
            model="document-classify",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:application/octet-stream;base64,{b64}"
                            },
                        }
                    ],
                }
            ],
            response_format=CLASSIFICATION_SCHEMA,
        )
        if tracker:
            tracker.track_doc("document-classify", 1)
        result = response.choices[0].message.content
        return f"[분류 결과]\n{result}"
    except Exception as e:
        return f"[분류 오류] {e}"


def parse_document(
    file_path: str, output_formats: list[str] | None = None, tracker=None
) -> str:
    """문서를 파싱하여 텍스트를 추출합니다 (document-parse REST API)."""
    if not os.path.isfile(file_path):
        return f"[오류] 파일이 존재하지 않습니다: {file_path}"

    if not output_formats:
        output_formats = ["text", "markdown"]

    api_key = os.environ.get("UPSTAGE_API_KEY", "")
    if not api_key:
        return "[오류] UPSTAGE_API_KEY가 설정되지 않았습니다."

    try:
        with open(file_path, "rb") as f:
            # [Upstage API] Document Digitization (REST API)
            # PDF/이미지에서 텍스트와 마크다운을 추출 (OCR 포함)
            response = http_requests.post(
                "https://api.upstage.ai/v1/document-ai/document-parse",
                headers={"Authorization": f"Bearer {api_key}"},
                files={"document": f},
                data={
                    "model": "document-parse",
                    "output_formats": json.dumps(output_formats),
                    "ocr": "auto",
                },
                timeout=60,
            )

        if response.status_code != 200:
            return f"[파싱 오류] HTTP {response.status_code}: {response.text[:300]}"

        result = response.json()
        content = result.get("content", {})

        parts = []
        if "text" in content:
            parts.append(f"[텍스트]\n{content['text']}")
        if "markdown" in content:
            parts.append(f"[마크다운]\n{content['markdown']}")
        if "html" in content:
            parts.append(f"[HTML]\n{content['html'][:500]}...")

        pages = result.get("usage", {}).get("pages", "?")
        if tracker and isinstance(pages, int):
            tracker.track_doc("document-parse", pages)
        parts.insert(0, f"[파싱 완료] {pages} 페이지 처리됨")

        return "\n\n".join(parts) if parts else f"[파싱 결과]\n{json.dumps(result, indent=2, ensure_ascii=False)[:1000]}"
    except Exception as e:
        return f"[파싱 오류] {e}"


def extract_information(file_path: str, doc_type: str | None = None, tracker=None) -> str:
    """IaC 문서에서 구조화된 데이터를 추출합니다 (information-extract API)."""
    if not os.path.isfile(file_path):
        return f"[오류] 파일이 존재하지 않습니다: {file_path}"

    # doc_type이 없으면 먼저 분류
    if not doc_type:
        classify_result = classify_document(file_path, tracker=tracker)
        try:
            # 분류 결과에서 카테고리 추출
            result_json = json.loads(
                classify_result.replace("[분류 결과]\n", "")
            )
            doc_type = result_json.get("category", "unknown")
        except (json.JSONDecodeError, AttributeError):
            doc_type = "unknown"

    schema = EXTRACTION_SCHEMAS.get(doc_type)
    if not schema:
        return f"[오류] '{doc_type}' 유형에 대한 추출 스키마가 없습니다. 지원: {list(EXTRACTION_SCHEMAS.keys())}"

    try:
        with open(file_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()

        # [Upstage API] Information Extraction
        # IaC 문서에서 리소스, 설정값 등 구조화된 데이터를 추출
        response = client.chat.completions.create(
            model="information-extract",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:application/octet-stream;base64,{b64}"
                            },
                        }
                    ],
                }
            ],
            response_format=schema,
        )
        if tracker:
            tracker.track_doc("information-extract", 1)
        result = response.choices[0].message.content
        return f"[정보 추출 결과] (유형: {doc_type})\n{result}"
    except Exception as e:
        return f"[추출 오류] {e}"


def analyze_iac_document(file_path: str, tracker=None) -> str:
    """IaC 문서를 종합 분석합니다 (분류 → 파싱 → 추출)."""
    if not os.path.isfile(file_path):
        return f"[오류] 파일이 존재하지 않습니다: {file_path}"

    parts = []

    # 1. 분류
    classify_result = classify_document(file_path, tracker=tracker)
    parts.append(f"=== 1단계: 문서 분류 ===\n{classify_result}")

    # doc_type 추출
    doc_type = "unknown"
    try:
        result_json = json.loads(classify_result.replace("[분류 결과]\n", ""))
        doc_type = result_json.get("category", "unknown")
    except (json.JSONDecodeError, AttributeError):
        pass

    # 2. 파싱
    parse_result = parse_document(file_path, tracker=tracker)
    parts.append(f"=== 2단계: 문서 파싱 ===\n{parse_result}")

    # 3. 정보 추출 (스키마가 있는 유형만)
    if doc_type in EXTRACTION_SCHEMAS:
        extract_result = extract_information(file_path, doc_type, tracker=tracker)
        parts.append(f"=== 3단계: 정보 추출 ===\n{extract_result}")
    else:
        parts.append(
            f"=== 3단계: 정보 추출 ===\n[건너뜀] '{doc_type}' 유형은 추출 스키마가 없습니다."
        )

    return "\n\n".join(parts)


def read_file_content(file_path: str) -> str:
    """텍스트 파일(.tf, .yaml 등)의 내용을 읽습니다."""
    if not os.path.isfile(file_path):
        return f"[오류] 파일이 존재하지 않습니다: {file_path}"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        line_count = content.count("\n") + 1

        return (
            f"[파일 정보] {file_name} ({file_size} bytes, {line_count} lines)\n\n"
            f"[내용]\n{content}"
        )
    except Exception as e:
        return f"[읽기 오류] {e}"
