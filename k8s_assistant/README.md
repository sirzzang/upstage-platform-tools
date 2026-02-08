# K8s YAML Assistant

자연어로 Kubernetes YAML 매니페스트를 생성, 분석, 검증, 비교하는 대화형 어시스턴트입니다. K8s 매니페스트 작성 경험이 부족해도 프로덕션 수준의 YAML을 만들 수 있습니다.

## 기능

다음과 같은 기능을 지원합니다.

- 자연어 요구사항을 기반으로 YAML 매니페스트 생성
- 기존 YAML 구조 분석 및 개선 방향 제안
- 보안, 리소스, 안정성, 네트워킹 관점의 베스트 프랙티스 검증
- 연관 리소스 일괄 생성 (Deployment + Service + Ingress 등)
- 두 YAML 매니페스트 비교
- 사용량 추적 (`--usage` 플래그)

## User Interface

이 어시스턴트는 **CLI (Command Line Interface)**로 제공됩니다.

- 대화형 프롬프트(`>`)를 통해 자연어 질문 또는 YAML 입력
- `apiVersion:`, `kind:`, `---`로 시작하면 멀티라인 YAML 입력 모드 활성화
- 빈 줄 2번 입력으로 멀티라인 입력 완료
- `help` - 도움말 표시
- `clear` - 대화 초기화
- `quit` 또는 `exit` - 종료

## 지원 리소스

### 템플릿 제공 (10종)

Deployment, Service, Ingress, StatefulSet, CronJob, ConfigMap, Secret, PersistentVolumeClaim, HorizontalPodAutoscaler, NetworkPolicy

### 템플릿 미제공

PodDisruptionBudget, EndpointSlice 등 템플릿에 정의되지 않은 리소스도 LLM의 사전 학습 지식으로 분석/생성/검증이 가능합니다. 검증 시 도구 레벨의 오탐이 발생할 수 있으나, LLM이 리소스 특성을 파악하여 최종 응답에서 교정합니다.

## 검증 규칙

프로덕션 배포 시 흔히 놓치는 항목을 체크합니다.

| ID | 심각도 | 카테고리 | 검사 항목 |
|----|--------|----------|----------|
| SEC001 | CRITICAL | 보안 | `latest` 이미지 태그 사용 금지 |
| SEC002 | CRITICAL | 보안 | `securityContext` 누락 |
| SEC003 | WARNING | 보안 | `allowPrivilegeEscalation` 미설정 |
| RES001 | CRITICAL | 리소스 | `resources.requests/limits` 누락 |
| REL001 | WARNING | 안정성 | `livenessProbe` 누락 |
| REL002 | WARNING | 안정성 | `readinessProbe` 누락 |
| REL003 | WARNING | 안정성 | `replicas` < 2 |
| NET001 | INFO | 네트워킹 | `namespace` 미지정 |

이 규칙들은 Pod 워크로드(Deployment, StatefulSet 등) 기준으로 하드코딩되어 있습니다. 비워크로드 리소스(PDB, Service 등)에는 오탐이 발생하지만, LLM이 최종 응답에서 해당 리소스에 맞게 보정합니다.

## 시작하기

### 요구사항

- Python 3.10+
- Upstage API Key

### 설치

```bash
# 프로젝트 루트에서
pip install -r requirements.txt

# API 키 설정 (환경 변수 또는 .env 파일)
export UPSTAGE_API_KEY="your-api-key"
# 또는 .env 파일에 UPSTAGE_API_KEY=your-api-key 추가
```

### 실행

```bash
python3 k8s_assistant/main.py
```

### 사용량 추적

`--usage` 플래그로 각 응답의 토큰 사용량과 예상 비용을 확인할 수 있습니다.

```bash
python3 k8s_assistant/main.py --usage
```

## 사용 예시

```bash
> nginx Deployment 만들어줘
> CKA 실습용으로 간단하게 다시 만들어줘
> (기존 YAML 붙여넣기)
> 보안 관점에서 검증해줘
> 더 나은 방향으로 수정해줘
> Redis StatefulSet + Service + PVC 만들어줘
```

## 구조

### 주요 파일

- **main.py**: CLI 진입점 (REPL 루프, 멀티라인 YAML 입력 처리)
- **k8s_agent.py**: K8sAgent 클래스 (Upstage API와 통신, Function Calling 오케스트레이션)
- **yaml_tools.py**: 5개 도구 함수 구현 (분석, 생성, 검증, 멀티 리소스, 비교)
- **templates.py**: 10종 K8s 리소스 YAML 템플릿 및 검증 규칙 정의

### 동작 흐름 (AI Agent 패턴)

```
사용자 입력 (CLI)
     │
     ▼
  main.py          ← 대화형 REPL, 멀티라인 YAML 입력 지원
     │
     ▼
  K8sAgent         ← 대화 상태 관리 + Upstage API 호출
     │
     ├──▶ Upstage API (solar-pro3, Function Calling)
     │
     ▼
  yaml_tools.py    ← 5개 도구 함수 구현
     │
     ▼
  templates.py     ← 10종 K8s 리소스 템플릿 + 8개 검증 규칙
```

개발자가 Tool을 정의하고, LLM이 언제 호출할지 자율적으로 판단하는 Agent 구조입니다.

1. 사용자 자연어 질문 또는 YAML 입력
2. LLM에 질문과 Tool 목록(5개 도구)을 함께 전달
3. LLM이 Tool 호출 여부를 스스로 판단하여 적절한 도구 선택
4. Tool 실행 후 결과(추출 정보 + 원본 YAML 또는 참고 템플릿)를 LLM에 반환
5. LLM이 결과를 해석하여 최종 응답 생성 (추가 도구 호출이 필요하면 3~4를 자율 반복)

## API 사용

- **모델**: `solar-pro3`
- **Chat Completions**: 자연어 질문 처리
- **Function Calling**: YAML 분석/생성/검증/비교 도구 호출

## 문서

- [질문 가이드](QUESTIONS.md): 카테고리별 질문 예시
- [실제 사용 사례](EXAMPLES.md): 실제 사용 사례와 활용 방향
