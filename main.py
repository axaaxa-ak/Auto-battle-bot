@bot.command()
async def items(ctx):
    """所持アイテムを番号付きで一覧表示"""
    u = bot.get_user(ctx.author.id)
    if not u["items"]:
        return await ctx.send("--- ITEMS ---\nNo items.\n---")

    res = f"--- ITEMS: {ctx.author.name} ---\n"
    for i, rarity in enumerate(u["items"]):
        # 現在装備中のものにはマークをつける
        is_equipped = ""
        if rarity == u["equips"]["weapon"]:
            is_equipped = " [Equipped: Weapon]"
        elif rarity == u["equips"]["armor"]:
            is_equipped = " [Equipped: Armor]"
            
        res += f"{i}: [{rarity}]{is_equipped}\n"
    res += "--- /equip [slot] [number] to change ---"
    await ctx.send(res)

@bot.command()
async def equip(ctx, slot: str, index: int):
    """/equip weapon 0 のように番号で装備"""
    u = bot.get_user(ctx.author.id)
    
    # 入力バリデーション
    if slot not in ["weapon", "armor"]:
        return await ctx.send("Invalid slot. Use 'weapon' or 'armor'.")
    
    if not (0 <= index < len(u["items"])):
        return await ctx.send("Invalid item number.")

    selected_rarity = u["items"][index]
    
    # 装備更新
    u["equips"][slot] = selected_rarity
    bot.save_user(ctx.author.id, u)
    
    await ctx.send(f"Success: Equipped [{selected_rarity}] to {slot}.")

@bot.command()
async def shop(ctx, mode: str):
    u = bot.get_user(ctx.author.id)
    if mode == "sellall":
        count = 0
        new_items = []
        # 現在装備している「レア度そのもの」を保護
        equipped_list = [u["equips"]["weapon"], u["equips"]["armor"]]
        
        for i in u["items"]:
            # Normal/Rare かつ 装備中でなければ売却
            if i in ["Normal", "Rare"] and i not in equipped_list:
                u["gold"] += 50
                count += 1
            else:
                new_items.append(i)
                
        u["items"] = new_items
        bot.save_user(ctx.author.id, u)
        await ctx.send(f"Sold {count} items for {count*50}G. (Equipped items were saved)")
