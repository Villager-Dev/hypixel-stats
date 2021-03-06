import arrow
import asyncio
import base64
import concurrent.futures
import discord
from discord.ext import commands
from functools import partial
from math import floor, ceil
from nbt import *
from os import remove
from random import randint


class NoStatError(Exception):
    """Raised when a given player doesn't have a certain statistic"""

    def __init__(self):
        self.msg = "This user doesn't have that stat!"

    def __str__(self):
        return self.msg


class SkyBlock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.cache = self.bot.get_cog("Cache")
        self.db = self.bot.get_cog("Database")

        self.embed = discord.Embed(color=discord.Color.gold())

    def get_nbt(self, data):
        b64 = data["inv_armor"]["data"]
        bytes = base64.b64decode(b64)
        fname = f"tmp/{arrow.utcnow().timestamp}.{randint(10000, 99999)}.nbt"
        with open(fname, "wb") as f:
            f.write(bytes)
        nbt_data = nbt.NBTFile(fname, "rb")
        remove(fname)
        return nbt_data

    async def get_armor(self, uuid, profile, user_island_stats):
        uuid = str(uuid) + str(profile)

        cached_armor = self.cache.armor_cache.get(uuid)
        if cached_armor is not None:
            return cached_armor

        with concurrent.futures.ThreadPoolExecutor() as pool:
            get_nbt_partial = partial(self.get_nbt, user_island_stats)
            try:
                armor = await self.bot.loop.run_in_executor(pool, get_nbt_partial)
            except KeyError:
                return "No Armor"

        armor = [
            armor['i'][3].get('tag')['display']['Name'] if armor['i'][3].get('tag') is not None else None,
            # Helmet
            armor['i'][2].get('tag')['display']['Name'] if armor['i'][2].get('tag') is not None else None,
            # Chestplate
            armor['i'][1].get('tag')['display']['Name'] if armor['i'][1].get('tag') is not None else None,
            # Leggings
            armor['i'][0].get('tag')['display']['Name'] if armor['i'][0].get('tag') is not None else None,
            # Boots
        ]

        def filter(piece):
            if piece is None: return
            cleaned = ""
            for i in range(1, len(piece), 1):
                if piece[i - 1] != "§" and piece[i] != "§":
                    cleaned += piece[i]
            return cleaned

        armor = [filter(piece) for piece in armor]

        for i in range(0, 5, 1):
            try:
                armor.pop(armor.index(None))
            except Exception:
                break

        final_armor = ("`" + "`\n`".join(armor) + "`") if len(armor) > 0 else "No Armor"

        self.cache.armor_cache[uuid] = final_armor

        return final_armor

    @commands.command(name="skyblock", aliases=["sb"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def skyblock(self, ctx, player=None):
        if player is None:
            player = await self.db.get_linked_account_via_id(ctx.author.id)
            if player is not None:
                player = player[1]
            else:
                await ctx.send(
                    embed=discord.Embed(color=await self.bot.cc(),
                                        description=f"You need to link your account to do this!\n"
                                                    f"Do `{ctx.prefix}link <mc_username>` to link your account!"))
                return

        def author_check(message):  # Basic check to make sure author and other stuff is proper right
            return message.author == ctx.message.author and ctx.guild == message.guild and ctx.channel == message.channel

        async with ctx.typing():  # Fetch player from cache or api
            p = await self.cache.get_player(player)

            head = await self.cache.get_player_head(player)

        try:
            skyblock = p.STATS["SkyBlock"]
        except KeyError:
            raise NoStatError
        except TypeError:
            raise NoStatError

        profiles = list(skyblock.get("profiles"))

        if len(profiles) == 0:
            await ctx.send(
                embed=discord.Embed(color=await self.bot.cc(), description="This user doesn't have any islands!"))
            return

        profile_names = f"Choose one with the provided indexes:\n\n"

        for profile_id in profiles:
            profile_names += f'`{profiles.index(profile_id) + 1}.` **{skyblock["profiles"][profile_id].get("cute_name")}** ' \
                             f'[`{skyblock["profiles"][profile_id].get("profile_id")}`]\n'
        picker_embed = discord.Embed(color=await self.bot.cc(ctx.author.id), description=profile_names)
        picker_embed.set_author(name=f"{p.DISPLAY_NAME}'s SkyBlock Islands:", icon_url=head)
        picker_embed.set_footer(text="Just send one of the above numbers!")
        await ctx.send(embed=picker_embed)

        valid = False

        try:
            for i in range(0, 3, 1):
                index = await self.bot.wait_for('message', check=author_check, timeout=20)

                try:
                    index = int(index.content)
                except ValueError:
                    await ctx.send(
                        embed=discord.Embed(color=await self.bot.cc(ctx.author.id),
                                            description="That's not a valid index!"))
                else:
                    if index > len(profiles) or index <= 0:
                        await ctx.send(
                            embed=discord.Embed(color=await self.bot.cc(ctx.author.id),
                                                description="That's not a valid index!"))
                    else:
                        valid = True
                        break
            if not valid:
                await ctx.send(embed=discord.Embed(color=await self.bot.cc(ctx.author.id),
                                                   description="The command was canceled."))
                return
        except asyncio.TimeoutError:
            return

        base = skyblock['profiles'][profiles[index - 1]]
        profile_id = base["profile_id"]

        async with ctx.typing():
            stats = await self.cache.get_skyblock_stats(profile_id)

        if stats is None:
            await ctx.send(embed=discord.Embed(color=await self.bot.cc(),
                                               description="The bot doesn't have sufficient data to show this!"))
            return

        members = []

        for member in list(stats.get('members', [])):
            if member == profile_id:
                members.append(f"**{discord.utils.escape_markdown(await self.cache.get_player_name(member))}**")
            else:
                members.append(discord.utils.escape_markdown(await self.cache.get_player_name(member)))

        if len(members) > 3:
            members = [f"**{p.DISPLAY_NAME}**", f"{len(members) - 1} others"]

        coop = False
        if len(members) > 1:
            coop = True

        user_island_stats = stats["members"].get(p.UUID)

        if user_island_stats.get("stats") is None:
            await ctx.send(embed=discord.Embed(color=await self.bot.cc(ctx.author.id),
                                               description="The bot doesn't have sufficient data to show this island!"))
            return

        armor = await self.get_armor(p.UUID, base, user_island_stats)

        embed = self.embed.copy()
        embed.color = await self.bot.cc(ctx.author.id)

        embed.set_author(name=f"{p.DISPLAY_NAME}'s Skyblock Stats", icon_url=head)

        embed.description = f'**{base.get("cute_name")}** - [``{profile_id}``]'

        embed.add_field(name="Co-Op", value=coop)
        embed.add_field(name="Members", value=', '.join(members))
        embed.add_field(name="First Join",
                        value=arrow.Arrow.fromtimestamp(user_island_stats.get("first_join", 0) / 1000).humanize())

        embed.add_field(name="Coin Purse", value=ceil(user_island_stats.get('coin_purse', 0)))
        embed.add_field(name="Kills", value=ceil(user_island_stats['stats'].get('kills', 0)))
        embed.add_field(name="Deaths", value=floor(user_island_stats['stats'].get('deaths', 0)))

        embed.add_field(name="Void Deaths", value=floor(user_island_stats['stats'].get("deaths_void", 0)))
        embed.add_field(name="Fairy Souls", value=user_island_stats.get('fairy_souls', 0))
        embed.add_field(name="Fairy Souls Collected", value=user_island_stats.get('fairy_souls_collected', 0))

        embed.add_field(name="Armor", value=armor)

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(SkyBlock(bot))
