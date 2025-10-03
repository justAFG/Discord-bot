import discord
from discord.ext import commands
import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Bot-Konfiguration
TOKEN = os.getenv('DISCORD_TOKEN')
ADMIN_ROLE_ID = int(os.getenv('ADMIN_ROLE_ID'))
LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID'))

# Spezifische User ID für /ticket Befehl
SPECIAL_USER_ID = 974640038648365116

# Speicher für Bewerbungen
applications = {}
current_questions = {}

# Fragenliste
QUESTIONS = [
    "Was Ist ihr benutzername auf Roblox?",
    "Wieso wollen sie hier Admin werden?",
    "Was ist Frp ausgeschrieben und nenne 1 Beispiel.",
    "Was ist Rdm ausgeschrieben und nenne 1 Beispiel.",
    "Was ist Vdm ausgeschrieben und nenne 1 Beispiel.",
    "Was ist Combatlogging",
    "Was ist Power RP?",
    "Wie viele Stunden Pro Tag können Sie online sein?",
    "Wie würden Sie reagieren, wenn zwei Spieler sich im Chat streiten?",
    "Was würden Sie tun, wenn ein Freund von Ihnen gegen die Regeln verstößt?",
    "Wie gehen Sie damit um, wenn ein Spieler Sie persönlich beleidigt?",
    "Wenn zwei Spieler sich gegenseitig beschuldigen, aber keine Beweise vorliegen – wie handeln Sie?",
    "Was ist für Sie der Unterschied zwischen einem Warn und einem Bann?",
    "Wie gehen Sie vor, wenn mehrere Spieler gleichzeitig einen Notruf machen, aber Sie alleine Admin sind?",
    "What is Metagaming, und nennen Sie ein Beispiel.",
    "Ein Spieler verlässt absichtlich kurz vor seiner Festnahme das Spiel. Wie reagieren Sie?",
    "Welche Eigenschaften sind Ihrer Meinung nach wichtig für einen Admin?",
    "Wie stellen Sie sicher, dass Sie neutral bleiben, auch wenn es um Freunde geht?",
    "Ein sehr beliebter Spieler bricht Regeln. Würden Sie ihn trotzdem bestrafen? Begründen Sie Ihre Antwort.",
    "Was würden Sie tun, wenn Sie merken, dass ein anderer Admin seine Macht missbraucht?"
]

@bot.event
async def on_ready():
    print(f'{bot.user} ist online!')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Bewerbungen"))

@bot.event
async def on_guild_join(guild):
    # Erstelle das Bewerbungs-Panel beim Beitritt zum Server
    channel = guild.system_channel
    if channel:
        await create_panel(channel)

async def create_panel(channel):
    embed = discord.Embed(
        title="🚀 Admin Bewerbung starten",
        description="Klicke auf den Button unten, um deine Admin-Bewerbung zu starten!",
        color=0x00ff00
    )
    embed.add_field(
        name="📋 Informationen",
        value="• Du wirst per DM 20 Fragen beantworten\n• Die Bewerbung kann jederzeit abgebrochen werden\n• Antworte mit `abbrechen` um zu stoppen",
        inline=False
    )
    
    view = discord.ui.View()
    start_button = discord.ui.Button(style=discord.ButtonStyle.primary, label="Bewerbung starten", custom_id="start_application")
    view.add_item(start_button)
    
    await channel.send(embed=embed, view=view)

@bot.event
async def on_interaction(interaction):
    if interaction.type == discord.InteractionType.component:
        if interaction.data['custom_id'] == 'start_application':
            await start_application(interaction)

async def start_application(interaction):
    user = interaction.user
    
    if user.id in applications:
        await interaction.response.send_message("❌ Du hast bereits eine laufende Bewerbung!", ephemeral=True)
        return
    
    try:
        # Starte DM Konversation
        embed = discord.Embed(
            title="📄 Admin Bewerbung",
            description="Willkommen zu deiner Admin-Bewerbung! Bitte beantworte die folgenden 20 Fragen.\n\n**Du kannst jederzeit mit `abbrechen` die Bewerbung beenden.**",
            color=0x3498db
        )
        embed.set_footer(text="Antworte auf diese Nachricht mit deiner Antwort")
        
        dm_channel = await user.create_dm()
        await dm_channel.send(embed=embed)
        
        # Starte den Bewerbungsprozess
        applications[user.id] = {
            'answers': [],
            'current_question': 0,
            'start_time': datetime.now(),
            'username': str(user),
            'display_name': user.display_name
        }
        current_questions[user.id] = 0
        
        await send_next_question(user.id)
        await interaction.response.send_message("✅ Bewerbung gestartet! Bitte checke deine DMs.", ephemeral=True)
        
    except discord.Forbidden:
        await interaction.response.send_message("❌ Ich kann dir keine DMs senden! Bitte aktiviere DMs von Server-Mitgliedern.", ephemeral=True)

