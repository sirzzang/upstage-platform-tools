# Commit Guardian 실제 사용 사례

`commit_guardian`의 실제 사용 사례를 정리했습니다.

## 실제 사용 사례

### 사례 0: 변경사항 없을 때의 빠른 종료

Go로 작성된 실제 백엔드 프로젝트를 대상으로, staged/unstaged 변경사항이 없는 상태에서 리뷰를 요청했습니다.

```bash
python3 commit_guardian/main.py ~/projects/my-admin-backend --usage
저장소: /home/user/projects/my-admin-backend

> review staged

[Git Diff 조회] get_git_diff 호출됨
[결과 미리보기]
(변경 사항 없음)

📈 세션 누적: 2회 호출 | 총 3,602 토큰 | 총 비용: $0.000954

현재 저장소에서 staged 상태의 코드 변경 사항을 확인했으나, staged 영역에 반영된 변경이 존재하지 않습니다.
- Grounded 발견사항 수: 0
- 결과: 코드 리뷰 대상 없음

> review unstaged

[Git Diff 조회] get_git_diff 호출됨
[결과 미리보기]
(변경 사항 없음)

📈 세션 누적: 2회 호출 | 총 3,902 토큰 | 총 비용: $0.001134

현재 unstaged 상태의 변경사항이 없습니다.
필요 시 staged 또는 특정 커밋에 대한 검토를 진행해 주세요.
```

변경사항이 없을 때 LLM이 불필요한 도구 호출 없이 **1회 diff 조회 → 즉시 종료**하는 것을 확인할 수 있습니다. 2회 호출, 약 3,600~3,900 토큰, $0.001 수준으로 매우 저렴합니다.

사례 2(자연어 질문)이나 사례 4(test 명령)에서 `get_git_diff`를 3~5번 반복 호출했던 것과 대비됩니다. `review staged`/`review unstaged`처럼 **프롬프트에 mode가 명시**되어 있으면 LLM이 다른 mode를 시도하지 않고 깔끔하게 종료합니다. 이것이 test 명령 개선에서 프롬프트에 mode를 명시하도록 변경한 이유이기도 합니다.

실제 사용 시에는 이 상태에서 `commit <hash>`로 특정 커밋을 지정하여 리뷰를 이어가면 됩니다.

### 사례 1: 단일 커밋 코드 리뷰 — Presigned URL 기능 추가

Go로 작성된 실제 백엔드 프로젝트의 커밋을 리뷰했습니다. 4개 파일에 걸쳐 +158줄, -7줄의 변경으로, 파일 경로 대신 Presigned URL을 반환하도록 하는 기능 추가입니다.

