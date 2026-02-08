# MLOps Dashboard 실제 사용 사례

## 실제 사용 사례

### 사례 1: 기본 조회 및 오타 처리

```bash
> 김민준이 몇 번의 실험을 했어?

[SQL] SELECT COUNT(*) AS experiment_count FROM pipelines p JOIN datasets d ON p.dataset_id = d.id JOIN projects pr ON d.project_id = pr.id WHERE pr.user_id = (SELECT id FROM users WHERE name = '김민준') AND p.model_id IS NOT NULL;

[결과]
[SQL 오류] no such column: p.model_id

[SQL] SELECT COUNT(DISTINCT p.id) AS experiment_count FROM pipelines p JOIN models m ON p.id = m.pipeline_id JOIN datasets d ON p.dataset_id = d.id JOIN projects pr ON d.project_id = pr.id JOIN users u ON pr.user_id = u.id WHERE u.name = '김민준';

[결과]
experiment_count
----------------
3

[설명] 김민준 님이 수행한 실험(학습 파이프라인) 수는 **3건**입니다.
```

첫 번째 SQL 쿼리에서 스키마 오류가 발생했지만, 에이전트가 자동으로 올바른 쿼리로 수정하여 정확한 답변을 제공했습니다.

- SQL 지식이 없어도 자연어 질문만으로 원하는 정보를 얻을 수 있습니다.

### 사례 2: 오타 및 띄어쓰기 오류에 대한 강건성

```bash
> 김민준이 사생성한 모델에 대해 알려줘  # "사생성" (오타: "생성")

[SQL] SELECT m.id AS model_id, m.name AS model_name, m.version, ...
[결과] 3개의 모델 정보 정확히 반환

> 이서 연이 담당하는 프로젝트는 뭐야?  # "이서 연" (띄어쓰기 오류)

[SQL] SELECT p.id AS project_id, p.name AS project_name, ...
[결과] 이서연 님의 프로젝트 2개 정확히 반환
```

- 오타("사생성" → "생성")가 있어도 의도를 정확히 파악하여 올바른 결과를 반환했습니다.
- 띄어쓰기 오류("이서 연" → "이서연")도 자동으로 보정하여 정확한 사용자를 찾았습니다.
- 사용자가 완벽한 문장을 입력하지 않아도 자연스럽게 대화할 수 있습니다.

### 사례 3: 불필요한 문자 처리 및 상세한 분석

```bash
> 옽 오탐이 적은 모델 추천해줘  # "옽" (불필요한 문자)

[SQL] SELECT m.id AS model_id, m.name AS model_name, m.version, m.stage, ...
       FROM models m JOIN metrics met ON m.id = met.model_id 
       WHERE m.stage = 'production' ORDER BY met.precision_val DESC LIMIT 5;

[결과] 4개 모델의 상세 정보 반환

[설명] ### 오탐(거짓 양성)이 적은 모델 추천
- Precision 기준 상위 모델들을 정렬
- 각 모델의 Precision, Recall, 추론 시간, Confidence Threshold, deploy_note 포함
- 실무 활용 가이드 및 다음 단계 제안까지 제공
```

- 불필요한 문자("옽")가 있어도 질문의 핵심을 정확히 파악했습니다.
- 단순히 모델 목록만 제공하는 것이 아니라, **Precision/Recall 트레이드오프에 대한 설명**, **각 모델의 실무 활용 가이드**, **다음 단계 제안**까지 포함한 매우 상세한 답변을 제공했습니다.
- 실무 의사결정에 바로 활용할 수 있는 수준의 분석입니다.

### 사례 4: 결과 없음 상황의 친절한 처리

```bash
> 송이레의 프로젝트 보여줘

[SQL] SELECT u.name AS user_name, u.email, u.team, u.role, p.id AS project_id, ...
       FROM users u JOIN projects p ON u.id = p.user_id WHERE u.name = '송이레';

[결과] 결과 없음

[SQL] SELECT id, name, email, team, role FROM users WHERE name = '송이레';
[결과] 결과 없음

[SQL] SELECT name FROM users WHERE name LIKE '%송이레%';
[결과] 결과 없음

[설명] 현재 `users` 테이블에 **'송이레'** 라는 이름을 가진 사용자가 존재하지 않아, 
해당 사용자의 프로젝트 정보를 조회할 수 없었습니다.

혹시 다음과 같은 정보를 추가로 알려주시면 정확히 찾아드릴 수 있어요:
- 사용자 ID (숫자 형태)
- 이메일 주소
- 팀명 또는 역할
또는 전체 사용자 목록을 확인하고 싶으신 경우에도 도와드릴게요.
```

