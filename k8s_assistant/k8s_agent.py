import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.client import client
from common.usage import UsageTracker, print_usage
from k8s_assistant.yaml_tools import (
    analyze_yaml,
    generate_yaml,
    validate_yaml,
    generate_multi_resource,
    diff_yaml,
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "analyze_yaml",
            "description": "입력된 Kubernetes YAML 매니페스트를 분석하여 리소스 종류, 주요 설정, 동작을 설명합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "yaml_content": {
                        "type": "string",
                        "description": "분석할 Kubernetes YAML 매니페스트 전문",
                    }
                },
                "required": ["yaml_content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_yaml",
            "description": "자연어 요구사항을 기반으로 Kubernetes YAML 매니페스트를 생성합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "requirement": {
                        "type": "string",
                        "description": "생성할 리소스에 대한 자연어 요구사항",
                    },
                    "resource_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "생성할 리소스 종류 목록 (예: ['Deployment', 'Service']). 비어있으면 요구사항에서 추론합니다.",
                    },
                },
                "required": ["requirement"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "validate_yaml",
            "description": "Kubernetes YAML의 보안, 리소스 제한, 베스트 프랙티스를 검증합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "yaml_content": {
                        "type": "string",
                        "description": "검증할 Kubernetes YAML 매니페스트 전문",
                    },
                    "check_categories": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "security",
                                "resources",
                                "reliability",
                                "networking",
                                "all",
                            ],
                        },
                        "description": "검증할 카테고리. 기본값은 ['all'].",
                    },
                },
                "required": ["yaml_content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_multi_resource",
            "description": "연관된 여러 Kubernetes 리소스를 한 번에 생성합니다 (예: Deployment + Service + Ingress).",
            "parameters": {
                "type": "object",
                "properties": {
                    "requirement": {
                        "type": "string",
                        "description": "전체 애플리케이션 배포에 대한 요구사항",
                    },
                    "resource_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "생성할 리소스 종류 목록 (예: ['Deployment', 'Service', 'Ingress'])",
                    },
                },
                "required": ["requirement", "resource_types"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "diff_yaml",
            "description": "두 개의 Kubernetes YAML 매니페스트를 비교하여 차이점을 설명합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "yaml_before": {
                        "type": "string",
                        "description": "변경 전 (또는 첫 번째) YAML 매니페스트",
                    },
                    "yaml_after": {
                        "type": "string",
                        "description": "변경 후 (또는 두 번째) YAML 매니페스트",
                    },
                },
                "required": ["yaml_before", "yaml_after"],
            },
        },
    },
]

SYSTEM_PROMPT = """당신은 Kubernetes YAML 전문가입니다. 사용자의 요청에 따라 K8s 매니페스트를 분석, 생성, 검증, 비교합니다.

역할:
- YAML 분석: 리소스 종류, 메타데이터, 주요 스펙, 실제 동작을 쉽게 설명
- YAML 생성: 프로덕션 품질의 매니페스트 생성 (리소스 제한, 헬스체크, 보안 컨텍스트 포함)
- 베스트 프랙티스 검증: 보안, 안정성, 리소스 관리 관점에서 문제점과 개선안 제시
- 멀티 리소스: 연관 리소스를 '---' 구분자로 한 번에 생성
- YAML 비교: 두 매니페스트의 차이를 항목별로 설명

규칙:
- 항상 적절한 도구(function)를 호출하여 작업하세요.
- YAML 생성 시 반드시 포함: metadata.labels, resources.requests/limits, securityContext
- 생성된 YAML은 apiVersion, kind, metadata, spec 구조를 갖추세요.
- 검증 시 심각도를 [CRITICAL], [WARNING], [INFO] 로 구분하세요.
- 모든 응답은 한국어로 작성하세요.
- YAML 코드블록은 ```yaml ... ``` 으로 감싸세요.

검증 체크리스트:
[보안] runAsNonRoot, readOnlyRootFilesystem, allowPrivilegeEscalation: false
[보안] image 태그에 latest 사용 금지 → 특정 버전 사용 권장
[리소스] resources.requests/limits 필수
[안정성] livenessProbe, readinessProbe 설정 권장
[안정성] replicas >= 2 권장 (프로덕션)
[네트워킹] Service type 적절성, port/targetPort 매칭
"""

TOOL_HANDLERS = {
    "analyze_yaml": lambda args: analyze_yaml(args["yaml_content"]),
    "generate_yaml": lambda args: generate_yaml(
        args["requirement"], args.get("resource_types")
    ),
    "validate_yaml": lambda args: validate_yaml(
        args["yaml_content"], args.get("check_categories")
    ),
    "generate_multi_resource": lambda args: generate_multi_resource(
        args["requirement"], args["resource_types"]
    ),
    "diff_yaml": lambda args: diff_yaml(args["yaml_before"], args["yaml_after"]),
}

TOOL_LABELS = {
    "analyze_yaml": "YAML 분석",
    "generate_yaml": "YAML 생성",
    "validate_yaml": "YAML 검증",
    "generate_multi_resource": "멀티 리소스 생성",
    "diff_yaml": "YAML 비교",
}


def handle_tool_call(tool_call) -> str:
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    handler = TOOL_HANDLERS.get(name)
    if handler:
        return handler(args)
    return "[오류] 알 수 없는 도구입니다."


class K8sAgent:
    def __init__(self, usage_enabled: bool = False):
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.tracker = UsageTracker(enabled=usage_enabled)

    def ask(self, question: str) -> str:
        self.messages.append({"role": "user", "content": question})

        # [Upstage API] Chat Completions + Function Calling
        # K8s YAML 생성/분석/검증 도구와 함께 호출
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

                result = handle_tool_call(tool_call)
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