```bash
python3 commit_guardian/main.py ~/projects/my-admin-backend --usage
저장소: /home/user/projects/my-admin-backend

> commit abc1234

[Git Diff 조회] get_git_diff 호출됨
[결과 미리보기]
diff --git a/internal/app/handler/data.go b/internal/app/handler/data.go
index f28831d..053cfa3 100644
--- a/internal/app/handler/data.go
+++ b/internal/app/handler/data.go
@@ -217,7 +217,29 @@ func (...

[코드 변경 분석] analyze_code_changes 호출됨
[결과 미리보기]
[변경 통계]
변경 파일 수: 4
추가된 줄: +158
삭제된 줄: -7
변경 파일:
  - internal/app/handler/data.go
  - internal/app/handler/report.go
  - internal/app/handler/export.go
  - internal/app/handler/user.go
...

[Groundedness 검증] check_finding_groundedness 호출됨
[결과 미리보기]
grounded

[테스트 제안] suggest_tests 호출됨
[결과 미리보기]
[변경된 함수/메서드]
(변경된 함수/메서드를 감지하지 못했습니다)

📈 세션 누적: 5회 호출 | 총 79,155 토큰 | 총 비용: $0.031409

### 코드 리뷰 결과 (Grounded Findings)

**총 발견된 항목:** 10개 (모두 grounded)

---

#### [CRITICAL] 보안 취약점
1. **[CRITICAL]** 에러 응답에 내부 파일 경로 및 에러 상세 노출
   - `strings.Split(record.FilePath, h.bucketName)` 결과 및 `err.Error()`를
     그대로 JSON 응답에 포함 → 민감 정보 유출 가능
   - **제안:** 에러 응답에서 내부 경로를 제거하고, 상세 로그는 서버 로그로 기록

2. **[CRITICAL]** 입력 검증 부재 (파일 경로 분할 로직)
   - `strings.Split(record.FilePath, h.bucketName)`에서
     `h.bucketName`이 설정값으로 사용되나, 입력값 검증 없이 직접 사용
   - **제안:** 특수 문자가 포함될 경우 경로 분할 오류 발생 가능 → 입력 검증 로직 추가 필요

3. **[CRITICAL]** N+1 호출 가능성
   - `h.storageClient.GetPresignedURL()`이 파일 경로마다 개별 호출 → 대량 요청 시 성능 저하 예상
   - **제안:** 파일 경로 목록을 일괄 처리하는 로직 도입 또는 캐싱 메커니즘 적용

---

#### [WARNING] 보안/에러 처리
1. **[WARNING]** `http.StatusInternalServerError` 대신 400 오류 코드 사용 권장
   - 클라이언트가 잘못된 파일 경로를 전달했을 경우 500 대신 400 응답으로 명확화 필요

2. **[WARNING]** `objectKey` 생성 시 `TrimPrefix` 전후 경로 처리 미비
   - `strings.TrimPrefix(pathParts[1], "/")`에서 leading/trailing 슬래시 처리 누락

3. **[WARNING]** 에러 응답 필드 타입 일관성 문제
   - 파일 경로(`string`)와 에러 메시지(`string`)가 혼재 → 클라이언트에서 데이터 파싱 오류 발생 가능

---

#### [INFO] 코드 스타일/성능
1. **[INFO]** `data.Image = &presignedURL` → 포인터 불필요
2. **[INFO]** 중복 코드 발생 (`strings.Split`, `TrimPrefix` 등) → 헬퍼 함수로 추출 가능
3. **[INFO]** `filepath.Clean` 미사용으로 인한 OS 독립성 문제

---

#### [SUGGESTION] 테스트 케이스 제안
1. 정상/비정상 경로 테스트
2. 에러 시나리오 테스트 (`GetPresignedURL()` 실패 시)
3. 보안 테스트 (에러 응답에 민감 정보 포함 여부)
4. 성능 테스트 (100개 이상 파일 경로 요청 시 N+1 확인)
5. JSON 직렬화 테스트

---

#### 릴리스 노트 (자동 생성)
[한국어]
feat: API 응답에서 파일 경로 대신 Presigned URL 제공

[English]
feat: Provide Presigned URLs instead of file paths in API response
```

한 번의 `commit abc1234` 입력으로 CRITICAL 3건, WARNING 3건, INFO 3건, 테스트 제안 5건, 릴리스 노트(한/영)까지 한꺼번에 나왔습니다.

#### Tool 호출 흐름

LLM이 4개의 도구를 순서대로 호출하는 과정이 터미널에 그대로 보입니다.

| 순서 | 도구 | 역할 |
|------|------|------|
| 1 | `get_git_diff` | 커밋의 raw diff 조회 |
| 2 | `analyze_code_changes` | diff + 변경 파일 + 함수 목록으로 리뷰 컨텍스트 구성 |
| 3 | `check_finding_groundedness` | 발견사항이 실제 diff에 근거하는지 검증 |
| 4 | `suggest_tests` | 변경된 함수 기반 테스트 케이스 제안 |

주목할 점은, LLM이 시스템 프롬프트의 워크플로우 지시를 따라 **스스로 도구 호출 순서를 결정**한다는 것입니다. "먼저 diff를 가져오고 → 분석하고 → 발견사항을 검증하고 → 테스트를 제안한다"는 흐름이 코드에 하드코딩된 것이 아니라, `while message.tool_calls:` 루프 안에서 LLM이 자율적으로 판단합니다.

#### Groundedness 검증 결과

이 사례에서는 10개 발견사항이 **모두 grounded** 판정을 받았습니다.

- `check_finding_groundedness`가 1회만 호출된 것으로 보아, LLM이 발견사항을 묶어서 한꺼번에 검증한 것으로 보입니다.
- 발견사항들이 `strings.Split`, `TrimPrefix`, `GetPresignedURL` 등 diff에 실제 등장하는 코드를 구체적으로 언급하고 있어, 근거가 명확합니다.
- notGrounded로 필터링된 항목이 없다는 것은, 이 커밋의 diff가 충분히 구체적이어서 LLM이 환각 없이 분석할 수 있었다는 뜻이기도 합니다.

#### 설계 결정: 정규식 기반 함수 추출을 두지 않은 이유

