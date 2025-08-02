# MCP Weather System

Model Context Protocol (MCP)을 활용한 날씨 정보 시스템입니다. HTTP 서버와 MCP 브리지를 통해 Cursor에서 자연어로 날씨 정보를 조회할 수 있습니다.

## 📋 프로젝트 개요

이 프로젝트는 다음과 같은 구성 요소로 이루어져 있습니다:

- **HTTP 서버**: 날씨 API와 LLM을 통합한 백엔드 서버
- **MCP 브리지**: Cursor와 HTTP 서버 사이의 중계 서버
- **HTTP 클라이언트**: 웹 기반 날씨 정보 조회 클라이언트
- **통합 시스템**: 모든 구성 요소 간의 원활한 통신

## 🏗️ 프로젝트 구조

```
mcp-study/
├── LICENSE                 # MIT 라이선스
├── README.md              # 프로젝트 메인 문서
├── mcp-client/            # HTTP 클라이언트
│   ├── client_app.py      # 메인 클라이언트 코드 (HTTP)
│   ├── client_ollama.py   # Ollama 기반 클라이언트 (참고용)
│   ├── client.py          # 기본 클라이언트 (참고용)
│   ├── pyproject.toml     # Python 프로젝트 설정
│   ├── README.md          # 클라이언트 문서
│   └── uv.lock            # 의존성 잠금 파일
└── mcp-server/            # 서버 (HTTP + MCP 브리지)
    ├── server_app.py      # HTTP 서버 구현 (FastAPI)
    ├── mcp_bridge.py      # MCP 브리지 서버 (Cursor용)
    ├── simple_test.py     # 간단한 MCP 테스트 서버
    ├── weather_mcp.py     # 기존 MCP 서버 (참고용)
    ├── weather_mcp_simple.py # 간단한 날씨 MCP 서버
    ├── weather.py         # 기본 날씨 서버 (참고용)
    ├── pyproject.toml     # Python 프로젝트 설정
    ├── README.md          # 서버 문서
    └── uv.lock            # 의존성 잠금 파일
```

## 🚀 주요 기능

### HTTP 서버 (`mcp-server/server_app.py`)

- **FastAPI 기반**: 현대적인 HTTP API 서버
- **스트리밍 응답**: Server-Sent Events (SSE) 방식의 실시간 처리
- **LLM 통합**: Groq 또는 Ollama를 통한 자연어 처리
- **날씨 정보 제공**: 미국 National Weather Service API 활용
- **한국어 번역**: 날씨 정보를 한국어로 번역 및 단위 변환
- **엔드포인트 제공**:
  - `POST /api/query`: 자연어 쿼리 처리 (스트리밍)
  - `POST /api/get_forecast`: 위도/경도 기반 날씨 예보 조회
  - `POST /api/get_alerts`: 미국 주별 날씨 경보 조회
  - `GET /api/tools`: 사용 가능한 도구 목록
  - `GET /health`: 서버 상태 확인

### MCP 브리지 서버 (`mcp-server/mcp_bridge.py`)

- **Cursor 호환**: Cursor에서 MCP Server로 등록 가능
- **URL 파라미터 지원**: 명령행에서 HTTP 서버 URL 지정 가능
- **MCP 프로토콜**: stdio 기반 통신
- **도구 제공**:
  - `get_forecast`: 특정 위치의 날씨 예보
  - `get_alerts`: 특정 주의 날씨 경보
  - `process_weather_query`: 자연어 날씨 쿼리 처리
- **HTTP 서버 연동**: HTTP 서버를 통해 실제 날씨 데이터 처리

### HTTP 클라이언트 (`mcp-client/`)

- **스트리밍 응답**: 서버의 실시간 처리 상태 확인
- **HTTP 통신**: RESTful API를 통한 서버와의 통신
- **대화형 인터페이스**: 사용자 쿼리를 받아 서버의 도구들을 활용

## 🛠️ 설치 및 실행

### 사전 요구사항

- Python 3.10 이상
- Groq API 키 (선택사항)
- uv 패키지 설치
    ```bash
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

### 1. 서버 설정

```bash
cd mcp-server
uv sync
```

### 2. 클라이언트 설정

```bash
cd mcp-client
uv sync
```

### 3. 환경 변수 설정

`.env` 파일을 생성하고 필요한 API 키를 설정:

```env
# Groq 설정 (선택사항)
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama3-8b-8192

# Ollama 설정 (기본값)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3:8b

# LLM Provider 선택 (groq 또는 ollama)
LLM_PROVIDER=ollama
```

### 4. 실행

#### 방법 1: HTTP 클라이언트-서버 (스트리밍)

**서버 실행:**
```bash
cd mcp-server
uv run python server_app.py
```

**클라이언트 실행:**
```bash
cd mcp-client
uv run python client_app.py
```

#### 방법 2: Cursor MCP 브리지 서버 등록

**MCP 브리지 서버 실행:**
```bash
cd mcp-server
uv run python mcp_bridge.py --url http://localhost:8000
```

**Cursor에서 MCP Server 등록:**
1. Cursor 설정에서 `MCP Servers` 섹션으로 이동
2. 새 서버 추가:
   - **Name**: `weather-mcp-bridge`
   - **Command**: `uv run python mcp_bridge.py --url http://localhost:8000`
   - **Working Directory**: `mcp-server` 폴더 경로
  ```mcp.json
    "mcpServers": {
        "Weather MCP": {
          "command": "uv",
          "args": [
            "--directory",
            "D:\\workspaces\\mcp-work\\mcp-study\\mcp-server",
            "run",
            "mcp_bridge.py",
            "--url",
            "http://localhost:8000" 
          ]
        }
    }
  ```

