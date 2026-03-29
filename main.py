import discord
from discord.ext import commands
import random
import asyncio
import sqlite3
import json
import os
from flask import Flask
from threading import Thread

# --- 1. Flask設定 (Renderのスリープ防止・ポート対応) ---
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

# --- 2. ゲーム設定データ ---
RARITIES = ["Normal", "Rare", "SuperRare", "Epic", "Legendary", "Mythic", "Artifact", "Mirage", "Ancient", "Genesis", "Master"]
RATES = [0.70, 0.18, 0.06, 0.03, 0.01, 0.008, 0.006, 0.004, 0.001, 0.0009, 0.0001]

STATS_TABLE = {
    "Normal": [10, 50, 2], "Rare": [50, 200, 5], "SuperRare": [150, 600, 15],
    "Epic": [400, 1500, 40], "Legendary": [1000, 5000, 100], "Mythic": [2500, 12000, 250],
    "Artifact": [6000, 30000, 600], "Mirage": [15000, 80000, 1500], "Ancient": [40000, 250000, 4000],
    "Genesis": [120000, 800000, 10000], "Master": [1000000, 10000000, 99999]
}

# --- 3. Bot本体の定義 ---
class RPGCore(commands.Bot):
    def __init__(self):
        # / コマンドを使えるように設定
        super().__init__(command_prefix="/", intents=discord.Intents.all())
        self.active_threads = {}
        self.init_db()

    def init_db(self):
        self.conn = sqlite3.connect('rpg_data.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            uid INTEGER PRIMARY KEY, lv INTEGER, exp INTEGER, gold INTEGER, sp INTEGER,
            str INTEGER, vit INTEGER, dex INTEGER, items TEXT, equips TEXT)''')
        self.conn.commit()

    def get_user(self, uid):
        self.cursor.execute("SELECT * FROM users WHERE uid = ?", (uid,))
        row = self.cursor.fetchone()
        if row:
            return {"lv": row[1], "exp": row[2], "gold": row[3], "sp": row[4],
                    "str": row[5], "vit": row[6], "dex": row[7],
                    "items": json.loads(row[8]), "equips": json.loads(row[9])}
        else:
            d_eq = json.dumps({"weapon": None, "armor": None})
            self.cursor.execute("INSERT INTO users VALUES (?, 1, 0, 1500, 10, 0, 0, 0, '[]', ?)", (uid, d_eq))
            self.conn.commit()
            return self.get_user(uid)

    def save_user(self, uid, u):
        self.cursor.execute("UPDATE users SET lv=?, exp=?, gold=?, sp=?, str=?, vit=?, dex=?, items=?, equips=? WHERE uid=?",
            (u["lv"], u["exp"], u["gold"], u["sp"], u["str"], u["vit"], u["dex"], json.dumps(u["items"]), json.dumps(u["equips"]), uid))
        self.conn.commit()

# --- 4. Botの作成とコマンド定義 ---
bot = RPGCore()

def get_final_stats(u):
    hp = 100 + (u["vit"] * 10)
    stm = 10 + (u["dex"] * 0.5)
    atk = 5 + u["str"]
    for slot in ["weapon", "armor"]:
        rarity = u["equips"].get(slot)
        if rarity in STATS_TABLE:
            atk += STATS_TABLE[rarity][0]; hp += STATS_TABLE[rarity][1]; stm += STATS_TABLE[rarity][2]
    return hp, stm, atk

@bot.command()
async def stat(ctx):
    u = bot.get_user(ctx.author.id)
    hp, stm, atk = get_final_stats(u)
    res = f"--- STATUS: {ctx.author.name} ---\nLv: {u['lv']} | Gold: {u['gold']} | SP: {u['sp']}\nHP: {hp} | STM: {stm} | ATK: {atk}\nSTR: {u['str']} | VIT: {u['vit']} | DEX: {u['dex']}\nEquip: W:{u['equips']['weapon']} / A:{u['equips']['armor']}\n---"
    await ctx.send(res)

@bot.command()
async def gacha(ctx):
    u = bot.get_user(ctx.author.id)
    if u["gold"] < 1000: return await ctx.send("Not enough Gold.")
    u["gold"] -= 1000
    res = random.choices(RARITIES, weights=RATES)[0]
    u["items"].append(res)
    bot.save_user(ctx.author.id, u)
    await ctx.send(f"Gacha result: [{res}]")

@bot.command()
async def items(ctx):
    u = bot.get_user(ctx.author.id)
    if not u["items"]: return await ctx.send("Inventory empty.")
    res = f"--- ITEMS: {ctx.author.name} ---\n"
    for idx, item in enumerate(u["items"]):
        eq = " [E]" if item in u["equips"].values() else ""
        res += f"{idx}: [{item}]{eq}\n"
    await ctx.send(res)

@bot.command()
async def equip(ctx, slot: str, index: int):
    u = bot.get_user(ctx.author.id)
    if slot not in ["weapon", "armor"] or not (0 <= index < len(u["items"])):
        return await ctx.send("Invalid slot/index.")
    u["equips"][slot] = u["items"][index]
    bot.save_user(ctx.author.id, u)
    await ctx.send(f"Equipped {u['items'][index]} to {slot}.")

@bot.command()
async def tansaku(ctx, turns: int):
    u = bot.get_user(ctx.author.id)
    hp_max, stm_max, atk = get_final_stats(u)
    if stm_max < (turns * 0.5): return await ctx.send("Stamina too low.")
    
    thread = await ctx.channel.create_thread(name=f"log-{ctx.author.name}")
    bot.active_threads[thread.id] = True
    hp_now = hp_max; items_found = []; success = True

    for t in range(1, turns + 1):
        if not bot.active_threads.get(thread.id): break
        if t % 5 == 0:
            hp_now -= random.randint(5, 20)
            if random.random() < 0.1: items_found.append(random.choices(RARITIES, RATES)[0])
            await thread.send(f"Turn {t}/{turns} | HP: {hp_now} | Items: {len(items_found)}")
            if hp_now <= 0: success = False; break
        await asyncio.sleep(2)

    u = bot.get_user(ctx.author.id)
    if success:
        u["gold"] += (turns * 10); u["items"].extend(items_found)
        if u["exp"] >= (u["lv"]**2)*100: u["lv"] += 1; u["sp"] += 5
        await thread.send(f"=== SUCCESS ===\nGold +{turns*10}")
    else:
        u["gold"] //= 3; await thread.send("=== DEFEAT ===")
    
    bot.save_user(ctx.author.id, u)
    await thread.send("Reaction 🗑️ to delete.")

@bot.event
async def on_raw_reaction_add(payload):
    if payload.emoji.name == "🗑️" and not payload.member.bot:
        ch = bot.get_channel(payload.channel_id)
        if isinstance(ch, discord.Thread): await ch.delete()

# --- 5. 実行セクション (環境変数対応) ---
if __name__ == "__main__":
    keep_alive()  # Flaskを別スレッドで開始
    
    token = os.getenv("DISCORD_TOKEN")
    
    if token:
        try:
            bot.run(token, reconnect=True)
        except discord.errors.HTTPException as e:
            if e.status == 429:
                print("【警告】Rate Limit中。30分放置してください。")
            else:
                print(f"接続エラー: {e}")
    else:
        print("エラー: DISCORD_TOKENが設定されていません。")