코드 리뷰 도구를 만들 때, diff에서 변경된 함수/메서드 시그니처를 정규식으로 추출하여 LLM에게 힌트로 제공하는 방식을 고려할 수 있습니다. 예를 들어 Python의 `def`, Go의 `func`, JavaScript의 `function` 등 언어별 키워드를 패턴 매칭하는 것입니다.

이 접근에는 근본적인 한계가 있습니다:
- diff의 변경 줄(`+`/`-`)에 함수 시그니처가 있을 때만 감지 가능 → 기존 함수의 내부 로직만 변경된 경우 감지 불가
- Go 메서드 리시버(`func (h *Handler) Method(...)`)처럼 언어별 변형 패턴을 모두 커버하기 어려움
- TypeScript, Rust 등 지원 언어를 확장할수록 패턴 관리 비용 증가, 멀티라인 시그니처 미지원

이 사례에서 LLM은 raw diff만으로 변경된 핸들러 함수들을 정확히 식별하고, 구체적인 코드 위치를 짚어 리뷰를 수행했습니다. 정규식 힌트가 없어도 리뷰 품질에 차이가 없는 것입니다.

이는 k8s_assistant 사례 5(PDB 오탐 교정)에서 관찰한 것과 같은 패턴입니다. 도구가 제공하는 보조 힌트보다 LLM이 원본 데이터를 직접 읽는 것이 더 정확합니다. 따라서 `suggest_tests` 도구는 diff만 반환하고, `analyze_code_changes`의 리뷰 컨텍스트에도 함수 목록 섹션을 두지 않았습니다. 변경된 함수/메서드 식별은 LLM이 diff를 직접 읽고 수행합니다.

### 사례 2: 자연어 질문의 한계 — 도구가 커버하지 않는 영역

사례 1의 세션을 이어서, 자연어로 특정 주제에 대한 리뷰를 요청했습니다.

```bash
> presigned URL 관련 코드에 문제가 없는지 리뷰해줘

[Git Diff 조회] get_git_diff 호출됨
[결과 미리보기]
(변경 사항 없음)

[Git Diff 조회] get_git_diff 호출됨
[결과 미리보기]
(변경 사항 없음)

[Git Diff 조회] get_git_diff 호출됨
[결과 미리보기]
(변경 사항 없음)

[Git Diff 조회] get_git_diff 호출됨
[결과 미리보기]
(변경 사항 없음)

[Git Diff 조회] get_git_diff 호출됨
[결과 미리보기]
diff --git a/internal/app/handler/user.go b/internal/app/handler/user.go
...

📈 세션 누적: 6회 호출 | 총 12,586 토큰 | 총 비용: $0.003273

## 코드 리뷰 요약

- **총 발견사항:** 1건
- **Grounded 발견사항:** 1건 (presigned URL 관련 코드가 현재 diff에 포함되어 있지 않음)

### 발견 사항
**[INFO]** `presigned URL` 관련 코드가 **unstaged / staged / commit** diff에 포함되어 있지 않습니다.

### 일반적인 presigned URL 구현 시 고려해야 할 체크리스트 (참고용)

| 카테고리 | 체크 포인트 |
|----------|-------------|
| **보안** | 버킷 정책 private 유지, IAM 최소 권한, URL 유효 기간 제한 |
| **에러 처리** | PresignClient 에러 로깅 시 민감 정보 제외 |
| **성능** | 대량 요청 시 비동기/배치 처리, 캐시 TTL 관리 |
| **테스트** | 만료 시간별 테스트, IAM 권한 부재 시 에러, 잘못된 URL 파싱 |
```

LLM이 `get_git_diff`를 5번이나 반복 호출했습니다. unstaged → staged → 최근 커밋 등 여러 모드를 시도한 것으로 보이는데, presigned URL 관련 변경사항을 찾지 못했습니다.

#### 왜 찾지 못했는가

이 도구의 근본적인 제약은 **diff 기반으로만 코드를 볼 수 있다**는 점입니다. 사용 가능한 도구 5개 모두 diff나 커밋 로그를 조회하는 것이고, 저장소의 파일을 직접 읽거나 검색하는 도구는 없습니다.

| 사용자 의도 | 필요한 도구 | 실제 가용 도구 |
|-------------|-------------|---------------|
| "presigned URL 코드를 리뷰해줘" | 파일 검색/읽기 (`grep`, `cat`) | `get_git_diff` (변경사항만) |

LLM은 이 한계를 인식하고, presigned URL 코드가 현재 diff에 없다는 사실을 정직하게 알려주었습니다. 대신 일반적인 presigned URL 구현 체크리스트를 제공했는데, 이는 실제 코드가 아닌 LLM의 사전 학습 지식에 기반한 것입니다.

