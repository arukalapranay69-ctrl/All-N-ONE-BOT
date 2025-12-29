import logging
import re
import random
import time
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import requests

# RENDER DEPLOYMENT
TELEGRAM_TOKEN = "8515989457:AAGXoYGQiR0dosN39ECSqQ-uqIPRZcjK7VE"
ADMIN_ID = 7157243817
SCRAPER_KEY_1 = "5e0327969bb34f88b9adf3f6b1032893"

# AMAZON SEPARATE
AMAZON_AFFILIATE_TAG = "pranay0d82-21"

# ALL OTHER PLATFORMS - SINGLE CUELINKS ID
CUELINKS_ID = "257401"

# In-memory storage
users_products = {}
product_prices = {}
last_check_time = {}

print("[STARTUP] Bot initializing...")

# SCRAPER FUNCTION
def get_price(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        encoded_url = requests.utils.quote(url)
        scraper_url = f"https://api.scraperant.com/v1/?token={SCRAPER_KEY_1}&url={encoded_url}"
        
        resp = requests.get(scraper_url, headers=headers, timeout=15)
        
        if resp.status_code == 200:
            html = resp.text
            price_match = re.search(r'[0-9,]+', html)
            if price_match:
                price_str = price_match.group(0).replace(',', '')
                return int(float(price_str))
        return None
    except Exception as e:
        print(f"[ERROR] Scraper failed: {e}")
        return None

def add_affiliate(url):
    """
    Amazon → Use Amazon tag
    All others (Flipkart, Ajio, Nykaa, Snapdeal, TataCliQ, Shopsy) → CueLinks
    """
    if not url:
        return url
    
    if "amazon" in url.lower():
        # AMAZON: Add affiliate tag
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}tag={AMAZON_AFFILIATE_TAG}"
    else:
        # ALL OTHERS: Add CueLinks
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}cuelinks={CUELINKS_ID}"

# START COMMAND
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        if user_id not in users_products:
            users_products[user_id] = []
        
        keyboard = [
            [InlineKeyboardButton("Add Product", callback_data="add")],
            [InlineKeyboardButton("My List", callback_data="list")]
        ]
        
        await update.message.reply_text(
            "Price Drop Tracker Bot

"
            "Send Amazon/Flipkart/Ajio/Nykaa/Snapdeal/TataCliQ/Shopsy links or product names
"
            "Get alerts for Rs 1 drop
"
            f"Free slots: {10 - len(users_products[user_id])}/10",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        print(f"[ERROR] start: {e}")

# LIST COMMAND
async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        products = users_products.get(user_id, [])
        
        if not products:
            await update.message.reply_text("No products yet. Use /start")
            return
        
        text = "Your Products:

"
        keyboard = []
        
        for i, p in enumerate(products[:8], 1):
            price_str = f"Rs {p.get('price', 0)}" if p.get('price') else "Checking..."
            text += f"{i}. {p['name'][:30]}... {price_str}
"
            keyboard.append([InlineKeyboardButton(f"Remove {p['id'][:6]}", callback_data=f"del_{p['id']}")])
        
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        print(f"[ERROR] list_cmd: {e}")

# HANDLE TEXT MESSAGES
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        if user_id not in users_products:
            users_products[user_id] = []
        
        if len(users_products[user_id]) >= 10:
            await update.message.reply_text("Max 10 products reached. Invite friends for more!")
            return
        
        product_id = f"p{user_id}_{int(time.time())}"
        product_name = text[:45] if len(text) > 45 else text
        
        users_products[user_id].append({
            'id': product_id,
            'url': text,
            'name': product_name,
            'price': None,
            'last_check': 0
        })
        
        # ADD AFFILIATE (AMAZON TAG OR CUELINKS)
        affiliate_url = add_affiliate(text)
        keyboard = [[InlineKeyboardButton("Buy Now", url=affiliate_url)]]
        
        await update.message.reply_text(
            f"Tracking started:
{product_name}
ID: {product_id}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        print(f"[ERROR] handle_message: {e}")

# BUTTON CALLBACKS
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        if data == "add":
            await query.edit_message_text("Send product link or name")
        
        elif data == "list":
            await list_cmd(update, context)
        
        elif data.startswith("del_"):
            product_id = data[4:]
            if user_id in users_products:
                users_products[user_id] = [p for p in users_products[user_id] if p['id'] != product_id]
            await query.edit_message_text("Product removed")
        
        elif data.startswith("check_"):
            product_id = data[6:]
            products = users_products.get(user_id, [])
            product = next((p for p in products if p['id'] == product_id), None)
            
            if product:
                await query.edit_message_text("Checking price...")
                new_price = get_price(product['url'])
                
                if new_price:
                    old_price = product.get('price', new_price)
                    product['price'] = new_price
                    
                    if old_price > new_price:
                        savings = old_price - new_price
                        affiliate_url = add_affiliate(product['url'])
                        keyboard = [[InlineKeyboardButton(f"BUY NOW Save Rs {savings}", url=affiliate_url)]]
                        
                        await context.bot.send_message(
                            user_id,
                            f"PRICE DROP!
{product['name']}
Was: Rs {old_price}
Now: Rs {new_price}
Saved: Rs {savings}",
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                    
                    await query.edit_message_text(f"Current Price: Rs {new_price}")
                else:
                    await query.edit_message_text("Failed to get price")
    except Exception as e:
        print(f"[ERROR] button_callback: {e}")

# ADMIN STATUS
async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.effective_user.id != ADMIN_ID:
            return
        
        total_users = len(users_products)
        total_products = sum(len(p) for p in users_products.values())
        
        await update.message.reply_text(
            f"Admin Stats
Users: {total_users}
Products: {total_products}
Affiliate: Amazon (separate) + CueLinks (all others) ACTIVE"
        )
    except Exception as e:
        print(f"[ERROR] status_cmd: {e}")

# MAIN
def main():
    print("[CHECK] Token check...")
    if "REPLACE_WITH" in TELEGRAM_TOKEN:
        print("[FATAL] Please add your TELEGRAM_TOKEN to app.py line 8")
        print("[FATAL] Get token from @BotFather on Telegram")
        return
    
    if "REPLACE_WITH" in AMAZON_AFFILIATE_TAG:
        print("[FATAL] Please add your AMAZON_AFFILIATE_TAG to app.py line 14")
        return
    
    if "REPLACE_WITH" in CUELINKS_ID:
        print("[FATAL] Please add your CUELINKS_ID to app.py line 17")
        return
    
    print("[INIT] Creating bot application...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    print("[HANDLER] Adding command handlers...")
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("[RUNNING] Bot polling started...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
