import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()


async def test_mimo_api():
    api_key = os.getenv("MIMO_API_KEY")
    api_base = os.getenv("MIMO_API_BASE", "https://api.xiaomimimo.com/v1")
    model = os.getenv("MIMO_MODEL", "mimo-v2.5-pro")

    if not api_key:
        print("错误：未设置 MIMO_API_KEY 环境变量")
        return

    print(f"测试 MIMO API...")
    print(f"API Base: {api_base}")
    print(f"Model: {model}")
    print()

    headers = {
        "api-key": api_key,
        "Content-Type": "application/json",
    }

    payload = {
        "messages": [
            {"role": "user", "content": "你好，请简单介绍一下自己"}
        ],
        "model": model,
        "max_completion_tokens": 256,
        "temperature": 1.0,
        "stream": False,
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            result = response.json()

            print("API 调用成功！")
            print(f"回复：{result['choices'][0]['message']['content']}")
            return True

        except httpx.HTTPStatusError as e:
            print(f"HTTP 错误：{e.response.status_code}")
            print(f"响应：{e.response.text}")
            return False

        except Exception as e:
            print(f"错误：{str(e)}")
            return False


if __name__ == "__main__":
    asyncio.run(test_mimo_api())