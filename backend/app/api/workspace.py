import json
import logging
import shutil
from typing import Any
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.workspace_manager import (
    ensure_workspace_initialized,
    ensure_safe_path,
    get_workspace_tree,
    WORKSPACE_ROOT,
    compile_knowledge,
)

logger = logging.getLogger("novelsmith.api.workspace")

router = APIRouter()


class FileWriteRequest(BaseModel):
    path: str
    content: str


class FileCreateRequest(BaseModel):
    path: str
    is_directory: bool = False
    content: str = ""


@router.get("/knowledge")
async def get_knowledge() -> dict[str, Any]:
    """Compile and return character, world, outline, etc. dynamically."""
    try:
        return compile_knowledge()
    except Exception as e:
        logger.exception("Error compiling workspace knowledge")
        raise HTTPException(status_code=500, detail=f"编译知识库数据失败: {str(e)}")


@router.get("/tree")
async def get_tree() -> dict[str, Any]:
    """Get the nested file directory tree of the workspace."""
    try:
        return get_workspace_tree()
    except Exception as e:
        logger.exception("Error getting workspace tree")
        raise HTTPException(status_code=500, detail=f"获取工作区目录树失败: {str(e)}")


@router.get("/file")
async def get_file(path: str) -> dict[str, Any]:
    """Read a specific file or paired files in the workspace."""
    try:
        normalized_path = path.replace("\\", "/").strip("/")
        
        # Check if it's a paired character/world item
        if "knowledge/characters/" in normalized_path or "knowledge/world/" in normalized_path:
            p = Path(normalized_path)
            base_name = p.stem
            parent_dir = p.parent
            
            md_rel_path = f"{parent_dir}/{base_name}.md"
            md_safe_path = ensure_safe_path(md_rel_path)
            
            from app.services.workspace_manager import parse_yaml_front_matter
            
            metadata = {}
            body = ""
            if md_safe_path.exists():
                md_text = md_safe_path.read_text(encoding="utf-8")
                metadata, body = parse_yaml_front_matter(md_text)
                
            return {
                "path": normalized_path,
                "type": "paired",
                "pairedPath": {
                    "json": f"{parent_dir}/{base_name}.md",
                    "md": f"{parent_dir}/{base_name}.md"
                },
                "content": {
                    "json": metadata,
                    "md": body
                }
            }

        safe_path = ensure_safe_path(path)
        if not safe_path.exists():
            raise HTTPException(status_code=404, detail=f"文件不存在: {path}")
        if safe_path.is_dir():
            raise HTTPException(status_code=400, detail=f"该路径是目录，不是文件: {path}")

        content_str = safe_path.read_text(encoding="utf-8")

        # If it's a JSON file, parse it and return parsed object, otherwise return string
        is_json = safe_path.suffix.lower() == ".json"
        if is_json:
            try:
                parsed_json = json.loads(content_str)
                return {"path": path, "content": parsed_json, "type": "json"}
            except json.JSONDecodeError:
                return {"path": path, "content": content_str, "type": "text"}
        
        return {"path": path, "content": content_str, "type": "text"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error reading file {path}")
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")


@router.post("/file")
async def write_file(payload: FileWriteRequest) -> dict[str, Any]:
    """Write content back to a file or paired files in the workspace."""
    try:
        normalized_path = payload.path.replace("\\", "/").strip("/")
        
        # Check if payload content is a paired JSON structure
        is_paired_write = False
        content_obj = None
        if isinstance(payload.content, str):
            try:
                content_obj = json.loads(payload.content)
                if isinstance(content_obj, dict) and "json" in content_obj and "md" in content_obj:
                    is_paired_write = True
            except Exception:
                pass
        else:
            content_obj = payload.content
            if isinstance(content_obj, dict) and "json" in content_obj and "md" in content_obj:
                is_paired_write = True
                
        if is_paired_write:
            p = Path(payload.path)
            base_name = p.stem
            parent_dir = p.parent
            
            md_rel_path = f"{parent_dir}/{base_name}.md"
            md_safe_path = ensure_safe_path(md_rel_path)
            md_safe_path.parent.mkdir(parents=True, exist_ok=True)
            
            from app.services.workspace_manager import serialize_yaml_front_matter
            
            metadata = content_obj["json"]
            body = content_obj["md"]
            
            serialized = serialize_yaml_front_matter(metadata, body)
            md_safe_path.write_text(serialized, encoding="utf-8")
            
            # Clean up residual .json file on disk if it exists
            json_rel_path = f"{parent_dir}/{base_name}.json"
            json_safe_path = ensure_safe_path(json_rel_path)
            if json_safe_path.exists():
                try:
                    json_safe_path.unlink()
                except Exception as e:
                    logger.warning(f"Failed to remove residual JSON file {json_rel_path}: {e}")
                    
            logger.info(f"YAML front-matter file written successfully: {md_rel_path}")
            return {"ok": True, "message": "保存属性与描述成功！"}

        # If it is a write to characters/world settings but not structured as paired
        if "knowledge/characters/" in normalized_path or "knowledge/world/" in normalized_path:
            p = Path(normalized_path)
            base_name = p.stem
            parent_dir = p.parent
            md_rel_path = f"{parent_dir}/{base_name}.md"
            md_safe_path = ensure_safe_path(md_rel_path)
            
            from app.services.workspace_manager import parse_yaml_front_matter, serialize_yaml_front_matter
            
            # If writing to .json file path (intercept)
            if normalized_path.endswith(".json"):
                try:
                    metadata = json.loads(payload.content) if isinstance(payload.content, str) else payload.content
                except Exception:
                    metadata = {}
                
                existing_body = ""
                if md_safe_path.exists():
                    try:
                        _, existing_body = parse_yaml_front_matter(md_safe_path.read_text(encoding="utf-8"))
                    except Exception:
                        pass
                
                serialized = serialize_yaml_front_matter(metadata, existing_body)
                md_safe_path.write_text(serialized, encoding="utf-8")
                
                # Delete old json if exists
                json_safe_path = ensure_safe_path(normalized_path)
                if json_safe_path.exists():
                    json_safe_path.unlink()
                
                return {"ok": True, "message": "已转换并更新设定卡的 Front-matter 元数据！"}
                
            # If writing to .md file path directly, merge with existing front-matter if new content doesn't have it
            elif normalized_path.endswith(".md"):
                content_str = payload.content if isinstance(payload.content, str) else json.dumps(payload.content)
                if not content_str.strip().startswith("---") and md_safe_path.exists():
                    try:
                        existing_text = md_safe_path.read_text(encoding="utf-8")
                        existing_meta, _ = parse_yaml_front_matter(existing_text)
                        if existing_meta:
                            content_str = serialize_yaml_front_matter(existing_meta, content_str)
                    except Exception as e:
                        logger.warning(f"Failed to merge existing front-matter on direct md write: {e}")
                
                md_safe_path.write_text(content_str, encoding="utf-8")
                return {"ok": True, "message": "写入文件成功！"}

        safe_path = ensure_safe_path(payload.path)
        if safe_path.is_dir():
            raise HTTPException(status_code=400, detail=f"目标路径是目录，无法写入文件: {payload.path}")

        safe_path.parent.mkdir(parents=True, exist_ok=True)

        content = payload.content
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False, indent=2)

        safe_path.write_text(content, encoding="utf-8")
        logger.info(f"File written successfully: {payload.path}")
        return {"ok": True, "message": "写入文件成功！"}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.exception(f"Error writing to file {payload.path}")
        raise HTTPException(status_code=500, detail=f"保存文件失败: {str(e)}")


