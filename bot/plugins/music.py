import threading
import time
import pytube
import discord
import asyncio
from typing import Any, Callable, Optional
from attrs import define
from discord import app_commands, Interaction, FFmpegPCMAudio
from discord.enums import SpeakingState
from discord.opus import Encoder as OpusEncoder
from discord.ext import commands
from utils import (
    ListMenu,
    Queue,
    RepeatMode,
    bot_connected,
    to_ordinal,
    to_readable_time,
    user_and_bot_connected,
    user_connected
)
from dotenv import load_dotenv
load_dotenv()


FFMPEG_SOURCE_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}


class VideoNotFoundError(Exception):
    pass


class PlayerError(Exception):
    pass


@define(kw_only=True)
class Song:
    """
    Represents a song data type.

    Song objects are returned from `find_video` instead of being created manually.

    Attributes
    ----------
    title: `str`
        The title of the video
    channel_name: `str`
        The name of the video uploader
    thumbnail: `str`
        URL to the thumbnail image
    page_url: `str`
        URL to the `youtube.com/watch/` page
    url: `str`
        URL to the audio stream of the song
    duration: `int`
        Duration of the song in seconds
    """

    title: str
    channel_name: str
    thumbnail: str
    page_url: str
    url: str
    duration: int

    def __str__(self) -> str:
        return f'[{self.title}]({self.page_url})'

    def __repr__(self) -> str:
        return f'Song([{self.title}]({self.page_url}))'


def find_video(arg: str) -> Song:
    """Return Song object with info extracted from first video found."""
    results = pytube.Search(arg).results
    if not results:
        raise VideoNotFoundError(f'Couldn\'t find video from query {arg}')
    video = results[0]
    url = video.streams.get_audio_only().url

    return Song(
        title=video.title,
        channel_name=video.author,
        thumbnail=video.thumbnail_url,
        page_url=video.watch_url,
        url=url,
        duration=video.length
    )


class Player(threading.Thread):
    """
    Wrapper class for controlling playback to a voice channel.

    Attributes
    ----------
    voice_client: `discord.VoiceClient`
        The client of the bot's connection to a voice channel
    queue: `Queue[T]`
        An optional starting queue
    """

    DELAY = OpusEncoder.FRAME_LENGTH / 1000.0

    def __init__(
        self,
        voice_client: discord.VoiceClient,
        *,
        queue: Queue[Song] = Queue(),
        timeout: float = 5,
        on_error: Optional[Callable[[Optional[Exception]], Any]] = None
    ) -> None:
        threading.Thread.__init__(self)
        self.daemon = True
        self.client = voice_client.client
        self.voice_client = voice_client
        self.voice_client.encoder = OpusEncoder()
        self.queue = queue
        self.timeout = timeout

        self.source = None

        self._lock = threading.Lock()
        self._end = threading.Event()
        self._source_set = threading.Event()
        self._resumed = threading.Event()
        self._resumed.set()
        self._connected = voice_client._connected

        self.on_error = on_error

    def _do_run(self):
        self.loops = 0
        self._start = time.perf_counter()
        self._speak(SpeakingState.voice)

        play = self.voice_client.send_audio_packet

        for song in self.queue:
            self._source_set.set()
            self.source = FFmpegPCMAudio(song.url)
            self._end.clear()
            while not self._end.is_set():
                if not self._resumed.is_set():
                    self._resumed.wait()
                    continue

                if not self._connected.is_set():
                    self._connected.wait()
                    self.loops = 0
                    self._start = time.perf_counter()

                self.loops += 1

                data = self.source.read()
                if not data:
                    self._end.set()
                    break

                play(data, encode=not self.source.is_opus())
                next_time = self._start + self.DELAY * self.loops
                delay = max(0, self.DELAY + (next_time - time.perf_counter()))
                time.sleep(delay)

    def run(self):
        try:
            self._do_run()
        except Exception as e:
            self._err = e
        finally:
            self._call_error()
            self.source.cleanup()

    def _call_error(self):
        if self.on_error is None:
            raise self._err
        try:
            self.on_error(self._err)
        except Exception as err:
            raise PlayerError('Player on_error raised exception') from err

    def stop(self, blocking: bool = True) -> None:
        '''
        Stop playing audio.

        If blocking is True and the player is playing, block until the next source is gathered from queue
        '''
        if blocking and self.is_playing():
            self._source_set.clear()
        self._end.set()
        self._resumed.set()
        self._speak(SpeakingState.none)
        self._source_set.wait()

    def pause(self, *, update_speaking: bool = True) -> None:
        self._resumed.clear()
        if update_speaking:
            self._speak(SpeakingState.none)

    def resume(self, *, update_speaking: bool = True) -> None:
        self.loops = 0
        self._start = time.perf_counter()
        self._resumed.set()
        if update_speaking:
            self._speak(SpeakingState.voice)

    def is_playing(self) -> bool:
        return self.source is not None and self._resumed.is_set() and not self._end.is_set()

    def is_paused(self) -> bool:
        return not self._end.is_set() and not self._resumed.is_set()

    def _speak(self, speaking: SpeakingState):
        asyncio.run_coroutine_threadsafe(
            self.voice_client.ws.speak(speaking), self.client.loop)


