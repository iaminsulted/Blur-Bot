import discord
from discord.ext import commands
import requests
import random
from datetime import datetime, timezone
from discord import app_commands
import re
from datetime import timedelta
import asyncio
import json

# Create an instance of Intents
intents = discord.Intents.default()
intents.members = True  # Enable the members intent
intents.message_content = True  # Enable message content intent (if needed)

# Initialize the bot with the specified intents
bot = commands.Bot(command_prefix='!', intents=intents)

GIPHY_API_KEY = "12b9uUTiW9BuyMEMQgAHyQSIx2Jm89hT" 

# Add this near the top of your file, after other imports
AUTO_ROLE_FILE = 'auto_role.json'

# Load the auto-role setting
try:
    with open(AUTO_ROLE_FILE, 'r') as f:
        auto_role_data = json.load(f)
except FileNotFoundError:
    auto_role_data = {}

@bot.event
async def on_ready():
    """Event that triggers when the bot is ready."""
    print(f'{bot.user} has connected to Discord!')
    await bot.tree.sync()

@bot.tree.command(name='hello')
async def hello(interaction: discord.Interaction):
    """Command that sends a greeting message."""
    embed = discord.Embed(title="Hello!", description=f'Hello, {interaction.user.mention}! I am a bot created by dyl', color=discord.Color.blue())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='repeat')
async def repeat(interaction: discord.Interaction, message: str):
    """Command that repeats the message."""
    embed = discord.Embed(title="Repeat", description=message, color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='ping')
async def ping(interaction: discord.Interaction):
    """Command that sends the bot's latency."""
    embed = discord.Embed(title="Pong!", description=f'Latency: {bot.latency * 1000:.2f}ms', color=discord.Color.red())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='add')
async def add(interaction: discord.Interaction, a: int, b: int):
    """Command that adds two numbers."""
    result = a + b
    embed = discord.Embed(title="Addition Result", description=f'The sum of {a} and {b} is {result}', color=discord.Color.gold())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='gif')
async def gif(interaction: discord.Interaction):
    """Command that sends a random GIF from Giphy."""
    url = f"https://api.giphy.com/v1/gifs/random?api_key={GIPHY_API_KEY}&rating=g"
    response = requests.get(url)
    data = response.json()
    
    if response.status_code == 200 and 'data' in data:
        gif_url = data['data']['images']['original']['url']
        embed = discord.Embed(title="Random GIF", color=discord.Color.purple())
        embed.set_image(url=gif_url)
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(title="Error", description="Sorry, I couldn't fetch a GIF at the moment.", color=discord.Color.dark_red())
        await interaction.response.send_message(embed=embed)

def is_admin():
    async def predicate(interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            raise app_commands.errors.CheckFailure("You need administrator permissions to use this command.")
        return True
    return app_commands.check(predicate)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.errors.CheckFailure):
        embed = discord.Embed(title="Error", description=str(error), color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        # Handle other types of errors here
        pass

@bot.tree.command(name='kick')
@is_admin()
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    """Kick a member from the server."""
    await member.kick(reason=reason)
    embed = discord.Embed(title="Member Kicked", description=f'{member.mention} has been kicked. Reason: {reason}', color=discord.Color.orange())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='ban')
@is_admin()
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    """Ban a member from the server."""
    await member.ban(reason=reason)
    embed = discord.Embed(title="Member Banned", description=f'{member.mention} has been banned. Reason: {reason}', color=discord.Color.red())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='mute')
@is_admin()
async def mute(interaction: discord.Interaction, member: discord.Member, duration: str, reason: str = None):
    """Mute a member for a specified duration. Use format: <number><s/d/w> (e.g., 30s, 2d, 1w)"""
    # Parse the duration
    duration_regex = re.match(r'(\d+)([sdw])', duration.lower())
    if not duration_regex:
        embed = discord.Embed(title="Error", description="Invalid duration format. Use <number><s/d/w> (e.g., 30s, 2d, 1w)", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    amount = int(duration_regex.group(1))
    unit = duration_regex.group(2)

    if unit == 's':
        mute_duration = timedelta(seconds=amount)
    elif unit == 'd':
        mute_duration = timedelta(days=amount)
    elif unit == 'w':
        mute_duration = timedelta(weeks=amount)

    # Ensure you have a role to mute members
    mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
    if mute_role is None:
        # Create the mute role if it doesn't exist
        mute_role = await interaction.guild.create_role(name="Muted")
        for channel in interaction.guild.channels:
            await channel.set_permissions(mute_role, speak=False, send_messages=False)

    await member.add_roles(mute_role, reason=reason)
    
    # Calculate unmute time
    unmute_time = (interaction.created_at + mute_duration).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    embed = discord.Embed(title="Member Muted", description=f'{member.mention} has been muted until {unmute_time}. Reason: {reason}', color=discord.Color.yellow())
    await interaction.response.send_message(embed=embed)

    # Schedule unmute (Note: This is a simple implementation and won't persist if the bot restarts)
    await asyncio.sleep(mute_duration.total_seconds())
    await member.remove_roles(mute_role, reason="Mute duration expired")

@bot.tree.command(name='unmute')
async def unmute(interaction: discord.Interaction, member: discord.Member, *, reason: str = "No reason provided"):
    """Command to unmute a member in the server."""
    mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
    if mute_role is not None:
        await member.remove_roles(mute_role, reason=reason)
        embed = discord.Embed(title="Member Unmuted", description=f'{member.mention} has been unmuted. Reason: {reason}', color=discord.Color.green())
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(title="Error", description="Mute role does not exist.", color=discord.Color.dark_red())
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name='avatar')
async def avatar(interaction: discord.Interaction, member: discord.Member = None):
    """Command to display a user's avatar."""
    target = member or interaction.user
    avatar_url = target.display_avatar.url
    embed = discord.Embed(title=f"{target.name}'s Avatar", color=discord.Color.blue())
    embed.set_image(url=avatar_url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='userinfo')
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    """Display information about a user's Discord account."""
    target = member or interaction.user
    
    # Use timezone-aware datetime objects
    now = datetime.now(timezone.utc)
    account_age = now - target.created_at.replace(tzinfo=timezone.utc)
    server_join_date = now - target.joined_at.replace(tzinfo=timezone.utc) if target.joined_at else None
    
    # Get user roles, excluding @everyone
    roles = [role.mention for role in target.roles if role.name != "@everyone"]
    roles_str = ", ".join(roles) if roles else "No roles"

    embed = discord.Embed(title=f"User Info - {target.name}", color=target.color)
    embed.set_thumbnail(url=target.display_avatar.url)
    
    embed.add_field(name="User ID", value=str(target.id), inline=False)
    embed.add_field(name="Account Created", value=f"{target.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC\n({account_age.days} days ago)", inline=False)
    
    if server_join_date:
        embed.add_field(name="Joined Server", value=f"{target.joined_at.strftime('%Y-%m-%d %H:%M:%S')} UTC\n({server_join_date.days} days ago)", inline=False)
    
    embed.add_field(name="Roles", value=roles_str, inline=False)
    embed.add_field(name="Bot", value="Yes" if target.bot else "No", inline=False)
    
    if target.premium_since:
        embed.add_field(name="Boosting Since", value=target.premium_since.strftime('%Y-%m-%d %H:%M:%S'), inline=False)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='clear')
