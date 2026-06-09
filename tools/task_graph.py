# -*- coding: utf-8 -*-
"""
Brain 集群 — Task Dependency Graph (任务依赖图)
功能: 基于 Hermes 原生 task_links 管理 parent->child 依赖关系，实现串行/并行编排
版本: v2.0.0 | 长期自主任务系统的核心组件
"""
import sqlite3, os, json, sys, subprocess, re
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import KANBAN_DB

EXECUTORS = ["executor-a", "executor-b", "executor-c"]
TASK_ID_RE = re.compile(r"\b(t_[a-f0-9]+)\b")
ROOT_TITLE_RE = re.compile(
    r"BATCH\[0/0\]: Generate (\d+) items in (\d+) styles \((\d+)/batch\)"
)


def _run_hermes_kanban(args, timeout=30):
    env = os.environ.copy()
    return subprocess.run(
        ["hermes", "kanban", *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )


def _extract_task_id(output):
    match = TASK_ID_RE.search(output or "")
    return match.group(1) if match else None


def _create_task(title, assignee=None, parents=None):
    args = ["create", title]
    if assignee:
        args.extend(["--assignee", assignee])
    for parent_id in parents or []:
        args.extend(["--parent", parent_id])
    result = _run_hermes_kanban(args)
    task_id = _extract_task_id(result.stdout)
    if not task_id:
        raise RuntimeError(f"Failed to create task: {title}\n{result.stderr.strip()}")
    return task_id


def _link_parent(parent_id, child_id):
    result = _run_hermes_kanban(["link", parent_id, child_id])
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to link {parent_id} -> {child_id}: {result.stderr.strip()}"
        )


def _complete_task(task_id, result_text):
    result = _run_hermes_kanban(["complete", task_id, "--result", result_text])
    if result.returncode != 0:
        raise RuntimeError(f"Failed to complete {task_id}: {result.stderr.strip()}")


def set_dependencies(task_id, depends_on):
    """为 task_id 设置依赖: 只有当 depends_on 列表中的任务全部 done 后才可派发
    Args:
        task_id: 当前任务ID
        depends_on: 依赖的任务ID列表
    """
    for parent_id in depends_on:
        _link_parent(parent_id, task_id)


def get_unresolved_dependencies(task_id):
    """返回 task_id 尚未完成的依赖任务列表"""
    conn = sqlite3.connect(KANBAN_DB, timeout=3)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.id
        FROM task_links l
        JOIN tasks p ON p.id = l.parent_id
        WHERE l.child_id = ?
          AND p.status NOT IN ('done', 'archived')
        ORDER BY p.id
    """, (task_id,))
    unresolved = [row[0] for row in cursor.fetchall()]
    conn.close()
    return unresolved


def is_ready(task_id):
    """检查任务是否可以派发（所有依赖已完成）"""
    return len(get_unresolved_dependencies(task_id)) == 0


def get_children(task_id):
    """获取所有子任务"""
    conn = sqlite3.connect(KANBAN_DB, timeout=3)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.id, t.title, t.status, t.assignee
        FROM task_links l
        JOIN tasks t ON t.id = l.child_id
        WHERE l.parent_id = ?
        ORDER BY t.created_at, t.id
    """, (task_id,))
    result = [
        {"id": row[0], "title": row[1], "status": row[2], "assignee": row[3]}
        for row in cursor.fetchall()
    ]
    conn.close()
    return result


def _collect_descendants(root_id):
    """收集 root_id 下的全部后代任务（去重）"""
    conn = sqlite3.connect(KANBAN_DB, timeout=3)
    cursor = conn.cursor()
    queue = [root_id]
    seen = set()
    descendants = []

    while queue:
        parent_id = queue.pop(0)
        cursor.execute("""
            SELECT t.id, t.title, t.status, t.assignee
            FROM task_links l
            JOIN tasks t ON t.id = l.child_id
            WHERE l.parent_id = ?
            ORDER BY t.created_at, t.id
        """, (parent_id,))
        for row in cursor.fetchall():
            child_id = row[0]
            if child_id in seen:
                continue
            seen.add(child_id)
            descendants.append({
                "id": row[0], "title": row[1], "status": row[2], "assignee": row[3]
            })
            queue.append(child_id)

    conn.close()
    return descendants


