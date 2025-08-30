# ✅ IMPORTS NECESARIOS
import discord
from discord.ext import commands
from flask import Flask, request
import threading
import asyncio
import json
import os
import time

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
ultima_actualizacion = 0

async def limpiar_mensajes_antiguos():
    """Eliminar mensajes antiguos del bot en el canal"""
    try:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            async for message in channel.history(limit=100):
                if message.author == bot.user and message.id != MESSAGE_ID:
                    await message.delete()
                    await asyncio.sleep(0.5)
            print("🧹 Mensajes antiguos limpiados")
    except Exception as e:
        print(f"⚠️ Error limpiando mensajes: {e}")

async def actualizar_mensaje(nuevos_datos):
    """Actualiza el mensaje con los nuevos datos de Roblox"""
    global MESSAGE_ID, actualizacion_pendiente, ultima_actualizacion

    # Verificar si ya hay una actualización en curso
    if actualizacion_pendiente:
        print("⏸️  Actualización en curso, omitiendo...")
        return

    actualizacion_pendiente = True
    print(f"🔄 Iniciando actualización... {time.time()}")

    try:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await limpiar_mensajes_antiguos()
            
            if MESSAGE_ID:
                try:
                    message = await channel.fetch_message(MESSAGE_ID)
                    msg_content = "\n".join(
                        [f"{aldea}: {monedas} $" for aldea, monedas in nuevos_datos.items()]
                    )
                    await message.edit(content=f"📊 Economía de las Aldeas:\n{msg_content}")
                    print("✏️ Mensaje actualizado")
                    ultima_actualizacion = time.time()
                except discord.NotFound:
                    print("❌ Mensaje no encontrado, creando nuevo...")
                    MESSAGE_ID = None
                except discord.Forbidden:
                    print("❌ Sin permisos para editar mensaje")
                    MESSAGE_ID = None
            
            if not MESSAGE_ID:
                msg_content = "\n".join(
                    [f"{aldea}: {monedas} $" for aldea, monedas in nuevos_datos.items()]
                )
                message = await channel.send(f"📊 Economía de las Aldeas:\n{msg_content}")
                MESSAGE_ID = message.id
                print("📝 Nuevo mensaje creado")
                ultima_actualizacion = time.time()
            
    except Exception as e:
        print(f"⚠️ Error al actualizar mensaje: {e}")
        import traceback
        traceback.print_exc()
    
    # ⚠️ IMPORTANTE: Siempre resetear la bandera
    actualizacion_pendiente = False
    print("✅ Actualización completada")

# ----------- Flask para recibir datos desde Roblox ----------- #
app = Flask(__name__)

@app.route("/actualizar", methods=["POST"])
def actualizar_economia():
    """Endpoint para recibir datos COMPLETOS de Roblox"""
    try:
        data = request.json
        
        if not isinstance(data, dict):
            return {"status": "error", "mensaje": "Datos deben ser un objeto JSON"}, 400
        
        print(f"📨 Datos recibidos de Roblox: {data}")
        
        # Crear task para actualizar sin bloquear
        asyncio.run_coroutine_threadsafe(actualizar_mensaje(data), bot.loop)
        
        return {"status": "ok", "mensaje": "Economía actualizada en Discord"}
        
    except Exception as e:
        print(f"❌ Error procesando datos: {e}")
        return {"status": "error", "mensaje": str(e)}, 500

@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint para health checks"""
    return {
        "status": "ok", 
        "bot_online": bot.is_ready(),
        "ultima_actualizacion": ultima_actualizacion,
        "actualizacion_pendiente": actualizacion_pendiente
    }

@app.route("/status", methods=["GET"])
def status_info():
    """Info de estado del bot"""
    return {
        "bot_ready": bot.is_ready(),
        "message_id": MESSAGE_ID,
        "hora_actual": time.time(),
        "ultima_actualizacion": ultima_actualizacion
    }

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
    
    await limpiar_mensajes_antiguos()
    
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
    
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"❌ Error fatal del bot: {e}")
        import traceback
        traceback.print_exc()
