import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta
import aiohttp
from dotenv import load_dotenv

from telegram import Update, ChatPermissions
from telegram.constants import ParseMode, ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
NOVA_API_KEY = os.getenv("NOVA_API_KEY")

# API Configuration
# -----------------
# Select your provider:
# - "NOVA_AI": Paid/Enterprise (https://nova-ai.nabzclan.vip/user/developer)
# - "NABZCLAN_DEV": Free Tier (https://developer.nabzclan.vip/dashboard/tokens)

API_PROVIDER = "NOVA_AI"  #switch to NABZCLAN_DEV for free tier

if API_PROVIDER == "NABZCLAN_DEV":
    NOVA_API_URL = "https://developer.nabzclan.vip/api/v1/moderation"
else:
    # Default to Nova AI
    NOVA_API_URL = "https://novaaiapi.nabzclan.vip/v1/moderation"

# File Configuration
BOT_DIR = Path(__file__).parent
POLICY_FILE = BOT_DIR / "policy.txt"
INSTRUCTIONS_FILE = BOT_DIR / "instructions.txt"
DEBUG_FILE = BOT_DIR / "debug.txt"

USE_POLICY_FILE = True
USE_INSTRUCTIONS_FILE = True
POLICY_MAX_CHARS = 10000
INSTRUCTIONS_MAX_CHARS = 2000

# Auto-Moderation Configuration
AUTO_MODERATE_MESSAGES = True
# Actions: "delete", "warn", "delete_and_warn", "mute", "ban"
# Note: "timeout" is called "mute" or "restrict" in Telegram usually
AUTO_MODERATE_ACTION = "delete_and_warn" 
AUTO_MODERATE_MIN_SEVERITY = "LOW"
AUTO_MODERATE_DEFAULT_TIMEOUT_DAYS = 1
AUTO_MODERATE_MAX_TIMEOUT_DAYS = 28 # Telegram supports up to 366 days, but consistent with Discord
AUTO_MODERATE_BAN_REASON = "Automatic ban: Content policy violation detected by Nova AI"

# Whitelist (Only allow these Chat IDs). Leave empty [] to allow all.
ALLOWED_CHAT_IDS = []

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def load_text_file(path: Path, max_chars: int) -> tuple[str | None, str | None]:
    if not path.exists():
        return None, f"File not found: {path.name}"
    try:
        content = path.read_text(encoding="utf-8").strip()
        lines = []
        for line in content.split("\n"):
            line = line.strip()
            if not line: continue
            if line.lower().startswith("#policy") or not line.startswith("#"):
                lines.append(line)
                
        content = "\n".join(lines)
        if not content:
            return None, None
        if len(content) > max_chars:
            return content[:max_chars], f"Truncated to {max_chars} chars"
        return content, None
    except Exception as e:
        return None, str(e)