#### 도구 설계의 범위 문제

이것은 LLM의 한계가 아니라, **개발자가 해당 도구(핸들러)를 정의하지 않은 것**으로 보는 것이 자연스럽습니다.

- k8s_assistant에서 `analyze_repo`를 추가한 뒤 매니페스트 품질이 극적으로 달라졌던 것(사례 7 → 8)과 같은 구조입니다.
- commit_guardian에 `search_code`나 `read_file` 같은 도구를 추가하면, "presigned URL 코드를 리뷰해줘" 같은 자연어 요청도 처리할 수 있을 것입니다.
- 다만 이는 "커밋/변경사항 리뷰"라는 이 도구의 설계 의도를 넘어서는 영역이기도 합니다.

LLM이 도구의 범위 밖 요청을 받았을 때 **환각 없이 솔직하게 한계를 알려주고, 대안(일반 체크리스트)을 제시**한 점은 긍정적입니다. `get_git_diff`를 5번 반복 호출한 것은 비효율적이지만, 가용한 도구 안에서 최선을 다한 결과이기도 합니다.

### 사례 3: 에러 핸들링 커밋 리뷰 — TODO 주석까지 짚어내는 분석

사례 1과 같은 세션에서, 에러 핸들링 관련 커밋을 이어서 리뷰했습니다. 1개 파일, +33줄/-1줄의 작은 변경입니다.

```bash
> commit a96c8b8

[Git Diff 조회] get_git_diff 호출됨
[Groundedness 검증] check_finding_groundedness 호출됨 → grounded
[테스트 제안] suggest_tests 호출됨
[Groundedness 검증] check_finding_groundedness 호출됨 → grounded
[Git Diff 조회] get_git_diff 호출됨 → (변경 사항 없음)
[코드 변경 분석] analyze_code_changes 호출됨

📈 세션 누적: 13회 호출 | 총 54,373 토큰 | 총 비용: $0.013084

## 커밋 코드 리뷰 결과
- **총 발견사항:** 2건
- **Grounded 발견사항:** 2건

### 1. [CRITICAL] 에러 메시지 노출
- `err.Error()`를 클라이언트 JSON 응답에 직접 포함 → 내부 DB 오류 상세 정보 유출
- **제안:** 응답에서 제거하고, 서버 로그에만 기록

### 2. [INFO] TODO 로직 미구현
- 주석 처리된 중복 업로드 방지 로직 감지
- 비즈니스 로직 누락으로 판단, 주석 해제 후 구현 권고
```

사례 1과 달리 흥미로운 점이 두 가지 있습니다.

#### Groundedness 검증이 2회 호출됨

사례 1에서는 10개 발견사항을 묶어 1회만 검증했지만, 이번에는 **발견사항 2건에 대해 각각 1회씩** `check_finding_groundedness`를 호출했습니다. LLM이 매번 같은 전략을 쓰는 것이 아니라, 상황에 따라 검증 방식을 달리한다는 것을 보여줍니다. 발견사항이 적을 때는 개별 검증이, 많을 때는 일괄 검증이 선택되는 것으로 보입니다.

#### TODO 주석을 코드 리뷰 대상으로 인식

가장 인상적인 부분입니다. diff에 추가된 주석 처리된 코드 블록(`// TODO: uncomment below...`)을 단순히 무시하지 않고, **비즈니스 로직 누락**으로 판단하여 [INFO]로 보고했습니다. 주석 안에 있는 `switch` 문의 분기 조건, `http.StatusConflict` 응답 구조까지 분석하고, 구현 시 주의사항(상수 매핑, 플래그 초기화)까지 제안했습니다.

이것은 사람 리뷰어가 "이 TODO 언제 구현할 건지?" 라고 물어보는 것과 같은 수준의 리뷰입니다. 정적 분석 도구는 주석을 무시하지만, LLM은 주석의 의미를 이해하고 리뷰 대상으로 삼을 수 있다는 차이점이 드러납니다.

#### 비용 누적

이 시점에서 세션 누적 비용이 $0.013으로, 사례 1($0.031)보다 낮습니다. 변경 규모가 작아(1파일, +33줄) diff 토큰이 적었기 때문입니다. 다만 세션 누적 13회 호출이라는 점에서, 한 세션에서 여러 커밋을 이어서 리뷰하면 **대화 히스토리 누적으로 인한 토큰 증가**가 발생합니다.

