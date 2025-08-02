import asyncio
import json
import httpx
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env

class WeatherClient:
    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url

    async def connect_to_server(self):
        """Connect to the weather server"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.server_url}/health")
                response.raise_for_status()
                print(f"\nConnected to server at {self.server_url}")
                return True
        except Exception as e:
            print(f"Error connecting to server: {e}")
            return False

    async def process_query(self, query: str):
        """Send query to server and stream response"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.server_url}/api/query",
                    json={"query": query},
                    headers={"Content-Type": "application/json"},
                    timeout=120.0
                )
                response.raise_for_status()
                
                # 스트리밍 응답 처리
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                        
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])  # "data: " 제거
                            
                            if data["type"] == "status":
                                print(f"\n[상태] {data['message']}", end="", flush=True)
                            elif data["type"] == "result":
                                # 결과를 chunk 단위로 출력
                                content = data['content']
                                print(f"\n[결과] ", end="", flush=True)
                                
                                # 한 글자씩 출력하여 타이핑 효과 생성
                                for char in content:
                                    print(char, end="", flush=True)
                                    await asyncio.sleep(0.01)  # 10ms 지연
                                print()  # 줄바꿈
                                
                            elif data["type"] == "error":
                                print(f"\n[오류] {data['message']}")
                                
                        except json.JSONDecodeError as e:
                            print(f"JSON 파싱 오류: {e}, 라인: {line}")
                            continue
                        except KeyError as e:
                            print(f"응답 형식 오류: {e}, 데이터: {data}")
                            continue
                    else:
                        # 일반 텍스트 응답도 처리
                        print(f"응답: {line}")
                            
        except httpx.HTTPStatusError as e:
            print(f"\nHTTP 오류: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            print(f"\n요청 오류: {e}")
        except Exception as e:
            print(f"\nError processing query: {str(e)}")
            import traceback
            traceback.print_exc()

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nWeather Client Started!")
        print("Type your queries or 'quit' to exit.")
        print("Try asking about weather in Los Angeles, New York, or Texas!")
        
        while True:
            try:
                query = input("\n[Query]: ").strip()
                
                if query.lower() == 'quit':
                    break
                    
                if not query:
                    print("Please enter a query.")
                    continue
                    
                await self.process_query(query)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
                print("Please try again.")

async def main():
    client = WeatherClient()
    
    # Connect to server
    if not await client.connect_to_server():
        print("Failed to connect to weather server. Make sure the server is running on http://localhost:8000")
        return
    
    # Start chat loop
    await client.chat_loop()

if __name__ == "__main__":
    asyncio.run(main()) 