- 결과가 없을 때 단순히 "결과 없음"만 표시하지 않고, **여러 방법으로 시도**하고 **대안을 제시**하는 친절한 응답을 제공했습니다.
- 사용자가 다음에 무엇을 할 수 있는지 명확하게 안내하여 대화의 연속성을 유지합니다.

### 사례 5: 복합 질문에 대한 상세 분석

```bash
> A100 GPU를 사용한 파이프라인은 몇 개야?

[SQL] SELECT COUNT(*) AS a100_pipeline_count FROM pipelines WHERE gpu_type = 'A100';
[결과] 3

[SQL] SELECT p.id AS pipeline_id, p.name AS pipeline_name, p.gpu_type, p.status, ...
       FROM pipelines p WHERE p.gpu_type = 'A100' ORDER BY p.finished_at DESC;
[결과] 3개 파이프라인 상세 정보

[설명] **A100 GPU를 사용한 파이프라인은 총 3개**이며, 모두 **완료(completed)** 상태입니다.
- 각 파이프라인과 연결된 모델 정보
- datasets → pipelines → models → metrics 흐름 설명
- 추가로 조회 가능한 정보 제안
```

- 단순한 개수 질문에도 **상세 정보를 자동으로 추가 조회**하여 더 유용한 답변을 제공했습니다.
- 관련된 모델 정보와 워크플로우 설명까지 포함하여 맥락을 이해하기 쉽게 설명했습니다.
- "추가로 조회 가능한 정보"를 제안하여 대화를 자연스럽게 확장할 수 있도록 했습니다.

### 사례 6: 같은 모델의 다른 세팅 비교 (실험 비교)

```bash
> wafer-defect v2.0과 v2.1의 메트릭 비교해줘

[SQL] SELECT met.id AS metric_id, met.map50, met.f1_score, met.precision_val, met.recall,
      met.inference_ms, met.confidence_threshold, met.deploy_note
      FROM metrics met JOIN models m ON met.model_id = m.id
      WHERE m.name = 'wafer-defect-yolov8m' ORDER BY m.version;

[결과]
metric_id | map50 | f1_score | precision_val | recall | inference_ms | confidence_threshold | deploy_note
---------------------------------------------------------------------------------------------------------
1 | 0.901 | 0.863 | 0.952 | 0.789 | 12.3 | 0.5  | high-precision 세팅. 오탐 민감 현장(A라인)용 ...
2 | 0.923 | 0.891 | 0.842 | 0.948 | 12.5 | 0.25 | high-recall 세팅. 미탐 민감 현장(B라인)용 ...

[설명] v2.0(Precision 95.2%, Recall 78.9%)과 v2.1(Precision 84.2%, Recall 94.8%)의
핵심 차이를 표로 정리하고, 오탐 민감 현장 vs 미탐 민감 현장별 선택 가이드를 제공했다.
Confidence Threshold 조정에 따른 트레이드오프까지 설명.
```

같은 모델(YOLOv8m, 25.9M params)에서 Confidence Threshold만 바꾼 두 버전의 차이를 명확히 비교했습니다.

- precision/recall 트레이드오프를 현장별 배포 관점에서 설명하여, 실무 의사결정에 직접 활용 가능한 수준의 분석을 제공합니다.

### 사례 7: 파이프라인 상태 모니터링

```bash
> 현재 실행 중이거나 실패한 파이프라인 있어?

[SQL] SELECT p.id, p.name, p.status, p.started_at, p.finished_at,
      d.name AS dataset_name, pr.name AS project_name, u.name AS user_name
      FROM pipelines p JOIN datasets d ON p.dataset_id = d.id
      JOIN projects pr ON d.project_id = pr.id JOIN users u ON pr.user_id = u.id
      WHERE p.status IN ('running', 'failed') ORDER BY p.started_at DESC;

[결과]
9 | lstm-log-exp01     | failed  | 2024-09-10 10:00:00 | 2024-09-10 10:15:00 | ... | 정하은
8 | yolov8-wafer-exp03 | running | 2024-06-15 08:00:00 | None                | ... | 김민준

(추가로 관련 아티팩트와 모델 등록 여부까지 자동 조회)

[설명] failed 파이프라인의 error.log 경로, running 파이프라인의 중간 체크포인트 정보,
모델 미등록 상태 안내, 그리고 다음 단계(로그 확인, 모니터링 방법)까지 제안.
```

단순 상태 조회에 그치지 않고, 연관 아티팩트와 모델 등록 여부까지 자동으로 추가 조회(3회 Function Calling)했습니다.

