"""
Nova Content Moderation Discord Bot
A Discord bot that uses the Nova AI Content Moderation API to analyze text for policy violations.
"""

import os
import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from dotenv import load_dotenv
from datetime import datetime, timedelta
from pathlib import Path

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
NOVA_API_KEY = os.getenv("NOVA_API_KEY")

# API Configuration
# -----------------
# Select your provider:
# - "NOVA_AI": Paid/Enterprise (https://nova-ai.nabzclan.vip/user/developer)
# - "NABZCLAN_DEV": Free Tier (https://developer.nabzclan.vip/dashboard/tokens)
API_PROVIDER = "NOVA_AI" #switch to NABZCLAN_DEV for free tier

if API_PROVIDER == "NABZCLAN_DEV":
    NOVA_API_URL = "https://developer.nabzclan.vip/api/v1/moderation"
else:
    # Default to Nova AI
    NOVA_API_URL = "https://novaaiapi.nabzclan.vip/v1/moderation"

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION - Policy & Instructions Files
# ═══════════════════════════════════════════════════════════════════════════════

# Toggle whether to use policy.txt and instructions.txt files
USE_POLICY_FILE = True
USE_INSTRUCTIONS_FILE = True

# Character limits
POLICY_MAX_CHARS = 10000
INSTRUCTIONS_MAX_CHARS = 2000

BOT_DIR = Path(__file__).parent
POLICY_FILE = BOT_DIR / "policy.txt"
INSTRUCTIONS_FILE = BOT_DIR / "instructions.txt"

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION - Auto-Moderation (Filter All Messages)
# ═══════════════════════════════════════════════════════════════════════════════

# Toggle automatic message filtering (scans ALL messages in the server)
AUTO_MODERATE_MESSAGES = True  # Set to True to enable

# What to do when content is BLOCKED:
#   "delete"          - Delete the message only
#   "warn"            - Reply with a warning (don't delete)
#   "log"             - Only log to the log channel (silent)
#   "delete_and_warn" - Delete and send DM warning to user
#   "timeout"         - Delete message + timeout user (uses AI's banned_days recommendation)
#   "ban"             - Delete message + ban user permanently (use with caution!)
AUTO_MODERATE_ACTION = "delete_and_warn"

# Default timeout duration in days (used if AI doesn't suggest banned_days)
# Only applies when AUTO_MODERATE_ACTION is "timeout"
AUTO_MODERATE_DEFAULT_TIMEOUT_DAYS = 1

# Maximum timeout duration in days (Discord limit is 28 days)
# The AI might suggest longer bans, but timeout will be capped at this
AUTO_MODERATE_MAX_TIMEOUT_DAYS = 28

# Ban reason template (used when AUTO_MODERATE_ACTION is "ban")
AUTO_MODERATE_BAN_REASON = "Automatic ban: Content policy violation detected by Nova AI"

# Log channel ID for auto-moderation alerts (set to None to disable logging)
# To get a channel ID: Enable Developer Mode in Discord, right-click channel, Copy ID
AUTO_MODERATE_LOG_CHANNEL_ID = None  # Example: 1234567890123456789

# Minimum severity to take action (options: "LOW", "MEDIUM", "HIGH", "CRITICAL")
# Messages with severity BELOW this will be allowed through
AUTO_MODERATE_MIN_SEVERITY = "LOW"

# Ignore bot messages
AUTO_MODERATE_IGNORE_BOTS = True

# Channels to EXCLUDE from auto-moderation (by ID)
# Example: [1234567890123456789, 9876543210987654321]
AUTO_MODERATE_EXCLUDED_CHANNELS = []

# Channels to INCLUDE in auto-moderation (if empty, ALL channels are included except excluded ones)
# Example: [1234567890123456789]
AUTO_MODERATE_INCLUDED_CHANNELS = []

# Roles that bypass auto-moderation (by ID)
# Example: [1234567890123456789]  # Moderator role ID
AUTO_MODERATE_BYPASS_ROLES = []

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION - Server Whitelist
# ═══════════════════════════════════════════════════════════════════════════════

# Only allow the bot to work in these specific servers (Guild IDs)
# Leave EMPTY [] to allow ALL servers.
# Example: [1234567890123456789, 9876543210987654321]
ALLOWED_GUILD_IDS = []


# ═══════════════════════════════════════════════════════════════════════════════
# FILE LOADING FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def load_policy_file() -> tuple[str | None, str | None]:
    if not USE_POLICY_FILE:
        return None, None
    
    if not POLICY_FILE.exists():
        return None, "⚠️ policy.txt not found"
    
    try:
        content = POLICY_FILE.read_text(encoding="utf-8").strip()
        
        lines = content.split("\n")
        policy_lines = []
        for line in lines:
            line = line.strip()
            if line.lower().startswith("#policy") or (line and not line.startswith("#")):
                policy_lines.append(line)
        
        content = "\n".join(policy_lines)
        
        if not content:
            return None, None
        
        if len(content) > POLICY_MAX_CHARS:
            warning = f"⚠️ policy.txt exceeds {POLICY_MAX_CHARS:,} character limit ({len(content):,} chars) - truncated"
            return content[:POLICY_MAX_CHARS], warning
        
        return content, None
    except Exception as e:
        return None, f"⚠️ Error reading policy.txt: {e}"


