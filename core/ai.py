import requests

from defines import *


class AiHandler:
    """
    AI处理模型基类，具体的AI调用在子类中完成
    """

    model = CONFIG.ai.model

    @staticmethod
    async def chat_completion(system, user, temperature=1.0):
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        body = {
            "model": CONFIG.ai.model,
            "stream": False,
            "temperature": temperature,
            "messages": messages,
        }
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {CONFIG.ai.key}"}
        response = requests.post(CONFIG.ai.url, json=body, headers=headers)
        if response.ok:
            data = response.json()
            return data["choices"][0]["message"]["content"]
