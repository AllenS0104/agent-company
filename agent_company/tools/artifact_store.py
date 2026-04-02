"""Artifact 存储 — 管理产出物（代码/测试报告/ADR/风险清单）"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..core.models import ArtifactType
from .base import BaseTool, ToolResult


class ArtifactStore(BaseTool):
    """产出物存储与管理"""

    def __init__(self, base_dir: str = ".artifacts"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @property
    def name(self) -> str:
        return "artifact_store"

    @property
    def description(self) -> str:
        return "存储和检索产出物（代码/测试报告/ADR/风险清单/文档）"

    async def execute(self, action: str = "save", **kwargs: Any) -> ToolResult:
        if action == "save":
            return await self._save(**kwargs)
        elif action == "load":
            return await self._load(**kwargs)
        elif action == "list":
            return await self._list(**kwargs)
        return ToolResult(success=False, error=f"Unknown action: {action}")

    async def _save(
        self,
        artifact_type: str = "document",
        title: str = "",
        content: str = "",
        thread_id: str = "",
        **kwargs: Any,
    ) -> ToolResult:
        atype = ArtifactType(artifact_type)
        type_dir = self.base_dir / atype.value
        type_dir.mkdir(exist_ok=True)

        safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in title) or "untitled"
        file_path = type_dir / f"{safe_title}.md"
        file_path.write_text(content, encoding="utf-8")

        # 保存元数据
        meta = {"title": title, "type": artifact_type, "thread_id": thread_id}
        meta_path = type_dir / f"{safe_title}.meta.json"
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        return ToolResult(success=True, output=f"Saved: {file_path}", artifacts=[str(file_path)])

    async def _load(self, path: str = "", **kwargs: Any) -> ToolResult:
        file_path = Path(path)
        if not file_path.exists():
            return ToolResult(success=False, error=f"File not found: {path}")
        content = file_path.read_text(encoding="utf-8")
        return ToolResult(success=True, output=content)

    async def _list(self, artifact_type: str = "", **kwargs: Any) -> ToolResult:
        results = []
        search_dir = self.base_dir / artifact_type if artifact_type else self.base_dir
        if search_dir.exists():
            for f in search_dir.rglob("*.md"):
                results.append(str(f.relative_to(self.base_dir)))
        output = "\n".join(results) if results else "No artifacts found"
        return ToolResult(success=True, output=output)
