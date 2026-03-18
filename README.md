# Assistant Carrière IA (Bot Telegram)

Ce projet est un bot Telegram propulsé par l'IA (via OpenRouter) conçu pour aider les candidats dans leur recherche d'emploi. Il propose deux modes principaux : un **Simulateur d'Entretien** et un **Coach CV**.

## Fonctionnalités

### Mode 1 : Simulateur d'Entretien
Un jeu de rôle interactif avec un recruteur virtuel.
- **Analyse contextuelle** : Le bot croise votre CV, la fiche de poste et le profil psychologique (persona) du recruteur.
- **Entretien conversationnel** : Le bot vous pose des questions ciblées comme lors d'un vrai recrutement.
- **Feedback en direct** : À chaque réponse que vous donnez, l'IA vous fait un retour constructif en aparté avant de poser sa question suivante.
- **Bilan final détaillé** : Points forts, axes d'amélioration, suggestions concrètes de reformulation de vos réponses et une note globale sur 10.

### Mode 2 : Coach CV
Une analyse pointue pour maximiser vos chances de décrocher un entretien pour un poste précis.
- **Extraction intelligente** : Lit la fiche de poste et identifie les compétences clés et attentes de l'entreprise.
- **Analyse de compatibilité** : Compare votre CV à la fiche de poste en ciblant ce qui correspond et ce qui manque.
- **Suggestions de reformulation** : Propose des réécritures exactes de phrases de votre CV pour mieux coller à l'offre.
- **Message LinkedIn** : Génère un message d'approche personnalisé et prêt à être envoyé pour contacter un employé de l'entreprise visée.

---

## Installation

### 1. Prérequis
- **Python 3.8** ou supérieur.
- Un compte Telegram.
- Un **Token de bot Telegram** (à créer gratuitement en parlant à [@BotFather](https://t.me/botfather) sur Telegram).
- Une **Clé API OpenRouter** (à générer sur [OpenRouter.ai](https://openrouter.ai/)).

### 2. Cloner ou télécharger le projet
Récupérez les fichiers de ce projet sur votre ordinateur et ouvrez un terminal dans ce dossier.

### 3. Installer les dépendances
Installez les bibliothèques Python nécessaires via `pip` :
```bash
pip install python-telegram-bot openai python-dotenv
```

### 4. Configuration des clés d'API
Créez un fichier nommé exactement `.env` à la racine de votre dossier et ajoutez-y vos identifiants :
```env
TELEGRAM_TOKEN=votre_token_telegram_ici
OPENROUTER_KEY=votre_cle_api_openrouter_ici
```

---

## Utilisation

### 1. Lancer le Bot
Dans votre terminal, lancez le fichier principal :
```bash
python bot.py
```
Si tout est bien configuré, le terminal affichera : `Démarrage du bot en mode polling...`

### 2. Parler au Bot
Ouvrez Telegram, cherchez votre bot (via le nom que vous lui avez donné sur BotFather) et lancez-le avec la commande `/start`. Laissez-vous ensuite guider par les boutons interactifs !

### Liste des Commandes
- `/start` : Démarre le bot et affiche le menu de choix de mode.
- `/setcv` : Permet d'envoyer votre CV au format `.md`.
- `/setfiche` : Permet d'envoyer la fiche de poste visée au format `.md`.
- `/setinterviewer` : Permet d'envoyer le profil du recruteur au format `.md` (requis uniquement pour le simulateur d'entretien).
- `/entretien` : Lance le simulateur d'entretien (après avoir fourni les 3 documents).
- `/stop` : Arrête l'entretien en cours et génère le bilan complet.
- `/cv` : Lance l'analyse de compatibilité CV / Fiche de poste.
- `/linkedin` : Génère le message de networking LinkedIn personnalisé.

**Note sur les documents :** Le bot n'accepte actuellement que des fichiers texte brut au format **Markdown (`.md`)**. Convertissez vos PDF/Word en texte avant de les fournir au bot !