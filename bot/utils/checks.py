from discord import app_commands, Interaction


__all__ = [
    'user_and_bot_connected',
    'user_connected',
    'bot_connected'
]


def _bot_connected(interaction: Interaction) -> bool:
    # TODO: check bot connection without needing user's voice
    return interaction.guild.me.voice is not None


def _user_connected(interaction: Interaction) -> bool:
    return interaction.user.voice is not None


def user_and_bot_connected():
    async def predicate(interaction: Interaction) -> bool:
        user_bool = _user_connected(interaction)
        bot_bool = _bot_connected(interaction)
        msg = ''
        if not user_bool:
            msg = 'You are not connected to a voice channel\n'
        if not bot_bool:
            msg += '\nI\'m not connected to your voice channel'
        if msg:
            await interaction.response.send_message(msg, ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)


def user_connected():
    async def predicate(interaction: Interaction) -> bool:
        if not _user_connected(interaction):
            await interaction.response.send_message('You are not connected to a voice channel')
            return False
        return True
    return app_commands.check(predicate)


def bot_connected():
    async def predicate(interaction: Interaction) -> bool:
        if not _user_connected(interaction):
            await interaction.response.send_message('I\'m not connected to your voice channel')
            return False
        return True
    return app_commands.check(predicate)
