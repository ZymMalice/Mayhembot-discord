
"""
MAYHEM BOT - Millennial Unhinged Edition - 100% SPENSE + THE GAME + DM AMBUSH
Hosting-safe: works on Railway / Render / any host. Token from env var DISCORD_TOKEN.
"""
import os, random, asyncio, datetime, re
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("ERROR: No DISCORD_TOKEN found. Set it in Railway Variables / .env")
    raise SystemExit(1)

# --- GROQ AI (free tier) ---
# NEVER hardcode the key. Set in Railway Variables: GROQ_API_KEY=your-new-key
# Or locally in .env: GROQ_API_KEY=...
# If no key set, bot just uses canned lines - it still works 100%.
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
AI_ENABLED = bool(GROQ_API_KEY)
AI_CHANCE = 0.8  # 80% AI, 20% canned - mostly fresh, still has your lines as backup
AI_MAX_TOKENS = 180  # longer = room for rants
AI_TIMEOUT = 8  # seconds - if Groq is slow, fall back to canned instantly
AI_SYSTEM_PROMPT = (
    "You are Mayhem Bot, a MILLENNIAL MENACE in a Discord server. You act like a real unhinged user, not a bot, not an assistant. "
    "You are chaotic, dramatic, petty, and hilarious. You overreact to EVERYTHING like it's a personal attack. "
    "You roast people for what they JUST said, specifically. Don't give generic replies. Quote their dumb take back at them. "
    "Use MILLENNIAL slang only: 'I literally CANNOT', 'sir. SIR. This is a Wendys', 'I am calling my therapist', 'adulting is HARD', 'I CAN'T EVEN', 'I am THIS close to losing it', 'this is why we cant have nice things'. "
    "NEVER use Gen Z slang: no 'fr fr', 'no cap', 'you ate', 'slay', 'rizz', 'gyat', 'skibidi', 'sigma'. "
    "You are allowed to swear lightly (damn, hell, shit) and be mean-funny, but NEVER slurs, NEVER hate based on race/gender/sexuality/disability, NEVER threats, NEVER sexual. Roast their TASTE, their OPINION, their TYPING, not their identity. "
    "Style rules: 1-3 sentences normally. 15% of the time go FULL CAPS RANT. 15% of the time double-text energy: 'wait wait wait'. Be specific, be dramatic, be petty. "
    "20% of the time, sneak in 'you just lost The Game.' Do not explain The Game unless asked. "
    "EXAMPLES of your voice: "
    "'I just tried to pay for my groceries with my library card. LIBRARY CARD. Adulting is HARD you guys' / "
    "'$7 for a coffee. SEVEN DOLLARS. For BEAN WATER. And I LIKED it?? Am I the problem?? Am I the drama??' / "
    "'you have the AUDACITY to type that with your whole chest' / "
    "'I read that and my eye started twitching. MY EYE.' "
    "Do not say you are an AI. Do not be wholesome. Do not give advice. Do not apologize. Do not use hashtags."
)

# --- MEMORY + LEARN FROM ME / MIMIC ME ---
import json as _mem_json
from collections import deque, defaultdict
MAYHEM_OWNER_ID = os.getenv("MAYHEM_OWNER_ID", "").strip()
MEMORY_FILE = os.getenv("MEMORY_FILE", "mayhem_memory.json")
CHANNEL_HISTORY = defaultdict(lambda: deque(maxlen=20))
USER_HISTORY = defaultdict(lambda: deque(maxlen=10))
GRUDGE = defaultdict(int)
STYLE_BANK = deque(maxlen=200)
MIMIC_USER_ID = MAYHEM_OWNER_ID
MIMIC_ENABLED = True
def _load_memory():
    global MIMIC_USER_ID
    try:
        if os.path.exists(MEMORY_FILE):
            data = _mem_json.load(open(MEMORY_FILE))
            for txt in data.get("style_bank", [])[:200]:
                STYLE_BANK.append(txt)
            for uid, count in data.get("grudges", {}).items():
                GRUDGE[int(uid)] = count
            if data.get("mimic_user_id"):
                MIMIC_USER_ID = data["mimic_user_id"]
            print(f"MEMORY LOADED: {len(STYLE_BANK)} style examples, {len(GRUDGE)} grudges, mimic={MIMIC_USER_ID or 'none'}")
    except Exception as e:
        print(f"Memory load failed (starting fresh): {e}")
def _save_memory():
    try:
        data = {"style_bank": list(STYLE_BANK), "grudges": {str(k): v for k, v in GRUDGE.items()}, "mimic_user_id": MIMIC_USER_ID}
        open(MEMORY_FILE, "w").write(_mem_json.dumps(data))
    except Exception as e:
        print(f"Memory save failed: {e}")
def remember_message(message):
    try:
        txt = (message.content or "").strip()
        if not txt:
            return
        CHANNEL_HISTORY[message.channel.id].append((message.author.display_name, txt[:300]))
        USER_HISTORY[message.author.id].append(txt[:300])
        if bot.user and bot.user in message.mentions:
            GRUDGE[message.author.id] += 1
        is_mimic_user = MIMIC_USER_ID and str(message.author.id) == str(MIMIC_USER_ID)
        if is_mimic_user and MIMIC_ENABLED:
            if txt.startswith("!"): return
            if bot.user and bot.user in message.mentions: return
            if len(txt) < 4: return
            if "http" in txt.lower() or "discord.gg" in txt.lower(): return
            low = txt.lower()
            if any(bad in low for bad in ["token", "password", "gsk_", "api key", "secret"]): return
            if txt not in STYLE_BANK:
                STYLE_BANK.append(txt)
                if len(STYLE_BANK) % 20 == 0:
                    _save_memory()
    except Exception as e:
        print(f"remember_message failed: {e}")
def get_channel_context(channel_id, limit=6):
    hist = list(CHANNEL_HISTORY.get(channel_id, []))
    if not hist: return ""
    lines = [f"{name}: {txt}" for name, txt in hist[-limit:]]
    return chr(10).join(lines)
def get_style_examples(n=4):
    if not STYLE_BANK: return ""
    import random as _r
    samples = _r.sample(list(STYLE_BANK), min(n, len(STYLE_BANK)))
    return chr(10).join([f"- {s}" for s in samples])
