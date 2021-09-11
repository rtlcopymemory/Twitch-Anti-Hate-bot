import os
from twitchio.ext import commands
from twitchio import Message, Channel, Chatter
import sqlite3
import re


regex = r"(h[o0][s5]{2,}[o0]*[0-9]*.*)|(h[o0][s5]t[0o]+[0-9]*.*)"


class Bot(commands.Bot):

    def __init__(self):
        super().__init__(
            token=os.getenv("ACCESS_TOKEN"),
            prefix=os.getenv("BOT_PREFIX"),
            initial_channels=os.getenv("CHANNELS").split(" ")
        )

        db_path = os.getenv("DB_PATH")

        self.con = sqlite3.connect(db_path)

        if not os.path.isfile(db_path):
            print(f"[ WARN ] File {db_path} doesn't exist, creating a new one")
            cur = self.con.cursor()
            cur.execute('''CREATE TABLE IF NOT EXISTS bans
                        (nickname TEXT UNIQUE)''')
            self.con.commit()


    async def event_ready(self):
        # Notify us when everything is ready!
        # We are logged in and ready to chat and use commands...
        print(f'Logged in as | {self.nick}')


    async def event_message(self, message: Message):
        if message.echo:
            return
        
        # Since we have commands and are overriding the default `event_message`
        # We must let the bot know we want to handle and invoke our commands...
        await self.handle_commands(message)


    @commands.command(aliases=["test", "world"])
    async def hello(self, ctx: commands.Context):
        await ctx.send(f'Hello {ctx.author.name}!')
    

    @commands.command(aliases=["init"])
    async def run_bans(self, ctx: commands.Context):
        bot = ctx.get_user(self.nick)
        if not bot.is_mod:
            ctx.send("Cannot run ban commands as not a mod")
            return

        if not ctx.author.is_mod:
            return

        cur = self.con.cursor()

        bans_fetch = cur.execute('SELECT nickname FROM bans').fetchall()
        await self.ban_users([row[0] for row in bans_fetch], ctx.channel)
        
        await ctx.send(f'Users banned')
    
    async def ban_users(self, users: list, channel: Channel):
        for nickname in users:
            await channel.send(f"/ban {nickname}")
    

    @commands.command(aliases=["ban"])
    async def add_ban(self, ctx: commands.Context):
        curr_bot = ctx.get_user(self.nick)
        if not curr_bot.is_mod:
            ctx.send("Cannot run ban commands as not a mod")
            return
        
        if not ctx.author.is_mod:
            return
        
        cur = self.con.cursor()

        content: str = ctx.message.content
        nicknames = content.split(" ")[1:]

        if len(nicknames) < 1:
            await ctx.send(f"Usage: {ctx.prefix} <user> [<user>, ...]")
            return

        for nickname in nicknames:
            try:
                cur.execute('INSERT INTO bans VALUES (?)', (nickname,))
            except sqlite3.IntegrityError as e:
                print(f"{e} | {nickname}")

            self.con.commit()
            await ctx.channel.send(f"/ban {nickname}")

        await ctx.send(f"User/Users banned")
    

    @commands.command()
    async def check(self, ctx: commands.Context):
        curr_bot = ctx.get_user(self.nick)
        if not curr_bot.is_mod:
            ctx.send("Cannot run ban commands as not a mod")
            return
        
        if not ctx.author.is_mod:
            return
        
        users: set = ctx.users
        res: str = ""
        for user in users:
            if re.match(regex, user.name, re.MULTILINE | re.IGNORECASE):
                res += f"{user.name} "
        
        await ctx.send(f"Run {ctx.prefix}please to ban: {res}")

    

    @commands.command()
    async def please(self, ctx: commands.Context):
        curr_bot = ctx.get_user(self.nick)
        if not curr_bot.is_mod:
            ctx.send("Cannot run ban commands as not a mod")
            return
        
        if not ctx.author.is_mod:
            return
        
        users: set = ctx.users
        to_ban: list = []
        user: Chatter
        for user in users:
            if re.match(regex, user.name, re.MULTILINE | re.IGNORECASE):
                to_ban.append(user.name)
        
        await self.ban_users(to_ban, ctx.channel)
        
        await ctx.send(f"Banned {len(to_ban)} users")


bot = Bot()

if __name__ == "__main__":
    bot.run()