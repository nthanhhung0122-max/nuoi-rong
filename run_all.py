#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SUPERVISOR 24/7 - QUẢN LÝ ĐA TÀI KHOẢN TRÊN 1 RUNNER GITHUB ACTIONS DUY NHẤT
- Tiết kiệm 75% runner slot: Gộp tất cả tài khoản vào 1 máy ảo Ubuntu duy nhất.
- Độc lập 100%: Mỗi tài khoản là 1 tiến trình riêng biệt (Subprocess), crash acc này không ảnh hưởng acc khác.
- Tự động restart tài khoản con nếu gặp sự cố mạng hoặc crash.
- Log real-time có gắn tag [Acc 1], [Acc 2]...
- Tự động kích hoạt ca tiếp theo (Chaining Handover 24/7) khi sắp hết 5.5 tiếng.
"""

import sys
import os
import time
import json
import subprocess
import threading
import requests
from datetime import datetime

# Cấu hình danh sách tài khoản
DEFAULT_ACCOUNTS = [1, 2, 3, 4]
accounts_str = os.getenv("ACCOUNTS")
if accounts_str:
    ACCOUNTS = [int(x.strip()) for x in accounts_str.split(",") if x.strip()]
else:
    ACCOUNTS = DEFAULT_ACCOUNTS

SCRIPT_NAME = os.getenv("SCRIPT_NAME", "auto_khobaurong.py")
WORKFLOW_FILE = os.getenv("WORKFLOW_FILE", "khobaurong.yml")
REPO_NAME = os.getenv("GITHUB_REPOSITORY", "nthanhhung0122-max/nuoi-rong")
GH_PAT = (os.getenv("GH_PAT") or os.getenv("GITHUB_TOKEN") or "").strip()

IS_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"
MAX_RUNTIME = int(os.getenv("MAX_RUNTIME_SECONDS", "19800" if IS_GITHUB_ACTIONS else "0"))  # 5.5h = 19800s

stop_flag = False

def account_env(acc_id):
    """Bơm session/api_hash từ secret TELEGRAM_ACCOUNTS_JSON xuống tiến trình con."""
    raw = os.getenv("TELEGRAM_ACCOUNTS_JSON")
    if not raw:
        return {}
    try:
        accounts = json.loads(raw)["accounts"]
        acc = accounts[acc_id - 1]
    except (ValueError, KeyError, IndexError):
        log("SUPERVISOR", f"TELEGRAM_ACCOUNTS_JSON không đọc được hoặc thiếu Acc {acc_id}.")
        return {}
    return {
        f"TELEGRAM_STRING_SESSION_ACC{acc_id}": acc.get("session_str") or "",
        f"TELEGRAM_API_HASH_ACC{acc_id}": acc.get("api_hash") or "",
    }

def log(tag, msg):
    t = datetime.now().strftime("%H:%M:%S")
    print(f"[{t}] [{tag}] {msg}", flush=True)

def stream_logs(pipe, prefix):
    try:
        for line in iter(pipe.readline, ''):
            if line:
                print(f"{prefix} {line.rstrip()}", flush=True)
    except Exception:
        pass

def trigger_next_shift():
    """Tự động kích hoạt ca tiếp theo trên GitHub Actions để chạy 24/7 liên tục"""
    if not GH_PAT or not REPO_NAME or not WORKFLOW_FILE:
        log("CHAIN", "Bỏ qua kích hoạt ca tiếp theo (chạy local hoặc thiếu PAT/Repo).")
        return
    log("CHAIN", f"🚀 Đang kích hoạt ca tiếp theo ({WORKFLOW_FILE}) trên repo {REPO_NAME}...")
    try:
        url = f"https://api.github.com/repos/{REPO_NAME}/actions/workflows/{WORKFLOW_FILE}/dispatches"
        h = {
            "Authorization": f"Bearer {GH_PAT}",
            "Accept": "application/vnd.github.v3+json"
        }
        r = requests.post(url, headers=h, json={"ref": "main"}, timeout=15)
        if r.status_code == 204:
            log("CHAIN", f"✅ Kích hoạt ca tiếp theo thành công (HTTP 204)!")
        else:
            log("CHAIN", f"⚠️ Phản hồi kích hoạt: HTTP {r.status_code} - {r.text}")
    except Exception as e:
        log("CHAIN_ERR", f"Lỗi kích hoạt ca tiếp theo: {e}")

def run_account_worker(acc_id, procs_dict):
    """Giám sát và tự động khởi động lại tiến trình của từng tài khoản nếu gặp lỗi"""
    while not stop_flag:
        cmd = [sys.executable, SCRIPT_NAME, "--acc", str(acc_id)]
        log("SUPERVISOR", f"Khởi động tiến trình cho Acc {acc_id}: {' '.join(cmd)}")
        try:
            child_env = os.environ.copy()
            child_env["MAX_RUNTIME_SECONDS"] = "0"
            child_env["ACC_NUM"] = str(acc_id)
            child_env["PYTHONUNBUFFERED"] = "1"
            child_env["PYTHONIOENCODING"] = "utf-8"
            child_env.update(account_env(acc_id))

            p = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=child_env
            )
            procs_dict[acc_id] = p
            t = threading.Thread(target=stream_logs, args=(p.stdout, f"[Acc {acc_id}]"), daemon=True)
            t.start()

            p.wait()

            if stop_flag:
                break

            log("SUPERVISOR", f"⚠️ Tiến trình Acc {acc_id} đã kết thúc với mã {p.returncode}. Sẽ tự khởi động lại sau 10s...")
            time.sleep(10)
        except Exception as e:
            if stop_flag:
                break
            log("SUPERVISOR", f"Lỗi thực thi Acc {acc_id}: {e}. Thử lại sau 15s...")
            time.sleep(15)

def main():
    global stop_flag
    log("SUPERVISOR", f"============================================================")
    log("SUPERVISOR", f"BẮT ĐẦU CHẠY TẤT CẢ TÀI KHOẢN TRÊN 1 RUNNER GITHUB DUY NHẤT")
    log("SUPERVISOR", f"Script mục tiêu : {SCRIPT_NAME}")
    log("SUPERVISOR", f"Danh sách acc   : {ACCOUNTS}")
    log("SUPERVISOR", f"Thời gian tối đa: {MAX_RUNTIME} giây ({MAX_RUNTIME//3600}h {(MAX_RUNTIME%3600)//60}m)")
    log("SUPERVISOR", f"============================================================")

    start_time = time.time()
    procs = {}
    threads = []

    for acc in ACCOUNTS:
        t = threading.Thread(target=run_account_worker, args=(acc, procs), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(3)

    while True:
        try:
            elapsed = time.time() - start_time
            if MAX_RUNTIME > 0 and elapsed >= MAX_RUNTIME:
                log("SUPERVISOR", f"⏳ Đã hoàn thành thời gian ca trực ({int(elapsed)}s). Bàn giao ca tiếp theo...")
                stop_flag = True
                break
            time.sleep(15)
        except KeyboardInterrupt:
            log("SUPERVISOR", "Nhận tín hiệu dừng từ người dùng.")
            stop_flag = True
            break

    # Dừng các tiến trình con
    log("SUPERVISOR", "Đang dừng tất cả tiến trình con an toàn...")
    for acc, p in list(procs.items()):
        try:
            p.terminate()
        except Exception:
            pass

    time.sleep(3)
    for acc, p in list(procs.items()):
        try:
            p.kill()
        except Exception:
            pass

    # Kích hoạt ca tiếp theo
    trigger_next_shift()
    log("SUPERVISOR", "Đã hoàn thành toàn bộ công việc supervisor!")

if __name__ == "__main__":
    main()
