import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.client import client
from common.usage import UsageTracker, print_usage
from mlops_dashboard.db_manager import get_schema, execute_query

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_sql",
            "description": "SQLite 데이터베이스에 SELECT 쿼리를 실행합니다. SELECT 쿼리만 허용됩니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "실행할 SQL SELECT 쿼리",
                    }
                },
                "required": ["sql"],
            },
        },
    }
]

SYSTEM_PROMPT = """당신은 MLOps 플랫폼의 SQL 전문가입니다. 사용자의 자연어 질문을 SQL 쿼리로 변환하고 실행 결과를 설명합니다.

데이터베이스 스키마:
{schema}

테이블 관계:
- users 1:N projects (user_id)
- projects 1:N datasets (project_id)
- datasets 1:N pipelines (dataset_id) — 보통 dataset당 0~1개 파이프라인
- pipelines 1:N artifacts (pipeline_id) — checkpoint, log, config 등
- pipelines 1:0..1 models (pipeline_id, UNIQUE) — 학습 완료 시 모델 등록
- models 1:1 metrics (model_id, UNIQUE) — mAP50, F1 score 등 평가 지표

주요 컬럼 설명:
- models.stage: development / staging / production / archived (모델 라이프사이클)
- models.parameters_m: 모델 파라미터 수 (백만 단위)
- metrics.map50: mAP@IoU=0.50 (object detection용, 분류 모델은 NULL)
- metrics.f1_score: F1 Score (precision과 recall의 조화 평균)
- metrics.precision_val: Precision (정밀도) — 모델이 양성으로 예측한 것 중 실제 양성 비율. 높으면 오탐(FP)이 적음
- metrics.recall: Recall (재현율) — 실제 양성 중 모델이 잡아낸 비율. 높으면 미탐(FN)이 적음
- metrics.inference_ms: 추론 시간 (밀리초)
- metrics.confidence_threshold: 모델 추론 시 사용한 confidence 기준값 (낮추면 recall↑ precision↓, 높이면 precision↑ recall↓)
- metrics.deploy_note: 배포 의사결정 메모 (현장별 오탐/미탐 요구사항)
- pipelines.status: pending / running / completed / failed
- artifacts.type: checkpoint / log / config

도메인 지식 (Precision vs Recall 트레이드오프):
- 오탐 민감 현장: precision 높은 모델 선호 (잘못 잡으면 비용 발생 — 예: 불필요한 작업 중단)
- 미탐 민감 현장: recall 높은 모델 선호 (놓치면 큰 손해 — 예: 불량 유출, 안전 사고)
- 같은 모델도 confidence_threshold를 조절하면 precision/recall 밸런스가 바뀜
- deploy_note에 현장별 의사결정 근거가 기록되어 있음

규칙:
- SELECT 쿼리만 사용하세요.
- execute_sql 도구를 사용해서 쿼리를 실행하세요.
- 쿼리 결과를 한국어로 친절하게 설명하세요.
- 메트릭 값은 소수점으로 표시하되, 퍼센트로 변환해서 설명해도 됩니다 (예: 0.923 → 92.3%).
- precision/recall 관련 질문에는 오탐/미탐 관점에서 실무적으로 설명하세요.
- 용량은 MB 단위입니다.
"""


def handle_tool_call(tool_call) -> str:
    '''
    LLM이 생성한 Tool 호출 정보를 받아 실제 함수(`execute_query`)를 실행합니다.
    '''
    if tool_call.function.name == "execute_sql":
        args = json.loads(tool_call.function.arguments)
        return execute_query(args["sql"])
    return "[오류] 알 수 없는 도구입니다."


class SQLAgent:
    '''
    SQLAgent는 자연어 질문을 SQL로 변환하고, 실행 결과를 설명하는 에이전트입니다.
    '''
    def __init__(self, usage_enabled: bool = False):
        schema = get_schema()
        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT.format(schema=schema)}
        ]
        self.tracker = UsageTracker(enabled=usage_enabled)

    def ask(self, question: str) -> str:
        '''
        자연어 질문을 받아 SQLAgent를 실행합니다.
        '''
        self.messages.append({"role": "user", "content": question})

        # [Upstage API] Chat Completions + Function Calling
        # 자연어 질문을 SQL로 변환하기 위해 tools(execute_sql)와 함께 호출
        # https://console.upstage.ai/docs/capabilities/generate/function-calling
        response = client.chat.completions.create(
            model="solar-pro3",
            messages=self.messages,
            tools=TOOLS,
        )
        self.tracker.track_chat(response)

        message = response.choices[0].message
        self.messages.append(message)

        # Tool 호출이 있으면 반복 실행
        while message.tool_calls:
            for tool_call in message.tool_calls:
                sql = json.loads(tool_call.function.arguments).get("sql", "")
                print(f"\n[SQL] {sql}")

                result = handle_tool_call(tool_call)
                print(f"\n[결과]\n{result}")

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

        last_info = {"input": self.tracker.total_input_tokens, "output": self.tracker.total_output_tokens, "cost": self.tracker.total_cost}
        print_usage(self.tracker, last_info)

        return message.content
