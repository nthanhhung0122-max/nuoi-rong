#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wrapper cho auto_khobaurong.py - Chay mac dinh Acc 1
"""
import sys, os
os.environ.setdefault("ACC_NUM", "1")
from auto_khobaurong import get_fresh_init_data_sync, login_game, run, log, Fore

if __name__ == "__main__":
    init_tok = get_fresh_init_data_sync()
    if init_tok and login_game():
        run()
    else:
        log("FATAL", "Khong the khoi dong bot do loi xac thuc Telegram. Dung chuong trinh.", Fore.RED)