### 사례 4: test 명령 — notGrounded 첫 등장과 세션 컨텍스트 활용

같은 세션에서 `test` 명령을 실행했습니다. 이 시점에서 unstaged/staged 변경사항은 없는 상태였습니다.

```bash
> test

[Git Diff 조회] get_git_diff 호출됨 → (변경 사항 없음)
[Git Diff 조회] get_git_diff 호출됨 → (변경 사항 없음)
[Git Diff 조회] get_git_diff 호출됨 → user.go diff 발견
[Groundedness 검증] check_finding_groundedness 호출됨 → notGrounded
[테스트 제안] suggest_tests 호출됨 → user.go diff

📈 세션 누적: 19회 호출 | 총 110,726 토큰 | 총 비용: $0.024525

## 전체 테스트 제안 개요
- 테스트 대상: user.go 핸들러 + DB 레이어 (2개 함수)
- 테스트 유형: 유닛 테스트 (sqlmock) + 통합 테스트 (Gin 라우터)
- 테스트 도구: go test + sqlmock + testify
- 커버리지 목표: 비즈니스 로직 90%, DB 오류 경로 100%

핸들러 테스트 케이스 6건, DB 레이어 테스트 케이스 11건 (Insert 6건 + Delete 5건),
심각도별 분류, Go 테스트 코드 예시까지 포함된 상세한 응답.
```

#### notGrounded 첫 등장

이 세션에서 처음으로 **notGrounded** 판정이 나왔습니다.

사례 1(10건 모두 grounded), 사례 3(2건 모두 grounded)과 달리, LLM이 도출한 발견사항 중 하나가 실제 diff에 근거하지 않는 것으로 판정되었습니다. 이 발견사항은 최종 응답에서 제외되었고, 사용자에게는 grounded된 내용만 제시되었습니다.

Groundedness 검증이 실제로 필터링 역할을 수행한 첫 사례입니다. 앞선 사례들에서는 "모두 grounded"여서 이 메커니즘이 안전장치로만 존재했지만, 여기서는 **실제로 환각을 걸러냈습니다**.

#### unstaged가 없을 때의 LLM 대응

`test` 명령의 프롬프트에는 mode 지정이 없어 기본값 unstaged로 동작합니다. 그런데 unstaged 변경사항이 없었습니다.

LLM은 `get_git_diff`를 3번 호출하면서 unstaged → staged → 최근 커밋 순으로 탐색하여, 결국 최근 커밋의 diff를 찾아냈습니다. 사례 2(자연어 질문)에서도 같은 패턴이 나타났는데, 가용한 도구 안에서 여러 mode를 시도하는 것은 LLM의 자율적 판단입니다.

#### 세션 컨텍스트의 영향

가장 주목할 점은 **테스트 제안의 범위**입니다. `suggest_tests`가 반환한 diff는 `user.go` 1개 파일뿐인데, 최종 응답에는 `user.go` 핸들러 테스트뿐 아니라 DB 레이어(`InsertLabTestReports`, `DeleteLabTestReportById`)까지 포함되어 있습니다.

이는 같은 세션에서 앞서 수행한 커밋 리뷰들(사례 1, 3)의 대화 히스토리가 남아 있기 때문입니다. LLM이 이전 리뷰에서 파악한 코드 구조(핸들러 → 리포지토리 → DB)를 기억하고, 테스트 제안에 반영한 것입니다.

- 장점: 단일 diff보다 넓은 범위의 테스트를 제안할 수 있음
- 단점: 세션 히스토리 누적으로 토큰 비용 증가 (이 시점에서 110K 토큰, $0.025)
- 주의: 이전 리뷰 내용에 기반한 테스트 제안은 groundedness 검증을 통과하지 않았을 수 있음 (현재 diff에 없는 코드에 대한 제안이므로)

#### 비용 누적

| 시점 | 세션 누적 호출 | 토큰 | 비용 |
|------|--------------|------|------|
| 사례 1 (commit 리뷰) | 5회 | 79K | $0.031 |
| 사례 3 (commit 리뷰) | 13회 | 54K | $0.013 |
| 사례 4 (test) | 19회 | 111K | $0.025 |

한 세션에서 여러 작업을 이어서 수행할수록 대화 히스토리가 쌓이면서 토큰이 누적됩니다. `test` 자체는 5개 도구 호출이었지만, 이전 대화가 매 호출마다 함께 전송되므로 토큰 소모가 큽니다.

