# -*- coding: utf-8 -*-
"""
Brain 集群 — 流水线编排引擎 (Pipeline Orchestrator)
监听 kanban.db, 自动串联: 执行→审查→仲裁→完成
"""
import sqlite3, subprocess, os, time, json
from datetime import datetime

KANBAN_DB = r"D:\brain\output\memory\kanban.db"
POLL_INTERVAL = 30  # 每30秒扫描一次

EXECUTORS = ["executor-a", "executor-b", "executor-c"]
REVIEWERS = ["reviewer-strict", "reviewer-creative"]

def get_done_tasks_without_review():
    """找出已完成但未审查的executor任务"""
    conn = sqlite3.connect(KANBAN_DB)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT id, title, assignee, result 
            FROM tasks 
            WHERE status='done' 
              AND assignee IN ('executor-a','executor-b','executor-c')
              AND id NOT IN (
                  SELECT DISTINCT json_extract(metadata, '$.parent') 
                  FROM tasks 
                  WHERE json_extract(metadata, '$.parent') IS NOT NULL
              )
            ORDER BY completed_at DESC
            LIMIT 10
        """)
    except Exception:
        cursor.execute("SELECT id, title, assignee FROM tasks WHERE status='done' LIMIT 5")
    
    tasks = [{"id": r[0], "title": r[1], "assignee": r[2]} for r in cursor.fetchall()]
    conn.close()
    return tasks

def create_review_tasks(executor_task):
    """为executor产出创建双审任务"""
    task_id = executor_task["id"]
    title = executor_task["title"]
    
    created = []
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = "sk-xGSsFRUlKUXduzjnwPK4m9J7eNmmVTRwraXROi0dhPiRTvP8"
    env["OPENAI_BASE_URL"] = "https://tokenshengsheng.com/v1"
    
    for reviewer in REVIEWERS:
        review_title = f"REVIEW[{reviewer}]: {title} (parent: {task_id})"
        r = subprocess.run(
            ["hermes", "kanban", "create", review_title, "--assignee", reviewer],
            capture_output=True, text=True, env=env, timeout=30
        )
        if "Created" in r.stdout:
            review_id = r.stdout.split()[-2] if len(r.stdout.split()) >= 2 else None
            created.append({"reviewer": reviewer, "id": review_id})
            print(f"  created review: {reviewer} → {review_id}")
    
    return created

def check_review_results(review_task_ids):
    """检查双审结果，分歧时触发仲裁"""
    conn = sqlite3.connect(KANBAN_DB)
    cursor = conn.cursor()
    scores = {}
    
    for r in review_task_ids:
        cursor.execute("SELECT status, result FROM tasks WHERE id=?", (r["id"],))
        row = cursor.fetchone()
        if row and row[0] == "done":
            try:
                result = json.loads(row[1]) if row[1] else {"total": 50}
            except:
                result = {"total": 50}
            scores[r["reviewer"]] = result.get("total", 50)
    
    conn.close()
    
    if len(scores) < 2:
        return False  # 审查未完成
    
    strict_score = scores.get("reviewer-strict", 50)
    creative_score = scores.get("reviewer-creative", 50)
    
    strict_pass = strict_score >= 60
    creative_pass = creative_score >= 50
    
    if strict_pass and creative_pass:
        print(f"  dual review PASS: strict={strict_score}, creative={creative_score}")
        return "pass"
    elif not strict_pass and not creative_pass:
        print(f"  dual review FAIL: strict={strict_score}, creative={creative_score}")
        return "fail"
    else:
        print(f"  dual review SPLIT: strict={strict_score}, creative={creative_score}")
        return "split"

def create_arbiter_task(parent_id, scores):
    """创建仲裁任务"""
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = "sk-xGSsFRUlKUXduzjnwPK4m9J7eNmmVTRwraXROi0dhPiRTvP8"
    env["OPENAI_BASE_URL"] = "https://tokenshengsheng.com/v1"
    
    title = f"ARBITER: split decision on {parent_id} (strict:{scores.get('reviewer-strict')} vs creative:{scores.get('reviewer-creative')})"
    r = subprocess.run(
        ["hermes", "kanban", "create", title, "--assignee", "arbiter"],
        capture_output=True, text=True, env=env, timeout=30
    )
    print(f"  created arbiter: {r.stdout[:60].strip()}")

def run_once():
    """一次扫描周期"""
    ts = datetime.now().strftime("%H:%M:%S")
    
    tasks = get_done_tasks_without_review()
    if tasks:
        print(f"\n[{ts}] Found {len(tasks)} done tasks without review")
        for task in tasks[:3]:  # 每次最多处理3个
            print(f"  Processing: {task['id']} by {task['assignee']}")
            created = create_review_tasks(task)
            if created:
                time.sleep(2)
    
    # 检查已有的审查任务
    conn = sqlite3.connect(KANBAN_DB)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, title, status FROM tasks 
            WHERE title LIKE 'REVIEW%' AND status='done'
            ORDER BY completed_at DESC LIMIT 10
        """)
    except:
        cursor.execute("SELECT id, title, status FROM tasks WHERE title LIKE 'REVIEW%' AND status='done'")
    
    review_tasks = cursor.fetchall()
    conn.close()

def run_daemon():
    """持续运行"""
    print("Pipeline Orchestrator started (30s interval)")
    try:
        while True:
            run_once()
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\nOrchestrator stopped.")

def run_once_and_exit():
    """执行一次后退出 (用于cron)"""
    run_once()

if __name__ == "__main__":
    import sys
    if "--daemon" in sys.argv:
        run_daemon()
    else:
        run_once_and_exit()
        print("Done.")
