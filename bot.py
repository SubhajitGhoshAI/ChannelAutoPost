"""
ChannelAutoPost Bot — Advanced Edition (Full Button UI)
All controls via inline buttons. Minimal typing required.
"""

import logging
import asyncio
import uuid
from datetime import datetime, timedelta
import pytz
from telethon import TelegramClient, events, Button
from telethon.errors import (
    ChannelPrivateError, FloodWaitError,
    UsernameNotOccupiedError, UsernameInvalidError,
)
from decouple import config
from motor.motor_asyncio import AsyncIOMotorClient

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(asctime)s - %(message)s"
)
log = logging.getLogger("ChannelAutoPost")
IST = pytz.timezone("Asia/Kolkata")

# ── Config ────────────────────────────────────────────────────────────────────
APP_ID     = config("APP_ID", cast=int)
API_HASH   = config("API_HASH")
BOT_TOKEN  = config("BOT_TOKEN")
MONGO_URI  = config("MONGO_URI")
ADMINS     = [int(x) for x in config("ADMINS", default="").split() if x]
FORCE_SUB  = [x.strip() for x in config("FORCE_SUB", default="").split() if x]
PAYMENT_QR = config(
    "PAYMENT_QR",
    default="https://i.ibb.co/Xrbrynst/IMG-20260213-090346-384.jpg"
)
PAYMENT_TEXT = config(
    "PAYMENT_TEXT",
    default=(
        "<b>- ᴀᴠᴀɪʟᴀʙʟᴇ ᴘʟᴀɴs -\n\n"
        "- 20ʀs - 1 ᴡᴇᴇᴋ\n"
        "- 39ʀs - 1 ᴍᴏɴᴛʜ\n"
        "- 69ʀs - 3 ᴍᴏɴᴛʜs\n"
        "- 89ʀs - 6 ᴍᴏɴᴛʜs\n"
        "- 99ʀs - 1 ʏᴇᴀʀ\n\n"
        "🎁 ᴘʀᴇᴍɪᴜᴍ ꜰᴇᴀᴛᴜʀᴇs 🎁\n\n"
        "○ 🔄 ᴜɴʟɪᴍɪᴛᴇᴅ ꜰᴏʀᴡᴀʀᴅɪɴɢ sᴇᴛᴜᴘs\n"
        "○ 📡 ᴘᴜʙʟɪᴄ ᴄʜᴀɴɴᴇʟ ᴀᴜᴛᴏ-sᴄᴀɴ\n"
        "○ 🎛️ ᴀᴅᴠᴀɴᴄᴇᴅ ᴍᴇssᴀɢᴇ ꜰɪʟᴛᴇʀs\n"
        "○ 📂 ᴜɴʟɪᴍɪᴛᴇᴅ ꜰɪʟᴇ ᴀᴄᴄᴇss\n"
        "○ 🚀 ʜɪɢʜ-sᴘᴇᴇᴅ ꜰᴏʀᴡᴀʀᴅɪɴɢ\n"
        "○ ⚡ ᴘʀɪᴏʀɪᴛʏ ʀᴇǫᴜᴇsᴛ ᴄᴏᴍᴘʟᴇᴛɪᴏɴ\n"
        "○ 🛠 ᴘʀɪᴏʀɪᴛʏ ᴀᴅᴍɪɴ sᴜᴘᴘᴏʀᴛ\n\n"
        "✨ ᴜᴘɪ ɪᴅ - <code>subhajitghoshjio@ybl</code>\n\n"
        "📩 sᴇɴᴅ ᴘᴀʏᴍᴇɴᴛ sᴄʀᴇᴇɴsʜᴏᴛ ᴛᴏ - @SubhajitGhosh0\n\n"
        "ᴄʟɪᴄᴋ ᴛᴏ ᴄʜᴇᴄᴋ ʏᴏᴜʀ ᴀᴄᴛɪᴠᴇ ᴘʟᴀɴ /myplan\n\n"
        "💢 ᴍᴜsᴛ sᴇɴᴅ sᴄʀᴇᴇɴsʜᴏᴛ ᴀꜰᴛᴇʀ ᴘᴀʏᴍᴇɴᴛ\n\n"
        "‼️ ᴀꜰᴛᴇʀ sᴇɴᴅɪɴɢ ᴀ sᴄʀᴇᴇɴsʜᴏᴛ ᴘʟᴇᴀsᴇ ɢɪᴠᴇ ᴜs sᴏᴍᴇ ᴛɪᴍᴇ ᴛᴏ ᴀᴅᴅ ʏᴏᴜ ɪɴ ᴛʜᴇ ᴘʀᴇᴍɪᴜᴍ</b>"
    )
)
# Fix literal \\n from .env and wrap in <b> if not already formatted
PAYMENT_TEXT = PAYMENT_TEXT.replace("\\n", "\n")
if not PAYMENT_TEXT.startswith("<b>"):
    PAYMENT_TEXT = f"<b>{PAYMENT_TEXT}</b>"

# ── Database ──────────────────────────────────────────────────────────────────
_db_client    = AsyncIOMotorClient(MONGO_URI)
_db           = _db_client.channel_auto_post
users_col     = _db.users
setups_col    = _db.setups
channels_col  = _db.channels
processed_col = _db.processed_msgs
settings_col  = _db.settings
pending_col   = _db.pending_private

