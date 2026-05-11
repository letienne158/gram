# GRAM - Telegram Group & Channel Scanner

GRAM est un outil OSINT permettant de rechercher et analyser des groupes et canaux Telegram par mots-cles, via une interface web locale moderne. Il repose sur **Flask** pour le serveur web et **Telethon** pour l'interaction avec l'API Telegram.

> **Avertissement** : Cet outil est destine uniquement a des fins educatives et de recherche. L'utilisateur est seul responsable de l'usage qu'il en fait. Respectez les conditions d'utilisation de Telegram et la legislation en vigueur dans votre pays.

---

## Fonctionnalites

- Recherche de groupes et canaux Telegram par mots-cles (fichier `.txt`)
- Progression en temps reel avec barre de progression visuelle
- Rejoindre des groupes/canaux directement depuis l'interface
- Sauvegarde et organisation des resultats dans des projets
- Export des resultats en **CSV** et **JSON**
- Session persistante (reconnexion automatique au redemarrage)
- Interface web sombre et responsive

---

## Pre-requis

- **Python 3.8** ou superieur
- **Identifiants API Telegram** (api_id et api_hash) obtenus sur [my.telegram.org](https://my.telegram.org)

---

## Obtenir les identifiants API Telegram

1. Rendez-vous sur [https://my.telegram.org](https://my.telegram.org)
2. Connectez-vous avec votre numero de telephone Telegram
3. Cliquez sur **API development tools**
4. Remplissez le formulaire :
   - **App title** : un nom au choix (ex : `GRAM`)
   - **Short name** : un identifiant court (ex : `gram`)
   - **Platform** : Desktop
5. Validez, puis notez votre **api_id** (nombre) et votre **api_hash** (chaine de caracteres)

Ces identifiants seront demandes au premier lancement de GRAM.

---

## Installation

### Windows

```bash
# Cloner le depot
git clone https://github.com/votre-utilisateur/gram.git
cd gram

# Creer un environnement virtuel
python -m venv venv
venv\Scripts\activate

# Installer les dependances
pip install -r requirements.txt
```

### macOS

```bash
# Cloner le depot
git clone https://github.com/votre-utilisateur/gram.git
cd gram

# Creer un environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installer les dependances
pip install -r requirements.txt
```

### Linux (Ubuntu / Debian)

```bash
# Installer Python et pip si necessaire
sudo apt update
sudo apt install python3 python3-pip python3-venv git

# Cloner le depot
git clone https://github.com/votre-utilisateur/gram.git
cd gram

# Creer un environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installer les dependances
pip install -r requirements.txt
```

---

## Utilisation

### 1. Lancer le serveur

```bash
# Activer l'environnement virtuel si ce n'est pas deja fait
# Windows : venv\Scripts\activate
# macOS/Linux : source venv/bin/activate

python app.py
```

L'interface est accessible sur **http://localhost:5000**.

### 2. Se connecter a Telegram

- Renseignez votre **API ID**, **API Hash** et **numero de telephone**
- Un code de verification sera envoye sur votre application Telegram
- Saisissez le code (et le mot de passe 2FA si active)
- La session est sauvegardee pour les prochains lancements

### 3. Lancer une recherche

- Preparez un fichier de mots-cles (voir format ci-dessous)
- Uploadez le fichier via l'interface
- La recherche demarre automatiquement avec une progression en temps reel
- Les resultats s'affichent au fur et a mesure dans le tableau

### 4. Exploiter les resultats

- **Rejoindre** un groupe/canal en un clic
- **Sauvegarder** les resultats dans un projet pour les retrouver plus tard
- **Exporter** en CSV ou JSON pour une analyse externe

---

## Format du fichier de mots-cles

Fichier texte (`.txt`) avec un mot-cle par ligne :

```
crypto france
trading signal
bitcoin group
NFT communaute
```

Les lignes vides sont ignorees.

---

## Structure du projet

```
gram/
├── app.py              # Application principale (Flask + Telethon)
├── requirements.txt    # Dependances Python
├── templates/
│   └── index.html      # Interface web
├── data/               # Donnees locales (credentials, cache) - ignore par git
├── projects/           # Projets sauvegardes - ignore par git
├── keywords.txt        # Exemple de fichier de mots-cles
└── frword.txt          # Exemple de fichier de mots-cles FR
```

---

## Captures d'ecran

*A venir.*

---

## Licence

Ce projet est distribue sous licence **MIT**. Voir le fichier [LICENSE](LICENSE) pour plus de details.

---

## Avertissement legal

GRAM est un outil a vocation **educative et de recherche**. Il ne doit en aucun cas etre utilise a des fins malveillantes, de harcelement, d'espionnage ou en violation des conditions d'utilisation de Telegram. L'auteur decline toute responsabilite en cas d'usage abusif.
