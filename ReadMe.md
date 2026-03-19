# 🤖 ChannelAutoPost Bot — Advanced Edition

A powerful, fully button-driven Telegram Bot that automatically forwards messages from source (FROM) channels to destination (TO) channels in real-time. No typing required — everything is controlled through inline buttons.

---

## ✨ Features

### 📋 Setup Management
- Create **unlimited forwarding setups**, each with its own FROM and TO channels
- **Activate / Pause** any setup at any time with a single tap
- **Rename** or **Delete** setups whenever needed
- View all setups and their status from one screen

### 📡 Channel Support
- Supports both **Public** and **Private** Telegram channels
- Add channels by **@username**, **t.me/link**, or **numeric ID** (e.g. `-1001234567890`)
- **Public FROM channel** — works in two ways:
  - Make bot **Admin** in the channel → instant real-time forwarding
  - **Login** with your Telegram account → no admin access needed at all
- **Private FROM channel** — bot must be Admin
- **Private TO channel** — bot must be Admin to post
- If a public FROM channel is added without bot admin AND without login — the channel is **blocked from saving** and the user is prompted to login immediately

### 🔑 Userbot Login
- Login with your own Telegram account directly inside the bot
- Enter phone number (with country code) → receive OTP → enter OTP → done
- Supports **2FA (Two-Factor Authentication)** — enter cloud password if enabled
- Once logged in, the bot joins all your public FROM channels automatically on your behalf
- Session is stored securely in MongoDB
- Logout anytime with a single tap — session is permanently deleted

### 🗺️ Channel Mapping
- Add multiple FROM and TO channels in a single setup
- Messages are forwarded in sequence:
  ```
  FROM[1] → TO[1]
  FROM[2] → TO[2]
  FROM[3] → TO[2]  ← extra FROM channels map to the last TO
  ```

### 🎛️ Message Filters (11 types)
Control exactly what gets forwarded in each setup:

| Filter | Description |
|---|---|
| 📝 Text | Plain text messages |
| 🖼 Photo | Images |
| 🎬 Video | Video files |
| 📄 Document | Files and documents |
| 🎵 Audio | Audio files |
| 🎭 Sticker | Stickers |
| 🎞 GIF | Animated GIFs |
| 🎤 Voice | Voice messages |
| ⭕ Round Video | Video notes (round videos) |
| 📊 Poll | Polls |
| 🔁 Forwarded | Messages that are already forwarded |

- **Toggle All ON / All OFF** with a single button
- **🚫 Remove Forward Tag** — copies the message instead of forwarding it, so the "Forwarded from …" header is completely hidden

### 💎 Premium System
- New users get a **free trial** (configurable days) automatically on first channel add
- **Admin** can add or remove premium for any user
- **Premium expiry warning** sent 24 hours before expiration
- **Expiry notification** sent when premium runs out
- `/plan` command shows pricing with QR code payment image
- `/myplan` command shows current plan status and expiry date

### 🔒 Force Subscribe
- Force users to join specific channels before they can use the bot
- Supports **numeric Channel ID** (private or public) and **@username** — both work
- Add as many force-sub channels as you want (space-separated)
- Users who are already joined in some channels will only see the channels they have not joined yet
- **"✅ I Joined — Try Again"** button re-checks membership in real-time
- If bot cannot generate an invite link, it gracefully falls back to a public link

### 🛡️ Auto Channel Health Check
- Runs **every 1 hour** in the background
- Checks every public FROM channel for accessibility
- If a channel becomes inaccessible (deleted, banned, made private):
  - `fail_count` increases by 1
  - After **3 consecutive failures**, the channel is **auto-removed**
  - Owner receives an instant notification with setup name and channel title
  - If the channel recovers, `fail_count` resets to 0

### ⏳ Pending Private Channel Monitor
- When a private channel is added without bot admin, a **15-minute timer** starts
- If bot is made admin within 15 minutes → channel is confirmed and stays
- If 15 minutes pass without admin access → channel is **auto-removed**
- Owner receives a notification to re-add once bot is made admin

### 📢 Broadcast
- Admin can broadcast any message (HTML supported) to all registered users
- Shows sent/failed count after completion

### 🔧 Admin Panel
- View total users, total setups, premium user count, current trial days
- **Add Premium** — grant premium to any user by ID and number of days
- **Remove Premium** — revoke premium from any user
- **Set Trial Days** — change the free trial duration globally
- **Broadcast** — send a message to all users