async def send_next_question(user_id):
    if user_id not in applications:
        return
    
    app_data = applications[user_id]
    current_q = app_data['current_question']
    
    if current_q >= len(QUESTIONS):
        await finish_application(user_id)
        return
    
    user = await bot.fetch_user(user_id)
    dm_channel = await user.create_dm()
    
    embed = discord.Embed(
        title=f"Frage {current_q + 1}/20",
        description=QUESTIONS[current_q],
        color=0x3498db
    )
    embed.set_footer(text=f"Fortschritt: {current_q + 1}/20 • Antworte mit 'abbrechen' um zu stoppen")
    
    await dm_channel.send(embed=embed)

async def finish_application(user_id):
    if user_id not in applications:
        return
    
    app_data = applications[user_id]
    user = await bot.fetch_user(user_id)
    
    # Sende Bestätigung an User
    embed = discord.Embed(
        title="✅ Bewerbung abgeschlossen",
        description="Vielen Dank für deine Bewerbung! Sie wurde an das Admin-Team weitergeleitet.",
        color=0x00ff00
    )
    dm_channel = await user.create_dm()
    await dm_channel.send(embed=embed)
    
    # Sende Bewerbung an Log-Channel
    await send_application_to_admins(user_id)
    
    # Bereinige Daten
    del applications[user_id]
    if user_id in current_questions:
        del current_questions[user_id]

async def send_application_to_admins(user_id):
    if user_id not in applications:
        return
    
    app_data = applications[user_id]
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    
    if not log_channel:
        print("Log-Channel nicht gefunden!")
        return
    
    # Berechne Dauer
    duration = datetime.now() - app_data['start_time']
    minutes, seconds = divmod(int(duration.total_seconds()), 60)
    
    # Erstelle Embed für die Bewerbung
    embed = discord.Embed(
        title="📄 Neue Admin Bewerbung",
        color=0x3498db,
        timestamp=datetime.now()
    )
    embed.add_field(name="👤 Bewerber", value=f"{app_data['username']}\n({app_data['display_name']})", inline=True)
    embed.add_field(name="⏱️ Dauer", value=f"{minutes}m {seconds}s", inline=True)
    embed.add_field(name="🆔 User ID", value=user_id, inline=True)
    
    # Füge Antworten hinzu
    for i, answer in enumerate(app_data['answers']):
        question_text = QUESTIONS[i] if i < len(QUESTIONS) else f"Frage {i+1}"
        # Kürze lange Antworten
        if len(answer) > 1024:
            answer = answer[:1021] + "..."
        embed.add_field(
            name=f"❓ {i+1}. {question_text[:200]}",
            value=answer or "*Keine Antwort*",
            inline=False
        )
    
    # Erstelle View mit Buttons
    view = discord.ui.View()
    
    accept_button = discord.ui.Button(style=discord.ButtonStyle.success, label="Annehmen", custom_id=f"accept_{user_id}")
    deny_button = discord.ui.Button(style=discord.ButtonStyle.danger, label="Ablehnen", custom_id=f"deny_{user_id}")
    accept_reason_button = discord.ui.Button(style=discord.ButtonStyle.primary, label="Annehmen mit Grund", custom_id=f"accept_reason_{user_id}")
    deny_reason_button = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Ablehnen mit Grund", custom_id=f"deny_reason_{user_id}")
    
    view.add_item(accept_button)
    view.add_item(deny_button)
    view.add_item(accept_reason_button)
    view.add_item(deny_reason_button)
    
    # Sende an Log-Channel (nur für Admins sichtbar)
    await log_channel.send(embed=embed, view=view)

@bot.event
async def on_message(message):
    # Ignoriere Bot-Nachrichten
    if message.author.bot:
        return
    
    # Handle DM Nachrichten für Bewerbungen
    if isinstance(message.channel, discord.DMChannel) and message.author.id in applications:
        await handle_application_response(message)
        return
    
    await bot.process_commands(message)

async def handle_application_response(message):
    user_id = message.author.id
    content = message.content.strip().lower()
    
    # Abbruch-Befehl
    if content == 'abbrechen':
        if user_id in applications:
            del applications[user_id]
        if user_id in current_questions:
            del current_questions[user_id]
        
        embed = discord.Embed(
            title="❌ Bewerbung abgebrochen",
            description="Deine Bewerbung wurde abgebrochen. Du kannst jederzeit eine neue starten.",
            color=0xff0000
        )
        await message.channel.send(embed=embed)
        return
    
    # Speichere Antwort
    if user_id in applications:
        app_data = applications[user_id]
        current_q = app_data['current_question']
        
        if current_q < len(QUESTIONS):
            app_data['answers'].append(message.content)
            app_data['current_question'] += 1
            
            # Bestätigung für Antwort
            embed = discord.Embed(
                title="✅ Antwort gespeichert",
                description=f"Antwort auf Frage {current_q + 1} wurde gespeichert.",
                color=0x00ff00
            )
            await message.channel.send(embed=embed)
            
            # Nächste Frage senden
            await send_next_question(user_id)

