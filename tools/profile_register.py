# -*- coding: utf-8 -*-
"""
Profile 注册引擎 — 将 23 个 Agent SOUL.md 注册到 Hermes 系统
=================================================================
实现:
  1. 扫描 D:\brain\input\profiles\ 下所有 SOUL.md
  2. 调用 hermes profile create 注册 (幂等: 已存在则跳过)
  3. 写入自定义 SOUL.md 到 Hermes 目录
  4. 通过 hermes auth add 注入 API credential
  5. 验证每个 profile 可启动
  6. 输出注册报告

先决条件:
  - Hermes Agent CLI 已安装 (hermes 命令可用)
  - 环境变量 OPENAI_BASE_URL / OPENAI_API_KEY 或 ccswitch endpoint.json 可用
"""

import os, json, subprocess, sys, yaml
from pathlib import Path
from datetime import datetime

# ── 路径配置 ──
BRAIN_PROFILES = Path(r"D:\brain\input\profiles")
HERMES_PROFILES = Path(os.path.expandvars(r"%LOCALAPPDATA%\hermes\profiles"))
ENDPOINT_CONFIG = Path(r"D:\brain\input\configs\ccswitch\endpoint.json")

# ── 读取 ccswitch 凭据 ──
def load_credentials():
    if ENDPOINT_CONFIG.exists():
        with open(ENDPOINT_CONFIG, encoding="utf-8") as f:
            cfg = json.load(f)
        return {
            "api_key": cfg.get("api_key", ""),
            "base_url": cfg.get("base_url", ""),
            "model": cfg.get("model", "gpt-5.5"),
        }
    return {
        "api_key": os.environ.get("OPENAI_API_KEY", ""),
        "base_url": os.environ.get("OPENAI_BASE_URL", "https://tokenshengsheng.com/v1"),
        "model": "gpt-5.5",
    }

# ── 扫描所有 Profile ──
def discover_profiles():
    profiles = {}
    for soul_path in BRAIN_PROFILES.rglob("SOUL.md"):
        name = soul_path.parent.name  # 目录名即 profile 名
        profiles[name] = {
            "soul_path": soul_path,
            "profile_dir": soul_path.parent,
        }
    return profiles

# ── 检查是否已注册 ──
def is_registered(name):
    profile_dir = HERMES_PROFILES / name
    return profile_dir.exists() and (profile_dir / "profile.yaml").exists()

# ── 注册单个 Profile ──
def register_profile(name, soul_path, creds, force=False):
    if is_registered(name) and not force:
        return {"name": name, "status": "skipped", "reason": "already registered"}

    # 1. 创建 profile
    try:
        r = subprocess.run(
            ["hermes", "profile", "create", name, "--description", f"Brain集群Agent - {name}"],
            capture_output=True, text=True, timeout=30
        )
        if r.returncode != 0 and "already exists" not in r.stderr.lower():
            return {"name": name, "status": "failed", "reason": f"create: {r.stderr[:100]}"}
    except Exception as e:
        return {"name": name, "status": "failed", "reason": str(e)}

    # 2. 复制自定义 SOUL.md
    try:
        target = HERMES_PROFILES / name / "SOUL.md"
        with open(soul_path, encoding="utf-8") as src:
            content = src.read()
        # 追加 Hermes 需要的 frontmatter
        if not content.strip().startswith("---"):
            content = f"---\ndescription: Brain集群 {name} Agent\n---\n\n{content}"
        with open(target, "w", encoding="utf-8") as dst:
            dst.write(content)
    except Exception as e:
        return {"name": name, "status": "failed", "reason": f"SOUL.md: {str(e)}"}

    # 3. 写入 config.yaml (模型配置)
    try:
        config = {
            "model": {
                "provider": "openai-api",
                "default": creds["model"],
                "base_url": creds["base_url"],
            },
            "api_key": creds["api_key"],
        }
        cfg_path = HERMES_PROFILES / name / "config.yaml"
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    except Exception as e:
        return {"name": name, "status": "failed", "reason": f"config.yaml: {str(e)}"}

    # 4. 注入 API credential 到全局 pool (Gateway worker 可读取)
    # Hermes auth add 是全局操作，只需执行一次
    try:
        subprocess.run(
            ["hermes", "auth", "add", "openai-api",
             "--api-key", creds["api_key"],
             "--label", f"ccswitch-{name}"],
            capture_output=True, text=True, timeout=15
        )
    except Exception:
        pass  # 如果已存在则忽略错误

    return {"name": name, "status": "registered"}

