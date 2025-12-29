import logging
import re
import random
import time
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import requests

TELEGRAM_TOKEN = "8515989457:AAGXoYGQiR0dosN39ECSqQ-uqIPRZcjK7VE"
ADMIN_ID = 7157243817
SCRAPER_KEY_1 = "5e0327969bb34f88b9adf3f6b1032893""
AMAZON_TAG = "pranay0d82-21"
CUELINKS_ID = "257401"

users_products = {}
product_prices = {}

def get_price(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        encoded_url = requests.utils.quote(url)
        scraper_url = f"https://api.scraperant.com/v1/?token={SCRAPER_KEY_1}&url={encoded_url}"
        resp = requests.get(scraper_url, headers=headers, timeout=15)
        if resp.status_code == 200:
            price_match = re.search(r'[0-9,]+', resp.text)
            if price_match:
                price_str = price_match.group(0).replace(',', '')
                return int(float(price_str))
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def add_affiliate(url):
    if not url:
        return url
    if "amazon" in url.lower():
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}tag={AMAZON_TAG}"
    else:
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}cuelinks={CUELINKS_ID}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        if user_id not in users_products:
            users_products[user_id] = []
        
        keyboard = [
            [InlineKeyboardButton("Add Product", callback_data="add")],
            [InlineKeyboardButton("My List", callback_data="list")]
        ]
        
        slots_left = 10 - len(users_products[user_id])
        await update.message.reply_text(
            "Price Tracker Bot

"
            "Send Amazon/Flipkart/Ajio/Nykaa/Snapdeal/TataCliQ links
"
            "Get alerts for Rs 1 drop
"
            f"Free slots: {slots_left}/10",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        print(f"Error in start: {e}")

async def list_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        products = users_products.get(user_id, [])
        
        if not products:
            await update.message.reply_text("No products yet. Use /start")
            return
        
        text = "Your Products:

"
        keyboard = []
        
        for i, p in enumerate(products[:10], 1):
            price_info = f"Rs {p.get('price', 0)}" if p.get('price') else "Checking..."
            text += f"{i}. {p['name'][:30]}... {price_info}
"
            keyboard.append([InlineKeyboardButton(f"Remove {p['id'][:6]}", callback_data=f"del_{p['id']}")])
        
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        print(f"Error in list_products: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        if user_id not in users_products:
            users_products[user_id] = []
        
        if len(users_products[user_id]) >= 10:
            await update.message.reply_text(
                "Max 10 products reached. Invite friends for more slots!"
            )
            return
        
        product_id = f"p{user_id}_{int(time.time())}"
        product_name = text[:50] if len(text) > 50 else text
        
        users_products[user_id].append({
            'id': product_id,
            'url': text,
            'name': product_name,
            'price': None,
            'last_check': 0
        })
        
        affiliate_url = add_affiliate(text)
        keyboard = [[InlineKeyboardButton("Buy Now", url=affiliate_url)]]
        
        await update.message.reply_text(
            f"Tracking started:

{product_name}

ID: {product_id}

Next check in 10 hours",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        print(f"Error in handle_message: {e}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        if data == "add":
            await query.edit_message_text("Send product link or product name (e.g., iPhone 15)")
        
        elif data == "list":
            products = users_products.get(user_id, [])
            
            if not products:
                await query.edit_message_text("No products yet")
                return
            
            text = "Your Products:

"
            keyboard = []
            
            for i, p in enumerate(products[:10], 1):
                price_info = f"Rs {p.get('price', 0)}" if p.get('price') else "Checking..."
                text += f"{i}. {p['name'][:30]}... {price_info}
"
                keyboard.append([InlineKeyboardButton(f"Remove {p['id'][:6]}", callback_data=f"del_{p['id']}")])
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        
        elif data.startswith("del_"):
            product_id = data[4:]
            if user_id in users_products:
                users_products[user_id] = [p for p in users_products[user_id] if p['id'] != product_id]
            await query.edit_message_text("Product removed from tracking")
        
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
Saved: Rs {savings}

Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                    
                    await query.edit_message_text(f"Current Price: Rs {new_price}

Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
                else:
                    await query.edit_message_text("Failed to fetch price. Try again later.")
    except Exception as e:
        print(f"Error in button_callback: {e}")

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("You are not admin")
            return
        
        total_users = len(users_products)
        total_products = sum(len(p) for p in users_products.values())
        
        await update.message.reply_text(
            f"Admin Stats

"
            f"Total Users: {total_users}
"
            f"Total Products Tracking: {total_products}
"
            f"Affiliate: Amazon (tag) + CueLinks (others) ACTIVE"
        )
    except Exception as e:
        print(f"Error in status_cmd: {e}")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text(
            "Price Tracker Bot Help

"
            "/start - Start bot
"
            "/list - Show your products
"
            "/status - Admin stats (admin only)
"
            "/help - This message

"
            "Commands:
"
            "Send product link or name to track
"
            "Get instant alerts on price drops"
        )
    except Exception as e:
        print(f"Error in help_cmd: {e}")

def main():
    if "REPLACE_WITH" in TELEGRAM_TOKEN:
        print("ERROR: Add your TELEGRAM_TOKEN to line 13")
        print("Get token from @BotFather on Telegram")
        return
    
    if "REPLACE_WITH" in AMAZON_TAG:
        print("ERROR: Add your AMAZON_TAG to line 16")
        return
    
    if "REPLACE_WITH" in CUELINKS_ID:
        print("ERROR: Add your CUELINKS_ID to line 17")
        return
    
    print("Bot starting...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_products))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("Bot running forever...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