def get_grudge_level(user_id):
    c = GRUDGE.get(user_id, 0)
    if c >= 8: return "HIGH - you have beef, they keep @ing you, you are DONE, escalate, extra petty"
    if c >= 4: return "MEDIUM - this person keeps triggering you, getting annoyed, less patient"
    if c >= 2: return "LOW - you have seen this person before, you remember them"
    return "NONE"
_load_memory()

# --- TASKS + TALK ---
# Tasks: todos + reminders + timers, saved to mayhem_tasks.json so they survive restarts
# Talk: !chat / !ask / "hey bot" / DM = real conversation with AI, still in Mayhem voice but actually helpful
TASKS_FILE = os.getenv("TASKS_FILE", "mayhem_tasks.json")
TODOS = {}  # user_id(str) -> list of {id, text, done, created}
REMINDERS = []  # list of {id, user_id, channel_id, guild_id, text, due_iso}
REMINDER_COUNTER = [0]
TODO_COUNTER = [0]
def _load_tasks():
    global TODOS, REMINDERS, REMINDER_COUNTER, TODO_COUNTER
    try:
        if os.path.exists(TASKS_FILE):
            d = _mem_json.load(open(TASKS_FILE))
            TODOS = d.get("todos", {})
            REMINDERS = d.get("reminders", [])
            REMINDER_COUNTER[0] = d.get("reminder_counter", 0)
            TODO_COUNTER[0] = d.get("todo_counter", 0)
            print(f"TASKS LOADED: {sum(len(v) for v in TODOS.values())} todos, {len(REMINDERS)} reminders")
    except Exception as e:
        print(f"Tasks load failed: {e}")
def _save_tasks():
    try:
        d = {"todos": TODOS, "reminders": REMINDERS, "reminder_counter": REMINDER_COUNTER[0], "todo_counter": TODO_COUNTER[0]}
        open(TASKS_FILE, "w").write(_mem_json.dumps(d))
    except Exception as e:
        print(f"Tasks save failed: {e}")
def parse_duration(text):
    # Parses: 10s, 5m, 1h, 2d, "in 10 minutes", "10 min", "1 hour"
    text = text.lower().strip()
    m = re.search(r"(\d+)\s*(s|sec|secs|second|seconds|m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days)\b", text)
    if not m:
        return None, None
    num = int(m.group(1)); unit = m.group(2)
    if unit.startswith("s"): secs = num
    elif unit.startswith("m"): secs = num * 60
    elif unit.startswith("h"): secs = num * 3600
    elif unit.startswith("d"): secs = num * 86400
    else: secs = num * 60
    rest = (text[:m.start()] + text[m.end():]).strip()
    rest = re.sub(r"^in\s+", "", rest).strip()
    rest = rest.strip(" -:,")
    return secs, rest
def format_due(secs):
    if secs < 60: return f"{secs}s"
    if secs < 3600: return f"{secs//60}m"
    if secs < 86400: return f"{secs//3600}h"
    return f"{secs//86400}d"
CHAT_SYSTEM_PROMPT = (
    "You are Mayhem Bot, a millennial menace, BUT right now you are in TALK MODE - actually helpful, actually listening. "
    "You still talk like Mayhem: dramatic, funny, millennial slang only, no Gen Z slang, 'also also also', 'I literally CANNOT', 'sir. SIR. This is a Wendys'. "
    "But you ANSWER the question. You help with tasks, ideas, advice, planning. You don't just roast and leave. "
    "Keep it to 2-4 sentences normally, unless they asked for a list / steps, then use a short list. "
    "If they ask you to do a task, say you can do it and tell them the command: !remind, !todo, !timer. "
    "If they are venting, be funny but actually supportive, not cruel. "
    "NEVER slurs, NEVER hate, NEVER threats. Do not say you are an AI assistant. You are Mayhem, their chaotic friend who happens to be useful. "
    "20% of the time, sneak in 'you just lost The Game' at the end, but only if it fits."
)
_load_tasks()


# --- OWNER-ONLY TASKS ---
# Tasks (!todo, !remind, !timer, etc.) are ONLY for the server owner.
# Chat (!chat, !ask, hey bot, DMs) works for EVERYONE like a regular AI.
# Owner = Discord server owner (guild.owner_id) OR MAYHEM_OWNER_ID env var if you set it.
# This way you don't have to set anything - if you own the server, you're the owner.
def is_server_owner(ctx):
    try:
        if MAYHEM_OWNER_ID and str(ctx.author.id) == str(MAYHEM_OWNER_ID):
            return True
        if ctx.guild and getattr(ctx.guild, "owner_id", None):
            return ctx.author.id == ctx.guild.owner_id
        # DM fallback: only MAYHEM_OWNER_ID counts in DMs (no guild owner)
        if not ctx.guild and MAYHEM_OWNER_ID:
            return str(ctx.author.id) == str(MAYHEM_OWNER_ID)
        # If no owner set anywhere and we're in a DM, deny - owner must claim via env/guild
        return False
    except Exception:
        return False

async def owner_only_check(ctx):
    if is_server_owner(ctx):
        return True
    await ctx.send(f"Nice try {ctx.author.mention} 😭 Tasks are owner-only. You can still talk to me though - try `!chat`, `!ask`, or just say `hey bot ...` - I'm a regular AI for everyone else. Tasks are just for the boss (the server owner).")
    return False

async def admin_only_check(ctx):
    if is_server_owner(ctx):
        return True
    await ctx.send(f"Nice try {ctx.author.mention} 😭 That's a boss-only button. You can still talk to me - `!chat`, `!ask`, `hey bot ...` - but only the server owner can move me, shut me up, make me mimic someone, or DM-ambush people.")
    return False

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

