"""把 materials/ 下的讲义转成可直接上传 Dify 的纯文本版本（materials_v3/）。

为什么需要这一步：
Dify「通用分段」会自己解析 Markdown 结构（标题行、有序列表、表格），把本该
在一起的「标题 + 列表正文」拆成多个只有几字的分段，导致检索只召回空标题。
本脚本剥掉全部 Markdown 标记，并把同一段落内的换行压成空格，使 Dify 只能按
空行切段。

用法：
    python tools/build_knowledge_base_materials.py
"""
from __future__ import annotations

import glob
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "materials"
DST = ROOT / "materials_v3"

TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$")


def strip_line(line: str) -> str | None:
    """剥掉单行的 Markdown 标记，返回 None 表示该行应丢弃。"""
    text = line.rstrip()

    # 标题号：# / ## / ###
    text = re.sub(r"^\s*#{1,6}\s+", "", text)

    # 表格分隔行 |---|---|
    if TABLE_SEP.match(text):
        return None

    # 代码围栏
    if re.match(r"^\s*```", text):
        return None

    # Markdown 表格行 -> 单元格用两个空格连接
    if text.strip().startswith("|"):
        cells = [c.strip() for c in text.strip().strip("|").split("|")]
        text = "  ".join(c for c in cells if c)

    # 无序列表前缀
    text = re.sub(r"^\s*[-*+]\s+", "", text)
    # 有序列表前缀（1. / 1) / 1、），不误伤 4.1 这类章节号
    text = re.sub(r"^\s*\d+[.)、]\s+", "", text)

    # 强调、行内代码、链接、引用
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^\s*>\s?", "", text)

    return text


HEADING = re.compile(r"^\s{0,3}#{1,3}\s+(.+?)\s*#*\s*$")


def convert(text: str) -> str:
    """Markdown -> 纯文本：按标题分节，一节一段，段内换行压成空格。

    标题开新节，节内所有行（含跨空行的正文、列表、表格）都并入同一段，
    直到遇到下一个标题。这样「学习目标 + 6 条列表」不会被 Dify 拆开。
    """
    paragraphs: list[str] = []
    buffer: list[str] = []

    def flush() -> None:
        if not buffer:
            return
        merged = "  ".join(buffer)
        paragraphs.append(re.sub(r" {3,}", "  ", merged).strip())
        buffer.clear()

    for raw in text.split("\n"):
        heading = HEADING.match(raw)
        if heading:
            flush()
            buffer.append(heading.group(1).strip())
            continue
        if not raw.strip():
            continue
        cleaned = strip_line(raw)
        if cleaned is None or not cleaned.strip():
            continue
        buffer.append(cleaned.strip())
    flush()

    return "\n\n".join(p for p in paragraphs if p)


def main() -> None:
    DST.mkdir(exist_ok=True)
    for path in sorted(glob.glob(str(SRC / "*.md"))):
        src = Path(path)
        out = convert(src.read_text(encoding="utf-8"))
        (DST / src.name).write_text(out, encoding="utf-8")

        paras = [p for p in out.split("\n\n") if p.strip()]
        lens = [len(p) for p in paras]
        has_hash = any(l.strip().startswith("#") for l in out.split("\n"))
        avg = sum(lens) // max(1, len(lens))
        print(
            f"{src.name}: {len(paras)} 段, 最短 {min(lens)}, 最长 {max(lens)}, "
            f"平均 {avg}, 残留 # {has_hash}"
        )


if __name__ == "__main__":
    main()