@router.post("/create")
async def create_node(payload: FileCreateRequest) -> dict[str, Any]:
    """Create a new file or directory in the workspace."""
    try:
        safe_path = ensure_safe_path(payload.path)
        if safe_path.exists():
            raise HTTPException(status_code=400, detail=f"路径已存在，无法创建: {payload.path}")

        if payload.is_directory:
            safe_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Directory created: {payload.path}")
            return {"ok": True, "message": "新建目录成功！"}
        else:
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            safe_path.write_text(payload.content, encoding="utf-8")
            logger.info(f"File created: {payload.path}")
            return {"ok": True, "message": "新建文件成功！"}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.exception(f"Error creating node {payload.path}")
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.delete("/file")
async def delete_node(path: str) -> dict[str, Any]:
    """Delete a file or directory from the workspace."""
    try:
        # Check if we should delete paired knowledge files
        normalized_path = path.replace("\\", "/").strip("/")
        if "knowledge/characters/" in normalized_path or "knowledge/world/" in normalized_path:
            p = Path(normalized_path)
            base_name = p.stem
            parent_dir = p.parent
            
            json_safe_path = ensure_safe_path(f"{parent_dir}/{base_name}.json")
            md_safe_path = ensure_safe_path(f"{parent_dir}/{base_name}.md")
            
            deleted = False
            if json_safe_path.exists():
                json_safe_path.unlink()
                deleted = True
            if md_safe_path.exists():
                md_safe_path.unlink()
                deleted = True
                
            if deleted:
                logger.info(f"Paired files deleted: {base_name}")
                return {"ok": True, "message": "删除成对的设定文件成功！"}

        safe_path = ensure_safe_path(path)
        if not safe_path.exists():
            raise HTTPException(status_code=404, detail=f"路径不存在: {path}")

        # Protect critical workspace files from deletion
        parts = Path(normalized_path).parts
        check_path = "/".join(parts[1:]) if len(parts) >= 2 else normalized_path
        if check_path in {"info.json", "knowledge", "chapters"}:
            raise HTTPException(status_code=403, detail="系统保护的根级目录或文件，不允许删除")

        if safe_path.is_dir():
            shutil.rmtree(safe_path)
            logger.info(f"Directory deleted: {path}")
            return {"ok": True, "message": "删除目录成功！"}
        else:
            safe_path.unlink()
            logger.info(f"File deleted: {path}")
            return {"ok": True, "message": "删除文件成功！"}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.exception(f"Error deleting path {path}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.post("/open-explorer")
async def open_explorer() -> dict[str, Any]:
    """Open the local workspace root directory in system file explorer."""
    try:
        import subprocess
        # On Windows, open explorer at WORKSPACE_ROOT
        subprocess.run(["explorer", str(WORKSPACE_ROOT)])
        return {"ok": True, "message": "已在资源管理器中打开工作区。"}
    except Exception as e:
        logger.exception("Failed to open file explorer")
        raise HTTPException(status_code=500, detail=f"打开资源管理器失败: {str(e)}")