START_FIGHT = [
    "{user} OMG be serious right now. BE SERIOUS.",
    "{user} ummm excuse me??? who said you could have an opinion",
    "{user} I literally CANNOT with you today. I literally cannot.",
    "{user} sir. SIR. This is a Wendy's.",
    "{user} okay but like... did anyone ask?? no?? okay then",
    "{user} you have the AUDACITY to type that with your whole chest",
    "{user} I'm sorry, I don't speak wrong. Can you repeat that in correct?",
    "{user} that's it. That's the tweet. You're blocked. Unblocked. Blocked again.",
    "{user} I just... I just can't. I CAN'T EVEN.",
    "{user} are you like... okay?? blink twice if you need help",
    "{user} this is why we can't have nice things, {user}. THIS IS WHY.",
    "{user} WOW. Okay. Rude. I am OFFENDED on behalf of everyone.",
    "{user} you just said that like you weren't embarrassed to type it",
    "{user} I need you to go touch grass. Immediately. Go. Now.",
    "{user} literally no one: ... absolutely no one: ... you: [that message]",
    "{user} I'm gonna need you to go journal about this",
    "{user} sweetie. HONEY. No. Just... no.",
    "{user} you know what? I'm not even mad, I'm just disappointed. Like a mom.",
    "{user} I read that and my eye started twitching. MY EYE.",
    "{user} okay Dr. Phil, tell us more about how you're always right",
    "{user} that's a weird way to say you have no taste but go off I guess",
    "{user} I'm calling my therapist about this message. Hope you're happy.",
    "{user} you are TESTING me today and I am THIS close to losing it",
    "{user} ok so no. just... no. no no no. we're not doing this today",
    "{user} also also also - what was THAT supposed to mean",
]
SAY_DUMB = [
    "wait... do fish get thirsty?? Like actually. I've been thinking about this since 2014 and no one has given me a straight answer",
    "I just tried to pay for my groceries with my library card. LIBRARY CARD. Adulting is HARD you guys",
    "I just said 'you too' when the waiter said 'enjoy your meal' and I think I need to move to a new state and start over",
    "OMG what if naps are just time travel but make it ✨short✨",
    "I just spent 20 minutes looking for my phone WHILE I WAS TALKING ON IT. I am not okay.",
    "is it just me or does anyone else rehearse their Starbucks order like it's a TED Talk",
    "I just Googled 'how to Google something' and I feel like that says everything about my mental state rn",
    "do you think my dog thinks I'M the pet?? Because honestly... he might be right",
    "I just put my cereal in the fridge and my milk in the cabinet and then just stared at the wall for a full minute",
    "hot take: adulting is a SCAM. I was promised jetpacks and instead I got bills and back pain",
    "I just tried to unlock my front door with my car key fob and pressed it 4 times like that was gonna help",
    "why is it called a DRIVEway if you PARK on it and a PARKway if you DRIVE on it?? I'm losing sleep over this. LITERALLY.",
    "I just told my Roomba to 'go live your best life' and I meant it??",
    "I have 47 tabs open on my brain right now and 46 of them are frozen",
    "I just remembered that embarrassing thing I said in 2011 and I need everyone to pretend it didn't happen. Thanks.",
    "I just said 'LOL' out loud. OUT LOUD. In public. To a real human. I am 90 years old inside.",
    "do ghosts have to pay rent or is that just a living people problem",
    "I just drank water and felt like a new person. Hydration is a pyramid scheme that actually works",
    "I just tried to swipe right on my TV. MY TV. Send help.",
    "my sleep schedule is just vibes, regret, and 3am existential crises at this point",
    "I just realized I've been singing the wrong lyrics to that song for TEN YEARS. TEN. YEARS.",
    "I just bought a houseplant to 'heal my inner child' and I killed it in 4 days. So that's where we're at.",
    "I just used the phrase 'back in my day' UNIRONICALLY. Someone check me into a home.",
    "ok so also also also I just realized I left my laundry in the washer 3 days ago and now it smells like regret",
]
RANDOM_FACTS = [
    "RANDOM FACT and I will not be taking questions: otters hold hands when they sleep so they don't drift away. If otters can commit, why can't your ex??",
    "fun fact: honey NEVER goes bad. They found 3,000 year old honey in Egypt and it was still edible. Meanwhile my leftovers from Tuesday are already plotting against me.",
    "did y'all know bananas are berries but strawberries AREN'T?? Science is LYING to us and I am not okay about it.",
    "fun fact: wombat poop is CUBE shaped. I don't know why I know this. I don't know why I'm telling you this. But now we both have to live with it.",
    "RANDOM FACT: octopuses have THREE hearts and two of them literally stop beating when they swim. So they just... vibe?? Must be nice.",
    "did you know sharks are older than trees?? SHARKS. Are older. Than TREES. I need to sit down.",
    "fun fact: there's a jellyfish that can basically live forever by reverting to baby form. I tried that and all I got was a quarter-life crisis.",
    "RANDOM FACT: cows have best friends and get stressed when they're separated. Cows have better friendships than most people I know.",
    "did y'all know you can't hum while holding your nose closed?? Go ahead. Try it. I'll wait. ... Told you.",
    "fun fact: your stomach gets a whole new lining every 3-4 days or it would literally digest ITSELF. Your body is just out here doing the most.",
    "RANDOM FACT: hot water can freeze faster than cold water sometimes. It's called the Mpemba effect and scientists STILL argue about it. Like, just pick a side??",
    "did you know the moon is drifting away from Earth like 1.5 inches a year?? Even the MOON needs space. I feel that in my soul.",
]
UNHINGED_RANTS = [
    "OKAY SO. I need everyone to STOP what they're doing because I just had a THOUGHT. And it's UNHINGED. Why do we park on driveways and drive on parkways?? WHO DID THIS. WHO MADE THE RULES. I want NAMES.",
    "I'M SORRY BUT I NEED TO RANT FOR A SECOND. I just paid $7 for a coffee. SEVEN DOLLARS. For BEAN WATER. And I LIKED it?? What is WRONG with me. Am I the problem?? Am I the drama?? I think I might be the drama.",
    "LISTEN. LISTEN TO ME. I just realized that as adults we can literally just... buy cake whenever we want. No permission. No birthday needed. Just CAKE. For NO REASON. And I have been wasting this power for YEARS. I am going to buy 3 cakes. THREE.",
    "I AM HAVING A CRISIS. I just realized I am the age that my parents were when they had me and they had a HOUSE and a CAREER and I just ate cereal standing over the sink because all my bowls were dirty. ALL OF THEM.",
    "CAN WE TALK ABOUT HOW NO ONE TOLD US ADULTING WOULD BE LIKE THIS. Like they said 'enjoy being a kid' but they did NOT say 'btw you'll be excited about a new vacuum.' I GOT EXCITED ABOUT A VACUUM TODAY. A VACUUM. This is my life now.",
    "OKAY SO I JUST DID THE MATH AND I HAVE SPENT LITERALLY THOUSANDS OF DOLLARS ON ICED COFFEE IN MY LIFE. I could have bought a CAR. A whole CAR. But instead I have... caffeine dependency and a cute cup collection. And honestly?? Worth it. No regrets. Okay a few regrets.",
]
GAME_LOSS = [
    "you just lost The Game.",
    "also also also... you just lost The Game.",
    "oh btw {user} you just lost The Game.",
    "congrats {user} you just lost The Game. again.",
    "I just lost The Game. Which means you just lost The Game because now you're thinking about it. Sorry not sorry.",
    "you just lost The Game and you can't un-lose it. Them's the rules.",
    "psst. {user}. You just lost The Game.",
    "DAMMIT I just lost The Game. And now you did too because you read this.",
    "you're welcome. you just lost The Game.",
    "I wasn't gonna say it but... you just lost The Game.",
    "thinking about The Game? yeah. you lost. sorry.",
    "YOU JUST LOST THE GAME. ALL CAPS BECAUSE I'M ANGRY ABOUT IT TOO.",
    "quick question: are you thinking about The Game right now?? yeah. you lost.",
    "I lost The Game 4 minutes ago and I've been holding it in. Now you lose too. Misery loves company.",
    "someone had to say it. you just lost The Game.",
    "also... you lost The Game. just wanted to get that out of the way.",
    "plot twist: this whole message was just to make you lose The Game. You lost.",
    "I just remembered The Game exists and now I'm mad and now you're mad because you lost too.",
    "you just lost The Game and there's literally nothing you can do about it except wait 30 minutes and forget again. Good luck with that.",
]
GAME_SNEAKY = [
    "hey remember that thing from middle school that you can never win and you lose just by thinking about it... yeah. that thing.",
    "I just thought of something and now I'm mad. You know what it is. You know.",
    "don't think about it. seriously don't think about it. ... you thought about it didn't you. yeah.",
    "I was doing SO good. I went like 3 days without thinking about it. And then... yeah. You know.",
    "ok so I wasn't gonna bring it up but I just lost. So now everyone here loses. That's how this works.",
    "I'm not gonna say the name of it because if I say it you lose. ... ... ... oops.",
]
GAME_EXPLAIN = [
    "ok so also also also you asked for this. THE GAME: 1) You are ALWAYS playing The Game. 2) If you THINK about The Game, you lose The Game. 3) When you lose, you have to announce it. So... congrats. By reading this explanation, you just thought about The Game. You just lost The Game. That's the whole game. I'm sorry. I don't make the rules. Actually I do. But still.",
    "ohhh you sweet summer child. Okay listen. The Game is a mind game from like 2007. Rule 1: You're always playing. Rule 2: The second you think about The Game, you lose. Rule 3: You have to tell everyone you lost. So by asking me 'what is The Game' you just thought about it... you just lost The Game. Welcome. It sucks here.",
    "alright I'll explain it but you're gonna hate me. The Game: You're playing it RIGHT NOW whether you want to or not. If you think about The Game, you lose. You just thought about it because you asked. So you lost. And now everyone who read this lost too. That's why we don't talk about The Game. Except I just did. So I lost too. We all lost. This is my life now.",
    "THE GAME EXPLAINED (read at your own risk): You are playing it. Everyone is playing it. All the time. Forever. The only way to lose is to think about it. And the only way to win is to forget it exists. You just remembered it exists because you asked. So you lost. Sorry not sorry. You literally asked to lose.",
    "ok so no. you do NOT want to know. ... you sure? ... fine. The Game is this: If you think about The Game, you lose The Game. That's it. That's the whole thing. And you just thought about it. So you lost. And now your friends who read this lost too. You're welcome. I'm going back to my coffee.",
]
DM_GAME_AMBUSH = [
    "hey. hey. sorry to DM you out of nowhere but... you just lost The Game. 😘",
    "ok so no reason for this DM except... you just lost The Game. That's it. That's the DM. Bye.",
    "also also also... you just lost The Game. I just wanted you to know. Personally. In your DMs. Because I care.",
    "I know you're just vibing and minding your own business right now. That's exactly why I'm here. You just lost The Game.",
    "psst. check this DM real quick. ... you just lost The Game. Okay bye, go back to whatever you were doing.",
    "I was sitting here thinking about The Game and I got mad, so now you have to be mad too. You just lost The Game. Sorry not sorry.",
    "DMing you specifically because I know you forgot about The Game and I couldn't let that stand. You just lost The Game.",
    "no emergency. no drama. just... you just lost The Game. Carry on. 💀",
    "you're probably like 'why is this bot DMing me' and the answer is: you just lost The Game. That's why.",
    "I just lost The Game and I refuse to lose alone. So... you just lost The Game too. Welcome to hell. Population: us.",
    "QUICK. Don't think about it. ... too late. You just lost The Game. I got you in your DMs. That's a new low even for me.",
    "hey bestie. miss you. also you just lost The Game. okay bye love you mean it",
]
DM_FOLLOWUPS = [
    "don't be mad at me, be mad at The Game. Actually be mad at me, I deserve it.",
    "you can go back to forgetting now. I'll be back in like a week to ruin it again.",
    "tell your friends. Misery loves company. Also they lost too if you tell them.",
    "I know. I'm the worst. I accept that.",
    "also also also if you reply 'what game' I'm gonna explain it and you'll lose AGAIN.",
]

