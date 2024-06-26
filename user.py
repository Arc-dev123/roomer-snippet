import disnake
from disnake.ext import commands
import config

db = config.db

cur = config.cur

class User(commands.Cog):

  def __init__(self, bot: commands.Bot):
    self.bot = bot

  @commands.slash_command(name="create_room", description="Lets the user create a room")
  async def create_room(interaction: disnake.ApplicationCommandInteraction, name: str):
    await interaction.response.send_message("Please wait...", ephemeral=True)
    cur.execute("SELECT room_key FROM server WHERE server_id = %s", (str(interaction.guild_id),))
    role = cur.fetchone()[0]
    role = disnake.utils.get(interaction.guild.roles, id=role)
    if role.name in interaction.user.roles:
        for x in interaction.user.roles:
            print(x)
        await interaction.edit_original_response("Whoops! It seems like you do not have the room key! Ask your server admin to give you the key first!")
        return
    cur.execute("SELECT channel_id FROM member WHERE server_id = %s AND user_id = %s",
                (str(interaction.guild.id), str(interaction.user.id),))
    if cur.fetchone():
        await interaction.edit_original_response(
            "Whoops! Seems like you already have a room in this server. Use /delete_room to delete your room then try again!")
        return
    cur.execute("SELECT room_category FROM server WHERE server_id = %s", (str(interaction.guild_id),))
    r_cate = cur.fetchone()[0]
    r_cate = disnake.utils.get(interaction.guild.categories, id=r_cate)
    channel = await interaction.guild.create_text_channel(name=name, category=r_cate)

    cur.execute("INSERT INTO member VALUES (%s, %s, %s)",
                (str(interaction.user.id), str(interaction.guild.id), channel.id,))
    db.commit()
    cur.execute("SELECT * FROM user_stats WHERE user_id = %s", (str(interaction.user.id),))
    if not cur.fetchall():
        cur.execute("INSERT INTO user_stats VALUES (%s, %s, %s, %s)", (str(interaction.user.id), 0, 1, 0,))
        cur.execute("INSERT INTO member_inventory VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (str(interaction.user.id), 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,))
        db.commit()
    await channel.set_permissions(interaction.guild.default_role,
                                  read_message_history=False,
                                  read_messages=False
                                  )
    await channel.set_permissions(interaction.author,
                                  read_message_history=True,
                                  read_messages=True,
                                  send_messages=True
                                  )
    embed = disnake.Embed(
        title="Woohoo!",
        description=f"Welcome to your room, {interaction.user.mention}!"
    )
    embed.add_field(name="/add_user (USER ID)", value="This command can be used to add more members into your room!",
                    inline=False)
    embed.add_field(name="/remove_user (USER ID)", value="This command can be used to remove members from your room!",
                    inline=False)
    embed.add_field(name="/purge", value="Delete all messages from the channel!", inline=False)
    embed.add_field(name="/stats", value="This command can be used to check your stats!", inline=False)
    embed.add_field(name="/rewards", value="This command can be used to check your rewards!", inline=False)
    embed.add_field(name="/claim", value="This command can be used to claim your rewards!", inline=False)
    await channel.send(content=interaction.user.mention, embed=embed)
    await interaction.edit_original_response(f"Done, check out your room in <#{channel.id}>!")
    return

  @commands.slash_command(name="delete_room", description="Lets the user delete their room")
  async def delete_room(interaction: disnake.ApplicationCommandInteraction):
      await interaction.response.send_message("Please wait...", ephemeral=True)
      cur.execute("SELECT room_key FROM server WHERE server_id = %s", (str(interaction.guild_id),))
      role = cur.fetchone()[0]
      role = disnake.utils.get(interaction.guild.roles, id=role)
      if not role in interaction.user.roles:
          await interaction.edit_original_response(
              "Whoops! It seems like you do not have the room key! Ask your server admin to give you the key first!")
          return
      cur.execute("SELECT channel_id FROM member WHERE server_id = %s AND user_id = %s",
                  (str(interaction.guild.id), str(interaction.user.id),))
      if not cur.fetchone():
          await interaction.edit_original_response(
              "Whoops! Seems like you don't have a room in this server. Use /create_room to create a room first!")
          return
      cur.execute("SELECT channel_id FROM member WHERE user_id = %s AND server_id = %s",
                  (str(interaction.user.id), str(interaction.guild_id),))

      channel_id = cur.fetchone()[0]
      channel = disnake.utils.get(interaction.guild.channels, id=channel_id)
      await channel.delete()
      cur.execute("DELETE FROM member WHERE user_id = %s AND server_id = %s",
                  (str(interaction.user.id), str(interaction.guild_id),))
      db.commit()
      if interaction.channel_id == channel_id:
          await interaction.user.send("Done, your room has been deleted!")
      await interaction.edit_original_response("Done, your room has been deleted!")
      return

  @commands.slash_command(name="stats", description="Lets the user see their stats")
  async def stats(interaction: disnake.ApplicationCommandInteraction):
    cur.execute("SELECT * FROM server WHERE server_id = %s", (str(interaction.guild_id),))
    if not cur.fetchone():
        await interaction.edit_original_response("Whoops! It seems like the server didn't setup the bot yet... tell an administrator to set it up!")
        return
    cur.execute("SELECT xp, level FROM user_stats WHERE user_id = %s", (str(interaction.user.id),))
    info = cur.fetchone()
    if info == None:
      await interaction.response.send_message("You don't have any stats yet! Create a room first!", ephemeral=True)
      return
    embed = disnake.Embed(title=f"{interaction.author.name}'s **STATS:**", description=f"**XP:** {info[0]}/{25 * info[1]}\n\n**Level:** {info[1]}", color=disnake.Color.green())
    await interaction.response.send_message(embed=embed)

  @commands.slash_command(name="add_user", description="Lets the user to add more members into their group")
  async def add_user(interaction: disnake.ApplicationCommandInteraction, user: str):
    await interaction.response.send_message("Please wait...", ephemeral=True)
    cur.execute("SELECT room_key FROM server WHERE server_id = %s", (str(interaction.guild_id),))
    if not cur.fetchone():
        await interaction.edit_original_response(
            "Whoops! It seems like the server didn't setup the bot yet... tell an administrator to set it up!")
        return
    cur.execute("SELECT channel_id FROM member WHERE server_id = %s and user_id = %s", (str(interaction.guild_id), str(interaction.user.id),))
    channel_id = cur.fetchone()[0]
    channel = disnake.utils.get(interaction.guild.channels, id=channel_id)
    if channel_id:
      user = interaction.guild.get_member(int(user))
      if not user:
        await interaction.edit_original_response("Whoops! It seems like the user you mentioned does not exist!")
        return
      await channel.set_permissions(user,
                    read_message_history=True,
                    read_messages=True,
                    send_messages=True
      )
      await interaction.edit_original_response(f"Done, {user.mention} can now chat in <#{channel_id}>")
      await user.send(f"You can now chat in <#{channel_id}>!")
      return
    await interaction.edit_original_response("You haven't made a room yet! Create a room first!")

  @commands.slash_command(name="remove_user", description="Lets the user to remove members from their group")
  async def remove_user(interaction: disnake.ApplicationCommandInteraction, user: str):
    await interaction.response.send_message("Please wait...", ephemeral=True)
    cur.execute("SELECT room_key FROM server WHERE server_id = %s", (str(interaction.guild_id),))
    if not cur.fetchone():
        await interaction.edit_original_response("Whoops! It seems like the server didn't setup the bot yet... tell an administrator to set it up!")
        return
    cur.execute("SELECT channel_id FROM member WHERE server_id = %s and user_id = %s", (str(interaction.guild_id), str(interaction.user.id),))
    channel_id = cur.fetchone()[0]
    channel = disnake.utils.get(interaction.guild.channels, id=channel_id)
    if channel_id:
      user = interaction.guild.get_member(int(user))
      await channel.set_permissions(user,
                    read_message_history=False,
                    read_messages=False,
                    send_messages=False
      )
      await interaction.edit_original_response(f"Done, {user.mention} has been removed from chatting in <#{channel_id}>")
      await user.send(f"You have been removed from <#{channel_id}>!")
      return
    await interaction.edit_original_response("You haven't made a room yet! Create a room first!")

  @commands.slash_command(name="purge", description="Deletes all messages from the user's room")
  async def purge(interaction: disnake.ApplicationCommandInteraction):
      await interaction.response.send_message("Please wait...", ephemeral=True)
      cur.execute("SELECT room_key FROM server WHERE server_id = %s", (str(interaction.guild_id),))
      if not cur.fetchone():
          await interaction.edit_original_response(
              "Whoops! It seems like the server didn't setup the bot yet... tell an administrator to set it up!")
          return
      cur.execute("SELECT channel_id FROM member WHERE user_id = %s AND server_id = %s", (str(interaction.user.id), str(interaction.guild.id),))
      channel_id = cur.fetchone()[0]
      if not channel_id:
          await interaction.edit_original_response(
              "Whoops! Seems like you don't have a room in this server. Use /create_room to create a room first!")
          return
      channel = disnake.utils.get(interaction.guild.text_channels, id=channel_id)
      async for message in channel.history(limit=None):
          await message.delete()
      return

def setup(bot: commands.Bot):
  bot.add_cog(User(bot))
