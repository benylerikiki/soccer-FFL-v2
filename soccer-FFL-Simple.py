import streamlit as st
import pandas as pd
import os
import shutil
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image, ImageDraw, ImageFont
import io
import itertools
import re
import base64
from github import Github, GithubException

# Fichiers requis
DATA_FILE = 'database_joueurs_v2.xlsx'       
BACKUP_FILE = 'database_joueurs_v2_backup.xlsx'
BLUE_CARD_PATH = 'card_blue.png'
RED_CARD_PATH = 'card_red.png'
YELLOW_CARD_PATH = 'card_yellow.png'
FONT_PATH = 'FootballAttack.otf'
LOGO_PATH = 'icon_ffl.png'
IMAGE_PATH = 'Intro.jpeg'

# --- 1. CHARGEMENT DE L'ICÔNE ---
app_icon = "⚽"
if os.path.exists(LOGO_PATH):
    try:
        app_icon = Image.open(LOGO_PATH)
    except Exception:
        app_icon = "⚽"

st.set_page_config(
    page_title="Soccer FFL Kompo", 
    page_icon=app_icon, 
    layout="wide"
)

# --- 2. CSS & PWA FIX ---
if os.path.exists(LOGO_PATH):
    with open(LOGO_PATH, "rb") as f:
        icon_bytes = f.read()
    icon_b64 = base64.b64encode(icon_bytes).decode('utf-8')
    
    pwa_javascript_fix = f"""
        <script>
            var link = document.querySelector("link[rel*='icon']") || document.createElement('link');
            link.type = 'image/png';
            link.rel = 'shortcut icon';
            link.href = 'data:image/png;base64,{icon_b64}';
            document.getElementsByTagName('head')[0].appendChild(link);

            var appleLink = document.createElement('link');
            appleLink.rel = 'apple-touch-icon';
            appleLink.sizes = '180x180';
            appleLink.href = 'data:image/png;base64,{icon_b64}';
            document.getElementsByTagName('head')[0].appendChild(appleLink);
        </script>
    """
    st.markdown(pwa_javascript_fix, unsafe_allow_html=True)

