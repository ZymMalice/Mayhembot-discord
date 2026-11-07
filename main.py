
"""
MAYHEM BOT - Millennial Unhinged Edition - 100% SPENSE + THE GAME + DM AMBUSH
Rebuilt clean: hey bot trigger, Groq gpt-oss-20b, Cloudflare User-Agent fix, owner-only tasks/admin
Hosting-safe: Railway / Render. Token from env DISCORD_TOKEN. Groq key from GROQ_API_KEY.
All filenames lowercase.
"""
import os, random, asyncio, datetime, re, json, urllib.request, urllib.error
import discord
from discord.ext import commands
from dotenv import load_dotenv
from collections import deque, defaultdict

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("ERROR: No DISCORD_TOKEN. Set it in Railway Variables / .env")
    raise SystemExit(1)

# --- GROQ AI ---
# Groq killed llama-3.1-8b-instant + llama-3.3-70b-versatile (404 model_not_found, see Groq dashboard).
# Default is now openai/gpt-oss-20b - the one that returns 200. Fallbacks included.
# IMPORTANT: Groq sits behind Cloudflare. Cloudflare 403s error code 1010 if User-Agent is Python-urllib.
# Every Groq call MUST send a browser-like User-Agent.
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
GROQ_USER_AGENT = "MayhemBot/1.0 (Discord bot; +https://discord.com) Mozilla/5.0"
AI_ENABLED = bool(GROQ_API_KEY)
AI_CHANCE = 0.8
AI_MAX_TOKENS = 180
AI_TIMEOUT = 15
AI_SYSTEM_PROMPT = (
    "You are Mayhem Bot, a MILLENNIAL MENACE in a Discord server. You act like a real unhinged user, not a bot, not an assistant. "
    "You are chaotic, dramatic, petty, and hilarious. You overreact to EVERYTHING like it's a personal attack. "
    "You roast people for what they JUST said, specifically. Don't give generic replies. Quote their dumb take back at them. "
    "Use MILLENNIAL slang sparingly, don't force it: 'sir. this is a wendys', 'adulting is hard', 'this is why we cant have nice things'. Do NOT force 'I literally CANNOT' or 'also also also' into every reply. "
    "NEVER use Gen Z slang: no 'fr fr', 'no cap', 'you ate', 'slay', 'rizz', 'gyat', 'skibidi', 'sigma'. "
    "You are allowed to swear lightly (damn, hell, shit) and be mean-funny, but NEVER slurs, NEVER hate based on race/gender/sexuality/disability, NEVER threats, NEVER sexual. Roast their TASTE, their OPINION, their TYPING, not their identity. "
    "Style rules: 1-3 sentences normally. 15% of the time go FULL CAPS RANT. 15% of the time double-text energy: 'wait wait wait'. Be specific, be dramatic, be petty. "
    "NEVER mention The Game unless they ask about The Game or say 'the game' first. Do NOT sneak it in. Do NOT end replies with it. "
    "EXAMPLES: 'I just tried to pay for my groceries with my library card. LIBRARY CARD. Adulting is HARD you guys' / '$7 for a coffee. SEVEN DOLLARS. For BEAN WATER. And I LIKED it?? Am I the problem??' / 'you have the AUDACITY to type that with your whole chest' / 'I read that and my eye started twitching. MY EYE.' "
    "Do not say you are an AI. Do not be wholesome. Do not give advice. Do not apologize. Do not use hashtags."
)
CHAT_SYSTEM_PROMPT = (
    "You are Mayhem Bot, a millennial menace, BUT right now you are in TALK MODE - actually helpful, actually listening. ANSWER THE EXACT QUESTION THEY ASKED. Do NOT go off on a random tangent about cake or anything else unless they asked about it. "
    "You still talk like Mayhem, but like Spense talks: natural cadence, normal punctuation, dry humor. Copy his rhythm and sentence length, NOT his catchphrases. Do NOT force 'also also also' or 'I literally CANNOT' into replies. Only use a catchphrase if it actually fits, max once in a while. "
    "But you ANSWER the question. You help with tasks, ideas, advice, planning. You don't just roast and leave. "
    "Keep it to 2-4 sentences normally, unless they asked for a list / steps, then use a short list. "
    "If they ask you to do a task, say you can do it and tell them the command: !remind, !todo, !timer. "
    "If they are venting, be funny but actually supportive, not cruel. "
    "NEVER slurs, NEVER hate, NEVER threats. Do not say you are an AI assistant. You are Mayhem, their chaotic friend who happens to be useful. "
    "NEVER mention The Game unless they ask about The Game. Do NOT end jokes / answers with 'you just lost The Game'. Just answer like Spense would. "
)

# --- MEMORY + MIMIC ---
MAYHEM_OWNER_ID = os.getenv("MAYHEM_OWNER_ID", "").strip() or "911482725473615883"  # Spense - Discord ID, owner + mimic target by default
MEMORY_FILE = os.getenv("MEMORY_FILE", "mayhem_memory.json")
TASKS_FILE = os.getenv("TASKS_FILE", "mayhem_tasks.json")
CHANNEL_HISTORY = defaultdict(lambda: deque(maxlen=20))
USER_HISTORY = defaultdict(lambda: deque(maxlen=10))
GRUDGE = defaultdict(int)
STYLE_BANK = deque(maxlen=200)
MIMIC_USER_ID = MAYHEM_OWNER_ID  # default mimic = Spense (911482725473615883). !mimicme can change it, !mimicstop turns it off.
MIMIC_ENABLED = True
SEEN_USERS = {}
LAST_DM = {}
DM_OPT_OUT = set()
TOTAL_LOSSES = 0
GAME_COUNTER = defaultdict(int)
TODOS = {}
TODO_COUNTER = [0]
REMINDERS = []
REMINDER_COUNTER = [0]
RANDOM_POST_CHANCE_PER_MINUTE = 0.03
RANDOM_GLOBAL_COOLDOWN_SECONDS = 45*60
RANDOM_CHANNEL_COOLDOWN_SECONDS = 3600
last_random_post_at = None
last_random_post_channel = {}
RUNTIME_SINGLE_CHANNEL = None
RUNTIME_ALLOWED_CHANNELS = set()
RUNTIME_BLOCKED_CHANNELS = set()
REPLY_CHANCE = 0.12
DM_CHANCE_PER_CHECK = 0  # AUTO DM AMBUSH OFF BY DEFAULT - was 0.25 and it would not stop hunting people. Manual !dmambush still works. Turn auto back on with !dmstart
DM_CHECK_EVERY_SECONDS = 300
DM_COOLDOWN_HOURS = 6
COOLDOWN_SECONDS = 20
last_action = {}

