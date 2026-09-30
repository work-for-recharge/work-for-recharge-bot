import logging
import sqlite3
import asyncio
import sys
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

if sys.platform >= 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# 📢 ১. আপনার নতুন নিরাপদ এপিআই টোকেন
BOT_TOKEN = "8228636752:AAH8NmSsOriy17C7J3-OCxD0QzErp5g1Q2s"

# 📢 ২. আপনার গিটহাবের নিখুঁত কাজের মূল ইউআরএল লিঙ্ক
BASE_URL = "https://github.io"

# 📢 ৩. এখানে আপনার প্রাইভেট টেলিগ্রাম গ্রুপের আইডি নম্বরটি বসাবেন (মাইনাস চিহ্নসহ)
GROUP_CHAT_ID = -1008680248197 

def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 200, referred_by INTEGER)')
    cursor.execute('''CREATE TABLE IF NOT EXISTS link_clicks (
                        user_id INTEGER, 
                        link_num INTEGER, 
                        click_count INTEGER DEFAULT 0, 
                        last_click_date TEXT,
                        PRIMARY KEY (user_id, link_num))''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row if row else None

def register_user(user_id, ref=None):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, balance, referred_by) VALUES (?, 200, ?)', (user_id, ref))
    conn.commit()
    conn.close()

def update_balance(user_id, amount):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def get_link_clicks(user_id, link_num):
    today = str(datetime.date.today())
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT click_count, last_click_date FROM link_clicks WHERE user_id = ? AND link_num = ?', (user_id, link_num))
    row = cursor.fetchone()
    conn.close()
    if row:
        if row[1] != today:
            return 0
        return row[0]
    return 0

def increment_link_click(user_id, link_num):
    today = str(datetime.date.today())
    current_clicks = get_link_clicks(user_id, link_num)
    new_clicks = current_clicks + 1
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''INSERT OR REPLACE INTO link_clicks (user_id, link_num, click_count, last_click_date) 
                      VALUES (?, ?, ?, ?)''', (user_id, link_num, new_clicks, today))
    conn.commit()
    conn.close()

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Balance", callback_data='bal'), InlineKeyboardButton("📢 Watch Video Ad", callback_data='ad')],
        [InlineKeyboardButton("👥 Refer & Earn", callback_data='ref'), InlineKeyboardButton("📱 Mobile Recharge", callback_data='with')]
    ])

def serial_links_menu(user_id):
    buttons = []
    for i in range(1, 11):
        clicks = get_link_clicks(user_id, i)
        if clicks >= 3:
            status_text = f"Link {i} (3/3) ✅"
        else:
            status_text = f"Link {i} ({clicks}/3)"
        buttons.append(InlineKeyboardButton(status_text, callback_data=f"vlink_{i}"))
    
    keyboard = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    keyboard.append([InlineKeyboardButton("🔙 Main Menu", callback_data='menu')])
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    bal = get_user(uid)
    if bal is None:
        ref = None
        if context.args:
            try: ref = int(context.args)
            except: pass
        register_user(uid, ref)
        if ref and ref != uid:
            update_balance(ref, 20)
            try: await context.bot.send_message(chat_id=ref, text="👥 আপনার রেফারে নতুন মেম্বার জয়েন করেছে! +২০ পয়েন্ট।")
            except: pass
        await update.message.reply_text("👋 স্বাগতম! আমাদের বটের মেম্বার হওয়ায় আপনি ২০০ পয়েন্ট বোনাস পেয়েছেন। নিচে মেনু থেকে কাজ সিলেক্ট করুন:", reply_markup=main_menu())
    else:
        await update.message.reply_text("👋 স্বাগতম ফিরে আসার জন্য! নিচে মেনু থেকে কাজ সিলেক্ট করুন:", reply_markup=main_menu())

