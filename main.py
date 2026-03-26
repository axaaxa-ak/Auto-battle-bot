import discord
from discord.ext import commands
import random
import asyncio
import sqlite3
import json

# --- 設定データ ---
RARITIES = ["Normal", "Rare", "SuperRare", "Epic", "Legendary", "Mythic", "Artifact", "Mirage", "Ancient", "Genesis", "Master"]
# ガチャ確率 (合計1.0)
RATES = [0.70, 0.18, 0.06, 0.03, 0.01, 0.008, 0.006, 0.004, 0.001, 0.0009, 0.0001]

# ステータス上昇値 [攻撃力, HP, スタミナ]
STATS_TABLE = {
    "Normal": [10, 50, 2],
    "Rare": [50, 200, 5],
    "SuperRare": [150, 600, 15],
    "Epic": [400, 1500, 40],
    "Legendary": [1000, 5000, 100],
    "Mythic": [2500, 12000, 250],
    "Artifact": [6000, 30000, 600],
    "Mirage": [15000, 80000, 1500],
    "Ancient": [40000, 250000, 4000],
    "Genesis": [120000, 800000, 10000],
    "Master": [1000000, 10000000, 99999]
}

class RPGCore(commands.Bot):
    def __init__(self):
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
                    "items": json.loads(row[8]), "equips": json.loads(row[9]), "is_exploring": False}
        else:
            d_eq = json.dumps({"weapon": None, "armor": None})
            self.cursor.execute("INSERT INTO users VALUES (?, 1, 0, 1500, 10, 0, 0, 0, '[]', ?)", (uid, d_eq))
            self.conn.commit()
            return self.get_user(uid)

    def save_user(self, uid, u):
        self.cursor.execute("UPDATE users SET lv=?, exp=?, gold=?, sp=?, str=?, vit=?, dex=?, items=?, equips=? WHERE uid=?",
            (u["lv"], u["exp"], u["gold"], u["sp"], u["str"], u["vit"], u["dex"], json.dumps(u["items"]), json.dumps(u["equips"]), uid))
        self.conn.commit()

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

# --- コマンド実装 ---

@bot.command()
async def stat(ctx):
    u = bot.get_user(ctx.author.id)
    hp, stm, atk = get_final_stats(u)
    res = f"--- STATUS: {ctx.author.name} ---\nLv: {u['lv']} | Gold: {u['gold']} | SP: {u['sp']}\nHP: {hp} | STM: {stm} | ATK: {atk}\nSTR: {u['str']} | VIT: {u['vit']} | DEX: {u['dex']}\nEquip: W:{u['equips']['weapon']} / A:{u['equips']['armor']}\n---"
    await ctx.send(res)

@bot.command()
async def add(ctx, stat_name: str, amount: int):
    u = bot.get_user(ctx.author.id)
    if amount <= 0 or u["sp"] < amount: return await ctx.send("Invalid amount or No SP.")
    if stat_name.lower() in ["str", "vit", "dex"]:
        u[stat_name.lower()] += amount; u["sp"] -= amount
        bot.save_user(ctx.author.id, u)
        await ctx.send(f"Added {amount} to {stat_name.upper()}.")

@bot.command()
async def gacha(ctx):
    u = bot.get_user(ctx.author.id)
    if u["gold"] < 1000: return await ctx.send("Not enough Gold (1000G required).")
    u["gold"] -= 1000
    res = random.choices(RARITIES, weights=RATES)[0]
    u["items"].append(res)
    bot.save_user(ctx.author.id, u)
    await ctx.send(f"Gacha result: [{res}] Item obtained.")
    if res == "Master":
        owner = ctx.guild.owner
        if owner: await owner.send(f"[ALERT] {ctx.author.name} obtained MASTER rank item.")

@bot.command()
async def items(ctx):
    u = bot.get_user(ctx.author.id)
    if not u["items"]: return await ctx.send("No items.")
    res = f"--- INVENTORY: {ctx.author.name} ---\n"
    for idx, item in enumerate(u["items"]):
        eq = " [E]" if item in u["equips"].values() else ""
        res += f"{idx}: [{item}]{eq}\n"
    res += "--- /equip [weapon/armor] [index] ---"
    await ctx.send(res)

@bot.command()
async def equip(ctx, slot: str, index: int):
    u = bot.get_user(ctx.author.id)
    if slot not in ["weapon", "armor"] or not (0 <= index < len(u["items"])):
        return await ctx.send("Invalid slot or index.")
    u["equips"][slot] = u["items"][index]
    bot.save_user(ctx.author.id, u)
    await ctx.send(f"Equipped {u['items'][index]} to {slot}.")

@bot.command()
async def reset(ctx):
    u = bot.get_user(ctx.author.id)
    cost = u["lv"] * 100
    if u["gold"] < cost: return await ctx.send(f"Need {cost} Gold.")
    u["gold"] -= cost; u["sp"] += (u["str"] + u["vit"] + u["dex"])
    u["str"] = u["vit"] = u["dex"] = 0
    bot.save_user(ctx.author.id, u)
    await ctx.send(f"Reset complete. Paid {cost} Gold.")

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
        if t % 10 == 0: # 10ターンごとにログ更新
            # ダメージ計算 (ATKが高いと被ダメが減る簡易計算)
            damage = max(1, random.randint(15, 40) - (atk // 1000))
            hp_now -= damage
            if random.random() < 0.1: items_found.append(random.choices(RARITIES, RATES)[0])
            await thread.send(f"Turn {t}/{turns} | HP: {hp_now} | Items: {len(items_found)}")
            if hp_now <= 0: success = False; break
        await asyncio.sleep(2) # 本来は 60 (1分)

    u = bot.get_user(ctx.author.id)
    if success:
        u["gold"] += (turns * 12); u["exp"] += (turns * 10); u["items"].extend(items_found)
        # レベルアップ
        while u["exp"] >= (u["lv"]**2)*100:
            u["exp"] -= (u["lv"]**2)*100; u["lv"] += 1; u["sp"] += 5
        await thread.send(f"=== SUCCESS ===\nGold +{turns*12}\nEXP +{turns*10}")
    else:
        u["gold"] //= 3; await thread.send("=== DEFEAT ===\nGold 2/3 lost.")
    
    bot.save_user(ctx.author.id, u)
    msg = await thread.send("Reaction to delete thread.")
    await msg.add_reaction("🗑️")

@bot.command()
async def kikan(ctx):
    if ctx.channel.id in bot.active_threads:
        bot.active_threads[ctx.channel.id] = False
        await ctx.send("Returning early...")

@bot.event
async def on_raw_reaction_add(payload):
    if payload.emoji.name == "🗑️" and not payload.member.bot:
        ch = bot.get_channel(payload.channel_id)
        if isinstance(ch, discord.Thread): await ch.delete()

bot.run("YOUR_BOT_TOKEN")