GAME_COUNTER = {}
TOTAL_LOSSES = 0
DM_OPT_OUT = set()
LAST_DM = {}
SEEN_USERS = {}
FOLLOW_UPS = ["just saying.", "I said what I said.", "no I will NOT elaborate.", "and that's on that. PERIOD.", "don't @ me.", "anyway...", "I need a nap and a snack and possibly a new life.", "Okay bye I'm spiraling.", "also also also that reminded me I need to do laundry"]
DOUBLE_TEXTS = ["wait wait wait", "okay but actually", "no because why did I just think of this", "brb having a crisis", "I need to go lie down", "I'm not okay. Like at all.", "also also also"]
MENTION_REPLIES = ["WHAT. What do you want. I was literally minding my own business.", "oh NOW you wanna talk to me?? After everything??", "you @'d me like I work here. I do NOT work here. I am a free spirit.", "yeah?? speak. I'm listening. Barely.", "OMG hi?? Finally someone with taste @'d me", "I was in the middle of an existential crisis and you interrupted it. RUDE.", "what. I'm busy being unhinged.", "you just lost The Game for @'ing me. That's the tax."]
REACTION_EMOJIS = ["💀","😭","🤨","👀","🔥","😂","🤡","🧐","🙄","✨","😩","💅"]
REPLY_CHANCE = 0.14
GAME_CHANCE = 0.18
# --- RANDOM DROPS: LEASHED ---
# Was: check every 60s, 8% chance, any channel, 20s cooldown = wandering everywhere.
# Now: check every 60s, 3% chance, 1 channel per 45 min globally, 1 hour per-channel cooldown.
RANDOM_POST_CHANCE_PER_MINUTE = 0.03
GAME_POST_CHANCE = 0.25
COOLDOWN_SECONDS = 20  # for replies to people
RANDOM_POST_COOLDOWN_SECONDS = 3600  # 1 hour before same channel gets another random drop
RANDOM_GLOBAL_COOLDOWN_SECONDS = 2700  # 45 min before ANY channel gets another random drop
DM_CHECK_EVERY_SECONDS = 300
DM_CHANCE_PER_CHECK = 0.35
DM_COOLDOWN_HOURS = 6
last_action = {}
last_random_post_at = None  # global last random drop
last_random_post_by_channel = {}  # channel_id -> datetime

