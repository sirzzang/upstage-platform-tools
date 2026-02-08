# IaC Doc Intelligence

IaC(Infrastructure as Code) 문서를 분류, 파싱, 분석하는 대화형 에이전트입니다. PDF나 이미지로 된 인프라 문서를 Upstage Document AI로 읽고, LLM이 보안/비용/안정성 관점에서 종합 분석합니다.

## 기능

다음과 같은 기능을 지원합니다.

- PDF/이미지 형태의 IaC 문서 유형 자동 분류 (Terraform, Kubernetes, Ansible)
- OCR 기반 문서 파싱 및 텍스트 추출
- 스키마 기반 구조화 데이터 추출 (리소스, 변수, 설정값)
- 보안/베스트 프랙티스/비용/안정성 관점의 종합 분석
- 분석 결과 위에서 자연어 후속 질문 (보안 심층 분석, 비용 추정 등)
- 텍스트 파일(.tf, .yaml) 직접 읽기
- 테스트용 샘플 PDF 생성
- 사용량 추적 (`--usage` 플래그)

## User Interface

이 에이전트는 **CLI (Command Line Interface)**로 제공됩니다.

- 대화형 프롬프트(`>`)를 통해 직접 명령어 또는 자연어 질문 입력
- `classify`, `parse`, `extract`, `analyze` 등 단축 명령어 지원
- 샘플 파일명만 입력하면 `samples/` 디렉토리에서 자동 탐색
- `help` - 도움말 표시
- `clear` - 대화 초기화
- `quit` 또는 `exit` - 종료

## 지원 문서 유형

### 분류 및 추출 스키마 제공 (3종)

| 유형 | 추출 항목 |
|------|----------|
| Terraform | provider, resources, variables, outputs, backend, modules |
| Kubernetes | kind, apiVersion, containers, volumes, services, configmaps |
| Ansible | playbook name, hosts, roles, tasks, variables, handlers |

### 스키마 미제공 유형

아키텍처 다이어그램, 런북 등 스키마가 정의되지 않은 문서도 파싱 후 LLM이 직접 분석합니다. 분류 단계에서 `unknown`으로 판정되더라도, 파싱된 텍스트를 기반으로 LLM이 문서 유형을 추론하고 분석을 수행합니다.

## 분석 체크리스트

`analyze` 명령 시 LLM이 다음 관점에서 분석합니다.

| 카테고리 | 심각도 | 체크 항목 예시 |
|----------|--------|--------------|
| 보안 | CRITICAL | 시크릿 하드코딩, 0.0.0.0/0 보안그룹, IAM 과잉 권한 |
| 보안 | WARNING | egress 전면 개방, 암호화 미설정 |
| 베스트 프랙티스 | CRITICAL | 리소스 미정의 (ALB, Target Group 등), IAM 역할 미연결 |
| 베스트 프랙티스 | WARNING | provider 버전 미고정, 태그 누락 |
| 비용 | INFO | 인스턴스 타입 과다, NAT Gateway 비용, 오토스케일링 설정 |
| 안정성 | INFO | 멀티 AZ 미배포, 백업 미설정, 모니터링 부재 |

