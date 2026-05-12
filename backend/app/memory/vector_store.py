"""
向量存储系统
基于向量数据库的长时记忆存储
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
import hashlib

from loguru import logger

# 尝试导入 ChromaDB
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

# 尝试导入 FAISS
try:
    import faiss
    import numpy as np
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False


class VectorMemoryStore:
    """
    向量记忆存储
    用于存储和检索长期记忆（如重要对话、用户喜好等）
    """
    
    def __init__(
        self,
        backend: str = "memory",
        collection_name: str = "travel_memories",
        persist_dir: Optional[str] = None
    ):
        """
        初始化向量存储
        
        Args:
            backend: 后端类型，memory/chroma/faiss
            collection_name: 集合名称
            persist_dir: 持久化目录（ChromaDB 用）
        """
        self.backend = backend
        self.collection_name = collection_name
        self.persist_dir = persist_dir
        
        self._embeddings: Dict[str, List[float]] = {}
        self._documents: Dict[str, Dict] = {}
        self._initialized = False
        
        # 初始化后端
        if backend == "chroma":
            self._init_chroma()
        elif backend == "faiss":
            self._init_faiss()
        
        logger.info(f"初始化向量存储: {backend}/{collection_name}")
    
    def _init_chroma(self):
        """初始化 ChromaDB"""
        if not CHROMA_AVAILABLE:
            logger.warning("ChromaDB 未安装，切换到内存模式")
            self.backend = "memory"
            return
        
        try:
            settings = ChromaSettings(
                persist_directory=self.persist_dir,
                anonymized_telemetry=False
            )
            self._client = chromadb.Client(settings)
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name
            )
            self._initialized = True
            logger.info("ChromaDB 初始化成功")
        except Exception as e:
            logger.error(f"ChromaDB 初始化失败: {e}")
            self.backend = "memory"
    
    def _init_faiss(self):
        """初始化 FAISS"""
        if not FAISS_AVAILABLE:
            logger.warning("FAISS 未安装，切换到内存模式")
            self.backend = "memory"
            return
        
        # FAISS 需要预先知道维度，这里简化为内存模式
        self.backend = "memory"
    
    async def add_memory(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        memory_type: str = "general"
    ) -> str:
        """
        添加记忆到向量存储
        
        Args:
            content: 记忆内容
            metadata: 元数据
            user_id: 用户ID
            session_id: 会话ID
            memory_type: 记忆类型
            
        Returns:
            记忆ID
        """
        # 生成唯一ID
        memory_id = self._generate_id(content, user_id or "")
        
        # 准备文档
        doc = {
            "id": memory_id,
            "content": content,
            "metadata": metadata or {},
            "user_id": user_id,
            "session_id": session_id,
            "memory_type": memory_type,
            "created_at": datetime.now().isoformat()
        }
        
        # 获取嵌入（简化版，实际应该用 Embedding 模型）
        embedding = self._get_embedding(content)
        
        # 存储
        if self.backend == "chroma" and self._initialized:
            self._collection.add(
                ids=[memory_id],
                documents=[content],
                metadatas=[doc],
                embeddings=[embedding]
            )
        else:
            # 内存存储
            self._documents[memory_id] = doc
            self._embeddings[memory_id] = embedding
        
        logger.debug(f"添加记忆: {memory_id[:8]}...")
        return memory_id
    
    async def search_memories(
        self,
        query: str,
        user_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        top_k: int = 5,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        搜索相似记忆
        
        Args:
            query: 查询文本
            user_id: 限制用户
            memory_type: 限制类型
            top_k: 返回数量
            threshold: 相似度阈值
            
        Returns:
            相似记忆列表
        """
        # 获取查询嵌入
        query_embedding = self._get_embedding(query)
        
        results = []
        
        if self.backend == "chroma" and self._initialized:
            # ChromaDB 查询
            where_filter = {}
            if user_id:
                where_filter["user_id"] = user_id
            if memory_type:
                where_filter["memory_type"] = memory_type
            
            chroma_results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter if where_filter else None
            )
            
            for i, doc_id in enumerate(chroma_results["ids"][0]):
                distance = chroma_results["distances"][0][i] if chroma_results["distances"] else 0
                similarity = 1 - distance
                
                if similarity >= threshold:
                    results.append({
                        "id": doc_id,
                        "content": chroma_results["documents"][0][i],
                        "metadata": chroma_results["metadatas"][0][i],
                        "similarity": similarity
                    })
        else:
            # 内存搜索（简化版，实际应该用向量相似度计算）
            for memory_id, doc in self._documents.items():
                # 过滤
                if user_id and doc.get("user_id") != user_id:
                    continue
                if memory_type and doc.get("memory_type") != memory_type:
                    continue
                
                # 简化的相似度计算（关键词匹配）
                similarity = self._simple_similarity(query, doc["content"])
                
                if similarity >= threshold:
                    results.append({
                        "id": memory_id,
                        "content": doc["content"],
                        "metadata": doc,
                        "similarity": similarity
                    })
            
            # 排序并限制数量
            results.sort(key=lambda x: x["similarity"], reverse=True)
            results = results[:top_k]
        
        logger.debug(f"搜索记忆: '{query[:30]}...' 找到 {len(results)} 条")
        return results
    
    async def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """获取特定记忆"""
        if self.backend == "chroma" and self._initialized:
            try:
                result = self._collection.get(ids=[memory_id])
                if result and result["ids"]:
                    return {
                        "id": result["ids"][0],
                        "content": result["documents"][0],
                        "metadata": result["metadatas"][0]
                    }
            except:
                pass
        
        return self._documents.get(memory_id)
    
    async def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        try:
            if self.backend == "chroma" and self._initialized:
                self._collection.delete(ids=[memory_id])
            
            if memory_id in self._documents:
                del self._documents[memory_id]
                del self._embeddings[memory_id]
            
            logger.debug(f"删除记忆: {memory_id[:8]}...")
            return True
        except Exception as e:
            logger.error(f"删除记忆失败: {e}")
            return False
    
    def _generate_id(self, content: str, user_id: str) -> str:
        """生成记忆ID"""
        data = f"{content}:{user_id}:{datetime.now().timestamp()}"
        return hashlib.md5(data.encode()).hexdigest()
    
    def _get_embedding(self, text: str) -> List[float]:
        """
        获取文本嵌入
        
        注意：这是简化实现，实际应该调用 Embedding 模型
        """
        # 简化版：使用字符哈希生成伪嵌入
        # 实际应该使用 text-embedding-v3 或类似模型
        import random
        random.seed(sum(ord(c) for c in text))
        return [random.random() for _ in range(128)]
    
    def _simple_similarity(self, query: str, content: str) -> float:
        """简化版相似度计算（关键词匹配）"""
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        
        if not query_words:
            return 0.0
        
        common = query_words & content_words
        return len(common) / len(query_words)


# 全局向量存储实例
_vector_store: Optional[VectorMemoryStore] = None


def get_vector_store() -> VectorMemoryStore:
    """获取全局向量存储实例"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorMemoryStore()
    return _vector_store


async def add_long_term_memory(
    content: str,
    user_id: Optional[str] = None,
    memory_type: str = "general"
) -> str:
    """添加长期记忆的便捷函数"""
    return await get_vector_store().add_memory(
        content=content,
        user_id=user_id,
        memory_type=memory_type
    )


async def search_long_term_memory(
    query: str,
    user_id: Optional[str] = None,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """搜索长期记忆的便捷函数"""
    return await get_vector_store().search_memories(
        query=query,
        user_id=user_id,
        top_k=top_k
    )
