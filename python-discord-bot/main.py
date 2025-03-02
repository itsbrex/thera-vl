#!/usr/bin/env python3
"""
Main entry point for the Discord bot.
Handles Discord API connections and event handling.
"""

import os
import discord
import asyncio
import logging
from discord.ext import commands
from dotenv import load_dotenv
import sys

# Add the current directory to the path so we can import local modules
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

# Local imports
from config import Config
# We no longer need to import individual command modules since we're using load_extension
from llm_client import llm_client
from models import DEFAULT_MODELS

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG for more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('discord')

# Load environment variables
load_dotenv('../.env.local')  # Adjust path as necessary for your folder structure

def setup_bot():
    """Initialize and configure the Discord bot"""
    intents = discord.Intents.default()
    intents.message_content = True  # Needed to read message content
    intents.members = True  # Needed for member-related events
    
    bot = commands.Bot(command_prefix='/', intents=intents)
    return bot

bot = setup_bot()

@bot.event
async def on_ready():
    """Event handler for when the bot connects to Discord"""
    logger.info(f'{bot.user.name} has connected to Discord!')
    logger.info(f'Bot ID: {bot.user.id}')
    logger.info(f'Connected to {len(bot.guilds)} guild(s)')
    
    for guild in bot.guilds:
        logger.info(f'- {guild.name} (ID: {guild.id})')
        # Debug: print all members in the guild
        logger.info(f'Guild {guild.name} has {guild.member_count} members')
        async for member in guild.fetch_members(limit=None):
            logger.debug(f'  - {member.name}#{member.discriminator} (ID: {member.id})')
    
    # Initialize LLM client
    logger.info("Checking LLM providers availability:")
    if Config.OPENAI_API_KEY:
        logger.info(f"- OpenAI: Available (Default model: {DEFAULT_MODELS['openai']})")
    else:
        logger.warning("- OpenAI: Not configured")
        
    if Config.ANTHROPIC_API_KEY:
        logger.info(f"- Anthropic: Available (Default model: {DEFAULT_MODELS['anthropic']})")
    else:
        logger.warning("- Anthropic: Not configured")
        
    if Config.MISTRAL_API_KEY:
        logger.info(f"- Mistral: Available (Default model: {DEFAULT_MODELS['mistral']})")
    else:
        logger.warning("- Mistral: Not configured")
        
    # Load command extensions
    try:
        # Directly load the commands as modules rather than calling setup manually
        # This allows Discord.py to handle the extension loading properly
        await load_extensions()
    except Exception as e:
        logger.error(f"Error loading commands: {e}")
    
    # Sync slash commands with Discord
    try:
        await sync_commands()
    except Exception as e:
        logger.error(f"Error syncing commands: {e}")

async def load_extensions():
    """Load all command extensions"""
    extensions = [
        "commands.session_commands",
        "commands.agent_commands",
        "commands.meeting_commands",
        "commands.brainstorm_commands",
        "commands.transcript_commands",
        "commands.help_command"
    ]
    
    for extension in extensions:
        try:
            await bot.load_extension(extension)
            logger.info(f"{extension} loaded successfully")
        except Exception as e:
            logger.error(f"Error loading {extension}: {e}")

async def sync_commands():
    """Sync slash commands with Discord"""
    logger.info("Syncing commands with Discord...")
    
    # Debug: print command names in the tree
    logger.debug("Commands in bot.tree:")
    for command in bot.tree.get_commands():
        logger.debug(f"- {command.name}")
    
    # Sync to all connected guilds individually for faster updates
    for guild in bot.guilds:
        try:
            guild_commands = await bot.tree.sync(guild=discord.Object(id=guild.id))
            logger.info(f"Synced {len(guild_commands)} command(s) to guild: {guild.name}")
        except Exception as e:
            logger.error(f"Error syncing commands to guild {guild.name}: {e}")
    
    # Also sync globally as a backup
    try:
        global_commands = await bot.tree.sync()
        logger.info(f"Synced {len(global_commands)} command(s) globally")
    except Exception as e:
        logger.error(f"Error syncing commands globally: {e}")

@bot.event
async def on_message(message):
    """Event handler for incoming messages"""
    # Ignore messages from the bot itself to prevent loops
    if message.author.bot or message.content.startswith('/'):
        return
    
    # Let the bot process commands
    await bot.process_commands(message)

@bot.command(name='ping')
async def ping_command(ctx):
    """Simple command to check if the bot is responsive"""
    response = f'Pong! Bot latency: {round(bot.latency * 1000)}ms'
    await ctx.send(response)

@bot.command(name='hello')
async def hello_command(ctx):
    """Simple greeting command"""
    await ctx.send(f'Hello, {ctx.author.mention}! Welcome to TheraLab!')

@bot.command(name='models')
async def models_command(ctx):
    """Command to list available LLM models"""
    available_providers = []
    
    if Config.OPENAI_API_KEY:
        available_providers.append("OpenAI")
    if Config.ANTHROPIC_API_KEY:
        available_providers.append("Anthropic")
    if Config.MISTRAL_API_KEY:
        available_providers.append("Mistral")
    
    if not available_providers:
        await ctx.send("⚠️ No LLM providers configured.")
        return
    
    providers_str = ", ".join(available_providers)
    await ctx.send(f"📚 Available LLM providers: {providers_str}")

async def shutdown():
    """Cleanly shut down the bot and close connections"""
    logger.info("Shutting down bot...")
    
    # Close the LLM client
    try:
        await llm_client.close()
        logger.info("Closed LLM client connection")
    except Exception as e:
        logger.error(f"Error closing LLM client: {e}")
    
    # Close the bot
    if bot:
        await bot.close()
        logger.info("Bot disconnected from Discord")

def main():
    """Main entry point for the bot"""
    token = os.environ.get('DISCORD_TOKEN')
    if not token:
        logger.error('No Discord token found. Please set the DISCORD_TOKEN environment variable.')
        return
    
    try:
        # Validate configuration
        missing_configs = Config.validate()
        if missing_configs:
            logger.warning(f"Missing configuration values: {', '.join(missing_configs)}")
        
        # Start the bot and handle clean shutdown
        bot.run(token, log_handler=None)
    except discord.errors.LoginFailure as e:
        logger.error(f'Failed to log in: {e}')
    except Exception as e:
        logger.error(f'An error occurred: {e}')
    finally:
        # Ensure we run the shutdown logic
        asyncio.run(shutdown())

if __name__ == '__main__':
    main() 