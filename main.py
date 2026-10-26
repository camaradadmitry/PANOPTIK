
import os
import unicodedata
import discord
from discord.ext import commands
from discord import app_commands

# ==================================================
# CONFIGURACIÓN
# ==================================================

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==================================================
# CATÁLOGO OFICIAL DE CONDECORACIONES
# Las medallas con materiales generan roles separados.
# Los nombres deben coincidir con los roles de Discord.
# ==================================================

MEDALLAS = {
    "Heroe de la República Democrática Alemana": None,
    "Heroe del Trabajo": None,
    "Orden de Karl Marx": None,

    "Medalla al Mérito de Servicio en el MfS":
        ["Oro", "Plata", "Bronce"],

    "Medalla al Mérito del servicio en el MfNV":
        ["Oro", "Plata", "Bronce"],

    "Orden Patriótica al Mérito":
        ["Oro", "Plata", "Bronce"],

    "Orden de Scharnhorst": None,

    "Bandera del Trabajo":
        ["Oro", "Plata", "Bronce"],

    "Veterano de la Guerra Civil Española": None,
    "Estrella de la Amistad de los Pueblos": None,
    "Medalla Hans Beimler": None,

    "Medalla por Servicio Fiel en el NVA":
        ["Oro", "Plata", "Bronce"],

    "Mérito al Brigadista Antifascista en España": None,

    "Orden de Blücher":
        ["Oro", "Plata", "Bronce"],
}


# ==================================================
# FUNCIONES AUXILIARES
# ==================================================

def normalizar(texto):
    """Ignora mayúsculas, tildes y diferencias de escritura."""
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        c for c in texto
        if unicodedata.category(c) != "Mn"
    )
    return " ".join(texto.casefold().split())


def buscar_medalla(nombre):
    for nombre_oficial, materiales in MEDALLAS.items():
        if normalizar(nombre) == normalizar(nombre_oficial):
            return nombre_oficial, materiales
    return None, None


def buscar_rol(guild, nombre):
    nombre_normalizado = normalizar(nombre)

    return discord.utils.find(
        lambda rol: normalizar(rol.name) == nombre_normalizado,
        guild.roles
    )


# ==================================================
# INICIO Y SINCRONIZACIÓN DE COMANDOS
# ==================================================

@bot.event
async def on_ready():
    if not getattr(bot, "comandos_sincronizados", False):
        try:
            await bot.tree.sync()
            bot.comandos_sincronizados = True
            print("Comandos slash sincronizados.")
        except Exception as error:
            print(f"Error al sincronizar comandos: {error}")

    print(f"Bot conectado como {bot.user}")


# ==================================================
# COMANDO !condecorar Y /condecorar
# ==================================================

