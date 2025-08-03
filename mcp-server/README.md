# A Simple MCP Weather Server written in Python

See the [Quickstart](https://modelcontextprotocol.io/quickstart) tutorial for more information.

## 로깅 설정

이 프로젝트는 환경변수를 통해 로깅을 설정할 수 있습니다.

### 환경변수 설정

`env.example` 파일을 참고하여 `.env` 파일을 생성하고 다음 설정을 구성하세요:

```bash
# 로깅 설정
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_OUTPUT=both                   # stdout, file, both
LOG_FILE_PATH=logs/mcp-server.log # 로그 파일 경로
LOG_MAX_SIZE=10                   # 로그 파일 최대 크기 (MB)
LOG_BACKUP_COUNT=5                # 백업 파일 개수
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

### 로깅 옵션

- **LOG_LEVEL**: 로그 레벨 설정
  - `DEBUG`: 모든 로그 출력
  - `INFO`: 정보, 경고, 오류 로그 출력
  - `WARNING`: 경고, 오류 로그 출력
  - `ERROR`: 오류 로그만 출력
  - `CRITICAL`: 치명적 오류만 출력

- **LOG_OUTPUT**: 로그 출력 방식
  - `stdout`: 콘솔에만 출력
  - `file`: 파일에만 출력
  - `both`: 콘솔과 파일 모두에 출력

- **LOG_FILE_PATH**: 로그 파일 경로 (기본값: `logs/mcp-server.log`)

- **LOG_MAX_SIZE**: 로그 파일 최대 크기 (MB, 기본값: 10)

- **LOG_BACKUP_COUNT**: 백업 파일 개수 (기본값: 5)

- **LOG_FORMAT**: 로그 포맷 (기본값: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`)

### 사용 예시

```bash
# 개발 환경 (모든 로그를 콘솔에 출력)
LOG_LEVEL=DEBUG LOG_OUTPUT=stdout python server_app.py

# 프로덕션 환경 (INFO 레벨 이상을 파일에 출력)
LOG_LEVEL=INFO LOG_OUTPUT=file python server_app.py

# 디버깅 환경 (모든 로그를 콘솔과 파일에 출력)
LOG_LEVEL=DEBUG LOG_OUTPUT=both python server_app.py
```