# ── Bot Client ────────────────────────────────────────────────────────────────
bot = TelegramClient("bot_session", APP_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ── FSM States ────────────────────────────────────────────────────────────────
# {user_id: {"state": str, "data": dict}}
user_states: dict = {}

S_IDLE            = "idle"
S_WAIT_SETUP_NAME = "wait_setup_name"
S_WAIT_FROM_CH    = "wait_from_ch"
S_WAIT_TO_CH      = "wait_to_ch"
S_WAIT_TRIAL_DAYS = "wait_trial_days"
S_WAIT_BROADCAST  = "wait_broadcast"
S_WAIT_PREMIUM_OP = "wait_premium_op"

def get_state(uid):
    return user_states.get(uid, {"state": S_IDLE, "data": {}})

def set_state(uid, state, data=None):
    user_states[uid] = {"state": state, "data": data or {}}

def clear_state(uid):
    user_states.pop(uid, None)

# ── DB Helpers ────────────────────────────────────────────────────────────────
DEFAULT_FILTERS = {
    "text": True, "photo": True, "video": True, "document": True,
    "audio": True, "sticker": True, "gif": True, "voice": True,
    "video_note": True, "poll": False, "forward": True,
    "remove_forward_tag": False,
}

async def get_setting(key, default=None):
    doc = await settings_col.find_one({"key": key})
    return doc["value"] if doc else default

async def set_setting(key, value):
    await settings_col.update_one({"key": key}, {"$set": {"value": value}}, upsert=True)

async def get_trial_days():
    return await get_setting("trial_days", 7)

async def is_premium(user_id):
    if user_id in ADMINS:
        return True
    user = await users_col.find_one({"user_id": user_id})
    if not user:
        return False
    pu = user.get("premium_until")
    return bool(pu and pu > datetime.utcnow())

async def ensure_user(user_id, username=None, first_name=None):
    doc = await users_col.find_one({"user_id": user_id})
    if not doc:
        await users_col.insert_one({
            "user_id": user_id, "username": username,
            "first_name": first_name, "premium_until": None,
            "trial_used": False, "joined_at": datetime.utcnow(),
        })
    else:
        upd = {}
        if username:   upd["username"]   = username
        if first_name: upd["first_name"] = first_name
        if upd:
            await users_col.update_one({"user_id": user_id}, {"$set": upd})

async def try_start_trial(user_id):
    user = await users_col.find_one({"user_id": user_id})
    if not user or user.get("trial_used") or user.get("premium_until"):
        return None
    days = await get_trial_days()
    exp = datetime.utcnow() + timedelta(days=days)
    await users_col.update_one(
        {"user_id": user_id},
        {"$set": {"premium_until": exp, "trial_used": True,
                  "expiry_warned": False, "expired_notified": False}}
    )
    return days, exp

# ── Force-sub ─────────────────────────────────────────────────────────────────
async def check_force_sub(user_id):
    if not FORCE_SUB:
        return []
    unjoined = []
    for ch in FORCE_SUB:
        try:
            entity = await bot.get_entity(ch)
            participant = await bot.get_permissions(entity, user_id)
            if not participant.is_member and not participant.is_admin:
                try:
                    from telethon.tl.functions.messages import ExportChatInviteRequest
                    inv = await bot(ExportChatInviteRequest(entity))
                    link = inv.link
                except Exception:
                    link = f"https://t.me/{ch.lstrip('@')}"
                unjoined.append((getattr(entity, "title", ch), link))
        except Exception:
            pass
    return unjoined

async def send_force_sub_msg(event, unjoined):
    lines = ["**⚠️ Please join these channels first:**\n"]
    btns = []
    for title, link in unjoined:
        lines.append(f"• {title}")
        btns.append([Button.url(f"📢 {title}", link)])
    btns.append([Button.inline("✅ I Joined — Try Again", b"check_fsub")])
    await event.respond("\n".join(lines), buttons=btns)

# ─────────────────────────────────────────────────────────────────────────────
#  UI BUILDERS
# ─────────────────────────────────────────────────────────────────────────────
async def _edit_or_respond(event, text, buttons=None, parse_mode="md"):
    try:
        await event.edit(text, buttons=buttons, parse_mode=parse_mode)
    except Exception:
        await event.respond(text, buttons=buttons, parse_mode=parse_mode)

async def show_main_menu(event, uid, edit=False):
    prem = await is_premium(uid)
    plan_icon = "💎" if prem else "🆓"
    text = (
        "🏠 **Main Menu**\n\n"
        "Manage your auto-forwarding setups using the buttons below.\n\n"
        f"Plan: {plan_icon} {'Premium ✅' if prem else 'Free / Trial'}"
    )
    btns = [
        [Button.inline("📋 My Setups",  b"setups_list"),
         Button.inline("➕ New Setup",   b"new_setup")],
        [Button.inline(f"{plan_icon} My Plan", b"my_plan"),
         Button.inline("💎 Premium",    b"premium_info")],
        [Button.inline("❓ Help",        b"help")],
    ]
    if uid in ADMINS:
        btns.append([Button.inline("🔧 Admin Panel", b"admin_panel")])
    if edit:
        await _edit_or_respond(event, text, btns)
    else:
        await event.respond(text, buttons=btns, parse_mode="md")

async def show_setups_list(event, uid):
    setups = await setups_col.find({"owner": uid}).sort("created_at", 1).to_list(50)
    if not setups:
        text = "📋 **My Setups**\n\nYou don't have any setups yet. Create one to start forwarding!"
        btns = [
            [Button.inline("➕ Create First Setup", b"new_setup")],
            [Button.inline("🏠 Main Menu", b"main_menu")],
        ]
    else:
        text = f"📋 **My Setups** ({len(setups)} total)\n\nTap a setup to manage it:"
        btns = []
        for s in setups:
            icon = "✅" if s.get("active") else "⏸"
            btns.append([Button.inline(
                f"{icon}  {s.get('name', 'Unnamed')}",
                f"setup:{s['setup_id']}".encode()
            )])
        btns.append([Button.inline("➕ New Setup", b"new_setup"),
                     Button.inline("🏠 Home", b"main_menu")])
    await _edit_or_respond(event, text, btns)

async def show_setup_detail(event, uid, setup_id):
    s = await setups_col.find_one({"setup_id": setup_id, "owner": uid})
    if not s:
        await event.answer("Setup not found!", alert=True)
        return
    from_count = await channels_col.count_documents({"setup_id": setup_id, "role": "from"})
    to_count   = await channels_col.count_documents({"setup_id": setup_id, "role": "to"})
    status = "✅ Active" if s.get("active") else "⏸ Paused"
    text = (
        f"⚙️ **Setup: {s.get('name')}**\n\n"
        f"Status: {status}\n"
        f"📥 FROM channels: **{from_count}**\n"
        f"📤 TO channels: **{to_count}**\n\n"
        "Use the buttons to manage this setup:"
    )
    toggle_label = "⏸ Pause" if s.get("active") else "▶️ Activate"
    btns = [
        [Button.inline("📥 FROM Channels", f"ch_list:from:{setup_id}".encode()),
         Button.inline("📤 TO Channels",   f"ch_list:to:{setup_id}".encode())],
        [Button.inline("➕ Add FROM",      f"add_ch:from:{setup_id}".encode()),
         Button.inline("➕ Add TO",        f"add_ch:to:{setup_id}".encode())],
        [Button.inline("🎛 Filters",       f"filters:{setup_id}".encode()),
         Button.inline(toggle_label,       f"toggle_setup:{setup_id}".encode())],
        [Button.inline("✏️ Rename",        f"rename_setup:{setup_id}".encode()),
         Button.inline("🗑 Delete",        f"del_setup_ask:{setup_id}".encode())],
        [Button.inline("◀️ My Setups",     b"setups_list")],
    ]
    await _edit_or_respond(event, text, btns)

async def show_channel_list(event, uid, setup_id, role):
    s = await setups_col.find_one({"setup_id": setup_id, "owner": uid})
    if not s:
        await event.answer("Setup not found!", alert=True)
        return
    chs = await channels_col.find({"setup_id": setup_id, "role": role}).to_list(30)
    icon = "📥" if role == "from" else "📤"
    label = "FROM" if role == "from" else "TO"
    text = f"{icon} **{label} Channels — {s.get('name')}**\n\n"
    btns = []
    if chs:
        text += f"**{len(chs)} channel(s)** — Tap 🗑 to remove:\n"
        for ch in chs:
            title = ch.get("title") or ch.get("identifier", "Unknown")
            ctype = "🌐" if ch.get("ch_type") == "public" else "🔒"
            cid = ch["ch_id"]
            btns.append([
                Button.inline(f"{ctype} {title}", f"ch_info:{role}:{setup_id}:{cid}".encode()),
                Button.inline("🗑", f"del_ch_ask:{role}:{setup_id}:{cid}".encode()),
            ])
    else:
        text += f"No {label} channels yet."
    btns.append([Button.inline(f"➕ Add {label} Channel", f"add_ch:{role}:{setup_id}".encode())])
    btns.append([Button.inline("◀️ Back to Setup", f"setup:{setup_id}".encode())])
    await _edit_or_respond(event, text, btns)

FILTER_LABELS = {
    "text":               "📝 Text",
    "photo":              "🖼 Photo",
    "video":              "🎬 Video",
    "document":           "📄 Document",
    "audio":              "🎵 Audio",
    "sticker":            "🎭 Sticker",
    "gif":                "🎞 GIF",
    "voice":              "🎤 Voice",
    "video_note":         "⭕ Round",
    "poll":               "📊 Poll",
    "forward":            "🔁 Forwarded",
    "remove_forward_tag": "🚫 Remove Fwd Tag",
}

async def show_filters(event, uid, setup_id):
    s = await setups_col.find_one({"setup_id": setup_id, "owner": uid})
    if not s:
        await event.answer("Setup not found!", alert=True)
        return
    filters = s.get("filters", DEFAULT_FILTERS.copy())
    text = (
        f"🎛 **Filters — {s.get('name')}**\n\n"
        "Toggle which message types to forward.\n"
        "🚫 **Remove Fwd Tag** — copies messages instead of forwarding "
        "(hides the 'Forwarded from …' header)."
    )
    btns = []
    keys = list(FILTER_LABELS.keys())
    for i in range(0, len(keys), 2):
        row = []
        for k in keys[i:i+2]:
            on = filters.get(k, DEFAULT_FILTERS[k])
            row.append(Button.inline(
                f"{'✅' if on else '❌'} {FILTER_LABELS[k]}",
                f"toggle_filter:{setup_id}:{k}".encode()
            ))
        btns.append(row)
    btns.append([
        Button.inline("✅ All ON",  f"filters_all_on:{setup_id}".encode()),
        Button.inline("❌ All OFF", f"filters_all_off:{setup_id}".encode()),
    ])
    btns.append([Button.inline("◀️ Back to Setup", f"setup:{setup_id}".encode())])
    await _edit_or_respond(event, text, btns)

async def show_admin_panel(event, uid):
    if uid not in ADMINS:
        await event.answer("Not authorized!", alert=True)
        return
    total_users  = await users_col.count_documents({})
    total_setups = await setups_col.count_documents({})
    prem_count   = await users_col.count_documents({"premium_until": {"$gt": datetime.utcnow()}})
    trial_days   = await get_trial_days()
    text = (
        "🔧 **Admin Panel**\n\n"
        f"👥 Users: **{total_users}**\n"
        f"⚙️ Setups: **{total_setups}**\n"
        f"💎 Premium: **{prem_count}**\n"
        f"🎁 Trial: **{trial_days} days**"
    )
    btns = [
        [Button.inline("💎 Add Premium",   b"admin_add_prem"),
         Button.inline("❌ Remove Premium", b"admin_rm_prem")],
        [Button.inline(f"🎁 Trial Days ({trial_days}d)", b"admin_trial_days")],
        [Button.inline("📢 Broadcast",     b"admin_broadcast")],
        [Button.inline("🏠 Main Menu",     b"main_menu")],
    ]
    await _edit_or_respond(event, text, btns)

async def show_my_plan(event, uid):
    if uid in ADMINS:
        text = "💎 **My Plan**\n\n👑 Admin — Lifetime Premium!"
    else:
        user = await users_col.find_one({"user_id": uid})
        pu = user.get("premium_until") if user else None
        if pu and pu > datetime.utcnow():
            exp_ist = pu.replace(tzinfo=pytz.utc).astimezone(IST)
            exp_str = exp_ist.strftime("%d %b %Y, %I:%M %p IST")
            trial_tag = " (Free Trial)" if user.get("trial_used") else ""
            text = f"💎 **My Plan**\n\n✅ Active Premium{trial_tag}\n📅 Expires: **{exp_str}**"
        else:
            text = "💎 **My Plan**\n\n❌ No active premium.\n\nBuy premium to unlock all features!"
    btns = [
        [Button.inline("💎 Get Premium", b"premium_info")],
        [Button.inline("🏠 Main Menu",   b"main_menu")],
    ]
    await _edit_or_respond(event, text, btns)

# ─────────────────────────────────────────────────────────────────────────────
#  /start
# ─────────────────────────────────────────────────────────────────────────────
@bot.on(events.NewMessage(pattern=r"^/start$", func=lambda e: e.is_private))
async def cmd_start(event):
    uid = event.sender_id
    sender = await event.get_sender()
    await ensure_user(uid, getattr(sender, "username", None),
                      getattr(sender, "first_name", None))
    unjoined = await check_force_sub(uid)
    if unjoined:
        await send_force_sub_msg(event, unjoined)
        return
    clear_state(uid)
    await show_main_menu(event, uid)

# ── /cancel ───────────────────────────────────────────────────────────────────
@bot.on(events.NewMessage(pattern=r"^/cancel$", func=lambda e: e.is_private))
async def cmd_cancel(event):
    uid = event.sender_id
    clear_state(uid)
    await event.respond("✅ Cancelled.", buttons=[[Button.inline("🏠 Main Menu", b"main_menu")]])

# ─────────────────────────────────────────────────────────────────────────────
#  CALLBACK QUERY HANDLER
# ─────────────────────────────────────────────────────────────────────────────
@bot.on(events.CallbackQuery())
async def on_callback(event):
    uid  = event.sender_id
    data = event.data.decode()

    # Force sub gate
    if data != "check_fsub":
        unjoined = await check_force_sub(uid)
        if unjoined:
            await event.answer("Please join required channels first!", alert=True)
            return

    # ── Navigation ────────────────────────────────────────────────────────
    if data == "main_menu":
        clear_state(uid)
        await show_main_menu(event, uid, edit=True)

    elif data == "setups_list":
        clear_state(uid)
        await show_setups_list(event, uid)

    elif data == "my_plan":
        await show_my_plan(event, uid)

    elif data == "help":
        text = (
            "❓ **Help Guide**\n\n"
            "**Step 1:** Tap **➕ New Setup** and give it a name.\n"
            "**Step 2:** Open the setup → tap **➕ Add FROM** and send the channel.\n"
            "**Step 3:** Tap **➕ Add TO** and send the destination channel.\n"
            "**Step 4:** Tap **▶️ Activate** to start forwarding.\n\n"
            "**Channel types:**\n"
            "🌐 Public — auto-scanned every 10s (no admin needed)\n"
            "🔒 Private — bot must be added as admin\n\n"
            "**Adding a channel:** Just send `@username`, a t.me link, or channel ID.\n\n"
            "**Mapping:** FROM[1]→TO[1], FROM[2]→TO[2], extras → last TO channel\n\n"
            "**Filters:** Control which message types are forwarded (Photo, Video, etc.)"
        )
        btns = [[Button.inline("🏠 Main Menu", b"main_menu")]]
        await _edit_or_respond(event, text, btns)

    elif data == "check_fsub":
        unjoined = await check_force_sub(uid)
        if unjoined:
            await event.answer("You haven't joined all channels yet!", alert=True)
        else:
            await event.answer("✅ Verified!", alert=False)
            await show_main_menu(event, uid, edit=True)

    # ── Premium ───────────────────────────────────────────────────────────
    elif data == "premium_info":
        try:
            await bot.send_file(
                uid, PAYMENT_QR,
                caption=PAYMENT_TEXT,
                parse_mode="html",
                buttons=[[Button.inline("◀️ Back", b"main_menu")]]
            )
            await event.answer()
        except Exception:
            await _edit_or_respond(event, PAYMENT_TEXT,
                                   [[Button.inline("◀️ Back", b"main_menu")]], "html")

    # ── New setup ──────────────────────────────────────────────────────────
    elif data == "new_setup":
        set_state(uid, S_WAIT_SETUP_NAME)
        text = (
            "📝 **Create New Setup**\n\n"
            "Send a **name** for this setup.\n"
            "_Example: NewsForward, CryptoBot, MyChannel_"
        )
        await _edit_or_respond(event, text, [[Button.inline("❌ Cancel", b"setups_list")]])

    # ── Setup detail ───────────────────────────────────────────────────────
    elif data.startswith("setup:"):
        await show_setup_detail(event, uid, data.split(":", 1)[1])

    # ── Channel list ───────────────────────────────────────────────────────
    elif data.startswith("ch_list:"):
        _, role, setup_id = data.split(":", 2)
        await show_channel_list(event, uid, setup_id, role)

    # ── Add channel ────────────────────────────────────────────────────────
    elif data.startswith("add_ch:"):
        _, role, setup_id = data.split(":", 2)
        if not await is_premium(uid):
            await event.answer("⚠️ Premium required!", alert=True)
            return
        state = S_WAIT_FROM_CH if role == "from" else S_WAIT_TO_CH
        set_state(uid, state, {"setup_id": setup_id})
        icon = "📥" if role == "from" else "📤"
        warn = "" if role == "from" else "\n\n⚠️ Bot must be **admin** in the TO channel."
        text = (
            f"{icon} **Add {'FROM' if role == 'from' else 'TO'} Channel**\n\n"
            f"Send the channel username or link:\n\n"
            f"• `@channelname`\n"
            f"• `https://t.me/channelname`\n"
            f"• Channel ID (e.g. `-1001234567890`)"
            f"{warn}"
        )
        await _edit_or_respond(event, text, [[Button.inline("❌ Cancel", f"setup:{setup_id}".encode())]])

    # ── Channel info ───────────────────────────────────────────────────────
    elif data.startswith("ch_info:"):
        _, role, setup_id, ch_id = data.split(":", 3)
        ch = await channels_col.find_one({"ch_id": ch_id, "setup_id": setup_id})
        if ch:
            ctype = "🌐 Public" if ch.get("ch_type") == "public" else "🔒 Private"
            text = (
                f"📊 **Channel Info**\n\n"
                f"**{ch.get('title', 'Unknown')}**\n"
                f"Type: {ctype}\n"
                f"ID: `{ch.get('identifier', ch_id)}`\n"
                f"Role: {'📥 FROM' if role == 'from' else '📤 TO'}\n"
                f"Fail count: {ch.get('fail_count', 0)}"
            )
            btns = [
                [Button.inline("🗑 Remove Channel", f"del_ch_ask:{role}:{setup_id}:{ch_id}".encode())],
                [Button.inline("◀️ Back", f"ch_list:{role}:{setup_id}".encode())],
            ]
            await _edit_or_respond(event, text, btns)
        else:
            await event.answer("Channel not found!", alert=True)

    # ── Delete channel (confirm) ───────────────────────────────────────────
    elif data.startswith("del_ch_ask:"):
        _, role, setup_id, ch_id = data.split(":", 3)
        ch = await channels_col.find_one({"ch_id": ch_id, "setup_id": setup_id})
        title = ch.get("title", "this channel") if ch else "this channel"
        btns = [
            [Button.inline("✅ Yes, Remove", f"del_ch_ok:{role}:{setup_id}:{ch_id}".encode()),
             Button.inline("❌ Cancel",      f"ch_list:{role}:{setup_id}".encode())],
        ]
        await _edit_or_respond(event, f"🗑 Remove **{title}**?\n\nThis cannot be undone.", btns)

    elif data.startswith("del_ch_ok:"):
        _, role, setup_id, ch_id = data.split(":", 3)
        await channels_col.delete_one({"ch_id": ch_id, "setup_id": setup_id})
        await event.answer("✅ Channel removed!")
        await show_channel_list(event, uid, setup_id, role)

    # ── Toggle setup ──────────────────────────────────────────────────────
    elif data.startswith("toggle_setup:"):
        setup_id = data.split(":", 1)[1]
        s = await setups_col.find_one({"setup_id": setup_id, "owner": uid})
        if s:
            new_active = not s.get("active", False)
            if new_active and not await is_premium(uid):
                await event.answer("⚠️ Premium required to activate!", alert=True)
                return
            await setups_col.update_one(
                {"setup_id": setup_id}, {"$set": {"active": new_active}}
            )
            await event.answer("✅ Activated!" if new_active else "⏸ Paused!")
            await show_setup_detail(event, uid, setup_id)

    # ── Rename setup ──────────────────────────────────────────────────────
    elif data.startswith("rename_setup:"):
        setup_id = data.split(":", 1)[1]
        set_state(uid, S_WAIT_SETUP_NAME, {"rename_id": setup_id})
        await _edit_or_respond(
            event,
            "✏️ **Rename Setup**\n\nSend the new name for this setup:",
            [[Button.inline("❌ Cancel", f"setup:{setup_id}".encode())]]
        )

    # ── Delete setup ──────────────────────────────────────────────────────
    elif data.startswith("del_setup_ask:"):
        setup_id = data.split(":", 1)[1]
        s = await setups_col.find_one({"setup_id": setup_id, "owner": uid})
        if s:
            btns = [
                [Button.inline("✅ Yes, Delete", f"del_setup_ok:{setup_id}".encode()),
                 Button.inline("❌ Cancel",      f"setup:{setup_id}".encode())],
            ]
            await _edit_or_respond(
                event,
                f"🗑 **Delete '{s.get('name')}'?**\n\n"
                "All channels and settings will be permanently removed!",
                btns
            )

    elif data.startswith("del_setup_ok:"):
        setup_id = data.split(":", 1)[1]
        await setups_col.delete_one({"setup_id": setup_id, "owner": uid})
        await channels_col.delete_many({"setup_id": setup_id})
        await event.answer("✅ Setup deleted!")
        await show_setups_list(event, uid)

    # ── Filters ────────────────────────────────────────────────────────────
    elif data.startswith("filters:"):
        await show_filters(event, uid, data.split(":", 1)[1])

    elif data.startswith("toggle_filter:"):
        _, setup_id, key = data.split(":", 2)
        s = await setups_col.find_one({"setup_id": setup_id, "owner": uid})
        if s:
            filters = s.get("filters", DEFAULT_FILTERS.copy())
            filters[key] = not filters.get(key, DEFAULT_FILTERS.get(key, True))
            await setups_col.update_one({"setup_id": setup_id}, {"$set": {"filters": filters}})
            await show_filters(event, uid, setup_id)

    elif data.startswith("filters_all_on:"):
        setup_id = data.split(":", 1)[1]
        await setups_col.update_one(
            {"setup_id": setup_id, "owner": uid},
            {"$set": {"filters": {k: True for k in DEFAULT_FILTERS}}}
        )
        await show_filters(event, uid, setup_id)

    elif data.startswith("filters_all_off:"):
        setup_id = data.split(":", 1)[1]
        await setups_col.update_one(
            {"setup_id": setup_id, "owner": uid},
            {"$set": {"filters": {k: False for k in DEFAULT_FILTERS}}}
        )
        await show_filters(event, uid, setup_id)

    # ── Admin panel ────────────────────────────────────────────────────────
    elif data == "admin_panel":
        await show_admin_panel(event, uid)

    elif data == "admin_add_prem":
        if uid not in ADMINS:
            await event.answer("Not authorized!", alert=True)
            return
        set_state(uid, S_WAIT_PREMIUM_OP, {"action": "add"})
        await _edit_or_respond(
            event,
            "💎 **Add Premium**\n\nSend: `<user_id> <days>`\n\nExample: `123456789 30`",
            [[Button.inline("❌ Cancel", b"admin_panel")]]
        )

    elif data == "admin_rm_prem":
        if uid not in ADMINS:
            await event.answer("Not authorized!", alert=True)
            return
        set_state(uid, S_WAIT_PREMIUM_OP, {"action": "remove"})
        await _edit_or_respond(
            event,
            "❌ **Remove Premium**\n\nSend the user ID:\n\nExample: `123456789`",
            [[Button.inline("❌ Cancel", b"admin_panel")]]
        )

    elif data == "admin_trial_days":
        if uid not in ADMINS:
            await event.answer("Not authorized!", alert=True)
            return
        set_state(uid, S_WAIT_TRIAL_DAYS)
        td = await get_trial_days()
        await _edit_or_respond(
            event,
            f"🎁 **Set Trial Days**\n\nCurrent: **{td} days**\n\nSend the new number:",
            [[Button.inline("❌ Cancel", b"admin_panel")]]
        )

    elif data == "admin_broadcast":
        if uid not in ADMINS:
            await event.answer("Not authorized!", alert=True)
            return
        set_state(uid, S_WAIT_BROADCAST)
        await _edit_or_respond(
            event,
            "📢 **Broadcast**\n\nSend the message to broadcast (HTML supported):",
            [[Button.inline("❌ Cancel", b"admin_panel")]]
        )

    try:
        await event.answer()
    except Exception:
        pass

# ─────────────────────────────────────────────────────────────────────────────
#  TEXT INPUT HANDLER (FSM)
# ─────────────────────────────────────────────────────────────────────────────
@bot.on(events.NewMessage(func=lambda e: e.is_private and not (e.message.text or "").startswith("/")))
async def on_text(event):
    uid   = event.sender_id
    text  = event.message.text.strip()
    st    = get_state(uid)
    state = st["state"]
    data  = st["data"]

    # ── Setup name / rename ───────────────────────────────────────────────
    if state == S_WAIT_SETUP_NAME:
        name = text[:40]
        rename_id = data.get("rename_id")

        if rename_id:
            # Rename existing setup
            clear_state(uid)
            await setups_col.update_one(
                {"setup_id": rename_id, "owner": uid}, {"$set": {"name": name}}
            )
            await event.respond(
                f"✅ Setup renamed to **{name}**!",
                parse_mode="md",
                buttons=[[Button.inline("◀️ Back to Setup", f"setup:{rename_id}".encode())]]
            )
        else:
            # New setup
            existing = await setups_col.find_one({"owner": uid, "name": name})
            if existing:
                await event.respond(
                    f"⚠️ A setup named **{name}** already exists! Send a different name:",
                    parse_mode="md"
                )
                return  # Keep state
            clear_state(uid)
            setup_id = str(uuid.uuid4())[:8]
            await setups_col.insert_one({
                "setup_id": setup_id, "owner": uid, "name": name,
                "active": False, "filters": DEFAULT_FILTERS.copy(),
                "created_at": datetime.utcnow(),
            })
            btns = [
                [Button.inline("➕ Add FROM Channel", f"add_ch:from:{setup_id}".encode()),
                 Button.inline("➕ Add TO Channel",   f"add_ch:to:{setup_id}".encode())],
                [Button.inline("⚙️ Open Setup",       f"setup:{setup_id}".encode())],
                [Button.inline("📋 All Setups",        b"setups_list")],
            ]
            await event.respond(
                f"✅ **Setup '{name}' created!**\n\n"
                "Now add FROM and TO channels using the buttons:",
                buttons=btns, parse_mode="md"
            )

    # ── Add FROM channel ──────────────────────────────────────────────────
    elif state == S_WAIT_FROM_CH:
        setup_id = data.get("setup_id")
        clear_state(uid)
        await process_add_channel(event, uid, text, setup_id, "from")

    # ── Add TO channel ────────────────────────────────────────────────────
    elif state == S_WAIT_TO_CH:
        setup_id = data.get("setup_id")
        clear_state(uid)
        await process_add_channel(event, uid, text, setup_id, "to")

    # ── Trial days ────────────────────────────────────────────────────────
    elif state == S_WAIT_TRIAL_DAYS:
        if uid not in ADMINS:
            clear_state(uid)
            return
        try:
            days = int(text)
            assert days >= 1
        except Exception:
            await event.respond("❌ Invalid number. Send a positive integer.")
            return
        clear_state(uid)
        await set_setting("trial_days", days)
        await event.respond(
            f"✅ Trial duration updated to **{days} days**!",
            parse_mode="md",
            buttons=[[Button.inline("◀️ Admin Panel", b"admin_panel")]]
        )

    # ── Broadcast ─────────────────────────────────────────────────────────
    elif state == S_WAIT_BROADCAST:
        if uid not in ADMINS:
            clear_state(uid)
            return
        clear_state(uid)
        all_users = await users_col.find({}, {"user_id": 1}).to_list(10000)
        sent = 0
        failed = 0
        status = await event.respond("📢 Broadcasting...")
        for u in all_users:
            try:
                await bot.send_message(u["user_id"], text, parse_mode="html")
                sent += 1
                await asyncio.sleep(0.05)
            except Exception:
                failed += 1
        await status.edit(
            f"📢 **Broadcast Done!**\n\n✅ Sent: {sent}\n❌ Failed: {failed}",
            parse_mode="md",
            buttons=[[Button.inline("◀️ Admin Panel", b"admin_panel")]]
        )

    # ── Add/Remove premium ────────────────────────────────────────────────
    elif state == S_WAIT_PREMIUM_OP:
        if uid not in ADMINS:
            clear_state(uid)
            return
        action = data.get("action", "add")
        clear_state(uid)

        if action == "remove":
            try:
                target = int(text.strip())
            except ValueError:
                await event.respond("❌ Invalid user ID.")
                return
            await users_col.update_one({"user_id": target}, {"$set": {"premium_until": None}})
            await event.respond(
                f"✅ Premium removed from `{target}`.",
                parse_mode="md",
                buttons=[[Button.inline("◀️ Admin Panel", b"admin_panel")]]
            )
            try:
                await bot.send_message(target, "⚠️ Your premium has been removed.")
            except Exception:
                pass
        else:
            parts = text.strip().split()
            if len(parts) != 2:
                await event.respond("❌ Format: `<user_id> <days>`", parse_mode="md")
                return
            try:
                target = int(parts[0])
                days   = int(parts[1])
            except ValueError:
                await event.respond("❌ Invalid input.")
                return
            exp = datetime.utcnow() + timedelta(days=days)
            await users_col.update_one(
                {"user_id": target},
                {"$set": {"premium_until": exp, "expiry_warned": False,
                          "expired_notified": False}},
                upsert=True
            )
            exp_ist = exp.replace(tzinfo=pytz.utc).astimezone(IST)
            exp_str = exp_ist.strftime("%d %b %Y, %I:%M %p IST")
            await event.respond(
                f"✅ Premium granted to `{target}` for **{days}** days.\nExpires: {exp_str}",
                parse_mode="md",
                buttons=[[Button.inline("◀️ Admin Panel", b"admin_panel")]]
            )
            try:
                await bot.send_message(
                    target,
                    f"🎉 **You've been granted Premium!**\n\n"
                    f"Duration: **{days} days**\nExpires: **{exp_str}**",
                    parse_mode="md"
                )
            except Exception:
                pass

# ─────────────────────────────────────────────────────────────────────────────
#  CHANNEL ADD LOGIC
# ─────────────────────────────────────────────────────────────────────────────
async def process_add_channel(event, uid, raw_input, setup_id, role):
    ident = raw_input.strip()
    # Normalise
    if "t.me/" in ident:
        ident = ident.split("t.me/")[-1].split("/")[0]
    if ident.startswith("@"):
        ident = ident[1:]

    wait = await event.respond("⏳ Looking up channel...")
    back_btn = [[Button.inline("◀️ Back to Setup", f"setup:{setup_id}".encode())]]

    try:
        entity = await bot.get_entity(int(ident) if ident.lstrip("-").isdigit() else ident)
    except (UsernameNotOccupiedError, UsernameInvalidError):
        await wait.edit(f"❌ Channel not found: `{ident}`\n\nCheck the username and try again.",
                        buttons=back_btn, parse_mode="md")
        return
    except Exception as e:
        await wait.edit(f"❌ Error: {str(e)[:200]}", buttons=back_btn, parse_mode="md")
        return

    ch_id   = str(entity.id)
    title   = getattr(entity, "title", ident)
    is_pub  = bool(getattr(entity, "username", None))
    ch_type = "public" if is_pub else "private"

    # Duplicate check
    if await channels_col.find_one({"ch_id": ch_id, "setup_id": setup_id, "role": role}):
        await wait.edit(
            f"⚠️ **{title}** is already in this setup as a {role.upper()} channel!",
            buttons=back_btn, parse_mode="md"
        )
        return

    # Admin check
    bot_is_admin = False
    try:
        me = await bot.get_me()
        perms = await bot.get_permissions(entity, me.id)
        bot_is_admin = perms.is_admin
    except Exception:
        pass

    # last_msg_id for public FROM
    last_msg_id = 0
    if role == "from" and ch_type == "public":
        try:
            msgs = await bot.get_messages(entity, limit=1)
            if msgs:
                last_msg_id = msgs[0].id
        except Exception:
            pass

    await channels_col.insert_one({
        "ch_id":        ch_id,
        "setup_id":     setup_id,
        "role":         role,
        "identifier":   getattr(entity, "username", None) or ch_id,
        "title":        title,
        "ch_type":      ch_type,
        "bot_is_admin": bot_is_admin,
        "last_msg_id":  last_msg_id,
        "fail_count":   0,
        "added_at":     datetime.utcnow(),
    })

    # Free trial on first channel
    trial_note = ""
    res = await try_start_trial(uid)
    if res:
        td, exp = res
        exp_ist = exp.replace(tzinfo=pytz.utc).astimezone(IST)
        trial_note = (
            f"\n\n🎁 **Free trial started!** {td} days premium, "
            f"expires {exp_ist.strftime('%d %b %Y, %I:%M %p IST')}"
        )

    # Pending private channel
    warn = ""
    if ch_type == "private" and not bot_is_admin and role == "from":
        await pending_col.insert_one({
            "ch_id": ch_id, "setup_id": setup_id,
            "uid": uid, "added_at": datetime.utcnow(),
        })
        warn = (
            "\n\n⚠️ **Private channel detected!**\n"
            "Please make the bot **admin** in this channel within **15 minutes**, "
            "or it will be auto-removed."
        )
    elif ch_type == "private" and not bot_is_admin and role == "to":
        warn = "\n\n⚠️ **Bot is not admin** in this channel! Make it admin so it can post."

    type_icon = "🌐" if ch_type == "public" else "🔒"
    role_label = "📥 FROM" if role == "from" else "📤 TO"
    btns = [
        [Button.inline(f"➕ Add Another {'FROM' if role == 'from' else 'TO'}",
                       f"add_ch:{role}:{setup_id}".encode())],
        [Button.inline("⚙️ Back to Setup", f"setup:{setup_id}".encode())],
    ]
    await wait.edit(
        f"✅ **Channel Added!**\n\n"
        f"{type_icon} **{title}**\n"
        f"Role: {role_label}  |  Type: {'Public' if ch_type == 'public' else 'Private'}"
        f"{warn}{trial_note}",
        buttons=btns, parse_mode="md"
    )

# ─────────────────────────────────────────────────────────────────────────────
#  FORWARDING ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def msg_passes_filters(msg, filters):
    # "remove_forward_tag" is a behaviour modifier, not a blocker — skip it here.
    if msg.forward and not filters.get("forward", True): return False
    if msg.text and not msg.media and not filters.get("text", True): return False
    if msg.photo and not filters.get("photo", True): return False
    if msg.video and not filters.get("video", True): return False
    # Document check must exclude all specialised media types that Telethon
    # also exposes as msg.document (video, audio, voice, sticker, gif, video_note).
    is_plain_doc = (
        msg.document
        and not msg.video
        and not msg.audio
        and not msg.voice
        and not msg.sticker
        and not msg.gif
        and not msg.video_note
    )
    if is_plain_doc and not filters.get("document", True): return False
    if msg.audio and not filters.get("audio", True): return False
    if msg.sticker and not filters.get("sticker", True): return False
    if msg.gif and not filters.get("gif", True): return False
    if msg.voice and not filters.get("voice", True): return False
    if msg.video_note and not filters.get("video_note", True): return False
    if msg.poll and not filters.get("poll", False): return False
    return True

async def already_processed(msg_id, ch_id):
    return bool(await processed_col.find_one({"msg_id": msg_id, "ch_id": ch_id}))

async def mark_processed(msg_id, ch_id):
    await processed_col.update_one(
        {"msg_id": msg_id, "ch_id": ch_id},
        {"$set": {"ts": datetime.utcnow()}}, upsert=True
    )

async def do_forward(dest, msg, remove_tag: bool):
    """Forward a message to dest.  When remove_tag is True the message is
    copied (no 'Forwarded from …' header).  Polls cannot be copied so they
    always fall back to a real forward."""
    if remove_tag and not msg.poll:
        if msg.media:
            await bot.send_file(dest, msg.media, caption=msg.text or "")
        else:
            await bot.send_message(dest, msg.text or "")
    else:
        await bot.forward_messages(dest, msg)

# Private channel event handler
@bot.on(events.NewMessage())
async def on_new_msg(event):
    if event.is_private:
        return
    raw_cid = str(event.chat_id)
    # Fix: use slicing instead of lstrip("100") which strips individual chars
    short   = raw_cid[4:] if raw_cid.startswith("-100") else raw_cid

    from_chs = await channels_col.find({
        "ch_id": {"$in": [raw_cid, short]},
        "role": "from", "ch_type": "private"
    }).to_list(10)

    for from_ch in from_chs:
        setup_id = from_ch["setup_id"]
        s = await setups_col.find_one({"setup_id": setup_id, "active": True})
        if not s:
            continue
        if not await is_premium(s["owner"]):
            continue
        if await already_processed(event.message.id, raw_cid):
            continue

        to_chs = await channels_col.find({"setup_id": setup_id, "role": "to"}).to_list(20)
        if not to_chs:
            continue

        from_list = await channels_col.find({"setup_id": setup_id, "role": "from"}).to_list(20)
        from_ids  = [c["ch_id"] for c in from_list]
        try:
            idx = from_ids.index(from_ch["ch_id"])
        except ValueError:
            idx = 0
        target = to_chs[min(idx, len(to_chs) - 1)]
        filters = s.get("filters", DEFAULT_FILTERS)
        remove_tag = filters.get("remove_forward_tag", False)

        if msg_passes_filters(event.message, filters):
            try:
                dest = int(target["ch_id"]) if target["ch_id"].lstrip("-").isdigit() else target["identifier"]
                await do_forward(dest, event.message, remove_tag)
                await mark_processed(event.message.id, raw_cid)
            except Exception as e:
                log.error(f"Private forward error: {e}")

# ─────────────────────────────────────────────────────────────────────────────
#  BACKGROUND TASKS
# ─────────────────────────────────────────────────────────────────────────────
async def task_poll_public():
    await asyncio.sleep(5)
    while True:
        try:
            active = await setups_col.find({"active": True}).to_list(200)
            for s in active:
                owner = s["owner"]
                if not await is_premium(owner):
                    continue
                sid     = s["setup_id"]
                filters = s.get("filters", DEFAULT_FILTERS)
                from_chs = await channels_col.find(
                    {"setup_id": sid, "role": "from", "ch_type": "public"}
                ).to_list(20)
                to_chs = await channels_col.find(
                    {"setup_id": sid, "role": "to"}
                ).to_list(20)
                if not from_chs or not to_chs:
                    continue

                for i, fc in enumerate(from_chs):
                    ident   = fc.get("identifier") or fc["ch_id"]
                    last_id = fc.get("last_msg_id", 0)
                    target  = to_chs[min(i, len(to_chs) - 1)]
                    remove_tag = filters.get("remove_forward_tag", False)
                    try:
                        msgs = await bot.get_messages(ident, min_id=last_id, limit=50)
                        if not msgs:
                            # No new messages — reset fail_count in case it drifted up
                            # from a previous transient error
                            if fc.get("fail_count", 0) > 0:
                                await channels_col.update_one(
                                    {"ch_id": fc["ch_id"], "setup_id": sid},
                                    {"$set": {"fail_count": 0}}
                                )
                            continue
                        msgs = sorted(msgs, key=lambda m: m.id)
                        new_last = last_id
                        for msg in msgs:
                            if await already_processed(msg.id, fc["ch_id"]):
                                continue
                            if msg_passes_filters(msg, filters):
                                try:
                                    dest = (int(target["ch_id"])
                                            if target["ch_id"].lstrip("-").isdigit()
                                            else target["identifier"])
                                    await do_forward(dest, msg, remove_tag)
                                    await mark_processed(msg.id, fc["ch_id"])
                                    await asyncio.sleep(0.5)
                                except FloodWaitError as e:
                                    await asyncio.sleep(e.seconds + 1)
                                except Exception as e:
                                    log.error(f"Poll fwd error: {e}")
                            new_last = max(new_last, msg.id)
                        if new_last > last_id:
                            await channels_col.update_one(
                                {"ch_id": fc["ch_id"], "setup_id": sid},
                                {"$set": {"last_msg_id": new_last, "fail_count": 0}}
                            )
                    except (ChannelPrivateError, UsernameNotOccupiedError,
                            UsernameInvalidError) as e:
                        # Channel is confirmed gone / private — increment fail counter
                        fail = fc.get("fail_count", 0) + 1
                        log.warning(f"Public channel '{ident}' inaccessible (fail {fail}/3): {e}")
                        await channels_col.update_one(
                            {"ch_id": fc["ch_id"], "setup_id": sid},
                            {"$set": {"fail_count": fail}}
                        )
                        if fail >= 3:
                            await channels_col.delete_one({"ch_id": fc["ch_id"], "setup_id": sid})
                            try:
                                await bot.send_message(
                                    owner,
                                    f"⚠️ **Channel Auto-Removed**\n\n"
                                    f"**{fc.get('title', ident)}** became inaccessible "
                                    f"(checked 3 times) and was removed from setup "
                                    f"**{s.get('name')}**.",
                                    parse_mode="md",
                                    buttons=[[Button.inline("📋 My Setups", b"setups_list")]]
                                )
                            except Exception:
                                pass
                    except FloodWaitError as e:
                        # Telegram rate-limit — wait and do NOT touch fail_count
                        log.warning(f"FloodWait {e.seconds}s while polling '{ident}'")
                        await asyncio.sleep(e.seconds + 1)
                    except Exception as e:
                        # Any other transient error (network, timeout, etc.)
                        # Log it but do NOT penalise the channel
                        log.error(f"Transient poll error for '{ident}': {e}")
        except Exception as e:
            log.error(f"task_poll_public: {e}")
        await asyncio.sleep(10)

async def task_monitor_pending():
    await asyncio.sleep(15)
    while True:
        try:
            cutoff  = datetime.utcnow() - timedelta(minutes=15)
            expired = await pending_col.find({"added_at": {"$lt": cutoff}}).to_list(100)
            for p in expired:
                ch_id    = p["ch_id"]
                setup_id = p["setup_id"]
                uid      = p["uid"]
                ch       = await channels_col.find_one({"ch_id": ch_id, "setup_id": setup_id})
                if ch:
                    # Public channels never need the bot to be admin —
                    # they are handled by the polling task, not pending queue.
                    if ch.get("ch_type") == "public":
                        await pending_col.delete_one({"_id": p["_id"]})
                        continue
                    # Check if bot is now admin
                    try:
                        me = await bot.get_me()
                        ident = ch.get("identifier") or ch_id
                        perms = await bot.get_permissions(ident, me.id)
                        if perms.is_admin:
                            await channels_col.update_one(
                                {"ch_id": ch_id, "setup_id": setup_id},
                                {"$set": {"bot_is_admin": True}}
                            )
                            await pending_col.delete_one({"_id": p["_id"]})
                            continue
                    except Exception:
                        pass
                    await channels_col.delete_one({"ch_id": ch_id, "setup_id": setup_id})
                await pending_col.delete_one({"_id": p["_id"]})
                s = await setups_col.find_one({"setup_id": setup_id})
                try:
                    await bot.send_message(
                        uid,
                        f"⚠️ **Channel Removed**\n\n"
                        f"**{ch.get('title', ch_id) if ch else ch_id}** was not granted admin "
                        f"within 15 min and was removed from **{s.get('name') if s else 'setup'}**.\n\n"
                        "Re-add it once the bot is made admin.",
                        parse_mode="md",
                        buttons=[[Button.inline("📋 My Setups", b"setups_list")]]
                    )
                except Exception:
                    pass
        except Exception as e:
            log.error(f"task_monitor_pending: {e}")
        await asyncio.sleep(60)

async def task_premium_expiry():
    await asyncio.sleep(30)
    while True:
        try:
            now            = datetime.utcnow()
            warn_threshold = now + timedelta(hours=24)

            # Warn soon-to-expire
            soon = await users_col.find({
                "premium_until": {"$gt": now, "$lt": warn_threshold},
                "expiry_warned": {"$ne": True}
            }).to_list(100)
            for user in soon:
                exp_ist = user["premium_until"].replace(tzinfo=pytz.utc).astimezone(IST)
                try:
                    await bot.send_message(
                        user["user_id"],
                        f"⚠️ **Premium Expiring Soon!**\n\n"
                        f"Expires: **{exp_ist.strftime('%d %b %Y, %I:%M %p IST')}**\n"
                        "Renew now to keep forwarding uninterrupted!",
                        parse_mode="md",
                        buttons=[[Button.inline("💎 Renew", b"premium_info")]]
                    )
                    await users_col.update_one(
                        {"user_id": user["user_id"]}, {"$set": {"expiry_warned": True}}
                    )
                except Exception:
                    pass

            # Notify expired
            expired = await users_col.find({
                "premium_until": {"$lt": now, "$ne": None},
                "expired_notified": {"$ne": True}
            }).to_list(100)
            for user in expired:
                try:
                    await bot.send_message(
                        user["user_id"],
                        "❌ **Premium Expired!**\n\nForwarding paused. Renew to resume!",
                        parse_mode="md",
                        buttons=[[Button.inline("💎 Renew Premium", b"premium_info")]]
                    )
                    await users_col.update_one(
                        {"user_id": user["user_id"]}, {"$set": {"expired_notified": True}}
                    )
                except Exception:
                    pass
        except Exception as e:
            log.error(f"task_premium_expiry: {e}")
        await asyncio.sleep(3600)

# ─────────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────────
async def main():
    await bot.start(bot_token=BOT_TOKEN)
    log.info("ChannelAutoPost Bot started!")
    asyncio.create_task(task_poll_public())
    asyncio.create_task(task_monitor_pending())
    asyncio.create_task(task_premium_expiry())
    await bot.run_until_disconnected()

if __name__ == "__main__":
    bot.loop.run_until_complete(main())
