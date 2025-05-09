import os
import discord
from discord.ext import tasks
import psutil
import re
from datetime import datetime
from dotenv import load_dotenv
import sqlite3
import asyncio

# Cargar variables de entorno
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
SERVER_NAME = os.getenv('SERVER_NAME')
SERVER_PATH = os.getenv('SERVER_PATH')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL'))

# Configurar intents de Discord
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

async def get_player_count():
    try:
        # Conectar a la base de datos
        db_path = os.path.join(SERVER_PATH, 'db', 'players.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Contar jugadores activos
        cursor.execute("SELECT COUNT(*) FROM networkPlayers WHERE isDead = 0")
        count = cursor.fetchone()[0]

        # Obtener nombres de jugadores
        cursor.execute("SELECT name FROM networkPlayers WHERE isDead = 0")
        players = [row[0] for row in cursor.fetchall()]

        conn.close()
        return count, players
    except Exception as e:
        print(f"Error al obtener jugadores: {e}")
        return 0, []

def is_server_running():
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            if 'java' in proc.info['name'].lower() and any('ProjectZomboid' in cmd for cmd in proc.info['cmdline']):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False

@client.event
async def on_ready():
    print(f'{client.user} ha iniciado sesión!')
    update_status.start()

@tasks.loop(seconds=CHECK_INTERVAL)
async def update_status():
    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        return

    server_status = "🟢 Online" if is_server_running() else "🔴 Offline"
    player_count, players = await get_player_count()

    embed = discord.Embed(
        title=f"Estado del Servidor: {SERVER_NAME}",
        color=discord.Color.green() if server_status == "🟢 Online" else discord.Color.red()
    )

    embed.add_field(name="Estado", value=server_status, inline=False)
    embed.add_field(name="Jugadores Online", value=f"{player_count}/16", inline=False)

    if players:
        embed.add_field(name="Jugadores Conectados", value="\n".join(players), inline=False)

    embed.set_footer(text=f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Buscar y editar el último mensaje del bot
    async for message in channel.history(limit=50):
        if message.author == client.user:
            await message.edit(embed=embed)
            return

    # Si no se encuentra mensaje anterior, enviar uno nuevo
    await channel.send(embed=embed)

client.run(DISCORD_TOKEN)