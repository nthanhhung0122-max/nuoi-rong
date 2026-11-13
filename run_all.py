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

def _account_from_json(raw, acc_id):
    """Chuẩn hóa nhiều định dạng JSON phổ biến; không ghi log dữ liệu bí mật."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"TELEGRAM_ACCOUNTS_JSON không phải JSON hợp lệ (vị trí {exc.pos}).") from None

    def normalize(item):
        # Một số cấu hình lưu trực tiếp StringSession thành chuỗi.
        if isinstance(item, str):
            return {"session": item}
        if not isinstance(item, dict):
            raise ValueError(f"Cấu hình Acc {acc_id} phải là object hoặc chuỗi session.")

        # Hỗ trợ object lồng trong telegram/config/account.
        for nested_key in ("telegram", "config", "account", "credentials"):
            nested = item.get(nested_key)
            if isinstance(nested, dict):
                merged = dict(item)
                merged.update(nested)
                item = merged
                break
        return item

    if isinstance(data, list):
        if acc_id < 1 or len(data) < acc_id:
            raise ValueError(f"TELEGRAM_ACCOUNTS_JSON thiếu Acc {acc_id}.")
        return normalize(data[acc_id - 1])

    if not isinstance(data, dict):
        raise ValueError("TELEGRAM_ACCOUNTS_JSON phải là object hoặc mảng.")

    # Dạng {"accounts": [...]} hoặc {"accounts": {"1": ...}}
    accounts = data.get("accounts")
    if isinstance(accounts, list):
        if acc_id < 1 or len(accounts) < acc_id:
            raise ValueError(f"TELEGRAM_ACCOUNTS_JSON thiếu Acc {acc_id}.")
        return normalize(accounts[acc_id - 1])
    if isinstance(accounts, dict):
        data = accounts

    # Dạng {"1": {...}}, {"acc1": "session"}, {"ACC1": {...}}
    keys = (
        str(acc_id), f"acc{acc_id}", f"ACC{acc_id}",
        f"account{acc_id}", f"Account{acc_id}",
        f"account_{acc_id}", f"acc_{acc_id}"
    )
    for key in keys:
        if key in data:
            return normalize(data[key])

    # Dạng object đơn của một tài khoản.
    session_keys = (
        "session_str", "string_session", "session", "sessionString",
        "stringSession", "session_b64", "session_base64"
    )
    if any(k in data for k in session_keys):
        return normalize(data)

    raise ValueError(
        "Không tìm thấy Acc trong TELEGRAM_ACCOUNTS_JSON. "
        "Hỗ trợ khóa 1/acc1/account1, mảng accounts hoặc object tài khoản đơn."
    )


def account_env(acc_id):
    """Lấy cấu hình Telegram cho tiến trình con; không bao giờ in session/API hash."""
    raw = (os.getenv("TELEGRAM_ACCOUNTS_JSON") or "").strip()
    session = ""
    api_hash = ""

    if raw:
        item = _account_from_json(raw, acc_id)
        session = (
            item.get("session_str")
            or item.get("string_session")
            or item.get("session")
            or item.get("sessionString")
            or item.get("stringSession")
            or item.get("session_b64")
            or item.get("session_base64")
            or ""
        )
        api_hash = (
            item.get("api_hash")
            or item.get("apiHash")
            or item.get("hash")
            or ""
        )

    # Secrets riêng từng tài khoản được ưu tiên; vẫn giữ fallback tên cũ.
    session = (
        session
        or os.getenv(f"TELEGRAM_STRING_SESSION_ACC{acc_id}", "")
        or os.getenv(f"TELEGRAM_SESSION_B64_ACC{acc_id}", "")
        or os.getenv("TELEGRAM_STRING_SESSION", "")
    )
    api_hash = (
        api_hash
        or os.getenv(f"TELEGRAM_API_HASH_ACC{acc_id}", "")
        or os.getenv("TELEGRAM_API_HASH", "")
    )

    missing = []
    if not str(session).strip():
        missing.append(f"TELEGRAM_STRING_SESSION_ACC{acc_id} (hoặc session trong TELEGRAM_ACCOUNTS_JSON)")
    if not str(api_hash).strip():
        missing.append(f"TELEGRAM_API_HASH_ACC{acc_id} (hoặc api_hash trong TELEGRAM_ACCOUNTS_JSON)")
    if missing:
        raise ValueError(f"Thiếu cấu hình Acc {acc_id}: " + "; ".join(missing))

    return {
        f"TELEGRAM_STRING_SESSION_ACC{acc_id}": str(session).strip(),
        f"TELEGRAM_API_HASH_ACC{acc_id}": str(api_hash).strip(),
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

def run_account_worker(acc_id, procs_dict, account_configs):
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
            child_env.update(account_configs[acc_id])

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

    # Kiểm tra toàn bộ cấu hình trước khi tạo worker để tránh vòng lặp restart vô hạn.
    account_configs = {}
    try:
        for acc in ACCOUNTS:
            account_configs[acc] = account_env(acc)
    except (ValueError, TypeError) as exc:
        log("CONFIG_ERROR", str(exc))
        log("CONFIG_ERROR", "Đã dừng trước khi khởi chạy tiến trình. Hãy kiểm tra GitHub Actions Secrets.")
        return 2

    start_time = time.time()
    procs = {}
    threads = []

    for acc in ACCOUNTS:
        t = threading.Thread(target=run_account_worker, args=(acc, procs, account_configs), daemon=True)
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
    sys.exit(main())
