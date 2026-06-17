import asyncio
import httpx
import json


async def test_backend():
    base_url = "http://localhost:8000"

    print("测试后端API...")
    print("=" * 50)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{base_url}/")
            print(f"根路径: {response.json()}")
        except Exception as e:
            print(f"根路径失败: {e}")
            return

        try:
            response = await client.get(f"{base_url}/health")
            print(f"健康检查: {response.json()}")
        except Exception as e:
            print(f"健康检查失败: {e}")

        print()
        print("测试聊天API...")
        try:
            response = await client.post(
                f"{base_url}/api/v1/chat/",
                json={"message": "你好"},
                timeout=60.0,
            )
            print(f"聊天响应: {response.json()}")
        except Exception as e:
            print(f"聊天失败: {e}")

        print()
        print("测试记忆API...")
        try:
            response = await client.get(f"{base_url}/api/v1/memory/")
            print(f"记忆列表: {response.json()}")
        except Exception as e:
            print(f"记忆列表失败: {e}")

        print()
        print("测试知识库API...")
        try:
            response = await client.get(f"{base_url}/api/v1/knowledge/")
            print(f"知识库列表: {response.json()}")
        except Exception as e:
            print(f"知识库列表失败: {e}")

        print()
        print("测试Persona API...")
        try:
            response = await client.get(f"{base_url}/api/v1/persona/")
            print(f"Persona: {response.json()}")
        except Exception as e:
            print(f"Persona失败: {e}")


if __name__ == "__main__":
    asyncio.run(test_backend())