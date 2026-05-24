import os
import json
import logging
from pathlib import Path

logger = logging.getLogger("novelsmith.workspace_manager")

WORKSPACE_ROOT = Path("G:/Codex/Curiosity/NovelSmith/workspace").resolve()


def ensure_safe_path(relative_path: str) -> Path:
    """Ensure path is resolved and is strictly inside the workspace root to prevent directory traversal."""
    resolved_path = (WORKSPACE_ROOT / relative_path.strip("/\\")).resolve()
    if not resolved_path.is_relative_to(WORKSPACE_ROOT):
        raise ValueError(f"Access denied: Path '{relative_path}' is outside the workspace root.")
    return resolved_path

def parse_yaml_front_matter(content: str) -> tuple[dict, str]:
    """Parse YAML front matter from markdown content and return metadata dict and markdown body."""
    import re
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        return {}, content

    yaml_block = match.group(1)
    body = match.group(2)
    
    metadata = {}
    for line in yaml_block.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip()
        
        # Parse list, e.g. tags: [A, B]
        if val.startswith("[") and val.endswith("]"):
            items = [item.strip() for item in val[1:-1].split(",") if item.strip()]
            metadata[key] = items
        else:
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            else:
                try:
                    val = int(val)
                except ValueError:
                    try:
                        val = float(val)
                    except ValueError:
                        if val.lower() == "true":
                            val = True
                        elif val.lower() == "false":
                            val = False
                        elif val.lower() in ("null", "none", ""):
                            val = None
            metadata[key] = val
    return metadata, body


def serialize_yaml_front_matter(metadata: dict, body: str) -> str:
    """Serialize metadata dict and markdown body into a single string with YAML front matter."""
    yaml_lines = ["---"]
    for key, val in metadata.items():
        if isinstance(val, list):
            list_str = ", ".join(str(item) for item in val)
            yaml_lines.append(f"{key}: [{list_str}]")
        elif isinstance(val, bool):
            yaml_lines.append(f"{key}: {str(val).lower()}")
        elif isinstance(val, (int, float)):
            yaml_lines.append(f"{key}: {val}")
        elif val is None:
            yaml_lines.append(f"{key}: null")
        else:
            # Ensure it is single line and escape quotes if needed
            val_str = str(val).replace("\n", " ")
            yaml_lines.append(f"{key}: {val_str}")
    yaml_lines.append("---")
    yaml_lines.append(body.lstrip())
    return "\n".join(yaml_lines)


def get_book_dir() -> Path:
    """Get the active book directory inside the workspace root.
    If none exist, returns default Path (WORKSPACE_ROOT / '雾城档案').
    """
    if WORKSPACE_ROOT.exists():
        for entry in os.scandir(WORKSPACE_ROOT):
            if entry.is_dir() and not entry.name.startswith("."):
                sub_dir = Path(entry.path)
                if (sub_dir / "info.json").exists():
                    return sub_dir
    return WORKSPACE_ROOT / "雾城档案"


