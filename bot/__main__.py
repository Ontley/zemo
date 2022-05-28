import importlib
import os
import json
from types import ModuleType
from typing import Iterable, Sequence
import discord
from discord.ext import commands
from dotenv import load_dotenv
load_dotenv()


with open('bot/bot_info.json', 'r') as bot_info_json:
    guild_ids = json.load(bot_info_json)['guilds']
    GUILD_IDS = list(map(discord.Object, guild_ids))
PLUGINS_DIR = 'plugins'


class Bot(commands.Bot):
    @staticmethod
    def _get_plugins(directory: str) -> Iterable[ModuleType]:
        plugin_path = f'{os.getcwd()}\\bot\\{directory}'
        for dirpath, _, filenames in os.walk(plugin_path):
            if '__pycache__' == dirpath:
                continue
            for file in filenames:
                if file == '__init__.py' or not file.endswith('.py'):
                    continue
                ext_path = f'{dirpath}\\{file}'.replace('\\', '.')
                start = ext_path.find(directory)
                ext_path = ext_path[start: -3]
                yield importlib.import_module(ext_path)

    async def load_plugins(
        self,
        directory: str,
        *,
        guilds: Sequence[discord.Object]
    ) -> None:
        for plugin in Bot._get_plugins(directory):
            if not hasattr(plugin, 'setup'):
                print(
                    f'Plugin \'{plugin.__name__}\' does not have a setup function'
                )
                continue
            await plugin.setup(self, guilds)
            print(f'loaded \'{plugin.__name__}\'')
        for guild in guilds:
            await self.tree.sync(guild=guild)

    async def reload_plugins(
        self,
        directory: str,
        *,
        guilds: Sequence[discord.Object]
    ) -> None:
        for plugin in Bot._get_plugins(directory):
            plugin = importlib.reload(plugin)
            if not hasattr(plugin, 'teardown'):
                print(
                    f'plugin \'{plugin.__name__}\' does not have a teardown function'
                )
                continue
            # somehow passes if teardown is commented out before reload
            # guessing it just keeps the previous version in the namespace
            # and reload just overwrites the same names
            await plugin.teardown(self, guilds)
            await plugin.setup(self, guilds)
            print(f'reloaded \'{plugin.__name__}\'')
        for guild in guilds:
            await self.tree.sync(guild=guild)

    async def setup_hook(self) -> None:
        await self.load_plugins(PLUGINS_DIR, guilds=GUILD_IDS)


intents = discord.Intents.default()
intents.message_content = True
client = Bot(
    '+',
    application_id=967433475521118268,
    intents=intents,
)


@client.command(name='reload')
async def _reload(ctx: commands.Context):
    await ctx.bot.reload_plugins(PLUGINS_DIR, guilds=GUILD_IDS)


client.run(os.environ.get('DISCORD_TOKEN'))