### 사례 5: test 명령 개선 후 — 커밋 지정과 정확한 도구 호출

사례 4에서 관찰한 문제(반복 호출, mode 미지정)를 개선한 뒤, `test <hash>` 형태로 특정 커밋을 지정하여 테스트 제안을 요청했습니다.

```bash
> test e1132d5

[테스트 제안] suggest_tests 호출됨
[결과 미리보기]
diff --git a/internal/app/handler/user.go ...

📈 세션 누적: 4회 호출 | 총 10,345 토큰 | 총 비용: $0.003375

### 커밋 변경사항에 대한 테스트 제안
- 핸들러 테스트: 경계값(20시간), 에러 처리, 성능(N+1 쿼리)
- DB 레이어 테스트: 동시성, 빈 슬라이스, 제약 위반, 에러 전파
- 테스트 도구: go test + testify + sqlmock
- 커버리지 목표: 핵심 로직 80% 이상

(Go 테스트 코드 예시 포함: 단위 테스트 + 통합 테스트)

### 다음 단계
1. 위 테스트 케이스를 실제 go test 파일에 구현
2. CI 파이프라인에 동시성 테스트와 coverage 체크 추가
3. 테스트 통과 후 git commit으로 커밋하고 PR에 리뷰
```

#### 사례 4와의 비교

| 항목 | 사례 4 (개선 전) | 사례 5 (개선 후) |
|------|-----------------|-----------------|
| 입력 | `test` (대상 미지정) | `test e1132d5` (커밋 지정) |
| `get_git_diff` 호출 | 3회 (unstaged → staged → 최근 커밋 탐색) | 0회 (불필요) |
| `suggest_tests` 호출 | 1회 | 1회 |
| `check_finding_groundedness` | 2회 (notGrounded 1건 포함) | 0회 |
| 총 도구 호출 | 6회 | 1회 |
| 토큰 | 110,726 (세션 누적) | 10,345 (새 세션) |
| 비용 | $0.025 (세션 누적) | $0.003 |

프롬프트에 "커밋 {hash}의 변경사항"이라고 mode를 명시했기 때문에, LLM이 `suggest_tests`를 정확한 mode(`commit`)와 hash로 **1회만 호출**했습니다. `get_git_diff`를 반복 시도하는 낭비가 완전히 사라졌습니다.

#### 다음 단계 안내가 인상적

테스트 제안 끝에 "다음 단계"를 구체적으로 안내하는 점이 좋습니다. 단순히 테스트 케이스를 나열하는 것에 그치지 않고, **구현 → CI 통합 → 커밋/PR**까지의 워크플로우를 제시합니다. k8s_assistant에서 매 응답 끝에 후속 선택지를 유도하던 패턴(사례 6)과 동일한 구조이지만, 여기서는 테스트 개발 프로세스에 맞게 구체화되어 있습니다.

### 사례 6: 릴리스 노트 생성 — 한/영 동시, 최저 비용

새 세션에서 `release` 명령을 실행했습니다.

```bash
> release

[릴리스 노트 생성] generate_release_notes 호출됨
[결과 미리보기]
[커밋 로그]
e1132d5 feat: Remove unnecessary transactions from repository
5eb87de feat: Set analysis status to true when there's lab test report uploaded
a96c8b8 feat: Reserve error handling for conflicti...

📈 세션 누적: 2회 호출 | 총 4,680 토큰 | 총 비용: $0.001538

## 릴리스 노트 (한국어)

### feat (기능 추가 / 개선)
- e1132d5: 저장소에서 불필요한 트랜잭션을 제거했습니다.
- 5eb87de: 검사 보고서가 업로드될 때 분석 상태를 true로 자동 설정하도록 기능을 추가했습니다.
- a96c8b8: 충돌하는 검사 보고서에 대한 에러 처리 로직을 예약했습니다.
- 40e9c96: 사용자가 검사 보고서를 업로드하지 않은 경우의 에러 케이스를 삭제했습니다.
- 7acbb44: 모든 객체 파일 경로를 버킷 엔드포인트를 이용해 올바르게 분할하도록 수정했습니다.

### test (테스트 케이스 추가)
- 파일 경로 분할 및 상태 전환 로직에 대한 단위 테스트가 추가되었습니다.

### docs (문서 업데이트)
- 검사 보고서 업로드 흐름과 분석 상태 전환 로직에 대한 API 문서가 최신화되었습니다.

---

## Release Notes (English)

### feat (Feature)
- e1132d5: Removed unnecessary transactions from the repository to improve performance.
- 5eb87de: Added logic to set analysis status to true automatically when a lab test report is uploaded.
- a96c8b8: Reserved error handling for cases where conflicting lab test reports exist.
- 40e9c96: Removed the error case that previously fired when a user had not uploaded any lab test.
- 7acbb44: Fixed the splitting of object file paths using the bucket endpoint to ensure correct path resolution.

### test (Testing)
- Test coverage increased with unit tests for file path splitting and analysis status transition logic.

### docs (Documentation)
- API documentation for lab test report upload flow and analysis status transition has been updated.
```

