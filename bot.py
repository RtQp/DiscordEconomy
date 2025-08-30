# ✅ IMPORTS NECESARIOS
import discord
from discord.ext import commands
from flask import Flask, request
import threading
import asyncio
import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# ----------- Configuración del bot de Discord ----------- #
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True  # ⬅️ NECESARIO para leer mensajes

bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = os.environ.get("DISCORD_TOKEN")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", 1411206971167735810))
MESSAGE_ID = None

# ----------- PostgreSQL Database ----------- #
def get_db_connection():
    return psycopg2.connect(os.environ['DATABASE_URL'])

def init_database():
    """Inicializar la tabla si no existe"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS economia (
                id SERIAL PRIMARY KEY,
                datos JSONB NOT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error inicializando base de datos: {e}")

def guardar_economia():
    """Guardar economía en PostgreSQL"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO economia (id, datos) VALUES (1, %s) "
            "ON CONFLICT (id) DO UPDATE SET datos = EXCLUDED.datos, last_updated = CURRENT_TIMESTAMP",
            (json.dumps(economias),)
        )
        conn.commit()
        cur.close()
        conn.close()
        print("💾 Economía guardada en PostgreSQL")
    except Exception as e:
        print(f"❌ Error guardando economía: {e}")

def cargar_economia():
    """Cargar economía desde PostgreSQL"""
    global economias
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT datos FROM economia WHERE id = 1")
        result = cur.fetchone()
        
        if result:
            economias = json.loads(result[0])
            print("📂 Economía cargada desde PostgreSQL")
        else:
            economias = {"Konoha": 0, "Suna": 0, "Kiri": 0, "Iwa": 0, "Kumo": 0}
            print("📝 Economía inicial creada")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error cargando economía: {e}")
        economias = {"Konoha": 0, "Suna": 0, "Kiri": 0, "Iwa": 0, "Kumo": 0}

# ----------- Inicializar base de datos y cargar economía ----------- #
init_database()
cargar_economia()

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

async def actualizar_mensaje():
    """Edita el mensaje en Discord con cooldown y limpia mensajes antiguos"""
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
                        [f"{aldea}: {monedas} $" for aldea, monedas in economias.items()]
                    )
                    await message.edit(content=f"📊 Economía de las Aldeas:\n{msg_content}")
                    print("✏️ Mensaje actualizado")
                    return
                except:
                    # Si el mensaje no existe, crear uno nuevo
                    MESSAGE_ID = None
            
            # Crear nuevo mensaje
            msg_content = "\n".join(
                [f"{aldea}: {monedas} $" for aldea, monedas in economias.items()]
            )
            message = await channel.send(f"📊 Economía de las Aldeas:\n{msg_content}")
            MESSAGE_ID = message.id
            print("📝 Nuevo mensaje creado")
            
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
        guardar_economia()

        bot.loop.create_task(actualizar_mensaje())
        return {"status": "ok", "nueva_economia": economias}

    return {"status": "error", "mensaje": "Aldea no encontrada"}, 400

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
    
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        msg_content = "\n".join(
            [f"{aldea}: {monedas} $" for aldea, monedas in economias.items()]
        )
        message = await channel.send(f"📊 Economía de las Aldeas:\n{msg_content}")
        MESSAGE_ID = message.id
        print("🎯 Mensaje inicial creado")

# ----------- Ejecutar Flask y Discord juntos ----------- #
if __name__ == "__main__":
    if not TOKEN:
        print("❌ ERROR: DISCORD_TOKEN no está configurado")
        exit(1)
    
    threading.Thread(target=run_flask, daemon=True).start()
    bot.run(TOKEN)
