# Nova Content Moderation Telegram Bot

A Telegram bot that uses the Nova AI Content Moderation API to automatically filter messages and enforce server policies.

## 🚀 Setup

1. **Install Python 3.10+**
2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure Environment:**
   Create a `.env` file in this directory with:
   ```env
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   NOVA_API_KEY=your_nova_api_key
   ```
4. **Run the Bot:**
   ```bash
   python3 bot.py
   ```

5. **CRITICAL STEP:**
   By default, bots can't see all messages in groups.
   - Go to **@BotFather**
   - Select your bot
   - Go to **Bot Settings** > **Group Privacy**
   - Set to **Turn off** (Disabled)
   - *Re-add the bot to your group if it was already there.*

## 🛠Configuration

Edit `bot.py` to change settings:

- `AUTO_MODERATE_MESSAGES`: Enable/Disable auto-mod.
- `AUTO_MODERATE_ACTION`: `delete`, `warn`, `delete_and_warn`, `timeout` (mute), `ban`.
- `AUTO_MODERATE_MIN_SEVERITY`: Minimum severity (`LOW`, `MEDIUM`, `HIGH`) to trigger action.

### API Provider (Free Tier) 🆓
Choose between Nova AI (Paid) and Nabzclan Developer (Free).

- **Nova AI**: [Get Key](https://nova-ai.nabzclan.vip/user/developer)
- **Nabzclan Dev**: [Get Key](https://developer.nabzclan.vip/dashboard/tokens)

- `API_PROVIDER`: Set to `"NABZCLAN_DEV"` for free tier (default is `"NOVA_AI"`).

### Chat Whitelist 🛡️
Restrict the bot to specific groups only.

- `ALLOWED_CHAT_IDS`: List of Chat IDs (e.g. `[-10012345678]`).
  - Leave empty `[]` to allow all groups.
  - Restart the bot and check logs to check your Group ID.

## 📝 Files

- `policy.txt`: Your community guidelines.
- `instructions.txt`: AI behavior instructions.

## 🤖 Commands

- `/moderate [text]` - Manually analyze text.
- `/status` - Check configuration.
- `/policy` - View current policy.
- `/help` - Show help message.

## License 📄

MIT License

---

**Powered by [Nova AI](https://nova-ai.nabzclan.vip/user/developer/docs/content-moderation) • [Full Documentation](https://nova-ai.nabzclan.vip/user/developer/docs/content-moderation)**