async def call_nova_moderation(content: str) -> dict:
    print(f"DEBUG: Entering call_nova_moderation. USE_POLICY_FILE={USE_POLICY_FILE}")
    policy_content = ""
    instructions_content = ""
    
    if USE_POLICY_FILE:
        p, _ = load_text_file(POLICY_FILE, POLICY_MAX_CHARS)
        if p: 
            policy_content = p
            print(f"   📄 Policy loaded: {len(p)} chars")
        else:
            print("   ⚠️ Policy enabled but not loaded")
        
    if USE_INSTRUCTIONS_FILE:
        i, _ = load_text_file(INSTRUCTIONS_FILE, INSTRUCTIONS_MAX_CHARS)
        if i: 
            instructions_content = i
            print(f"   📄 Instructions loaded: {len(i)} chars")
        
    headers = {
        "Authorization": f"Bearer {NOVA_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {"content": content}
    if policy_content: payload["policy"] = policy_content
    if instructions_content: payload["instructions"] = instructions_content
    
    async with aiohttp.ClientSession() as session:
        async with session.post(NOVA_API_URL, headers=headers, json=payload) as response:
            text = await response.text()
            
            try:
                with open(DEBUG_FILE, "a", encoding="utf-8") as f:
                    f.write(f"\n[{datetime.now().isoformat()}] Status: {response.status}\nRequest Content: {content[:100]}...\nResponse: {text}\n")
            except Exception:
                pass
                
            if response.status == 200:
                return json.loads(text)
            else:
                return {"error": True, "message": text}

def format_report(result: dict, content: str) -> str:
    if result.get("error"):
        return f"<b>Error:</b> {result.get('message')}"
        
    status = result.get("status", "UNKNOWN")
    severity = result.get("severity", "UNKNOWN")
    category = result.get("category", "UNKNOWN")
    reason = result.get("reason", "No reason provided")
    confidence = result.get("confidence", 0)
    
    report = f"<b>Content Moderation Result</b>\n\n"
    report += f"<b>Content Analyzed:</b>\n<code>{content[:200]}...</code>\n\n"
    report += f"<b>Status:</b> {status}\n"
    report += f"<b>Category:</b> {category}\n"
    report += f"<b>Severity:</b> {severity}\n"
    report += f"<b>Confidence:</b> {confidence:.0%}\n\n"
    report += f"<b>Reason:</b> {reason}\n"
    
    if result.get("banned_days"):
        report += f"<b>Suggested Ban:</b> {result.get('banned_days')} days\n"
    
    report += f"\n<i>Powered by Nova AI</i>"
    return report

# ═══════════════════════════════════════════════════════════════════════════════
# COMMAND HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "<b>Nova AI - AI Content Moderation Bot</b>\n"
        "I protect this group using advanced AI moderation.\n\n"
        "<b>Commands:</b>\n"
        "/moderate [text] - Analyze text manually\n"
        "/status - Check bot status\n"
        "/policy - View current policy\n"
        "/help - Show this message"
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)

