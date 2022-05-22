import os
import json
import discord
from typing import Sequence
from importlib import import_module
from discord import app_commands
from dotenv import load_dotenv
load_dotenv()

with open('bot/bot_info.json', 'r') as bot_info_json:
    guild_ids = json.load(bot_info_json)['guilds']
    GUILD_IDS = list(map(discord.Object, guild_ids))


def load_plugins(
    tree: app_commands.CommandTree,
    *,
    directory: str,
    guilds: Sequence[discord.Object]
) -> None:
    """Load plugins from the given folder, ignoring `__pycache__`."""
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
            ext = import_module(ext_path)
            for attr in vars(ext).values():
                if isinstance(attr, app_commands.Command):
                    tree.add_command(attr, guilds=guilds)


intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(application_id=967433475521118268, intents=intents)
tree = app_commands.CommandTree(client)
load_plugins(tree, directory='plugins', guilds=GUILD_IDS)


@client.event
async def on_message(msg: discord.Message) -> None:
    if msg.content.strip() == 'sync':
        if msg.guild is None:
            return
        await tree.sync(guild=discord.Object(msg.guild.id))

client.run(os.environ.get('DISCORD_TOKEN'))
