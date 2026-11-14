#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
====================================================================
  BOT AUTO KHO BAU RONG TCG 24/7 (DRAGON CARDS) - UNIFIED ENGINE
  Bot Telegram : @khobaurong_bot
  Web App URL  : https://khobaurong.online/
  Support      : Da tai khoan Acc 1..4 (Hung Zai, gaylobucu, phanhhyy, Wind_trader)
  
  TINH NANG NANG CAP TOAN DIEN:
    1. STRING_SESSION TELETHON 100% RAM:
       - Tu dong xin init_data moi nhat, khong bao gio het han token
       - Khong dung SQLite tren disk -> triet tieu hoan toan loi database locked/malformed.
    2. TAB SMARTLINK (Uu dai doi tac Monetag, Maven, HilltopAds):
       - 15 luot / ngay, cooldown 10 phut / luot.
       - Tu dong chon Smartlink co thuong cao nhat (+3.000 Vang / luot thay vi 1.000 Vang).
    3. TAB ADS FULL 4 NGUON (Toi da 480.000 Vang / ngay):
       - Thu Thach Rong (Ads Task): 30 luot x 10.000 = 300.000 Vang / ngay.
         Kich hoat toan bo tracking events Adsgram Task (Block 34662: render, show, click, reward, return).
       - Video Rewarded: 20 luot x 3.000 = 60.000 Vang / ngay (cooldown 15m).
         Kich hoat video events Adsgram Rewarded (Block 34191: render, quartiles, complete, reward).
       - Monetag Popup & Interstitial: 20 luot x 3.000 = 60.000 Vang / ngay (cooldown 15m).
         Tu dong quet va nhan thuong cho xac minh (pendingVerified).
    4. DAU TRUONG (ARENA) & DANH THUC RONG (Wake Up):
       - Tu dong danh thuc Rong ngay khi ngu (status=sleeping hoac sleepAt qua han).
       - Tu dong mo khoa O Dau Truong moi khi du Vang.
       - Tu dong sap xep Rong co Luc Chien (Power) cao nhat vao o trong.
       - Tu dong mua & ap Trung Dong (14.000 Vang) khi con o trong ma het Rong de san sinh Vang lien tuc.
    5. FUSION & QUESTS:
       - Tu dong ghep the Rong giong nhau de tang Cap (Level Up).
       - Tu dong hoan thanh va nhan toan bo Nhiem vu he thong (Quests).
