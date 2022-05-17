import os
import discord
from importlib import import_module
from discord import app_commands
from dotenv import load_dotenv
load_dotenv()


def clean_path(path: str) -> str:
    '''cleans the path of slashes and replaces them with . for loading extensions'''
    start = path.find('cogs')
    end = path.find('.py')
    path = path[start: end]
    path = path.replace('/', '.')
    path = path.replace(r'\\', '.')
    return path


def load_extensions(
    tree: app_commands.CommandTree,
    directory: str,
    guilds=[
        discord.Object(id=967430088163467314),
    ]
) -> None:
    '''loads cogs from the given folder, ignoring pycache'''
    for dirpath, _, filenames in os.walk(directory):

        if '__pycache__' == dirpath:
            continue

        for file in filenames:
            if file == '__init__.py' or not file.endswith('.py'):
                continue

            dirty = f'{dirpath}.{file}'
            clean = clean_path(dirty)
            ext = import_module(clean)
            for attr in vars(ext).values():
                if isinstance(attr, app_commands.Command):
                    tree.add_command(attr, guilds=guilds)


intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(application_id=967433475521118268, intents=intents)
tree = app_commands.CommandTree(client)
load_extensions(tree, 'bot/cogs')


# TODO: this should be made more shmurt, or maybe not cuz dev
@client.event
async def on_message(msg: discord.Message) -> None:
    if msg.content == 'sync':
        if msg.guild is None:
            return
        await tree.sync(guild=discord.Object(msg.guild.id))

client.run(os.environ.get('DISCORD_TOKEN'))
