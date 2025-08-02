import sys
import os
from typing import Any, AsyncGenerator
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn
from pydantic import BaseModel
import json
import httpx
from dotenv import load_dotenv
import groq

# .env 파일 로드
load_dotenv()

# LLM Provider 설정
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()

# GROQ 설정
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "your_groq_api_key_here")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-8b-8192")

# Ollama 설정
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b")

# Weather API 설정
NWS_API_BASE = os.getenv("NWS_API_BASE", "https://api.weather.gov")

# GROQ 클라이언트 초기화
groq_client = None
if LLM_PROVIDER == "groq" and GROQ_API_KEY != "your_groq_api_key_here":
    groq_client = groq.Groq(api_key=GROQ_API_KEY)

# Set encoding for proper character handling
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Initialize FastAPI server
app = FastAPI(
    title="Weather API Server",
    description="A weather API server with LLM integration",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
# NWS_API_BASE = "https://api.weather.gov"
# USER_AGENT = "weather-app/1.0"
# OLLAMA_URL = "http://localhost:11434"
# OLLAMA_MODEL = "llama3:8b"

# Pydantic models for request/response
class QueryRequest(BaseModel):
    query: str

class ForecastRequest(BaseModel):
    latitude: float
    longitude: float

class AlertsRequest(BaseModel):
    state: str

class WeatherResponse(BaseModel):
    success: bool
    data: str
    error: str = None

async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the National Weather Service API"""
    print(f"[DEBUG] NWS API 호출: {url}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers={"User-Agent": "WeatherApp/1.0"})
            print(f"[DEBUG] NWS API 응답 상태: {response.status_code}")
            response.raise_for_status()
            result = response.json()
            print(f"[DEBUG] NWS API 응답 성공")
            return result
    except Exception as e:
        print(f"[DEBUG] NWS API 오류: {e}")
        return None

async def call_groq(messages: list, is_translation: bool = False) -> dict:
    """Call GROQ API using groq.Groq() client"""
    print(f"[DEBUG] GROQ API 호출 시작 - 모델: {GROQ_MODEL}")
    print(f"[DEBUG] 메시지 개수: {len(messages)}")
    print(f"[DEBUG] 번역 요청 여부: {is_translation}")
    
    if groq_client is None:
        raise Exception("GROQ 클라이언트가 초기화되지 않았습니다. GROQ_API_KEY를 확인해주세요.")
    
    print(f"[DEBUG] GROQ 메시지: {json.dumps(messages, ensure_ascii=False, indent=2)}")
    
    try:
        # 번역 요청인 경우 더 많은 토큰 허용
        max_tokens = 1024 if is_translation else 128
        
        # client.py와 동일한 방식으로 GROQ API 호출
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.0,
            max_tokens=max_tokens,
            top_p=0.9,
            stop=["\n\n"] if not is_translation else None  # 번역 시에는 stop 토큰 제거
        )
        
        print(f"[DEBUG] GROQ API 응답 성공 (max_tokens: {max_tokens})")
        print(f"[DEBUG] GROQ API 응답: {response}")
        
        # 응답에서 content 추출
        if response.choices and len(response.choices) > 0:
            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason
            print(f"[DEBUG] GROQ API 응답 내용: {content}")
            print(f"[DEBUG] GROQ API finish_reason: {finish_reason}")
            
            if finish_reason == 'length':
                print(f"[DEBUG] 경고: 응답이 토큰 제한으로 잘렸습니다.")
            
            return {
                "response": content.strip() if content else ""
            }
        else:
            raise Exception("GROQ API 응답에 content가 없습니다.")
            
    except Exception as e:
        print(f"[DEBUG] GROQ API 오류: {str(e)}")
        raise Exception(f"GROQ API error: {str(e)}")

async def call_ollama(messages: list) -> dict:
    """Call Ollama API"""
    print(f"[DEBUG] Ollama API 호출 시작 - 모델: {OLLAMA_MODEL}")
    print(f"[DEBUG] 메시지 개수: {len(messages)}")
    
    # 메시지를 프롬프트로 변환
    prompt = ""
    for msg in messages:
        if msg["role"] == "system":
            prompt += f"System: {msg['content']}\n\n"
        elif msg["role"] == "user":
            prompt += f"User: {msg['content']}\n\n"
        elif msg["role"] == "assistant":
            prompt += f"Assistant: {msg['content']}\n\n"
    
    # 프롬프트 길이 제한
    if len(prompt) > 4000:
        prompt = prompt[:4000] + "\n\n[Content truncated due to length]"
    
    print(f"[DEBUG] Ollama 프롬프트 길이: {len(prompt)}")
    print(f"[DEBUG] Ollama 프롬프트: {prompt[:200]}...")
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 1024
        }
    }
    
    print(f"[DEBUG] Ollama API URL: {OLLAMA_URL}/api/generate")
    print(f"[DEBUG] Ollama API Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            headers = {
                "Content-Type": "application/json"
            }
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json=payload,
                headers=headers
            )
            print(f"[DEBUG] Ollama API 응답 상태: {response.status_code}")
            
            response.raise_for_status()
            result = response.json()
            print(f"[DEBUG] Ollama API 응답: {json.dumps(result, ensure_ascii=False, indent=2)}")
            
            if "response" in result:
                print(f"[DEBUG] Ollama API 응답 내용: {result['response'][:200]}...")
            
            return result
        except Exception as e:
            print(f"[DEBUG] Ollama API 오류: {str(e)}")
            raise Exception(f"Ollama API error: {str(e)}")

async def call_llm(messages: list, is_translation: bool = False) -> dict:
    """Call the configured LLM provider"""
    print(f"[DEBUG] LLM 호출 시작 - Provider: {LLM_PROVIDER}, 번역: {is_translation}")
    if LLM_PROVIDER == "groq":
        return await call_groq(messages, is_translation)
    elif LLM_PROVIDER == "ollama":
        return await call_ollama(messages)
    else:
        raise Exception(f"지원하지 않는 LLM Provider: {LLM_PROVIDER}")

def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
Event: {props.get('event', 'Unknown')}
Area: {props.get('areaDesc', 'Unknown')}
Severity: {props.get('severity', 'Unknown')}
Description: {props.get('description', 'No description available')}
Instructions: {props.get('instruction', 'No specific instructions provided')}
"""

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Weather API Server is running", 
        "version": "1.0.0",
        "llm_provider": LLM_PROVIDER,
        "groq_model": GROQ_MODEL if LLM_PROVIDER == "groq" else None,
        "ollama_model": OLLAMA_MODEL if LLM_PROVIDER == "ollama" else None
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "llm_provider": LLM_PROVIDER}