st.markdown(
    """
    <style>
    @media (max-width: 768px) {
        div[data-testid="stHorizontalBlock"]:has(div[data-testid="stCheckbox"]) {
            display: grid !important;
            grid-template-columns: repeat(3, 1fr) !important;
            gap: 8px !important;
        }
        div[data-testid="stHorizontalBlock"]:has(div[data-testid="stCheckbox"]) > div[data-testid="stColumn"] {
            width: 100% !important;
            max-width: 100% !important;
            min-width: 0 !important;
            flex: none !important;
        }
        div[data-testid="stCheckbox"] label {
            font-size: 13px !important;
        }
    }

    .landing-wrapper {
        position: relative;
        width: 100%;
        max-width: 900px;
        margin: 0 auto;
        display: flex;
        justify-content: center;
    }
    .landing-img {
        width: 100%;
        max-height: 80vh;
        object-fit: contain;
        border-radius: 16px;
        box-shadow: 0 6px 25px rgba(0,0,0,0.6);
    }
    div[data-testid="stElementContainer"]:has(button[key="overlay_enter_btn"]) {
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        width: 100% !important;
        height: 100% !important;
        z-index: 10 !important;
    }
    button[key="overlay_enter_btn"] {
        width: 100% !important;
        height: 100% !important;
        background: transparent !important;
        border: none !important;
        color: transparent !important;
        cursor: pointer !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- INITIALISATION DE L'ÉTAT DE L'APPLICATION ---
if 'show_landing' not in st.session_state:
    st.session_state['show_landing'] = True

if 'db_editor_version' not in st.session_state:
    st.session_state['db_editor_version'] = 0

if 'auto_selected' not in st.session_state:
    st.session_state.auto_selected = set()

NUMERIC_OPTIONS = list(range(1, 11))

def push_file_to_github(file_path: str, content_bytes: bytes, commit_message: str) -> bool:
    """Pousse un fichier sur GitHub via l'API pour assurer la persistance permanente."""
    token = st.secrets.get("GITHUB_TOKEN")
    repo_name = st.secrets.get("GITHUB_REPO")
    branch = st.secrets.get("GITHUB_BRANCH", "main")

    if not token or not repo_name:
        return False

    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        try:
            file_content = repo.get_contents(file_path, ref=branch)
            repo.update_file(
                path=file_content.path,
                message=commit_message,
                content=content_bytes,
                sha=file_content.sha,
                branch=branch
            )
        except GithubException as ge:
            if ge.status == 404:
                repo.create_file(
                    path=file_path,
                    message=commit_message,
                    content=content_bytes,
                    branch=branch
                )
            else:
                raise ge
        return True
    except Exception as e:
        st.error(f"❌ Erreur lors de la synchronisation GitHub : {e}")
        return False

def text_to_score(val):
    """Convertit n'importe quelle valeur en entier strict entre 1 et 10."""
    if pd.isna(val):
        return 5
    match = re.search(r'\d+', str(val))
    if match:
        return max(1, min(10, int(match.group())))
    return 5

def calculate_global_score(row):
    """Calcule la moyenne numérique directe des 4 compétences."""
    att = text_to_score(row.get("Attaque", 5))
    defe = text_to_score(row.get("Défense", 5))
    gk = text_to_score(row.get("Gardien", 5))
    col = text_to_score(row.get("Collectif", 5))
    avg = (att + defe + gk + col) / 4.0
    return round(avg, 1)

def load_data():
    """Charge la dernière version du fichier Excel physique."""
    if os.path.exists(DATA_FILE):
        try: 
            df = pd.read_excel(DATA_FILE)
            if "Surnoms" not in df.columns:
                df["Surnoms"] = ""
            if "Gardien" not in df.columns:
                df["Gardien"] = 5
                
            df["Surnoms"] = df["Surnoms"].fillna("").astype(str)
            
            for col in ["Attaque", "Défense", "Gardien", "Collectif"]:
                if col in df.columns:
                    df[col] = df[col].apply(text_to_score)
                else:
                    df[col] = 5
                    
            ordered_cols = ["Nom du Joueur", "Attaque", "Défense", "Gardien", "Collectif", "Surnoms"]
            existing = [c for c in ordered_cols if c in df.columns]
            return df[existing]
        except Exception as e: 
            st.error(f"Erreur lors de la lecture de {DATA_FILE} : {e}")
            
    return pd.DataFrame({
        "Nom du Joueur": ["Antho", "Cyril V", "Apou", "Benoit", "Nico P", "Mouyss", "Cédric", "Nico M", "David", "Cyril L"],
        "Attaque": [9, 5, 7, 9, 5, 7, 3, 7, 5, 3],
        "Défense": [5, 9, 5, 3, 9, 3, 9, 5, 7, 7],
        "Gardien": [3, 5, 7, 3, 7, 5, 9, 3, 5, 5],
        "Collectif": [7, 9, 7, 5, 7, 5, 7, 5, 5, 5],
        "Surnoms": ["", "Cyril", "", "beny", "nicop, nico", "mouys", "", "nicom, nico", "Dav, dimeh", "Cyril"]
    })

def save_data(df):
    """Crée un backup local, écrit le fichier Excel et synchronise sur GitHub."""
    if os.path.exists(DATA_FILE):
        try:
            shutil.copyfile(DATA_FILE, BACKUP_FILE)
        except Exception as e:
            st.warning(f"⚠️ Impossible de créer le backup : {e}")

    clean_df = df.copy()
    if "Note Globale" in clean_df.columns:
        clean_df = clean_df.drop(columns=["Note Globale"])
    if "is_joker" in clean_df.columns:
        clean_df = clean_df.drop(columns=["is_joker"])
        
    for col in ["Attaque", "Défense", "Gardien", "Collectif"]:
        if col in clean_df.columns:
            clean_df[col] = clean_df[col].apply(text_to_score)
            
    ordered_cols = ["Nom du Joueur", "Attaque", "Défense", "Gardien", "Collectif", "Surnoms"]
    existing_cols = [c for c in ordered_cols if c in clean_df.columns]
    other_cols = [c for c in clean_df.columns if c not in ordered_cols]
    clean_df = clean_df[existing_cols + other_cols]
    
    clean_df.to_excel(DATA_FILE, index=False)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        clean_df.to_excel(writer, index=False)
    buffer.seek(0)

    if push_file_to_github(DATA_FILE, buffer.getvalue(), "Mise à jour base joueurs [via Soccer FFL]"):
        st.toast("Base synchronisée sur GitHub !", icon="☁️")

if 'players_df' not in st.session_state:
    st.session_state.players_df = load_data()

# ==========================================
# 🖼️ PAGE DE GARDE
# ==========================================
if st.session_state.get('show_landing', True):
    if os.path.exists(IMAGE_PATH):
        with open(IMAGE_PATH, "rb") as f:
            img_bytes = f.read()
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        
        st.markdown(
            f"""
            <div class="landing-wrapper">
                <img class="landing-img" src="data:image/jpeg;base64,{img_b64}" alt="Soccer FFL Kompo Intro">
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        if st.button("Entrer dans l'application", key="overlay_enter_btn"):
            st.session_state['show_landing'] = False
            st.rerun()

        st.markdown("<p style='text-align: center; color: #888; margin-top: 15px;'>👆 Cliquez sur l'image pour accéder aux compositions</p>", unsafe_allow_html=True)
    else:
        st.warning(f"⚠️ Fichier d'image introuvable (`{IMAGE_PATH}`).")
        if st.button("🚀 ENTRER DANS L'APPLICATION", type="primary"):
            st.session_state['show_landing'] = False
            st.rerun()

    st.stop()

# ==========================================
# ⚽ FONCTIONS DU TERRAIN & DIALOGS
# ==========================================
def create_player_card(card_path, player_name):
    if not os.path.exists(card_path):
        return None
    
    card_img = Image.open(card_path).convert("RGBA")
    draw = ImageDraw.Draw(card_img)
    w, h = card_img.size
    
    y_pos = int(h * (2 / 3))
    font_size = max(24, int(w * 0.18))
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except Exception:
        font = ImageFont.load_default()
        
    text_bbox = draw.textbbox((0, 0), player_name.upper(), font=font)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]
    
    x_pos = (w - text_w) / 2
    y_pos_centered = y_pos - (text_h / 2)
    
    stroke_w = max(2, int(font_size * 0.07))
    draw.text((x_pos, y_pos_centered), player_name.upper(), fill="white", font=font, stroke_width=stroke_w, stroke_fill="black")
    
    return card_img

def draw_combined_field(t1, t2):
    fig, ax = plt.subplots(figsize=(10, 6.5))
    fig.patch.set_facecolor('#226343')
    ax.set_facecolor('#226343')
    
    ax.plot([0, 100, 100, 0, 0], [0, 0, 60, 60, 0], color='white', linewidth=2.0)
    ax.plot([50, 50], [0, 60], color='white', linewidth=2.0)
    center_circle