- 실패 원인 파악 → 재실행 판단까지의 운영 워크플로우를 안내하여 실무에서 바로 활용할 수 있습니다.

### 사례 8: Production 모델 성능 한눈에 보기

```bash
> production에 배포된 모델 목록과 성능 보여줘

[SQL] SELECT m.id, m.name, m.version, m.architecture, m.parameters_m,
      met.map50, met.f1_score, met.precision_val, met.recall,
      met.inference_ms, met.confidence_threshold, met.deploy_note
      FROM models m JOIN metrics met ON m.id = met.model_id
      WHERE m.stage = 'production' ORDER BY m.registered_at DESC;

[결과]
4 | intent-kobert         | v3.0 | KoBERT   | 110.0 | None  | 0.887 | 0.902 | 0.873 | 15.2 | 0.5  | ...
2 | wafer-defect-yolov8m  | v2.1 | YOLOv8m  | 25.9  | 0.923 | 0.891 | 0.842 | 0.948 | 12.5 | 0.25 | ...
7 | document-paddle-ocr   | v2.0 | PP-OCRv4 | 14.8  | None  | 0.921 | 0.935 | 0.908 | 45.0 | 0.5  | ...
5 | surface-yolov5l       | v3.2 | YOLOv5l  | 46.5  | 0.956 | 0.934 | 0.908 | 0.961 | 11.8 | 0.3  | ...

[설명] 4개 production 모델의 성능 비교 테이블, 모델별 강점/약점 분석,
현장 상황별 선택 가이드(오탐 비용 vs 미탐 손실), Confidence Threshold 조정 팁 제공.
```

production 전체 모델을 한 번에 비교하면서 각 모델의 특성(detection vs classification vs OCR)에 맞는 지표 해석을 제공했습니다.

- mAP가 NULL인 분류/OCR 모델은 F1 기준으로 별도 설명하는 등, 도메인 지식이 잘 반영되어 있습니다.

## 강점

1. **오타 및 띄어쓰기 오류에 강건함**
   - "사생성" → "생성" 자동 보정
   - "이서 연" → "이서연" 자동 보정
   - 불필요한 문자("옽") 무시하고 핵심 질문 파악

2. **SQL 오류 자동 수정**
   - 스키마 오류 발생 시 올바른 쿼리로 자동 재시도
   - 사용자가 SQL을 몰라도 안정적으로 작동합니다.

3. **상세하고 실무적인 답변**
   - 단순 데이터 나열이 아닌 **맥락 설명** 포함
   - Precision/Recall 트레이드오프 등 **도메인 지식** 활용
   - **다음 단계 제안**으로 대화 확장 유도

4. **친절한 에러 처리**
   - 결과 없음 시 대안 제시
   - 사용자가 다음에 할 수 있는 행동을 안내합니다.

5. **자동 상세 정보 추가**
   - 개수 질문에도 상세 정보를 자동으로 조회합니다.
   - 관련 정보까지 함께 제공하여 한 번의 질문으로 많은 정보를 얻을 수 있습니다.

## 개선 가능한 점

- 매우 긴 답변의 경우 가독성을 위해 요약 옵션 제공을 고려할 수 있습니다.
- 복잡한 질문의 경우 단계별로 나누어 설명하는 방식을 고려할 수 있습니다.

## 사용 팁

1. **자연어로 질문**: SQL을 몰라도 자연어로 질문하면 자동으로 SQL로 변환됩니다.
2. **구체적으로 질문**: "모델 보여줘"보다 "production 단계의 모델 보여줘"가 더 정확합니다.
3. **비교 질문 활용**: "비교해줘", "차이는?", "순위는?" 같은 표현을 사용해 보세요.
4. **실무 맥락 포함**: "오탐 민감", "미탐 민감" 같은 실무 용어를 사용하면 더 정확한 답변을 받을 수 있습니다.
5. **오타 걱정 없이 질문**: 오타나 띄어쓰기 오류가 있어도 대부분 정확히 이해합니다.
6. **사용량 추적**: `--usage` 플래그로 비용을 확인하면서 사용합니다.
   ```bash
   python3 mlops_dashboard/main.py --usage
   ```

## 예시 세션

```bash
> 김민준의 프로젝트 목록 보여줘
> defect-detection-v2 프로젝트의 모델 성능 비교해줘
> 오탐이 적은 모델 추천해줘
> 그 모델의 deploy_note 알려줘
> 해당 모델의 체크포인트 경로는?
```

이런 질문들을 통해 MLOps 플랫폼의 데이터를 효율적으로 탐색하고 분석하는 데에 활용할 수 있습니다.