@app.post("/api/query")
async def process_query(request: QueryRequest):
    """Process a query using configured LLM and weather tools"""
    print(f"[DEBUG] 쿼리 처리 시작: {request.query}")
    print(f"[DEBUG] LLM Provider: {LLM_PROVIDER}")
    
    async def generate_response() -> AsyncGenerator[str, None]:
        try:
            # 1. 초기 응답 전송
            yield f"data: {json.dumps({'type': 'status', 'message': f'쿼리를 처리하고 있습니다... (LLM: {LLM_PROVIDER})'})}\n\n"
            
            # 2. 날씨 관련 키워드 감지
            weather_keywords = ["weather", "forecast", "temperature", "날씨", "예보", "기온"]
            query_lower = request.query.lower()
            
            print(f"[DEBUG] 날씨 키워드 검사: {weather_keywords}")
            print(f"[DEBUG] 쿼리 (소문자): {query_lower}")
            
            weather_data = None
            if any(keyword in query_lower for keyword in weather_keywords):
                print(f"[DEBUG] 날씨 관련 쿼리 감지됨")
                yield f"data: {json.dumps({'type': 'status', 'message': '날씨 정보를 가져오고 있습니다...'})}\n\n"
                
                # 위치에 따른 도구 선택
                tool_name = None
                tool_args = {}
                
                if any(location in query_lower for location in ["los angeles", "la", "캘리포니아", "california"]):
                    tool_name = "get_forecast"
                    tool_args = {"latitude": 34.0522, "longitude": -118.2437}
                elif any(location in query_lower for location in ["new york", "뉴욕", "ny"]):
                    tool_name = "get_forecast"
                    tool_args = {"latitude": 40.7128, "longitude": -74.0060}
                elif any(location in query_lower for location in ["texas", "텍사스", "tx"]):
                    tool_name = "get_alerts"
                    tool_args = {"state": "TX"}
                elif any(location in query_lower for location in ["california", "캘리포니아", "ca"]):
                    tool_name = "get_alerts"
                    tool_args = {"state": "CA"}
                else:
                    # 기본적으로 LA 날씨 제공
                    tool_name = "get_forecast"
                    tool_args = {"latitude": 34.0522, "longitude": -118.2437}
                
                print(f"[DEBUG] 선택된 도구: {tool_name}")
                print(f"[DEBUG] 도구 인수: {tool_args}")
                
                # 3. 날씨 API 호출
                if tool_name == "get_forecast":
                    print(f"[DEBUG] 예보 API 호출 시작")
                    points_url = f"{NWS_API_BASE}/points/{tool_args['latitude']},{tool_args['longitude']}"
                    points_data = await make_nws_request(points_url)
                    
                    if points_data:
                        print(f"[DEBUG] Points API 응답 성공")
                        forecast_url = points_data["properties"]["forecast"]
                        print(f"[DEBUG] Forecast URL: {forecast_url}")
                        forecast_data = await make_nws_request(forecast_url)
                        
                        if forecast_data:
                            print(f"[DEBUG] Forecast API 응답 성공")
                            periods = forecast_data["properties"]["periods"]
                            forecasts = []
                            for period in periods[:5]:
                                forecast = f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