class Music(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.players: dict[int, Player] = {}

    async def join_vc(self, vc: discord.VoiceChannel | discord.StageChannel) -> Player:
        """Join a voice channel."""
        voice_client: discord.VoiceClient = await vc.connect(self_deaf=True)
        self.players[voice_client.guild.id] = player = Player(voice_client)
        return player

    @app_commands.command(name='join')
    @app_commands.guild_only()
    @user_connected()
    async def _join(self, interaction: Interaction) -> None:
        """Join your channel"""
        player = self.players.get(id, None)
        user = interaction.user
        if player is None:
            await self.join_vc(user.voice.channel)
            await interaction.response.send_message('Joining your voice channel', ephemeral=True)
            return
        elif player.voice_client.channel == interaction.user.voice.channel:
            await interaction.response.send_message('Already in your channel', ephemeral=True)
        else:
            # TODO: Swap channels menu, also don't lol and shid
            pass

    @app_commands.command(name='leave')
    @app_commands.guild_only()
    async def _leave(self, interaction: Interaction) -> None:
        """Leave the channel and remove the queue"""
        player = self.players[interaction.guild_id]
        await player.leave()
        await interaction.response.send_message('Leaving')
        player = self.players[interaction.guild_id]
        player.queue.clear()
        del self.players[interaction.guild_id]

    @app_commands.command(name='add')
    @app_commands.describe(query='What to search for')
    @app_commands.guild_only()
    @user_connected()
    async def _add(self, interaction: Interaction, query: str) -> None:
        """Add a song to the queue and start playing if not already started"""
        await interaction.response.defer()
        player = self.players.get(interaction.guild_id, None)
        if player is None:
            player = await self.join_vc(interaction.user.voice.channel)
        try:
            song = find_video(query)
        except VideoNotFoundError:
            await interaction.edit_original_message(
                content=f'Couldn\'t find any videos from query `{query}`'
            )
            return
        player.queue.append(song)
        if not player.is_playing():
            player.start()
        await interaction.edit_original_message(content=f'Added `{song.title}` to queue')

    @app_commands.command(name='loop')
    @app_commands.describe(mode='Looping mode')
    @app_commands.guild_only()
    @user_and_bot_connected()
    async def _loop(self, interaction: Interaction, mode: RepeatMode) -> None:
        """Set the looping mode"""
        player = self.players[interaction.guild_id]
        player.queue.repeat = mode
        await interaction.response.send_message(f'Looping set to `{mode.value}`')
        if player.queue and not player.voice_client.is_playing():
            player.start()

    @app_commands.command(name='shuffle')
    @app_commands.guild_only()
    @user_and_bot_connected()
    async def _shuffle(self, interaction: Interaction) -> None:
        """Shuffle the queue"""
        player = self.players[interaction.guild_id]
        player.queue.shuffle()
        await interaction.response.send_message('Shuffled the queue')

    @app_commands.command(name='queue')
    @app_commands.guild_only()
    @bot_connected()
    async def _queue(self, interaction: Interaction) -> None:
        """Sends an embed with the queue list"""
        player = self.players[interaction.guild_id]
        if not player.queue:
            await interaction.response.send_message('Nothing in queue')
            return
        songs = [
            f'**{index}. **{song}  {to_readable_time(song.duration)}'
            for index, song in enumerate(player.queue.items, start=1)
        ]
        m = ListMenu(
            items=songs,
            title='Queue',
            description='based',
            owner=interaction.user
        )
        await m.start(interaction)

    @app_commands.command(name='current')
    @app_commands.guild_only()
    @bot_connected()
    async def _current(self, interaction: Interaction):
        """Currently playing song"""
        player = self.players[interaction.guild_id]
        if not player.queue:
            await interaction.response.send_message('Nothing in queue')
            return
        q = player.queue
        index, song = q.index, q.current
        description = f'{song}\nDuration: {to_readable_time(song.duration)}\n{to_ordinal(index + 1)} in queue'
        embed = discord.Embed(
            title='Currently playing',
            description=description,
        ).set_thumbnail(url=song.thumbnail)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='skip')
    @app_commands.describe(offset='How far to skip')
    @app_commands.guild_only()
    @user_and_bot_connected()
    async def _skip(self, interaction: Interaction, offset: int = 1) -> None:
        """Skip a certain number of songs, negative values allowed"""
        player = self.players[interaction.guild_id]
        player.queue.skip(offset)
        player.stop()
        song = player.queue.current
        await interaction.response.send_message(f'Skipped to `{song.title}`!')

    @app_commands.command(name='jump')
    @app_commands.describe(position='The position in queue to jump to')
    @app_commands.guild_only()
    @user_and_bot_connected()
    async def _jump(self, interaction: Interaction, position: int) -> None:
        """Jump to a certain position in the queue"""
        player = self.players[interaction.guild_id]
        try:
            player.queue.jump(position - 1)
        except ValueError:
            await interaction.response.send_message(
                f'Position {position} is out of range of the queue'
            )
            return
        player.stop()
        song = player.queue.current
        await interaction.response.send_message(f'Jumped to `{song.title}`')

    @app_commands.command(name='pause')
    @app_commands.guild_only()
    @user_and_bot_connected()
    async def _pause(self, interaction: Interaction):
        """Pause playback"""
        player = self.players[interaction.guild_id]
        player.voice_client.pause()
        await interaction.response.send_message('Paused')

    @app_commands.command(name='resume')
    @app_commands.guild_only()
    @user_and_bot_connected()
    async def _resume(self, interaction: Interaction):
        """Resume playback"""
        player = self.players[interaction.guild_id]
        player.voice_client.resume()
        await interaction.response.send_message('Resumed')

    @app_commands.command(name='remove')
    @app_commands.describe(position='Position of the song to remove, removes the current song if not given')
    @app_commands.guild_only()
    @user_and_bot_connected()
    async def _remove(self, interaction: Interaction, position: int = None):
        """Removes a song from the queue, removes the current song if called without argument"""
        player = self.players[interaction.guild_id]
        if position is None:
            position = player.queue.index + 1
        if position not in range(len(player.queue) + 1):
            await interaction.response.send_message(
                f'Position {position} is outside the range of the queue'
            )
            return
        removed = player.queue.pop(position - 1)
        await interaction.response.send_message(f'Removed `{removed.title}`')

    @app_commands.command(name='clear')
    @app_commands.guild_only()
    @user_and_bot_connected()
    async def _clear(self, interaction: Interaction):
        """Clear the queue"""
        player = self.players[interaction.guild_id]
        player.queue.clear()
        await interaction.response.send_message('Cleared the queue')

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceClient,
        after: discord.VoiceClient
    ):
        if member.bot:
            if member == member.guild.me and after is None:
                del self.players[member.guild.id]
            return
        player = self.players.get(member.guild.id, None)
        if player is None:
            return
        if before is None and after is not None:
            if after == member.guild.me.voice:
                await player.stop_timeout()
                return
        members = before.channel.members
        if all(member.bot for member in members):
            await player.start_timeout()


async def setup(client: commands.Bot, guilds: list[int]) -> None:
    await client.add_cog(
        Music(client),
        guilds=guilds
    )


async def teardown(client: commands.Bot, guilds: list[int]) -> None:
    await client.remove_cog('Music', guilds=guilds)
