import discord
from contextlib import suppress
from discord import FFmpegPCMAudio, app_commands
from utils import (
    bot_is_connected,
    find_video,
    user_is_connected,
    readable_time,
    RepeatMode,
    ListMenu,
    Queue,
    Song
)


class Player:
    '''
    Wrapper class for controlling playback to a voice channel

    ----------
    Attributes
    ----------
    voice_client: `discord.VoiceClient`
        The client of the bot's connection to a voice channel
    queue: Optional[`Queue[T]`]
        An optional starting queue
    '''

    def __init__(self, voice_client: discord.VoiceClient, *, queue: Queue[Song] = Queue()):
        self._vc = voice_client
        self.queue = queue

    @property
    def voice_client(self) -> discord.VoiceClient:
        return self._vc

    def _after(self, e: Exception | None):
        if e is not None:
            print(e)
        self.start()

    def start(self) -> None:
        try:
            song = next(self.queue)
        except StopIteration:
            return
        source = FFmpegPCMAudio(song.url)
        with suppress(discord.errors.ClientException):
            self._vc.play(source, after=self._after)

    def stop(self) -> None:
        self._vc.stop()


players: dict[int, Player] = {}


async def join_vc(vc: discord.VoiceChannel | discord.StageChannel, guild_id: int) -> Player:
    voice_client: discord.VoiceClient = await vc.connect(self_deaf=True)
    players[guild_id] = player = Player(voice_client)
    return player


@app_commands.command(name='join')
@user_is_connected()
async def _join(interaction: discord.Interaction) -> None:
    id: int = interaction.guild_id
    player = players.get(id, None)
    user_voice: discord.VoiceClient = interaction.user
    if player is None:
        await join_vc(user_voice.channel, id)
        await interaction.response.send_message('Joining your voice channel', ephemeral=True)
        return

    if player.voice_client.channel == interaction.user.voice.channel:
        await interaction.response.send_message('Already in your channel', ephemeral=True)
    else:
        # TODO: Swap channels menu, also don't lol and shid
        pass


@app_commands.command(name='leave')
@bot_is_connected()
@user_is_connected()
async def _leave(interaction: discord.Interaction) -> None:
    await interaction.guild.voice_client.disconnect()
    await interaction.response.send_message('Leaving')
    # TODO: player cleanup in events


@app_commands.command(name='add')
@app_commands.describe(query='What to search for')
@user_is_connected()
async def _add(interaction: discord.Interaction, query: str) -> None:
    await interaction.response.defer()
    player = players.get(interaction.guild_id, None)
    if player is None:
        player = await join_vc(interaction.user.voice.channel, interaction.guild_id)

    song = find_video(query)
    player.queue.append(song)
    if not player.voice_client.is_playing():
        player.start()
    await interaction.edit_original_message(content=f'Added `{song.title}` to queue')


@app_commands.command(name='loop')
@app_commands.describe(mode='Looping mode')
@user_is_connected()
@bot_is_connected()
async def _loop(interaction: discord.Interaction, mode: RepeatMode) -> None:
    player = players[interaction.guild_id]
    player.queue.repeat = mode
    await interaction.response.send_message(f'Looping set to `{mode.value}`')


@app_commands.command(name='forceskip')
@app_commands.describe(offset='How far to skip')
@bot_is_connected()
@user_is_connected()
async def _fskip(interaction: discord.Interaction, offset: int = 1) -> None:
    player = players[interaction.guild_id]
    player.queue.index += offset - 1
    await interaction.response.send_message('Skipped!')
    player.stop()


@app_commands.command(name='forcejump')
@app_commands.describe(position='The position in queue to jump to (wraps around if larger than maximum)')
@bot_is_connected()
@user_is_connected()
async def _fjump(interaction: discord.Interaction, position: int = 1) -> None:
    player = players[interaction.guild_id]
    player.queue.index = position - 1
    await interaction.response.send_message(f'Jumped to {position}')
    player.stop()


@app_commands.command(name='queue')
@bot_is_connected()
async def _queue(interaction: discord.Interaction) -> None:
    # don't fucking ask what this shit is, because it doesn't even work due to discord
    player = players[interaction.guild_id]
    longest_title = max(player.queue.items, key=lambda song: len(song.title))
    longest_duration = max(player.queue.items, key=lambda song: len(
        readable_time(song.duration)))
    title_width = max(20, len(longest_title.title) + 10)
    duration_width = len(readable_time(longest_duration.duration)) + 10
    songs = [
        f'{song!s:{title_width}}{readable_time(song.duration):>{duration_width}}'
        for song in player.queue.items
    ]
    m = ListMenu(
        items=songs,
        title='Queue',
        description='based'
    )
    await m.start(interaction)