이 체크리스트는 하드코딩된 규칙이 아니라 시스템 프롬프트로 LLM에 가이드됩니다. LLM이 문서 내용에 따라 자율적으로 판단하므로, 문서 유형에 관계없이 유연하게 적용됩니다.

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
python3 iac_doc_intel/main.py
```

### 사용량 추적

`--usage` 플래그로 각 응답의 토큰 사용량, 페이지 수, 예상 비용을 확인할 수 있습니다.

```bash
python3 iac_doc_intel/main.py --usage
```

### 샘플 생성

테스트용 PDF 샘플을 생성합니다.

```bash
python3 iac_doc_intel/main.py
> generate-samples
> samples              # 생성된 파일 목록 확인
```

## 사용 예시

```bash
> classify terraform_sample.pdf
> parse terraform_fargate_sample.pdf
> analyze terraform_fargate_sample.pdf
> 여기서 보안그룹 규칙 중 가장 위험한 건 뭐야?
> 이 구성의 월 예상 비용은 얼마나 될까?
```

## 구조

### 주요 파일

- **main.py**: CLI 진입점 (REPL 루프, 단축 명령어 처리, 샘플 관리)
- **iac_agent.py**: IaCDocAgent 클래스 (Upstage Chat API와 통신, Function Calling 오케스트레이션)
- **doc_tools.py**: 5개 도구 함수 구현 (분류, 파싱, 추출, 종합 분석, 파일 읽기)
- **schemas.py**: 문서 분류 스키마 + 3종 IaC 유형별 정보 추출 스키마 정의
- **sample_generator.py**: 5종 테스트용 PDF 샘플 생성 (Terraform Basic/Advanced, K8s, Ansible Basic/Advanced)

### 동작 흐름 (AI Agent 패턴)

```
사용자 입력 (CLI)
     │
     ▼
  main.py             ← 대화형 REPL, 단축 명령어 해석
     │
     ▼
  IaCDocAgent          ← 대화 상태 관리 + Upstage Chat API 호출
     │
     ├──▶ Upstage Chat API (solar-pro3, Function Calling)
     │
     ▼
  doc_tools.py         ← 5개 도구 함수 구현
     │
     ├──▶ Upstage Document AI v2 API (classify, extract)
     ├──▶ Upstage Document Parse REST API (parse)
     │
     ▼
  schemas.py           ← 분류 스키마 + 3종 추출 스키마
```

개발자가 Tool을 정의하고, LLM이 언제 호출할지 자율적으로 판단하는 Agent 구조입니다.

1. 사용자 자연어 질문 또는 단축 명령어 입력
2. LLM에 질문과 Tool 목록(5개 도구)을 함께 전달
3. LLM이 Tool 호출 여부를 스스로 판단하여 적절한 도구 선택
4. Tool 실행 후 결과(파싱된 텍스트 + 추출된 구조화 데이터)를 LLM에 반환
5. LLM이 결과를 해석하여 최종 응답 생성 (추가 도구 호출이 필요하면 3~4를 자율 반복)

## API 사용

| API | 용도 | 엔드포인트 |
|-----|------|-----------|
| Chat Completions | 자연어 질문 처리, Function Calling | `v1` (solar-pro3) |
| Document Classify | 문서 유형 분류 | `v2` (document-classify) |
| Document Parse | PDF/이미지 OCR 및 텍스트 추출 | `v1` REST API (document-parse) |
| Information Extract | 스키마 기반 구조화 데이터 추출 | `v2` (information-extract) |

## 추후 개선 가능성

현재 `iac_doc_intel`은 대화형 CLI 도구입니다. 실무 환경에서 더 넓게 활용하려면 다음과 같은 확장이 가능합니다.

### 1. 비대화형 모드 (CI/CD 통합용)

```bash
# PR에 Terraform 파일이 변경되면 자동 실행
python3 iac_doc_intel/main.py --analyze /path/to/main.tf --format json
# → 보안 이슈 개수, 심각도별 분류를 JSON으로 출력
# → exit code로 Pass/Fail 판정 (CRITICAL이 있으면 exit 1)
```

### 2. 배치 분석 + 리포트 생성

```bash
# 디렉토리 내 모든 .tf 파일을 일괄 분석
python3 iac_doc_intel/main.py --scan /infra/ --output report.md
```

### 3. 정책 기반 게이트

```bash
# 예: "0.0.0.0/0 인바운드 규칙이 있으면 FAIL"
# 현재는 LLM이 자유롭게 판단하지만,
# 하드코딩된 정책 규칙 + LLM 분석을 결합
```

### 4. 지식 베이스 + RAG 연계

```bash
# 분석 결과를 지식베이스에 자동 등록
python3 iac_doc_intel/main.py --analyze main.tf --save-to-kb
# → "우리 인프라에서 Aurora 설정이 어떻게 되어있어?"로 검색 가능
```

이런 확장은 기존 Function Calling Agent 구조 위에 입출력 인터페이스와 후처리 레이어를 추가하는 방식으로, 핵심 로직을 거의 변경하지 않고 구현할 수 있습니다.

## 문서

- [질문 가이드](QUESTIONS.md): 카테고리별 질문 예시
- [실제 사용 사례](EXAMPLES.md): 실제 사용 사례와 활용 방향