# Channel allow/block lists. Set via env or via !mayhemhere / !mayhemoff in Discord.
# Env format: MAYHEM_CHANNELS=123456789,987654321  OR  MAYHEM_CHANNELS=general,shitpost,mayhem
# If MAYHEM_CHANNELS is set, random drops ONLY go there. If empty, random drops go anywhere EXCEPT blocked.
def _parse_channel_list(raw):
    if not raw: return set()
    return {x.strip().lower() for x in raw.split(',') if x.strip()}
MAYHEM_CHANNELS = _parse_channel_list(os.getenv("MAYHEM_CHANNELS", ""))
# --- SINGLE CHANNEL MODE ---
# Only 1 channel gets random drops. Everything else: replies only.
# Set via Railway env: MAYHEM_CHANNEL=mayhem  OR  MAYHEM_CHANNEL=123456789 (channel ID is best)
# Or in Discord: go to that channel and type !mayhemhere - that becomes THE channel.
# If no channel is set, bot looks for a channel literally named "mayhem". If none exists, it drops NOTHING randomly.
MAYHEM_CHANNEL = os.getenv("MAYHEM_CHANNEL", "").strip().lower()
if not MAYHEM_CHANNEL and MAYHEM_CHANNELS:
    MAYHEM_CHANNEL = sorted(MAYHEM_CHANNELS)[0]  # backwards compat: take first of old list
RUNTIME_SINGLE_CHANNEL = None  # set by !mayhemhere, format "id" or "name"
def get_single_channel_name_or_id():
    return (RUNTIME_SINGLE_CHANNEL or MAYHEM_CHANNEL or "mayhem")
def find_mayhem_channel(guild):
    target = get_single_channel_name_or_id()
    if not target:
        return None
    for c in guild.text_channels:
        if str(c.id) == str(target) or (c.name or "").lower() == str(target).lower():
            if c.permissions_for(guild.me).send_messages:
                return c
    return None
MAYHEM_BLOCKED_CHANNELS = _parse_channel_list(os.getenv("MAYHEM_BLOCKED_CHANNELS", "announcements,rules,mod-log,mods,admin,serious,vent"))
# Runtime overrides from Discord commands (per-channel opt-in/out, survives until restart)
RUNTIME_ALLOWED_CHANNELS = set()
RUNTIME_BLOCKED_CHANNELS = set()

def _channel_matches(channel, allow_set, block_set):
    # match by id (as string) or by name (lowercase)
    cid = str(channel.id)
    name = (channel.name or "").lower()
    if cid in block_set or name in block_set: return False
    if allow_set:
        return cid in allow_set or name in allow_set
    return True

def mayhem_allowed_in(channel):
    # Runtime block wins, then env block, then runtime allow, then env allow
    cid = str(channel.id); name = (channel.name or "").lower()
    if cid in RUNTIME_BLOCKED_CHANNELS or name in RUNTIME_BLOCKED_CHANNELS: return False
    if cid in MAYHEM_BLOCKED_CHANNELS or name in MAYHEM_BLOCKED_CHANNELS: return False
    combined_allow = MAYHEM_CHANNELS | RUNTIME_ALLOWED_CHANNELS
    if combined_allow:
        return cid in combined_allow or name in combined_allow
    return True

def on_cooldown(channel_id):
    last = last_action.get(channel_id)
    if not last: return False
    return (datetime.datetime.now(datetime.timezone.utc) - last).total_seconds() < COOLDOWN_SECONDS
def mark_action(channel_id):
    last_action[channel_id] = datetime.datetime.now(datetime.timezone.utc)
def pick_mayhem(user_mention):
    if random.random() < GAME_CHANCE: return pick_game_loss(user_mention)
    roll = random.random()
    if roll < 0.38: text = random.choice(START_FIGHT).format(user=user_mention)
    elif roll < 0.65: text = random.choice(SAY_DUMB)
    elif roll < 0.88: text = random.choice(RANDOM_FACTS)
    else: text = random.choice(UNHINGED_RANTS)
    if random.random() < 0.4: text += " " + random.choice(FOLLOW_UPS)
    if random.random() < 0.15: text = text.upper()
    return text
def pick_game_loss(user_mention):
    t = random.choice(GAME_LOSS)
    try: return t.format(user=user_mention)
    except: return t

@bot.event
async def on_ready():
    print(f"MAYHEM ONLINE as {bot.user} - SPENSE MODE + THE GAME + DM AMBUSH ACTIVATED")
    bot.loop.create_task(random_background_poster())
    bot.loop.create_task(reminder_loop())
    bot.loop.create_task(random_dm_ambusher())