## 💡 사용 예시

### HTTP 클라이언트 사용
```
Query: LA 날씨 정보를 알려줘
[상태] 쿼리를 처리하고 있습니다... (LLM: ollama)
[상태] 날씨 정보를 가져오고 있습니다...
[상태] OLLAMA 모델을 호출하고 있습니다...
[결과] 로스앤젤레스의 현재 날씨 정보입니다...
```

### Cursor Chat 사용
```
사용자: LA 날씨 정보를 알려줘
Cursor: get_forecast 도구를 사용하여 LA의 날씨 정보를 가져오겠습니다...
```

### 지원하는 질문 예시
- "캘리포니아의 날씨 경보를 알려줘"
- "뉴욕시의 날씨 예보를 보여줘"
- "텍사스에 현재 활성화된 경보가 있나요?"
- "LA 날씨 정보를 한국어로 알려줘"
- "뉴욕의 날씨 주의보는?"

## 🔧 기술 스택

### HTTP 서버
- **fastapi**: 현대적인 웹 API 프레임워크
- **uvicorn**: ASGI 서버
- **pydantic**: 데이터 검증 및 직렬화
- **httpx**: 비동기 HTTP 클라이언트
- **groq**: Groq LLM API 클라이언트
- **python-dotenv**: 환경 변수 관리

### MCP 브리지 서버
- **mcp**: Model Context Protocol 구현
- **httpx**: 비동기 HTTP 클라이언트
- **argparse**: 명령행 인수 처리

### HTTP 클라이언트
- **httpx**: 비동기 HTTP 클라이언트
- **python-dotenv**: 환경 변수 관리

## 🌟 주요 특징

### 1. 유연한 LLM Provider 지원
- **Groq**: 빠른 응답 속도, 유료 서비스
- **Ollama**: 로컬 실행, 무료, 오프라인 가능

### 2. 실시간 스트리밍 응답
- Server-Sent Events (SSE)를 통한 실시간 처리 상태 표시
- 사용자가 처리 진행 상황을 실시간으로 확인 가능

### 3. 한국어 번역 및 단위 변환
- 화씨 → 섭씨 변환
- 마일 → 킬로미터 변환
- 자연스러운 한국어 번역

### 4. URL 파라미터 지원
- MCP 브리지 서버에서 다양한 HTTP 서버 URL 지원
- 개발/운영 환경별 유연한 설정 가능

### 5. Cursor 완벽 통합
- MCP 프로토콜을 통한 Cursor와의 원활한 통신
- 자연어로 날씨 정보 조회 가능

## 📚 학습 목표

이 프로젝트를 통해 다음을 학습할 수 있습니다:

1. **HTTP API 설계**: RESTful API 설계 및 구현
2. **FastAPI 활용**: 현대적인 Python 웹 프레임워크 사용
3. **비동기 프로그래밍**: async/await를 활용한 비동기 처리
4. **LLM 통합**: Groq/Ollama를 활용한 자연어 처리
5. **API 통신**: HTTP를 통한 클라이언트-서버 통신
6. **MCP 프로토콜**: Model Context Protocol 이해 및 구현
7. **스트리밍 응답**: Server-Sent Events (SSE) 구현
8. **Cursor 통합**: MCP 서버를 Cursor에 등록하여 사용
9. **브리지 패턴**: 서로 다른 프로토콜 간의 중계 서버 구현

## 🔍 문제 해결

### MCP 도구가 등록되지 않는 경우
- `@mcp.list_tools()` 데코레이터 제거 확인
- FastMCP는 자동으로 `@mcp.tool()` 데코레이터를 감지

### HTTP 서버 연결 오류
- 서버가 포트 8000에서 실행 중인지 확인
- `uv run python server_app.py` 명령으로 서버 시작

### LLM 응답 오류
- 환경 변수 설정 확인 (GROQ_API_KEY, OLLAMA_URL 등)
- LLM_PROVIDER 설정 확인

## 🤝 기여하기

이 프로젝트는 학습 목적으로 만들어졌습니다. 개선 사항이나 버그 리포트는 언제든 환영합니다.

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🔗 참고 자료

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [Uvicorn 서버](https://www.uvicorn.org/)
- [Pydantic 데이터 검증](https://docs.pydantic.dev/)
- [Groq API](https://console.groq.com/)
- [Ollama 문서](https://ollama.ai/docs)
- [National Weather Service API](https://www.weather.gov/documentation/services-web-api)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Cursor MCP 설정](https://cursor.sh/docs/mcp)