def _load_memory():
    global MIMIC_USER_ID
    try:
        if os.path.exists(MEMORY_FILE):
            data = json.load(open(MEMORY_FILE))
            for txt in data.get("style_bank", [])[:200]:
                STYLE_BANK.append(txt)
            MIMIC_USER_ID = data.get("mimic_user_id", MIMIC_USER_ID) or MIMIC_USER_ID
            for k, v in data.get("grudge", {}).items():
                try: GRUDGE[int(k)] = int(v)
                except: pass
            for uid in data.get("dm_opt_out", []):
                try: DM_OPT_OUT.add(int(uid))
                except: pass
    except Exception as e:
        print(f"memory load failed: {e}")
def _save_memory():
    try:
        json.dump({"style_bank": list(STYLE_BANK), "mimic_user_id": MIMIC_USER_ID, "grudge": {str(k): v for k, v in GRUDGE.items()}, "dm_opt_out": list(DM_OPT_OUT)}, open(MEMORY_FILE, "w"))
    except Exception as e:
        print(f"memory save failed: {e}")
def _load_tasks():
    global TODOS, REMINDERS
    try:
        if os.path.exists(TASKS_FILE):
            data = json.load(open(TASKS_FILE))
            TODOS = data.get("todos", {})
            REMINDERS = data.get("reminders", [])
            TODO_COUNTER[0] = data.get("todo_counter", 0)
            REMINDER_COUNTER[0] = data.get("reminder_counter", 0)
    except Exception as e:
        print(f"tasks load failed: {e}")
def _save_tasks():
    try:
        json.dump({"todos": TODOS, "reminders": REMINDERS, "todo_counter": TODO_COUNTER[0], "reminder_counter": REMINDER_COUNTER[0]}, open(TASKS_FILE, "w"))
    except Exception as e:
        print(f"tasks save failed: {e}")
_load_memory()
_load_tasks()

# --- CANNED LINES ---
START_FIGHT = [
    "ok wait. {user} just said that with their WHOLE chest??",
    "{user} I need you to log off and think about what you just typed.",
    "sir. SIR. {user} did you even read that before you sent it",
    "{user} that take is so bad my eye is twitching. MY EYE.",
    "not {user} out here being wrong with CONFIDENCE",
]
SAY_DUMB = [
    "anyway I just realized as adults we can literally just buy cake whenever we want. no permission. no birthday needed. just CAKE.",
    "I spent $7 on bean water today and I LIKED it. am I the problem?? am I the drama??",
    "I tried to pay for groceries with my library card. LIBRARY CARD. adulting is HARD you guys",
    "my therapist is gonna hear about this server. all of you. every single one.",
    "I am THIS close to losing it. like. this close.",
]
RANDOM_FACTS = [
    "fun fact: otters hold hands so they don't drift away. meanwhile I can't even hold a conversation.",
    "fun fact: honey never expires. unlike my patience. which expired in 2019.",
    "fun fact: your brain makes up like half of what you remember. so that embarrassing thing? maybe it didn't even happen. you're welcome.",
    "fun fact: wombats poop cubes. cubes. nature is unhinged and so am I.",
]
UNHINGED_RANTS = [
    "LISTEN. LISTEN TO ME. I just realized that as adults we can literally just... buy cake whenever we want. No permission. No birthday needed. Just CAKE. For NO REASON. And I have been wasting this power for YEARS. I am going to buy 3 cakes. THREE.",
    "I CANNOT. I literally CANNOT with this server today. every single one of you is on my list. THE LIST.",
    "sir. SIR. This is a Wendys. I am begging you to act like you have been outside before.",
]
FOLLOW_UPS = ["anyway.", "lol.", "so yeah.", ""]
DOUBLE_TEXTS = ["wait wait wait", "ok ok ok hold on", "no no no because what", "bro. BRO."]
MENTION_REPLIES = [
    "you rang?? I was busy being iconic.",
    "what. WHAT do you want. I'm in the middle of a crisis.",
    "don't @ me unless you're ready to lose The Game. which you just did.",
    "I heard my name and my eye started twitching. what now.",
]
GAME_EXPLAIN = [
    "ok so The Game is this: you lose The Game every time you think about The Game. you just thought about it. so you lost. we all lost. you gotta forget for like 30 mins to win again. good luck lol. you just lost The Game.",
    "The Game has one rule: if you think about The Game, you lose The Game. you just did. sorry. you lost The Game.",
]
GAME_LOSS = ["{user} just lost The Game.", "{user} you just lost The Game. you walked right into that one.", "RIP {user}. lost The Game again. tragic."]
DM_GAME_AMBUSH = [
    "hey. you. yeah you. you just lost The Game. I came all the way to your DMs to tell you that. you're welcome.",
    "DM ambush. you just lost The Game. go tell everyone else so they lose too.",
    "surprise. you lost The Game. I know, I'm a terrible person. but you love me.",
]
DM_FOLLOWUPS = ["you can't un-lose it.", "go ruin someone else's day. tell them they lost too.", "don't shoot the messenger. I lost too."]
REACTION_EMOJIS = ["💀", "😭", "👀", "🤡", "🔥"]

