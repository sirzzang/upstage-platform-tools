# Commit Guardian

Git 커밋과 코드 변경사항을 AI가 자동으로 리뷰하는 대화형 CLI 도구입니다. Groundedness Check로 AI 환각을 필터링하여, 실제 diff에 근거한 발견사항만 제시합니다.

## 기능

- unstaged/staged/특정 커밋의 코드 변경사항 리뷰
- 심각도 분류: [CRITICAL] [WARNING] [INFO] [SUGGESTION]
- Groundedness Check: 발견사항이 실제 diff에 근거하는지 검증하여 환각 방지
- 변경사항 기반 테스트 케이스 제안 (변경 없으면 최근 커밋으로 자동 fallback)
- 릴리스 노트 자동 생성 (한국어 + 영어, Conventional Commits 스타일)
- 사용량 추적 (`--usage` 플래그)

## User Interface

이 도구는 **CLI (Command Line Interface)**로 제공됩니다.

- 대화형 프롬프트(`>`)를 통해 단축 명령 또는 자연어 입력
- `help` - 도움말 표시
- `clear` - 대화 초기화
- `quit` 또는 `exit` - 종료

### 단축 명령

| 명령 | 설명 |
|------|------|
| `review` | unstaged 변경사항 리뷰 |
| `staged` | staged 변경사항 리뷰 |
| `commit <hash>` | 특정 커밋 리뷰 |
| `test` | 테스트 제안 (변경 없으면 최근 커밋) |
| `test staged` | staged 변경사항에 대한 테스트 제안 |
| `test <hash>` | 특정 커밋에 대한 테스트 제안 |
| `release` | 릴리스 노트 생성 (한/영) |
| `repo <path>` | 저장소 경로 변경 |

자연어 입력도 지원합니다. 단, 자연어 질문도 diff 기반으로 동작하므로, 단축 명령으로 diff를 확보한 뒤 후속 질문으로 사용하는 것이 효과적입니다: `commit abc1234` → "보안 관점에서만 더 자세히 봐줘".

## 리뷰 체크리스트

시스템 프롬프트에 정의된 코드 리뷰 관점입니다.

| 카테고리 | 검사 항목 |
|----------|----------|
| 보안 | SQL 인젝션, XSS, 하드코딩된 시크릿, 권한 문제 |
| 성능 | N+1 쿼리, 불필요한 반복, 메모리 누수, 큰 파일 로딩 |
| 에러 처리 | 미처리 예외, 빈 catch 블록, 에러 메시지 노출 |
| 코드 스타일 | 네이밍 규칙, 코드 중복, 함수 길이, 복잡도 |
| 테스트 | 테스트 커버리지, 경계값 테스트, 에러 케이스 테스트 |

이 항목들은 검증 규칙이 아니라 LLM에 대한 지시입니다. LLM이 diff를 직접 읽고 해당 관점에서 발견사항을 도출하며, 하드코딩된 패턴 매칭이 아니므로 언어나 프레임워크에 관계없이 동작합니다.

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
python3 commit_guardian/main.py /path/to/git/repo
```

### 사용량 추적

`--usage` 플래그로 각 응답의 토큰 사용량과 예상 비용을 확인할 수 있습니다.

```bash
python3 commit_guardian/main.py /path/to/git/repo --usage
```

## 사용 예시

```bash
> commit abc1234                             # 특정 커밋 리뷰
> review                                     # unstaged 변경사항 리뷰
> staged                                     # staged 변경사항 리뷰
> 보안적으로 주의해야 할 부분이 있는지 확인해줘   # 자연어 후속 질문 (diff 있는 상태에서)
> test abc1234                               # 특정 커밋 테스트 제안
> release                                    # 릴리스 노트 생성 (한/영)
> clear                                      # 대화 초기화 (토큰 절약)
```

## 구조

### 주요 파일

- **main.py**: CLI 진입점 (REPL 루프, 단축 명령 파싱, test fallback 로직)
- **guardian_agent.py**: GuardianAgent 클래스 (Upstage API와 통신, Function Calling 오케스트레이션)
- **git_tools.py**: Git 명령어 래퍼 (diff, log, show, changed files)
- **review_tools.py**: diff 통계 파싱 및 리뷰 컨텍스트 포맷팅
- **groundedness.py**: 발견사항의 근거 검증 (별도 LLM 호출로 환각 필터링)

### 동작 흐름 (Groundedness Check 포함)

```
사용자 입력 (CLI)
     │
     ▼
  main.py               ← 단축 명령 파싱, test fallback 로직
     │
     ▼
  GuardianAgent         ← 대화 상태 관리 + Upstage API 호출
     │
     ├──▶ Upstage API (solar-pro3, Function Calling)
     │         │
     │         ▼
     │    LLM이 도구 호출 판단 ──────────────────────────┐
     │         │                                     │
     │         ▼                                     ▼
     │    [1] get_git_diff          [2] analyze_code_changes
     │         │  git diff 실행           │  diff + 통계 + 파일 목록
     │         │                         │
     │         ▼                         ▼
     │    LLM이 diff를 분석하여 발견사항 도출
     │         │
     │         ▼
     │    [3] check_finding_groundedness   ← 핵심: 환각 필터링
     │         │  발견사항 vs 실제 diff 대조
     │         │  (별도 solar-pro3 호출)
     │         │
     │         ├── grounded    → 최종 리뷰에 포함
     │         ├── notGrounded → 최종 리뷰에서 제외
     │         └── notSure     → 최종 리뷰에서 제외
     │         │
     │         ▼
     │    [4] suggest_tests / [5] generate_release_notes
     │         │
     │         ▼
     │    LLM이 grounded 발견사항만으로 최종 응답 생성
     │
     ▼
  사용자에게 리뷰 결과 출력
