# Deploy Mayhem Bot - Railway (easiest, free)
1. Go to discord.com/developers/applications -> Your Mayhem Bot -> Bot -> Reset Token -> COPY it (never share it)
2. Same page: enable MESSAGE CONTENT INTENT + SERVER MEMBERS INTENT + Save
3. OAuth2 -> URL Generator -> scopes: bot + applications.commands, permissions: Administrator -> invite to your server
4. Go to railway.app -> New Project -> Deploy from GitHub repo (upload this folder to GitHub first) OR Deploy from local / empty + upload
5. In Railway: Variables -> Add DISCORD_TOKEN = your token -> Deploy
6. Check Logs: you should see "MAYHEM ONLINE as Mayhem Bot..."
7. Test in Discord: say hi, @ the bot, type "what's the game", type !dmambush @yourself

# Render alternative
- render.com -> New Worker -> connect repo -> Start Command: python main.py -> Add Env Var DISCORD_TOKEN

# Local test
pip install -r requirements.txt
cp .env.example .env (paste token)
python main.py