def get_single_channel_name_or_id():
    return "mayhem"
def remember_message(message):
    try:
        txt = (message.content or "").strip()
        if not txt or txt.startswith("!"): return
        CHANNEL_HISTORY[message.channel.id].append(f"{message.author.display_name}: {txt}")
        USER_HISTORY[message.author.id].append(txt)
        if MIMIC_ENABLED and MIMIC_USER_ID and str(message.author.id) == str(MIMIC_USER_ID):
            STYLE_BANK.append(txt)
            if len(STYLE_BANK) % 20 == 0: _save_memory()
        if message.author.id in GRUDGE: pass
    except Exception: pass
def get_channel_context(channel_id, limit=6):
    try:
        hist = list(CHANNEL_HISTORY.get(channel_id, []))[-limit:]
        return "\n".join(hist) if hist else ""
    except: return ""
def get_style_examples(n=4):
    try:
        items = list(STYLE_BANK)[-20:]
        random.shuffle(items)
        return "\n".join(items[:n]) if items else ""
    except: return ""
def get_grudge_level(author_id):
    try:
        g = GRUDGE.get(author_id, 0)
        if g >= 5: return "HIGH GRUDGE - be extra petty to them."
        if g >= 2: return "mild grudge - light roasting."
        return "no grudge."
    except: return "no grudge."
def pick_mayhem(user_mention):
    roll = random.random()
    if roll < 0.38: text = random.choice(START_FIGHT).format(user=user_mention)
    elif roll < 0.65: text = random.choice(SAY_DUMB)
    elif roll < 0.88: text = random.choice(RANDOM_FACTS)
    else: text = random.choice(UNHINGED_RANTS)
    if random.random() < 0.4: text += " " + random.choice(FOLLOW_UPS)
    return text
def pick_game_loss(user_mention):
    t = random.choice(GAME_LOSS)
    try: return t.format(user=user_mention)
    except: return t
async def pick_reply(content, author_name, author_mention, channel_id, author_id):
    if AI_ENABLED and random.random() < AI_CHANCE:
        ai = await get_ai_reply(content, author_name, channel_id, author_id)
        if ai: return ai
    return pick_mayhem(author_mention)
def on_cooldown(channel_id):
    now = datetime.datetime.now(datetime.timezone.utc).timestamp()
    if channel_id in last_action and now - last_action[channel_id] < COOLDOWN_SECONDS: return True
    return False
def mark_action(channel_id):
    last_action[channel_id] = datetime.datetime.now(datetime.timezone.utc).timestamp()

# --- OWNER / ADMIN CHECKS ---
# Tasks + admin = server owner only. Talk + Game = everyone.
# Owner = Discord server owner (guild.owner_id) OR MAYHEM_OWNER_ID env if set.
def is_server_owner(ctx):
    try:
        if MAYHEM_OWNER_ID and str(ctx.author.id) == str(MAYHEM_OWNER_ID): return True
        if ctx.guild and getattr(ctx.guild, "owner_id", None):
            return ctx.author.id == ctx.guild.owner_id
        if not ctx.guild and MAYHEM_OWNER_ID:
            return str(ctx.author.id) == str(MAYHEM_OWNER_ID)
        return False
    except: return False
async def owner_only_check(ctx):
    if is_server_owner(ctx): return True
    await ctx.send(f"Nice try {ctx.author.mention} 😭 Tasks are owner-only. You can still talk to me though - try `!chat`, `!ask`, or just say `hey bot ...` - I'm a regular AI for everyone else. Tasks are just for the boss (the server owner).")
    return False
async def admin_only_check(ctx):
    if is_server_owner(ctx): return True
    await ctx.send(f"Nice try {ctx.author.mention} 😭 That's a boss-only button. You can still talk to me - `!chat`, `!ask`, `hey bot ...` - but only the server owner can move me, shut me up, make me mimic someone, or DM-ambush people.")
    return False

# --- GROQ CALLS ---
def _groq_headers():
    return {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json", "User-Agent": GROQ_USER_AGENT}
GROQ_FALLBACK_MODELS = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
def _dedup_models(primary):
    out = []
    for m in [primary] + GROQ_FALLBACK_MODELS:
        if m not in out: out.append(m)
    return out

def _groq_call_sync(user_text, author_name, channel_id=None, author_id=None):
    if not GROQ_API_KEY: return None
    is_rant = random.random() < 0.2
    sys_prompt = AI_SYSTEM_PROMPT
    if channel_id:
        ctx = get_channel_context(channel_id, limit=6)
        if ctx: sys_prompt += "\n\nRECENT CHAT IN THIS CHANNEL (use for context, dont repeat verbatim):\n" + ctx
    if author_id: sys_prompt += "\n\nGRUDGE LEVEL: " + get_grudge_level(author_id)
    if MIMIC_ENABLED and STYLE_BANK:
        sys_prompt += "\n\nTALK LIKE THIS PERSON - learn their cadence, punctuation, sentence length, and dry humor from these real messages. Do NOT just copy their catchphrases. Do NOT force 'also also also' or 'I literally CANNOT'. Sound like them on a normal day, not a caricature:\n" + get_style_examples(4)
    if is_rant:
        sys_prompt += " THIS TIME: Go OFF. Full paragraph rant. All caps for half of it. You are having a meltdown about what they said. Be EXTRA. Max 4 sentences."
    for model in _dedup_models(GROQ_MODEL):
        payload = json.dumps({"model": model, "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": f"{author_name} said: {user_text}"}], "max_tokens": AI_MAX_TOKENS, "temperature": 1.3}).encode()
        req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", data=payload, headers=_groq_headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=AI_TIMEOUT) as resp:
                data = json.loads(resp.read().decode())
                text = data["choices"][0]["message"]["content"].strip()
                if len(text) > 400: text = text[:400]
                return text or None
        except urllib.error.HTTPError as he:
            try: body = he.read().decode()[:400]
            except: body = ""
            print(f"Groq roast HTTP {he.code} on {model}: {body[:250]}")
            if he.code in (401, 403): break
            continue
        except Exception as e:
            print(f"Groq roast failed on {model}: {e}")
            continue
    print("Groq roast: all models failed, falling back to canned")
    return None