@bot.hybrid_command(
    name="condecorar",
    description="Concede una condecoración oficial de la RDA."
)
@app_commands.describe(
    usuario="Usuario que recibirá la condecoración",
    medalla="Nombre de la condecoración",
    material="Oro, Plata, Bronce o Ninguno",
    motivo="Motivo oficial de la concesión",
    firma="Autoridad que firma la concesión"
)
@app_commands.guild_only()
async def condecorar(
    ctx: commands.Context,
    usuario: discord.Member,
    medalla: str,
    material: str,
    motivo: str,
    firma: str
):
    # Solo se permite ejecutar dentro de un servidor.
    if ctx.guild is None:
        return await ctx.send(
            "Este comando solo puede utilizarse en un servidor.",
            ephemeral=True
        )

    # Control de permisos: solo personal autorizado.
    permisos = ctx.author.guild_permissions

    if not (
        permisos.manage_roles
        or permisos.administrator
    ):
        return await ctx.send(
            "No tienes permiso para conceder condecoraciones.",
            ephemeral=True
        )

    if usuario.bot:
        return await ctx.send(
            "No puedes conceder condecoraciones a bots.",
            ephemeral=True
        )

    if usuario.id == ctx.author.id:
        return await ctx.send(
            "No puedes concederte una condecoración a ti mismo.",
            ephemeral=True
        )

    # Comprobar que la medalla existe en el catálogo.
    nombre_oficial, materiales = buscar_medalla(medalla)

    if nombre_oficial is None:
        return await ctx.send(
            "Medalla no reconocida. Comprueba el nombre "
            "en el catálogo oficial.",
            ephemeral=True
        )

    material_limpio = material.strip()
    material_normalizado = normalizar(material_limpio)

    # Determinar el nombre exacto del rol que se concederá.
    if materiales is None:
        if material_normalizado not in (
            "ninguno", "sin material", "n/a"
        ):
            return await ctx.send(
                "Esta medalla no tiene variantes de material. "
                "Escribe `Ninguno` en el campo material.",
                ephemeral=True
            )

        nombre_rol = nombre_oficial
        material_mostrado = "No especificado"

    else:
        materiales_validos = {
            normalizar(m): m for m in materiales
        }

        if material_normalizado not in materiales_validos:
            disponibles = ", ".join(materiales)
            return await ctx.send(
                f"Material no válido para esta medalla. "
                f"Opciones: {disponibles}.",
                ephemeral=True
            )

        material_mostrado = materiales_validos[
            material_normalizado
        ]

        nombre_rol = (
            f"{nombre_oficial} ({material_mostrado})"
        )

    # Buscar el rol en el servidor.
    rol = buscar_rol(ctx.guild, nombre_rol)

    if rol is None:
        return await ctx.send(
            f"No encuentro el rol `{nombre_rol}`. "
            "Crea ese rol en Discord con ese nombre exacto.",
            ephemeral=True
        )

    # Comprobar los permisos y la jerarquía del bot.
    bot_member = ctx.guild.me

    if not bot_member.guild_permissions.manage_roles:
        return await ctx.send(
            "El bot necesita el permiso Gestionar roles.",
            ephemeral=True
        )

    if rol >= bot_member.top_role:
        return await ctx.send(
            "Mi rol está por debajo de la condecoración. "
            "Sube el rol del bot por encima de los roles "
            "de las medallas.",
            ephemeral=True
        )

    if rol in usuario.roles:
        return await ctx.send(
            f"{usuario.mention} ya tiene esta condecoración.",
            ephemeral=True
        )

    # Conceder la condecoración.
    try:
        await usuario.add_roles(
            rol,
            reason=(
                f"Condecoración de la RDA. Motivo: {motivo}. "
                f"Firma: {firma}. Concedida por {ctx.author}."
            )
        )
    except discord.Forbidden:
        return await ctx.send(
            "Discord ha rechazado la operación. "
            "Comprueba los permisos y la jerarquía de roles.",
            ephemeral=True
        )
    except discord.HTTPException:
        return await ctx.send(
            "Ha ocurrido un error al asignar la condecoración.",
            ephemeral=True
        )

    # Crear el registro oficial.
    embed = discord.Embed(
        title="🏅 Condecoración oficial concedida",
        description=(
            f"Se ha concedido una condecoración a "
            f"{usuario.mention}."
        ),
        color=discord.Color.dark_green()
    )

    embed.add_field(
        name="Condecorado",
        value=f"{usuario.mention}\n`{usuario.id}`",
        inline=False
    )

    embed.add_field(
        name="Condecoración",
        value=nombre_oficial,
        inline=False
    )

    embed.add_field(
        name="Material",
        value=material_mostrado,
        inline=True
    )

    embed.add_field(
        name="Motivo",
        value=motivo[:1024],
        inline=False
    )

    embed.add_field(
        name="Firma oficial",
        value=firma[:1024],
        inline=False
    )

    embed.add_field(
        name="Concedida por",
        value=ctx.author.mention,
        inline=False
    )

    embed.set_footer(
        text="Deutsche Demokratische Republik • Registro de condecoraciones"
    )

    await ctx.send(embed=embed)


# ==================================================
# EJECUCIÓN
# ==================================================

if not TOKEN:
    raise RuntimeError(
        "Falta la variable de entorno TOKEN en Bot-Hosting."
    )

bot.run(TOKEN)
