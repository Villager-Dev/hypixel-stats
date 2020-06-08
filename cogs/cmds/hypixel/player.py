from discord.ext import commands
import discord
import aiopypixel


class Player(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        self.cache = self.bot.get_cog("Cache")

    @commands.command(name="friends", aliases=["pfriends", "playerfriends", "friendsof"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def player_friends(self, ctx, player):
        try:
            player_friends = await self.cache.get_player_friends(player)
        except aiopypixel.exceptions.exceptions.InvalidPlayerError:
            await ctx.send("That player is invalid or doesn't exist!")
        else:
            if not player_friends:
                await ctx.send(embed=discord.Embed(color=self.bot.cc, description=f"{player} doesn't have any friends! :cry:"))

            body = ""
            for friend in player_friends:
                body.append(f"{await self.cache.get_player_name(friend)}\n")

            embed = discord.Embed(color=self.bot.cc, title=f"__{player}'s friends__:", description=body)

            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Player(bot))