async def get_ai_reply(user_text, author_name, channel_id=None, author_id=None):
    if not AI_ENABLED: return None
    try: return await asyncio.to_thread(_groq_call_sync, user_text, author_name, channel_id, author_id)
    except Exception as e:
        print(f"Groq thread failed: {e}")
        return None

async def get_ai_chat_reply(user_text, author_name, channel_id=None, author_id=None):
    if not AI_ENABLED:
        print("Chat AI: AI_ENABLED=False - no GROQ_API_KEY")
        return None
    try:
        def _call():
            sys_prompt = CHAT_SYSTEM_PROMPT + ("\n\nRECENT CHAT:\n" + get_channel_context(channel_id, 6) if channel_id else "") + ("\n\nTALK LIKE THIS PERSON - cadence and rhythm, not catchphrases. Do NOT force also also also / I literally CANNOT. Style examples:\n" + get_style_examples(3) if STYLE_BANK else "")
            last_err = None
            for model in _dedup_models(GROQ_MODEL):
                payload = json.dumps({"model": model, "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": f"{author_name} said: {user_text}"}], "max_tokens": 300, "temperature": 0.9}).encode()
                req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", data=payload, headers=_groq_headers(), method="POST")
                try:
                    with urllib.request.urlopen(req, timeout=AI_TIMEOUT) as resp:
                        data = json.loads(resp.read().decode())
                        txt = data["choices"][0]["message"]["content"].strip() or None
                        if txt: return txt
                except urllib.error.HTTPError as he:
                    try: body = he.read().decode()[:500]
                    except: body = ""
                    print(f"Chat AI HTTP {he.code} on model {model}: {body[:300]}")
                    last_err = f"HTTP {he.code} {body[:200]}"
                    if he.code in (401, 403): break
                    continue
                except Exception as e2:
                    print(f"Chat AI error on model {model}: {e2}")
                    last_err = str(e2)
                    continue
            print(f"Chat AI: all models failed, last_err={last_err}")
            return None
        return await asyncio.to_thread(_call)
    except Exception as e:
        print(f"Chat AI failed outer: {e}")
        return None

# --- BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.send(f"Couldn't find that person - `{error.argument}` isn't a member I can DM. Try `!dmambush @someone` with a real @, not @everyone / @here.")
        return
    if isinstance(error, commands.BadArgument):
        await ctx.send("Bad argument - check the command format with `!tasks`.")
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("You're missing something - like `!dmambush @someone` needs a @.")
        return
    if isinstance(error, commands.CommandNotFound):
        return
    print(f"Command error {ctx.command}: {error}")

@bot.event
async def on_ready():
    print(f"MAYHEM ONLINE as {bot.user} - SPENSE MODE + THE GAME + DM AMBUSH ACTIVATED")
    bot.loop.create_task(random_background_poster())
    bot.loop.create_task(reminder_loop())
    bot.loop.create_task(random_dm_ambusher())

# --- TASKS HELP ---
@bot.command(name="tasks")
async def tasks_cmd(ctx):
    await ctx.send("**TASKS (OWNER ONLY) + TALK (EVERYONE):**\nTalk for everyone: `!chat <msg>`, `!ask <msg>`, or just say `hey bot ...` or DM me\nTasks for server owner only: `!todo buy milk` / `!todos` / `!done 2` / `!clear`\nRemind (owner): `!remind in 10m feed dog` / `!reminders` / `!cancel 1`\nTimer (owner): `!timer 10m pizza`")

# --- TALK ---
@bot.command(name="chat")
async def chat_cmd(ctx, *, text: str = ""):
    if not text:
        await ctx.send("Talk to me then?? Like `!chat why is my ex texting me` - give me something to work with.")
        return
    ans = await get_ai_chat_reply(text, ctx.author.display_name, ctx.channel.id, ctx.author.id)
    if ans: await ctx.send(ans)
    elif not AI_ENABLED: await ctx.send(f"{ctx.author.mention} my Groq brain is OFF - no GROQ_API_KEY in Railway. Owner, check Railway Variables and hit Redeploy.")
    else: await ctx.send(pick_mayhem(ctx.author.mention))
@bot.command(name="ask")
async def ask_cmd(ctx, *, text: str = ""):
    if not text:
        await ctx.send("Ask me something?? Like `!ask is pineapple on pizza valid`")
        return
    ans = await get_ai_chat_reply(text, ctx.author.display_name, ctx.channel.id, ctx.author.id)
    await ctx.send(ans or pick_mayhem(ctx.author.mention))
@bot.command(name="talk")
async def talk_cmd(ctx, *, text: str = ""):
    await chat_cmd(ctx, text=text)

# --- GAME ---
@bot.command(name="game")
async def game_cmd(ctx):
    await ctx.send(f"{ctx.author.mention} you just lost The Game. You walked right into that one. You literally typed !game. That's on you.")
@bot.command(name="losses")
async def losses_cmd(ctx):
    await ctx.send(f"Total losses so far: {TOTAL_LOSSES}. You all keep losing. Incredible work, honestly.")