@is_admin()
async def clear(interaction: discord.Interaction, amount: int):
    """Delete a specified number of messages from the channel."""
    if amount <= 0:
        embed = discord.Embed(title="Error", description="Please specify a positive number of messages to delete.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Defer the response since deletion might take a while
    await interaction.response.defer(ephemeral=True)

    try:
        deleted = await interaction.channel.purge(limit=amount)
        embed = discord.Embed(title="Messages Deleted", description=f"Successfully deleted {len(deleted)} messages.", color=discord.Color.green())
        await interaction.followup.send(embed=embed, ephemeral=True)
    except discord.Forbidden:
        embed = discord.Embed(title="Error", description="I don't have the required permissions to delete messages.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)
    except discord.HTTPException as e:
        embed = discord.Embed(title="Error", description=f"An error occurred while deleting messages: {str(e)}", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name='set_auto_role')
@is_admin()
async def set_auto_role(interaction: discord.Interaction, role: discord.Role):
    """Set a role to be automatically added to new members."""
    guild_id = str(interaction.guild.id)
    auto_role_data[guild_id] = role.id
    
    with open(AUTO_ROLE_FILE, 'w') as f:
        json.dump(auto_role_data, f)
    
    embed = discord.Embed(title="Auto Role Set", description=f"The role {role.mention} will now be automatically added to new members.", color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

@bot.event
async def on_member_join(member: discord.Member):
    guild_id = str(member.guild.id)
    if guild_id in auto_role_data:
        role_id = auto_role_data[guild_id]
        role = member.guild.get_role(role_id)
        if role:
            try:
                await member.add_roles(role)
                print(f"Added role {role.name} to {member.name}")
            except discord.Forbidden:
                print(f"Failed to add role {role.name} to {member.name}: Missing permissions.")
            except discord.HTTPException as e:
                print(f"Failed to add role {role.name} to {member.name}: {str(e)}")
        else:
            print(f"Auto-role with ID {role_id} not found in the server.")

@bot.tree.command(name='clear_auto_role')
@is_admin()
async def clear_auto_role(interaction: discord.Interaction):
    """Clear the auto-role setting for this server."""
    guild_id = str(interaction.guild.id)
    if guild_id in auto_role_data:
        del auto_role_data[guild_id]
        with open(AUTO_ROLE_FILE, 'w') as f:
            json.dump(auto_role_data, f)
        embed = discord.Embed(title="Auto Role Cleared", description="The auto-role setting has been cleared for this server.", color=discord.Color.blue())
    else:
        embed = discord.Embed(title="No Auto Role Set", description="There was no auto-role set for this server.", color=discord.Color.yellow())
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='create_color_role')
async def create_color_role(interaction: discord.Interaction, role_name: str, hex_color: str):
    """Create a color role for the user with a specified name and hex color."""
    # Validate the hex color format
    if not re.match(r'^#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})$', hex_color):
        embed = discord.Embed(title="Error", description="Invalid hex color format. Please use #RRGGBB or #RGB.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Check if the role already exists
    existing_role = discord.utils.get(interaction.guild.roles, name=role_name)
    if existing_role:
        embed = discord.Embed(title="Error", description=f"A role with the name '{role_name}' already exists.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Create the new role with the specified color
    try:
        color = int(hex_color.replace('#', ''), 16)  # Convert hex to integer
        new_role = await interaction.guild.create_role(name=role_name, color=discord.Color(color))
        await interaction.user.add_roles(new_role)  # Assign the role to the user

        embed = discord.Embed(title="Color Role Created", description=f"You have created and been assigned the role '{new_role.name}' with color {hex_color}.", color=new_role.color)
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        embed = discord.Embed(title="Error", description="I don't have permission to create roles.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except discord.HTTPException as e:
        embed = discord.Embed(title="Error", description=f"An error occurred while creating the role: {str(e)}", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

bot.run('TOKENHERE')