#### 비용: 전체 사례 중 최저

2회 호출, 4,680 토큰, **$0.0015**. 코드 리뷰(사례 1: $0.031)의 1/20 수준입니다. `generate_release_notes` 도구가 커밋 로그 + 변경 파일 + diff를 한꺼번에 반환하므로 도구 호출이 1회로 끝나고, groundedness 검증도 필요 없기 때문입니다.

#### 일반적인 릴리스 노트와 비교

잘한 점:
- **Conventional Commits 분류가 정확** — 5개 커밋 모두 `feat:`으로 시작하는 원본 메시지를 정확히 feat 카테고리로 분류했습니다.
- **한/영 동시 생성** — 한국어 섹션과 영어 섹션이 동일한 구조로 생성되어, 다국어 팀에서 바로 사용 가능합니다.
- **커밋 해시 참조** — 각 항목에 커밋 해시가 포함되어 있어, 릴리스 노트에서 실제 변경으로 역추적하기 쉽습니다.

아쉬운 점:
- **test, docs 카테고리가 환각** — 실제 커밋 5개는 모두 `feat:`인데, 존재하지 않는 test/docs 변경을 만들어냈습니다. "테스트 커버리지가 증가했으며", "API 문서가 최신화되었습니다"라는 내용은 실제 커밋에 없습니다. 코드 리뷰에서는 groundedness 검증이 이를 걸러냈겠지만, **릴리스 노트 생성 경로에는 groundedness 검증이 적용되지 않습니다**.
- **커밋 메시지 의역 수준** — 원본 "Remove unnecessary transactions from repository"를 "저장소에서 불필요한 트랜잭션을 제거했습니다"로 거의 직역했습니다. 릴리스 노트라면 사용자 관점에서 "DB 트랜잭션 오버헤드를 줄여 성능을 개선했습니다" 같은 **영향 중심 서술**이 더 적합합니다.
- **버전 번호, 날짜 없음** — 일반적인 릴리스 노트에는 `v1.2.0 (2026-02-08)` 같은 헤더가 있지만, 이 도구는 버전 관리 정보를 참조하지 않으므로 누락됩니다.

정리하면, 커밋 로그 기반 초안으로는 충분히 유용하지만, **최종 릴리스 노트로 그대로 사용하기보다는 편집이 필요한 수준**입니다. 특히 환각된 test/docs 카테고리는 삭제해야 합니다.

## 강점

1. **심각도 분류가 실용적**
   - CRITICAL/WARNING/INFO/SUGGESTION 4단계 분류로, 어떤 항목을 먼저 처리해야 하는지 명확합니다.
   - 보안 취약점(민감 정보 노출)은 CRITICAL, 코드 스타일(포인터 불필요)은 INFO로 적절히 구분됩니다.

2. **발견사항이 구체적이고 실행 가능함**
   - "보안 이슈가 있을 수 있습니다" 같은 모호한 피드백이 아니라, **정확한 코드 위치와 함수명**을 짚어줍니다.
   - 각 발견사항에 **구체적인 수정 제안**이 포함되어 있어, 리뷰를 받은 뒤 바로 수정 작업에 들어갈 수 있습니다.

3. **Groundedness 검증으로 환각 방지**
   - AI 코드 리뷰의 가장 큰 위험인 "없는 코드를 있다고 지적하는" 환각을, 별도 LLM 호출로 필터링합니다.
   - 이 사례에서는 10건 모두 grounded였지만, 대규모 diff에서 환각이 섞일 가능성을 구조적으로 차단하는 안전장치입니다.

4. **코드 리뷰 + 테스트 제안 + 릴리스 노트를 한꺼번에 제공**
   - 한 번의 커밋 리뷰로 코드 품질 피드백, 테스트 케이스, 릴리스 노트까지 모두 얻을 수 있습니다.
   - 릴리스 노트가 한국어/영어 모두 생성되어, 다국어 팀에서 바로 활용 가능합니다.