def init_workspace():
    """Initialize the default workspace files if they do not exist."""
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)

    # 1. 自动迁移检测：若 info.json 存在于根目录，将旧版数据搬迁到书名子目录下
    old_info_path = WORKSPACE_ROOT / "info.json"
    if old_info_path.exists():
        logger.info("Detect old workspace files in root, starting migration...")
        book_title = "雾城档案"
        try:
            info_data = json.loads(old_info_path.read_text(encoding="utf-8"))
            if isinstance(info_data, dict) and info_data.get("title"):
                book_title = info_data["title"].strip()
        except Exception as e:
            logger.warning(f"Failed to read title from old info.json: {e}")

        # 创建目标子目录
        target_dir = WORKSPACE_ROOT / book_title
        target_dir.mkdir(exist_ok=True)

        # 迁移旧的文件/目录
        items_to_move = ["info.json", "chapters", "knowledge"]
        import shutil
        for item in items_to_move:
            src = WORKSPACE_ROOT / item
            if src.exists():
                dst = target_dir / item
                try:
                    if dst.exists():
                        if src.is_dir():
                            shutil.rmtree(dst)
                            shutil.move(str(src), str(dst))
                        else:
                            src.unlink()
                    else:
                        shutil.move(str(src), str(dst))
                    logger.info(f"Migrated: {item} -> {target_dir.name}/{item}")
                except Exception as ex:
                    logger.error(f"Failed to migrate {item}: {ex}")

    # 获取当前书籍的目录进行初始化
    book_dir = get_book_dir()
    book_dir.mkdir(parents=True, exist_ok=True)

    # 1. info.json
    info_path = book_dir / "info.json"
    if not info_path.exists():
        info_data = {
            "title": "雾城档案",
            "brief": "长篇连载悬疑小说。近未来都市，主线围绕雾城档案、失忆调查员与灰塔组织展开。"
        }
        info_path.write_text(json.dumps(info_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2. chapters/
    chapters_dir = book_dir / "chapters"
    chapters_dir.mkdir(exist_ok=True)

    
    default_chapters = [
        ("01_第一章：雾中来信.md", "三年前在执行雾城灰塔调查任务时失踪，苏醒后丧失了全部记忆。\n只留下口袋里一封盖有灰塔印章的未寄出信件。\n\n林藏站在窗前，看着落入黑色海水的雨水，思绪如雨雾般散乱。\n这封信，会是找到过去的钥匙吗？"),
        ("02_第二章：雾城的规则.md", "雾城没有阳光，或者说，阳光被上空的灰幕彻底滤成了冷灰色。\n在这里，只有三条规则：不要打听灰塔的命令、不要在浓雾漫上街道时外出、不要相信任何失忆者。\n\n林藏走在潮湿的街头，苏黎给他的档案袋沉甸甸地贴在胸口。"),
        ("03_第三章：灰塔的影子.md", "影子在墙壁上拉长，呈现出怪异的折角。\n夜枭靠着路灯，手里玩弄着一枚黄铜打火机。\n\n“你终于来了，”夜枭的声音沙哑，“失忆的调查员先生。”")
    ]
    for filename, content in default_chapters:
        c_path = chapters_dir / filename
        if not c_path.exists():
            c_path.write_text(content, encoding="utf-8")

    # 3. knowledge/
    knowledge_dir = book_dir / "knowledge"
    knowledge_dir.mkdir(exist_ok=True)

    # 3a. characters/
    chars_dir = knowledge_dir / "characters"
    chars_dir.mkdir(parents=True, exist_ok=True)
    
    characters_data = [
        ("林藏", {
            "name": "林藏",
            "role": "主角",
            "tags": ["理性", "执着", "过去成谜"],
            "score": 24
        }, "# 角色卡：林藏\n\n失忆调查员，冷静理智，做事极其执着，唯一的线索是口袋里的信件。\n\n## 形象设定\n常穿一件深灰色风衣，目光深邃，习惯在思考时转动手上的旧铜扣。\n\n## 隐藏线索\n他脑部深处有灰塔植入的‘记忆阻断器’，当接近特定物理地点时，阻断器会发生电磁共振，从而碎片化恢复部分记忆。"),
        ("苏黎", {
            "name": "苏黎",
            "role": "盟友",
            "tags": ["冷静", "清醒", "守护秘密"],
            "score": 18
        }, "# 角色卡：苏黎\n\n雾城档案保管员，灰塔组织边缘成员。暗中帮助林藏寻找记忆，似乎知道林藏的过去，但因为某种誓言无法直接透露。\n\n## 形象设定\n戴金丝边眼镜，喜欢喝黑咖啡，办公桌上永远堆满古旧的纸质文件。"),
        ("夜枭", {
            "name": "夜枭",
            "role": "反派",
            "tags": ["神秘", "窥视", "目标不明"],
            "score": 32
        }, "# 角色卡：夜枭\n\n灰塔组织的高级联络员。林藏失踪事件的知情者之一，以戏谑和恐吓的手段试探林藏，试图阻止其找回记忆。")
    ]
    for name, meta, md_text in characters_data:
        md_path = chars_dir / f"{name}.md"
        needs_write_md = True
        if md_path.exists():
            try:
                content = md_path.read_text(encoding="utf-8").strip()
                if content:
                    needs_write_md = False
            except Exception:
                pass
        if needs_write_md:
            md_content = serialize_yaml_front_matter(meta, md_text)
            md_path.write_text(md_content, encoding="utf-8")

    # 3b. world/
    world_dir = knowledge_dir / "world"
    world_dir.mkdir(parents=True, exist_ok=True)
    
    world_data = [
        ("雾城C区", {
            "title": "雾城C区",
            "type": "地理"
        }, "# 设定：雾城C区\n\n常年被浓雾笼罩的沿海都市，权力分割混乱。地下管线错综复杂，是灰塔暗中进行实验的主要场所。"),
        ("灰塔组织", {
            "title": "灰塔组织",
            "type": "组织"
        }, "# 设定：灰塔组织\n\n掌控情报与秩序的隐秘组织，信仰“秩序即正义”。利用城市广播和电磁阻断系统牢牢控制市民的思想。")
    ]
    for title, meta, md_text in world_data:
        md_path = world_dir / f"{title}.md"
        needs_write_md = True
        if md_path.exists():
            try:
                content = md_path.read_text(encoding="utf-8").strip()
                if content:
                    needs_write_md = False
            except Exception:
                pass
        if needs_write_md:
            md_content = serialize_yaml_front_matter(meta, md_text)
            md_path.write_text(md_content, encoding="utf-8")

    # 3c. timeline, threads, outline JSON files
    timeline_path = knowledge_dir / "timeline.json"
    if not timeline_path.exists():
        timeline_data = [
            "三年前",
            "第一次调查中失踪，记忆自此断裂。",
            "第一卷",
            "灰塔组织收紧控制，雾城局势暗流涌动。",
            "Chapter 01"
        ]
        timeline_path.write_text(json.dumps(timeline_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # Clean up old json files if any
    for name, _, _ in characters_data:
        json_path = chars_dir / f"{name}.json"
        if json_path.exists():
            try:
                json_path.unlink()
            except Exception:
                pass
    for title, _, _ in world_data:
        json_path = world_dir / f"{title}.json"
        if json_path.exists():
            try:
                json_path.unlink()
            except Exception:
                pass

    threads_path = knowledge_dir / "threads.json"
    if not threads_path.exists():
        threads_data = [
            { "title": "未来来信", "desc": "来自未来的警告不断改变林藏的行动选择。" },
            { "title": "种子名单", "desc": "灰塔隐藏的核心名单，牵动失忆与城市权限。" },
            { "title": "重启记忆协议", "desc": "部分线索会在关键节点自动触发记忆恢复。" }
        ]
        threads_path.write_text(json.dumps(threads_data, ensure_ascii=False, indent=2), encoding="utf-8")

    outline_path = knowledge_dir / "outline.json"
    if not outline_path.exists():
        outline_data = {
            "volume": "第一卷：迷雾初起",
            "chapters": [
                "Chapter 01　第一章：雾中来信",
                "Chapter 02　雾城的规则",
                "Chapter 03　灰塔的影子"
            ]
        }
        outline_path.write_text(json.dumps(outline_data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_workspace_tree() -> dict:
    """Scan the workspace directory and return a nested tree representation."""
    ensure_workspace_initialized()
    
    def scan_dir(path: Path) -> list:
        nodes = []
        for entry in os.scandir(path):
            entry_path = Path(entry.path)
            rel_path = str(entry_path.relative_to(WORKSPACE_ROOT)).replace("\\", "/")
            if entry.is_dir():
                nodes.append({
                    "name": entry.name,
                    "type": "directory",
                    "path": rel_path,
                    "children": scan_dir(entry_path)
                })
            else:
                nodes.append({
                    "name": entry.name,
                    "type": "file",
                    "path": rel_path,
                    "size": entry.stat().st_size
                })
        # Sort directories first, then files
        nodes.sort(key=lambda x: (0 if x["type"] == "directory" else 1, x["name"].lower()))
        return nodes

    return {
        "name": "workspace",
        "type": "directory",
        "path": "",
        "children": scan_dir(WORKSPACE_ROOT)
    }


def ensure_workspace_initialized():
    """Ensure the workspace files exist, initialize if not."""
    init_workspace()


def compile_knowledge() -> dict:
    """Compile character, world, timeline, threads, outline, and chapters data from the workspace."""
    ensure_workspace_initialized()
    
    book_dir = get_book_dir()
    book_name = book_dir.name

    # 1. compile characters
    characters = []
    chars_dir = book_dir / "knowledge" / "characters"
    if chars_dir.exists():
        # find all .md files
        for entry in os.scandir(chars_dir):
            if entry.is_file() and entry.name.endswith(".md"):
                name = entry.name[:-3]
                md_path = Path(entry.path)
                
                # read md
                meta = {}
                desc = ""
                try:
                    md_text = md_path.read_text(encoding="utf-8")
                    meta, body = parse_yaml_front_matter(md_text)
                    
                    # Extract first meaningful text line as description (skipping title and empty lines)
                    for line in body.splitlines():
                        line_strip = line.strip()
                        if line_strip and not line_strip.startswith("#"):
                            desc = line_strip[:60]
                            if len(line_strip) > 60:
                                desc += "..."
                            break
                except Exception as e:
                    logger.warning(f"Failed to read md character: {entry.name}, error: {e}")
                
                characters.append({
                    "name": meta.get("name", name),
                    "role": meta.get("role", "无"),
                    "desc": desc or "暂无设定描述。",
                    "tags": meta.get("tags", []),
                    "score": meta.get("score", 0),
                    "path": f"{book_name}/knowledge/characters/{name}.md"
                })
                
    # 2. compile worldSettings
    world_settings = []
    world_dir = book_dir / "knowledge" / "world"
    if world_dir.exists():
        for entry in os.scandir(world_dir):
            if entry.is_file() and entry.name.endswith(".md"):
                title = entry.name[:-3]
                md_path = Path(entry.path)
                
                meta = {}
                desc = ""
                try:
                    md_text = md_path.read_text(encoding="utf-8")
                    meta, body = parse_yaml_front_matter(md_text)
                    
                    for line in body.splitlines():
                        line_strip = line.strip()
                        if line_strip and not line_strip.startswith("#"):
                            desc = line_strip[:60]
                            if len(line_strip) > 60:
                                desc += "..."
                            break
                except Exception as e:
                    logger.warning(f"Failed to read md world setting: {entry.name}, error: {e}")
                        
                world_settings.append({
                    "title": meta.get("title", title),
                    "type": meta.get("type", "设定"),
                    "desc": desc or "暂无详细设定描述。",
                    "path": f"{book_name}/knowledge/world/{title}.md"
                })

    # 3. timeline
    timeline = []
    timeline_path = book_dir / "knowledge" / "timeline.json"
    if timeline_path.exists():
        try:
            timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Failed to read timeline.json: {e}")
            
    # 4. threads (threadCards)
    thread_cards = []
    threads_path = book_dir / "knowledge" / "threads.json"
    if threads_path.exists():
        try:
            thread_cards = json.loads(threads_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Failed to read threads.json: {e}")
            
    # 5. outline
    outline = {"volume": "大纲", "chapters": []}
    outline_path = book_dir / "knowledge" / "outline.json"
    if outline_path.exists():
        try:
            outline = json.loads(outline_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Failed to read outline.json: {e}")
            
    # 6. chapters
    chapters = []
    chapters_dir = book_dir / "chapters"
    if chapters_dir.exists():
        for entry in os.scandir(chapters_dir):
            if entry.is_file() and entry.name.endswith(".md"):
                chapters.append(entry.name)
        # Sort chapters naturally
        chapters.sort()
        
    return {
        "bookName": book_name,
        "characters": characters,
        "worldSettings": world_settings,
        "timeline": timeline,
        "threadCards": thread_cards,
        "outline": outline,
        "chapters": chapters
    }

