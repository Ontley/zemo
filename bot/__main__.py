import discord
import importlib
import json
import os
from discord.ext import commands
from typing import Sequence

from dotenv import load_dotenv
load_dotenv()


with open('bot/bot_info.json', 'r') as bot_info_json:
    guild_ids = json.load(bot_info_json)['guilds']
    GUILD_IDS = list(map(discord.Object, guild_ids))


class Bot(commands.Bot):
    """Inherits from `commands.Bot`."""

    def __init__(self,
        *args,
        plugin_dir: str,
        **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self._plugins_dir = plugin_dir

    async def load_plugins(
        self,
        *,
        guilds: Sequence[discord.Object]
    ) -> None:
        plugin_path = f'bot/{self._plugins_dir}'
        for dirpath, _, filenames in os.walk(plugin_path):
            if '__pycache__' == dirpath:
                continue
            for file in filenames:
                if file == '__init__.py' or not file.endswith('.py'):
                    continue
                plugin_path = f'{dirpath.replace("/", ".")}.{file}'
                start = plugin_path.find(self._plugins_dir)
                plugin_path = plugin_path[start: -3]
                plugin = importlib.import_module(plugin_path)
                if not hasattr(plugin, 'setup'):
                    print(
                        f'Plugin \'{plugin.__name__}\' does not have a setup function'
                    )
                    continue
                await plugin.setup(self, guilds)
                print(f'loaded \'{plugin.__name__}\'')

        for guild in guilds:
            await self.tree.sync(guild=guild)

    async def setup_hook(self) -> None:
        await self.load_plugins(guilds=GUILD_IDS)


intents = discord.Intents.default()
intents.message_content = True
client = Bot(
    '+',
    plugin_dir='plugins',
    application_id=967433475521118268,
    intents=intents
)


@client.command(name='reload')
async def _reload(ctx: commands.Context):
    await ctx.bot.reload_plugins()


TOKEN = os.environ.get('DISCORD_TOKEN')
if TOKEN is None:
    raise ValueError("TOKEN NOT FOUND!")
client.run(TOKEN)
