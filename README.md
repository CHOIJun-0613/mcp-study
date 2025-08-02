# MCP Study Project

Model Context Protocol (MCP)을 학습하기 위한 클라이언트-서버 프로젝트입니다. 이 프로젝트는 MCP의 핵심 개념을 이해하고 실제 구현을 통해 학습할 수 있도록 구성되어 있습니다.

## 📋 프로젝트 개요

이 프로젝트는 다음과 같은 구성 요소로 이루어져 있습니다:

- **MCP Client**: Groq LLM을 활용한 대화형 클라이언트
- **MCP Server**: 날씨 정보를 제공하는 서버
- **통합 시스템**: 클라이언트와 서버 간의 MCP 프로토콜 통신

## 🏗️ 프로젝트 구조

```
mcp-study/
├── LICENSE                 # MIT 라이선스
├── README.md              # 프로젝트 메인 문서
├── mcp-client/            # HTTP 클라이언트
│   ├── client_app.py      # 메인 클라이언트 코드 (HTTP)
│   ├── client_ollama.py   # 기존 MCP 클라이언트 (참고용)
│   ├── pyproject.toml     # Python 프로젝트 설정
│   ├── README.md          # 클라이언트 문서
│   └── uv.lock            # 의존성 잠금 파일
└── mcp-server/            # 서버 (HTTP + MCP)
    ├── server_app.py      # HTTP 서버 구현 (FastAPI)
    ├── weather_mcp.py     # MCP 서버 구현 (Cursor용)
    ├── weather.py         # 기존 MCP 서버 (참고용)
    ├── pyproject.toml     # Python 프로젝트 설정
    ├── README.md          # 서버 문서
    └── uv.lock            # 의존성 잠금 파일
```

## 🚀 주요 기능

### HTTP 클라이언트 (`mcp-client/`)

- **스트리밍 응답**: 서버의 실시간 처리 상태 확인
- **HTTP 통신**: RESTful API를 통한 서버와의 통신
- **대화형 인터페이스**: 사용자 쿼리를 받아 서버의 도구들을 활용
- **상태 표시**: 처리 진행 상황을 실시간으로 확인

### HTTP 서버 (`mcp-server/server_app.py`)

- **FastAPI 기반**: 현대적인 HTTP API 서버
- **스트리밍 응답**: Server-Sent Events (SSE) 방식
- **통합 처리**: 모든 LLM 호출과 도구 실행을 서버에서 처리
- **날씨 정보 제공**: 미국 National Weather Service API 활용
- **엔드포인트 제공**:
  - `POST /api/query`: 자연어 쿼리 처리 (스트리밍)
  - `POST /api/get_forecast`: 위도/경도 기반 날씨 예보 조회
  - `POST /api/get_alerts`: 미국 주별 날씨 경보 조회
- **RESTful API**: 표준 HTTP 메서드와 JSON 응답
- **CORS 지원**: 웹 클라이언트에서의 접근 허용

### MCP 서버 (`mcp-server/weather_mcp.py`)

- **Cursor 호환**: Cursor에서 MCP Server로 등록 가능
- **MCP 프로토콜**: stdio 기반 통신
- **도구 제공**:
  - `get_forecast`: 특정 위치의 날씨 예보
  - `get_alerts`: 특정 주의 날씨 경보
  - `process_weather_query`: 자연어 날씨 쿼리 처리
- **Ollama 통합**: Llama3-8b 모델을 사용한 자연어 처리
- **한국어 번역**: 날씨 정보를 한국어로 번역 및 단위 변환

## 🛠️ 설치 및 실행

### 사전 요구사항

- Python 3.10 이상
- Groq API 키 (클라이언트용)
- uv 패키지 설치
    ```bash
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```
- 환경변수(%PATH%)에 uv실행 경로 추가

### 1. 서버 설정

```bash
cd mcp-server
uv venv
.venv\Scripts\activate
uv sync
```

### 2. 클라이언트 설정

```bash
cd mcp-client
uv venv
.venv\Scripts\activate
uv sync
```

### 3. 실행

#### 방법 1: HTTP 클라이언트-서버 (스트리밍)

**서버 실행:**
```bash
cd mcp-server
uv run server_app.py
```

**클라이언트 실행:**
```bash
cd mcp-client
uv run client_app.py
```

#### 방법 2: Cursor MCP Server 등록

**MCP 서버 실행:**
```bash
cd mcp-server
uv run weather_mcp.py
```

**Cursor에서 MCP Server 등록:**
1. Cursor 설정에서 `MCP Servers` 섹션으로 이동
2. 새 서버 추가:
   - **Name**: `weather-mcp`
   - **Command**: `uv run weather_mcp.py`
   - **Working Directory**: `mcp-server` 폴더 경로

## 💡 사용 예시

### HTTP 클라이언트 사용
```
Query: LA 날씨 정보를 알려줘
[상태] 쿼리를 처리하고 있습니다...
[상태] AI 모델을 호출하고 있습니다...
[상태] 날씨 정보를 가져오고 있습니다...
[상태] 한국어로 번역하고 있습니다...
[결과] 로스앤젤레스의 현재 날씨 정보입니다...
```

### Cursor Chat 사용
```
사용자: LA 날씨 정보를 알려줘
Cursor: process_weather_query 도구를 사용하여 LA의 날씨 정보를 가져오겠습니다...
```

### 지원하는 질문 예시
- "캘리포니아의 날씨 경보를 알려줘"
- "뉴욕시의 날씨 예보를 보여줘"
- "텍사스에 현재 활성화된 경보가 있나요?"
- "LA 날씨 정보를 한국어로 알려줘"

## 🔧 기술 스택

### HTTP 클라이언트
- **httpx**: 비동기 HTTP 클라이언트
- **python-dotenv**: 환경 변수 관리

### HTTP 서버
- **fastapi**: 현대적인 웹 API 프레임워크
- **uvicorn**: ASGI 서버
- **pydantic**: 데이터 검증 및 직렬화
- **httpx**: 비동기 HTTP 클라이언트
- **python-dotenv**: 환경 변수 관리

### MCP 서버
- **mcp**: Model Context Protocol 구현
- **httpx**: 비동기 HTTP 클라이언트
- **asyncio**: 비동기 프로그래밍

## 📚 학습 목표

이 프로젝트를 통해 다음을 학습할 수 있습니다:

1. **HTTP API 설계**: RESTful API 설계 및 구현
2. **FastAPI 활용**: 현대적인 Python 웹 프레임워크 사용
3. **비동기 프로그래밍**: async/await를 활용한 비동기 처리
4. **LLM 통합**: Ollama를 활용한 자연어 처리
5. **API 통신**: HTTP를 통한 클라이언트-서버 통신
6. **MCP 프로토콜**: Model Context Protocol 이해 및 구현
7. **스트리밍 응답**: Server-Sent Events (SSE) 구현
8. **Cursor 통합**: MCP 서버를 Cursor에 등록하여 사용

## 🤝 기여하기

이 프로젝트는 학습 목적으로 만들어졌습니다. 개선 사항이나 버그 리포트는 언제든 환영합니다.

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🔗 참고 자료

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [Uvicorn 서버](https://www.uvicorn.org/)
- [Pydantic 데이터 검증](https://docs.pydantic.dev/)
- [Ollama 문서](https://ollama.ai/docs)
- [National Weather Service API](https://www.weather.gov/documentation/services-web-api)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Cursor MCP 설정](https://cursor.sh/docs/mcp)