async def moderate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
        
    if not context.args:
        await update.message.reply_text("Usage: /moderate [text content]")
        return
        
    content = " ".join(context.args)
    if len(content) > 50000:
        await update.message.reply_text("Error: Text too long (max 50k chars).")
        return
        
    status_msg = await update.message.reply_text("Analyzing...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    result = await call_nova_moderation(content)
    report = format_report(result, content)
    
    await status_msg.edit_text(report, parse_mode=ParseMode.HTML)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_text = (
        "<b>Auto-Moderation Status</b>\n\n"
        f"<b>Status:</b> {'ENABLED' if AUTO_MODERATE_MESSAGES else 'DISABLED'}\n"
        f"<b>Action:</b> {AUTO_MODERATE_ACTION}\n"
        f"<b>Min Severity:</b> {AUTO_MODERATE_MIN_SEVERITY}\n"
    )
    await update.message.reply_text(status_text, parse_mode=ParseMode.HTML)

async def policy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p, warning = load_text_file(POLICY_FILE, POLICY_MAX_CHARS)
    if not p:
        await update.message.reply_text("No policy file loaded.")
        return
    
    text = f"<b>Policy Configuration</b>\n\n<code>{p[:1000]}</code>"
    if len(p) > 1000:
        text += "\n<i>(truncated)</i>"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# ═══════════════════════════════════════════════════════════════════════════════
# MESSAGE HANDLER
# ═══════════════════════════════════════════════════════════════════════════════

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not AUTO_MODERATE_MESSAGES:
        return
    
    message = update.message
    if not message or not message.text:
        return
        
    print(f"\n🔍 Processing message from {message.from_user.first_name} in {message.chat.title or 'DM'} (ID: {message.chat.id})")

    if ALLOWED_CHAT_IDS and message.chat.id not in ALLOWED_CHAT_IDS:
        print(f"   Skipped: Chat ID {message.chat.id} not in whitelist")
        return

    content = message.text
    
    print("   Calling Nova API...")
    result = await call_nova_moderation(content)
    
    if result.get("error"):
        logger.error(f"API Error: {result}")
        return
        
    status = result.get("status", "ALLOWED")
    severity = result.get("severity", "LOW")
    
    if status not in ["BLOCKED", "DISALLOWED"]:
        print("   Allowed: Status is not BLOCKED/DISALLOWED")
        return

    severity_levels = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
    if severity_levels.get(severity, 0) < severity_levels.get(AUTO_MODERATE_MIN_SEVERITY, 0):
        print(f"   Allowed: Severity {severity} is below threshold")
        return
    print(f"   Taking action: {AUTO_MODERATE_ACTION}")
    
    user_name = message.from_user.mention_html()
    if message.sender_chat:
        user_name = f"<b>{message.sender_chat.title}</b>"

    try:
        if AUTO_MODERATE_ACTION in ["delete", "delete_and_warn", "timeout", "ban"]:
            await message.delete()
            print("   ✅ Message deleted")
            
        if AUTO_MODERATE_ACTION == "warn":
            msg = await message.reply_text(
                f"<b>Content Warning</b>\n{user_name}, your message was flagged for {result.get('reason', 'policy violations')}.",
                parse_mode=ParseMode.HTML
            )
            asyncio.create_task(delete_later(msg, 30))
            print("   ✅ Warning sent")
            
        elif AUTO_MODERATE_ACTION == "delete_and_warn":
            warn_msg = await context.bot.send_message(
                chat_id=message.chat_id,
                text=f"<b>Message Removed</b>\n{user_name}, your message was removed for <b>{result.get('reason')}</b>.",
                parse_mode=ParseMode.HTML
            )
            asyncio.create_task(delete_later(warn_msg, 10))
            
            try:
                await message.from_user.send_message(
                    f"<b>Message Removed</b>\n"
                    f"Your message in <b>{message.chat.title}</b> was removed.\n"
                    f"<b>Reason:</b> {result.get('reason')}\n"
                    f"<b>Category:</b> {result.get('category')}",
                    parse_mode=ParseMode.HTML
                )
                print("   ✅ DM warning sent")
            except Exception:
                pass
                
        elif AUTO_MODERATE_ACTION == "timeout":
            days = result.get("banned_days", AUTO_MODERATE_DEFAULT_TIMEOUT_DAYS)
            days = min(days, AUTO_MODERATE_MAX_TIMEOUT_DAYS)
            until = datetime.now() + timedelta(days=days)
            
            await context.bot.restrict_chat_member(
                chat_id=message.chat_id,
                user_id=message.from_user.id,
                permissions=ChatPermissions.no_permissions(),
                until_date=until
            )
            
            warn_msg = await context.bot.send_message(
                chat_id=message.chat_id,
                text=f"<b>User Muted</b>\n{user_name} has been muted for {days} day(s).",
                parse_mode=ParseMode.HTML
            )
            asyncio.create_task(delete_later(warn_msg, 10))
            print(f"   ✅ User muted for {days} days")
            
        elif AUTO_MODERATE_ACTION == "ban":
            await context.bot.ban_chat_member(
                chat_id=message.chat_id,
                user_id=message.from_user.id
            )
             
            warn_msg = await context.bot.send_message(
                chat_id=message.chat_id,
                text=f"<b>User Banned</b>\n{user_name} has been banned for severe violations.",
                parse_mode=ParseMode.HTML
            )
            asyncio.create_task(delete_later(warn_msg, 10))
            print("   ✅ User banned")
            
    except Exception as e:
        logger.error(f"Failed to execute action: {e}")

async def delete_later(message, delay):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    if not TELEGRAM_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found in environment.")
        return
        
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", start_command))
    app.add_handler(CommandHandler("moderate", moderate_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("policy", policy_command))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🚀 Telegram Bot Started...")
    app.run_polling()

if __name__ == "__main__":
    main()
