import os
import pytube
import asyncio
import discord
from random import shuffle
from attrs import define
from googleapiclient.discovery import build
from discord import FFmpegPCMAudio, app_commands
from utils import (
    readable_time,
    user_and_bot_connected,
    user_connected,
    RepeatMode,
    ListMenu,
    Queue
)
from dotenv import load_dotenv
load_dotenv()


AUDIO_SOURCE_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
YOUTUBE_TOKEN = os.environ.get('YOUTUBE_TOKEN')
if YOUTUBE_TOKEN is None:
    raise ValueError('No YOUTUBE_TOKEN found in environment')


class VideoNotFound(Exception):
    pass


@define(kw_only=True)
class Song:
    title: str
    channel_name: int
    thumbnail: str
    page_url: str
    url: str
    duration: int

    def __str__(self) -> str:
        return f'[{self.title}]({self.page_url})'

    def __repr__(self) -> str:
        return f'Song([{self.title}]({self.page_url}))'


def find_video(arg: str) -> Song:
    '''Returns Song object with info extracted from first video found'''
    with build('youtube', 'v3', developerKey=YOUTUBE_TOKEN) as yt_service:
        request = yt_service.search().list(
            part='snippet',
            type='video',
            maxResults=1,
            q=arg
        )
        # wtf is the youtube api
        items = request.execute()['items']
        if not items:
            raise VideoNotFound(f'Found no videos with search argument: {arg}')
        video_id = items[0]['id']['videoId']

    video = pytube.YouTube(f'http://youtube.com/watch?v={video_id}')
    video.streams.get_audio_only().url

    # pprint(video, best_audio)
    return Song(
        title=video.title,
        channel_name=video.author,
        thumbnail=video.thumbnail_url,
        page_url=video.watch_url,
        url=video.streams.get_audio_only().url,
        duration=video.length
    )


if __name__ == '__main__':
    find_video('amogus')


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
        source = FFmpegPCMAudio(song.url, **AUDIO_SOURCE_OPTIONS)
        self._vc.play(source, after=self._after)

    async def start_timeout(self) -> None:
        self._dc_flag = True
        await asyncio.sleep(self._dc_timeout)
        if self._dc_flag and self._vc.is_connected():
            await self.leave()

    async def leave(self) -> None:
        self._vc.stop()
        await self._vc.disconnect()


players: dict[int, Player] = {}


async def join_vc(vc: discord.VoiceChannel | discord.StageChannel) -> Player:
    voice_client: discord.VoiceClient = await vc.connect(self_deaf=True)
    players[voice_client.guild.id] = player = Player(voice_client)
    return player


@app_commands.command(name='join')
@app_commands.guild_only()
@user_connected()
async def _join(interaction: discord.Interaction) -> None:
    player = players.get(id, None)
    user = interaction.user
    if player is None:
        await join_vc(user.voice.channel)
        await interaction.response.send_message('Joining your voice channel', ephemeral=True)
        return
    if player.voice_client.channel == interaction.user.voice.channel:
        await interaction.response.send_message('Already in your channel', ephemeral=True)
    else:
        # TODO: Swap channels menu, also don't lol and shid
        pass


@app_commands.command(name='leave')
@app_commands.guild_only()
async def _leave(interaction: discord.Interaction) -> None:
    player = players[interaction.guild_id]
    await player.leave()
    await interaction.response.send_message('Leaving')
    del players[interaction.guild_id]


@app_commands.command(name='add')
@app_commands.describe(query='What to search for')
@app_commands.guild_only()
@user_connected()
async def _add(interaction: discord.Interaction, query: str) -> None:
    await interaction.response.defer()
    player = players.get(interaction.guild_id, None)
    if player is None:
        player = await join_vc(interaction.user.voice.channel)
    try:
        song = find_video(query)
    except VideoNotFound:
        await interaction.edit_original_message(f'Couldn\'t find any videos from query `{query}`')
    player.queue.append(song)
    if not player.voice_client.is_playing():
        await player.start()
    await interaction.edit_original_message(content=f'Added `{song.title}` to queue')


@app_commands.command(name='loop')
@app_commands.describe(mode='Looping mode')
@app_commands.guild_only()
@user_and_bot_connected()
async def _loop(interaction: discord.Interaction, mode: RepeatMode) -> None:
    player = players[interaction.guild_id]
    player.queue.repeat = mode
    await interaction.response.send_message(f'Looping set to `{mode.value}`')
    if player.queue:
        if mode != RepeatMode.Off:
            if not player.voice_client.is_playing():
                await player.start()


@app_commands.command(name='shuffle')
@app_commands.guild_only()
@user_and_bot_connected()
async def _shuffle(interaction: discord.Interaction) -> None:
    player = players[interaction.guild_id]
    shuffle(player.queue)
    await interaction.response.send_message('Shuffled the queue')


@app_commands.command(name='queue')
@app_commands.guild_only()
@user_and_bot_connected()
async def _queue(interaction: discord.Interaction) -> None:
    player = players[interaction.guild_id]
    songs = [
        f'**{index}. **{song!s}  {readable_time(song.duration)}'
        for index, song in enumerate(player.queue.items)
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
@user_and_bot_connected()
async def _fskip(interaction: discord.Interaction, offset: int = 1) -> None:
    player = players[interaction.guild_id]
    player.queue.index += offset - 1
    await interaction.response.send_message('Skipped!')
    player.stop()


@app_commands.command(name='forcejump')
@app_commands.describe(position='The position in queue to jump to (wraps around if larger than maximum)')
@app_commands.guild_only()
@user_and_bot_connected()
async def _fjump(interaction: discord.Interaction, position: int = 1) -> None:
    player = players[interaction.guild_id]
    player.queue.index = position - 1
    await interaction.response.send_message(f'Jumped to {position}')
    player.stop()


@app_commands.command(name='pause')
@app_commands.guild_only()
@user_and_bot_connected()
async def _pause(interaction: discord.Interaction):
    player = players[interaction.guild_id]
    player.voice_client.pause()
    await interaction.response.send_message('Paused')


@app_commands.command(name='resume')
@app_commands.guild_only()
@user_and_bot_connected()
async def _resume(interaction: discord.Interaction):
    player = players[interaction.guild_id]
    player.voice_client.resume()
    await interaction.response.send_message('Resumed')