5. **실제 코드를 읽는 리뷰**
   - `git diff`/`git show`로 실제 변경 내역을 가져와서 분석하므로, 일반적인 "코드 패턴 검사 도구"와 달리 변경의 맥락을 이해합니다.
   - N+1 호출 가능성(`GetPresignedURL`을 파일마다 개별 호출)처럼, 단순 정적 분석으로는 잡기 어려운 패턴도 감지합니다.

## 비용에 대한 관찰

이 사례에서 가장 눈에 띄는 수치는 **비용**입니다.

```
📈 세션 누적: 5회 호출 | 총 79,155 토큰 | 총 비용: $0.031409
```

단일 커밋 리뷰 하나에:
- **5회 API 호출** (메인 LLM 호출 + 도구 결과 반영 재호출 + groundedness 검증용 별도 호출)
- **79,155 토큰** 소모
- **약 $0.03** 비용

커밋 하나당 약 3센트는 단발성으로는 저렴하지만, 팀 규모와 커밋 빈도를 고려하면 빠르게 늘어날 수 있습니다.

| 시나리오 | 일일 커밋 수 | 일일 비용 | 월간 비용 (20일) |
|----------|-------------|----------|-----------------|
| 개인 프로젝트 | 5 | $0.15 | $3 |
| 소규모 팀 (5명) | 25 | $0.75 | $15 |
| 중규모 팀 (20명) | 100 | $3.00 | $60 |

비용이 높아지는 구조적 이유:
- **메인 LLM + Groundedness 검증 LLM**: 같은 solar-pro3 모델을 2번 이상 호출합니다.
- **diff가 길수록 토큰 증가**: 이 커밋은 +158줄이었는데, 대규모 리팩토링이면 토큰이 배로 늘어납니다.
- **Tool Calling 루프**: LLM이 도구를 호출할 때마다 이전 대화 전체를 다시 전송하므로, 호출 횟수에 비례하여 토큰이 누적됩니다.

비용 최적화 방향:
- Groundedness 검증을 경량 모델이나 전용 API로 대체하면 1회 호출을 절약할 수 있습니다.
- diff 길이 제한(현재 8000자)을 줄이면 토큰 비용이 감소하지만, 리뷰 품질과 트레이드오프입니다.
- CI/CD에 통합할 경우, 모든 커밋이 아니라 PR 단위로만 실행하면 호출 빈도를 줄일 수 있습니다.

확실히 유용한 리뷰를 제공하지만, **"모든 커밋에 자동 적용"보다는 "중요한 변경에 선택적으로 사용"하는 편이 현실적**입니다.

## 활용 방향

- **PR 리뷰 보조**: 머지 전에 주요 커밋을 `commit <hash>`로 빠르게 검토하여, 사람 리뷰어의 부담을 줄일 수 있습니다.
- **보안 감사**: Presigned URL, 인증 토큰, DB 접근 관련 커밋을 중점적으로 리뷰하여 보안 취약점을 사전에 탐지합니다.
- **온보딩**: 새 팀원이 기존 코드의 변경 이력을 이해할 때, 커밋별 리뷰를 통해 변경의 맥락과 주의점을 빠르게 파악할 수 있습니다.
- **릴리스 노트 자동화**: `release` 명령으로 최근 커밋들의 릴리스 노트를 한/영 모두 생성하여, 수동 작성 시간을 절약합니다.

## 사용 팁

1. **비용을 추적하면서 사용**: `--usage` 플래그로 세션별 비용을 확인합니다.
   ```bash
   python3 commit_guardian/main.py ~/projects/my-repo --usage
   ```
2. **대규모 변경보다 단일 기능 커밋이 효과적**: diff가 8000자를 넘으면 잘리므로, atomic commit 단위로 리뷰하는 것이 좋습니다.
3. **자연어로 초점을 맞출 수 있습니다**: "보안 관점에서만 리뷰해줘", "에러 핸들링만 봐줘"처럼 구체적으로 요청하면 해당 관점에 집중한 리뷰를 받을 수 있습니다.

## 예시 세션

```bash
> commit abc1234                             # 특정 커밋 리뷰
> review                                     # unstaged 변경사항 리뷰
> staged                                     # staged 변경사항 리뷰
> 보안적으로 주의해야 할 부분이 있는지 확인해줘   # 자연어 질문
> release                                    # 릴리스 노트 생성 (한/영)
> test                                       # 테스트 케이스 제안
```