# Button Interactions für Admin-Aktionen
@bot.event
async def on_interaction(interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data['custom_id']
        
        # Start Button
        if custom_id == "start_application":
            await start_application(interaction)
            return
        
        # Admin Buttons
        if custom_id.startswith(("accept_", "deny_", "accept_reason_", "deny_reason_")):
            # Überprüfe Admin-Berechtigung
            if not any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles):
                await interaction.response.send_message("❌ Nur Admins können Bewerbungen bearbeiten!", ephemeral=True)
                return
            
            parts = custom_id.split('_')
            action = parts[0]
            user_id = int(parts[1])
            
            if action == "accept":
                await handle_application_decision(interaction, user_id, "angenommen", None)
            elif action == "deny":
                await handle_application_decision(interaction, user_id, "abgelehnt", None)
            elif action == "accept_reason":
                await request_reason(interaction, user_id, "annehmen")
            elif action == "deny_reason":
                await request_reason(interaction, user_id, "ablehnen")

async def handle_application_decision(interaction, user_id, decision, reason):
    try:
        user = await bot.fetch_user(user_id)
        
        embed = discord.Embed(
            title=f"📄 Bewerbung {decision}",
            color=0x00ff00 if decision == "angenommen" else 0xff0000
        )
        embed.add_field(name="Entscheidung", value=decision.capitalize(), inline=True)
        embed.add_field(name="Bearbeitet von", value=interaction.user.display_name, inline=True)
        if reason:
            embed.add_field(name="Grund", value=reason, inline=False)
        
        # Sende an User
        try:
            dm_channel = await user.create_dm()
            await dm_channel.send(embed=embed)
        except discord.Forbidden:
            pass
        
        # Update die ursprüngliche Nachricht
        original_embed = interaction.message.embeds[0]
        original_embed.color = 0x00ff00 if decision == "angenommen" else 0xff0000
        original_embed.add_field(name="📋 Status", value=f"{decision.capitalize()} von {interaction.user.mention}", inline=True)
        if reason:
            original_embed.add_field(name="📝 Grund", value=reason, inline=True)
        
        # Entferne die Buttons
        view = discord.ui.View()
        await interaction.message.edit(embed=original_embed, view=view)
        
        await interaction.response.send_message(f"✅ Bewerbung wurde {decision}.", ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Fehler: {str(e)}", ephemeral=True)

async def request_reason(interaction, user_id, action_type):
    modal = ReasonModal(user_id, action_type)
    await interaction.response.send_modal(modal)

class ReasonModal(discord.ui.Modal):
    def __init__(self, user_id, action_type):
        super().__init__(title=f"Bewerbung {action_type}")
        self.user_id = user_id
        self.action_type = action_type
        
        self.reason = discord.ui.TextInput(
            label="Grund",
            placeholder="Gib den Grund hier ein...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )
        self.add_item(self.reason)
    
    async def on_submit(self, interaction: discord.Interaction):
        decision = "angenommen" if self.action_type == "annehmen" else "abgelehnt"
        await handle_application_decision(interaction, self.user_id, decision, self.reason.value)

# Spezieller /ticket Befehl nur für bestimmte User ID
@bot.tree.command(name="ticket", description="Erstelle das Bewerbungs-Panel (Nur für bestimmte User)")
async def ticket(interaction: discord.Interaction):
    if interaction.user.id != SPECIAL_USER_ID:
        await interaction.response.send_message("❌ Du hast keine Berechtigung für diesen Befehl!", ephemeral=True)
        return
    
    await create_panel(interaction.channel)
    await interaction.response.send_message("✅ Bewerbungs-Panel wurde erstellt!", ephemeral=True)

# Befehl zum Erstellen des Bewerbungs-Panels (für Admins)
@bot.command()
@commands.has_role(ADMIN_ROLE_ID)
async def panel(ctx):
    await create_panel(ctx.channel)
    await ctx.send("✅ Bewerbungs-Panel wurde erstellt!", delete_after=5)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send("❌ Du hast keine Berechtigung für diesen Befehl!", delete_after=5)

# Sync der Slash Commands
@bot.event
async def on_connect():
    await bot.tree.sync()
    print("Slash Commands wurden gesynct")

if __name__ == "__main__":
    bot.run(TOKEN)
