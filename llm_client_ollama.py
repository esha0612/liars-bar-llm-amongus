import requests
import json

API_BASE_URL = "http://localhost:11434"  # Ollama默认地址

class LLMClient:
    def __init__(self, base_url=API_BASE_URL):
        """初始化Ollama客户端"""
        self.base_url = base_url
        
    def chat(self, messages, model="deepseek-r1"):
        """与Ollama模型交互
        
        Args:
            messages: 消息列表
            model: 使用的Ollama模型
        
        Returns:
            tuple: (content, reasoning_content)
        """
        try:
            print(f"Ollama请求: {messages}")
            
            # 构建Ollama API请求
            url = f"{self.base_url}/api/chat"
            payload = {
                "model": model,
                "messages": messages,
                "options": {
                    "temperature": 0.7
                }
            }
            
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            if "message" in data.get("message", {}):
                content = data["message"]["content"]
                # Ollama原生不支持reasoning_content，可根据需要扩展
                reasoning_content = ""
                print(f"Ollama回复内容: {content}")
                return content, reasoning_content
                
            return "", ""
                
        except Exception as e:
            print(f"Ollama调用出错: {str(e)}")
            return "", ""
        
# 使用示例
if __name__ == "__main__":
    llm = LLMClient()
    messages = [
        {"role": "user", "content": "你好"}
    ]
    response = llm.chat(messages)
    print(f"响应: {response}")