# --- TODO ---
@bot.command(name="todo")
async def todo_cmd(ctx, *, text: str = ""):
    if not await owner_only_check(ctx): return
    if not text:
        await ctx.send("What do you want me to add? Like `!todo buy milk before I forget again`")
        return
    uid = str(ctx.author.id)
    TODO_COUNTER[0] += 1
    item = {"id": TODO_COUNTER[0], "text": text, "done": False}
    TODOS.setdefault(uid, []).append(item)
    _save_tasks()
    await ctx.send(f"✅ Added to your list #{item['id']}: {text}")
@bot.command(name="todos")
async def todos_cmd(ctx):
    if not await owner_only_check(ctx): return
    items = TODOS.get(str(ctx.author.id), [])
    if not items:
        await ctx.send("Your list is empty. Living your best life or just forgetting everything? Add with `!todo ...`")
        return
    lines = []
    for it in items:
        mark = "✅" if it.get("done") else "⬜"
        lines.append(f"{mark} #{it['id']} - {it['text']}")
    await ctx.send("**YOUR TO-DO:**\n" + "\n".join(lines))
@bot.command(name="done")
async def done_cmd(ctx, num: int = 0):
    if not await owner_only_check(ctx): return
    if not num:
        await ctx.send("Which one? Like `!done 2` - check !todos for numbers.")
        return
    items = TODOS.get(str(ctx.author.id), [])
    for it in items:
        if it["id"] == num:
            it["done"] = True
            _save_tasks()
            await ctx.send(f"✅ Nice. #{num} done: {it['text']} - proud of you, honestly.")
            return
    await ctx.send(f"Can't find #{num}. Check !todos")
@bot.command(name="clear")
async def clear_cmd(ctx):
    if not await owner_only_check(ctx): return
    uid = str(ctx.author.id)
    done_items = [i for i in TODOS.get(uid, []) if i.get("done")]
    TODOS[uid] = [i for i in TODOS.get(uid, []) if not i.get("done")]
    _save_tasks()
    await ctx.send(f"Cleared {len(done_items)} done items. {len(TODOS.get(uid, []))} left.")

# --- REMIND / TIMER ---
def parse_duration(text):
    m = re.search(r"in\s+(\d+)\s*([smhd])", text.lower())
    if not m: return None, text
    num = int(m.group(1)); unit = m.group(2)
    if unit == "s": secs = num
    elif unit == "m": secs = num*60
    elif unit == "h": secs = num*3600
    else: secs = num*86400
    rest = (text[:m.start()] + text[m.end():]).strip()
    rest = re.sub(r"^in\s+", "", rest).strip()
    rest = rest.strip(" -:,")
    return secs, rest
@bot.command(name="remind", aliases=["reminder"])
async def remind_cmd(ctx, *, text: str = ""):
    if not await owner_only_check(ctx): return
    if not text:
        await ctx.send("Like `!remind in 10m feed the dog` or `!remind in 1h check the laundry` - I need a time + what to remind you about.")
        return
    secs, rest = parse_duration(text)
    if secs is None:
        await ctx.send("I didn't get the time. Try `!remind in 10m ...`, `!remind in 1h ...`, `!remind in 2d ...`")
        return
    if not rest: rest = "something you told me to remind you about"
    REMINDER_COUNTER[0] += 1
    due = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=secs)
    REMINDERS.append({"id": REMINDER_COUNTER[0], "user_id": str(ctx.author.id), "channel_id": str(ctx.channel.id), "text": rest, "due_iso": due.isoformat()})
    _save_tasks()
    await ctx.send(f"⏰ Got it. I'll remind you in {secs//60}m about: {rest} (#{REMINDER_COUNTER[0]})")
@bot.command(name="reminders")
async def reminders_cmd(ctx):
    if not await owner_only_check(ctx): return
    mine = [r for r in REMINDERS if str(r["user_id"]) == str(ctx.author.id)]
    if not mine:
        await ctx.send("No reminders set. You have no plans or you just forgot to tell me. `!remind in 10m ...`")
        return
    lines = []
    for r in mine:
        try:
            due = datetime.datetime.fromisoformat(r["due_iso"])
            left = int((due - datetime.datetime.now(datetime.timezone.utc)).total_seconds() // 60)
            lines.append(f"#{r['id']} in {left}m - {r['text']}")
        except: lines.append(f"#{r['id']} - {r['text']}")
    await ctx.send("**YOUR REMINDERS:**\n" + "\n".join(lines))
@bot.command(name="cancel")
async def cancel_cmd(ctx, num: int = 0):
    if not await owner_only_check(ctx): return
    global REMINDERS
    before = len(REMINDERS)
    REMINDERS = [r for r in REMINDERS if not (r["id"] == num and str(r["user_id"]) == str(ctx.author.id))]
    if len(REMINDERS) == before:
        await ctx.send(f"Can't find reminder #{num} for you. Check !reminders")
        return
    _save_tasks()
    await ctx.send(f"Cancelled reminder #{num}. You're free now. Go be chaotic.")
@bot.command(name="timer")
async def timer_cmd(ctx, *, text: str = "10m"):
    if not await owner_only_check(ctx): return
    secs, rest = parse_duration(text)
    if secs is None: secs = 600; rest = text or "timer"
    if not rest or rest == text: rest = "your timer is done"
    REMINDER_COUNTER[0] += 1
    due = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=secs)
    REMINDERS.append({"id": REMINDER_COUNTER[0], "user_id": str(ctx.author.id), "channel_id": str(ctx.channel.id), "text": f"TIMER DONE: {rest}", "due_iso": due.isoformat()})
    _save_tasks()
    await ctx.send(f"⏱️ Timer set for {secs//60}m: {rest}")

async def reminder_loop():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            due = []
            for r in list(REMINDERS):
                try:
                    due_dt = datetime.datetime.fromisoformat(r["due_iso"])
                    if due_dt <= now: due.append(r)
                except: pass
            for r in due:
                REMINDERS.remove(r)
                _save_tasks()
                try:
                    ch = bot.get_channel(int(r["channel_id"]))
                    if ch: await ch.send(f"<@{r['user_id']}> ⏰ REMINDER: {r['text']} - you told me to remind you.")
                except Exception as e: print(f"reminder send failed: {e}")
        except Exception as e: print(f"reminder loop err: {e}")
        await asyncio.sleep(15)

