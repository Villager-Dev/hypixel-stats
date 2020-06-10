import arrow
import discord
from discord.ext import commands


class Guild(commands.Cog):

    def __init__(self, bot: commands.Bot):
        """basic initalization of the guild cog"""

        self.bot = bot
        self.cache = self.bot.get_cog("Cache")

    @commands.command(name="guild", aliases=["g"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def guild(self, ctx, *, guild_name):
        await ctx.trigger_typing()

        guild_id = await self.cache.get_guild_id_from_name(guild_name)
        g = await self.cache.get_guild(guild_id)

        author = discord.utils.escape_markdown(g.NAME)

        desc = g.DESCRIPTION
        if desc is None:
            embed = discord.Embed(color=self.bot.cc)
        else:
            length = len(author) + 2
            embed = discord.Embed(color=self.bot.cc,
                                  description='\n'.join(
                                      desc[i:i + len(length) if len(length) > 30 else 30] for i in
                                      range(0, len(desc), len(author) + 2)))

        member_count = len(g.MEMBERS)
        coins = g.COINS
        xp = g.EXP
        tag = g.TAG
        created = arrow.Arrow.fromtimestamp(g.CREATED / 1000).humanize()

        embed.set_author(name=author)
        embed.add_field(name="Members", value=member_count, inline=True)
        embed.add_field(name="Tag", value=tag, inline=True)
        embed.add_field(name="\uFEFF", value=f"\uFEFF")
        embed.add_field(name="Coins", value=coins, inline=True)
        embed.add_field(name="XP", value=xp, inline=True)
        embed.add_field(name="\uFEFF", value=f"\uFEFF")
        embed.add_field(name="Created", value=created, inline=False)

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Guild(bot))
