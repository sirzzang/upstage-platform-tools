# MLOps Dashboard

자연어로 MLOps 플랫폼 데이터를 조회하는 읽기 전용 대시보드입니다. SQL 지식 없이도 프로젝트, 실험, 데이터셋, 파이프라인, 아티팩트, 모델 메트릭을 검색할 수 있습니다.

## 기능

다음과 같은 기능을 지원합니다.

- 자연어 질문을 SQL 쿼리로 자동 변환
- 오타 및 띄어쓰기 오류 자동 보정
- SQL 오류 자동 수정 및 재시도
- 실무 의사결정 지원 (Precision/Recall 트레이드오프 기반 모델 추천)
- 사용량 추적 (`--usage` 플래그)

## User Interface

이 대시보드는 **CLI (Command Line Interface)**로 제공됩니다.

- 대화형 프롬프트(`>`)를 통해 자연어 질문 입력
- 질문에 대한 SQL 쿼리 생성 및 실행 결과를 자동으로 설명
- `quit` 또는 `exit` 명령으로 종료
- `Ctrl+C` 또는 `EOF`로도 종료 가능

## 데이터베이스 스키마

```
users → projects → datasets → pipelines → artifacts
                                ↓
                              models → metrics
```

### 주요 엔티티

- **users**: 사용자 정보 (이름, 이메일, 팀, 역할)
- **projects**: 프로젝트 (타입, 상태)
- **datasets**: 데이터셋 (포맷, 샘플 수, 용량)
- **pipelines**: 학습 파이프라인 (상태, GPU 타입, 프레임워크)
- **artifacts**: 아티팩트 (체크포인트, 로그, 설정 파일)
- **models**: 모델 (아키텍처, 버전, 스테이지, 파라미터 수)
- **metrics**: 평가 메트릭 (mAP50, F1, precision, recall, 추론 시간)

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
python3 mlops_dashboard/main.py
```

처음 실행 시 샘플 데이터베이스가 자동으로 생성되고, data/sample_db에 저장됩니다.

### 사용량 추적

`--usage` 플래그로 각 응답의 토큰 사용량과 예상 비용을 확인할 수 있습니다.

```bash
python3 mlops_dashboard/main.py --usage
```

## 사용 예시

```bash
> 김민준의 프로젝트 목록 보여줘
> defect-detection-v2 프로젝트의 모델 성능 비교해줘
> 오탐이 적은 모델 추천해줘
> A100 GPU를 사용한 파이프라인은 몇 개야?
> yolov8-wafer-exp01의 체크포인트 경로 알려줘
```

## 구조

### 주요 파일

- **main.py**: CLI 진입점
- **sql_agent.py**: SQLAgent 클래스 (Upstage API와 통신)
- **db_manager.py**: SQLite 데이터베이스 관리 (스키마 조회, 쿼리 실행)
- **setup_db.py**: 샘플 데이터베이스 생성

### 동작 흐름 (AI Agent 패턴)

개발자가 Tool을 정의하고, LLM이 언제 호출할지 자율적으로 판단하는 Agent 구조입니다.

1. 사용자 자연어 질문 입력
2. LLM에 질문과 Tool 목록(`execute_sql`)을 함께 전달
3. LLM이 Tool 호출 여부를 스스로 판단하여 SQL 쿼리 생성
4. Tool 실행 후 결과를 LLM에 반환
5. LLM이 결과를 해석하여 최종 응답 생성 (추가 조회나 오류 수정이 필요하면 3~4를 자율 반복)

### 보안

- SELECT 쿼리만 허용 (DROP, DELETE, UPDATE, INSERT 등 차단)
- 읽기 전용 접근

## API 사용

- **모델**: `solar-pro3`
- **Chat Completions**: 자연어 질문 처리
- **Function Calling**: SQL 쿼리 생성 및 실행

## 문서

- [질문 가이드](QUESTIONS.md): 카테고리별 질문 예시
- [실제 사용 사례](EXAMPLES.md): 실제 사용 사례와 성능 감상