def load_instructions_file() -> tuple[str | None, str | None]:
    if not USE_INSTRUCTIONS_FILE:
        return None, None
    
    if not INSTRUCTIONS_FILE.exists():
        return None, "⚠️ instructions.txt not found"
    
    try:
        content = INSTRUCTIONS_FILE.read_text(encoding="utf-8").strip()
        
        lines = content.split("\n")
        instruction_lines = [line for line in lines if line.strip() and not line.strip().startswith("#")]
        content = "\n".join(instruction_lines)
        
        if not content:
            return None, None
        
        if len(content) > INSTRUCTIONS_MAX_CHARS:
            warning = f"⚠️ instructions.txt exceeds {INSTRUCTIONS_MAX_CHARS:,} character limit ({len(content):,} chars) - truncated"
            return content[:INSTRUCTIONS_MAX_CHARS], warning
        
        return content, None
    except Exception as e:
        return None, f"⚠️ Error reading instructions.txt: {e}"


def get_file_status() -> dict:
    policy_content, policy_warning = load_policy_file()
    instructions_content, instructions_warning = load_instructions_file()
    
    return {
        "policy": {
            "enabled": USE_POLICY_FILE,
            "exists": POLICY_FILE.exists(),
            "content": policy_content,
            "length": len(policy_content) if policy_content else 0,
            "max_length": POLICY_MAX_CHARS,
            "warning": policy_warning
        },
        "instructions": {
            "enabled": USE_INSTRUCTIONS_FILE,
            "exists": INSTRUCTIONS_FILE.exists(),
            "content": instructions_content,
            "length": len(instructions_content) if instructions_content else 0,
            "max_length": INSTRUCTIONS_MAX_CHARS,
            "warning": instructions_warning
        }
    }


SEVERITY_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def severity_meets_threshold(severity: str, min_severity: str) -> bool:
    return SEVERITY_ORDER.get(severity, 0) >= SEVERITY_ORDER.get(min_severity, 0)


class ModerationBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
    
    async def setup_hook(self):
        await self.tree.sync()
        print(f"✅ Synced {len(self.tree.get_commands())} command(s)")
    
    async def on_ready(self):
        print(f"🤖 {self.user} is online!")
        print(f"📊 Connected to {len(self.guilds)} server(s):")
        for guild in self.guilds:
            print(f"   - {guild.name} (ID: {guild.id})")
        
        status = get_file_status()
        print("\n📁 File Configuration:")
        print(f"   Policy:       {'✅ Enabled' if status['policy']['enabled'] else '❌ Disabled'} | "
              f"{'Found' if status['policy']['exists'] else 'Not Found'} | "
              f"{status['policy']['length']:,}/{status['policy']['max_length']:,} chars")
        print(f"   Instructions: {'✅ Enabled' if status['instructions']['enabled'] else '❌ Disabled'} | "
              f"{'Found' if status['instructions']['exists'] else 'Not Found'} | "
              f"{status['instructions']['length']:,}/{status['instructions']['max_length']:,} chars")
        
        if status['policy']['warning']:
            print(f"   {status['policy']['warning']}")
        if status['instructions']['warning']:
            print(f"   {status['instructions']['warning']}")
        
        print("\n🔍 Auto-Moderation:")
        print(f"   Status:       {'✅ ENABLED' if AUTO_MODERATE_MESSAGES else '❌ Disabled'}")
        if AUTO_MODERATE_MESSAGES:
            print(f"   Action:       {AUTO_MODERATE_ACTION}")
            print(f"   Min Severity: {AUTO_MODERATE_MIN_SEVERITY}")
            print(f"   Log Channel:  {AUTO_MODERATE_LOG_CHANNEL_ID or 'Not Set'}")
            if AUTO_MODERATE_EXCLUDED_CHANNELS:
                print(f"   Excluded:     {len(AUTO_MODERATE_EXCLUDED_CHANNELS)} channel(s)")
            if AUTO_MODERATE_BYPASS_ROLES:
                print(f"   Bypass Roles: {len(AUTO_MODERATE_BYPASS_ROLES)} role(s)")
        
        print()
        
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="for content violations"
            )
        )


bot = ModerationBot()


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

