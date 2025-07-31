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
├── mcp-client/            # MCP 클라이언트
│   ├── client.py          # 메인 클라이언트 코드
│   ├── pyproject.toml     # Python 프로젝트 설정
│   ├── README.md          # 클라이언트 문서
│   └── uv.lock            # 의존성 잠금 파일
└── mcp-server/            # MCP 서버
    ├── weather.py         # 날씨 서버 구현
    ├── pyproject.toml     # Python 프로젝트 설정
    ├── README.md          # 서버 문서
    └── uv.lock            # 의존성 잠금 파일
```

## 🚀 주요 기능

### MCP 클라이언트 (`mcp-client/`)

- **Groq LLM 통합**: Llama3-8b-8192 모델을 사용한 자연어 처리
- **대화형 인터페이스**: 사용자 쿼리를 받아 서버의 도구들을 활용
- **자동 도구 호출**: LLM이 적절한 도구를 자동으로 선택하고 실행
- **타입 변환**: 도구 파라미터의 자동 타입 변환 지원
- **환경 변수 관리**: `.env` 파일을 통한 설정 관리

### MCP 서버 (`mcp-server/`)

- **날씨 정보 제공**: 미국 National Weather Service API 활용
- **두 가지 도구 제공**:
  - `get_alerts`: 미국 주별 날씨 경보 조회
  - `get_forecast`: 위도/경도 기반 날씨 예보 조회
- **FastMCP 프레임워크**: 간편한 MCP 서버 구현
- **에러 처리**: 안정적인 API 통신 및 예외 처리

## 🛠️ 설치 및 실행

### 사전 요구사항

- Python 3.10 이상
- Groq API 키 (클라이언트용)
- uv 패키지 설치
    ```bash
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```
- 환경변수(%PATH%)에 uv실행 경로 추가

### 1. 클라이언트 설정

```bash
cd mcp-client
uv venv
.venv\Scripts\activate
uv sync
```

`.env` 파일을 생성하고 Groq API 키를 설정하세요:

```env
GROQ_API_KEY=your_groq_api_key_here
```

### 2. 서버 가상 환경 설정

```bash
cd mcp-server
uv venv
.venv\Scripts\activate
uv sync
```

### 3. 실행

**서버 실행:**
```bash
cd mcp-server
python weather.py
```

**클라이언트 실행:**
```bash
cd mcp-client
uv run client.py ../mcp-server/weather.py
```

## 💡 사용 예시

클라이언트를 실행한 후 다음과 같은 질문을 할 수 있습니다:

- "캘리포니아의 날씨 경보를 알려줘"
- "뉴욕시(40.7128, -74.0060)의 날씨 예보를 보여줘"
- "텍사스에 현재 활성화된 경보가 있나요?"

## 🔧 기술 스택

### 클라이언트
- **mcp**: Model Context Protocol 클라이언트 라이브러리
- **groq**: LLM API 클라이언트
- **python-dotenv**: 환경 변수 관리
- **httpx**: HTTP 클라이언트

### 서버
- **mcp[cli]**: MCP 서버 프레임워크
- **httpx**: 비동기 HTTP 클라이언트
- **FastMCP**: 간편한 MCP 서버 구현

## 📚 학습 목표

이 프로젝트를 통해 다음을 학습할 수 있습니다:

1. **MCP 프로토콜 이해**: 클라이언트-서버 간 통신 방식
2. **도구 호출 메커니즘**: LLM이 도구를 어떻게 선택하고 실행하는지
3. **타입 시스템**: MCP의 스키마 기반 타입 변환
4. **실제 구현**: 실제 API를 활용한 MCP 서버 개발
5. **에러 처리**: 안정적인 MCP 시스템 구축

## 🤝 기여하기

이 프로젝트는 학습 목적으로 만들어졌습니다. 개선 사항이나 버그 리포트는 언제든 환영합니다.

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🔗 참고 자료

- [Model Context Protocol 공식 문서](https://modelcontextprotocol.io/)
- [MCP 클라이언트 튜토리얼](https://modelcontextprotocol.io/tutorials/building-a-client)
- [MCP 퀵스타트 가이드](https://modelcontextprotocol.io/quickstart)
- [Groq API 문서](https://console.groq.com/docs)
- [National Weather Service API](https://www.weather.gov/documentation/services-web-api)