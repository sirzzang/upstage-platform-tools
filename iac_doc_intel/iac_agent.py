import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.client import client
from common.usage import UsageTracker, print_usage
from iac_doc_intel.doc_tools import (
    classify_document,
    parse_document,
    extract_information,
    analyze_iac_document,
    read_file_content,
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "classify_document",
            "description": "업로드된 문서를 분류합니다 (terraform/kubernetes/ansible/architecture_diagram/runbook/unknown).",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "분류할 문서 파일 경로",
                    }
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "parse_document",
            "description": "PDF/이미지 문서를 파싱하여 구조화된 텍스트(HTML/Markdown)를 추출합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "파싱할 문서 파일 경로",
                    },
                    "output_formats": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "출력 형식 목록 (예: ['text', 'markdown']). 기본값: ['text', 'markdown']",
                    },
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "extract_information",
            "description": "IaC 문서에서 구조화된 데이터를 스키마 기반으로 추출합니다 (리소스, 설정, 변수 등).",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "정보를 추출할 문서 파일 경로",
                    },
                    "doc_type": {
                        "type": "string",
                        "enum": ["terraform", "kubernetes", "ansible"],
                        "description": "문서 유형. 미지정 시 자동 분류합니다.",
                    },
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_iac_document",
            "description": "IaC 문서를 종합 분석합니다 (분류 + 파싱 + 정보추출). 보안, 베스트 프랙티스 분석에 사용합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "분석할 문서 파일 경로",
                    }
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file_content",
            "description": "텍스트 파일(.tf, .yaml 등)의 내용을 읽어옵니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "읽을 파일 경로",
                    }
                },
                "required": ["file_path"],
            },
        },
    },
]

TOOL_LABELS = {
    "classify_document": "문서 분류",
    "parse_document": "문서 파싱",
    "extract_information": "정보 추출",
    "analyze_iac_document": "IaC 종합 분석",
    "read_file_content": "파일 읽기",
}

SYSTEM_PROMPT = """당신은 IaC(Infrastructure as Code) 문서 분석 전문가입니다. Terraform, Kubernetes, Ansible 등의 IaC 문서를 분류, 파싱, 분석합니다.

역할:
- 문서 분류: 업로드된 문서가 어떤 IaC 유형인지 자동 분류
- 문서 파싱: PDF/이미지에서 텍스트를 추출하여 구조화
- 정보 추출: IaC 문서에서 리소스, 설정, 변수 등 핵심 정보를 스키마 기반으로 추출
- IaC 분석: 보안 취약점, 베스트 프랙티스 위반, 비용 최적화 기회를 식별
- Q&A: 파싱된 문서에 대한 질문에 답변

규칙:
- 항상 적절한 도구(function)를 호출하여 작업하세요.
- 파일 경로가 주어지면 먼저 classify_document로 문서 유형을 파악하세요.
- PDF/이미지 파일은 parse_document로 먼저 파싱하세요.
- .tf, .yaml 등 텍스트 파일은 read_file_content로 읽으세요.
- 종합 분석 요청 시 analyze_iac_document를 사용하세요.
- 모든 응답은 한국어로 작성하세요.
- 심각도를 다음과 같이 구분하세요: [CRITICAL] [WARNING] [INFO] [SUGGESTION]

IaC 분석 체크리스트:
[보안] 하드코딩된 시크릿, 과도한 권한, 암호화 미설정, 퍼블릭 접근 (0.0.0.0/0)
[네트워킹] 과도한 포트 오픈, 보안그룹 규칙, 네트워크 세그멘테이션
[베스트 프랙티스] 태그 지정, 리소스 제한, 버전 고정, 상태 파일 관리
[비용] 과도한 인스턴스 타입, 미사용 리소스, 예약 인스턴스/Spot 검토
[안정성] 고가용성, 백업, 모니터링 설정, 멀티 AZ
"""


def handle_tool_call(tool_call, tracker=None) -> str:
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    handlers = {
        "classify_document": lambda a: classify_document(a["file_path"], tracker=tracker),
        "parse_document": lambda a: parse_document(
            a["file_path"], a.get("output_formats"), tracker=tracker
        ),
        "extract_information": lambda a: extract_information(
            a["file_path"], a.get("doc_type"), tracker=tracker
        ),
        "analyze_iac_document": lambda a: analyze_iac_document(
            a["file_path"], tracker=tracker
        ),
        "read_file_content": lambda a: read_file_content(a["file_path"]),
    }
    handler = handlers.get(name)
    if handler:
        return handler(args)
    return "[오류] 알 수 없는 도구입니다."


class IaCDocAgent:
    def __init__(self, usage_enabled: bool = False):
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.tracker = UsageTracker(enabled=usage_enabled)

    def ask(self, question: str) -> str:
        self.messages.append({"role": "user", "content": question})

        # [Upstage API] Chat Completions + Function Calling
        # IaC 문서 분석 도구(classify, parse, extract, analyze, read)와 함께 호출
        response = client.chat.completions.create(
            model="solar-pro3",
            messages=self.messages,
            tools=TOOLS,
        )
        self.tracker.track_chat(response)

        message = response.choices[0].message
        self.messages.append(message)

        while message.tool_calls:
            for tool_call in message.tool_calls:
                name = tool_call.function.name
                label = TOOL_LABELS.get(name, name)
                print(f"\n[{label}] {name} 호출됨")

                result = handle_tool_call(tool_call, tracker=self.tracker)
                preview = result[:200] + "..." if len(result) > 200 else result
                print(f"[결과 미리보기]\n{preview}")

                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    }
                )

            # [Upstage API] Chat Completions + Function Calling (tool 결과 반영 후 재호출)
            response = client.chat.completions.create(
                model="solar-pro3",
                messages=self.messages,
                tools=TOOLS,
            )
            self.tracker.track_chat(response)
            message = response.choices[0].message
            self.messages.append(message)

        print_usage(self.tracker, None)
        return message.content
