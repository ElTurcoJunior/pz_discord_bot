import os
import discord
from discord.ext import tasks
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
SERVER_NAME = os.getenv('SERVER_NAME')
BIN_FOLDER = os.getenv('BIN_FOLDER')  # Ruta a la carpeta con los .bin
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL'))

intents = discord.Intents.default()
client = discord.Client(intents=intents)

def get_stat_from_bin(data, stat_name):
    idx = data.find(stat_name.encode())
    if idx != -1:
        idx += len(stat_name)
        while idx < len(data) and data[idx] == 0:
            idx += 1
        if idx + 4 <= len(data):
            return int.from_bytes(data[idx:idx+4], 'little')
    return None

def get_string_from_bin(data, stat_name):
    idx = data.find(stat_name.encode())
    if idx != -1:
        idx += len(stat_name)
        while idx < len(data) and data[idx] == 0:
            idx += 1
        end = idx
        while end < len(data) and data[end] != 0:
            end += 1
        return data[idx:end].decode(errors='ignore')
    return None

def get_player_stats(bin_path):
    with open(bin_path, 'rb') as f:
        data = f.read()
        kills = get_stat_from_bin(data, 'ZombieKills')
        survived = get_stat_from_bin(data, 'SurvivedFor')
        is_dead = get_stat_from_bin(data, 'isDead')
        # Nombre: forename + surname (si existe)
        forename = get_string_from_bin(data, 'forename')
        surname = get_string_from_bin(data, 'surname')
        if forename and surname:
            name = f"{forename} {surname}"
        elif forename:
            name = forename
        else:
            name = os.path.basename(bin_path)
        return {
            'name': name,
            'kills': kills if kills is not None else 0,
            'survived': survived if survived is not None else 0,
            'is_dead': is_dead == 1  # True si está muerto
        }

def format_survived(minutes):
    # Convierte minutos a días, horas, minutos
    td = timedelta(minutes=minutes)
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    mins = remainder // 60
    return f"{days}d {hours}h {mins}m"

def get_top_players(bin_folder, top_n=15):
    players = []
    for filename in os.listdir(bin_folder):
        if filename.endswith('.bin'):
            path = os.path.join(bin_folder, filename)
            stats = get_player_stats(path)
            # Solo jugadores vivos
            if not stats['is_dead']:
                players.append(stats)
    players.sort(key=lambda x: x['kills'], reverse=True)
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

    if not os.path.exists(BIN_FOLDER):
        ranking = "No se encontró la carpeta de jugadores."
    else:
        top_players = get_top_players(BIN_FOLDER)
        if not top_players:
            ranking = "No hay jugadores vivos en el ranking."
        else:
            ranking = ""
            for idx, player in enumerate(top_players, 1):
                survived_str = format_survived(player['survived'])
                ranking += f"**{idx}. {player['name']}** — {player['kills']} kills — {survived_str}\n"

    embed = discord.Embed(
        title=f"Ranking de Kills - {SERVER_NAME}",
        color=discord.Color.gold()
    )
    embed.add_field(name="Top 15 jugadores vivos con más kills", value=ranking, inline=False)
    embed.set_footer(text=f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Buscar y editar el último mensaje del bot
    async for message in channel.history(limit=50):
        if message.author == client.user:
            await message.edit(embed=embed)
            return

    await channel.send(embed=embed)

client.run(DISCORD_TOKEN)