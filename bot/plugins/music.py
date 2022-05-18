import discord
import asyncio
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
    queue: `Queue[T]`
        An optional starting queue
    '''

    def __init__(
        self,
        voice_client: discord.VoiceClient,
        *,
        queue: Queue[Song] = Queue(),
        timeout: float = 5
    ) -> None:
        self._vc = voice_client
        self._loop = voice_client.loop
        self.queue = queue
        self._dc_timeout = timeout
        self._dc_flag = False

    @property
    def voice_client(self) -> discord.VoiceClient:
        return self._vc

    def _after(self, e: Exception | None):
        if e is not None:
            raise e
        self._loop.create_task(self.start())

    async def start(self) -> None:
        try:
            song = next(self.queue)
            self._dc_flag = False
        except StopIteration:
            await self.start_timeout()
            return
        source = FFmpegPCMAudio(song.url)
        self._vc.play(source, after=self._after)

    async def start_timeout(self) -> None:
        self._dc_flag = True
        await asyncio.sleep(self._dc_timeout)
        if self._dc_flag and self._vc.is_connected():
            await self.leave()

    def stop(self) -> None:
        self._vc.stop()

    async def leave(self) -> None:
        await self._vc.disconnect()
        del players[self._vc.guild.id]


players: dict[int, Player] = {}


async def join_vc(vc: discord.VoiceChannel | discord.StageChannel) -> Player:
    voice_client: discord.VoiceClient = await vc.connect(self_deaf=True)
    players[voice_client.guild.id] = player = Player(voice_client)
    return player


@app_commands.command(name='join')
@app_commands.guild_only()
@user_is_connected()
async def _join(interaction: discord.Interaction) -> None:
    player = players.get(id, None)
    user_voice: discord.VoiceClient = interaction.user
    if player is None:
        await join_vc(user_voice.channel)
        await interaction.response.send_message('Joining your voice channel', ephemeral=True)
        return

    if player.voice_client.channel == interaction.user.voice.channel:
        await interaction.response.send_message('Already in your channel', ephemeral=True)
    else:
        # TODO: Swap channels menu, also don't lol and shid
        pass


@app_commands.command(name='leave')
@app_commands.guild_only()
@bot_is_connected()
@user_is_connected()
async def _leave(interaction: discord.Interaction) -> None:
    player = players[interaction.guild_id]
    player.leave()
    await interaction.response.send_message('Leaving')
    del players[interaction.guild_id]


@app_commands.command(name='add')
@app_commands.describe(query='What to search for')
@app_commands.guild_only()
@user_is_connected()
async def _add(interaction: discord.Interaction, query: str) -> None:
    await interaction.response.defer()
    player = players.get(interaction.guild_id, None)
    if player is None:
        player = await join_vc(interaction.user.voice.channel)

    song = find_video(query)
    player.queue.append(song)
    if not player.voice_client.is_playing():
        await player.start()
    await interaction.edit_original_message(content=f'Added `{song.title}` to queue')


@app_commands.command(name='loop')
@app_commands.describe(mode='Looping mode')
@app_commands.guild_only()
@bot_is_connected()
@user_is_connected()
async def _loop(interaction: discord.Interaction, mode: RepeatMode) -> None:
    player = players[interaction.guild_id]
    player.queue.repeat = mode
    if mode != RepeatMode.Off and not player.voice_client.is_playing():
        await player.start()
    await interaction.response.send_message(f'Looping set to `{mode.value}`')


@app_commands.command(name='queue')
@app_commands.guild_only()
@bot_is_connected()
@user_is_connected()
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


@app_commands.command(name='forceskip')
@app_commands.describe(offset='How far to skip')
@app_commands.guild_only()
@bot_is_connected()
@user_is_connected()
async def _fskip(interaction: discord.Interaction, offset: int = 1) -> None:
    player = players[interaction.guild_id]
    player.queue.index += offset - 1
    await interaction.response.send_message('Skipped!')
    player.stop()


@app_commands.command(name='forcejump')
@app_commands.describe(position='The position in queue to jump to (wraps around if larger than maximum)')
@app_commands.guild_only()
@bot_is_connected()
@user_is_connected()
async def _fjump(interaction: discord.Interaction, position: int = 1) -> None:
    player = players[interaction.guild_id]
    player.queue.index = position - 1
    await interaction.response.send_message(f'Jumped to {position}')
    player.stop()


@app_commands.command(name='pause')
@app_commands.guild_only()
@bot_is_connected()
@user_is_connected()
async def _pause(interaction: discord.Interaction):
    player = players[interaction.guild_id]
    player.voice_client.pause()
    await interaction.response.send_message('Paused')


@app_commands.command(name='resume')
@app_commands.guild_only()
@bot_is_connected()
@user_is_connected()
async def _resume(interaction: discord.Interaction):
    player = players[interaction.guild_id]
    player.voice_client.resume()
    await interaction.response.send_message('Resumed')
