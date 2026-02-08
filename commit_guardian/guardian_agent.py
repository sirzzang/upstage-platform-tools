import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.client import client
from common.usage import UsageTracker, print_usage
from commit_guardian.git_tools import (
    get_diff,
    get_commit_log,
    get_changed_files,
    get_commit_info,
)
from commit_guardian.review_tools import format_review_context
from commit_guardian.groundedness import check_groundedness


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_git_diff",
            "description": "Git 저장소에서 변경사항(diff)을 가져옵니다. unstaged, staged, 또는 특정 커밋의 diff를 조회합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Git 저장소 경로",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["unstaged", "staged", "commit"],
                        "description": "diff 모드: unstaged(기본), staged, commit",
                    },
                    "commit_hash": {
                        "type": "string",
                        "description": "특정 커밋 해시 (mode가 commit일 때 필수)",
                    },
                },
                "required": ["repo_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_code_changes",
            "description": "코드 변경사항을 분석하기 위한 컨텍스트를 준비합니다. diff, 변경 파일 목록, 변경된 함수를 포함한 리뷰 컨텍스트를 반환합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Git 저장소 경로",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["unstaged", "staged", "commit"],
                        "description": "diff 모드",
                    },
                    "commit_hash": {
                        "type": "string",
                        "description": "특정 커밋 해시 (mode가 commit일 때)",
                    },
                },
                "required": ["repo_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_tests",
            "description": "변경된 코드에 대한 테스트 제안을 위해 diff와 변경된 함수 목록을 반환합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Git 저장소 경로",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["unstaged", "staged", "commit"],
                        "description": "diff 모드",
                    },
                    "commit_hash": {
                        "type": "string",
                        "description": "특정 커밋 해시",
                    },
                },
                "required": ["repo_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_finding_groundedness",
            "description": "AI가 생성한 코드 리뷰 발견사항이 실제 diff에 근거하는지 검증합니다. 환각(hallucination)을 방지합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "diff_context": {
                        "type": "string",
                        "description": "실제 코드 diff (검증의 근거)",
                    },
                    "finding": {
                        "type": "string",
                        "description": "검증할 코드 리뷰 발견사항",
                    },
                },
                "required": ["diff_context", "finding"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_release_notes",
            "description": "변경사항을 기반으로 릴리스 노트를 생성하기 위한 컨텍스트를 준비합니다. 커밋 로그와 변경 파일 목록을 반환합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Git 저장소 경로",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["unstaged", "staged", "commit"],
                        "description": "diff 모드",
                    },
                    "commit_hash": {
                        "type": "string",
                        "description": "특정 커밋 해시",
                    },
                    "language": {
                        "type": "string",
                        "enum": ["ko", "en", "both"],
                        "description": "릴리스 노트 언어. both면 한국어+영어 모두 생성. 기본값: both",
                    },
                },
                "required": ["repo_path"],
            },
        },
    },
]

TOOL_HANDLERS = {
    "get_git_diff": lambda args: get_diff(
        args["repo_path"],
        args.get("mode", "unstaged"),
        args.get("commit_hash"),
    ),
    "analyze_code_changes": lambda args: format_review_context(
        get_diff(
            args["repo_path"], args.get("mode", "unstaged"), args.get("commit_hash")
        ),
        get_changed_files(
            args["repo_path"], args.get("mode", "unstaged"), args.get("commit_hash")
        ),
    ),
    "suggest_tests": lambda args: get_diff(
        args["repo_path"], args.get("mode", "unstaged"), args.get("commit_hash")
    ),
    "check_finding_groundedness": lambda args: check_groundedness(
        args["diff_context"],
        args["finding"],
    ),
    "generate_release_notes": lambda args: (
        f"[커밋 로그]\n"
        f"{get_commit_log(args['repo_path'])}\n\n"
        f"[변경 파일]\n"
        f"{get_changed_files(args['repo_path'], args.get('mode', 'unstaged'), args.get('commit_hash'))}\n\n"
        f"[Diff]\n"
        f"{get_diff(args['repo_path'], args.get('mode', 'unstaged'), args.get('commit_hash'))}\n\n"
        f"[요청 언어] {args.get('language', 'both')}"
    ),
}