"""
                                forecasts.append(forecast)
                            
                            weather_data = "\n---\n".join(forecasts)
                            print(f"[DEBUG] 날씨 데이터 생성 완료 (길이: {len(weather_data)})")
                        else:
                            weather_data = "날씨 데이터를 가져올 수 없습니다."
                            print(f"[DEBUG] Forecast API 실패")
                    else:
                        weather_data = "날씨 데이터를 가져올 수 없습니다."
                        print(f"[DEBUG] Points API 실패")
                        
                elif tool_name == "get_alerts":
                    print(f"[DEBUG] 경보 API 호출 시작")
                    url = f"{NWS_API_BASE}/alerts/active/area/{tool_args['state']}"
                    data = await make_nws_request(url)
                    
                    if data and "features" in data:
                        if data["features"]:
                            alerts = [format_alert(feature) for feature in data["features"]]
                            weather_data = "\n---\n".join(alerts)
                            print(f"[DEBUG] 경보 데이터 생성 완료 (경보 수: {len(data['features'])})")
                        else:
                            weather_data = "이 지역에 활성화된 경보가 없습니다."
                            print(f"[DEBUG] 활성 경보 없음")
                    else:
                        weather_data = "경보 데이터를 가져올 수 없습니다."
                        print(f"[DEBUG] 경보 API 실패")
            
            # 4. LLM을 한 번만 호출하여 날씨 정보와 번역을 함께 처리
            yield f"data: {json.dumps({'type': 'status', 'message': f'{LLM_PROVIDER.upper()} 모델을 호출하고 있습니다...'})}\n\n"
            
            if weather_data:
                # 날씨 정보가 있는 경우: 날씨 정보와 번역을 함께 처리
                system_message = f"""
당신은 도움이 되는 어시스턴트입니다.
다음 날씨 정보를 한국어로 번역하고, 단위를 한국에서 사용하는 단위로 변경해주세요:

1. 화씨(°F) → 섭씨(°C)로 변환
2. 마일(mph) → 킬로미터(km/h)로 변환
3. 모든 텍스트를 자연스러운 한국어로 번역
4. 날씨 상태를 한국어로 표현 (예: sunny → 맑음, cloudy → 흐림)

답변은 반드시 한국어로만 작성해주세요.
"""
                
                messages = [
                    {
                        "role": "system",
                        "content": system_message
                    },
                    {
                        "role": "user",
                        "content": f"다음 날씨 정보를 한국어로 번역하고 단위를 변환해주세요:\n\n{weather_data}"
                    }
                ]
                
                print(f"[DEBUG] 날씨 정보와 번역을 함께 처리")
                print(f"[DEBUG] 번역할 데이터 길이: {len(weather_data)}")
                
            else:
                # 날씨 정보가 없는 경우: 일반 쿼리 처리
                system_message = f"""
