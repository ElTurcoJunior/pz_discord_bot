import os
import discord
from discord.ext import tasks
from datetime import datetime
from dotenv import load_dotenv
import sqlite3
import re

# Cargar variables de entorno
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
SERVER_NAME = os.getenv('SERVER_NAME')
SERVER_PATH = os.getenv('SERVER_PATH')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL'))

intents = discord.Intents.default()
client = discord.Client(intents=intents)

def get_top_killers(db_path, top_n=15):
    players = []
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name, data FROM networkPlayers")
        for name, data in cursor.fetchall():
            if data is None:
                continue
            # Buscar el patrón ZombieKills en el binario
            match = re.search(rb'ZombieKills\x00*([0-9]+)', data)
            if not match:
                # Alternativamente, busca el patrón como string seguido de 4 bytes (int)
                match = re.search(rb'ZombieKills\x00{0,3}(.{4})', data)
                if match:
                    # Interpreta los 4 bytes como un entero little-endian
                    kills = int.from_bytes(match.group(1), 'little')
                else:
                    kills = 0
            else:
                try:
                    kills = int(match.group(1))
                except Exception:
                    kills = 0
            players.append((name, kills))
        conn.close()
    except Exception as e:
        print(f"Error al leer la base de datos: {e}")
        return []
    # Ordenar de mayor a menor
    players.sort(key=lambda x: x[1], reverse=True)
    return players[:top_n]

@client.event
async def on_ready():
    print(f'{client.user} ha iniciado sesión!')
    update_status.start()

@tasks.loop(seconds=CHECK_INTERVAL)
async def update_status():
    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        print("No se pudo encontrar el canal de Discord.")
        return

    db_path = SERVER_PATH  # Ahora SERVER_PATH debe ser la ruta completa a players.db
    if not os.path.exists(db_path):
        ranking = "No se encontró la base de datos."
    else:
        top_players = get_top_killers(db_path)
        if not top_players:
            ranking = "No hay datos de jugadores."
        else:
            ranking = ""
            for idx, (name, kills) in enumerate(top_players, 1):
                ranking += f"**{idx}. {name}** — {kills} kills\n"

    embed = discord.Embed(
        title=f"Ranking de Kills - {SERVER_NAME}",
        color=discord.Color.gold()
    )
    embed.add_field(name="Top 15 jugadores con más kills", value=ranking, inline=False)
    embed.set_footer(text=f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Buscar y editar el último mensaje del bot
    async for message in channel.history(limit=50):
        if message.author == client.user:
            await message.edit(embed=embed)
            return

    await channel.send(embed=embed)

client.run(DISCORD_TOKEN)