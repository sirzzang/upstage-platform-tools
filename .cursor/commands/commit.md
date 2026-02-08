# Commit Command

스테이지된 변경사항을 분석하여 커밋 메시지를 자동 생성하고 커밋을 실행합니다.

## 사용법
- `/commit` 또는 `/commit 영어` - 영어로 커밋 메시지 생성 (기본값)
- `/commit 한국어` - 한국어로 커밋 메시지 생성

## 작업 순서

1. **스테이지된 파일 확인**
   - `git diff --cached --name-status` 명령어로 스테이지된 파일 목록을 가져옵니다.

2. **파일 분석 및 그룹화**
   - 각 파일을 분석하여 커밋 타입과 스코프를 결정합니다:
     - **커밋 타입 결정 규칙:**
       - `.md`, `.txt`, `README` 파일 → `docs`
       - `.example`, `.env` 파일 → `chore`
       - 새로 추가된 파일 (`A`) → `feat`
       - 수정된 파일 (`M`) → `refactor`
       - 삭제된 파일 (`D`) → `chore`
     - **스코프 결정 규칙:**
       - 파일 경로의 첫 번째 디렉토리를 스코프로 사용 (예: `common/client.py` → `common`)
       - 루트 디렉토리의 파일이거나 `.`으로 시작하는 특수 파일은 스코프 없음

3. **커밋 메시지 생성**
   - 파일들을 타입과 스코프별로 그룹화합니다.
   - 각 그룹에 대해 다음과 같은 형식으로 커밋 메시지를 생성합니다:
     ```
     feat(common), docs: A new feature, Documentation only changes
     
     - client.py 추가/수정
     - usage.py 추가/수정
     - README.md 추가/수정
     ```
   - 주 커밋 메시지는 타입별로 정렬: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `build`, `chore`, `style`
   - 같은 타입 내에서는 스코프별로 정렬합니다.
   - 커밋 메시지 내에 이모지는 사용하지 않습니다.

4. **커밋 타입 설명 (언어별)**

   **영어:**
   - `feat`: A new feature
   - `fix`: A bug fix
   - `refactor`: Code refactoring
   - `chore`: Changes to build process or auxiliary tools
   - `docs`: Documentation only changes
   - `build`: Changes that affect the build system or external dependencies
   - `style`: Code style changes (formatting, missing semicolons, etc.)
   - `test`: Adding or updating tests
   - `perf`: Performance improvements

   **한국어:**
   - `feat`: 새로운 기능 추가
   - `fix`: 버그 수정
   - `refactor`: 코드 리팩토링
   - `chore`: 빌드 업무 수정, 패키지 매니저 설정 등
   - `docs`: 문서 수정
   - `build`: 빌드 시스템 또는 외부 의존성에 영향을 주는 변경사항
   - `style`: 코드 포맷팅, 세미콜론 누락 등
   - `test`: 테스트 코드 추가 또는 수정
   - `perf`: 성능 개선

5. **커밋 실행**
   - 생성된 커밋 메시지를 사용자에게 보여줍니다.
   - 사용자 확인 후 `git commit` 명령어를 실행합니다.
   - 커밋 메시지는 `-F` 옵션을 사용하여 파일로 전달합니다.

## 예시

스테이지된 파일:
- `A common/client.py`
- `A common/usage.py`
- `A .env.example`

생성되는 커밋 메시지 (영어):
```
feat(common), chore: A new feature, Changes to build process or auxiliary tools

- client.py 추가/수정
- usage.py 추가/수정
- .env.example 추가/수정
```

생성되는 커밋 메시지 (한국어):
```
feat(common), chore: 새로운 기능 추가, 빌드 업무 수정, 패키지 매니저 설정 등

- client.py 추가/수정
- usage.py 추가/수정
- .env.example 추가/수정
```