You are a helpful assistant with access to weather tools. 
Available tools: ['get_alerts', 'get_forecast']
When asked about weather, I will automatically call the appropriate weather tool.
답변은 한국어로 해주세요.
"""

                messages = [
                    {
                        "role": "system",
                        "content": system_message
                    },
                    {
                        "role": "user",
                        "content": request.query
                    }
                ]
                
                print(f"[DEBUG] 일반 쿼리 처리")

            print(f"[DEBUG] 시스템 메시지: {system_message}")
            print(f"[DEBUG] 사용자 메시지: {request.query if not weather_data else '날씨 정보 번역 요청'}")

            # LLM 호출 (번역이 필요한 경우 is_translation=True)
            response = await call_llm(messages, is_translation=bool(weather_data))
            
            if "response" not in response:
                print(f"[DEBUG] LLM 응답에 'response' 키가 없음: {response}")
                yield f"data: {json.dumps({'type': 'error', 'message': 'LLM 응답을 받을 수 없습니다.'})}\n\n"
                return

            response_text = response["response"]
            print(f"[DEBUG] LLM 응답: {response_text}")
            
            # 5. 최종 결과 반환
            yield f"data: {json.dumps({'type': 'result', 'content': response_text})}\n\n"
                
        except Exception as e:
            print(f"[DEBUG] 쿼리 처리 중 오류: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'오류가 발생했습니다: {str(e)}'})}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )

@app.post("/api/get_forecast", response_model=WeatherResponse)
async def get_forecast(request: ForecastRequest):
    """Get weather forecast for a location.

    Args:
        request: ForecastRequest with latitude and longitude
    """
    try:
        # First get the forecast grid endpoint
        points_url = f"{NWS_API_BASE}/points/{request.latitude},{request.longitude}"
        points_data = await make_nws_request(points_url)

        if not points_data:
            return WeatherResponse(
                success=False,
                data="",
                error="Unable to fetch forecast data for this location."
            )

        # Get the forecast URL from the points response
        forecast_url = points_data["properties"]["forecast"]
        forecast_data = await make_nws_request(forecast_url)

        if not forecast_data:
            return WeatherResponse(
                success=False,
                data="",
                error="Unable to fetch detailed forecast."
            )

        # Format the periods into a readable forecast
        periods = forecast_data["properties"]["periods"]
        forecasts = []
        for period in periods[:5]:  # Only show next 5 periods
            forecast = f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
"""
            forecasts.append(forecast)

        result = "\n---\n".join(forecasts)
        
        return WeatherResponse(
            success=True,
            data=result
        )
        
    except Exception as e:
        return WeatherResponse(
            success=False,
            data="",
            error=f"Error processing forecast request: {str(e)}"
        )

@app.post("/api/get_alerts", response_model=WeatherResponse)
async def get_alerts(request: AlertsRequest):
    """Get weather alerts for a US state.

    Args:
        request: AlertsRequest with state code
    """
    try:
        url = f"{NWS_API_BASE}/alerts/active/area/{request.state}"
        data = await make_nws_request(url)

        if not data or "features" not in data:
            return WeatherResponse(
                success=False,
                data="",
                error="Unable to fetch alerts or no alerts found."
            )

        if not data["features"]:
            return WeatherResponse(
                success=True,
                data="No active alerts for this state."
            )

        alerts = [format_alert(feature) for feature in data["features"]]
        result = "\n---\n".join(alerts)
        
        return WeatherResponse(
            success=True,
            data=result
        )
        
    except Exception as e:
        return WeatherResponse(
            success=False,
            data="",
            error=f"Error processing alerts request: {str(e)}"
        )

@app.get("/api/tools")
async def list_tools():
    """List available tools"""
    return {
        "tools": [
            {
                "name": "get_forecast",
                "description": "Get weather forecast for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "latitude": {"type": "number", "description": "Latitude of the location"},
                        "longitude": {"type": "number", "description": "Longitude of the location"}
                    },
                    "required": ["latitude", "longitude"]
                }
            },
            {
                "name": "get_alerts",
                "description": "Get weather alerts for a US state",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "state": {"type": "string", "description": "Two-letter US state code (e.g. CA, NY)"}
                    },
                    "required": ["state"]
                }
            }
        ]
    }

if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        "server_app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug"
    ) 