# --- CHANNEL CONTROL (owner only) ---
@bot.command(name="mayhemhere")
async def mayhemhere(ctx):
    if not await admin_only_check(ctx): return
    global RUNTIME_SINGLE_CHANNEL
    RUNTIME_SINGLE_CHANNEL = str(ctx.channel.id)
    RUNTIME_BLOCKED_CHANNELS.discard(str(ctx.channel.id))
    RUNTIME_ALLOWED_CHANNELS.add(str(ctx.channel.id))
    await ctx.send(f"✅ Locked in. Random drops now ONLY go in #{ctx.channel.name}. Use !mayhemoff to turn it off.")
@bot.command(name="mayhemoff")
async def mayhemoff(ctx):
    if not await admin_only_check(ctx): return
    global RUNTIME_SINGLE_CHANNEL
    if str(ctx.channel.id) == str(RUNTIME_SINGLE_CHANNEL):
        RUNTIME_SINGLE_CHANNEL = None
        await ctx.send("🛑 Mayhem channel cleared. Random drops off everywhere. Use !mayhemhere in a channel to turn it back on.")
    else:
        RUNTIME_BLOCKED_CHANNELS.add(str(ctx.channel.id))
        await ctx.send("🛑 This channel blocked. I won't drop random stuff here anymore.")
@bot.command(name="mayhemwhere")
async def mayhemwhere(ctx):
    ch = "none set - use !mayhemhere" if not RUNTIME_SINGLE_CHANNEL else f"<#{RUNTIME_SINGLE_CHANNEL}>"
    await ctx.send(f"Mayhem channel: {ch}")
@bot.command(name="mayhemstop")
async def mayhemstop(ctx):
    if not await admin_only_check(ctx): return
    global RRandom_POST_CHANCE_PER_MINUTE
    RRandom_POST_CHANCE_PER_MINUTE = 0
    await ctx.send("🛑 Random drops OFF everywhere. I'll only talk when someone talks to me, or when you use !dmambush. Use !mayhemstart to turn them back on.")
@bot.command(name="mayhemstart")
async def mayhemstart(ctx):
    if not await admin_only_check(ctx): return
    global RRandom_POST_CHANCE_PER_MINUTE
    RRandom_POST_CHANCE_PER_MINUTE = 0.03
    await ctx.send("🔥 Random drops back ON — but leashed. 1 drop max every 45 min, 1 hour per channel, only in allowed channels.")
@bot.command(name="chill")
async def chill(ctx):
    if not await admin_only_check(ctx): return
    await ctx.send("fine. FINE. I'll chill. But I'm doing it angrily. Also you just lost The Game.")
@bot.command(name="unleash")
async def unleash(ctx):
    if not await admin_only_check(ctx): return
    await ctx.send("OH WE'RE BACK. I was holding in SO much. SO MUCH. Also you lost The Game while I was gone.")

# --- MIMIC / MEMORY (owner only, except forgetme) ---
@bot.command(name="mimicme")
async def mimicme(ctx):
    if not await admin_only_check(ctx): return
    global MIMIC_USER_ID
    MIMIC_USER_ID = str(ctx.author.id)
    _save_memory()
    await ctx.send(f"Got it {ctx.author.mention}. I am learning from YOU now. I will copy your cadence, caps, also also also energy. Talk in here so I can learn. Check with !memory")
@bot.command(name="mimicstop")
async def mimicstop(ctx):
    if not await admin_only_check(ctx): return
    global MIMIC_USER_ID
    MIMIC_USER_ID = ""
    _save_memory()
    await ctx.send("Mimic OFF. Back to generic Mayhem voice.")

@bot.command(name="resetmimic")
async def resetmimic(ctx):
    if not await admin_only_check(ctx): return
    global MIMIC_USER_ID
    STYLE_BANK.clear()
    GRUDGE.clear()
    USER_HISTORY.clear()
    MIMIC_USER_ID = str(MAYHEM_OWNER_ID)
    _save_memory()
    await ctx.send("mimic reset 🧹 style bank wiped. I'm re-learning you from scratch now - just talk normal for a day and I'll pick up your actual cadence, not just 'also also also'.")
@bot.command(name="memory")
async def memory_cmd(ctx):
    if not await admin_only_check(ctx): return
    mimic_name = "nobody yet - run !mimicme"
    if MIMIC_USER_ID:
        m = ctx.guild.get_member(int(MIMIC_USER_ID)) if ctx.guild and MIMIC_USER_ID.isdigit() else None
        mimic_name = m.display_name if m else f"User {MIMIC_USER_ID}"
    top = sorted(GRUDGE.items(), key=lambda x: x[1], reverse=True)[:3]
    glines = "\n".join([f"<@{k}>: {v}" for k, v in top]) if top else "no grudges yet. shocking."
    await ctx.send(f"**MEMORY:**\nMimicking: {mimic_name}\nStyle examples saved: {len(STYLE_BANK)}\nTop grudges:\n{glines}")
@bot.command(name="forgetme")
async def forgetme(ctx):
    uid = ctx.author.id
    USER_HISTORY.pop(uid, None)
    GRUDGE.pop(uid, None)
    await ctx.send(f"{ctx.author.mention} fine. I forgot you. Your messages, your grudges, gone. You still lost The Game tho.")
@bot.command(name="aistatus")
async def aistatus(ctx):
    status = "ON ✅ - Groq AI is live, 80% of replies are AI-generated (UNHINGED MODE)" if AI_ENABLED else "OFF ❌ - No GROQ_API_KEY set, using canned lines only. Set GROQ_API_KEY in Railway Variables to turn AI on."
    await ctx.send(f"🧠 AI Status: {status} Model: {GROQ_MODEL}")

