import discord
from discord import app_commands


def user_is_connected():
    async def predicate(interaction: discord.Interaction) -> bool:
        user: discord.Member = interaction.user
        if user.voice is not None:
            return True
        await interaction.response.send_message('You are not connected to a voice channel', ephemeral=True)
        return False
    return app_commands.check(predicate)


def bot_is_connected():
    async def predicate(interaction: discord.Interaction) -> bool:
        # TODO: check bot connection without needing user's voice
        user: discord.Member = interaction.user
        states = user.voice.channel.voice_states
        if interaction.client.user.id in states:
            return True
        await interaction.response.send_message('I am not in your channel', ephemeral=True)
        return False
    return app_commands.check(predicate)