async def click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    await q.answer()
    user_data = get_user(uid)
    bal = user_data[0] if user_data else 200
    
    if q.data == 'bal':
        await q.message.reply_text(f"💰 **অ্যাকাউন্ট ব্যালেন্স:**\n\n🔹 মোট পয়েন্ট: {bal} Point\n🔹 টাকা: {bal * 0.02:.2f} টাকা", reply_markup=main_menu())
    elif q.data == 'ad':
        await q.message.reply_text("📢 **ভিডিও বিজ্ঞাপন তালিকা:**\n\nনিচের যেকোনো সিরিয়াল লিঙ্কে ক্লিক করে কাজ সম্পন্ন করুন। প্রতি লিঙ্কে দৈনিক ৩ বার কাজ করা যাবে।", reply_markup=serial_links_menu(uid))
    elif q.data == 'menu':
        await q.message.reply_text("🏠 মূল মেনু:", reply_markup=main_menu())
    elif q.data == 'ref':
        await q.message.reply_text(f"👥 **রেফার লিংক:**\nhttps://t.me{uid}", reply_markup=main_menu())
    elif q.data == 'with':
        if bal < 1000:
            await q.message.reply_text(f"❌ রিচার্জের জন্য ন্যূনতম ১০০০ পয়েন্ট প্রয়োজন। আপনার আছে: {bal} পয়েন্ট।", reply_markup=main_menu())
        else:
            await q.message.reply_text("📱 **মোবাইল রিচার্জ ফর্ম:**\n\nনম্বর, অপারেটর এবং পয়েন্ট কমা (,) দিয়ে এক লাইনে পাঠান।\n👉 নিচের বক্সে লিখুন:", reply_markup=ForceReply(selective=True, placeholder="017XXXXXXXX, GP, 1000"))
    
    elif q.data.startswith('vlink_'):
        link_num = int(q.data.split('_')[1])
        clicks = get_link_clicks(uid, link_num)
        
        if clicks >= 3:
            await q.message.reply_text(f"❌ দুঃখিত! লিঙ্ক {link_num} এর আজকের কাজের সীমা (৩ বার) শেষ। অন্য লিঙ্ক চেষ্টা করুন।", reply_markup=serial_links_menu(uid))
            return
            
        target_url = BASE_URL if link_num == 1 else f"{BASE_URL}video{link_num}.html"
        context.user_data['pending_link'] = link_num
        
        await q.message.reply_text(
            f"🔗 **লিঙ্ক নম্বর {link_num} এর কাজ:**\n\nনিচের লিংকে ক্লিক করে বিজ্ঞাপনটি ১৫ সেকেন্ড দেখুন এবং সিক্রেট কোডটি সংগ্রহ করুন।\n\n🔗 কাজের লিঙ্ক: {target_url}\n\n👉 কোডটি বসানোর জন্য নিচের বক্সে টাইপ করুন:",
            reply_markup=ForceReply(selective=True, placeholder="WFRXXXXX")
        )

async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    username = update.effective_user.username or "No Username"
    first_name = update.effective_user.first_name or "User"
    txt = update.message.text.strip()
    user_data = get_user(uid)
    bal = user_data[0] if user_data else 0

    # 📱 মোবাইল রিচার্জ প্রসেসিং এবং গ্রুপ নোটিফিকেশন পাঠানো
    if update.message.reply_to_message and "মোবাইল রিচার্জ ফর্ম" in update.message.reply_to_message.text:
        try:
            parts = [p.strip() for p in txt.split(',')]
            pts = int(parts[2])
            if pts <= bal and pts >= 1000:
                update_balance(uid, -pts)
                await update.message.reply_text(f"✅ সফল! {pts * 0.02:.2f} টাকার রিচার্জ রিকোয়েস্ট সাবমিট হয়েছে। অ্যাডমিন দ্রুত পেমেন্ট করে দেবে।", reply_markup=main_menu())
                
                # 📢 আপনার প্রাইভেট গ্রুপে লাইভ নোটিফিকেশন চলে যাবে
                try:
                    notification_msg = (
                        f"🔔 **নতুন রিচার্জ রিকোয়েস্ট এসেছে!**\n\n"
                        f"👤 **নাম:** {first_name}\n"
                        f"🆔 **ইউজার আইডি:** `{uid}`\n"
                        f"🔗 **ইউজারনেম:** @{username}\n"
                        f"📊 **আবেদন ফরম্যাট:** `{txt}`\n\n"
                        f"👉 _দয়া করে যাচাই করে রিচার্জ কমপ্লিট করুন।_"
                    )
                    await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=notification_msg, parse_mode="Markdown")
                except Exception as e:
                    print(f"গ্রুপ নোটিফিকেশন এরর: {e}")
            else:
                await update.message.reply_text("❌ পর্যাপ্ত পয়েন্ট নেই অথবা ভুল পরিমাণ নির্দিষ্ট করেছেন!", reply_markup=main_menu())
        except:
            await update.message.reply_text("❌ ভুল ফরম্যাট! দয়া করে কমা (,) দিয়ে সঠিক নিয়মে লিখুন। উদাহরণ: 017XXXXXXXX, GP, 1000", reply_markup=main_menu())
        return

    # কোড ভেরিফাই প্রসেস
    if txt.startswith("WFR") and len(txt) == 8:
        link_num = context.user_data.get('pending_link')
        if not link_num:
            await update.message.reply_text("❌ কোনো অ্যাক্টিভ লিঙ্ক সিলেক্ট করা নেই। দয়া করে মেনু থেকে যান।", reply_markup=main_menu())
            return
            
        clicks = get_link_clicks(uid, link_num)
        if clicks >= 3:
            await update.message.reply_text(f"❌ লিঙ্ক {link_num} এর আজকের কাজের লিমিট শেষ হয়ে গেছে!", reply_markup=main_menu())
            return
            
        increment_link_click(uid, link_num)
        update_balance(uid, 5)
        context.user_data['pending_link'] = None
        
        await update.message.reply_text(f"✅ **অভিনন্দন!** লিঙ্ক {link_num} এর কোড ভেরিফাই হয়েছে। আপনার অ্যাকাউন্টে **৫ পয়েন্ট** যোগ হয়েছে।", reply_markup=main_menu())
    else:
        await update.message.reply_text("❌ ভুল কোড! অনুগ্রহ করে সঠিক কোডটি ইনপুট বক্সে দিন।", reply_markup=main_menu())

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).read_timeout(30).connect_timeout(30).build()
    app.add_handler(CommandHandler("start", start))
