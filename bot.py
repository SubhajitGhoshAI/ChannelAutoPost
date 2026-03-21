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
from telethon.sessions import StringSession
from telethon.errors import (
    ChannelPrivateError, FloodWaitError,
    UsernameNotOccupiedError, UsernameInvalidError,
    SessionPasswordNeededError, PhoneCodeInvalidError,
    PhoneCodeExpiredError,
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
        "- 49ʀs - 1 ᴡᴇᴇᴋ\n"
        "- 99ʀs - 1 ᴍᴏɴᴛʜ\n"
        "- 179ʀs - 3 ᴍᴏɴᴛʜs\n"
        "- 249ʀs - 6 ᴍᴏɴᴛʜs\n"
        "- 299ʀs - 1 ʏᴇᴀʀ (🔥ʙᴇsᴛ ᴠᴀʟᴜᴇ)\n\n"
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
sessions_col  = _db.user_sessions    # {user_id, session_string, phone}

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
S_WAIT_PHONE      = "wait_phone"
S_WAIT_OTP        = "wait_otp"
S_WAIT_2FA        = "wait_2fa"

# Active userbot clients {user_id: TelegramClient}
user_clients:  dict = {}
# Temporary clients used during login before session is saved
login_clients: dict = {}
# Force-sub check cache {user_id: (datetime, result)}
_fsub_cache:   dict = {}
FSUB_CACHE_TTL = 300  # 5 minutes

# ── Per-setup Forward Queues (each setup gets its own sequential queue) ────────
setup_queues:  dict = {}   # {setup_id: asyncio.Queue}
setup_workers: dict = {}   # {setup_id: asyncio.Task}

async def _setup_forward_worker(setup_id: str):
    """One worker per setup — sequential, 2s gap, never misses a message."""
    q = setup_queues[setup_id]
    while True:
        try:
            item        = await q.get()
            dest        = item["dest"]
            msg         = item["msg"]
            remove_tag  = item["remove_tag"]
            client_use  = item["client_to_use"]
            owner_id    = item["owner_id"]
            target      = item["target"]
            from_ch_id  = item["from_ch_id"]
            try:
                await do_forward(dest, msg, remove_tag, client_to_use=client_use)
                await channels_col.update_one(
                    {"ch_id": from_ch_id, "setup_id": setup_id},
                    {"$set": {"last_msg_id": msg.id}}
                )
            except FloodWaitError as e:
                log.warning(f"[setup={setup_id}] FloodWait {e.seconds}s — retrying after wait")
                await asyncio.sleep(e.seconds + 1)
                try:
                    await do_forward(dest, msg, remove_tag, client_to_use=client_use)
                    await channels_col.update_one(
                        {"ch_id": from_ch_id, "setup_id": setup_id},
                        {"$set": {"last_msg_id": msg.id}}
                    )
                except Exception as retry_e:
                    log.error(f"[setup={setup_id}] Retry after FloodWait failed: {retry_e}")
            except Exception as e:
                log.error(f"[setup={setup_id}] Queue forward error: {e}")
                err_str = str(e).lower()
                if any(k in err_str for k in ["admin", "forbidden", "rights", "not allowed", "permission", "chat_write_forbidden", "chatwriteforbidden"]):
                    try:
                        if client_use is None:
                            reason = (
                                "**Bot is not admin** in this TO channel or does not have post permission.\n\n"
                                "Please make the Bot admin in this channel and forwarding will resume automatically."
                            )
                        else:
                            reason = (
                                "Your **logged-in Telegram account** is not admin in this TO channel.\n\n"
                                "Please make your account admin in this channel and forwarding will resume automatically."
                            )
                        await bot.send_message(
                            owner_id,
                            f"❌ **Forwarding Stopped!**\n\n"
                            f"📤 TO Channel: **{target.get('title', target['ch_id'])}**\n\n"
                            f"🔧 Reason: {reason}",
                            parse_mode="md",
                            buttons=[[Button.inline("📋 My Setups", b"setups_list")]]
                        )
                    except Exception:
                        pass
                elif any(k in err_str for k in ["input entity", "could not find", "peerchannel", "peeruser", "no user", "invalid peer"]):
                    try:
                        if client_use is None:
                            reason = (
                                "**Bot cannot find this TO channel internally.**\n\n"
                                "✅ **Fix:** Remove this TO channel and re-add it — "
                                "bot will auto-connect when re-added as admin."
                            )
                        else:
                            reason = (
                                "**Your logged-in account has not joined this TO channel.**\n\n"
                                "✅ **Fix:** Manually join this TO channel with your Telegram account, "
                                "then forwarding will resume automatically."
                            )
                        await bot.send_message(
                            owner_id,
                            f"❌ **Forwarding Failed!**\n\n"
                            f"📤 TO Channel: **{target.get('title', target['ch_id'])}**\n\n"
                            f"🔧 Reason: {reason}",
                            parse_mode="md",
                            buttons=[[Button.inline("📋 My Setups", b"setups_list")]]
                        )
                    except Exception:
                        pass
            finally:
                q.task_done()
            await asyncio.sleep(3)
        except asyncio.CancelledError:
            log.info(f"Worker {setup_id} cancelled")
            return
        except Exception as e:
            log.error(f"_setup_forward_worker [{setup_id}]: {e}")

def get_setup_queue(setup_id: str) -> asyncio.Queue:
    """Return existing queue for setup, or create a new one with its own worker."""
    if setup_id not in setup_queues:
        setup_queues[setup_id] = asyncio.Queue()
        setup_workers[setup_id] = asyncio.create_task(
            _setup_forward_worker(setup_id)
        )
    return setup_queues[setup_id]

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

async def ensure_indexes():
    """Create DB indexes for performance and TTL cleanup."""
    await users_col.create_index([("user_id", 1)], unique=True, background=True)
    await setups_col.create_index([("setup_id", 1)], background=True)
    await setups_col.create_index([("owner", 1)], background=True)
    await channels_col.create_index([("ch_id", 1), ("setup_id", 1), ("role", 1)], background=True)
    await channels_col.create_index([("setup_id", 1), ("role", 1)], background=True)
    await processed_col.create_index([("msg_id", 1), ("ch_id", 1)], background=True)
    # TTL: auto-delete processed entries after 7 days
    await processed_col.create_index([("ts", 1)], expireAfterSeconds=604800, background=True)
    await sessions_col.create_index([("user_id", 1)], unique=True, background=True)
    log.info("DB indexes ensured")

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
    # Serve from cache if fresh
    cached = _fsub_cache.get(user_id)
    if cached:
        ts, result = cached
        if (datetime.utcnow() - ts).total_seconds() < FSUB_CACHE_TTL:
            return result
    from telethon.tl.functions.channels import GetParticipantRequest
    from telethon.errors import UserNotParticipantError
    unjoined = []
    for ch in FORCE_SUB:
        try:
            resolved = int(ch) if ch.lstrip("-").isdigit() else ch
            entity = await bot.get_entity(resolved)
            is_joined = False
            try:
                await bot(GetParticipantRequest(entity, user_id))
                is_joined = True
            except UserNotParticipantError:
                is_joined = False
            except Exception:
                is_joined = False
            if not is_joined:
                username = getattr(entity, "username", None)
                link = f"https://t.me/{username}" if username else None
                if not link:
                    try:
                        from telethon.tl.functions.messages import ExportChatInviteRequest
                        inv = await bot(ExportChatInviteRequest(entity))
                        link = inv.link
                    except Exception:
                        pass
                if link:
                    unjoined.append((getattr(entity, "title", str(ch)), link))
        except Exception:
            pass
    _fsub_cache[user_id] = (datetime.utcnow(), unjoined)
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
    has_session = uid in user_clients
    login_label = "🔴 Logout Account" if has_session else "🔑 Login Account"
    login_cb    = b"logout_confirm"    if has_session else b"login_start"
    btns = [
        [Button.inline("📋 My Setups",  b"setups_list"),
         Button.inline("➕ New Setup",   b"new_setup")],
        [Button.inline(f"{plan_icon} My Plan", b"my_plan"),
         Button.inline("💎 Premium",    b"premium_info")],
        [Button.inline(login_label,     login_cb),
         Button.inline("❓ Help",       b"help")],
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


# ── /myplan ───────────────────────────────────────────────────────────────────
@bot.on(events.NewMessage(pattern=r"^/myplan$", func=lambda e: e.is_private))
async def cmd_myplan(event):
    uid = event.sender_id
    await ensure_user(uid)
    unjoined = await check_force_sub(uid)
    if unjoined:
        await send_force_sub_msg(event, unjoined)
        return
    await show_my_plan(event, uid)

# ── /plan ─────────────────────────────────────────────────────────────────────
@bot.on(events.NewMessage(pattern=r"^/plan$", func=lambda e: e.is_private))
async def cmd_plan(event):
    uid = event.sender_id
    await ensure_user(uid)
    unjoined = await check_force_sub(uid)
    if unjoined:
        await send_force_sub_msg(event, unjoined)
        return
    try:
        await bot.send_file(
            uid, PAYMENT_QR,
            caption=PAYMENT_TEXT,
            parse_mode="html",
            buttons=[[Button.inline("◀️ Back", b"main_menu")]]
        )
    except Exception:
        await event.respond(PAYMENT_TEXT, parse_mode="html",
                            buttons=[[Button.inline("◀️ Back", b"main_menu")]])

# ── /help ─────────────────────────────────────────────────────────────────────
@bot.on(events.NewMessage(pattern=r"^/help$", func=lambda e: e.is_private))
async def cmd_help(event):
    uid = event.sender_id
    await ensure_user(uid)
    unjoined = await check_force_sub(uid)
    if unjoined:
        await send_force_sub_msg(event, unjoined)
        return
    text = (
        "📘 **ChannelAutoPost — Complete Help Guide**\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "**🤖 What Does This Bot Do?**\n"
        "Automatically forwards new messages from source (FROM) channels "
        "to destination (TO) channels in real-time.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "**⚡ Quick Start (5 Steps)**\n"
        "1️⃣ /start → tap **➕ New Setup** → enter a name\n"
        "2️⃣ Tap **➕ Add FROM** → send the source channel\n"
        "3️⃣ Tap **➕ Add TO** → send the destination channel\n"
        "4️⃣ Tap **▶️ Activate** to start forwarding\n"
        "5️⃣ Done! New posts will be auto-forwarded instantly\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "**📡 Channel Types — Who Needs Admin Where**\n\n"
        "🌐 **Public Channel** (has a @username)\n\n"
        "  📥 As a FROM channel:\n"
        "  ▸ Option A: Make **Bot Admin** in the FROM channel → works instantly\n"
        "  ▸ Option B: Use **🔑 Login** with your Telegram account\n"
        "    → No bot admin needed, your account joins the channel automatically\n\n"
        "  📤 As a TO channel:\n"
        "  ▸ If Bot is admin in FROM → make only the **Bot admin** in the TO channel\n"
        "  ▸ If you used Login (no bot admin in FROM) → make **BOTH** admin in the TO channel:\n"
        "    • 🤖 Add the **Bot** as admin in the TO channel\n"
        "    • 👤 Add your **logged-in Telegram account** as admin in the TO channel\n"
        "    ⚠️ Missing either one will stop forwarding completely\n\n"
        "🔒 **Private Channel** (no @username)\n\n"
        "  📥 As a FROM channel:\n"
        "  ▸ Bot MUST be **Admin** in the FROM channel\n\n"
        "  📤 As a TO channel:\n"
        "  ▸ Bot MUST be **Admin** in the TO channel\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "**🔑 Login Feature — Step by Step**\n"
        "Use this when you cannot make the bot admin in a public FROM channel:\n"
        "  • Main Menu → tap **🔑 Login Account**\n"
        "  • Enter your phone number with country code (e.g. +919876543210)\n"
        "  • Enter the OTP received in your Telegram app\n"
        "  • If 2FA is enabled, enter your cloud password\n"
        "  • ✅ Once logged in, public FROM channels are auto-joined by your account\n"
        "  • To disconnect → Main Menu → tap **🔴 Logout Account**\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "**📥 How to Add a Channel**\n"
        "Send the channel in any of these formats:\n"
        "  • `@channelname`\n"
        "  • `https://t.me/channelname`\n"
        "  • Numeric ID: `-1001234567890`\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "**🗺️ Channel Mapping — How It Works**\n\n"
        "📌 **FROM = TO (equal count)** → perfect 1-to-1 mapping\n"
        "  FROM[A] → TO[X]\n"
        "  FROM[B] → TO[Y]\n"
        "  FROM[C] → TO[Z]\n\n"
        "📌 **FROM > TO (more FROM than TO)** → extra FROM channels map to the last TO\n"
        "  FROM[A] → TO[X]\n"
        "  FROM[B] → TO[Y]\n"
        "  FROM[C] → TO[Y] _(extra, maps to last TO)_\n"
        "  FROM[D] → TO[Y] _(extra, maps to last TO)_\n\n"
        "📌 **FROM < TO (more TO than FROM)** → every FROM broadcasts to all TO channels\n"
        "  FROM[A] → TO[X], TO[Y], TO[Z] _(all of them)_\n"
        "  FROM[B] → TO[X], TO[Y], TO[Z] _(all of them)_\n\n"
        "📌 **FROM 1, TO 1** → direct forward\n"
        "  FROM[A] → TO[X]\n\n"
        "⚠️ Channel order is based on the order you added them.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "**🎛 Filters — Control What Gets Forwarded**\n"
        "Inside each setup tap **🎛 Filters** to toggle:\n"
        "  📝 Text · 🖼 Photo · 🎬 Video · 📄 Document\n"
        "  🎵 Audio · 🎭 Sticker · 🎞 GIF · 🎤 Voice\n"
        "  ⭕ Round Video · 📊 Poll · 🔁 Forwarded msgs\n"
        "  🚫 **Remove Fwd Tag** — sends as a copy (no 'Forwarded from' header)\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "**⚙️ Setup Controls**\n"
        "  ▶️ **Activate / ⏸ Pause** — start or pause forwarding\n"
        "  ✏️ **Rename** — change the setup name\n"
        "  🗑 **Delete** — permanently remove setup and all its channels\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "**🛡 Auto Channel Health Check**\n"
        "If a FROM channel is deleted, banned, or made private:\n"
        "The bot checks it up to 3 times. If all 3 checks fail, "
        "the channel is auto-removed and you receive a notification.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "**⚠️ The Bot Will Notify You When**\n"
        "  • Bot or your account is not admin in a TO channel → told exactly what to fix\n"
        "  • Bot cannot find a TO channel internally → told to re-add it\n"
        "  • Your login session expires → told to login again\n"
        "  • A FROM channel becomes inaccessible → auto-removed with notification\n"
        "  • Premium expires in 24 hours → advance warning sent\n"
        "  • Premium expires → forwarding paused, renewal reminder sent\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "**💎 Premium Required For**\n"
        "  • Creating and activating setups\n"
        "  • Adding channels\n"
        "  • All forwarding features\n\n"
        "Use /plan to see pricing · /myplan to check your current plan\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "**📋 All Commands**\n"
        "  /start — Open main menu\n"
        "  /myplan — Check your current plan\n"
        "  /plan — View premium plans & pricing\n"
        "  /help — Show this guide\n"
        "  /cancel — Cancel any ongoing action"
    )
    await event.respond(text, parse_mode="md",
                        buttons=[[Button.inline("🏠 Main Menu", b"main_menu")]])

# ─────────────────────────────────────────────────────────────────────────────
#  ADMIN COMMANDS
# ─────────────────────────────────────────────────────────────────────────────
@bot.on(events.NewMessage(pattern=r"^/listpremium$", func=lambda e: e.is_private))
async def cmd_listpremium(event):
    uid = event.sender_id
    if uid not in ADMINS:
        await event.respond("❌ Not authorized!")
        return
    now = datetime.utcnow()
    active_users = await users_col.find({
        "premium_until": {"$gt": now}
    }).sort("premium_until", 1).to_list(500)
    if not active_users:
        await event.respond("📋 **Active Premium Users**\n\nNo active premium users found.")
        return
    header = f"👑 **Active Premium Users: {len(active_users)}**\n"
    user_lines = []
    for i, user in enumerate(active_users, 1):
        uid_u       = user["user_id"]
        days_left   = (user["premium_until"] - now).days
        is_trial    = user.get("trial_used") and user.get("premium_until")
        plan_icon   = "🆓" if is_trial else "💎"
        user_setups = await setups_col.find({"owner": uid_u}).to_list(100)
        setup_ids   = [s["setup_id"] for s in user_setups]
        from_chs    = await channels_col.count_documents({"setup_id": {"$in": setup_ids}, "role": "from"})
        to_chs      = await channels_col.count_documents({"setup_id": {"$in": setup_ids}, "role": "to"})
        name        = user.get("first_name") or user.get("username") or str(uid_u)
        user_lines.append(
            f"{i}. {plan_icon} `{uid_u}` — **{name}**\n"
            f"   ⚙️ Setups: {len(user_setups)} | 📥 FROM: {from_chs} | 📤 TO: {to_chs}\n"
            f"   ⏳ Days Left: {days_left}"
        )
    MAX_LEN = 4000
    chunks   = []
    current  = header
    for line in user_lines:
        block = "\n\n" + line
        if len(current) + len(block) > MAX_LEN:
            chunks.append(current)
            current = line
        else:
            current += block
    if current:
        chunks.append(current)
    for chunk in chunks:
        await event.respond(chunk, parse_mode="md")
        
@bot.on(events.NewMessage(pattern=r"^/status$", func=lambda e: e.is_private))
async def cmd_status(event):
    uid = event.sender_id
    if uid not in ADMINS:
        await event.respond("❌ Not authorized!")
        return
    now           = datetime.utcnow()
    total_users   = await users_col.count_documents({})
    active_prem   = await users_col.count_documents({"premium_until": {"$gt": now}})
    trial_users   = await users_col.count_documents({
        "trial_used": True, "premium_until": {"$gt": now}
    })
    paid_users    = active_prem - trial_users
    expired       = await users_col.count_documents({
        "premium_until": {"$lt": now, "$ne": None}
    })
    free_users    = total_users - active_prem - expired
    total_setups  = await setups_col.count_documents({})
    active_setups = await setups_col.count_documents({"active": True})
    total_from    = await channels_col.count_documents({"role": "from"})
    total_to      = await channels_col.count_documents({"role": "to"})
    text = (
        "📊 **Bot Status**\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👥 **Users**\n"
        f"  • Total: **{total_users}**\n"
        f"  • 💎 Paid Premium: **{paid_users}**\n"
        f"  • 🆓 Free Trial: **{trial_users}**\n"
        f"  • ❌ Expired: **{expired}**\n"
        f"  • 🔵 Free (no trial): **{free_users}**\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚙️ **Setups**\n"
        f"  • Total: **{total_setups}**\n"
        f"  • ✅ Active: **{active_setups}**\n"
        f"  • ⏸ Paused: **{total_setups - active_setups}**\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📡 **Channels**\n"
        f"  • 📥 FROM Total: **{total_from}**\n"
        f"  • 📤 TO Total: **{total_to}**"
    )
    await event.respond(text, parse_mode="md",
                        buttons=[[Button.inline("🔧 Admin Panel", b"admin_panel")]])

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
            await send_force_sub_msg(event, unjoined)
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
        await event.answer()
        text = (
            "📘 **ChannelAutoPost — Complete Help Guide**\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**⚡ Quick Start**\n"
            "1️⃣ Tap **➕ New Setup** → enter a name\n"
            "2️⃣ Tap **➕ Add FROM** → send the source channel\n"
            "3️⃣ Tap **➕ Add TO** → send the destination channel\n"
            "4️⃣ Tap **▶️ Activate** to start forwarding\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**📡 Channel Types**\n"
            "🌐 **Public** — make bot Admin OR use /login\n"
            "🔒 **Private** — bot must be Admin in both channels\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**🔑 Login (Public channels without Admin)**\n"
            "Tap **🔑 Login Account** → enter phone + OTP\n"
            "Your account joins public FROM channels automatically\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**📥 Add Channels**\n"
            "`@username` · `t.me/link` · `-1001234567890`\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**📋 Commands**\n"
            "/start · /myplan · /plan · /help · /cancel\n\n"
            "For the full guide use /help"
        )
        btns = [[Button.inline("🏠 Main Menu", b"main_menu")]]
        await _edit_or_respond(event, text, btns)

    elif data == "check_fsub":
        _fsub_cache.pop(uid, None)
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
            res = await try_start_trial(uid)
            if not res:
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
        await pending_col.delete_one({"ch_id": ch_id, "setup_id": setup_id})
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
        # Cleanup in-memory queue and worker task to prevent ghost forwarding
        if setup_id in setup_workers:
            setup_workers[setup_id].cancel()
            del setup_workers[setup_id]
        if setup_id in setup_queues:
            del setup_queues[setup_id]
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

    # ── Login / Logout ────────────────────────────────────────────────────
    elif data == "login_start":
        if uid in user_clients:
            await event.answer("✅ Already logged in!", alert=True)
            return
        if uid in login_clients:
            await event.answer("⏳ Login already in progress.", alert=True)
            return
        set_state(uid, S_WAIT_PHONE)
        await _edit_or_respond(
            event,
            "🔑 **Login with Your Telegram Account**\n\n"
            "This allows the bot to join public channels on your behalf — "
            "so you don't need to make the bot admin in FROM channels.\n\n"
            "Please send your **phone number** with country code:\n"
            "_Example: +919876543210_\n\n"
            "⚠️ Your session is stored securely. Use **Logout** anytime to remove it.",
            [[Button.inline("❌ Cancel", b"main_menu")]]
        )

    elif data == "logout_confirm":
        if uid not in user_clients:
            await event.answer("No active session.", alert=True)
            return
        await _edit_or_respond(
            event,
            "🔴 **Logout Confirmation**\n\n"
            "Are you sure you want to log out?\n"
            "Your Telegram account session will be deleted from the bot.",
            [
                [Button.inline("✅ Yes, Logout", b"logout_ok"),
                 Button.inline("❌ Cancel",      b"main_menu")],
            ]
        )

    elif data == "logout_ok":
        try:
            client = user_clients.pop(uid, None)
            if client:
                await client.disconnect()
        except Exception:
            pass
        await sessions_col.delete_one({"user_id": uid})
        await event.answer("✅ Logged out successfully!")
        await show_main_menu(event, uid, edit=True)

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
    unjoined = await check_force_sub(uid)
    if unjoined:
        await send_force_sub_msg(event, unjoined)
        return
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
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds + 1)
                try:
                    await bot.send_message(u["user_id"], text, parse_mode="html")
                    sent += 1
                except Exception:
                    failed += 1
            except Exception:
                failed += 1
        await status.edit(
            f"📢 **Broadcast Done!**\n\n✅ Sent: {sent}\n❌ Failed: {failed}",
            parse_mode="md",
            buttons=[[Button.inline("◀️ Admin Panel", b"admin_panel")]]
        )

    # ── Login: phone number ──────────────────────────────────────────────
    elif state == S_WAIT_PHONE:
        phone = text.strip()
        if not phone.startswith("+"):
            await event.respond("❌ Phone must start with country code, e.g. **+919876543210**",
                                parse_mode="md")
            return
        wait_msg = await event.respond("⏳ Sending OTP...")
        try:
            tmp = TelegramClient(StringSession(), APP_ID, API_HASH)
            await tmp.connect()
            result = await tmp.send_code_request(phone)
            login_clients[uid] = tmp
            set_state(uid, S_WAIT_OTP, {"phone": phone, "phone_code_hash": result.phone_code_hash})
            await wait_msg.edit(
                "📱 **OTP Sent!**\n\n"
                "Enter the **verification code** you received on Telegram:\n"
                "_Example: 12345_\n\n"
                "Send /cancel to abort.",
                parse_mode="md"
            )
        except Exception as e:
            login_clients.pop(uid, None)
            clear_state(uid)
            await wait_msg.edit(f"❌ Failed to send OTP: {str(e)[:200]}\n\nTry again with /start.",
                                parse_mode="md")

    # ── Login: OTP code ───────────────────────────────────────────────────
    elif state == S_WAIT_OTP:
        code  = text.strip().replace(" ", "")
        phone = data.get("phone")
        pch   = data.get("phone_code_hash")
        tmp   = login_clients.get(uid)
        if not tmp:
            clear_state(uid)
            await event.respond("❌ Session expired. Please start again with /start.")
            return
        try:
            await tmp.sign_in(phone, code, phone_code_hash=pch)
            # Save session
            session_str = tmp.session.save()
            await sessions_col.update_one(
                {"user_id": uid},
                {"$set": {"user_id": uid, "session_string": session_str, "phone": phone}},
                upsert=True
            )
            login_clients.pop(uid, None)
            clear_state(uid)
            await tmp.disconnect()
            await start_userbot(uid, session_str)
            asyncio.create_task(_join_public_channels_for_user(uid, user_clients.get(uid)))
            await event.respond(
                "✅ **Login Successful!**\n\n"
                "Your account is now connected. Public FROM channels will be "
                "auto-joined by your account — no bot admin needed.\n\n"
                "Tap **🔴 Logout Account** on the main menu to disconnect anytime.",
                parse_mode="md",
                buttons=[[Button.inline("🏠 Main Menu", b"main_menu")]]
            )
        except PhoneCodeInvalidError:
            await event.respond("❌ Wrong OTP. Please try again:")
        except PhoneCodeExpiredError:
            login_clients.pop(uid, None)
            clear_state(uid)
            await event.respond("❌ OTP expired. Please start login again from /start.")
        except SessionPasswordNeededError:
            set_state(uid, S_WAIT_2FA, {"phone": phone, "phone_code_hash": pch})
            await event.respond(
                "🔒 **Two-Factor Authentication Required**\n\n"
                "Your account has 2FA enabled. Please enter your **cloud password**:",
                parse_mode="md"
            )
        except Exception as e:
            login_clients.pop(uid, None)
            clear_state(uid)
            await event.respond(f"❌ Login failed: {str(e)[:200]}\n\nTry again from /start.")

    # ── Login: 2FA password ───────────────────────────────────────────────
    elif state == S_WAIT_2FA:
        password = text.strip()
        phone    = data.get("phone")
        tmp      = login_clients.get(uid)
        if not tmp:
            clear_state(uid)
            await event.respond("❌ Session expired. Please start again with /start.")
            return
        try:
            await tmp.sign_in(password=password)
            session_str = tmp.session.save()
            await sessions_col.update_one(
                {"user_id": uid},
                {"$set": {"user_id": uid, "session_string": session_str, "phone": phone}},
                upsert=True
            )
            login_clients.pop(uid, None)
            clear_state(uid)
            await tmp.disconnect()
            await start_userbot(uid, session_str)
            asyncio.create_task(_join_public_channels_for_user(uid, user_clients.get(uid)))
            await event.respond(
                "✅ **Login Successful!**\n\n"
                "Your account is now connected.",
                parse_mode="md",
                buttons=[[Button.inline("🏠 Main Menu", b"main_menu")]]
            )
        except Exception as e:
            login_clients.pop(uid, None)
            clear_state(uid)
            await event.respond(f"❌ 2FA failed: {str(e)[:200]}\n\nTry again from /start.")

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

    # Block: public FROM + no admin + no userbot = impossible, don't even save
    if ch_type == "public" and role == "from" and not bot_is_admin and uid not in user_clients:
        await wait.edit(
            f"⛔ **Channel Not Added**\n\n"
            f"**{title}** is a public FROM channel, but:\n"
            "• Bot is **not admin** in this channel\n"
            "• You are **not logged in**\n\n"
            "Without at least one of these, forwarding is **impossible** — "
            "so the channel was **not saved**.\n\n"
            "👇 Login with your Telegram account first, then add this channel again — "
            "no admin access needed!",
            parse_mode="md",
            buttons=[
                [Button.inline("🔑 Login Now", b"login_start")],
                [Button.inline("◀️ Back to Setup", f"setup:{setup_id}".encode())],
            ]
        )
        return

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

    # Auto-join public FROM channel via userbot if logged in
    if ch_type == "public" and role == "from" and uid in user_clients:
        asyncio.create_task(_userbot_join(uid, getattr(entity, "username", None) or ch_id, ch_title=title, notify=True))
    # Pending private channel
    warn = ""
    if ch_type == "private" and not bot_is_admin and role == "from" and uid not in user_clients:
        await pending_col.insert_one({
            "ch_id": ch_id, "setup_id": setup_id,
            "uid": uid, "added_at": datetime.utcnow(),
        })
        warn = (
            "\n\n⚠️ **Private FROM Channel — Action Required!**\n\n"
            "Bot is **not admin** in this channel. You have **15 minutes** to do one of the following:\n\n"
            "**Option A — Make Bot Admin:**\n"
            "Add the bot as admin in this FROM channel → forwarding starts automatically\n\n"
            "**Option B — Use Your Account:**\n"
            "• Tap **🔑 Login Account** on the main menu\n"
            "• After login, **manually join** this FROM channel with your Telegram account\n"
            "• No bot admin needed\n\n"
            "⏱ If neither is done within **15 minutes**, this channel will be auto-removed."
        )
    elif ch_type == "private" and not bot_is_admin and role == "from" and uid in user_clients:
        warn = (
            "\n\n⚠️ **Private FROM Channel — Manual Join Required!**\n\n"
            "Your logged-in Telegram account must be a **member** of this private channel.\n\n"
            "✅ **What to do:**\n"
            "• Join this private channel manually with your Telegram account\n"
            "• Once joined, forwarding will work automatically\n\n"
            "❌ If your account is not a member of this channel, forwarding will NOT work."
        )
    elif not bot_is_admin and role == "to":
        if uid in user_clients:
            warn = (
                "\n\n⚠️ **Bot is not admin in this TO channel — Forwarding will NOT work!**\n\n"
                "You must make **both** of the following admin in this TO channel:\n"
                "• 🤖 **Bot** — Add the bot as admin in this channel\n"
                "• 👤 **Your logged-in Telegram account** — Add your account as admin in this channel too\n\n"
                "Forwarding will remain stopped until both are made admin."
            )
        else:
            warn = (
                "\n\n⚠️ **Bot is not admin in this TO channel — Forwarding will NOT work!**\n\n"
                "Please make the **Bot admin** in this channel to start forwarding.\n\n"
                "💡 If you use 🔑 Login Account, your **logged-in Telegram account** "
                "must also be made admin in this TO channel."
            )

    # If public FROM channel and bot is NOT admin AND no userbot, warn user
    if ch_type == "public" and role == "from" and not bot_is_admin and uid not in user_clients:
        warn = (
            "\n\n⚠️ **Bot is not admin in this channel.**\n"
            "Option A: Make bot admin → instant real-time forwarding\n"
            "Option B: Use /login with your Telegram account → no admin needed"
        )
    # Send init message to TO channel so bot caches the entity
    if role == "to" and bot_is_admin:
        try:
            dest = getattr(entity, "username", None) or (int(ch_id) if ch_id.startswith("-") else int("-100" + ch_id))
            await bot.send_message(
                dest,
                "✅ **ChannelAutoPost connected!**\n\n"
                "This channel is now set as a destination (TO) channel.\n"
                "Forwarding will begin as soon as a FROM channel posts.",
                parse_mode="md"
            )
        except Exception as e:
            log.warning(f"Init message failed for TO channel {ch_id}: {e}")
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

async def do_forward(dest, msg, remove_tag: bool, client_to_use=None):
    """Forward a message to dest.  When remove_tag is True the message is
    copied (no 'Forwarded from …' header).  Polls cannot be copied so they
    always fall back to a real forward."""
    c = client_to_use or bot
    if remove_tag and not msg.poll:
        if msg.media:
            await c.send_file(dest, msg.media, caption=msg.text or "", formatting_entities=msg.entities or [])
        else:
            await c.send_message(dest, msg.text or "", formatting_entities=msg.entities or [])
    else:
        await c.forward_messages(dest, msg)


# ─────────────────────────────────────────────────────────────────────────────
#  USERBOT ENGINE
# ─────────────────────────────────────────────────────────────────────────────
async def _userbot_join(user_id: int, identifier, ch_title: str = None, notify: bool = False):
    """Tell the user's client to join a public channel."""
    client = user_clients.get(user_id)
    if not client:
        return
    try:
        from telethon.tl.functions.channels import JoinChannelRequest
        entity = await client.get_entity(identifier)
        await client(JoinChannelRequest(entity))
        log.info(f"Userbot {user_id} joined channel {identifier}")
    except Exception as e:
        log.warning(f"Userbot join failed for {identifier}: {e}")
        if notify:
            name = ch_title or str(identifier)
            try:
                await bot.send_message(
                    user_id,
                    f"⚠️ **Auto-Join Failed**\n\n"
                    f"Could not auto-join **{name}**.\n"
                    f"Please join this channel **manually** with your Telegram account, "
                    f"then forwarding will work automatically.",
                    parse_mode="md"
                )
            except Exception:
                pass

async def _join_public_channels_for_user(user_id: int, client):
    """After login, join all existing public FROM channels for this user."""
    try:
        setups = await setups_col.find({"owner": user_id}).to_list(100)
        for s in setups:
            pub_chs = await channels_col.find({
                "setup_id": s["setup_id"], "role": "from", "ch_type": "public"
            }).to_list(50)
            for ch in pub_chs:
                ident = ch.get("identifier") or ch["ch_id"]
                await _userbot_join(user_id, ident, ch_title=ch.get("title"), notify=True)
                await asyncio.sleep(1)
    except Exception as e:
        log.error(f"_join_public_channels_for_user: {e}")

async def _userbot_keepalive(user_id: int, session_string: str):
    """Keep userbot alive; auto-reconnect on unexpected disconnect."""
    while True:
        try:
            client = user_clients.get(user_id)
            if client and client.is_connected():
                await client.run_until_disconnected()
            # Disconnected — try to reconnect
            log.warning(f"Userbot {user_id} disconnected — reconnecting in 10s")
            user_clients.pop(user_id, None)
            await asyncio.sleep(10)
            ok = await start_userbot(user_id, session_string)
            if ok:
                return  # start_userbot already spawned a new keepalive task
            else:
                break   # session invalid, stop retrying
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.error(f"_userbot_keepalive {user_id}: {e}")
            await asyncio.sleep(15)

async def start_userbot(user_id: int, session_string: str) -> bool:
    """Start a userbot client for a user and register its event handler."""
    try:
        client = TelegramClient(StringSession(session_string), APP_ID, API_HASH)
        await client.connect()
        if not await client.is_user_authorized():
            log.warning(f"Userbot session for {user_id} is no longer valid — removing.")
            await sessions_col.delete_one({"user_id": user_id})
            try:
                await bot.send_message(
                    user_id,
                    "⚠️ **Your Login Session has expired!**\n\n"
                    "Possible reasons:\n"
                    "• You logged out from another device\n"
                    "• Your Telegram session expired\n"
                    "• Your account password was changed\n\n"
                    "🔧 **Action required:**\n"
                    "Please logout and login again —\n"
                    "Main Menu → 🔑 Login Account\n\n"
                    "⚡ Forwarding from public channels will remain stopped until you login again.",
                    parse_mode="md",
                    buttons=[[Button.inline("🔑 Login Now", b"login_start")]]
                )
            except Exception:
                pass
            return False
        user_clients[user_id] = client

        @client.on(events.NewMessage())
        async def _ub_on_msg(event):
            if event.is_private:
                return
            raw_cid = str(event.chat_id)
            short   = raw_cid[4:] if raw_cid.startswith("-100") else raw_cid

            from_chs = await channels_col.find({
                "ch_id": {"$in": [raw_cid, short]},
                "role": "from",
            }).to_list(10)

            for from_ch in from_chs:
                # Skip if bot is admin in this FROM channel — bot handler will process it
                if from_ch.get("bot_is_admin"):
                    continue
                setup_id = from_ch["setup_id"]
                s = await setups_col.find_one({
                    "setup_id": setup_id, "owner": user_id, "active": True
                })
                if not s:
                    continue
                if not await is_premium(user_id):
                    continue
                if await already_processed(event.message.id, raw_cid):
                    continue
                to_chs = await channels_col.find({
                    "setup_id": setup_id, "role": "to"
                }).to_list(20)
                if not to_chs:
                    continue
                from_list = await channels_col.find({
                    "setup_id": setup_id, "role": "from"
                }).to_list(20)
                from_ids = [c["ch_id"] for c in from_list]
                try:
                    idx = from_ids.index(from_ch["ch_id"])
                except ValueError:
                    idx = 0
                filters = s.get("filters", DEFAULT_FILTERS)
                remove_tag = filters.get("remove_forward_tag", False)

                if not msg_passes_filters(event.message, filters):
                    continue
                if len(from_list) >= len(to_chs):
                    targets = [to_chs[min(idx, len(to_chs) - 1)]]
                else:
                    targets = to_chs
                q = get_setup_queue(setup_id)
                for target in targets:
                    ch_id_str = target["ch_id"]
                    if ch_id_str.lstrip("-").isdigit():
                        cid = int(ch_id_str)
                        if cid > 0:
                            cid = int("-100" + ch_id_str)
                        dest = cid
                    else:
                        dest = target["identifier"]
                    await q.put({
                        "dest":          dest,
                        "msg":           event.message,
                        "remove_tag":    remove_tag,
                        "client_to_use": client,
                        "owner_id":      user_id,
                        "target":        target,
                        "setup_id":      setup_id,
                        "from_ch_id":    from_ch["ch_id"],
                    })
                await mark_processed(event.message.id, raw_cid)
        asyncio.create_task(_userbot_keepalive(user_id, session_string))
        log.info(f"Userbot started for user {user_id}")
        return True
    except Exception as e:
        log.error(f"start_userbot failed for {user_id}: {e}")
        user_clients.pop(user_id, None)
        return False

async def load_all_userbots():
    """Called at startup — restore all saved sessions."""
    docs = await sessions_col.find({}).to_list(1000)
    for doc in docs:
        uid = doc["user_id"]
        ok  = await start_userbot(uid, doc["session_string"])
        if ok:
            log.info(f"Restored userbot session for user {uid}")
        await asyncio.sleep(0.5)

async def task_check_channels():
    """Hourly health-check: if a FROM public channel is inaccessible
    3 consecutive times (via userbot entity lookup), auto-remove it."""
    await asyncio.sleep(3600)
    while True:
        try:
            pub_chs = await channels_col.find({
                "role": "from", "ch_type": "public"
            }).to_list(500)
            for ch in pub_chs:
                setup_id = ch["setup_id"]
                s = await setups_col.find_one({"setup_id": setup_id})
                if not s:
                    continue
                owner  = s["owner"]
                ident  = ch.get("identifier") or ch["ch_id"]
                client = user_clients.get(owner) or bot
                try:
                    await client.get_entity(ident)
                    # Accessible — reset fail count
                    if ch.get("fail_count", 0) > 0:
                        await channels_col.update_one(
                            {"ch_id": ch["ch_id"], "setup_id": setup_id},
                            {"$set": {"fail_count": 0}}
                        )
                except (ChannelPrivateError, UsernameNotOccupiedError,
                        UsernameInvalidError):
                    fail = ch.get("fail_count", 0) + 1
                    log.warning(f"Channel {ident} health-check fail {fail}/3")
                    await channels_col.update_one(
                        {"ch_id": ch["ch_id"], "setup_id": setup_id},
                        {"$set": {"fail_count": fail}}
                    )
                    if fail >= 3:
                        await channels_col.delete_one({
                            "ch_id": ch["ch_id"], "setup_id": setup_id
                        })
                        try:
                            await bot.send_message(
                                owner,
                                f"⚠️ **Channel Auto-Removed**\n\n"
                                f"**{ch.get('title', ident)}** became inaccessible "
                                f"(checked 3 times) and was removed from setup "
                                f"**{s.get('name')}**.",
                                parse_mode="md",
                                buttons=[[Button.inline("📋 My Setups", b"setups_list")]]
                            )
                        except Exception:
                            pass
                except Exception:
                    pass  # Transient errors do not affect fail count
                await asyncio.sleep(0.3)
        except Exception as e:
            log.error(f"task_check_channels: {e}")
        await asyncio.sleep(3600)

# Real-time event handler — handles BOTH public and private FROM channels.
# For public channels the bot MUST be admin in the FROM channel so that
# Telegram delivers NewMessage events to it.
# For private channels the bot must also be admin.
@bot.on(events.NewMessage())
async def on_new_msg(event):
    if event.is_private:
        return
    raw_cid = str(event.chat_id)
    # Fix: use slicing instead of lstrip("100") which strips individual chars
    short   = raw_cid[4:] if raw_cid.startswith("-100") else raw_cid

    # Match against BOTH public and private FROM channels
    from_chs = await channels_col.find({
        "ch_id": {"$in": [raw_cid, short]},
        "role": "from",
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
        filters = s.get("filters", DEFAULT_FILTERS)
        remove_tag = filters.get("remove_forward_tag", False)

        if msg_passes_filters(event.message, filters):
            if len(from_list) >= len(to_chs):
                targets = [to_chs[min(idx, len(to_chs) - 1)]]
            else:
                targets = to_chs
            q = get_setup_queue(setup_id)
            for target in targets:
                ch_id_str = target["ch_id"]
                if ch_id_str.lstrip("-").isdigit():
                    cid = int(ch_id_str)
                    if cid > 0:
                        cid = int("-100" + ch_id_str)
                    dest = cid
                else:
                    dest = target["identifier"]
                await q.put({
                    "dest":          dest,
                    "msg":           event.message,
                    "remove_tag":    remove_tag,
                    "client_to_use": None,
                    "owner_id":      s["owner"],
                    "target":        target,
                    "setup_id":      setup_id,
                    "from_ch_id":    from_ch["ch_id"],
                })
            await mark_processed(event.message.id, raw_cid)

# ─────────────────────────────────────────────────────────────────────────────
#  BACKGROUND TASKS
# ─────────────────────────────────────────────────────────────────────────────
async def task_poll_public():
    # GetHistoryRequest (bot.get_messages) is permanently banned for bot accounts
    # by Telegram — it raises BotMethodInvalidError every time regardless of
    # admin status.  Public channel forwarding is handled in real-time by the
    # on_new_msg event handler instead (bot must be admin in the FROM channel).
    # This stub keeps the task alive so the start-up code does not need changes.
    log.info("task_poll_public: polling disabled — using real-time events instead.")

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

async def _send_restart_notifications():
    """On restart, silently warm up entity cache for active TO channels (no spam)."""
    await asyncio.sleep(3)
    try:
        active_setups = await setups_col.find({"active": True}).to_list(200)
        notified = set()
        for s in active_setups:
            to_chs = await channels_col.find(
                {"setup_id": s["setup_id"], "role": "to"}
            ).to_list(20)
            for ch in to_chs:
                if ch["ch_id"] in notified:
                    continue
                try:
                    cid = ch["ch_id"]
                    dest = int(cid) if cid.startswith("-") else int("-100" + cid)
                    await bot.get_entity(dest)  # warm up entity cache silently
                    notified.add(ch["ch_id"])
                    await asyncio.sleep(0.5)
                except Exception as e:
                    log.warning(f"Cache warmup failed for {ch.get('identifier', ch['ch_id'])}: {e}")
    except Exception as e:
        log.error(f"_send_restart_notifications: {e}")

# ─────────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────────
async def main():
    await bot.start(bot_token=BOT_TOKEN)
    log.info("ChannelAutoPost Bot started!")
    await ensure_indexes()
    asyncio.create_task(_send_restart_notifications())
    await load_all_userbots()
    asyncio.create_task(task_poll_public())
    asyncio.create_task(task_monitor_pending())
    asyncio.create_task(task_premium_expiry())
    asyncio.create_task(task_check_channels())
    await bot.run_until_disconnected()

if __name__ == "__main__":
    bot.loop.run_until_complete(main())