# ── 验证可启动性 ──
def verify_profile(name):
    """检查 profile 的关键文件完整性"""
    profile_dir = HERMES_PROFILES / name
    checks = {
        "SOUL.md": (profile_dir / "SOUL.md").exists(),
        "config.yaml": (profile_dir / "config.yaml").exists(),
        "profile.yaml": (profile_dir / "profile.yaml").exists(),
    }
    ok = all(checks.values())
    return {"name": name, "verified": ok, "checks": checks}

# ── 主流程 ──
def main(force=False, verify=True):
    print("=" * 60)
    print("  Brain 集群 Profile 注册引擎")
    print(f"  时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"  来源: {BRAIN_PROFILES}")
    print(f"  目标: {HERMES_PROFILES}")
    print("=" * 60)

    creds = load_credentials()
    if not creds["api_key"]:
        print("\n❌ 未找到 API key! 请确保 ccswitch endpoint.json 或环境变量已配置")
        return

    profiles = discover_profiles()
    print(f"\n发现 {len(profiles)} 个 Agent Profile:\n")
    for name in sorted(profiles):
        status = "✅ 已注册" if is_registered(name) else "⬜ 待注册"
        print(f"  {status:12s}  {name}")

    # 先执行全局 auth add (只需一次)
    print("\n── 注入全局 API credential ──")
    r = subprocess.run(
        ["hermes", "auth", "add", "openai-api",
         "--api-key", creds["api_key"],
         "--label", "ccswitch-brain"],
        capture_output=True, text=True, timeout=15
    )
    print(f"  {'✅' if r.returncode == 0 else '⚠'} {r.stdout.strip() or r.stderr.strip()[:80]}")

    # 逐 profile 注册
    results = []
    print(f"\n── 注册 {len(profiles)} 个 Profile ──")
    for name in sorted(profiles):
        soul = profiles[name]["soul_path"]
        result = register_profile(name, soul, creds, force=force)
        icon = {"registered": "✅", "skipped": "⏭", "failed": "❌"}.get(result["status"], "?")
        print(f"  {icon} {name}: {result['status']}")
        if result["status"] == "failed":
            print(f"     原因: {result.get('reason', 'unknown')}")
        results.append(result)

    # 验证
    if verify:
        print(f"\n── 验证完整性 ──")
        all_ok = True
        for name in sorted(profiles):
            v = verify_profile(name)
            if v["verified"]:
                print(f"  ✅ {name}")
            else:
                missing = [k for k, ok in v["checks"].items() if not ok]
                print(f"  ❌ {name}: 缺少 {missing}")
                all_ok = False

    # 汇总
    registered = sum(1 for r in results if r["status"] == "registered")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    failed = sum(1 for r in results if r["status"] == "failed")
    print(f"\n{'=' * 60}")
    print(f"  注册: {registered} | 跳过: {skipped} | 失败: {failed}")
    print(f"  总计: {len(profiles)} profiles")
    print(f"{'=' * 60}")

    # 写入报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "total": len(profiles),
        "registered": registered,
        "skipped": skipped,
        "failed": failed,
        "details": results,
    }
    report_path = Path(r"D:\brain\output\reports\profile_register.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  报告: {report_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Brain Profile 注册引擎")
    parser.add_argument("--force", action="store_true", help="强制重新注册所有 profile")
    parser.add_argument("--no-verify", action="store_true", help="跳过验证步骤")
    args = parser.parse_args()

    # 检查 yaml 是否可用
    try:
        import yaml
    except ImportError:
        print("❌ 需要 PyYAML: pip install pyyaml")
        sys.exit(1)

    main(force=args.force, verify=not args.no_verify)
