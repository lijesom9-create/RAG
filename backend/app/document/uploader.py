"""
文档上传服务

将解析后的文档分块存入统一知识库（UnifiedKnowledgeStore）。
支持文件系统存储，保存原始文件。
"""

import uuid
from typing import List, Optional
from pathlib import Path
from loguru import logger

from .parser import DocumentParser
from .chunker import DocumentChunker
from ..knowledge.unified_store import UnifiedKnowledgeStore, KnowledgeItem
from ..storage.file_storage import FileStorage, get_file_storage


class DocumentUploader:
    """文档上传服务"""

    def __init__(
        self,
        knowledge_store: UnifiedKnowledgeStore = None,
        file_storage: FileStorage = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        strategy: str = "auto",  # 自动选择分块策略
    ):
        self.parser = DocumentParser()
        self.chunker = DocumentChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            strategy=strategy,
        )
        self.knowledge_store = knowledge_store
        self.file_storage = file_storage or get_file_storage()

    async def upload(
        self,
        content: bytes,
        filename: str,
        title: Optional[str] = None,
        course_id: Optional[str] = None,
        user_id: Optional[str] = None,
        topic_id: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> dict:
        """
        上传并索引文档

        Args:
            content: 文件二进制内容
            filename: 文件名
            title: 文档标题
            course_id: 关联课程 ID（兼容旧版）
            user_id: 关联用户 ID
            topic_id: 关联主题 ID

        Returns:
            dict: 上传结果，包含 document_id, chunk_count
        """
        # 1. 解析文档
        text = self.parser.parse(content, filename)
        if not text.strip():
            raise ValueError("文档内容为空或解析失败")

        # 2. 生成文档 ID
        document_id = document_id or str(uuid.uuid4())
        metadata = self.parser.get_metadata(filename, title)
        metadata["course_id"] = course_id
        metadata["user_id"] = user_id
        metadata["topic_id"] = topic_id
        metadata["document_id"] = document_id

        # 3. 保存原始文件到文件系统
        file_info = None
        if user_id and self.file_storage:
            try:
                file_info = await self.file_storage.save(
                    content=content,
                    filename=filename,
                    user_id=user_id,
                    document_id=document_id,
                )
                metadata["file_path"] = file_info.get("file_path")
                metadata["file_size"] = file_info.get("file_size")
                logger.info(f"原始文件已保存: {file_info.get('file_path')}")
            except Exception as e:
                logger.warning(f"保存原始文件失败: {e}")

        # 4. 根据文件类型选择分块策略
        ext = Path(filename).suffix.lower()
        if ext in (".md", ".markdown"):
            force_strategy = "markdown"
        else:
            force_strategy = "recursive"  # PDF/Word/TXT 使用递归分块

        # 5. 分块
        chunks = self.chunker.chunk(text, document_id, force_strategy=force_strategy)
        if not chunks:
            raise ValueError("文档分块后为空")

        # 6. 转换为 KnowledgeItem 并存入统一知识库
        items = []
        for chunk in chunks:
            # 合并元数据，保留 heading_path
            chunk_metadata = chunk["metadata"]
            merged = {
                **metadata,
                **chunk_metadata,
                "source": "user_document",
            }

            # 过滤 None 值和空列表
            cleaned = {}
            for k, v in merged.items():
                if v is None:
                    continue
                if isinstance(v, list) and len(v) == 0:
                    continue
                cleaned[k] = v

            # 标题路径转为字符串（方便存储）
            if "heading_path" in cleaned and isinstance(cleaned["heading_path"], list):
                cleaned["heading_path_str"] = " > ".join(cleaned["heading_path"])

            item = KnowledgeItem(
                id=chunk["id"],
                title=title or filename,
                content=chunk["text"],
                source="user_document",
                metadata=cleaned,
            )
            items.append(item)

        # 7. 批量添加到统一知识库
        if not self.knowledge_store:
            raise RuntimeError("UnifiedKnowledgeStore 未初始化，文档无法入库")
        self.knowledge_store.add_batch(items)

        logger.info(f"文档上传完成: {filename} -> {document_id}, 共 {len(chunks)} 块")

        return {
            "document_id": document_id,
            "filename": filename,
            "title": metadata["title"],
            "chunk_count": len(chunks),
            "char_count": len(text),
            "file_path": file_info.get("file_path") if file_info else None,
        }

    def list_documents(self, user_id: Optional[str] = None) -> List[dict]:
        """列出已上传的文档"""
        if not self.knowledge_store:
            return []

        results = self.knowledge_store.search(
            query="",
            source="user_document",
            user_id=user_id,
            top_k=1000,
            min_score=0.0,
        )

        # 按 document_id 聚合
        docs = {}
        for r in results:
            doc_id = r.get("metadata", {}).get("document_id", "")
            if doc_id and doc_id not in docs:
                docs[doc_id] = {
                    "document_id": doc_id,
                    "title": r.get("title", ""),
                    "user_id": r.get("metadata", {}).get("user_id", ""),
                    "topic_id": r.get("metadata", {}).get("topic_id", ""),
                }

        return list(docs.values())