====================================================================
"""

import os
import sys
import re
import time
import json
import uuid
import random
import base64
import asyncio
import argparse
import urllib.parse
from datetime import datetime, timezone
import requests
from colorama import Fore, Style, init

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import RequestWebViewRequest

init(autoreset=True)

# -----------------------------------------------------------------
#  DANH SACH TAI KHOAN HO TRO
# -----------------------------------------------------------------
ACCOUNTS_CONFIG = {
    1: {"name": "Acc 1 (hungzai22)", "api_id": 39182276, "api_hash": "f02b155d895a3a3fbf8a1cbe810b5338", "session": ""},
    2: {"name": "Acc 2 (gaylobucu)", "api_id": 39182276, "api_hash": "f02b155d895a3a3fbf8a1cbe810b5338", "session": ""},
    3: {"name": "Acc 3 (phanhhyy)", "api_id": 39182276, "api_hash": "f02b155d895a3a3fbf8a1cbe810b5338", "session": ""},
    4: {"name": "Acc 4 (Wind_trader)", "api_id": 34333329, "api_hash": "f02b155d895a3a3fbf8a1cbe810b5338", "session": ""},
}

parser = argparse.ArgumentParser()
parser.add_argument("--acc", type=int, default=int(os.getenv("ACC_NUM", "1")), help="Account index (1..4)")
parser.add_argument("--once", action="store_true", help="Chay 1 vong duy nhat roi thoat")
args, _ = parser.parse_known_args()

ACC_INDEX = args.acc
acc_data = ACCOUNTS_CONFIG.get(ACC_INDEX, ACCOUNTS_CONFIG[1])

API_ID = int(os.getenv(f"TELEGRAM_API_ID_ACC{ACC_INDEX}") or acc_data["api_id"])
API_HASH = (
    os.getenv(f"TELEGRAM_API_HASH_ACC{ACC_INDEX}")
    or os.getenv("TELEGRAM_API_HASH")
    or acc_data["api_hash"]
)
STRING_SESSION = (
    os.getenv(f"TELEGRAM_STRING_SESSION_ACC{ACC_INDEX}")
    or os.getenv("TELEGRAM_STRING_SESSION")
    or os.getenv(f"TELEGRAM_SESSION_B64_ACC{ACC_INDEX}")
    or acc_data["session"]
)

BOT_USERNAME = "khobaurong_bot"
BASE_URL = "https://khobaurong.online"

ADSGRAM_BLOCK_TASK = "34662"      # Adsgram Task (Thu Thach Rong: +10.000 Vang)
ADSGRAM_BLOCK_REWARDED = "34191"  # Adsgram Rewarded Video (+3.000 Vang)

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
#  TU DONG LAY INIT_DATA MOI QUA TELETHON STRING_SESSION
# -----------------------------------------------------------------
async def fetch_fresh_init_data():
    global CURRENT_INIT_DATA, USER_INFO
    acc_name = acc_data.get("name", f"Acc {ACC_INDEX}")
    log("TELETHON", f"Ket noi Telegram bang StringSession [{acc_name}]...", Fore.CYAN)

    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        log("ERR", f"Phien Telegram chua xac thuc cho [{acc_name}]! Kiem tra lai session.", Fore.RED)
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
            "telegramId": str(user_json.get("id")),
            "username": user_json.get("username", f"user_{user_json.get('id')}"),
            "firstName": user_json.get("first_name", ""),
            "lastName": user_json.get("last_name", ""),
            "displayName": f"{user_json.get('first_name', '')} {user_json.get('last_name', '')}".strip() or str(user_json.get("id")),
            "languageCode": user_json.get("language_code", "vi"),
            "photoUrl": user_json.get("photo_url", ""),
            "isPremium": user_json.get("is_premium", False),
        }
        log("AUTH_OK", f"Lay init_data thanh cong! User: {USER_INFO['displayName']} (@{USER_INFO['username']}) - ID: {USER_INFO['telegramId']}", Fore.GREEN)
        return CURRENT_INIT_DATA
    except Exception as e:
        log("ERR", f"Loi khi lay webview init_data: {e}", Fore.RED)
        await client.disconnect()
        return None

def get_fresh_init_data_sync():
    return asyncio.run(fetch_fresh_init_data())

def get_game_headers():
    return {
        'user-agent': 'Mozilla/5.0 (Linux; Android 16; Pixel 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Mobile Safari/537.36',
        'content-type': 'application/json',
        'accept': '*/*',
        'x-telegram-init-data': CURRENT_INIT_DATA,
        'referer': f"{BASE_URL}/"
    }

def get_adsgram_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 14; SM-S928B Build/UP1A.231005.007; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/124.0.6367.82 Mobile Safari/537.36 Telegram-Android/10.11.1',
        'Origin': 'https://khobaurong.online',
        'Referer': 'https://khobaurong.online/',
        'Accept': 'application/json, text/plain, */*',
        'X-Requested-With': 'org.telegram.messenger'
    }

def make_adsgram_dcs(init_data_str):
    parsed = dict(urllib.parse.parse_qsl(init_data_str))
    items = [f"{k}={v}" for k, v in parsed.items() if k not in ['hash', 'signature']]
    items.sort()
    raw = "\n".join(items)
    return base64.urlsafe_b64encode(raw.encode('utf-8')).decode('utf-8').rstrip('=')

# -----------------------------------------------------------------
#  DANG NHAP GAME & DONG BO PROFILE
# -----------------------------------------------------------------
def login_game():
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
        r = http_session.post(f"{BASE_URL}/api/auth/login", json=payload, headers=get_game_headers(), timeout=15)
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
#  NHIEM VU HANG NGAY & HE THONG (FULL QUESTS SOLVER)
# -----------------------------------------------------------------
def handle_quests():
    try:
        t_id = USER_INFO["telegramId"]
        r = http_session.get(
            f"{BASE_URL}/api/quests/my?telegramId={t_id}&initData={urllib.parse.quote(CURRENT_INIT_DATA)}",
            headers=get_game_headers(),
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
                # 1. Thử gọi claim trực tiếp
                claim_res = http_session.post(f"{BASE_URL}/api/quests/claim", json={
                    "telegramId": t_id,
                    "questId": q_id,
                    "initData": CURRENT_INIT_DATA
                }, headers=get_game_headers(), timeout=15)
                
                if claim_res.status_code == 200:
                    c_data = claim_res.json()
                    log("QUEST", f"Nhan thuong nhiem vu [{title}]: +{fmt_num(c_data.get('rewardGold', 0))} Vang!", Fore.GREEN)
                else:
                    # 2. Nếu chưa cho claim, thử gọi complete/verify nếu nhiệm vụ dạng link/social
                    complete_res = http_session.post(f"{BASE_URL}/api/quests/complete", json={
                        "telegramId": t_id,
                        "questId": q_id,
                        "initData": CURRENT_INIT_DATA
                    }, headers=get_game_headers(), timeout=15)
                    if complete_res.status_code == 200:
                        # Thử claim lại sau khi complete
                        time.sleep(1)
                        c2 = http_session.post(f"{BASE_URL}/api/quests/claim", json={
                            "telegramId": t_id,
                            "questId": q_id,
                            "initData": CURRENT_INIT_DATA
                        }, headers=get_game_headers(), timeout=15)
                        if c2.status_code == 200:
                            c_data = c2.json()
                            log("QUEST", f"Hoan thanh & Nhan thuong [{title}]: +{fmt_num(c_data.get('rewardGold', 0))} Vang!", Fore.GREEN)
                time.sleep(0.5)
    except Exception as e:
        log("ERR", f"Loi kiem tra nhiem vu: {e}", Fore.RED)

# -----------------------------------------------------------------
#  TAB SMARTLINK (UU DAI DOI TAC - TOI UU CHON LINK 3.000 VANG)
# -----------------------------------------------------------------
def handle_partner_smartlinks():
    t_id = USER_INFO["telegramId"]
    u_name = USER_INFO["username"]

    try:
        r_stat = http_session.get(
            f"{BASE_URL}/api/smartlinks/status?telegramId={t_id}&initData={urllib.parse.quote(CURRENT_INIT_DATA)}",
            headers=get_game_headers(),
            timeout=15
        )
        if r_stat.status_code != 200:
            return 600

        st = r_stat.json()
        daily_limit = st.get("dailyLimit", 15)
        total_taps_today = st.get("totalTapsToday", 0)
        rem = max(0, daily_limit - total_taps_today)
        cd_sec = st.get("cooldownRemainingSec", 0)
        links = st.get("links", [])

        if rem <= 0:
            log("SMARTLINK", f"Tab Smartlink: Da hoan thanh {total_taps_today}/{daily_limit} luot hom nay!", Fore.WHITE)
            return 600

        if cd_sec > 0:
            mins, secs = divmod(cd_sec, 60)
            log("SMARTLINK", f"Tab Smartlink: Con {rem}/{daily_limit} luot (dang cho cooldown {mins}p {secs}s)", Fore.YELLOW)
            return cd_sec

        # Sap xep chon link co thuong cao nhat (uu tien Monetag 3.000 Vang)
        if links:
            available_links = [l for l in links if l.get("remainingToday", 1) > 0]
            if not available_links:
                available_links = links
            available_links.sort(key=lambda x: x.get("rewardGold", 0), reverse=True)
            chosen = available_links[0]
            link_id = chosen.get("id")
            net_name = chosen.get("network", "Doi tac")
            exp_reward = chosen.get("rewardGold", 1000)

            log("SMARTLINK", f"Dang mo Smartlink [{net_name}] (ID: {link_id}, Thuong: +{fmt_num(exp_reward)} Vang)...", Fore.CYAN)
            tap_r = http_session.post(f"{BASE_URL}/api/smartlinks/tap", json={
                "telegramId": t_id,
                "username": u_name,
                "initData": CURRENT_INIT_DATA,
                "linkId": link_id
            }, headers=get_game_headers(), timeout=15)

            if tap_r.status_code == 200:
                res_data = tap_r.json()
                reward = res_data.get("rewardGold", exp_reward)
                taps = res_data.get("totalTapsToday", total_taps_today + 1)
                cd = res_data.get("cooldownRemainingSec", 600)
                gold_total = res_data.get("gold", 0)
                log("SMARTLINK", f"🎉 Nhan thanh cong Smartlink [{net_name}]: +{fmt_num(reward)} Vang! (Hom nay: {taps}/{daily_limit} luot | So du: {fmt_num(gold_total)} Vang)", Fore.GREEN)
                return cd
            else:
                log("WARN", f"Smartlink tap bao: {tap_r.text}", Fore.YELLOW)
                return 60
    except Exception as e:
        log("ERR", f"Loi tab Smartlink: {e}", Fore.RED)
        return 600

# -----------------------------------------------------------------
#  TAB QUANG CAO (ADS FULL 4 NGUON - THU THACH RONG, REWARDED, MONETAG)
# -----------------------------------------------------------------

def trigger_adsgram_task(block_id=ADSGRAM_BLOCK_TASK):
    """Kich hoat Adsgram Task (Thu Thach Rong - Block 34662)"""
    try:
        parsed = dict(urllib.parse.parse_qsl(CURRENT_INIT_DATA))
        sig = parsed.get('signature', '')
        dcs = make_adsgram_dcs(CURRENT_INIT_DATA)

        ad_headers = get_adsgram_headers()
        params = {
            'blockId': str(block_id),
            'tg_id': str(USER_INFO.get('telegramId', '')),
            'tg_platform': 'android',
            'platform': 'Linux aarch64',
            'language': 'en',
            'top_domain': 'khobaurong.online',
            'signature': sig,
            'data_check_string': dcs,
            'sdk_version': '2.2.5'
        }
        r = requests.get('https://api.adsgram.ai/adv', headers=ad_headers, params=params, timeout=12)
        if r.status_code == 200:
            data = r.json()
            banners = data.get('banners', [])
            if banners:
                trackings = banners[0].get('banner', {}).get('trackings', [])
                for t in trackings:
                    t_url = t.get('value')
                    t_name = t.get('name')
                    try:
                        requests.get(t_url, headers=ad_headers, timeout=6)
                    except Exception:
                        pass
                    if t_name in ['render', 'show']:
                        time.sleep(1.0)
                    elif t_name == 'click':
                        time.sleep(2.0)
                return True
    except Exception as e:
        log("ADSGRAM_ERR", f"Loi kich hoat Adsgram Task {block_id}: {e}", Fore.LIGHTBLACK_EX)
    return False

def trigger_adsgram_rewarded(block_id=ADSGRAM_BLOCK_REWARDED):
    """Kich hoat Adsgram Rewarded Video (Block 34191)"""
    try:
        parsed = dict(urllib.parse.parse_qsl(CURRENT_INIT_DATA))
        sig = parsed.get('signature', '')
        dcs = make_adsgram_dcs(CURRENT_INIT_DATA)

        ad_headers = get_adsgram_headers()
        params = {
            'blockId': str(block_id),
            'tg_id': str(USER_INFO.get('telegramId', '')),
            'tg_platform': 'android',
            'platform': 'Linux aarch64',
            'language': 'en',
            'top_domain': 'khobaurong.online',
            'signature': sig,
            'data_check_string': dcs,
            'sdk_version': '2.2.5'
        }
        r = requests.get('https://api.adsgram.ai/adv', headers=ad_headers, params=params, timeout=12)
        urls = [u.replace('<![CDATA[', '').replace(']]>', '').strip() 
                for u in re.findall(r'https://api\.adsgram\.ai/[^\s"\'<>]+', r.text) if 'error' not in u]

        if urls:
            log("ADS_WATCH", f"Dang xem Video Adsgram ({len(urls)} su kien tracking)...", Fore.CYAN)
            for u in urls[:3]:
                try: requests.get(u, headers=ad_headers, timeout=6)
                except Exception: pass
            time.sleep(3.0)

            for u in urls[3:-2]:
                try: requests.get(u, headers=ad_headers, timeout=6)
                except Exception: pass
            time.sleep(4.0)

            for u in urls[-2:]:
                try: requests.get(u, headers=ad_headers, timeout=6)
                except Exception: pass
            return True
    except Exception as e:
        log("ADSGRAM_ERR", f"Loi kich hoat Adsgram Rewarded {block_id}: {e}", Fore.LIGHTBLACK_EX)
    return False

def handle_ads_tab():
    t_id = USER_INFO["telegramId"]
    u_name = USER_INFO["username"]
    next_cooldowns = []

    # -------------------------------------------------------------
    # 1. Ads Task (Thu Thach Rong: 30 luot x 10.000 = 300.000 Vang, khong cooldown)
    # -------------------------------------------------------------
    try:
        r_task = http_session.get(
            f"{BASE_URL}/api/ads/task/status?telegramId={t_id}&initData={urllib.parse.quote(CURRENT_INIT_DATA)}",
            headers=get_game_headers(),
            timeout=15
        )
        if r_task.status_code == 200:
            task_status = r_task.json()
            rem = task_status.get("remaining", 0)
            pending_verified = task_status.get("pendingVerified", 0)

            # Nhan thuong dang cho xac minh (pendingVerified) neu co
            while pending_verified > 0:
                log("ADS_CLAIM", f"Co {pending_verified} thuong Thu Thach Rong da xac minh! Dang nhan...", Fore.GREEN)
                c_r = http_session.post(f"{BASE_URL}/api/ads/task/claim", json={
                    "telegramId": t_id,
                    "username": u_name,
                    "initData": CURRENT_INIT_DATA
                }, headers=get_game_headers(), timeout=15)
                if c_r.status_code == 200:
                    c_data = c_r.json()
                    pending_verified -= 1
                    rem = c_data.get("remaining", rem - 1)
                    log("ADS_OK", f"🎉 Nhan thanh cong Thu Thach Rong: +{fmt_num(c_data.get('rewardGold', 10000))} Vang! (Con {rem} luot)", Fore.GREEN)
                    time.sleep(1.5)
                else:
                    break

            if rem > 0:
                log("ADS", f"Phat hien {rem} luot Thu Thach Rong (+10.000 Vang/luot), bat dau cay...", Fore.YELLOW)
                consecutive_fails = 0
                while rem > 0 and consecutive_fails < 3:
                    trigger_adsgram_task(ADSGRAM_BLOCK_TASK)
                    time.sleep(2.5)

                    claim_ok = False
                    for attempt in range(1, 5):
                        claim_r = http_session.post(f"{BASE_URL}/api/ads/task/claim", json={
                            "telegramId": t_id,
                            "username": u_name,
                            "initData": CURRENT_INIT_DATA
                        }, headers=get_game_headers(), timeout=15)

                        if claim_r.status_code == 200:
                            c_data = claim_r.json()
                            rem = c_data.get("remaining", rem - 1)
                            log("ADS_OK", f"🎉 Hoan thanh Thu Thach Rong: +{fmt_num(c_data.get('rewardGold', 10000))} Vang! (Hom nay: {c_data.get('claimedToday', 30-rem)}/30, Con {rem} luot)", Fore.GREEN)
                            consecutive_fails = 0
                            claim_ok = True
                            time.sleep(random.uniform(2.0, 3.5))
                            break
                        elif claim_r.status_code == 202 or "pendingVerification" in claim_r.text:
                            time.sleep(3.0)
                        else:
                            break

                    if not claim_ok:
                        consecutive_fails += 1
                        time.sleep(3.0)
            else:
                log("ADS", "Thu Thach Rong: Da hoan thanh 30/30 luot trong ngay!", Fore.WHITE)
    except Exception as e:
        log("ERR", f"Loi Ads Task: {e}", Fore.RED)

    # -------------------------------------------------------------
    # 2. Ads Rewarded Video (Block 34191: 20 luot x 3.000 = 60.000 Vang, 15m cooldown)
    # -------------------------------------------------------------
    try:
        r_rew = http_session.get(
            f"{BASE_URL}/api/ads/rewarded/status?telegramId={t_id}&initData={urllib.parse.quote(CURRENT_INIT_DATA)}",
            headers=get_game_headers(),
            timeout=15
        )
        if r_rew.status_code == 200:
            st = r_rew.json()
            rem = st.get("remaining", 0)
            cd_sec = st.get("cooldownRemainingSec", 0)
            pending_verified = st.get("pendingVerified", 0)

            while pending_verified > 0:
                log("ADS_CLAIM", f"Co {pending_verified} video Rewarded da xac minh! Dang nhan...", Fore.GREEN)
                c_r = http_session.post(f"{BASE_URL}/api/ads/rewarded/claim", json={
                    "telegramId": t_id, "username": u_name, "initData": CURRENT_INIT_DATA
                }, headers=get_game_headers(), timeout=15)
                if c_r.status_code == 200:
                    c_data = c_r.json()
                    pending_verified -= 1
                    rem = c_data.get("remaining", rem - 1)
                    log("ADS_OK", f"🎉 Nhan Video Rewarded: +{fmt_num(c_data.get('rewardGold', 3000))} Vang!", Fore.GREEN)
                    time.sleep(1.5)
                else:
                    break

            if rem > 0:
                if cd_sec <= 0:
                    log("ADS", f"Dang xem Adsgram Rewarded Video (+3.000 Vang)...", Fore.CYAN)
                    trigger_adsgram_rewarded(ADSGRAM_BLOCK_REWARDED)
                    time.sleep(2.0)

                    for attempt in range(1, 6):
                        claim_r = http_session.post(f"{BASE_URL}/api/ads/rewarded/claim", json={
                            "telegramId": t_id, "username": u_name, "initData": CURRENT_INIT_DATA
                        }, headers=get_game_headers(), timeout=15)

                        if claim_r.status_code == 200 and not claim_r.json().get("pendingVerification"):
                            c_data = claim_r.json()
                            rem = c_data.get("remaining", rem - 1)
                            log("ADS_OK", f"🎉 Nhan Video Rewarded thanh cong: +{fmt_num(c_data.get('rewardGold', 3000))} Vang! (Con {rem} luot)", Fore.GREEN)
                            next_cooldowns.append(900)
                            break
                        elif claim_r.status_code in [200, 202] and "pendingVerification" in claim_r.text:
                            time.sleep(3.0)
                        else:
                            break
                else:
                    mins, secs = divmod(cd_sec, 60)
                    log("ADS", f"Video Rewarded: con {rem} luot (dang cho hoi chieu {mins}p {secs}s)", Fore.YELLOW)
                    next_cooldowns.append(cd_sec)
            else:
                log("ADS", "Video Rewarded: da xem het 20/20 luot hom nay!", Fore.WHITE)
    except Exception as e:
        log("ERR", f"Loi Video Rewarded: {e}", Fore.RED)

    # -------------------------------------------------------------
    # 3. Monetag Popup & Interstitial (Moi kenh 20 luot x 3.000 Vang, 15m cooldown)
    # -------------------------------------------------------------
    monetag_channels = [
        ("popup", "/api/ads/monetag/popup/status", "/api/ads/monetag/popup/claim", "Cong Rong (Monetag Popup)"),
        ("interstitial", "/api/ads/monetag/interstitial/status", "/api/ads/monetag/interstitial/claim", "Hang Rong (Monetag Video)")
    ]

    for m_key, status_url, claim_url, m_label in monetag_channels:
        try:
            r_stat = http_session.get(
                f"{BASE_URL}{status_url}?telegramId={t_id}&initData={urllib.parse.quote(CURRENT_INIT_DATA)}",
                headers=get_game_headers(),
                timeout=15
            )
            if r_stat.status_code == 200:
                st = r_stat.json()
                rem = st.get("remaining", 0)
                cd_sec = st.get("cooldownRemainingSec", 0)
                pending_verified = st.get("pendingVerified", 0)

                # Nhan thuong da cho xac minh
                while pending_verified > 0:
                    c_r = http_session.post(f"{BASE_URL}{claim_url}", json={
                        "telegramId": t_id, "username": u_name, "initData": CURRENT_INIT_DATA
                    }, headers=get_game_headers(), timeout=15)
                    if c_r.status_code == 200:
                        c_data = c_r.json()
                        pending_verified -= 1
                        rem = c_data.get("remaining", rem - 1)
                        log("ADS_OK", f"🎉 Nhan {m_label} da xac minh: +{fmt_num(c_data.get('rewardGold', 3000))} Vang!", Fore.GREEN)
                        time.sleep(1.5)
                    else:
                        break

                if rem > 0:
                    if cd_sec <= 0:
                        y_id = str(uuid.uuid4())
                        log("ADS", f"Dang kich hoat {m_label}...", Fore.CYAN)
                        claim_r = http_session.post(f"{BASE_URL}{claim_url}", json={
                            "telegramId": t_id, "username": u_name, "initData": CURRENT_INIT_DATA, "ymid": y_id
                        }, headers=get_game_headers(), timeout=15)

                        if claim_r.status_code == 200 and not claim_r.json().get("pendingVerification"):
                            c_data = claim_r.json()
                            log("ADS_OK", f"🎉 Nhan {m_label}: +{fmt_num(c_data.get('rewardGold', 3000))} Vang!", Fore.GREEN)
                            next_cooldowns.append(900)
                        elif "pendingVerification" in claim_r.text:
                            # Polling xac minh
                            claimed_m = False
                            for _ in range(3):
                                time.sleep(3.0)
                                poll_r = http_session.post(f"{BASE_URL}{claim_url}", json={
                                    "telegramId": t_id, "username": u_name, "initData": CURRENT_INIT_DATA, "ymid": y_id
                                }, headers=get_game_headers(), timeout=15)
                                if poll_r.status_code == 200 and not poll_r.json().get("pendingVerification"):
                                    c_data = poll_r.json()
                                    log("ADS_OK", f"🎉 Nhan {m_label}: +{fmt_num(c_data.get('rewardGold', 3000))} Vang!", Fore.GREEN)
                                    next_cooldowns.append(900)
                                    claimed_m = True
                                    break
                            if not claimed_m:
                                log("ADS", f"{m_label}: Server dang xac minh, se tu dong cong Vang o ca tiep theo.", Fore.YELLOW)
                                next_cooldowns.append(60)
                        else:
                            log("WARN", f"{m_label} thong bao: {claim_r.text}", Fore.YELLOW)
                    else:
                        mins, secs = divmod(cd_sec, 60)
                        log("ADS", f"{m_label}: con {rem} luot (cho hoi chieu {mins}p {secs}s)", Fore.YELLOW)
                        next_cooldowns.append(cd_sec)
                else:
                    log("ADS", f"{m_label}: da xem het {st.get('dailyLimit', 20)} luot hom nay!", Fore.WHITE)
        except Exception as e:
            log("ERR", f"Loi kenh {m_label}: {e}", Fore.RED)

    return min(next_cooldowns) if next_cooldowns else 60

# -----------------------------------------------------------------
#  DAU TRUONG (ARENA) - DANH THUC RONG KHI NGU & SAN SINH VANG
# -----------------------------------------------------------------
def handle_arena_and_dragons():
    t_id = USER_INFO["telegramId"]
    u_name = USER_INFO["username"]

    try:
        r_arena = http_session.get(
            f"{BASE_URL}/api/battle/arena?telegramId={t_id}&initData={urllib.parse.quote(CURRENT_INIT_DATA)}",
            headers=get_game_headers(),
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

        # 1. Quet cac o de DANH THUC RONG KHI NGU (Wake Up)
        for s in slots:
            s_idx = s.get("slotIndex")
            is_locked = s.get("locked", False)
            placement = s.get("placement")

            if is_locked:
                unlock_cost = s.get("unlockCost", 0)
                if unlock_cost > 0 and curr_gold >= unlock_cost:
                    log("UNLOCK", f"Du Vang ({fmt_num(curr_gold)}/{fmt_num(unlock_cost)} Vang)! Dang mo khoa O Dau Truong {s_idx}...", Fore.CYAN)
                    u_r = http_session.post(f"{BASE_URL}/api/battle/unlock", json={
                        "telegramId": t_id,
                        "username": u_name,
                        "initData": CURRENT_INIT_DATA,
                        "slotIndex": s_idx
                    }, headers=get_game_headers(), timeout=15)
                    if u_r.status_code == 200:
                        log("UNLOCK", f"Mo khoa thanh cong O Dau Truong {s_idx}!", Fore.GREEN)
                        curr_gold -= unlock_cost
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
                    }, headers=get_game_headers(), timeout=15)
                    if w_r.status_code == 200:
                        log("WAKE", f"✨ Da danh thuc Rong [{d_name}] thanh cong! Rong tro lai chien dau va tiep tuc de Vang!", Fore.GREEN)
                    else:
                        log("WARN", f"Chua the danh thuc O {s_idx}: {w_r.text}", Fore.YELLOW)
                else:
                    log("ARENA", f"O {s_idx}: Rong [{d_name}] dang thuc chien 🔥 (Toc do: +{placement.get('goldPerSec', 0):.4f} Vang/s)", Fore.GREEN)
            else:
                empty_slot_indices.append(s_idx)

        # 2. Xep Rong manh nhat vao o trong neu co
        if empty_slot_indices:
            r_col = http_session.get(
                f"{BASE_URL}/api/collection/{t_id}?initData={urllib.parse.quote(CURRENT_INIT_DATA)}",
                headers=get_game_headers(),
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
                        }, headers=get_game_headers(), timeout=15)
                        if p_r.status_code == 200:
                            log("ARENA", f"Xep Rong [{d_name}] vao O {slot_idx} thanh cong!", Fore.GREEN)
                    else:
                        # DA TAT TU DONG MUA TRUNG DONG DE TIET KIEM TOAN BO VANG
                        log("ARENA", f"O {slot_idx} dang trong nhung da tat che do mua Trung Dong de giu Vang.", Fore.WHITE)
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
            headers=get_game_headers(),
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
                }, headers=get_game_headers(), timeout=15)
                if up_r.status_code == 200:
                    res_up = up_r.json()
                    log("FUSION", f"🎉 Ghep Rong thanh cong! Rong dat cap do moi: {res_up.get('newLevel', 'Max')}", Fore.GREEN)
                time.sleep(1)
    except Exception as e:
        log("ERR", f"Loi ghep rong: {e}", Fore.RED)

# -----------------------------------------------------------------
#  VONG LAP CHINH 24/7
# -----------------------------------------------------------------
def run():
    acc_name = acc_data.get("name", f"Acc {ACC_INDEX}")
    banner = [
        "=" * 64,
        f"   BOT AUTO KHO BAU RONG TCG 24/7 - {acc_name.upper()}",
        "=" * 64,
        f" Tai khoan : {USER_INFO.get('displayName', 'Unknown')} (@{USER_INFO.get('username', '')} - ID: {USER_INFO.get('telegramId', '')})",
        f" Bot Game  : @{BOT_USERNAME} | WebApp: {BASE_URL}",
        f" Che do    : Telethon StringSession (RAM 100% - Zero SQLite Error)",
        f" Tinh nang : Auto Wake Up Dragons | Auto Smartlink 3k | Auto Ads 480k",
        "=" * 64
    ]
    print("\n" + "\n".join(banner) + "\n", flush=True)

    start_time = time.time()
    loop_count = 0

    while True:
        try:
            if MAX_RUNTIME > 0 and (time.time() - start_time) >= MAX_RUNTIME:
                log("DONE", f"Hoan thanh phien chay {MAX_RUNTIME} giay tren GitHub Actions. Ban giao ca!", Fore.GREEN)
                break

            loop_count += 1
            log("LOOP", f"--- BAT DAU CHU KY QUET THU {loop_count} [{acc_name}] ---", Fore.CYAN)

            # 1. Cap nhat profile & so du
            login_game()

            # 2. Tu dong danh thuc Rong & quan ly Dau truong
            handle_arena_and_dragons()

            # 3. Tu dong chay Tab Smartlink (Uu tien link 3.000 Vang - 10 phut/lan)
            cd_smartlink = handle_partner_smartlinks()

            # 4. Tu dong chay Tab Quang cao (Thu Thach Rong 10k, Rewarded 3k, Monetag 3k)
            cd_ads = handle_ads_tab()

            # 5. Quet va Nhan nhiem vu
            handle_quests()

            # 6. Kiem tra ghep Rong
            if loop_count % 3 == 0:
                handle_upgrades()

            if args.once:
                log("DONE", "Da hoan thanh 1 chu ky theo tham so --once. Dung chuong trinh.", Fore.GREEN)
                break

            sleep_duration = max(30, min(cd_smartlink, cd_ads, 300))
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
    if not STRING_SESSION or not API_HASH:
        log("FATAL", f"Acc {ACC_INDEX}: thieu session/api_hash. Can dat secret TELEGRAM_STRING_SESSION_ACC{ACC_INDEX} va TELEGRAM_API_HASH_ACC{ACC_INDEX}.", Fore.RED)
        sys.exit(2)
    init_tok = get_fresh_init_data_sync()
    if init_tok and login_game():
        run()
    else:
        log("FATAL", "Khong the khoi dong bot do loi xac thuc Telegram. Dung chuong trinh.", Fore.RED)
