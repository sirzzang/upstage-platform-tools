# upstage-platform-tools

Upstage Solar API를 활용한 플랫폼 엔지니어링 / MLOps 도구 모음입니다.

실무에서 경험한 MLOps 워크플로우와, 플랫폼 엔지니어로서 다뤄보고 싶었던 영역을 CLI 에이전트로 구현했습니다. 각 프로젝트는 Upstage의 서로 다른 API를 커버하며, 전체적으로 8개 API를 모두 사용합니다.

## 프로젝트 구성

```
common/              # 공통 Upstage API 클라이언트
mlops_dashboard/       # MLOps 메트릭 조회 (실무 경험 기반)
k8s_assistant/       # Kubernetes YAML 생성/분석
commit_guardian/     # Git 커밋 코드 리뷰
iac_doc_intel/       # IaC 문서 분류/파싱/분석
platform_kb/         # 내부 문서 RAG 지식 베이스 (예정)
```

### 1. MLOps Dashboard — 메트릭 조회

자연어로 MLOps 플랫폼 데이터를 조회하는 읽기 전용 대시보드. 프로젝트, 실험, 데이터셋, 파이프라인, 아티팩트, 모델 메트릭을 SQL 없이 검색할 수 있다.

- **DB 스키마**: user → project → dataset → pipeline → artifact / model → metric
- **조회 가능 항목**: 프로젝트 목록, 실험 결과, 아티팩트 경로, 로그 경로, 모델 메트릭 (mAP50, F1, precision, recall, inference_ms)
- **SELECT 전용**: 읽기 전용 대시보드 설계. 데이터 조회만 지원하여 API 호출을 최소화하고, 제한된 크레딧으로 5개 프로젝트를 모두 실험할 수 있도록 함
- **API**: Chat Completions, Function Calling

```bash
python3 mlops_dashboard/main.py

> 김민준의 프로젝트 목록 보여줘
> defect-detection 파이프라인의 아티팩트 경로 알려줘
> wafer-defect v2.0과 v2.1의 메트릭 비교해줘
> 현재 실행 중이거나 실패한 파이프라인 있어?
> production에 배포된 모델 목록과 성능 보여줘
> 오탐이 적은 모델 추천해줘          # 실무 경험 반영: precision/recall 트레이드오프 기반 배포 결정
```

### 2. K8s YAML Assistant — Kubernetes 매니페스트 생성/분석

Deployment, Service, Ingress 등 10종 리소스 템플릿 기반 생성과 보안/베스트 프랙티스를 검증합니다.

- **API**: Chat Completions, Function Calling

```bash
python3 k8s_assistant/main.py

> nginx deployment 3 replicas로 만들어줘
> (YAML 붙여넣기) 이 매니페스트 검증해줘
```



### 3. Commit Guardian — Git 코드 리뷰

Git diff를 분석하고, 리뷰 발견사항이 실제 코드에 근거하는지 Groundedness Check로 검증합니다.

- **API**: Chat Completions, Function Calling, **Groundedness Check**, **Translation**

```bash
python3 commit_guardian/main.py /path/to/repo

> review          # unstaged 변경사항 리뷰
> staged          # staged 변경사항 리뷰
> release         # 릴리스 노트 생성 (한/영)
```



### 4. IaC Doc Intelligence — IaC 문서 분류/파싱/분석

PDF/이미지 형태의 Terraform, Kubernetes, Ansible 문서를 자동 분류하고 구조화된 데이터를 추출합니다.

- **API**: **Document Classification**, **Document Digitization**, **Information Extraction**, Chat Completions, Function Calling

```bash
python3 iac_doc_intel/main.py

> generate-samples                    # 테스트용 PDF 생성
> classify samples/terraform_sample.pdf
> analyze samples/kubernetes_sample.pdf
```



### 5. Platform Knowledge Base — RAG 지식 베이스 (예정)

Runbook, 포스트모템, 아키텍처 문서를 임베딩해서 저장하고, 자연어 질문에 근거 기반 답변을 생성합니다.