async def call_nova_moderation(
    content: str, 
    policy: str = None, 
    instructions: str = None,
    use_policy_file: bool = True,
    use_instructions_file: bool = True
) -> tuple[dict, list[str]]:
    sources = []
    final_policy = ""
    final_instructions = ""
    
    if use_policy_file and USE_POLICY_FILE:
        file_policy, _ = load_policy_file()
        if file_policy:
            final_policy = file_policy
            sources.append("📄 policy.txt")
    
    if use_instructions_file and USE_INSTRUCTIONS_FILE:
        file_instructions, _ = load_instructions_file()
        if file_instructions:
            final_instructions = file_instructions
            sources.append("📄 instructions.txt")
    
    if policy:
        if final_policy:
            final_policy += "\n" + policy
        else:
            final_policy = policy
        sources.append("💬 inline policy")
    
    if instructions:
        if final_instructions:
            final_instructions += "\n" + instructions
        else:
            final_instructions = instructions
        sources.append("💬 inline instructions")
    
    if final_policy and len(final_policy) > POLICY_MAX_CHARS:
        final_policy = final_policy[:POLICY_MAX_CHARS]
    if final_instructions and len(final_instructions) > INSTRUCTIONS_MAX_CHARS:
        final_instructions = final_instructions[:INSTRUCTIONS_MAX_CHARS]
    
    headers = {
        "Authorization": f"Bearer {NOVA_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {"content": content}
    if final_policy:
        payload["policy"] = final_policy
    if final_instructions:
        payload["instructions"] = final_instructions
    
    async with aiohttp.ClientSession() as session:
        async with session.post(NOVA_API_URL, headers=headers, json=payload) as response:
            response_text = await response.text()
            
            debug_file = BOT_DIR / "debug.txt"
            try:
                import json
                with open(debug_file, "a", encoding="utf-8") as f:
                    f.write(f"\n{'='*60}\n")
                    f.write(f"[{datetime.now().isoformat()}]\n")
                    f.write(f"REQUEST:\n")
                    f.write(f"  Content: {content[:200]}{'...' if len(content) > 200 else ''}\n")
                    f.write(f"  Policy: {'Yes' if final_policy else 'No'}\n")
                    f.write(f"  Instructions: {'Yes' if final_instructions else 'No'}\n")
                    f.write(f"\nRESPONSE (Status {response.status}):\n")
                    try:
                        formatted = json.dumps(json.loads(response_text), indent=2)
                        f.write(f"{formatted}\n")
                    except:
                        f.write(f"{response_text}\n")
                    f.write(f"{'='*60}\n")
            except Exception as e:
                print(f"⚠️ Failed to write debug.txt: {e}")
            
            if response.status == 200:
                import json
                return json.loads(response_text), sources
            else:
                return {"error": True, "status_code": response.status, "message": response_text}, sources


def get_status_color(status: str, severity: str) -> discord.Color:
    if status == "ALLOWED":
        return discord.Color.green()
    
    severity_colors = {
        "LOW": discord.Color.yellow(),
        "MEDIUM": discord.Color.orange(),
        "HIGH": discord.Color.red(),
        "CRITICAL": discord.Color.dark_red()
    }
    return severity_colors.get(severity, discord.Color.red())


def get_status_emoji(status: str) -> str:
    return "✅" if status == "ALLOWED" else "🚫"


def get_severity_emoji(severity: str) -> str:
    emojis = {
        "LOW": "🟡",
        "MEDIUM": "🟠",
        "HIGH": "🔴",
        "CRITICAL": "⛔"
    }
    return emojis.get(severity, "⚪")


def get_category_emoji(category: str) -> str:
    emojis = {
        "SAFE": "🛡️",
        "HATE": "💢",
        "VIOLENCE": "⚔️",
        "SEXUAL": "🔞",
        "HARASSMENT": "😠",
        "SELF_HARM": "💔",
        "ILLEGAL": "🚨"
    }
    return emojis.get(category, "❓")


def get_action_emoji(action: str) -> str:
    emojis = {
        "ALLOW": "✅",
        "WARN": "⚠️",
        "BLOCK": "🚫",
        "ESCALATE": "🚨"
    }
    return emojis.get(action, "❓")


def create_moderation_embed(result: dict, content_preview: str, sources: list[str] = None) -> discord.Embed:
    if result.get("error"):
        embed = discord.Embed(
            title="❌ Moderation Error",
            description=f"Failed to analyze content.\n\n**Status Code:** {result.get('status_code')}\n**Message:** {result.get('message', 'Unknown error')}",
            color=discord.Color.dark_gray(),
            timestamp=datetime.now()
        )
        return embed
    
    status = result.get("status", "UNKNOWN")
    severity = result.get("severity", "UNKNOWN")
    category = result.get("category", "UNKNOWN")
    action = result.get("action", "UNKNOWN")
    confidence = result.get("confidence", 0)
    reason = result.get("reason", "No reason provided")
    detected_signals = result.get("detected_signals", [])
    banned_days = result.get("banned_days")
    uncertainty_flag = result.get("uncertainty_flag", False)
    escalation_required = result.get("escalation_required", False)
    
    status_emoji = get_status_emoji(status)
    embed = discord.Embed(
        title=f"{status_emoji} Content Moderation Result",
        color=get_status_color(status, severity),
        timestamp=datetime.now()
    )
    
    if len(content_preview) > 200:
        content_preview = content_preview[:200] + "..."
    embed.add_field(
        name="Content Analyzed",
        value=f"```{content_preview}```",
        inline=False
    )
    
    embed.add_field(
        name="Status",
        value=f"**{status}**",
        inline=True
    )
    embed.add_field(
        name="Category",
        value=f"**{category}**",
        inline=True
    )
    embed.add_field(
        name="Severity",
        value=f"**{severity}**",
        inline=True
    )
    
    confidence_bar = create_confidence_bar(confidence)
    embed.add_field(
        name="🎯 Confidence",
        value=f"{confidence_bar} **{confidence:.0%}**",
        inline=True
    )
    embed.add_field(
        name=f"{get_action_emoji(action)} Recommended Action",
        value=f"**{action}**",
        inline=True
    )
    
    if banned_days:
        embed.add_field(
            name="⏰ Suggested Ban",
            value=f"**{banned_days} day(s)**",
            inline=True
        )
    
    embed.add_field(
        name="📋 Reason",
        value=reason,
        inline=False
    )
    
    if detected_signals:
        signals_text = "\n".join([f"• {signal}" for signal in detected_signals[:5]])
        if len(detected_signals) > 5:
            signals_text += f"\n*...and {len(detected_signals) - 5} more*"
        embed.add_field(
            name="🔍 Detected Signals",
            value=signals_text,
            inline=False
        )
    
    flags = []
    if uncertainty_flag:
        flags.append("⚠️ **Uncertainty Flag** - Human review recommended")
    if escalation_required:
        flags.append("🚨 **Escalation Required** - Human review strictly recommended")
    
    if flags:
        embed.add_field(
            name="🚩 Review Flags",
            value="\n".join(flags),
            inline=False
        )
    
    if sources:
        embed.add_field(
            name="📁 Sources Used",
            value=" • ".join(sources),
            inline=False
        )
    
    embed.set_footer(text="Powered by Nova AI - AI Content Moderation")
    
    return embed


def create_auto_mod_log_embed(message: discord.Message, result: dict, action_taken: str) -> discord.Embed:
    severity = result.get("severity", "UNKNOWN")
    category = result.get("category", "UNKNOWN")
    confidence = result.get("confidence", 0)
    reason = result.get("reason", "No reason provided")
    detected_signals = result.get("detected_signals", [])
    
    embed = discord.Embed(
        title="🔍 Auto-Moderation Alert",
        color=get_status_color("BLOCKED", severity),
        timestamp=datetime.now()
    )
    
    embed.set_author(
        name=f"{message.author.display_name} ({message.author.id})",
        icon_url=message.author.display_avatar.url
    )
    
    content_preview = message.content
    if len(content_preview) > 500:
        content_preview = content_preview[:500] + "..."
    embed.add_field(
        name="📝 Message Content",
        value=f"```{content_preview}```",
        inline=False
    )
    
    embed.add_field(
        name="📍 Location",
        value=f"**Channel:** {message.channel.mention}\n**Message ID:** `{message.id}`",
        inline=True
    )
    
    
    action_labels = {
        "delete": "Deleted",
        "warn": "Warned",
        "log": "Logged Only",
        "delete_and_warn": "Deleted + DM Warning",
        "timeout": "Deleted + Timeout",
        "ban": "Deleted + Banned"
    }
    embed.add_field(
        name="Action Taken",
        value=action_labels.get(action_taken, action_taken),
        inline=True
    )
    
    embed.add_field(
        name="Analysis",
        value=f"**Category:** {category}\n"
              f"**Severity:** {severity}\n"
              f"**Confidence:** {confidence:.0%}",
        inline=False
    )
    
    embed.add_field(
        name="📋 Reason",
        value=reason,
        inline=False
    )
    
    if detected_signals:
        signals_text = ", ".join(detected_signals[:5])
        if len(detected_signals) > 5:
            signals_text += f", +{len(detected_signals) - 5} more"
        embed.add_field(
            name="Detected Signals",
            value=signals_text,
            inline=False
        )
    
    if action_taken not in ["delete", "delete_and_warn", "timeout", "ban"]:
        embed.add_field(
            name="Jump to Message",
            value=f"[Click here]({message.jump_url})",
            inline=False
        )
    
    embed.set_footer(text="Nova AI - AI Content Moderation model")
    
    return embed


def create_confidence_bar(confidence: float) -> str:
    filled = int(confidence * 10)
    empty = 10 - filled
    return "█" * filled + "░" * empty


# ═══════════════════════════════════════════════════════════════════════════════
# AUTO-MODERATION EVENT
# ═══════════════════════════════════════════════════════════════════════════════

@bot.event
async def on_message(message: discord.Message):
    await bot.process_commands(message)
    
    if not AUTO_MODERATE_MESSAGES:
        return
    
    print(f"\n🔍 Processing message from {message.author} in #{message.channel}")

    if AUTO_MODERATE_IGNORE_BOTS and message.author.bot:
        print("   Skipped: Bot message")
        return
    
    if not message.guild:
        print("   Skipped: DM")
        return
    
    if not message.content:
        print("   ⚠️ Skipped: Empty content (Check 'Message Content Intent' in Dev Portal!)")
        return
    
    if ALLOWED_GUILD_IDS and message.guild.id not in ALLOWED_GUILD_IDS:
        print(f"   Skipped: Guild {message.guild.name} ({message.guild.id}) not in whitelist")
        return

    if AUTO_MODERATE_INCLUDED_CHANNELS:
        if message.channel.id not in AUTO_MODERATE_INCLUDED_CHANNELS:
            print("   Skipped: Channel not in included list")
            return
    elif message.channel.id in AUTO_MODERATE_EXCLUDED_CHANNELS:
        print("   Skipped: Channel excluded")
        return
    
    if AUTO_MODERATE_BYPASS_ROLES and hasattr(message.author, 'roles'):
        author_role_ids = [role.id for role in message.author.roles]
        if any(role_id in author_role_ids for role_id in AUTO_MODERATE_BYPASS_ROLES):
            print("   Skipped: User has bypass role")
            return
    
    print("   Calling Nova API...")
    try:
        result, _ = await call_nova_moderation(message.content)
    except Exception as e:
        print(f"❌ Auto-moderation API error: {e}")
        return
    
    if result.get("error"):
        print(f"❌ Auto-moderation API returned error: {result.get('message')}")
        return
    
    status = result.get("status", "ALLOWED")
    severity = result.get("severity", "LOW")
    print(f"   API Result: Status={status}, Severity={severity}")
    
    if status not in ["BLOCKED", "DISALLOWED"]:
        print("   Allowed: Status is not BLOCKED/DISALLOWED")
        return
    
    if not severity_meets_threshold(severity, AUTO_MODERATE_MIN_SEVERITY):
        print(f"   Allowed: Severity {severity} is below threshold {AUTO_MODERATE_MIN_SEVERITY}")
        return
    
    action_taken = AUTO_MODERATE_ACTION
    print(f"   Taking action: {action_taken}")
    
    try:
        if AUTO_MODERATE_ACTION == "delete":
            await message.delete()
            print("   ✅ Message deleted")
            
        elif AUTO_MODERATE_ACTION == "warn":
            warning_embed = discord.Embed(
                title="Content Warning",
                description=f"{message.author.mention}, your message was flagged for policy violations.",
                color=discord.Color.orange()
            )
            warning_embed.add_field(
                name="Reason",
                value=result.get("reason", "Policy violation detected"),
                inline=False
            )
            await message.reply(embed=warning_embed, delete_after=30)
            print("   ✅ Warning sent")
            
        elif AUTO_MODERATE_ACTION == "log":
            pass
            print("   ✅ Log action (no deletion)")
            
        elif AUTO_MODERATE_ACTION == "delete_and_warn":
            try:
                dm_embed = discord.Embed(
                    title="Message Removed",
                    description=f"Your message in **{message.guild.name}** was removed for violating content policies.",
                    color=discord.Color.red()
                )
                dm_embed.add_field(
                    name="Channel",
                    value=f"#{message.channel.name}",
                    inline=True
                )
                dm_embed.add_field(
                    name="Category",
                    value=result.get('category', 'Unknown'),
                    inline=True
                )
                dm_embed.add_field(
                    name="Reason",
                    value=result.get("reason", "Policy violation detected"),
                    inline=False
                )
                dm_embed.add_field(
                    name="Your Message",
                    value=f"```{message.content[:500]}{'...' if len(message.content) > 500 else ''}```",
                    inline=False
                )
                dm_embed.set_footer(text="Please review server rules to avoid future violations.")
                await message.author.send(embed=dm_embed)
                print("   ✅ DM warning sent")
            except discord.Forbidden:
                print("   ⚠️ Failed to send DM (Forbidden)")
            
            try:
                channel_embed = discord.Embed(
                    title="Message Removed",
                    description=f"{message.author.mention}, your message was removed for **{result.get('reason', 'policy violations')}**.",
                   color=discord.Color.orange()
                )
                await message.channel.send(embed=channel_embed, delete_after=10)
                print("   ✅ Channel warning sent")
            except Exception as e:
                print(f"   ⚠️ Failed to send channel warning: {e}")
            
            await message.delete()
            print("   ✅ Message deleted")
        
        elif AUTO_MODERATE_ACTION == "timeout":
            banned_days = result.get("banned_days")
            if banned_days:
                timeout_days = min(banned_days, AUTO_MODERATE_MAX_TIMEOUT_DAYS)
            else:
                timeout_days = AUTO_MODERATE_DEFAULT_TIMEOUT_DAYS
            
            timeout_duration = timedelta(days=timeout_days)
            
            try:
                await message.author.timeout(timeout_duration, reason=f"Auto-moderation: {result.get('reason', 'Policy violation')}")
                action_taken = f"timeout ({timeout_days}d)"
                print(f"   ✅ User timed out for {timeout_days} days")
            except discord.Forbidden:
                print(f"❌ Missing permissions to timeout {message.author}")
            
            try:
                dm_embed = discord.Embed(
                    title="You Have Been Timed Out",
                    description=f"You have been timed out in **{message.guild.name}** for **{timeout_days} day(s)**.",
                    color=discord.Color.red()
                )
                dm_embed.add_field(
                    name="Reason",
                    value=result.get("reason", "Policy violation detected"),
                    inline=False
                )
                dm_embed.add_field(
                    name="Category",
                    value=result.get('category', 'Unknown'),
                    inline=True
                )
                dm_embed.add_field(
                    name="Severity",
                    value=result.get('severity', 'Unknown'),
                    inline=True
                )
                dm_embed.add_field(
                    name="Your Message",
                    value=f"```{message.content[:300]}{'...' if len(message.content) > 300 else ''}```",
                    inline=False
                )
                dm_embed.set_footer(text="Please review server rules before your timeout ends.")
                await message.author.send(embed=dm_embed)
                print("   ✅ DM warning sent")
            except discord.Forbidden:
                print("   ⚠️ Failed to send DM (Forbidden)")
            
            try:
                channel_embed = discord.Embed(
                    title="User Timed Out",
                    description=f"{message.author.mention} has been timed out for **{timeout_days} day(s)** for violating server policies.",
                    color=discord.Color.red()
                )
                await message.channel.send(embed=channel_embed, delete_after=10)
                print("   ✅ Channel warning sent")
            except Exception as e:
                print(f"   ⚠️ Failed to send channel warning: {e}")
            
            await message.delete()
            print("   ✅ Message deleted")
        
        elif AUTO_MODERATE_ACTION == "ban":
            try:
                await message.author.ban(
                    reason=f"{AUTO_MODERATE_BAN_REASON} | Category: {result.get('category')} | Severity: {result.get('severity')}",
                    delete_message_seconds=0
                )
                print("   ✅ User banned")
            except discord.Forbidden:
                print(f"❌ Missing permissions to ban {message.author}")
            
            try:
                dm_embed = discord.Embed(
                    title="You Have Been Banned",
                    description=f"You have been banned from **{message.guild.name}** for severe content policy violations.",
                    color=discord.Color.dark_red()
                )
                dm_embed.add_field(
                    name="Reason",
                    value=result.get("reason", "Policy violation detected"),
                    inline=False
                )
                dm_embed.add_field(
                    name="Category",
                    value=result.get('category', 'Unknown'),
                    inline=True
                )
                dm_embed.add_field(
                    name="Severity",
                    value=result.get('severity', 'Unknown'),
                    inline=True
                )
                dm_embed.set_footer(text="If you believe this was a mistake, contact server staff.")
                await message.author.send(embed=dm_embed)
                print("   ✅ DM warning sent")
            except discord.Forbidden:
                print("   ⚠️ Failed to send DM (Forbidden)")
            
            try:
                channel_embed = discord.Embed(
                    title="User Banned",
                    description=f"{message.author.mention} has been banned for severe policy violations.",
                    color=discord.Color.dark_red()
                )
                await message.channel.send(embed=channel_embed, delete_after=10)
                print("   ✅ Channel warning sent")
            except Exception as e:
                print(f"   ⚠️ Failed to send channel warning: {e}")
            
            try:
                await message.delete()
                print("   ✅ Message deleted")
            except discord.NotFound:
                print("   ⚠️ Message already gone")
    
    except discord.Forbidden:
        print(f"❌ Missing permissions to moderate message in #{message.channel}")
        return
    except discord.NotFound:
        print("   ⚠️ Message not found (already deleted?)")
    
    if AUTO_MODERATE_LOG_CHANNEL_ID:
        try:
            log_channel = bot.get_channel(AUTO_MODERATE_LOG_CHANNEL_ID)
            if log_channel:
                log_embed = create_auto_mod_log_embed(message, result, action_taken)
                await log_channel.send(embed=log_embed)
        except Exception as e:
            print(f"❌ Failed to send to log channel: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# SLASH COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════

@bot.tree.command(name="moderate", description="Analyze text content for policy violations using Nova AI")
@app_commands.describe(
    content="The text content to analyze for moderation (max 50,000 chars)"
)
async def moderate(
    interaction: discord.Interaction,
    content: str
):    
    await interaction.response.defer(ephemeral=True)
    
    if len(content) > 50000:
        embed = discord.Embed(
            title="❌ Error",
            description="Content exceeds maximum length of 50,000 characters.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    result, sources = await call_nova_moderation(
        content, 
        policy=None, 
        instructions=None,
        use_policy_file=True,
        use_instructions_file=True
    )
    
    embed = create_moderation_embed(result, content, sources)
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="moderate-message", description="Moderate a specific message by its ID")
@app_commands.describe(
    message_id="The ID of the message to moderate",
    policy="Optional additional policy",
    instructions="Optional additional instructions",
    use_policy_file="Use policies from policy.txt (default: True)",
    use_instructions_file="Use instructions from instructions.txt (default: True)"
)
async def moderate_message(
    interaction: discord.Interaction,
    message_id: str,
    policy: str = None,
    instructions: str = None,
    use_policy_file: bool = True,
    use_instructions_file: bool = True
):    
    await interaction.response.defer(ephemeral=True)
    
    try:
        msg_id = int(message_id)
        message = await interaction.channel.fetch_message(msg_id)
    except (ValueError, discord.NotFound):
        embed = discord.Embed(
            title="❌ Error",
            description="Message not found. Make sure you're using a valid message ID from this channel.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    except discord.Forbidden:
        embed = discord.Embed(
            title="❌ Error",
            description="I don't have permission to read that message.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    if not message.content:
        embed = discord.Embed(
            title="❌ Error",
            description="That message has no text content to moderate.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    result, sources = await call_nova_moderation(
        message.content, 
        policy, 
        instructions,
        use_policy_file,
        use_instructions_file
    )
    
    embed = create_moderation_embed(result, message.content, sources)
    embed.set_author(
        name=f"Message by {message.author.display_name}",
        icon_url=message.author.display_avatar.url
    )
    
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="show-policy", description="Display the current policy.txt contents")
async def show_policy(interaction: discord.Interaction):
    status = get_file_status()
    policy_info = status["policy"]
    
    embed = discord.Embed(
        title="Policy Configuration",
        color=discord.Color.blurple(),
        timestamp=datetime.now()
    )
    
    status_text = "Enabled" if policy_info["enabled"] else "Disabled"
    file_status = "Found" if policy_info["exists"] else "Not Found"
    embed.add_field(
        name="Status",
        value=f"**File Loading:** {status_text}\n**File Status:** {file_status}",
        inline=False
    )
    
    char_count = policy_info["length"]
    max_chars = policy_info["max_length"]
    percentage = (char_count / max_chars * 100) if max_chars > 0 else 0
    
    embed.add_field(
        name="Character Usage",
        value=f"**{char_count:,}** / {max_chars:,} characters ({percentage:.1f}%)",
        inline=False
    )
    
    if policy_info["warning"]:
        embed.add_field(
            name="Warning",
            value=policy_info["warning"],
            inline=False
        )
    
    if policy_info["content"]:
        content_preview = policy_info["content"]
        if len(content_preview) > 1000:
            content_preview = content_preview[:1000] + "\n\n*... truncated for display ...*"
        embed.add_field(
            name="Content",
            value=f"```\n{content_preview}\n```",
            inline=False
        )
    else:
        embed.add_field(
            name="Content",
            value="*No policy content loaded*",
            inline=False
        )
    
    embed.set_footer(text=f"File: {POLICY_FILE.name}")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="show-instructions", description="Display the current instructions.txt contents")
async def show_instructions(interaction: discord.Interaction):
    status = get_file_status()
    instructions_info = status["instructions"]
    
    embed = discord.Embed(
        title="Instructions Configuration",
        color=discord.Color.blurple(),
        timestamp=datetime.now()
    )
    
    status_text = "Enabled" if instructions_info["enabled"] else "Disabled"
    file_status = "Found" if instructions_info["exists"] else "Not Found"
    embed.add_field(
        name="Status",
        value=f"**File Loading:** {status_text}\n**File Status:** {file_status}",
        inline=False
    )
    
    char_count = instructions_info["length"]
    max_chars = instructions_info["max_length"]
    percentage = (char_count / max_chars * 100) if max_chars > 0 else 0
    
    embed.add_field(
        name="Character Usage",
        value=f"**{char_count:,}** / {max_chars:,} characters ({percentage:.1f}%)",
        inline=False
    )
    
    if instructions_info["warning"]:
        embed.add_field(
            name="Warning",
            value=instructions_info["warning"],
            inline=False
        )
    
    if instructions_info["content"]:
        content_preview = instructions_info["content"]
        if len(content_preview) > 1000:
            content_preview = content_preview[:1000] + "\n\n*... truncated for display ...*"
        embed.add_field(
            name="Content",
            value=f"```\n{content_preview}\n```",
            inline=False
        )
    else:
        embed.add_field(
            name="Content",
            value="*No instructions content loaded*",
            inline=False
        )
    
    embed.set_footer(text=f"File: {INSTRUCTIONS_FILE.name}")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="automod-status", description="Show auto-moderation configuration status")