def build_batch_graph(total_items, batch_size, styles=None):
    """自动构建批次任务依赖图
    场景: "用N种风格写X篇文案"
    拆解: X篇 -> Y个批次, 每批 batch_size 篇, 批内并行, 批间串行
          styles: 风格列表 (如 ["种草风","干货风","故事风"])

    Returns:
        {"root_id": str, "batch_ids": [[...], ...], "dependency_map": {...}}
    """
    try:
        root_id = _create_task(
            f"BATCH[0/0]: Generate {total_items} items in {len(styles) if styles else 1} styles ({batch_size}/batch)",
            assignee="strategist",
        )
    except Exception as e:
        print(f"[TASKGRAPH] Failed to create root task: {e}")
        return None

    # 计算批次
    num_batches = (total_items + batch_size - 1) // batch_size
    all_batch_ids = []

    for batch_idx in range(num_batches):
        start = batch_idx * batch_size + 1
        end = min((batch_idx + 1) * batch_size, total_items)
        style_str = f" [{', '.join(styles)}]" if styles else ""
        batch_ids = []

        if styles:
            # 每批内每种风格并发
            for si, style in enumerate(styles):
                parents = [root_id] if batch_idx == 0 else all_batch_ids[batch_idx - 1]
                tid = _create_task(
                    f"BATCH[{batch_idx+1}/{num_batches}]: {style} items {start}-{end}",
                    assignee=EXECUTORS[si % len(EXECUTORS)],
                    parents=parents,
                )
                batch_ids.append(tid)
        else:
            parents = [root_id] if batch_idx == 0 else all_batch_ids[batch_idx - 1]
            tid = _create_task(
                f"BATCH[{batch_idx+1}/{num_batches}]: items {start}-{end}",
                assignee="executor-a",
                parents=parents,
            )
            batch_ids.append(tid)

        all_batch_ids.append(batch_ids)

    # root 任务只作为依赖起点，建图完成后立刻标记 done，释放第一批任务。
    _complete_task(root_id, "Task graph initialized")

    print(f"[TASKGRAPH] Built graph: {total_items} items -> {num_batches} batches x {len(styles) if styles else 1} styles")
    print(f"[TASKGRAPH] Root: {root_id}, Total tasks: {sum(len(b) for b in all_batch_ids)}")

    return {
        "root_id": root_id,
        "batches": all_batch_ids,
        "task_count": sum(len(b) for b in all_batch_ids),
    }


def get_progress(root_id):
    """获取任务树进度
    Returns:
        {"total_tasks": int, "done": int, "running": int, "pending": int,
         "blocked": int, "failed": int, "pct": float, "batches": [...]}
    """
    all_children = _collect_descendants(root_id)
    status_counts = {
        "triage": 0, "todo": 0, "scheduled": 0, "ready": 0,
        "running": 0, "blocked": 0, "done": 0, "archived": 0
    }
    for child in all_children:
        status = child["status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    total = sum(status_counts.values())
    pct = round(status_counts["done"] / total * 100, 1) if total > 0 else 0
    total_batches = 0
    total_items = 0
    batch_size = 0
    conn = sqlite3.connect(KANBAN_DB, timeout=3)
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM tasks WHERE id=?", (root_id,))
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        match = ROOT_TITLE_RE.search(row[0])
        if match:
            total_items = int(match.group(1))
            batch_size = int(match.group(3))
            total_batches = (total_items + batch_size - 1) // batch_size if batch_size else 0

    return {
        "root_id": root_id,
        "total_tasks": total,
        "done": status_counts["done"],
        "running": status_counts["running"],
        "todo": status_counts["todo"],
        "ready": status_counts["ready"],
        "scheduled": status_counts["scheduled"],
        "triage": status_counts["triage"],
        "blocked": status_counts["blocked"],
        "archived": status_counts["archived"],
        "completion_pct": pct,
        "total_batches": total_batches,
        "total_items": total_items,
    }


def print_tree(root_id, indent=0):
    """打印任务依赖树"""
    children = get_children(root_id)

    conn = sqlite3.connect(KANBAN_DB, timeout=3)
    cursor = conn.cursor()
    cursor.execute("SELECT title, status FROM tasks WHERE id=?", (root_id,))
    row = cursor.fetchone()
    conn.close()

    status = row[1] if row else "?"
    title = row[0] if row else str(root_id)
    prefix = "  " * indent
    icon = {
        "triage": "~", "todo": "-", "scheduled": "s", "ready": ">",
        "running": "*", "blocked": "!", "done": "+", "archived": "a"
    }.get(status, "?")
    print(f"{prefix}[{icon}] {title[:60]} ({status})")

    for child in children:
        print_tree(child["id"], indent + 1)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("USAGE: python task_graph.py <command> [args]")
        print("  build <total_items> <batch_size> [style1,style2,...]")
        print("    Example: python task_graph.py build 50 10 种草风,干货风,故事风")
        print("  progress <root_id>")
        print("    Example: python task_graph.py progress t_abc123")
        print("  tree <root_id>")
        print("  deps <task_id>    — check unresolved dependencies")
        print("  ready <task_id>   — check if task is ready to dispatch")
    else:
        cmd = sys.argv[1]
        if cmd == "build":
            total = int(sys.argv[2])
            batch = int(sys.argv[3])
            styles = sys.argv[4].split(",") if len(sys.argv) > 4 else None
            result = build_batch_graph(total, batch, styles)
            if result:
                print(f"\nRoot task ID: {result['root_id']}")
                print(f"Use: python task_graph.py progress {result['root_id']}")
        elif cmd == "progress":
            root_id = sys.argv[2]
            prog = get_progress(root_id)
            print(json.dumps(prog, ensure_ascii=False, indent=2))
        elif cmd == "tree":
            root_id = sys.argv[2]
            print_tree(root_id)
        elif cmd == "deps":
            task_id = sys.argv[2]
            unresolved = get_unresolved_dependencies(task_id)
            if unresolved:
                print(f"Unresolved dependencies for {task_id}: {unresolved}")
            else:
                print(f"All dependencies resolved for {task_id} — ready to dispatch")
        elif cmd == "ready":
            task_id = sys.argv[2]
            print(f"Task {task_id} is {'READY' if is_ready(task_id) else 'BLOCKED (pending dependencies)'}")
        else:
            print(f"Unknown command: {cmd}")
