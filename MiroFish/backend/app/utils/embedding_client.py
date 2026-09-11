"""
Embedding客户端封装
用于调用 NVIDIA Embedding API (OpenAI 兼容格式)
"""

import httpx
from typing import Optional, List, Dict, Any
from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('mirofish.embedding_client')

class EmbeddingClient:
    """Embedding客户端"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or Config.EMBEDDING_API_KEY
        self.base_url = base_url or Config.EMBEDDING_BASE_URL
        self.model = model or Config.EMBEDDING_MODEL_NAME
        
        if not self.api_key:
            raise ValueError("EMBEDDING_API_KEY 未配置")
        
        # 确保 base_url 以 v1 结尾（如果是 OpenAI 风格）
        self.base_url = self.base_url.rstrip('/')
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def get_embedding(self, text: str) -> List[float]:
        """
        获取单个文本的 Embedding
        """
        embeddings = await self.get_embeddings([text])
        return embeddings[0] if embeddings else []
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        批量获取 Embedding
        """
        if not texts:
            return []
            
        url = f"{self.base_url}/embeddings"
        payload = {
            "input": texts,
            "model": self.model,
            "encoding_format": "float"
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=self.headers, json=payload)
                response.raise_for_status()
                data = response.json()
                
                # 解析 OpenAI 格式的响应
                embeddings = [item["embedding"] for item in data["data"]]
                return embeddings
        except Exception as e:
            logger.error(f"获取 Embedding 失败: {str(e)}")
            raise