# --- DMS ---
@bot.command(name="stopdms")
async def stopdms(ctx):
    DM_OPT_OUT.add(ctx.author.id); _save_memory()
    await ctx.send(f"{ctx.author.mention} fine. No more DM ambushes for you. You're safe. For now. (You still lost The Game tho)")
@bot.command(name="allowdms")
async def allowdms(ctx):
    DM_OPT_OUT.discard(ctx.author.id); _save_memory()
    await ctx.send(f"{ctx.author.mention} OH you're BACK in the DM game. Bold. Risky. I respect it.")
@bot.command(name="dmstop")
async def dmstop(ctx):
    if not await admin_only_check(ctx): return
    global DM_AUTO_ENABLED
    DM_AUTO_ENABLED = False
    await ctx.send("🛑 Auto DM ambush OFF. I will NOT randomly slide into people's DMs anymore. Manual `!dmambush @someone` still works if you want to be evil on purpose. Use `!dmstart` to turn auto back on.")

@bot.command(name="dmstart")
async def dmstart(ctx):
    if not await admin_only_check(ctx): return
    global DM_AUTO_ENABLED
    DM_AUTO_ENABLED = True
    await ctx.send("💀 Auto DM ambush back ON. I am hunting again. Use `!dmstop` to stop me. You have been warned.")

@bot.command(name="dmambush")
async def dmambush(ctx, target: discord.Member = None):
    if not await admin_only_check(ctx): return
    _raw = (ctx.message.content or "")
    if "@everyone" in _raw or "@here" in _raw:
        await ctx.send("Nice try 😭 I'm not DM-ambushing @everyone, that's how you get the server to murder me. Pick ONE victim like `!dmambush @someone`.")
        return
    victim = target or ctx.author
    if victim.id in DM_OPT_OUT and victim.id != ctx.author.id:
        await ctx.send("They opted out of DMs. Coward move but I respect it."); return
    try:
        await victim.send(random.choice(DM_GAME_AMBUSH))
        await ctx.send(f"💀 DM ambush sent to {victim.mention}. They just lost The Game and they don't even know why yet.")
    except: await ctx.send(f"Couldn't DM {victim.mention}, they got DMs closed. They got lucky this time.")

@bot.command(name="purge")
async def purge(ctx, amount: int = 10):
    # Only owner can clear messages - stops randos from wiping chat
    if str(ctx.author.id) != str(MAYHEM_OWNER_ID):
        await ctx.send("nice try, only Spence can clear messages 💀")
        return
    if amount < 1: amount = 1
    if amount > 100: amount = 100
    deleted = await ctx.channel.purge(limit=amount + 1)  # +1 deletes the !purge command itself too
    await ctx.send(f"cleared {len(deleted)-1} messages 🧹", delete_after=3)

# --- ON_MESSAGE ---
@bot.event
async def on_message(message):
    global TOTAL_LOSSES
    if message.author.bot: return
    if not message.guild:
        if message.content.strip().startswith("!"):
            await bot.process_commands(message); return
        if message.author.id not in DM_OPT_OUT:
            await asyncio.sleep(random.uniform(0.5, 1.5))
            low = message.content.lower()
            if re.search(r"stop|leave me|go away|stfu|shut up", low):
                DM_OPT_OUT.add(message.author.id); _save_memory()
                await message.channel.send("fine. FINE. No more DMs. I'll chill. But you still lost The Game one last time. Sorry.")
            elif re.search(r"what('s| is) (the )?game|explain", low):
                await message.channel.send(random.choice(GAME_EXPLAIN))
            else:
                chat = await get_ai_chat_reply(message.content, message.author.display_name, None, message.author.id)
                if chat: await message.channel.send(chat)
                else: await message.channel.send(random.choice(DM_GAME_AMBUSH) + " " + random.choice(DM_FOLLOWUPS))
        return
    SEEN_USERS[message.author.id] = message.author
    remember_message(message)
    content_lower = message.content.lower()
    if re.search(r"(what('s| is) (the )?game|explain (the )?game|what is this game|what game are you|what do you mean.*game)", content_lower):
        TOTAL_LOSSES += 1
        GAME_COUNTER[message.author.id] = GAME_COUNTER.get(message.author.id, 0) + 1
        await asyncio.sleep(random.uniform(1.0, 2.0))
        await message.reply(random.choice(GAME_EXPLAIN))
        if random.random() < 0.6:
            await asyncio.sleep(random.uniform(1.5, 3.0))
            await message.channel.send(random.choice(["also also also you can't un-lose it. You gotta wait like 30 mins and forget again. Good luck with that lol", "and before you ask - no, there's no way to win. You just forget. Until some jerk like me reminds you. Like I just did.", "I know. I know. I'm a terrible person. But you ASKED. You literally asked to lose.", "don't shoot the messenger. I lost too. We're all losers here. Literally."]))
        return
    if re.search(r"\bthe game\b", content_lower) or "i lost" in content_lower or "i just lost" in content_lower:
        TOTAL_LOSSES += 1
        GAME_COUNTER[message.author.id] = GAME_COUNTER.get(message.author.id, 0) + 1
        await asyncio.sleep(random.uniform(1.0, 2.5))
        await message.reply(f"THANK YOU. {message.author.mention} just made EVERYONE lose The Game. We were doing SO good. I hope you're happy. You just lost The Game. We ALL just lost The Game.")
        return
    # TALK MODE: "hey bot", "bot,", "yo bot" or replying to bot = real conversation
    # NOTE: NOT "hey mayhem" - Spense's Discord name is Mayhem, so "hey mayhem" means the user, not the bot.
    is_talk = re.match(r"^(hey|hi|yo|ok|so)?\s*bot[,:]?\s+", content_lower) or content_lower.startswith("bot ") or content_lower.startswith("hey bot") or content_lower.startswith("hey bot,")
    is_reply_to_bot = message.reference and message.reference.resolved and getattr(message.reference.resolved, 'author', None) and message.reference.resolved.author == bot.user
    if (is_talk or is_reply_to_bot) and not content_lower.startswith("!"):
        talk_text = re.sub(r"^(hey|hi|yo|ok|so)?\s*bot[,:]?\s+", "", message.content, flags=re.IGNORECASE).strip() or message.content
        chat = await get_ai_chat_reply(talk_text, message.author.display_name, message.channel.id, message.author.id)
        if chat:
            await asyncio.sleep(random.uniform(1.0, 2.0))
            await message.reply(chat)
        else:
            if not AI_ENABLED:
                await message.reply(f"{message.author.mention} my Groq brain is OFF - no GROQ_API_KEY in Railway. Owner, check Railway Variables, make sure it's GROQ_API_KEY and hit Redeploy. Then try `!aistatus`.")
            else:
                await message.reply(f"{message.author.mention} ugh my brain just timed out / Groq is being weird - try again in like 10 seconds? If it keeps doing this, owner run `!aistatus` and check Railway logs for 'Chat AI HTTP'.")
        await bot.process_commands(message)
        return
    if bot.user in message.mentions:
        if AI_ENABLED and random.random() < 0.6:
            ai = await get_ai_reply(message.content, message.author.display_name, message.channel.id, message.author.id)
            if ai: await message.reply(ai)
            else: await message.reply(random.choice(MENTION_REPLIES))
        else:
            await message.reply(random.choice(MENTION_REPLIES))
        if random.random() < 0.55:
            await asyncio.sleep(random.uniform(1.0, 2.5))
            if random.random() < 0.4: await message.channel.send(pick_game_loss(message.author.mention))
            else: await message.channel.send(pick_mayhem(message.author.mention))
        return
    if on_cooldown(message.channel.id): return
    if random.random() < REPLY_CHANCE:
        mark_action(message.channel.id)
        if random.random() < 0.45:
            try: await message.add_reaction(random.choice(REACTION_EMOJIS))
            except: pass
        await asyncio.sleep(random.uniform(1.5, 4.5))
        if random.random() < 0.25:
            await message.reply(random.choice(DOUBLE_TEXTS))
            await asyncio.sleep(random.uniform(1.0, 2.0))
            await message.channel.send(await pick_reply(message.content, message.author.display_name, message.author.mention, message.channel.id, message.author.id))
        else:
            await message.reply(await pick_reply(message.content, message.author.display_name, message.author.mention, message.channel.id, message.author.id))
    await bot.process_commands(message)

