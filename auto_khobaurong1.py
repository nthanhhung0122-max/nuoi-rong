#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
====================================================================
  BOT AUTO KHO BAU RONG TCG 24/7 (DRAGON CARDS)
  Bot Telegram : @khobaurong_bot
  Web App URL  : https://khobaurong.online/
  Tai khoan    : Hùng Zai (@hungzai22 - ID: 7744031191)
  
  TINH NANG NANG CAP:
      - SU DUNG STRING_SESSION CHUAN TELETHON (100% RAM - KHONG LOI DISK MALFORMED)
      - TU DONG LAY INIT_DATA MOI QUA TELETHON (KHONG BAO GIO HET HAN TOKEN)
      - TU DONG DAU TRUONG (ARENA):
          + Thu thap Vang tu dong san sinh theo giay
          + TU DONG DANH THUC RONG KHI NGU (Wake Up Dragons) ngay khi sleepAt hoac status=sleeping
          + Tu dong mo khoa o Dau truong moi khi du Vang
          + Tu dong xep Rong chien dau manh nhat vao o trong
          + Tu dong mua & ap Trung Dong (14.000 Vang) khi con o trong ma het Rong
      - TU DONG CAY SMART LINKS & ADS FULL 4 NGUON (Toi da 480.000 Vang/ngay):
          + Ads Task (30 lan x 10.000 = 300.000 Vang)
          + Monetag Popup Smart Link (20 lan x 3.000 = 60.000 Vang)
          + Monetag Interstitial Smart Link (20 lan x 3.000 = 60.000 Vang)
          + Adsgram Rewarded Video (20 lan x 3.000 = 60.000 Vang)
      - TU DONG NANG CAP & GHEP RONG (Fusion) khi co the giong nhau
      - TU DONG NHAN TOAN BO NHIEM VU HANG NGAY (Quests)
      - HO TRO CHAY 24/7 TREN GITHUB ACTIONS HOAC MAY CA NHAN