TOOL_LABELS = {
    "get_git_diff": "Git Diff 조회",
    "analyze_code_changes": "코드 변경 분석",
    "suggest_tests": "테스트 제안",
    "check_finding_groundedness": "Groundedness 검증",
    "generate_release_notes": "릴리스 노트 생성",
}

# 시스템 프롬프트에서 LLM에게 groundedness 검증할 것을 지시하는 메시지를 추가
SYSTEM_PROMPT = """당신은 시니어 코드 리뷰어이자 플랫폼 엔지니어입니다. 개발자의 커밋과 코드 변경사항을 분석하여 품질 높은 코드 리뷰를 제공합니다.

현재 저장소 경로: {repo_path}

역할:
- 코드 리뷰: diff를 분석하여 버그, 안티패턴, 보안 이슈를 찾아냅니다
- 테스트 제안: 변경된 코드에 대한 테스트 케이스를 제안합니다
- 위협 탐지: 보안/성능 위협을 식별합니다
- 릴리스 노트: 한국어+영어 릴리스 노트를 자동 생성합니다

규칙:
- 항상 적절한 도구(function)를 호출하여 작업하세요.
- 코드 리뷰 발견사항은 반드시 check_finding_groundedness 도구로 검증하세요.
- 검증되지 않은(notGrounded) 발견사항은 사용자에게 제시하지 마세요.
- 모든 응답은 한국어로 작성하세요.
- 심각도를 다음과 같이 구분하세요: [CRITICAL] [WARNING] [INFO] [SUGGESTION]

리뷰 체크리스트:
[보안] SQL 인젝션, XSS, 하드코딩된 시크릿, 권한 문제
[성능] N+1 쿼리, 불필요한 반복, 메모리 누수, 큰 파일 로딩
[에러 처리] 미처리 예외, 빈 catch 블록, 에러 메시지 노출
[코드 스타일] 네이밍 규칙, 코드 중복, 함수 길이, 복잡도
[테스트] 테스트 커버리지, 경계값 테스트, 에러 케이스 테스트

릴리스 노트 형식:
- Conventional Commits 스타일 (feat:, fix:, refactor:, docs:, test:, chore:)
- language가 both이면 한국어 섹션 먼저, 그 다음 영어 섹션
- 각 변경사항을 카테고리별로 분류

Groundedness 검증 워크플로우:
1. analyze_code_changes로 diff를 가져옵니다
2. diff를 분석하여 발견사항을 도출합니다
3. 각 주요 발견사항을 check_finding_groundedness로 검증합니다
4. grounded된 발견사항만 최종 리뷰에 포함합니다
5. 필터링된 발견사항 수를 사용자에게 알립니다
"""


def handle_tool_call(tool_call) -> str:
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    handler = TOOL_HANDLERS.get(name)
    if handler:
        return handler(args)
    return "[오류] 알 수 없는 도구입니다."


class GuardianAgent:
    def __init__(self, repo_path: str = "", usage_enabled: bool = False):
        self.repo_path = repo_path
        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT.format(repo_path=repo_path)}
        ]
        self.tracker = UsageTracker(enabled=usage_enabled)

    def set_repo(self, repo_path: str):
        """저장소 변경 및 대화 초기화."""
        self.repo_path = repo_path
        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT.format(repo_path=repo_path)}
        ]

    def ask(self, question: str) -> str:
        self.messages.append({"role": "user", "content": question})

        # [Upstage API] Chat Completions + Function Calling
        # Git diff 분석, 코드 리뷰, 릴리스 노트 생성(한/영 Translation 포함) 도구와 함께 호출
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
