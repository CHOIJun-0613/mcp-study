#!/usr/bin/env python3
"""
MCP Bridge Server - HTTP 서버와 Cursor 사이의 중계 서버
"""

import sys
import json
import httpx
import asyncio
import argparse
from typing import Any
from mcp.server.fastmcp import FastMCP
from logger_config import setup_logger

# Set encoding for proper character handling
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 로거 설정
logger = setup_logger("mcp-bridge")

# 명령행 인수 파싱
parser = argparse.ArgumentParser(description='MCP Bridge Server')
parser.add_argument('--url', '-u', 
                   default='http://localhost:8000',
                   help='HTTP 서버 URL (기본값: http://localhost:8000)')
args = parser.parse_args()

# HTTP 서버 URL 설정
HTTP_SERVER_URL = args.url

logger.info(f"MCP Bridge Server 시작 - HTTP 서버 URL: {HTTP_SERVER_URL}")

# Initialize FastMCP server
mcp = FastMCP("weather-mcp-bridge")

# 서버 메타데이터 설정

async def call_http_server(query: str) -> str:
    """HTTP 서버에 요청을 보내고 응답을 받습니다."""
    logger.debug(f"HTTP 서버 호출 시작: {query}")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            logger.debug(f"HTTP 요청 전송: {HTTP_SERVER_URL}/api/query")
            
            response = await client.post(
                f"{HTTP_SERVER_URL}/api/query",
                json={"query": query},
                headers={"Content-Type": "application/json"}
            )
            
            logger.debug(f"HTTP 응답 상태: {response.status_code}")
            response.raise_for_status()
            
            # 스트리밍 응답 처리
            result_parts = []
            async for line in response.aiter_lines():
                logger.debug(f"스트림 라인: {line}")
                
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])  # "data: " 제거
                        logger.debug(f"파싱된 데이터: {data}")
                        
                        if data["type"] == "status":
                            logger.info(f"상태: {data['message']}")
                        elif data["type"] == "result":
                            result_parts.append(data["content"])
                            logger.debug(f"결과 추가: {data['content'][:50]}...")
                        elif data["type"] == "error":
                            error_msg = f"오류: {data['message']}"
                            logger.error(f"오류 발생: {error_msg}")
                            return error_msg
                            
                    except json.JSONDecodeError as e:
                        logger.warning(f"JSON 파싱 오류: {e}")
                        continue
            
            final_result = "\n".join(result_parts) if result_parts else "응답을 받을 수 없습니다."
            logger.debug(f"최종 결과: {final_result[:100]}...")
            return final_result
                        
    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP 상태 오류: {e.response.status_code} - {e.response.text}"
        logger.error(error_msg)
        return error_msg
    except httpx.RequestError as e:
        error_msg = f"HTTP 요청 오류: {e}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"HTTP 서버 호출 오류: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool()
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state.

    Args:
        state: Two-letter US state code (e.g. CA, NY)
    """
    logger.info(f"get_alerts 호출됨: state={state}")
    query = f"{state} 주의 날씨 경보를 알려줘"
    result = await call_http_server(query)
    logger.debug(f"get_alerts 결과: {result[:100]}...")
    return result

@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    logger.info(f"get_forecast 호출됨: lat={latitude}, lon={longitude}")
    query = f"위도 {latitude}, 경도 {longitude} 위치의 날씨 예보를 알려줘"
    result = await call_http_server(query)
    logger.debug(f"get_forecast 결과: {result[:100]}...")
    return result

@mcp.tool()
async def process_weather_query(query: str) -> str:
    """Process a natural language weather query with AI assistance.

    Args:
        query: Natural language weather query (Korean or English)
    """
    logger.info(f"process_weather_query 호출됨: {query}")
    result = await call_http_server(query)
    logger.debug(f"process_weather_query 결과: {result[:100]}...")
    return result

if __name__ == "__main__":
    logger.info("MCP 브리지 서버 시작 중...")
    logger.info(f"HTTP 서버 URL: {HTTP_SERVER_URL}")
    logger.info("사용 가능한 도구: get_alerts, get_forecast, process_weather_query")
    logger.info("사용법: python mcp_bridge.py --url <HTTP_SERVER_URL>")
    mcp.run(transport='stdio') 