- **API**: **Embeddings** (passage/query), Chat Completions, Function Calling, Groundedness Check

```bash
python3 platform_kb/main.py

> generate-samples                                        # 샘플 문서 생성
> add platform_kb/samples/runbook_k8s_troubleshoot.md     # 문서 추가
> Pod가 CrashLoopBackOff일 때 어떻게 해?                    # RAG Q&A
```



## Usage

각 프로젝트의 사용법과 예시는 해당 프로젝트 디렉토리의 문서를 참고한다.

- **MLOps Dashboard**: [질문 가이드](mlops_dashboard/QUESTIONS.md) | [실제 사용 사례](mlops_dashboard/EXAMPLES.md)

## API 사용 범위

| Upstage API             | 사용 프로젝트                |
| ----------------------- | ---------------------------- |
| Chat Completions        | 전체                         |
| Function Calling        | 전체                         |
| Embeddings              | Platform KB                  |
| Groundedness Check      | Commit Guardian, Platform KB |
| Translation             | Commit Guardian              |
| Document Digitization   | IaC Doc Intel                |
| Information Extraction  | IaC Doc Intel                |
| Document Classification | IaC Doc Intel                |



## 시작하기

```bash
# 의존성 설치
pip install -r requirements.txt

# API 키 설정
cp .env.example .env
# .env 파일에 UPSTAGE_API_KEY 입력

# 아무 프로젝트나 실행
python3 mlops_dashboard/main.py
```

### 요구사항

- Python 3.10+
- Upstage API Key ([console.upstage.ai](https://console.upstage.ai))



## 아키텍처

모든 에이전트가 동일한 패턴을 따릅니다.

```
Agent class
├── SYSTEM_PROMPT   — 역할/규칙 정의
├── TOOLS[]         — Function Calling 도구 목록
├── TOOL_HANDLERS{} — 도구 이름 → 핸들러 함수 매핑
└── ask(question)   — 메시지 루프 (tool_calls 반복 처리)
```



공통 클라이언트 (`common/client.py`)는 아래와 같습니다.

```python
from openai import OpenAI
client = OpenAI(
    api_key=os.environ["UPSTAGE_API_KEY"],
    base_url="https://api.upstage.ai/v1",
)
```



Upstage API는 OpenAI SDK와 호환되므로, `openai` 패키지 하나로 Chat, Function Calling, Embeddings, Groundedness Check를 모두 사용할 수 있습니다. Document Digitization만 REST API로 별도 호출합니다.



## API 비용

`--usage` 플래그를 붙이면 매 응답 후 사용 토큰 수와 예상 비용을 표시합니다.

```bash
# 사용량 추적 활성화
python3 mlops_dashboard/main.py --usage

> 김민준의 프로젝트 보여줘
[SQL] SELECT ...
[결과] ...

📊 토큰: 1,200 in + 350 out | 비용: $0.000390
📈 세션 누적: 2회 호출 | 총 3,100 토큰 | 총 비용: $0.000870
```

> **주의**: 표시되는 비용은 코드에 포함된 단가 기준의 **추정치**이며, 실제 대시보드 차감액과 다를 수 있습니다. 정확한 사용량과 비용은 반드시 [Upstage 대시보드](https://console.upstage.ai/billing)에서 확인하세요.

### 모델별 단가 (참고용, [출처](https://www.upstage.ai/pricing/api))

| API | 모델 | 가격 |
|-----|------|------|
| Solar Pro 3 (Chat/FC/Groundedness) | solar-pro3 | $0.15 / $0.60 per 1M tokens (in/out) |
| Embeddings | embedding-passage/query | $0.10 per 1M tokens |
| Document Parse | document-parse | $0.01 / page |
| Document Classify | document-classify | $0.004 / page |
| Information Extract | information-extract | $0.04 / page |

### 참고
- 사용량 확인: [console.upstage.ai/billing](https://console.upstage.ai/billing)
- 토큰 사전 추정: `pip install tokenizers==0.20.0` → `upstage/solar-pro3-tokenizer`