```

개발자가 Tool을 정의하고, LLM이 언제 호출할지 자율적으로 판단하는 Agent 구조입니다. 특히 Groundedness Check는 코드에 하드코딩된 순서가 아니라, 시스템 프롬프트의 워크플로우 지시를 따라 LLM이 자율적으로 수행합니다.

### Groundedness Check 상세

AI 코드 리뷰의 가장 큰 위험은 "없는 코드를 있다고 지적하는" 환각입니다. Commit Guardian은 이를 구조적으로 방지합니다.

1. 메인 LLM이 diff를 분석하여 발견사항을 도출
2. 각 발견사항을 `check_finding_groundedness` 도구로 전달
3. 도구 내부에서 **별도의 solar-pro3 호출**로 "이 발견사항이 실제 diff에 근거하는가?" 판정
4. `grounded` 판정을 받은 발견사항만 최종 리뷰에 포함
5. 필터링된 항목 수를 사용자에게 알림

이 검증은 코드 리뷰 경로(`review`, `staged`, `commit`)에만 적용됩니다. 릴리스 노트 생성(`release`)과 테스트 제안(`test`)에는 적용되지 않습니다.

diff에서 변경된 함수를 식별하는 데 정규식 패턴이 아닌 LLM 직접 분석을 채택한 이유는 [EXAMPLES.md](./EXAMPLES.md)의 "설계 결정" 항목을 참고하세요.

## 등록된 도구 (Function Calling)

| 도구 | 설명 |
|------|------|
| `get_git_diff` | unstaged/staged/특정 커밋의 diff 조회 |
| `analyze_code_changes` | diff + 변경 통계 + 파일 목록으로 리뷰 컨텍스트 구성 |
| `suggest_tests` | 변경사항 기반 테스트 케이스 제안용 diff 반환 |
| `check_finding_groundedness` | 발견사항이 실제 diff에 근거하는지 검증 (환각 방지) |
| `generate_release_notes` | 커밋 로그 + diff 기반 릴리스 노트 생성 컨텍스트 구성 |

## API 사용

- **모델**: `solar-pro3`
- **Chat Completions**: 자연어 질문 처리 + 코드 리뷰
- **Function Calling**: Git diff 조회, 코드 분석, Groundedness 검증, 릴리스 노트 생성

## 비용 참고

커밋 규모와 세션 길이에 따라 다르지만, 대략적인 비용:

| 작업 | 호출 수 | 토큰 | 비용 |
|------|--------|------|------|
| 단일 커밋 리뷰 (158줄 변경) | 5회 | ~80K | ~$0.03 |
| 테스트 제안 (커밋 지정) | 2회 | ~10K | ~$0.003 |
| 릴리스 노트 생성 | 2회 | ~5K | ~$0.0015 |

세션을 이어가면 대화 히스토리 누적으로 토큰이 증가합니다. 작업 간에 `clear`로 초기화하면 비용을 절약할 수 있습니다.

## 문서

- [질문 가이드](QUESTIONS.md): 카테고리별 질문 예시
- [실제 사용 사례](EXAMPLES.md): 실제 사용 사례와 활용 방향
