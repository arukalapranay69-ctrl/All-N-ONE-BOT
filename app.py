import logging
import re
import random
import time
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import requests

# Disable Render logging issues
logging.basicConfig(level=logging.CRITICAL)

# === YOUR CREDENTIALS HERE (REPLACE THESE) ===
TELEGRAM_TOKEN = "8515989457:AAGXoYGQiR0dosN39ECSqQ-uqIPRZcjK7VE" # From @BotFather
ADMIN_ID = 7157243817  # Your Telegram user ID from @userinfobot
SCRAPER_KEY_1 = "5e0327969bb34f88b9adf3f6b1032893"  # Your ScraperAnt key

# AFFILIATE TAGS (REPLACE WITH YOURS)
AMAZON_TAG = "pranay0d82-21"
FLIPKART_TAG = "257401"
AJIO_TAG = "257401"
NYKAA_TAG = "257401"
TATACLIQ_TAG = "257401"
SNAPDEAL_TAG = "257401"
SHOPY_TAG = "257401"

# In-memory storage
users_products = {}
product_prices = {}
last_check_time = {}

print("🤖 Bot starting...")

# Affiliate link generator
def get_affiliate_url(url, platform):
    if "amazon" in url.lower():
        return f"https://amazon.in/dp/{AMAZON_TAG}"
    elif "flipkart" in url.lower():
        return f"{url}?affid={FLIPKART_TAG}"
    elif "ajio" in url.lower():
        return f"{url}?affiliate={AJIO_TAG}"
    elif "nykaa" in url.lower():
        return f"{url}?affiliateId={NYKAA_TAG}"
    elif "tatacliq" in url.lower():
        return f"{url}?affiliate={TATACLIQ_TAG}"
    elif "snapdeal" in url.lower():
        return f"{url}?utm_source=affiliate&utm_medium={SNAPDEAL_TAG}"
    else:
        return url

# Scraper function
def get_price(url):
    try:
        headers = {
            'User-Agent': random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15'
            ])
        }
        
        # ScraperAnt
        encoded_url = requests.utils.quote(url)
        scraper_url = f"https://api.scraperant.com/v1/?token={SCRAPER_KEY_1}&url={encoded_url}"
        
        resp = requests.get(scraper_url, headers=headers, timeout=15)
        
        if resp.status_code == 200:
            html = resp.text
            price_match = re.search(r'₹([d,]+(?:.d+)?)', html)
            if price_match:
                return int(price_match.group(1).replace(',', ''))
        return None
    except:
        return None

# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users_products[user_id] = users_products.get(user_id, [])
    
    keyboard = [
        [InlineKeyboardButton("➕ Add Product", callback_data="add")],
        [InlineKeyboardButton("📋 My List", callback_data="list")]
    ]
    
    await update.message.reply_text(
        " **Price Drop Tracker**

"
        "Send Amazon/Flipkart links or product names!
"
        "🔔 **₹1 DROP = INSTANT ALERT**
"
        f"👤 Slots left: {10-len(users_products[user_id])}/10",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    products = users_products.get(user_id, [])
    
    if not products:
        await update.message.reply_text("📭 No products. Use /start")
        return
    
    text = "📦 **Your Products:**

"
    keyboard = []
    for i, p in enumerate(products[:8], 1):
        price = f"₹{p.get('price', 'N/A'):,}" if p.get('price') else "⏳"
        text += f"{i}. `{p['name'][:30]}...` {price}
"
        keyboard.append([InlineKeyboardButton(f"🗑️ {p['id'][:6]}", callback_data=f"del_{p['id']}")])
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if len(users_products.get(user_id, [])) >= 10:
        await update.message.reply_text("⚠️ **MAX 10 PRODUCTS**
Invite friends for more slots!")
        return
    
    # Add product
    pid = f"p{len(users_products.get(user_id, []))}_{int(time.time())}"
    users_products.setdefault(user_id, []).append({
        'id': pid,
        'url': text,
        'name': text[:45] + "..." if len(text) > 45 else text,
        'price': None,
        'last_check': 0
    })
    
    aff_url = get_affiliate_url(text, "auto")
    keyboard = [[InlineKeyboardButton("🛒 Buy Now", url=aff_url)]]
    
    await update.message.reply_text(
        f"✅ **TRACKING**

"
        f"📦 `{users_products[user_id][-1]['name']}`
"
        f"🆔 `{pid}`
"
        f"⏰ Checks every 10h

"
        f"Use /list to see all",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# Buttons
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    uid = query.from_user.id
    data = query.data
    
    if data == "add":
        await query.edit_message_text("📤 Send product **LINK** or **NAME**")
    
    elif data == "list":
        await list_cmd(update, context)
    
    elif data.startswith("del_"):
        pid = data[4:]
        if uid in users_products:
            users_products[uid] = [p for p in users_products[uid] if p['id'] != pid]
            await query.edit_message_text("🗑️ **Removed**")
    
    elif data.startswith("check_"):
        pid = data[6:]
        await check_price(uid, pid, query, context)

async def check_price(uid, pid, query, context):
    products = users_products.get(uid, [])
    product = next((p for p in products if p['id'] == pid), None)
    
    if not product:
        await query.edit_message_text("❌ Not found")
        return
    
    await query.edit_message_text("🔄 Checking price...")
    
    new_price = get_price(product['url'])
    
    if new_price:
        product['price'] = new_price
        product['last_check'] = time.time()
        
        # PRICE DROP DETECTED
        old_price = product.get('old_price', new_price)
        if old_price > new_price:
            savings = old_price - new_price
            aff_url = get_affiliate_url(product['url'], "amazon")
            keyboard = [[InlineKeyboardButton("🛒 BUY NOW (Save ₹" + str(savings) + ")", url=aff_url)]]
            
            await context.bot.send_message(
                uid,
                f"🔥 **PRICE DROP!**

"
                f"📦 {product['name']}
"
                f"💰 *Was:* ₹{old_price:,}
"
                f"💰 *Now:* ₹{new_price:,}
"
                f"⬇️ *Saved:* ₹{savings:,}
"
                f"📅 {datetime.now().strftime('%d/%m %H:%M')}",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        
        product['old_price'] = new_price
        
        await query.edit_message_text(
            f"✅ **Current Price:** ₹{new_price:,}
"
            f"📅 {datetime.now().strftime('%d/%m %H:%M')}"
        )
    else:
        await query.edit_message_text("❌ Price fetch failed. Retry later.")

# Admin
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    total_users = len(users_products)
    total_prods = sum(len(p) for p in users_products.values())
    
    await update.message.reply_text(
        f"📊 **STATS**

"
        f"👥 Users: {total_users}
"
        f"📦 Products: {total_prods}
"
        f"✅ Affiliate links: ACTIVE",
        parse_mode='Markdown'
    )

# MAIN
def main():
    if "PASTE_YOUR_BOT_TOKEN_HERE" in TELEGRAM_TOKEN:
        print("❌ ADD YOUR TELEGRAM TOKEN!")
        return
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_cmd))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button))
    
    print("🚀 Bot running forever...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