async def automod_status(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Auto-Moderation Status",
        color=discord.Color.green() if AUTO_MODERATE_MESSAGES else discord.Color.red(),
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="Status",
        value=f"**{'ENABLED' if AUTO_MODERATE_MESSAGES else 'DISABLED'}**",
        inline=False
    )
    
    if AUTO_MODERATE_MESSAGES:
        action_labels = {
            "delete": "Delete message",
            "warn": "Reply with warning",
            "log": "Log only (silent)",
            "delete_and_warn": "Delete + DM warning",
            "timeout": "Delete + Timeout",
            "ban": "Delete + Banned"
        }
        embed.add_field(
            name="Action",
            value=action_labels.get(AUTO_MODERATE_ACTION, AUTO_MODERATE_ACTION),
            inline=True
        )
        
        embed.add_field(
            name="Min Severity",
            value=f"{AUTO_MODERATE_MIN_SEVERITY}+",
            inline=True
        )
        
        if AUTO_MODERATE_LOG_CHANNEL_ID:
            log_channel = interaction.guild.get_channel(AUTO_MODERATE_LOG_CHANNEL_ID)
            log_text = log_channel.mention if log_channel else f"ID: {AUTO_MODERATE_LOG_CHANNEL_ID}"
        else:
            log_text = "Not configured"
        embed.add_field(
            name="Log Channel",
            value=log_text,
            inline=True
        )
        
        filters = []
        if AUTO_MODERATE_IGNORE_BOTS:
            filters.append("Ignoring bots")
        if AUTO_MODERATE_EXCLUDED_CHANNELS:
            filters.append(f"{len(AUTO_MODERATE_EXCLUDED_CHANNELS)} excluded channel(s)")
        if AUTO_MODERATE_INCLUDED_CHANNELS:
            filters.append(f"{len(AUTO_MODERATE_INCLUDED_CHANNELS)} included channel(s) only")
        if AUTO_MODERATE_BYPASS_ROLES:
            filters.append(f"{len(AUTO_MODERATE_BYPASS_ROLES)} bypass role(s)")
        
        if filters:
            embed.add_field(
                name="Filters",
                value="\n".join(filters),
                inline=False
            )
    else:
        embed.add_field(
            name="How to Enable",
            value="Set `AUTO_MODERATE_MESSAGES = True` in `bot.py` and restart the bot.",
            inline=False
        )
    
    embed.set_footer(text="Configure in bot.py")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="moderation-help", description="Get help on using the content moderation bot")
