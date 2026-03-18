import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
from openai import AsyncOpenAI

# Chargement des variables d'environnement
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")

# Configuration des logs pour suivre d'éventuelles erreurs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Initialisation du client OpenAI asynchrone branché sur OpenRouter
# J'utilise le modèle Meta Llama 3 (tu peux changer par un modèle Anthropic si tu as les accès)
OPENROUTER_MODEL = "meta-llama/llama-3.1-70b-instruct"
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_KEY,
)

# ==========================================
# ÉTAPE A : Commandes de base et documents
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /start : Accueil l'utilisateur."""
    keyboard = [
        [
            InlineKeyboardButton("🎙️ Simulateur d'Entretien", callback_data='mode_interview'),
            InlineKeyboardButton("📝 Coach CV", callback_data='mode_coach')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Bienvenue ! Que souhaitez-vous faire aujourd'hui ?\n\n"
        "Choisissez le mode qui vous intéresse :",
        reply_markup=reply_markup
    )

async def mode_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère le choix du mode via les boutons inline."""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'mode_interview':
        context.user_data['mode'] = 'interview'
        text = (
            "🎙️ Mode Simulateur d'Entretien sélectionné !\n\n"
            "J'ai besoin de trois fichiers (.md) :\n"
            "1. /setcv : pour me donner ton CV.\n"
            "2. /setfiche : pour me donner la fiche de poste.\n"
            "3. /setinterviewer : pour définir le profil du recruteur.\n\n"
            "Une fois les 3 fichiers fournis, tape /entretien pour commencer !"
        )
    elif query.data == 'mode_coach':
        context.user_data['mode'] = 'coach'
        text = (
            "📝 Mode Coach CV sélectionné !\n\n"
            "J'ai besoin de deux fichiers (.md) :\n"
            "1. /setcv : pour me donner ton CV.\n"
            "2. /setfiche : pour me donner la fiche de poste.\n\n"
            "Une fois fournis, utilise :\n"
            "👉 /cv pour analyser le matching CV/Fiche.\n"
            "👉 /linkedin pour générer un message d'approche personnalisé."
        )
    
    await query.edit_message_text(text=text)

async def setcv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['expected_file'] = 'cv'
    await update.message.reply_text("Veuillez envoyer votre CV au format .md.")

async def setfiche(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['expected_file'] = 'fiche'
    await update.message.reply_text("Veuillez envoyer la fiche de poste au format .md.")

async def setinterviewer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['expected_file'] = 'interviewer'
    await update.message.reply_text("Veuillez envoyer le profil de l'interviewer au format .md.")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la réception des fichiers document (.md)."""
    expected = context.user_data.get('expected_file')
    
    if not expected:
        await update.message.reply_text("Merci d'utiliser d'abord /setcv, /setfiche ou /setinterviewer avant d'envoyer un fichier.")
        return

    document = update.message.document
    if not document.file_name.endswith('.md'):
        await update.message.reply_text("❌ Erreur : Je n'accepte que les fichiers au format .md.")
        return

    # Téléchargement asynchrone du fichier en mémoire
    file = await context.bot.get_file(document.file_id)
    file_bytes = await file.download_as_bytearray()
    
    # Lecture du contenu textuel du fichier markdown
    content = file_bytes.decode('utf-8')
    
    # Enregistrement dans la bonne clé du context (cv, fiche ou interviewer)
    context.user_data[expected] = content
    context.user_data['expected_file'] = None
    
    await update.message.reply_text(f"✅ Le document pour '{expected}' a été enregistré avec succès !")

# ==========================================
# ÉTAPE B : Initialisation & Commande /entretien
# ==========================================

async def entretien(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lance l'entretien en générant le persona et la phrase d'accroche."""
    required_keys = ['cv', 'fiche', 'interviewer']
    missing = [key for key in required_keys if key not in context.user_data]
    
    if missing:
        await update.message.reply_text(f"⚠️ Il manque des documents : {', '.join(missing)}. Utilise les commandes /set... pour les fournir.")
        return

    await update.message.reply_text("⏳ Création de l'interviewer et préparation de l'entretien en cours...")

    # 1. Appel LLM pour créer le persona à partir de la fiche et du profil
    persona_prompt = (
        f"Voici la fiche de poste :\n{context.user_data['fiche']}\n\n"
        f"Voici ton profil initial d'interviewer :\n{context.user_data['interviewer']}\n\n"
        "Fusionne ces informations pour définir ton 'persona' interne pour l'entretien."
    )
    
    persona_response = await client.chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=[
            {"role": "system", "content": "Tu es un assistant IA spécialisé dans le recrutement."},
            {"role": "user", "content": persona_prompt}
        ]
    )
    
    context.user_data['persona'] = persona_response.choices[0].message.content
    context.user_data['history'] = []

    # 2. Appel LLM pour générer la toute première phrase d'accroche
    greeting_prompt = (
        f"Le candidat vient d'entrer. Voici son CV :\n{context.user_data['cv']}\n"
        "Génère UNIQUEMENT ta toute première phrase d'accroche ou question pour lancer l'entretien "
        "en respectant ton persona."
    )
    
    greeting_response = await client.chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=[
            {"role": "system", "content": f"Tu es l'interviewer défini ici : {context.user_data['persona']}"},
            {"role": "user", "content": greeting_prompt}
        ]
    )
    
    first_message = greeting_response.choices[0].message.content
    context.user_data['history'].append({"role": "assistant", "content": first_message})
    
    await update.message.reply_text("🎙️ L'entretien commence ! \n💡 Astuce : Vous pouvez taper /stop à tout moment pour y mettre fin et obtenir un bilan complet.")
    await update.message.reply_text(first_message)

# ==========================================
# ÉTAPE C : Boucle de conversation (Feedback / Questions)
# ==========================================

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère les réponses du candidat pendant l'entretien."""
    if 'history' not in context.user_data:
        # Ignore si aucun entretien n'est en cours (le start ou d'autres textes)
        return

    user_text = update.message.text
    context.user_data['history'].append({"role": "user", "content": user_text})
    
    # System prompt strict forçant le format en deux parties
    sys_prompt = f"""Tu es un recruteur professionnel menant un entretien d'embauche.
Ton persona : {context.user_data['persona']}
Fiche de poste : {context.user_data['fiche']}
CV du candidat : {context.user_data['cv']}

IMPORTANT : À chaque réponse du candidat, tu DOIS structurer ta réponse en DEUX parties strictes :
1. D'abord un feedback constructif en aparté sur sa réponse, qui commence EXTREMEMENT STRICTEMENT par '💬 Feedback :'
2. Ensuite, à la ligne (fais un double saut de ligne), la question suivante du recruteur dans son persona pour continuer l'entretien."""

    messages_to_send = [{"role": "system", "content": sys_prompt}] + context.user_data['history']
    
    # J'indique à l'utilisateur que le LLM est en train d'écrire
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    try:
        response = await client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=messages_to_send
        )
        
        bot_reply = response.choices[0].message.content
        context.user_data['history'].append({"role": "assistant", "content": bot_reply})
        
        await update.message.reply_text(bot_reply)
    except Exception as e:
        logging.error(f"Erreur lors de l'appel OpenRouter : {e}")
        await update.message.reply_text("❌ Une erreur est survenue lors de l'analyse de ta réponse.")

# ==========================================
# ÉTAPE D : La commande /stop et le bilan
# ==========================================

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Termine l'entretien et génère le bilan final."""
    if 'history' not in context.user_data:
        await update.message.reply_text("Aucun entretien n'est en cours. Tape /entretien pour en démarrer un.")
        return

    await update.message.reply_text("🏁 Entretien terminé. Génération de votre bilan final en cours...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    sys_prompt = """Tu es un expert RH de très haut niveau. Sors totalement de ton persona d'interviewer. 
L'entretien est terminé. Tu as l'historique complet de la conversation.
Rédige un bilan final EXTRÊMEMENT COMPLET, DÉTAILLÉ et VISUELLEMENT AGRÉABLE en Markdown.
Utilise des émojis pour structurer le contenu et le rendre attrayant. Le bilan doit OBLIGATOIREMENT contenir :
- 🌟 Évaluation générale : un résumé de l'impression laissée par le candidat.
- 💪 Points forts : ce qui a été particulièrement bien géré (attitude, réponses précises, etc.).
- 🎯 Axes d'amélioration : ce qui a manqué ou peut être optimisé.
- 🔍 Analyse de moments clés : reprends 2 à 3 réponses du candidat. Explique ce qui allait ou n'allait pas, et propose une MEILLEURE reformulation concrète (plus impactante ou plus pro).
- 🏆 Note finale justifiée sur 10 et un ultime conseil pour ses futurs entretiens."""

    messages_to_send = [{"role": "system", "content": sys_prompt}] + context.user_data['history']

    try:
        response = await client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=messages_to_send
        )
        
        bilan = response.choices[0].message.content
        # On renvoie le texte sans parse_mode strict car le Markdown renvoyé par le LLM peut 
        # casser le parser V2 très rigide de Telegram. L'application native gère très bien ce rendu direct.
        await update.message.reply_text(bilan)
        
        # Nettoyage de l'historique pour un prochain entretien
        del context.user_data['history']
        
    except Exception as e:
        logging.error(f"Erreur lors de la génération du bilan : {e}")
        await update.message.reply_text("❌ Une erreur est survenue lors de la création du bilan.")

# ==========================================
# ÉTAPE E : Le Coach CV
# ==========================================

async def cv_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lance l'analyse Coach CV en deux étapes."""
    if 'cv' not in context.user_data or 'fiche' not in context.user_data:
        await update.message.reply_text("⚠️ Il me faut ton CV (/setcv) et la fiche de poste (/setfiche) avant de lancer l'analyse.")
        return

    await update.message.reply_text("⏳ Étape 1/2 : Analyse et extraction de la fiche de poste en cours...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    # Premier appel LLM — extraction
    extract_prompt = f"Voici une fiche de poste :\n{context.user_data['fiche']}\n\nExtrais de manière synthétique :\n1. Les compétences techniques et soft skills requises.\n2. Les mots-clés importants.\n3. Le contexte de l'entreprise et les défis du poste.\nNe renvoie que cette extraction."

    try:
        extract_response = await client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[{"role": "user", "content": extract_prompt}]
        )
        extraction = extract_response.choices[0].message.content
        context.user_data['extraction_fiche'] = extraction

        await update.message.reply_text("✅ Extraction terminée.\n⏳ Étape 2/2 : Comparaison avec ton CV en cours...")
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

        # Deuxième appel LLM — comparaison
        compare_prompt = f"Tu es un Coach Carrière expert.\nVoici l'extraction des attentes du poste :\n{extraction}\n\nVoici le CV du candidat :\n{context.user_data['cv']}\n\nFais une analyse structurée en 3 parties distinctes :\n✅ Ce qui correspond déjà dans le CV (points forts alignés avec le poste).\n⚠️ Ce qui manque ou est mal mis en valeur.\n✏️ Suggestions de reformulation concrètes (propose 3 à 5 réécritures exactes de phrases du CV pour mieux coller à l'offre)."

        compare_response = await client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[{"role": "user", "content": compare_prompt}]
        )
        analysis = compare_response.choices[0].message.content
        await update.message.reply_text(analysis)
        
    except Exception as e:
        logging.error(f"Erreur lors de l'analyse CV : {e}")
        await update.message.reply_text("❌ Une erreur est survenue lors de l'analyse de votre CV.")

async def linkedin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Génère un message d'approche LinkedIn."""
    if 'cv' not in context.user_data or 'fiche' not in context.user_data:
        await update.message.reply_text("⚠️ Il me faut ton CV (/setcv) et la fiche de poste (/setfiche) pour créer le message LinkedIn.")
        return
    
    await update.message.reply_text("⏳ Génération de votre message LinkedIn d'approche en cours...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    prompt = f"Tu es un expert en networking. Rédige un message LinkedIn direct et percutant (max 300 caractères) pour le candidat afin d'approcher un collaborateur de l'entreprise.\nLe message doit s'appuyer sur la fiche de poste :\n{context.user_data['fiche']}\nEt le profil du candidat :\n{context.user_data['cv']}\nNe fournis que le message prêt à copier-coller."

    try:
        response = await client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        message = response.choices[0].message.content
        await update.message.reply_text(f"👔 Proposition de message LinkedIn :\n\n{message}")
    except Exception as e:
        logging.error(f"Erreur LinkedIn : {e}")
        await update.message.reply_text("❌ Une erreur est survenue lors de la génération du message.")

# ==========================================
# FONCTION PRINCIPALE
# ==========================================

def main():
    """Initialise et lance le bot Telegram."""
    if not TELEGRAM_TOKEN:
        logging.error("TELEGRAM_TOKEN manquant dans le fichier .env")
        return

    # Construction de l'application (v20+)
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Enregistrement des handlers pour les commandes
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setcv", setcv))
    application.add_handler(CommandHandler("setfiche", setfiche))
    application.add_handler(CommandHandler("setinterviewer", setinterviewer))
    application.add_handler(CommandHandler("entretien", entretien))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("cv", cv_analysis))
    application.add_handler(CommandHandler("linkedin", linkedin_message))

    # Handler pour les boutons inline de la commande /start
    application.add_handler(CallbackQueryHandler(mode_selection))

    # Handler pour attraper les documents (fichiers .md)
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # Handler pour attraper le texte libre (hors commandes) de l'utilisateur
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Lancement en mode Polling
    logging.info("Démarrage du bot en mode polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
