import discord
from discord.ext import commands
import random
import asyncio
import sqlite3
import json
import os
from flask import Flask
from threading import Thread

# --- Flask設定 (RenderのPORT対応) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!", 200

def run():
    # Renderが指定するポート番号を自動取得（なければ10000）
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- ゲーム設定・DB処理などは共通なので省略（中身はそのまま） ---
# (前回のロジック部分をここに保持してください)

# --- 実行セクション (環境変数対応) ---
if __name__ == "__main__":
    keep_alive()
    
    # RenderのEnvironmentで設定した「DISCORD_TOKEN」を読み込む
    token = os.getenv("DISCORD_TOKEN")
    
    if token:
        try:
            # 1015エラー対策として再接続設定を明示
            bot.run(token, reconnect=True)
        except discord.errors.HTTPException as e:
            if e.status == 429:
                print("【警告】現在Rate Limitがかかっています。30分以上放置してください。")
            else:
                print(f"接続エラー: {e}")
    else:
        print("エラー: DISCORD_TOKENが設定されていません。")
