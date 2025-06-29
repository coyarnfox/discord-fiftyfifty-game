import discord
from discord import app_commands
import random
import asyncio
import sqlite3
import os

discordbottoken = (
    os.environ["FIFTY_FIFTY_GAME_BOTTOKEN"]
)
applicationid = os.environ["FIFTY_FIFTY_GAME_APPLICATION_ID"]

intents = discord.Intents(messages=True)
client = discord.Client(intents=intents, applicationid=applicationid)
comtree = app_commands.CommandTree(client)


class gamestate:
    pass


class States:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._statedata = {}
        self._sqlite = sqlite3.connect("judge.db", timeout=10, autocommit=False)
        pass

    async def isactive(self, messageid):
        async with self._lock:
            try:
                cur = self._sqlite.cursor()
                cur.execute("INSERT INTO RETURNLOG (refid) VALUES (?);", (messageid,))
                cur.close()
                self._sqlite.commit()
            except Exception as e:
                return False
        return True

    async def getgamedata(self, messageid):
        async with self._lock:
            try:
                cur = self._sqlite.cursor()
                cur.execute(
                    "SELECT prob, choice FROM GAMESTATE WHERE id = ?;", (messageid,)
                )
                data = cur.fetchall()
                cur.close()
            except Exception as e:
                return None
        if len(data) == 0:
            return None
        prob: int = data[0][0]
        ans: str = data[0][1]
        return (prob, ans)

    async def setgamedata(self, messageid, prob, ans):
        async with self._lock:
            try:
                cur = self._sqlite.cursor()
                cur.execute(
                    "INSERT INTO GAMESTATE (id, prob, choice) VALUES (?,?,?);",
                    (messageid, prob, ans),
                )
                cur.close()
                self._sqlite.commit()
            except Exception as e:
                return False
        return True


class mainview(discord.ui.View):
    choice = ["赤", "緑"]

    def __init__(self):
        super().__init__(timeout=None)
        self.ans = random.choice(self.choice)

    @discord.ui.button(
        label="赤", custom_id="game_red_2", style=discord.ButtonStyle.red
    )
    async def gamered(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.judge(interaction, "赤")

    @discord.ui.button(
        label="緑", custom_id="game_green_2", style=discord.ButtonStyle.green
    )
    async def gamegreen(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.judge(interaction, "緑")

    async def judge(self, interaction: discord.Interaction, choice):
        assert interaction.message is not None
        assert interaction.channel is not None

        ch = interaction.channel
        

        mes: discord.Message = interaction.message
        print(f"ジャッジ対象メッセージ:{mes.id}")

        if not await states.isactive(mes.id):
            await interaction.response.send_message(
                "⚠️ほかの人が先に回答しています！⚠️", ephemeral=True
            )
            return

        ret = await states.getgamedata(mes.id)
        if ret is None:
            await interaction.response.send_message(
                "⚠️サーバエラーです⚠️", ephemeral=True
            )
            return
        prob = ret[0]
        ans = ret[1]

        emb = discord.Embed(
            colour=(
                discord.Colour.blurple()
                if choice == ans
                else discord.Colour.dark_magenta()
            )
        )
        emb.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url,
        )
        emb.add_field(name="確率", value=f"1/{prob}", inline=True)
        emb.add_field(name="選択", value=choice, inline=True)
        retmes = ""
        if choice == ans:
            retmes = "成功"
        else:
            retmes = "失敗"
            prob = 1
        emb.add_field(name="結果", value=retmes, inline=True)
        
        await mes.delete()
        await ch.send( # type: ignore
            embed=emb,
        )
        await self.makeview(interaction, prob)

    async def makeview(self, interaction: discord.Interaction, prob: int):

        newprob = prob * 2
        view = mainview()
        ic = await interaction.response.send_message(
            f"次の確率は 1/{newprob} です。", view=view
        )
        if type(ic.resource) == discord.InteractionMessage:
            resp = ic.message_id
        print(f"登録メッセージ:{resp}")
        await states.setgamedata(resp, newprob, view.ans)


@comtree.command()
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("pong!", ephemeral=True)


@comtree.command()
async def startview(interaction: discord.Interaction):
    view = mainview()
    await view.makeview(interaction, 1)


@client.event
async def on_ready():
    await comtree.sync()
    client.add_view(mainview())


states = States()
client.run(discordbottoken)
