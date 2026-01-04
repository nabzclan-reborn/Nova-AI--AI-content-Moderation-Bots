# Nova Content Moderation Discord Bot 🤖

A Discord bot that uses the Nova AI Content Moderation API to analyze text for policy violations, harassment, hate speech, and other harmful content.

![Discord](https://img.shields.io/badge/Discord-Bot-5865F2?style=flat&logo=discord&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat&logo=python&logoColor=white)

## Features ✨

- **Slash Commands** - Modern Discord slash command interface
- **Beautiful Embeds** - Color-coded results with severity indicators
- **Context Menu** - Right-click any message to moderate it
- **Custom Policies** - Define your own moderation rules
- **Confidence Scores** - Visual confidence bars for AI decisions
- **Review Flags** - Automatic flags for uncertain or escalation-required content

## Commands 📋

| Command | Description |
|---------|-------------|
| `/moderate` | Analyze text content for policy violations |
| `/moderate-message` | Moderate a specific message by ID |
| `/moderation-help` | Display help and usage information |
| **Right-click → Moderate This Message** | Context menu to moderate any message |

## Setup 🚀

### 1. Create a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **New Application** and give it a name
3. Go to **Bot** → Click **Add Bot**
4. Copy the **Bot Token** (keep this secret!)
5. Enable these **Privileged Gateway Intents**:
   - Message Content Intent

### 2. Invite the Bot

1. Go to **OAuth2** → **URL Generator**
2. Select scopes: `bot`, `applications.commands`
3. Select permissions: `Send Messages`, `Embed Links`, `Read Message History`
4. Copy the URL and open it to invite the bot to your server

### 3. Configure Environment

```bash
# Clone or download this directory
cd "Content Moderation AI - Bots"

# Create .env file from example
cp .env.example .env

# Edit .env with your tokens
nano .env
```

Add your credentials:
```env
DISCORD_BOT_TOKEN=your_discord_bot_token
NOVA_API_KEY=your_nova_api_key
```

### 4. Install Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 5. Run the Bot

```bash
python3 bot.py
```

You should see:
```
🚀 Starting Nova Content Moderation Bot...
✅ Synced 3 command(s)
🤖 YourBot#1234 is online!
📊 Connected to X server(s)
```

## ⚙️ Configuration

Edit `bot.py` to configure Auto-Moderation:

### Auto-Moderation
Automatically scan all messages in the server.

```python
# Enable/Disable
AUTO_MODERATE_MESSAGES = True

# Action to take
# Options: "delete", "warn", "log", "delete_and_warn", "timeout", "ban"
AUTO_MODERATE_ACTION = "delete_and_warn"

# Minimum severity to trigger action
# Options: "LOW", "MEDIUM", "HIGH", "CRITICAL"
AUTO_MODERATE_MIN_SEVERITY = "LOW"
```

### API Provider (Free Tier) 🆓
Choose between Nova AI (Paid) and Nabzclan Developer (Free).

- **Nova AI**: [Get Key](https://nova-ai.nabzclan.vip/user/developer)
- **Nabzclan Dev**: [Get Key](https://developer.nabzclan.vip/dashboard/tokens)

```python
# Options: "NOVA_AI" or "NABZCLAN_DEV"
API_PROVIDER = "NOVA_AI"
```

### Server Whitelist 🛡️
Restrict the bot to specific servers only.

```python
# List of Allowed Guild IDs (Empty [] = Allow All)
ALLOWED_GUILD_IDS = [1234567890123456789]
```
To find your Guild ID, restart the bot and check the terminal logs.

## Usage Examples 💡

### Basic Moderation
```
/moderate content: This is a test message to analyze
```

### With Custom Policy
```
/moderate content: You're such a noob! policy: #policy 1: block gaming insults
```

### With Instructions
```
/moderate content: Some text instructions: be strict, max ban 7 days
```

### Moderate Existing Message
```
/moderate-message message_id: 123456789012345678
```

Or simply **right-click** any message → **Apps** → **Moderate This Message**

## Response Fields 📊

| Field | Description |
|-------|-------------|
| **Status** | `ALLOWED` or `BLOCKED` |
| **Category** | `SAFE`, `HATE`, `VIOLENCE`, `SEXUAL`, `HARASSMENT`, `SELF_HARM`, `ILLEGAL` |
| **Severity** | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |
| **Confidence** | AI confidence score (0-100%) |
| **Action** | Recommended: `ALLOW`, `WARN`, `BLOCK`, `ESCALATE` |
| **Reason** | Explanation of the decision |
| **Detected Signals** | Specific policy triggers found |
| **Suggested Ban** | Recommended ban duration (if applicable) |

## ❓ Troubleshooting

**Error: `Missing permissions to moderate message`**
Even if the bot is Admin, it **cannot** moderate users with a **Higher Role** than itself.
1. Go to **Server Settings** > **Roles**.
2. Drag the **Bot's Role** to the top of the list.
3. Ensure the bot is above the users you are testing on.

## License 📄

MIT License - Feel free to modify and use in your projects!

---

**Powered by [Nova AI](https://nova-ai.nabzclan.vip/user/developer/docs/content-moderation) • [Full Documentation](https://nova-ai.nabzclan.vip/user/developer/docs/content-moderation)**
