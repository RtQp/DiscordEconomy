import discord
from discord.ext import commands
from flask import Flask, request
import threading
import asyncio
import json
import os

# ----------- Configuración del bot de Discord ----------- #
intents = discord.Intents.default()
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = os.environ.get("DISCORD_TOKEN")  # ✅ MANTENER esta estructura
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", 1411206971167735810))  # ✅ MANTENER
MESSAGE_ID = None  # Guardaremos el ID del mensaje que vamos a editar

# ----------- Persistencia en archivo JSON ----------- #
def guardar_economia():
    with open("economia.json", "w") as f:
        json.dump(economias, f)

def cargar_economia():
    global economias
    if os.path.exists("economia.json"):
        with open("economia.json", "r") as f:
            economias = json.load(f)
    else:
        economias = {
          "Konoha": 0,
          "Suna": 0,
          "Kiri": 0,
          "Iwa": 0,
          "Kumo": 0
        }

# Cargar datos al iniciar
cargar_economia()

# ----------- Control de actualizaciones ----------- #
actualizacion_pendiente = False

async def actualizar_mensaje():
    """Edita el mensaje en Discord con cooldown para evitar spam."""
    global MESSAGE_ID, actualizacion_pendiente

    if actualizacion_pendiente:
        return  # ya hay actualización en curso

    actualizacion_pendiente = True
    await asyncio.sleep(2)  # cooldown de 2 segundos

    channel = bot.get_channel(CHANNEL_ID)
    if channel and MESSAGE_ID:
        try:
            message = await channel.fetch_message(MESSAGE_ID)
            msg_content = "\n".join(
                [f"{aldea}: {monedas} $" for aldea, monedas in economias.items()]
            )
            await message.edit(content=f"📊 Economía de las Aldeas:\n{msg_content}")
        except Exception as e:
            print(f"⚠️ Error al actualizar mensaje: {e}")

    actualizacion_pendiente = False

# ----------- Flask para recibir datos desde Roblox ----------- #
app = Flask(__name__)

@app.route("/sumar", methods=["POST"])
def sumar():
    global economias
    data = request.json
    aldea = data.get("aldea")
    cantidad = data.get("cantidad", 0)

    if aldea in economias:
        economias[aldea] += cantidad
        guardar_economia()  # 🔹 Guardar después de cada cambio

        # Llamamos a la actualización con cooldown
        bot.loop.create_task(actualizar_mensaje())
        return {"status": "ok", "nueva_economia": economias}

    return {"status": "error", "mensaje": "Aldea no encontrada"}, 400

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# ----------- Eventos del bot ----------- #
@bot.event
async def on_ready():
    print(f'✅ Conectado como {bot.user}')
    global MESSAGE_ID
    channel = bot.get_channel(CHANNEL_ID)
    if channel and MESSAGE_ID is None:
        msg_content = "\n".join(
            [f"{aldea}: {monedas} $" for aldea, monedas in economias.items()]
        )
        message = await channel.send(f" # Economías Aldeas :\n{msg_content}")
        MESSAGE_ID = message.id

# ----------- Ejecutar Flask y Discord juntos ----------- #
threading.Thread(target=run_flask).start()
bot.run(TOKEN)