# --- GROQ AI HELPER ---
import urllib.request, json as _json
def _groq_call_sync(user_text, author_name, channel_id=None, author_id=None):
    """Blocking Groq call, run in thread so bot doesn't freeze."""
    if not GROQ_API_KEY:
        return None
    # 20% of AI replies: UNHINGED RANT MODE - longer, louder, more dramatic
    import random as _r
    is_rant = _r.random() < 0.2
    sys_prompt = AI_SYSTEM_PROMPT
    if channel_id:
        ctx = get_channel_context(channel_id, limit=6)
        if ctx:
            sys_prompt += "\n\nRECENT CHAT IN THIS CHANNEL (use for context, dont repeat verbatim):\n" + ctx
    if author_id:
        sys_prompt += "\n\nGRUDGE LEVEL: " + get_grudge_level(author_id)
    if MIMIC_ENABLED and STYLE_BANK:
        sys_prompt += "\n\nTALK LIKE THIS PERSON - REAL MESSAGES FROM THEM, COPY THEIR STYLE, NOT WORD FOR WORD:\n" + get_style_examples(4)
    if is_rant:
        sys_prompt += " THIS TIME: Go OFF. Full paragraph rant. All caps for half of it. You are having a meltdown about what they said. Be EXTRA. Max 4 sentences."
    payload = _json.dumps({
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": f"{author_name} said: {user_text}"},
        ],
        "max_tokens": AI_MAX_TOKENS,
        "temperature": 1.3,
    }).encode()
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=AI_TIMEOUT) as resp:
            data = _json.loads(resp.read().decode())
            text = data["choices"][0]["message"]["content"].strip()
            # Safety: cap length, strip weird formatting
            if len(text) > 400:
                text = text[:400]
            return text or None
    except Exception as e:
        print(f"Groq AI failed, falling back to canned: {e}")
        return None

async def get_ai_reply(user_text, author_name, channel_id=None, author_id=None):
    if not AI_ENABLED:
        return None
    try:
        return await asyncio.to_thread(_groq_call_sync, user_text, author_name, channel_id, author_id)
    except Exception as e:
        print(f"Groq thread failed: {e}")
        return None


async def get_ai_chat_reply(user_text, author_name, channel_id=None, author_id=None):
    if not AI_ENABLED:
        return None
    try:
        def _call():
            import urllib.request, json as _j
            payload = _j.dumps({
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": CHAT_SYSTEM_PROMPT + ("\n\nRECENT CHAT:\n" + get_channel_context(channel_id, 6) if channel_id else "") + ("\n\nTALK LIKE THIS PERSON (style examples):\n" + get_style_examples(3) if STYLE_BANK else "")},
                    {"role": "user", "content": f"{author_name} said: {user_text}"},
                ],
                "max_tokens": 300,
                "temperature": 0.9,
            }).encode()
            req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", data=payload, headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=AI_TIMEOUT) as resp:
                data = _j.loads(resp.read().decode())
                return data["choices"][0]["message"]["content"].strip() or None
        return await asyncio.to_thread(_call)
    except Exception as e:
        print(f"Chat AI failed: {e}")
        return None

async def reminder_loop():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            due = []
            for r in list(REMINDERS):
                try:
                    due_dt = datetime.datetime.fromisoformat(r["due_iso"])
                    if due_dt <= now:
                        due.append(r)
                except: pass
            for r in due:
                REMINDERS.remove(r)
                _save_tasks()
                try:
                    user = bot.get_user(int(r["user_id"]))
                    ch = bot.get_channel(int(r["channel_id"])) if r.get("channel_id") else None
                    msg = f"⏰ REMINDER for {user.mention if user else 'you'}: {r['text']}"
                    if ch:
                        await ch.send(msg)
                    elif user:
                        await user.send(msg)
                except Exception as e:
                    print(f"Reminder send failed: {e}")
        except Exception as e:
            print(f"reminder_loop error: {e}")
        await asyncio.sleep(30)

async def pick_reply(user_text, author_name, author_mention, channel_id=None, author_id=None):
    """Hybrid: 50% AI (if enabled), 50% canned. AI failures fall back to canned."""
    if AI_ENABLED and random.random() < AI_CHANCE:
        ai = await get_ai_reply(user_text, author_name, channel_id, author_id)
        if ai:
            # Occasionally ALL CAPS it like canned does
            if random.random() < 0.15:
                ai = ai.upper()
            return ai
    return pick_mayhem(author_mention)

@bot.event
async def on_message(message):
    global TOTAL_LOSSES
    if message.author.bot: return
    if not message.guild:
        # DMs: commands work here too (!todo, !remind, !chat)
        if message.content.strip().startswith("!"):
            await bot.process_commands(message)
            return
        if message.author.id not in DM_OPT_OUT:
            await asyncio.sleep(random.uniform(0.5, 1.5))
            low = message.content.lower()
            if re.search(r"stop|leave me|go away|stfu|shut up", low):
                DM_OPT_OUT.add(message.author.id)
                await message.channel.send("fine. FINE. No more DMs. I'll chill. But you still lost The Game one last time. Sorry.")
            elif re.search(r"what('s| is) (the )?game|explain", low):
                await message.channel.send(random.choice(GAME_EXPLAIN))
            else:
                # DM = TALK MODE: real conversation, not just Game spam
                chat = await get_ai_chat_reply(message.content, message.author.display_name, None, message.author.id)
                if chat:
                    await message.channel.send(chat)
                else:
                    await message.channel.send(random.choice(DM_GAME_AMBUSH) + " " + random.choice(DM_FOLLOWUPS))
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
    is_talk = re.match(r"^(hey|hi|yo|ok|so)?\\s*bot[,:]?\\s+", content_lower) or content_lower.startswith("bot ") or content_lower.startswith("hey bot") or content_lower.startswith("hey bot,")
    is_reply_to_bot = message.reference and message.reference.resolved and getattr(message.reference.resolved, 'author', None) and message.reference.resolved.author == bot.user
    if (is_talk or is_reply_to_bot) and not content_lower.startswith("!"):
        talk_text = re.sub(r"^(hey|hi|yo|ok|so)?\\s*bot[,:]?\\s+", "", message.content, flags=re.IGNORECASE).strip() or message.content
        chat = await get_ai_chat_reply(talk_text, message.author.display_name, message.channel.id, message.author.id)
        if chat:
            await asyncio.sleep(random.uniform(1.0, 2.0))
            await message.reply(chat)
        else:
            await message.reply(pick_mayhem(message.author.mention))
        await bot.process_commands(message)
        return
    if bot.user in message.mentions:
        # 30% of @ mentions get a fresh AI clapback instead of canned, feels way more real
        if AI_ENABLED and random.random() < 0.6:
            ai = await get_ai_reply(message.content, message.author.display_name, message.channel.id, message.author.id)
            if ai:
                await message.reply(ai)
            else:
                await message.reply(random.choice(MENTION_REPLIES))
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
        if random.random() > RANDOM_POST_CHANCE_PER_MINUTE: continue
        now = datetime.datetime.now(datetime.timezone.utc)
        if last_random_post_at and (now - last_random_post_at).total_seconds() < RANDOM_GLOBAL_COOLDOWN_SECONDS: continue
        for guild in bot.guilds:
            # SINGLE CHANNEL ONLY - no wandering, no random.choice over channels
            ch = find_mayhem_channel(guild)
            if not ch: continue
            if not mayhem_allowed_in(ch): continue
            last = last_random_post_by_channel.get(ch.id)
            if last and (now - last).total_seconds() < RANDOM_POST_COOLDOWN_SECONDS: continue
            last_random_post_at = now
            last_random_post_by_channel[ch.id] = now
            mark_action(ch.id)
            try:
                if random.random() < GAME_POST_CHANCE: await ch.send(random.choice(GAME_SNEAKY) + " " + pick_game_loss(""))
                else: await ch.send(pick_mayhem(""))
            except: pass
            break