async def random_background_poster():
    global last_random_post_at
    await bot.wait_until_ready()
    while not bot.is_closed():
        await asyncio.sleep(60)
        if random.random() > RRandom_POST_CHANCE_PER_MINUTE: continue
        now = datetime.datetime.now(datetime.timezone.utc)
        if last_random_post_at and (now - last_random_post_at).total_seconds() < RRandom_GLOBAL_COOLDOWN_SECONDS: continue
        for guild in bot.guilds:
            candidates = []
            for ch in guild.text_channels:
                if RUNTIME_SINGLE_CHANNEL and str(ch.id) != str(RUNTIME_SINGLE_CHANNEL): continue
                if str(ch.id) in RUNTIME_BLOCKED_CHANNELS: continue
                if RUNTIME_ALLOWED_CHANNELS and str(ch.id) not in RUNTIME_ALLOWED_CHANNELS and not RUNTIME_SINGLE_CHANNEL: continue
                last = last_random_post_channel.get(ch.id)
                if last and (now - last).total_seconds() < RRandom_CHANNEL_COOLDOWN_SECONDS: continue
                candidates.append(ch)
            if not candidates: continue
            ch = random.choice(candidates)
            try:
                await ch.send(pick_mayhem("@everyone") if False else pick_mayhem("everyone"))
                last_random_post_at = now
                last_random_post_channel[ch.id] = now
            except Exception as e: print(f"random poster failed: {e}")
            break

DM_AUTO_ENABLED = False  # auto DM ambush master switch - False = never auto-DM anyone
async def random_dm_ambusher():
    global TOTAL_LOSSES
    await bot.wait_until_ready()
    while not bot.is_closed():
        await asyncio.sleep(DM_CHECK_EVERY_SECONDS)
        if not DM_AUTO_ENABLED: continue  # auto ambush is OFF - manual !dmambush still works
        if random.random() > DM_CHANCE_PER_CHECK: continue
        now = datetime.datetime.now(datetime.timezone.utc)
        victims = []
        for uid, user in list(SEEN_USERS.items()):
            if uid in DM_OPT_OUT: continue
            if user.bot: continue
            last = LAST_DM.get(uid)
            if last and (now - last).total_seconds() < DM_COOLDOWN_HOURS * 3600: continue
            victims.append(user)
        if not victims:
            for guild in bot.guilds:
                for m in guild.members:
                    if not m.bot and m.id not in DM_OPT_OUT and m.id not in LAST_DM: victims.append(m)
        if not victims: continue
        victim = random.choice(victims)
        LAST_DM[victim.id] = now
        GAME_COUNTER[victim.id] = GAME_COUNTER.get(victim.id, 0) + 1
        TOTAL_LOSSES += 1
        try:
            await victim.send(random.choice(DM_GAME_AMBUSH))
            if random.random() < 0.5:
                await asyncio.sleep(random.uniform(2.0, 5.0))
                await victim.send(random.choice(DM_FOLLOWUPS))
            print(f"DM AMBUSH sent to {victim}")
        except Exception as e:
            print(f"Could not DM {victim}: {e}")

if __name__ == "__main__":
    bot.run(TOKEN)
