from discord import app_commands, Interaction


__all__ = [
    'user_and_bot_connected',
    'user_connected',
    'bot_connected'
]


def user_and_bot_connected():
    """Fails if either the user or bot aren't connected to the same channel."""
    async def predicate(interaction: Interaction) -> bool:
        user_voice = interaction.user.voice
        bot_voice = interaction.guild.me.voice

        msg = ''
        if user_voice is None:
            msg = 'You are not connected to a voice channel\n'
        if bot_voice is None or bot_voice.channel != user_voice.channel:
            msg += '\nI\'m not connected to your voice channel'
        if msg:
            await interaction.response.send_message(msg, ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)


def user_connected():
    """Fails if the user is not connected to a voice channel."""
    async def predicate(interaction: Interaction) -> bool:
        if interaction.user.voice is None:
            await interaction.response.send_message(
                'You are not connected to a voice channel',
                ephemeral=True
            )
            return False
        return True
    return app_commands.check(predicate)


def bot_connected():
    """Fails if the bot is not connected to voice channel."""
    async def predicate(interaction: Interaction) -> bool:
        if interaction.guild.me.voice is None:
            await interaction.response.send_message(
                'I\'m not connected to a voice channel',
                ephemeral=True
            )
            return False
        return True
    return app_commands.check(predicate)