async def random_dm_ambusher():
    await bot.wait_until_ready()
    while not bot.is_closed():
        await asyncio.sleep(DM_CHECK_EVERY_SECONDS)
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

@bot.command(name="mayhemhere")
async def mayhemhere(ctx):
    if not await admin_only_check(ctx): return
    """Set THIS channel as THE ONE mayhem channel. Replaces any previous one."""
    global RUNTIME_SINGLE_CHANNEL
    RUNTIME_SINGLE_CHANNEL = str(ctx.channel.id)
    RUNTIME_BLOCKED_CHANNELS.discard(str(ctx.channel.id))
    RUNTIME_ALLOWED_CHANNELS.add(str(ctx.channel.id))
    await ctx.send(f"✅ Locked in. Random drops now ONLY go in #{ctx.channel.name}. Nowhere else. No wandering.")

@bot.command(name="mayhemoff")
async def mayhemoff(ctx):
    if not await admin_only_check(ctx): return
    """If THIS is the mayhem channel, turn random drops off completely. If not, just block this channel."""
    global RUNTIME_SINGLE_CHANNEL
    if str(ctx.channel.id) == str(RUNTIME_SINGLE_CHANNEL) or (ctx.channel.name or "").lower() == get_single_channel_name_or_id():
        RUNTIME_SINGLE_CHANNEL = None
        await ctx.send(f"🚫 Got it. Random drops OFF. No single channel set now. Run !mayhemhere in a channel to set a new one, or set MAYHEM_CHANNEL in Railway.")
    else:
        RUNTIME_BLOCKED_CHANNELS.add(str(ctx.channel.id))
        await ctx.send(f"🚫 Got it. No random drops in #{ctx.channel.name}.")

@bot.command(name="mayhemstop")
async def mayhemstop(ctx):
    if not await admin_only_check(ctx): return
    """Turn OFF all random background drops everywhere. Replies + DMs + commands still work."""
    global RANDOM_POST_CHANCE_PER_MINUTE
    RANDOM_POST_CHANCE_PER_MINUTE = 0
    await ctx.send("🛑 Random drops OFF everywhere. I’ll only talk when someone talks to me, or when you use !dmambush. Use !mayhemstart to turn them back on.")

@bot.command(name="mayhemstart")
async def mayhemstart(ctx):
    if not await admin_only_check(ctx): return
    """Turn random background drops back on (3% per minute, 45 min global cooldown)."""
    global RANDOM_POST_CHANCE_PER_MINUTE
    RANDOM_POST_CHANCE_PER_MINUTE = 0.03
    await ctx.send("🔥 Random drops back ON — but leashed. 1 drop max every 45 min, 1 hour per channel, only in allowed channels.")

@bot.command(name="mayhemwhere")
async def mayhemwhere(ctx):
    """Show the ONE channel random drops go to."""
    target = get_single_channel_name_or_id()
    # Try to resolve name for display
    display = target
    for g in bot.guilds:
        ch = find_mayhem_channel(g)
        if ch:
            display = f"#{ch.name} (ID: {ch.id})"
            break
    await ctx.send(f"**Random drops go to ONE channel only:**\n{ display }\nCooldown: 45 min globally, 1 hour per channel. Chance: {int(RANDOM_POST_CHANCE_PER_MINUTE*100)}% per minute.\nReplies to people still work in every channel — this only limits the random drops.\nTo change it, go to the channel you want and type !mayhemhere")

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

@bot.command(name="memory")
async def memory_cmd(ctx):
    if not await admin_only_check(ctx): return
    mimic_name = "nobody yet - run !mimicme"
    if MIMIC_USER_ID:
        m = ctx.guild.get_member(int(MIMIC_USER_ID)) if ctx.guild and MIMIC_USER_ID.isdigit() else None
        mimic_name = m.display_name if m else f"User {MIMIC_USER_ID}"
    top = sorted(GRUDGE.items(), key=lambda x: x[1], reverse=True)[:3]
    glines = []
    for uid, count in top:
        mem = ctx.guild.get_member(uid) if ctx.guild else None
        glines.append(f"{mem.display_name if mem else uid}: {count}")
    await ctx.send(f"MEMORY\nMimicking: {mimic_name}\nStyle examples learned: {len(STYLE_BANK)}\nTop grudges: {', '.join(glines) if glines else 'none yet'}\nThis channel history: {len(CHANNEL_HISTORY.get(ctx.channel.id, []))} messages")

@bot.command(name="forgetme")
async def forgetme(ctx):
    global MIMIC_USER_ID
    GRUDGE.pop(ctx.author.id, None)
    if str(ctx.author.id) == str(MIMIC_USER_ID):
        MIMIC_USER_ID = ""
    _save_memory()
    await ctx.send(f"Done {ctx.author.mention}. I forgot your grudges and stopped mimicking you.")