async def moderation_help(interaction: discord.Interaction):
    status = get_file_status()
    
    embed = discord.Embed(
        title="Nova AI - Content Moderation AI - BOT",
        description="Analyze text for policy violations, harassment, hate speech, and other harmful content using nabzclan in-house AI models.",
        color=discord.Color.blurple()
    )
    
    embed.add_field(
        name="📋 Commands",
        value="""
**`/moderate`** - Analyze text content
• `content` - The text to analyze (required)
• `policy` - Additional policies to apply
• `instructions` - Additional instructions
• `use_policy_file` - Load policy.txt (default: True)
• `use_instructions_file` - Load instructions.txt (default: True)
• `ephemeral` - Hide response from others

**`/moderate-message`** - Analyze an existing message
• `message_id` - The message ID to analyze

**`/show-policy`** - View current policy.txt
**`/show-instructions`** - View current instructions.txt
**`/automod-status`** - View auto-moderation settings
**`/moderation-help`** - Show this help message
        """,
        inline=False
    )
    
    policy_status = "✅" if status["policy"]["enabled"] and status["policy"]["exists"] else "❌"
    instructions_status = "✅" if status["instructions"]["enabled"] and status["instructions"]["exists"] else "❌"
    automod_status = "✅" if AUTO_MODERATE_MESSAGES else "❌"
    
    embed.add_field(
        name="📁 Configuration Status",
        value=f"""
{policy_status} **policy.txt** - {status["policy"]["length"]:,}/{status["policy"]["max_length"]:,} chars
{instructions_status} **instructions.txt** - {status["instructions"]["length"]:,}/{status["instructions"]["max_length"]:,} chars
{automod_status} **Auto-Moderation** - {'Enabled' if AUTO_MODERATE_MESSAGES else 'Disabled'}
        """,
        inline=False
    )
    
    embed.add_field(
        name="⚠️ Character Limits",
        value="""
• **Content:** 50,000 characters max
• **Policy:** 10,000 characters max
• **Instructions:** 2,000 characters max
        """,
        inline=True
    )
    
    embed.add_field(
        name="🏷️ Categories",
        value="""
🛡️ SAFE • 💢 HATE • ⚔️ VIOLENCE
🔞 SEXUAL • 😠 HARASSMENT
💔 SELF_HARM • 🚨 ILLEGAL
        """,
        inline=True
    )
    
    embed.add_field(
        name="📝 Policy Format",
        value="""
```
#policy 1: block all spam
#policy 2: warn on profanity
#policy 3: ban 7 days for slurs
```
        """,
        inline=False
    )
    
    embed.set_footer(text="Powered by Nova AI by nabzclan • AI Content Moderation - API")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.context_menu(name="Moderate This Message")
async def moderate_context(interaction: discord.Interaction, message: discord.Message):    
    await interaction.response.defer(ephemeral=True)
    
    if not message.content:
        embed = discord.Embed(
            title="❌ Error",
            description="This message has no text content to moderate.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    result, sources = await call_nova_moderation(message.content)
    
    embed = create_moderation_embed(result, message.content, sources)
    embed.set_author(
        name=f"Message by {message.author.display_name}",
        icon_url=message.author.display_avatar.url
    )
    
    await interaction.followup.send(embed=embed)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    if not DISCORD_TOKEN:
        print("❌ Error: DISCORD_BOT_TOKEN not found in environment variables!")
        print("   Create a .env file with your Discord bot token:")
        print("   DISCORD_BOT_TOKEN=your_token_here")
        return
    
    if not NOVA_API_KEY:
        print("❌ Error: NOVA_API_KEY not found in environment variables!")
        print("   Add your Nova AI API key to the .env file:")
        print("   NOVA_API_KEY=your_key_here")
        return
    
    print("🚀 Starting Nova AI - AI Content Moderation Bot...")
    print("give us a star on github - https://github.com/nabzclan-reborn/Nova-AI--AI-content-Moderation-Bots")
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
