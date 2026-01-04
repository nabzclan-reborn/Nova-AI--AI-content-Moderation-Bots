# Nova AI - Content Moderation Bots 🛡️

**Professional, AI-powered content moderation for Discord and Telegram.**

📚 **[Read Full Documentation (Nabzclan Developer Platform)](https://developer.nabzclan.vip/docs/endpoints/content-moderation)**


📚 **[Read Full Documentation (Nova AI)](https://nova-ai.nabzclan.vip/user/developer/docs/content-moderation)**


This repository contains two fully-featured bots powered by the **Nova AI Content Moderation API**, designed to keep your communities safe from spam, hate speech, harassment, and other policy violations.


## 📂 Repository Structure

- **[`/discord`](./discord)** - Discord Bot source code and setup.
- **[`/telegram`](./telegram)** - Telegram Bot source code and setup.

## 🚀 Getting Started

Choose your platform:

### For Discord
Go to the [`discord/`](./discord) folder and follow the instructions to set up your bot, invite it to your server, and configure your policies.

### For Telegram
Go to the [`telegram/`](./telegram) folder to set up the bot, add it to your group, and enable privacy settings.

## � API Keys

You can choose between two providers:

1. **Nova AI (Paid / Enterprise)**
   - Recommended for production use.
   - [Get API Key](https://nova-ai.nabzclan.vip/user/developer)

2. **Nabzclan Developer Platform (Free)**
   - Free tier with rate limits.
   - [Get API Key](https://developer.nabzclan.vip/dashboard/tokens)

Configure your choice in `bot.py` via the `API_PROVIDER` setting.

## �🛠️ Configuration

Both bots share a similar configuration philosophy:
1. **`.env`**: Store your API keys (`NOVA_API_KEY`, `DISCORD_BOT_TOKEN`, `TELEGRAM_BOT_TOKEN`).
2. **`bot.py`**: Configure settings like `AUTO_MODERATE_ACTION` (delete, warn, ban) and severity thresholds.
3. **`policy.txt`**: Write your custom moderation rules in plain English.

## 🔒 Privacy & Safety

- **Data Privacy:** Messages are processed by the Nova AI API for moderation purposes.
- **Open Source:** You have full control over the code and can host it on your own infrastructure.

---
## 📄 License & Attribution

This project is open-source under the **MIT License**.

**❤️ Give Props:**
If you use this bot, please keep the attribution to **Nova AI** in the footer of messages and documentation. We worked hard to provide this tool for allowed use!

See [LICENSE](./LICENSE) for full details.

**🔗 Official Repository:** [nabzclan-reborn/Nova-AI--AI-content-Moderation-Bots](https://github.com/nabzclan-reborn/Nova-AI--AI-content-Moderation-Bots)

---
*Powered by [Nova AI](https://nova.nabzclan.vip) - NabzClan*