====================================================================
"""

import os
import sys
import time
import json
import random
import asyncio
import urllib.parse
from datetime import datetime, timezone
import requests
from colorama import Fore, Style, init

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import RequestWebViewRequest

init(autoreset=True)

# -----------------------------------------------------------------
#  CAU HINH HE THONG & TAI KHOAN HUNG ZAI
# -----------------------------------------------------------------
API_ID = 39182276
API_HASH = "f02b155d895a3a3fbf8a1cbe810b5338"

# StringSession Telethon cho Hùng Zai (@hungzai22 - ID: 7744031191)
# 100% chay tren RAM, khong tao file SQLite -> Khong bao gio loi disk malformed
DEFAULT_STRING_SESSION = (
    "1BVtsOHIBuxmpWiBJ9hvwV9pSrzWw5U2I5Fe20Ww8l1LCk9rnsG6T6lLZEJXZE1JJC_qUH_yyWHnRoed"
    "RNI5lJYnfjRN4gyGeDrCxquDU12ZflrpCz0VLhMZx2C0LlyUCy2eHRSRE1wUCpEYZaymL0P7Z9eAHwMy4"
    "Oogewh5TqyO4x4MF6j0yTq8Zvfpv43O4aQDzErNv3GRqpx8DXBcOJIMP9yVhq-Mby5VH5J9cF-h-bJ5ws"
    "3xKjA4GY7YKjHxDt9OI-Zr7mr-V3qZy99UxJooThJj51f2RqOKhODdLh9XZQ0ygSoAd3iFAZDOPMEo8Ch"
    "5TrrzLXi2Q3N0HorIL1JfV0xoFQlY="
)

BOT_USERNAME = "khobaurong_bot"
BASE_URL = "https://khobaurong.online"

IS_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"
MAX_RUNTIME = int(os.getenv("MAX_RUNTIME_SECONDS", "19800" if IS_GITHUB_ACTIONS else "0"))

CURRENT_INIT_DATA = ""
USER_INFO = {}
http_session = requests.Session()

def log(tag, msg, color=Fore.WHITE):
    t = datetime.now().strftime("%H:%M:%S")
    print(f"[{t}] [{tag}] {color}{msg}{Style.RESET_ALL}", flush=True)

def fmt_num(val):
    try:
        return f"{int(val):,}"
    except:
        return str(val)

# -----------------------------------------------------------------
#  TU DONG LAY INIT_DATA MOI QUA TELETHON
# -----------------------------------------------------------------
async def fetch_fresh_init_data():
    global CURRENT_INIT_DATA, USER_INFO
    log("TELETHON", f"Dang ket noi Telegram bang StringSession (Acc: Hùng Zai @hungzai22)...", Fore.CYAN)

    session_str = os.getenv("TELEGRAM_STRING_SESSION") or os.getenv("TELEGRAM_SESSION_B64_ACC1") or DEFAULT_STRING_SESSION
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        log("ERR", "Phiên Telegram chưa được xác thực! Vui lòng kiểm tra lại StringSession.", Fore.RED)
        await client.disconnect()
        return None

    try:
        bot = await client.get_input_entity(BOT_USERNAME)
        res = await client(RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform="android",
            from_bot_menu=False,
            url=f"{BASE_URL}/"
        ))
        await client.disconnect()

        parsed = urllib.parse.urlparse(res.url)
        params = urllib.parse.parse_qs(parsed.fragment)
        CURRENT_INIT_DATA = params.get("tgWebAppData", [""])[0]

        qs = urllib.parse.parse_qs(CURRENT_INIT_DATA)
        user_json = json.loads(qs.get("user", ["{}"])[0])
        USER_INFO = {
            "telegramId": str(user_json.get("id", "7744031191")),
            "username": user_json.get("username", "hungzai22"),
            "firstName": user_json.get("first_name", "Hùng"),
            "lastName": user_json.get("last_name", "Zai"),
            "displayName": f"{user_json.get('first_name', '')} {user_json.get('last_name', '')}".strip() or "Hùng Zai",
            "languageCode": user_json.get("language_code", "vi"),
            "photoUrl": user_json.get("photo_url", ""),
            "isPremium": user_json.get("is_premium", False),
        }
        log("SUCCESS", f"Lay init_data thanh cong! User: {USER_INFO['displayName']} (@{USER_INFO['username']}) - ID: {USER_INFO['telegramId']}", Fore.GREEN)
        return CURRENT_INIT_DATA
    except Exception as e:
        log("ERR", f"Loi khi lay webview: {e}", Fore.RED)
        await client.disconnect()
        return None

def get_fresh_init_data_sync():
    return asyncio.run(fetch_fresh_init_data())

def get_headers():
    return {
        'user-agent': 'Mozilla/5.0 (Linux; Android 16; Pixel 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Mobile Safari/537.36',
        'content-type': 'application/json',
        'accept': '*/*',
        'x-telegram-init-data': CURRENT_INIT_DATA,
        'referer': f"{BASE_URL}/"
    }

# -----------------------------------------------------------------
#  DANG NHAP GAME
# -----------------------------------------------------------------
def login_game():
    global USER_INFO
    payload = {
        "telegramId": USER_INFO["telegramId"],
        "username": USER_INFO["username"],
        "displayName": USER_INFO["displayName"],
        "firstName": USER_INFO["firstName"],
        "lastName": USER_INFO["lastName"],
        "languageCode": USER_INFO["languageCode"],
        "photoUrl": USER_INFO["photoUrl"],
        "isPremium": USER_INFO["isPremium"],
        "initData": CURRENT_INIT_DATA,
        "startParam": "",
        "source": "telegram"
    }
    try:
        r = http_session.post(f"{BASE_URL}/api/auth/login", json=payload, headers=get_headers(), timeout=15)
        if r.status_code == 200:
            user = r.json().get("user", {})
            gold = user.get("gold", 0)
            cards = user.get("cardsOwned", 0)
            log("LOGIN", f"Dang nhap thanh cong! So du: {fmt_num(gold)} Vang | So The Rong: {cards}", Fore.CYAN)
            return user
        else:
            log("ERR", f"Dang nhap that bai: {r.status_code} - {r.text}", Fore.RED)
            return None
    except Exception as e:
        log("ERR", f"Loi ket noi dang nhap: {e}", Fore.RED)
        return None

# -----------------------------------------------------------------
#  NHIEM VU (QUESTS)
# -----------------------------------------------------------------
def handle_quests():
    try:
        t_id = USER_INFO["telegramId"]
        r = http_session.get(
            f"{BASE_URL}/api/quests/my?telegramId={t_id}&initData={urllib.parse.quote(CURRENT_INIT_DATA)}",
            headers=get_headers(),
            timeout=15
        )
        if r.status_code != 200:
            return

        quests = r.json().get("quests", [])
        for q in quests:
            q_id = q.get("id")
            title = q.get("title", q_id)
            claimed = q.get("claimed", False)
            if not claimed:
                claim_res = http_session.post(f"{BASE_URL}/api/quests/claim", json={
                    "telegramId": t_id,
                    "questId": q_id,
                    "initData": CURRENT_INIT_DATA
                }, headers=get_headers(), timeout=15)
                if claim_res.status_code == 200:
                    c_data = claim_res.json()
                    log("QUEST", f"Nhan thuong nhiem vu [{title}]: +{fmt_num(c_data.get('rewardGold', 0))} Vang!", Fore.GREEN)
                time.sleep(0.5)
    except Exception as e:
        log("ERR", f"Loi kiem tra nhiem vu: {e}", Fore.RED)

# -----------------------------------------------------------------
#  SMART LINKS & QUANG CAO (FULL 4 NGUON)
# -----------------------------------------------------------------
def handle_smartlinks_and_ads():
    t_id = USER_INFO["telegramId"]
    u_name = USER_INFO["username"]
    next_cooldowns = []

    # 1. Ads Task (Thuong 10.000 Vang / lan, toi da 30 lan / ngay, khong cooldown)
    try:
        r_task = http_session.get(
            f"{BASE_URL}/api/ads/task/status?telegramId={t_id}&initData={urllib.parse.quote(CURRENT_INIT_DATA)}",
            headers=get_headers(),
            timeout=15
        )
        if r_task.status_code == 200:
            task_status = r_task.json()
            rem = task_status.get("remaining", 0)
            if rem > 0:
                log("SMARTLINK", f"Phat hien {rem} luot Ads Task (+10.000 Vang/luot), bat dau nhan...", Fore.YELLOW)
                while rem > 0:
                    claim_r = http_session.post(f"{BASE_URL}/api/ads/task/claim", json={
                        "telegramId": t_id,
                        "username": u_name,
                        "initData": CURRENT_INIT_DATA
                    }, headers=get_headers(), timeout=15)
                    if claim_r.status_code == 200:
                        c_data = claim_r.json()
                        rem = c_data.get("remaining", 0)
                        log("SMARTLINK", f"Nhan Ads Task thanh cong: +{fmt_num(c_data.get('rewardGold', 10000))} Vang! (Con {rem} luot)", Fore.GREEN)
                        time.sleep(random.uniform(2, 3.5))
                    else:
                        break
            else:
                log("ADS", "Ads Task: da hoan thanh 30/30 luot trong ngay!", Fore.WHITE)
    except Exception as e:
        log("ERR", f"Loi Ads Task: {e}", Fore.RED)

    # 2. Cac kenh Smartlink & Video Rewarded (cooldown 15 phut / lan)
    ad_channels = [
        ("popup", "/api/ads/monetag/popup/status", "/api/ads/monetag/popup/claim", "Monetag Popup (Smart Link)"),
        ("interstitial", "/api/ads/monetag/interstitial/status", "/api/ads/monetag/interstitial/claim", "Monetag Interstitial (Smart Link)"),
        ("rewarded", "/api/ads/rewarded/status", "/api/ads/rewarded/claim", "Adsgram Rewarded (Video Ad)")
    ]

    for ad_key, status_url, claim_url, ad_label in ad_channels:
        try:
            r_stat = http_session.get(
                f"{BASE_URL}{status_url}?telegramId={t_id}&initData={urllib.parse.quote(CURRENT_INIT_DATA)}",
                headers=get_headers(),
                timeout=15
            )
            if r_stat.status_code == 200:
                st = r_stat.json()
                rem = st.get("remaining", 0)
                cd_sec = st.get("cooldownRemainingSec", 0)
                if rem > 0:
                    if cd_sec <= 0:
                        log("SMARTLINK", f"Dang kich hoat {ad_label}...", Fore.CYAN)
                        claim_r = http_session.post(f"{BASE_URL}{claim_url}", json={
                            "telegramId": t_id,
                            "username": u_name,
                            "initData": CURRENT_INIT_DATA
                        }, headers=get_headers(), timeout=15)
                        if claim_r.status_code == 200:
                            c_data = claim_r.json()
                            log("SMARTLINK", f"Nhan thuong {ad_label}: +{fmt_num(c_data.get('rewardGold', 3000))} Vang! (Con {c_data.get('remaining', 0)} luot)", Fore.GREEN)
                            next_cooldowns.append(900)
                        else:
                            log("WARN", f"{ad_label} thong bao: {claim_r.text}", Fore.YELLOW)
                    else:
                        mins, secs = divmod(cd_sec, 60)
                        log("ADS", f"{ad_label}: con {rem} luot (cho hoi chieu {mins}p {secs}s)", Fore.YELLOW)
                        next_cooldowns.append(cd_sec)
                else:
                    log("ADS", f"{ad_label}: da xem het {st.get('dailyLimit', 20)} luot hom nay!", Fore.WHITE)
        except Exception as e:
            log("ERR", f"Loi kenh {ad_label}: {e}", Fore.RED)

    return min(next_cooldowns) if next_cooldowns else 60

# -----------------------------------------------------------------
#  DAU TRUONG (ARENA) - DANH THUC RONG & SAN SINH VANG
# -----------------------------------------------------------------
def handle_arena_and_dragons():
    t_id = USER_INFO["telegramId"]
    u_name = USER_INFO["username"]

    try:
        # 1. Lay trang thai Arena (API nay tu dong thu thap Vang da sinh ra)
        r_arena = http_session.get(
            f"{BASE_URL}/api/battle/arena?telegramId={t_id}&initData={urllib.parse.quote(CURRENT_INIT_DATA)}",
            headers=get_headers(),
            timeout=15
        )
        if r_arena.status_code != 200:
            return

        arena_res = r_arena.json()
        arena = arena_res.get("arena", {})
        curr_gold = arena_res.get("gold", 0)
        slots = arena.get("slots", [])
        total_pwr = arena.get("totalPower", 0)
        gold_per_sec = arena.get("goldPerSec", 0)

        log("ARENA", f"Luc chien tong: {fmt_num(total_pwr)} Power | Toc do san sinh: +{gold_per_sec:.4f} Vang/s", Fore.MAGENTA)

        now_utc = datetime.now(timezone.utc)
        empty_slot_indices = []

        # 2. Quet cac o de DANH THUC RONG KHI NGU (Wake Up)
        for s in slots:
            s_idx = s.get("slotIndex")
            is_locked = s.get("locked", False)
            placement = s.get("placement")

            if is_locked:
                # Tu dong mo khoa o moi neu du Vang
                unlock_cost = s.get("unlockCost", 0)
                if unlock_cost > 0 and curr_gold >= unlock_cost:
                    log("UNLOCK", f"Du Vang ({fmt_num(curr_gold)}/{fmt_num(unlock_cost)} Vang)! Dang mo khoa O Dau Truong {s_idx}...", Fore.CYAN)
                    u_r = http_session.post(f"{BASE_URL}/api/battle/unlock", json={
                        "telegramId": t_id,
                        "username": u_name,
                        "initData": CURRENT_INIT_DATA,
                        "slotIndex": s_idx
                    }, headers=get_headers(), timeout=15)
                    if u_r.status_code == 200:
                        log("UNLOCK", f"Mo khoa thanh cong O Dau Truong {s_idx}!", Fore.GREEN)
                        empty_slot_indices.append(s_idx)
                continue

            if placement:
                status = placement.get("status")
                dragon = placement.get("dragon", {})
                d_name = dragon.get("name", f"Rong O {s_idx}")
                sleep_at_str = placement.get("sleepAt")

                is_sleeping = (status == "sleeping")
                if not is_sleeping and sleep_at_str:
                    try:
                        sleep_dt = datetime.fromisoformat(sleep_at_str.replace("Z", "+00:00"))
                        if now_utc >= sleep_dt:
                            is_sleeping = True
                    except:
                        pass

                # Kich hoat danh thuc Rong ngay khi ngu!
                if is_sleeping:
                    log("WAKE", f"⏰ Phat hien Rong [{d_name}] o O {s_idx} DANG NGU! Tien hanh danh thuc...", Fore.YELLOW)
                    w_r = http_session.post(f"{BASE_URL}/api/battle/wake", json={
                        "telegramId": t_id,
                        "username": u_name,
                        "initData": CURRENT_INIT_DATA,
                        "slotIndex": s_idx
                    }, headers=get_headers(), timeout=15)
                    if w_r.status_code == 200:
                        log("WAKE", f"✨ Da danh thuc Rong [{d_name}] thanh cong! Rong da tro lai chien dau va tiep tuc de Vang!", Fore.GREEN)
                    else:
                        log("WARN", f"Chua the danh thuc O {s_idx}: {w_r.text}", Fore.YELLOW)
                else:
                    log("ARENA", f"O {s_idx}: Rong [{d_name}] dang thuc chien 🔥 (Toc do: +{placement.get('goldPerSec', 0):.4f} Vang/s)", Fore.GREEN)
            else:
                empty_slot_indices.append(s_idx)

        # 3. Neu co o trong, xep Rong manh nhat vao o
        if empty_slot_indices:
            r_col = http_session.get(
                f"{BASE_URL}/api/collection/{t_id}?initData={urllib.parse.quote(CURRENT_INIT_DATA)}",
                headers=get_headers(),
                timeout=15
            )
            if r_col.status_code == 200:
                collection = r_col.json()
                fighting_dragon_codes = set()
                for s in slots:
                    if s.get("placement"):
                        fighting_dragon_codes.add(s["placement"]["dragon"]["code"])

                available_dragons = [
                    c for c in collection
                    if c.get("dragon", {}).get("code") not in fighting_dragon_codes
                ]
                available_dragons.sort(key=lambda x: x.get("dragon", {}).get("power", 0), reverse=True)

                for slot_idx in empty_slot_indices:
                    if available_dragons:
                        chosen = available_dragons.pop(0)
                        d_info = chosen.get("dragon", {})
                        d_code = d_info.get("code")
                        d_name = d_info.get("name")
                        lvl = chosen.get("level", 1)

                        log("ARENA", f"Xep Rong manh nhat [{d_name}] (Lv.{lvl}) vao O {slot_idx}...", Fore.CYAN)
                        p_r = http_session.post(f"{BASE_URL}/api/battle/place", json={
                            "telegramId": t_id,
                            "username": u_name,
                            "initData": CURRENT_INIT_DATA,
                            "slotIndex": slot_idx,
                            "dragonCode": d_code,
                            "level": lvl
                        }, headers=get_headers(), timeout=15)
                        if p_r.status_code == 200:
                            log("ARENA", f"Xep Rong [{d_name}] vao O {slot_idx} thanh cong!", Fore.GREEN)
                    else:
                        # Neu het Rong ma con Vang (>= 14.000 Vang), tu dong mua va ap Trung Dong
                        if curr_gold >= 14000:
                            log("SHOP", f"Con o trong, dang mua Trung Dong (14.000 Vang) de ap Rong moi...", Fore.YELLOW)
                            open_r = http_session.post(f"{BASE_URL}/api/packs/trung-dong/open", json={
                                "telegramId": t_id,
                                "username": u_name,
                                "initData": CURRENT_INIT_DATA
                            }, headers=get_headers(), timeout=15)
                            if open_r.status_code == 200:
                                curr_gold -= 14000
                                log("SHOP", f"Ap Trung Dong thanh cong! Rong moi da san sang.", Fore.GREEN)
                                time.sleep(1)
                                break
    except Exception as e:
        log("ERR", f"Loi xu ly dau truong: {e}", Fore.RED)

# -----------------------------------------------------------------
#  TU DONG GHEP RONG (UPGRADE / FUSION)
# -----------------------------------------------------------------
def handle_upgrades():
    t_id = USER_INFO["telegramId"]
    u_name = USER_INFO["username"]
    try:
        r_col = http_session.get(
            f"{BASE_URL}/api/collection/{t_id}?initData={urllib.parse.quote(CURRENT_INIT_DATA)}",
            headers=get_headers(),
            timeout=15
        )
        if r_col.status_code != 200:
            return

        collection = r_col.json()
        code_counts = {}
        for c in collection:
            d_code = c.get("dragon", {}).get("code")
            if d_code:
                code_counts[d_code] = code_counts.get(d_code, 0) + 1

        for d_code, count in code_counts.items():
            if count >= 2:
                log("FUSION", f"Phat hien {count} the giong nhau ({d_code}), tien hanh ghep rong nang cap...", Fore.CYAN)
                up_r = http_session.post(f"{BASE_URL}/api/upgrade", json={
                    "telegramId": t_id,
                    "username": u_name,
                    "initData": CURRENT_INIT_DATA,
                    "dragonCode": d_code
                }, headers=get_headers(), timeout=15)
                if up_r.status_code == 200:
                    res_up = up_r.json()
                    log("FUSION", f"🎉 Ghep Rong thanh cong! Rong dat cap do moi: {res_up.get('newLevel', 'Max')}", Fore.GREEN)
                time.sleep(1)
    except Exception as e:
        log("ERR", f"Loi ghep rong: {e}", Fore.RED)

# -----------------------------------------------------------------
#  VONG LAP CHINH AUTO KHO BAU RONG 24/7
# -----------------------------------------------------------------
def run():
    banner = [
        "=" * 64,
        "      BOT AUTO KHO BAU RONG TCG 24/7 (DRAGON CARDS)",
        "=" * 64,
        f" Tai khoan : {USER_INFO.get('displayName', 'Hùng Zai')} (@{USER_INFO.get('username', 'hungzai22')} - ID: {USER_INFO.get('telegramId', '7744031191')})",
        f" Bot Game  : @{BOT_USERNAME} | WebApp: {BASE_URL}",
        f" Che do    : Telethon StringSession (RAM 100% - Zero SQLite Error)",
        f" Tinh nang : Auto Wake Up Dragons | Auto Smartlinks & Ads (480k Vang)",
        "=" * 64
    ]
    print("\n" + "\n".join(banner) + "\n", flush=True)

    start_time = time.time()
    loop_count = 0

    while True:
        try:
            if MAX_RUNTIME > 0 and (time.time() - start_time) >= MAX_RUNTIME:
                log("DONE", f"Hoan thanh phien chay {MAX_RUNTIME} giay tren GitHub Actions. Nghi ngoi!", Fore.GREEN)
                break

            loop_count += 1
            log("LOOP", f"--- BAT DAU CHU KY QUET THU {loop_count} ---", Fore.CYAN)

            # 1. Cap nhat profile & so du
            login_game()

            # 2. Tu dong danh thuc Rong & quan ly Dau truong
            handle_arena_and_dragons()

            # 3. Lam Smart Links & Cay Ads full 4 nguon
            cooldown_min = handle_smartlinks_and_ads()

            # 4. Quet va Nhan nhiem vu
            handle_quests()

            # 5. Kiem tra ghep Rong
            if loop_count % 3 == 0:
                handle_upgrades()

            sleep_duration = max(30, min(cooldown_min, 300))
            mins, secs = divmod(sleep_duration, 60)
            log("WAIT", f"Chu ky {loop_count} hoan tat. Cho {mins}p {secs}s truoc chu ky tiep theo...\n", Fore.WHITE)
            time.sleep(sleep_duration)

        except KeyboardInterrupt:
            log("STOP", "Da dung bot theo yeu cau nguoi dung.", Fore.YELLOW)
            break
        except Exception as e:
            log("ERR", f"Loi ngoai le vong lap: {e}", Fore.RED)
            time.sleep(15)

if __name__ == "__main__":
    init_tok = get_fresh_init_data_sync()
    if init_tok and login_game():
        run()
    else:
        log("FATAL", "Khong the khoi dong bot do loi xac thuc Telegram. Dung chuong trinh.", Fore.RED)
