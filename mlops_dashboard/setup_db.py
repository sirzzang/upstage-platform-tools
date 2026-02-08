import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "sample.db")


def create_sample_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ── 테이블 생성 ──────────────────────────────────────

    cur.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            team TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE projects (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            task_type TEXT NOT NULL,
            created_at DATE NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE datasets (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            format TEXT NOT NULL,
            num_samples INTEGER NOT NULL,
            size_mb REAL NOT NULL,
            created_at DATE NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)

    cur.execute("""
        CREATE TABLE pipelines (
            id INTEGER PRIMARY KEY,
            dataset_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            framework TEXT NOT NULL,
            gpu_type TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            started_at DATETIME,
            finished_at DATETIME,
            FOREIGN KEY (dataset_id) REFERENCES datasets(id)
        )
    """)

    cur.execute("""
        CREATE TABLE artifacts (
            id INTEGER PRIMARY KEY,
            pipeline_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            file_path TEXT NOT NULL,
            size_mb REAL NOT NULL,
            created_at DATETIME NOT NULL,
            FOREIGN KEY (pipeline_id) REFERENCES pipelines(id)
        )
    """)

    cur.execute("""
        CREATE TABLE models (
            id INTEGER PRIMARY KEY,
            pipeline_id INTEGER NOT NULL UNIQUE,
            name TEXT NOT NULL,
            version TEXT NOT NULL,
            architecture TEXT NOT NULL,
            parameters_m REAL NOT NULL,
            registered_at DATE NOT NULL,
            stage TEXT NOT NULL DEFAULT 'development',
            FOREIGN KEY (pipeline_id) REFERENCES pipelines(id)
        )
    """)

    cur.execute("""
        CREATE TABLE metrics (
            id INTEGER PRIMARY KEY,
            model_id INTEGER NOT NULL UNIQUE,
            map50 REAL,
            f1_score REAL,
            precision_val REAL,
            recall REAL,
            inference_ms REAL,
            confidence_threshold REAL,
            deploy_note TEXT,
            evaluated_at DATE NOT NULL,
            FOREIGN KEY (model_id) REFERENCES models(id)
        )
    """)

    # ── 데이터 삽입 ──────────────────────────────────────

    users = [
        (1, "김민준", "minjun@company.com", "ML Platform", "MLOps Engineer"),
        (2, "이서연", "seoyeon@company.com", "Vision AI", "ML Engineer"),
        (3, "박지호", "jiho@company.com", "NLP", "ML Engineer"),
        (4, "정하은", "haeun@company.com", "ML Platform", "MLOps Engineer"),
        (5, "최윤서", "yoonseo@company.com", "Vision AI", "Data Scientist"),
    ]
    cur.executemany("INSERT INTO users VALUES (?,?,?,?,?)", users)

    projects = [
        (1, 1, "defect-detection-v2", "반도체 웨이퍼 결함 탐지 모델 v2", "object_detection", "2024-06-01", "active"),
        (2, 2, "product-classification", "상품 이미지 분류 모델", "image_classification", "2024-05-15", "active"),
        (3, 3, "intent-classifier", "고객 문의 의도 분류", "text_classification", "2024-07-10", "active"),
        (4, 1, "surface-inspection", "외관 검사 자동화", "object_detection", "2024-03-20", "completed"),
        (5, 5, "anomaly-detection", "생산 라인 이상 탐지", "anomaly_detection", "2024-08-01", "active"),
        (6, 2, "ocr-pipeline", "문서 OCR 파이프라인", "ocr", "2024-04-12", "completed"),
        (7, 4, "log-anomaly", "서버 로그 이상 탐지 파이프라인", "anomaly_detection", "2024-09-01", "active"),
    ]
    cur.executemany("INSERT INTO projects VALUES (?,?,?,?,?,?,?)", projects)

    datasets = [
        (1, 1, "wafer-defect-train-v2", "COCO", 12500, 8400.0, "2024-06-05"),
        (2, 1, "wafer-defect-val-v2", "COCO", 2500, 1700.0, "2024-06-05"),
        (3, 2, "product-images-train", "ImageFolder", 45000, 15200.0, "2024-05-20"),
        (4, 2, "product-images-val", "ImageFolder", 5000, 1700.0, "2024-05-20"),
        (5, 3, "intent-corpus-v3", "CSV", 32000, 48.5, "2024-07-12"),
        (6, 4, "surface-defect-train", "COCO", 8000, 5600.0, "2024-03-25"),
        (7, 4, "surface-defect-val", "COCO", 1500, 1100.0, "2024-03-25"),
        (8, 5, "production-sensor-data", "Parquet", 500000, 320.0, "2024-08-05"),
        (9, 6, "document-ocr-train", "COCO", 20000, 9800.0, "2024-04-15"),
        (10, 7, "server-logs-aug", "JSON", 1200000, 780.0, "2024-09-05"),
    ]
    cur.executemany("INSERT INTO datasets VALUES (?,?,?,?,?,?,?)", datasets)

    pipelines = [
        (1, 1, "yolov8-wafer-exp01", "ultralytics", "A100", "completed", "2024-06-10 09:00:00", "2024-06-10 18:30:00"),
        (2, 1, "yolov8-wafer-exp02", "ultralytics", "A100", "completed", "2024-06-12 10:00:00", "2024-06-12 22:15:00"),
        (3, 3, "resnet50-product-exp01", "PyTorch", "V100", "completed", "2024-05-25 08:00:00", "2024-05-25 14:00:00"),
        (4, 5, "kobert-intent-exp01", "HuggingFace", "V100", "completed", "2024-07-15 10:00:00", "2024-07-15 12:30:00"),
        (5, 6, "yolov5-surface-exp03", "ultralytics", "A100", "completed", "2024-04-01 09:00:00", "2024-04-01 16:00:00"),
        (6, 8, "isolation-forest-exp01", "scikit-learn", None, "completed", "2024-08-10 11:00:00", "2024-08-10 11:45:00"),
        (7, 9, "paddle-ocr-exp02", "PaddleOCR", "V100", "completed", "2024-04-20 09:00:00", "2024-04-20 20:00:00"),
        (8, 1, "yolov8-wafer-exp03", "ultralytics", "H100", "running", "2024-06-15 08:00:00", None),
        (9, 10, "lstm-log-exp01", "PyTorch", "V100", "failed", "2024-09-10 10:00:00", "2024-09-10 10:15:00"),
    ]
    cur.executemany("INSERT INTO pipelines VALUES (?,?,?,?,?,?,?,?)", pipelines)

    artifacts = [
        # pipeline 1 artifacts
        (1, 1, "checkpoint", "/artifacts/wafer-exp01/best.pt", 85.2, "2024-06-10 18:30:00"),
        (2, 1, "log", "/artifacts/wafer-exp01/train.log", 2.1, "2024-06-10 18:30:00"),
        (3, 1, "config", "/artifacts/wafer-exp01/config.yaml", 0.01, "2024-06-10 09:00:00"),
        # pipeline 2 artifacts
        (4, 2, "checkpoint", "/artifacts/wafer-exp02/best.pt", 85.2, "2024-06-12 22:15:00"),
        (5, 2, "checkpoint", "/artifacts/wafer-exp02/epoch50.pt", 85.2, "2024-06-12 16:00:00"),
        (6, 2, "log", "/artifacts/wafer-exp02/train.log", 3.4, "2024-06-12 22:15:00"),
        # pipeline 3 artifacts
        (7, 3, "checkpoint", "/artifacts/product-exp01/best.pth", 102.5, "2024-05-25 14:00:00"),
        (8, 3, "log", "/artifacts/product-exp01/train.log", 1.8, "2024-05-25 14:00:00"),
        # pipeline 4 artifacts
        (9, 4, "checkpoint", "/artifacts/intent-exp01/model.bin", 420.0, "2024-07-15 12:30:00"),
        (10, 4, "log", "/artifacts/intent-exp01/train.log", 0.8, "2024-07-15 12:30:00"),
        # pipeline 5 artifacts
        (11, 5, "checkpoint", "/artifacts/surface-exp03/best.pt", 85.2, "2024-04-01 16:00:00"),
        (12, 5, "log", "/artifacts/surface-exp03/train.log", 1.5, "2024-04-01 16:00:00"),
        # pipeline 6 artifacts
        (13, 6, "checkpoint", "/artifacts/iforest-exp01/model.pkl", 12.3, "2024-08-10 11:45:00"),
        # pipeline 7 artifacts
        (14, 7, "checkpoint", "/artifacts/ocr-exp02/best_model.tar", 210.0, "2024-04-20 20:00:00"),
        (15, 7, "log", "/artifacts/ocr-exp02/train.log", 2.8, "2024-04-20 20:00:00"),
        # pipeline 8 (running) - 중간 체크포인트
        (16, 8, "checkpoint", "/artifacts/wafer-exp03/epoch30.pt", 85.2, "2024-06-15 14:00:00"),
        (17, 8, "log", "/artifacts/wafer-exp03/train.log", 1.2, "2024-06-15 14:00:00"),
        # pipeline 9 (failed)
        (18, 9, "log", "/artifacts/log-exp01/error.log", 0.3, "2024-09-10 10:15:00"),
    ]
    cur.executemany("INSERT INTO artifacts VALUES (?,?,?,?,?,?)", artifacts)

    models = [
        # wafer-defect 프로젝트: exp01(high-precision), exp02(high-recall) 두 모델 비교
        (1, 1, "wafer-defect-yolov8m", "v2.0", "YOLOv8m", 25.9, "2024-06-11", "archived"),
        (2, 2, "wafer-defect-yolov8m", "v2.1", "YOLOv8m", 25.9, "2024-06-13", "production"),
        # product-classification
        (3, 3, "product-resnet50", "v1.0", "ResNet-50", 25.6, "2024-05-26", "staging"),
        # intent-classifier
        (4, 4, "intent-kobert", "v3.0", "KoBERT", 110.0, "2024-07-16", "production"),
        # surface-inspection: production 배포 중
        (5, 5, "surface-yolov5l", "v3.2", "YOLOv5l", 46.5, "2024-04-02", "production"),
        # anomaly-detection
        (6, 6, "anomaly-iforest", "v1.0", "IsolationForest", 0.5, "2024-08-11", "staging"),
        # ocr-pipeline
        (7, 7, "document-paddle-ocr", "v2.0", "PP-OCRv4", 14.8, "2024-04-21", "production"),
    ]
    cur.executemany("INSERT INTO models VALUES (?,?,?,?,?,?,?,?)", models)

    # metrics 설명:
    #   precision_val 높음 = 오탐(FP) 적음 → 오탐 민감 현장에 적합
    #   recall 높음 = 미탐(FN) 적음 → 미탐 민감 현장에 적합
    #   confidence_threshold: 모델 추론 시 사용한 confidence 기준값
    #   deploy_note: 현장 배포 의사결정 메모
    metrics = [
        # wafer exp01 (v2.0): conf=0.5, precision 높고 recall 낮음 → 오탐 적음
        (1, 1, 0.901, 0.863, 0.952, 0.789, 12.3, 0.50,
         "high-precision 세팅. 오탐 민감 현장(A라인)용. FP 적지만 작은 결함 놓칠 수 있음",
         "2024-06-11"),
        # wafer exp02 (v2.1): conf=0.25, recall 높고 precision 낮음 → 미탐 적음
        (2, 2, 0.923, 0.891, 0.842, 0.948, 12.5, 0.25,
         "high-recall 세팅. 미탐 민감 현장(B라인)용. 결함 놓치지 않지만 오탐 다소 발생",
         "2024-06-13"),
        # product-classification: 분류 모델이라 mAP 없음
        (3, 3, None, 0.945, 0.952, 0.938, 8.3, 0.50,
         "상품 분류 정확도 우수. staging에서 A/B 테스트 중",
         "2024-05-26"),
        # intent-classifier: NLP 분류
        (4, 4, None, 0.887, 0.902, 0.873, 15.2, 0.50,
         "의도 분류 F1 기준 충분. 오분류 시 상담원 연결로 fallback",
         "2024-07-16"),
        # surface-inspection: 외관 검사 - recall 우선 (미탐 시 불량 유출)
        (5, 5, 0.956, 0.934, 0.908, 0.961, 11.8, 0.30,
         "recall 우선. 불량 유출 방지가 최우선. 오탐은 작업자가 재검",
         "2024-04-02"),
        # anomaly-detection: 이상 탐지
        (6, 6, None, 0.812, 0.798, 0.827, 0.5, 0.50,
         "precision/recall 밸런스. 알림 피로도 vs 이상 누락 트레이드오프",
         "2024-08-11"),
        # OCR
        (7, 7, None, 0.921, 0.935, 0.908, 45.0, 0.50,
         "문자 인식률 우수. 후처리 규칙으로 오탐 보정 중",
         "2024-04-21"),
    ]
    cur.executemany(
        "INSERT INTO metrics VALUES (?,?,?,?,?,?,?,?,?,?)", metrics
    )

    conn.commit()
    conn.close()
    print(f"MLOps DB 생성 완료: {DB_PATH}")
    print("  - users: 5명 (MLOps/ML Engineer)")
    print("  - projects: 7개 (detection, classification, anomaly 등)")
    print("  - datasets: 10개")
    print("  - pipelines: 9개 (completed/running/failed)")
    print("  - artifacts: 18개 (checkpoint, log, config)")
    print("  - models: 7개 (같은 프로젝트 내 실험 비교 포함)")
    print("  - metrics: 7개 (mAP50, F1, precision, recall, inference_ms, confidence_threshold, deploy_note)")


if __name__ == "__main__":
    create_sample_db()
