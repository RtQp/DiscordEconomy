# ✅ IMPORTS NECESARIOS
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
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = os.environ.get("DISCORD_TOKEN")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", 1411206971167735810))
MESSAGE_ID = None

# ----------- Control de actualizaciones ----------- #
actualizacion_pendiente = False

async def limpiar_mensajes_antiguos():
    """Eliminar mensajes antiguos del bot en el canal"""
    try:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            # Obtener todos los mensajes del bot
            async for message in channel.history(limit=100):
                if message.author == bot.user and message.id != MESSAGE_ID:
                    await message.delete()
                    await asyncio.sleep(0.5)  # Evitar rate limits
            print("🧹 Mensajes antiguos limpiados")
    except Exception as e:
        print(f"⚠️ Error limpiando mensajes: {e}")

async def actualizar_mensaje(nuevos_datos):
    """Actualiza el mensaje con los nuevos datos de Roblox"""
    global MESSAGE_ID, actualizacion_pendiente

    if actualizacion_pendiente:
        return

    actualizacion_pendiente = True
    await asyncio.sleep(2)

    try:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            # Limpiar mensajes antiguos primero
            await limpiar_mensajes_antiguos()
            
            if MESSAGE_ID:
                # Intentar editar mensaje existente
                try:
                    message = await channel.fetch_message(MESSAGE_ID)
                    msg_content = "\n".join(
                        [f"{aldea}: {monedas} $" for aldea, monedas in nuevos_datos.items()]
                    )
                    await message.edit(content=f"📊 Economía de las Aldeas:\n{msg_content}")
                    print("✏️ Mensaje actualizado con datos de Roblox")
                    return
                except:
                    # Si el mensaje no existe, crear uno nuevo
                    MESSAGE_ID = None
            
            # Crear nuevo mensaje
            msg_content = "\n".join(
                [f"{aldea}: {monedas} $" for aldea, monedas in nuevos_datos.items()]
            )
            message = await channel.send(f"📊 Economía de las Aldeas:\n{msg_content}")
            MESSAGE_ID = message.id
            print("📝 Nuevo mensaje creado con datos de Roblox")
            
    except Exception as e:
        print(f"⚠️ Error al actualizar mensaje: {e}")

    actualizacion_pendiente = False

# ----------- Flask para recibir datos desde Roblox ----------- #
app = Flask(__name__)

@app.route("/actualizar", methods=["POST"])
def actualizar_economia():
    """Endpoint para recibir datos COMPLETOS de Roblox"""
    try:
        data = request.json
        
        # Verificar que los datos tienen el formato esperado
        if not isinstance(data, dict):
            return {"status": "error", "mensaje": "Datos deben ser un objeto JSON"}, 400
        
        print(f"📨 Datos recibidos de Roblox: {data}")
        
        # Actualizar el mensaje en Discord con los datos de Roblox
        bot.loop.create_task(actualizar_mensaje(data))
        
        return {"status": "ok", "mensaje": "Economía actualizada en Discord"}
        
    except Exception as e:
        print(f"❌ Error procesando datos de Roblox: {e}")
        return {"status": "error", "mensaje": str(e)}, 500

@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint para health checks"""
    return {"status": "ok", "bot_online": bot.is_ready()}

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Starting Flask server on port {port}")
    
    if os.environ.get("PRODUCTION", "false").lower() == "true":
        from waitress import serve
        serve(app, host="0.0.0.0", port=port)
    else:
        app.run(host="0.0.0.0", port=port, debug=False)

# ----------- Eventos del bot ----------- #
@bot.event
async def on_ready():
    print(f'✅ Conectado como {bot.user}')
    global MESSAGE_ID
    
    # Limpiar mensajes antiguos al iniciar
    await limpiar_mensajes_antiguos()
    
    # Mensaje inicial vacío
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        message = await channel.send("📊 Esperando datos de Roblox...")
        MESSAGE_ID = message.id
        print("🎯 Mensaje inicial creado")

# ----------- Ejecutar Flask y Discord juntos ----------- #
if __name__ == "__main__":
    if not TOKEN:
        print("❌ ERROR: DISCORD_TOKEN no está configurado")
        exit(1)
    
    threading.Thread(target=run_flask, daemon=True).start()
    bot.run(TOKEN)