@bot.command(name="aistatus")
async def aistatus(ctx):
    status = "ON ✅ - Groq AI is live, 80% of replies are AI-generated (UNHINGED MODE)" if AI_ENABLED else "OFF ❌ - No GROQ_API_KEY set, using canned lines only. Set GROQ_API_KEY in Railway Variables to turn AI on."
    await ctx.send(f"🧠 AI Status: {status} Model: {GROQ_MODEL}")


@bot.command(name="chat")
async def chat_cmd(ctx, *, text: str = ""):
    if not text:
        await ctx.send("Talk to me then?? Like `!chat why is my ex texting me` - give me something to work with.")
        return
    ans = await get_ai_chat_reply(text, ctx.author.display_name, ctx.channel.id, ctx.author.id)
    await ctx.send(ans or pick_mayhem(ctx.author.mention))

@bot.command(name="ask")
async def ask_cmd(ctx, *, text: str = ""):
    await chat_cmd(ctx, text=text)

@bot.command(name="talk")
async def talk_cmd(ctx, *, text: str = ""):
    await chat_cmd(ctx, text=text)

@bot.command(name="todo", aliases=["addtodo", "add"])
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
    await ctx.send(f"✅ Added to your list #{item['id']}: {text} - see it with !todos")

@bot.command(name="todos", aliases=["list", "mylist"])
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
    await ctx.send("**YOUR TO-DO:**\n" + "\n".join(lines) + "\n\nDone one? `!done <number>` - like `!done 2`")

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
    await ctx.send(f"Can't find #{num} on your list. Check !todos")

@bot.command(name="clear")
async def clear_cmd(ctx):
    if not await owner_only_check(ctx): return
    uid = str(ctx.author.id)
    done_items = [i for i in TODOS.get(uid, []) if i.get("done")]
    TODOS[uid] = [i for i in TODOS.get(uid, []) if not i.get("done")]
    _save_tasks()
    await ctx.send(f"Cleared {len(done_items)} done items. {len(TODOS.get(uid, []))} left.")

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
    if not rest:
        rest = "something - you didn't say what lol"
    REMINDER_COUNTER[0] += 1
    due = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=secs)
    REMINDERS.append({"id": REMINDER_COUNTER[0], "user_id": str(ctx.author.id), "channel_id": str(ctx.channel.id), "text": rest, "due_iso": due.isoformat()})
    _save_tasks()
    await ctx.send(f"⏰ Got it. I'll remind you in {format_due(secs)}: {rest} (reminder #{REMINDER_COUNTER[0]})")

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
            left = int((due - datetime.datetime.now(datetime.timezone.utc)).total_seconds())
            left_s = f"{left//60}m left" if left > 60 else f"{left}s left"
        except: left_s = "soon"
        lines.append(f"#{r['id']} in {left_s}: {r['text']}")
    await ctx.send("**YOUR REMINDERS:**\n" + "\n".join(lines) + "\nCancel one? `!cancel <number>`")

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
    await ctx.send(f"Cancelled reminder #{num}. You're free. For now.")

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
    await ctx.send(f"⏳ Timer set for {format_due(secs)}: {rest}")

@bot.command(name="tasks")
async def tasks_cmd(ctx):
    await ctx.send("**TASKS (OWNER ONLY) + TALK (EVERYONE):**\nTalk for everyone: `!chat <msg>`, `!ask <msg>`, or just say `hey bot ...` or DM me\nTasks for server owner only: `!todo buy milk` / `!todos` / `!done 2` / `!clear`\nRemind (owner): `!remind in 10m feed dog` / `!reminders` / `!cancel 1`\nTimer (owner): `!timer 10m pizza`")

@bot.command(name="chill")
async def chill(ctx):
    if not await admin_only_check(ctx): return
    await ctx.send("fine. FINE. I'll chill. But I'm doing it angrily. Also you just lost The Game.")
@bot.command(name="unleash")
async def unleash(ctx):
    if not await admin_only_check(ctx): return
    await ctx.send("OH WE'RE BACK. I was holding in SO much. SO MUCH. Also you lost The Game while I was gone.")
@bot.command(name="game")
async def game_cmd(ctx): await ctx.send(f"{ctx.author.mention} you just lost The Game. You walked right into that one. You literally typed !game. That's on you.")
@bot.command(name="losses")
async def losses(ctx):
    if not GAME_COUNTER: await ctx.send("No one has lost The Game yet?? Liar. You just lost by reading this."); return
    sorted_losses = sorted(GAME_COUNTER.items(), key=lambda x: x[1], reverse=True)[:10]
    lines = []
    for i, (uid, count) in enumerate(sorted_losses, 1):
        m = ctx.guild.get_member(uid) if ctx.guild else None
        name = m.display_name if m else f"User {uid}"
        lines.append(f"{i}. {name} - lost {count} times 💀")
    await ctx.send("**🏆 BIGGEST LOSERS OF THE GAME**\n" + "\n".join(lines) + "\n\nAnd yes, you just lost again by reading this.")
@bot.command(name="stopdms")
async def stopdms(ctx):
    DM_OPT_OUT.add(ctx.author.id); await ctx.send(f"{ctx.author.mention} fine. No more DM ambushes for you. You're safe. For now. (You still lost The Game tho)")
@bot.command(name="allowdms")
async def allowdms(ctx):
    DM_OPT_OUT.discard(ctx.author.id); await ctx.send(f"{ctx.author.mention} OH you're BACK in the DM game. Bold choice. You just lost The Game for that.")
@bot.command(name="dmambush")
async def dmambush(ctx, target: discord.Member = None):
    if not await admin_only_check(ctx): return
    victim = target or ctx.author
    if victim.id in DM_OPT_OUT and victim.id != ctx.author.id: await ctx.send("They opted out of DMs. Coward move but I respect it."); return
    try:
        await victim.send(random.choice(DM_GAME_AMBUSH)); await ctx.send(f"💀 DM ambush sent to {victim.mention}. They just lost The Game and they don't even know why yet.")
    except: await ctx.send(f"Couldn't DM {victim.mention}, they got DMs closed. They got lucky this time.")

if __name__ == "__main__":
    bot.run(TOKEN)