### 🔄 Duplicate Protection
- Every forwarded message is tracked in MongoDB by message ID and channel ID
- The same message is never forwarded twice, even across restarts

### ⚡ Real-Time Forwarding
- Bot-admin mode: Telegram delivers `NewMessage` events directly — zero delay
- Userbot mode: user's account receives messages and bot forwards them instantly

---

## ⚙️ Environment Variables

Set these in your `.env` file or hosting platform:

| Variable | Description | Example |
|---|---|---|
| `APP_ID` | Telegram API ID from [my.telegram.org](https://my.telegram.org) | `12345678` |
| `API_HASH` | Telegram API Hash from [my.telegram.org](https://my.telegram.org) | `abcdef1234...` |
| `BOT_TOKEN` | Bot token from [@BotFather](https://t.me/BotFather) | `1234567890:AABBcc...` |
| `MONGO_URI` | MongoDB connection string | `mongodb+srv://user:pass@cluster...` |
| `ADMINS` | Space-separated Telegram user IDs with admin access | `123456789 987654321` |
| `FORCE_SUB` | Space-separated channel IDs or usernames for force-subscribe | `-1001234567890 SGBACKUP` |
| `PAYMENT_QR` | URL of payment QR code image shown on `/plan` | `https://i.ibb.co/...` |
| `PAYMENT_TEXT` | HTML text shown on `/plan` (leave blank to use built-in default) | `<b>Plans...</b>` |

### Notes on FORCE_SUB
- Both **numeric ID** (e.g. `-1001234567890`) and **username** (e.g. `SGBACKUP`) are supported
- Multiple channels: `FORCE_SUB=-1001234567890 -1009876543210 SGBACKUP`
- Leave blank to disable force-sub completely

---

## 📋 Bot Commands

| Command | Description |
|---|---|
| `/start` | Open the main menu |
| `/myplan` | Check your current plan and expiry date |
| `/plan` | View premium plans and pricing |
| `/help` | Show the complete help guide |
| `/cancel` | Cancel any ongoing action |

---

## 🚀 How to Deploy

### Local / VPS
```bash
git clone https://github.com/yourrepo/ChannelAutoPost
cd ChannelAutoPost
pip install -r requirements.txt
cp .env.sample .env
# Fill in all variables in .env
python3 bot.py
```

### Docker
```bash
docker build -t channelautopost .
docker run --env-file .env channelautopost
```

### Heroku / Koyeb / Railway
1. Fork this repository
2. Set all Environment Variables in your platform dashboard
3. Connect the repository and deploy — `Procfile` is already included

---

## 📦 Requirements

```
Telethon
motor
pymongo
python-decouple
pytz
```

Install all at once:
```bash
pip install -r requirements.txt
```

---

## 🗃️ MongoDB Collections

| Collection | Purpose |
|---|---|
| `users` | Registered users, premium status, trial info |
| `setups` | Forwarding setups with filters and active state |
| `channels` | FROM and TO channels linked to each setup |
| `user_sessions` | Saved userbot session strings |
| `processed_msgs` | Tracks already-forwarded message IDs |
| `pending_private` | Private channels waiting for bot to be made admin |
| `settings` | Global bot settings (e.g. trial days) |

---

## 🔐 How Userbot Login Works

1. Tap **🔑 Login Account** on the main menu
2. Send your phone number with country code (e.g. `+919876543210`)
3. Enter the OTP received in your Telegram app
4. If 2FA is enabled, enter your cloud password
5. Done — your account is now connected
6. The bot will automatically join all your existing public FROM channels
7. Any new public FROM channel you add will also be auto-joined
8. Tap **🔴 Logout Account** at any time to disconnect and delete your session

> ⚠️ Your session is stored securely in MongoDB. It is never shared or used for anything other than joining and reading FROM channels.

---

## ⚠️ Important Notes

- The bot **cannot** use `get_messages` (Telegram blocks this for bots) — forwarding is handled via real-time `NewMessage` events only
- For **public FROM channels**: either make bot admin OR login with your account — one of the two is mandatory
- For **private channels**: bot must be admin in both FROM and TO
- Premium is required to activate setups and use all forwarding features
- Admins have lifetime premium automatically

---

**Maintained by:** [@SubhajitGhosh0](https://t.me/SubhajitGhosh0)
**Support / Updates:** [@SGBACKUP](https://t.me/SGBACKUP)
