#!/usr/bin/env python3
"""校验 guide 里所有源码锚点 (file:line) 是否仍指向真实存在的文件与有效行号。

guide 大量引用 hermes-agent 源码的 `path.py:123`。源码演进会让行号漂移、
文件重命名，这些引用会悄悄过时。本脚本是**开发期校验工具**（非运行时依赖）：
解析 part*.py 里的所有锚点，去源码仓库逐一验证。

用法:
    python3 check_anchors.py [SRC_ROOT]
    SRC_ROOT 默认 ../../hermes-agent（可用环境变量 HERMES_SRC 覆盖）

退出码: 0 = 全部解析成功; 1 = 有失效锚点（缺文件 / 行号越界）。
源码不可达时打印提示并退出 0（CI 无源码时不阻塞）。
"""
import os
import re
import sys
import glob
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SRC = os.environ.get(
    "HERMES_SRC",
    os.path.normpath(os.path.join(HERE, "..", "..", "hermes-agent")),
)

# path.py:123 或 path.py:123-456，扩展名限定为源码类型，避免误匹配 viewBox 等
ANCHOR_RE = re.compile(
    r"\b([\w./-]+\.(?:py|md|yaml|yml|tsx|ts|toml|cjs|json)):(\d+)(?:-(\d+))?\b"
)


def find_candidates(src_root: str, ref_path: str, _cache: dict) -> list:
    """返回锚点路径可能对应的源码文件列表（basename 可能多命中）。"""
    direct = os.path.join(src_root, ref_path)
    if os.path.isfile(direct):
        return [direct]
    base = os.path.basename(ref_path)
    if base not in _cache:
        _cache[base] = glob.glob(os.path.join(src_root, "**", base), recursive=True)
    hits = _cache[base]
    # 锚点带目录时优先后缀匹配的候选
    suffix = [h for h in hits if h.replace(src_root, "").lstrip("/").endswith(ref_path)]
    return suffix or hits


def main() -> int:
    src_root = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SRC
    if not os.path.isdir(src_root):
        print(f"[skip] 源码仓库不可达: {src_root}（设 HERMES_SRC 指向 hermes-agent）")
        return 0

    # 收集所有锚点：{(ref_path, line_start, line_end): [(guide_file, guide_line), ...]}
    anchors: dict = defaultdict(list)
    for gf in sorted(glob.glob(os.path.join(HERE, "part*.py"))):
        for i, line in enumerate(open(gf, encoding="utf-8"), 1):
            for m in ANCHOR_RE.finditer(line):
                ref, a, b = m.group(1), int(m.group(2)), m.group(3)
                anchors[(ref, a, int(b) if b else a)].append((os.path.basename(gf), i))

    fcache: dict = {}
    line_count: dict = {}
    missing_file: list = []
    out_of_range: list = []
    ok = 0

    def nlines(path: str) -> int:
        if path not in line_count:
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    line_count[path] = sum(1 for _ in fh)
            except OSError:
                line_count[path] = 0
        return line_count[path]

    for (ref, a, b), uses in sorted(anchors.items()):
        cands = find_candidates(src_root, ref, fcache)
        if not cands:
            missing_file.append((ref, a, b, uses))
            continue
        # 多个同名文件时用行号消歧：只要有一个候选行号在范围内就算有效
        if any(max(a, b) <= nlines(c) for c in cands):
            ok += 1
        else:
            longest = max(nlines(c) for c in cands)
            out_of_range.append((ref, a, b, longest, uses))

    total = len(anchors)
    print(f"=== 锚点校验：源码 {src_root} ===")
    print(f"唯一锚点 {total} 个（{sum(len(u) for u in anchors.values())} 处引用）"
          f"｜文件+行号有效 {ok}｜缺文件 {len(missing_file)}｜行号越界 {len(out_of_range)}")

    if missing_file:
        print("\n[缺文件] guide 引用的源码文件找不到（可能已重命名/删除）：")
        for ref, a, b, uses in missing_file:
            where = ", ".join(f"{f}:{ln}" for f, ln in uses[:3])
            print(f"  {ref}:{a}{'-'+str(b) if b!=a else ''}  ←  {where}")

    if out_of_range:
        print("\n[行号越界] 行号超出当前文件长度（源码缩短/行号过时）：")
        for ref, a, b, n, uses in out_of_range:
            where = ", ".join(f"{f}:{ln}" for f, ln in uses[:3])
            print(f"  {ref}:{a}{'-'+str(b) if b!=a else ''} (文件仅 {n} 行)  ←  {where}")

    if not missing_file and not out_of_range:
        print("\n✓ 全部锚点的文件存在、行号在范围内。")
        print("  注：本脚本只校验「文件存在 + 行号有效」，不保证行号附近的符号未漂移；")
        print("  内容级准确性仍需人工/审计子代理抽查。")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
