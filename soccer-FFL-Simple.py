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
from datetime import datetime
from github import Github, GithubException

# Fichiers et dossiers requis
DATA_FILE = 'database_joueurs_v2.xlsx'       
BACKUP_FILE = 'database_joueurs_v2_backup.xlsx'
JOKERS_FILE = 'database_jokers.xlsx'
HISTORY_FILE = 'database_historique.xlsx'
DEFAULT_FONT_PATH = 'FootballAttack.otf'
LOGO_PATH = 'icon_ffl.png'
IMAGE_PATH = 'Intro.jpeg'
FUT_CARDS_DIR = 'cards_fut'
CARTE_FUT_DIR = 'carte_fut'  
CARTE_FUT_PREV_DIR = 'cartes_fut_prev'
PHOTO_JOUEUR_DIR = 'photo_joueur'
FONTS_DIR = 'fonts'

os.makedirs(FUT_CARDS_DIR, exist_ok=True)
os.makedirs(CARTE_FUT_DIR, exist_ok=True)
os.makedirs(CARTE_FUT_PREV_DIR, exist_ok=True)
os.makedirs(PHOTO_JOUEUR_DIR, exist_ok=True)
os.makedirs(FONTS_DIR, exist_ok=True)

if os.path.exists(DEFAULT_FONT_PATH):
    dest_default = os.path.join(FONTS_DIR, DEFAULT_FONT_PATH)
    if not os.path.exists(dest_default):
        shutil.copyfile(DEFAULT_FONT_PATH, dest_default)

# --- GESTION DES MINIATURES DE PRÉVISUALISATION (100px) ---
def resize_and_save_preview(source_path, target_dir=CARTE_FUT_PREV_DIR, target_width=100):
    try:
        filename = os.path.basename(source_path)
        target_path = os.path.join(target_dir, filename)
        if not os.path.exists(target_path) or os.path.getmtime(source_path) > os.path.getmtime(target_path):
            with Image.open(source_path) as img:
                w_percent = (target_width / float(img.size[0]))
                h_size = int(float(img.size[1]) * float(w_percent))
                img_resized = img.resize((target_width, h_size), Image.Resampling.LANCZOS)
                img_resized.save(target_path)
        return target_path
    except Exception:
        return source_path

def sync_all_previews():
    if os.path.exists(CARTE_FUT_DIR):
        for f in os.listdir(CARTE_FUT_DIR):
            if f.lower().endswith('.png'):
                resize_and_save_preview(os.path.join(CARTE_FUT_DIR, f))
    for default_c in ['card_blue.png', 'card_red.png', 'card_yellow.png']:
        if os.path.exists(default_c):
            resize_and_save_preview(default_c)

# --- GESTION DES JOUEURS & PHOTOS ---
def get_player_id(player_name: str) -> str:
    clean = re.sub(r'[^a-zA-Z0-9]', '_', str(player_name).strip().lower())
    return re.sub(r'_+', '_', clean).strip('_')

def get_player_photo_path(player_name: str) -> str:
    if not player_name:
        return None
    clean_name = re.sub(r'^joker\s+', '', str(player_name).strip().lower())
    pid = get_player_id(clean_name)
    
    for ext in ['.png', '.jpg', '.jpeg']:
        path = os.path.join(PHOTO_JOUEUR_DIR, f"{pid}{ext}")
        if os.path.exists(path):
            return path
        path_raw = os.path.join(PHOTO_JOUEUR_DIR, f"{get_player_id(player_name)}{ext}")
        if os.path.exists(path_raw):
            return path_raw
    return None

def text_to_score(val):
    if pd.isna(val):
        return 5
    match = re.search(r'\d+', str(val))
    if match:
        return max(1, min(10, int(match.group())))
    return 5

def calculate_global_score(row):
    att = text_to_score(row.get("Attaque", 5))
    defe = text_to_score(row.get("Défense", 5))
    gk = text_to_score(row.get("Gardien", 1))
    col = text_to_score(row.get("Collectif", 5))
    avg = (att + defe + gk + col) / 4.0
    return round(avg, 1)

def get_card_generation(filename):
    base = os.path.basename(filename).lower()
    match = re.search(r'(fut[-]?\d+|fifa[-]?\d+|toty[-]?\d+|tots[-]?\d+|hero[-]?\d+|fc[-]?\d+)', base)
    if match:
        return match.group(1)
    parts = re.split(r'[-_]', base)
    return parts[0] if len(parts) > 0 else 'default'

def get_available_cards_list():
    available_cards = []
    if os.path.exists(CARTE_FUT_DIR):
        available_cards = [os.path.join(CARTE_FUT_DIR, f) for f in os.listdir(CARTE_FUT_DIR) if f.lower().endswith('.png')]
    for default_c in ['card_blue.png', 'card_red.png', 'card_yellow.png']:
        if os.path.exists(default_c) and default_c not in available_cards:
            available_cards.append(default_c)
    if not available_cards:
        available_cards = ['card_blue.png', 'card_red.png', 'card_yellow.png']
    return available_cards

def get_preview_card_path(full_card_path):
    filename = os.path.basename(full_card_path)
    prev_path = os.path.join(CARTE_FUT_PREV_DIR, filename)
    if os.path.exists(prev_path):
        return prev_path
    elif os.path.exists(full_card_path):
        return resize_and_save_preview(full_card_path)
    return full_card_path

sync_all_previews()

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

# --- GESTION DE L'ÉTAPE DE LANDING ---
if "enter" in st.query_params:
    st.session_state['show_landing'] = False

if 'show_landing' not in st.session_state:
    st.session_state['show_landing'] = True

# --- 2. CSS & STYLES ---
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
    div[data-testid="stImage"] img {
        object-fit: contain !important;
        max-width: 130px !important;
        height: auto !important;
        margin: 0 auto !important;
        display: block !important;
    }

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

    .landing-card-container {
        display: flex;
        justify-content: center;
        align-items: center;
        width: 100%;
        margin-top: 20px;
    }

    .landing-card {
        display: inline-flex;
        flex-direction: column;
        max-width: 650px;
        width: 100%;
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 10px 30px rgba(0,0,0,0.6);
        background-color: #1e1e1e;
    }

    .landing-card img {
        width: 100%;
        height: auto;
        display: block;
        object-fit: contain;
    }

    .landing-card a.landing-btn {
        display: block;
        width: 100%;
        background-color: #28a745;
        color: white !important;
        text-align: center;
        font-size: 20px;
        font-weight: bold;
        padding: 16px 0;
        text-decoration: none !important;
        transition: background-color 0.2s ease, transform 0.1s ease;
        box-sizing: border-box;
    }

    .landing-card a.landing-btn:hover {
        background-color: #218838;
        color: white !important;
    }

    .landing-card a.landing-btn:active {
        transform: scale(0.99);
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- INITIALISATION DE SESSION ---
if 'db_editor_version' not in st.session_state:
    st.session_state['db_editor_version'] = 0

if 'jokers_editor_version' not in st.session_state:
    st.session_state['jokers_editor_version'] = 0

if 'auto_selected' not in st.session_state:
    st.session_state.auto_selected = set()

if 'match_jokers_list' not in st.session_state:
    st.session_state.match_jokers_list = []

if 'active_font_path' not in st.session_state:
    default_in_folder = os.path.join(FONTS_DIR, DEFAULT_FONT_PATH)
    if os.path.exists(default_in_folder):
        st.session_state['active_font_path'] = default_in_folder
    elif os.path.exists(DEFAULT_FONT_PATH):
        st.session_state['active_font_path'] = DEFAULT_FONT_PATH
    else:
        st.session_state['active_font_path'] = None

NUMERIC_OPTIONS = list(range(1, 11))

# --- GESTION GITHUB ---
def push_file_to_github(file_path: str, content_bytes: bytes, commit_message: str) -> bool:
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
        st.error(f"❌ Erreur synchronisation GitHub ({file_path}) : {e}")
        return False

# --- CHARGEMENT / SAUVEGARDE BASE JOUEURS ---
def load_data():
    if os.path.exists(DATA_FILE):
        try: 
            df = pd.read_excel(DATA_FILE)
            if "Surnoms" not in df.columns:
                df["Surnoms"] = ""
            if "Gardien" not in df.columns:
                df["Gardien"] = 1
            if "Photo" not in df.columns:
                df["Photo"] = ""
                
            df["Surnoms"] = df["Surnoms"].fillna("").astype(str)
            df["Photo"] = df["Photo"].fillna("").astype(str)
            
            for col in ["Attaque", "Défense", "Gardien", "Collectif"]:
                if col in df.columns:
                    df[col] = df[col].apply(text_to_score)
                else:
                    df[col] = 1 if col == "Gardien" else 5
                    
            ordered_cols = ["Nom du Joueur", "Attaque", "Défense", "Gardien", "Collectif", "Surnoms", "Photo"]
            existing = [c for c in ordered_cols if c in df.columns]
            return df[existing]
        except Exception as e: 
            st.error(f"Erreur lors de la lecture de {DATA_FILE} : {e}")
            
    return pd.DataFrame({
        "Nom du Joueur": ["Antho", "Cyril V", "Apou", "Benoit", "Nico P", "Mouyss", "Cédric", "Nico M", "David", "Cyril L"],
        "Attaque": [9, 5, 7, 9, 5, 7, 3, 7, 5, 3],
        "Défense": [5, 9, 5, 3, 9, 3, 9, 5, 7, 7],
        "Gardien": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        "Collectif": [7, 9, 7, 5, 7, 5, 7, 5, 5, 5],
        "Surnoms": ["", "Cyril", "", "beny", "nicop, nico", "mouys", "", "nicom, nico", "Dav, dimeh", "Cyril"],
        "Photo": ["", "", "", "", "", "", "", "", "", ""]
    })

def save_data(df):
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
            
    ordered_cols = ["Nom du Joueur", "Attaque", "Défense", "Gardien", "Collectif", "Surnoms", "Photo"]
    existing_cols = [c for c in ordered_cols if c in clean_df.columns]
    other_cols = [c for c in clean_df.columns if c not in ordered_cols]
    clean_df = clean_df[existing_cols + other_cols]
    
    clean_df.to_excel(DATA_FILE, index=False)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        clean_df.to_excel(writer, index=False)
    buffer.seek(0)

    push_file_to_github(DATA_FILE, buffer.getvalue(), "Mise à jour base joueurs [via Soccer FFL]")

# --- CHARGEMENT / SAUVEGARDE BASE JOKERS ---
def load_jokers_db():
    if os.path.exists(JOKERS_FILE):
        try:
            df = pd.read_excel(JOKERS_FILE)
            if "Photo" not in df.columns:
                df["Photo"] = ""
            df["Photo"] = df["Photo"].fillna("").astype(str)
            for col in ["Attaque", "Défense", "Gardien", "Collectif", "Note Globale"]:
                if col in df.columns:
                    df[col] = df[col].apply(text_to_score)
            return df
        except Exception:
            pass
            
    return pd.DataFrame(columns=["Nom Joker", "Joueur Rattaché", "Note Globale", "Attaque", "Défense", "Gardien", "Collectif", "Photo"])

def save_jokers_db(df):
    clean_df = df.copy()
    clean_df.to_excel(JOKERS_FILE, index=False)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        clean_df.to_excel(writer, index=False)
    buffer.seek(0)

    push_file_to_github(JOKERS_FILE, buffer.getvalue(), "Mise à jour base jokers [via Soccer FFL]")

# --- CHARGEMENT / SAUVEGARDE HISTORIQUE ---
def load_history_db():
    if os.path.exists(HISTORY_FILE):
        try:
            return pd.read_excel(HISTORY_FILE)
        except Exception:
            pass
    return pd.DataFrame(columns=[
        "ID Match", "Date", 
        "T1_Joueurs", "T1_Att", "T1_Def", "T1_Gk", "T1_Col",
        "T2_Joueurs", "T2_Att", "T2_Def", "T2_Gk", "T2_Col",
        "Team1_JSON", "Team2_JSON"
    ])

def save_match_to_history(df_t1, df_t2):
    hist_df = load_history_db()
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    t1_names = ", ".join(df_t1["Nom du Joueur"].tolist())
    t2_names = ", ".join(df_t2["Nom du Joueur"].tolist())
    
    t1_att = df_t1['Attaque'].apply(text_to_score).sum()
    t1_def = df_t1['Défense'].apply(text_to_score).sum()
    t1_gk  = df_t1['Gardien'].apply(text_to_score).sum()
    t1_col = df_t1['Collectif'].apply(text_to_score).sum()

    t2_att = df_t2['Attaque'].apply(text_to_score).sum()
    t2_def = df_t2['Défense'].apply(text_to_score).sum()
    t2_gk  = df_t2['Gardien'].apply(text_to_score).sum()
    t2_col = df_t2['Collectif'].apply(text_to_score).sum()

    match_id = f"Match_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    new_row = pd.DataFrame([{
        "ID Match": match_id,
        "Date": now_str,
        "T1_Joueurs": t1_names,
        "T1_Att": t1_att, "T1_Def": t1_def, "T1_Gk": t1_gk, "T1_Col": t1_col,
        "T2_Joueurs": t2_names,
        "T2_Att": t2_att, "T2_Def": t2_def, "T2_Gk": t2_gk, "T2_Col": t2_col,
        "Team1_JSON": df_t1.to_json(orient="records"),
        "Team2_JSON": df_t2.to_json(orient="records")
    }])

    hist_df = pd.concat([new_row, hist_df], ignore_index=True)
    if len(hist_df) > 100:
        hist_df = hist_df.iloc[:100]

    hist_df.to_excel(HISTORY_FILE, index=False)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        hist_df.to_excel(writer, index=False)
    buffer.seek(0)
    push_file_to_github(HISTORY_FILE, buffer.getvalue(), f"Ajout composition {now_str} à l'historique")

if 'players_df' not in st.session_state:
    st.session_state.players_df = load_data()

if 'jokers_db' not in st.session_state:
    st.session_state.jokers_db = load_jokers_db()

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
            <div class="landing-card-container">
                <div class="landing-card">
                    <img src="data:image/jpeg;base64,{img_b64}" alt="Soccer FFL Kompo Intro">
                    <a class="landing-btn" href="?enter=true" target="_self">Entrez faire votre Kompo ⚽</a>
                </div>
            </div>
            """, 
            unsafe_allow_html=True
        )
    else:
        st.warning(f"⚠️ Fichier d'image introuvable (`{IMAGE_PATH}`).")
        if st.button("Entrez faire votre Kompo ⚽", type="primary"):
            st.session_state['show_landing'] = False
            st.rerun()

    st.stop()

# ==========================================
# ⚽ RENDU DU TERRAIN & INCRUSTATION PHOTO
# ==========================================
def create_player_card(card_path, player_name, is_custom_fut=False, override_font_path=None):
    if not os.path.exists(card_path):
        return None
    
    card_img = Image.open(card_path).convert("RGBA")
    if is_custom_fut:
        return card_img

    w, h = card_img.size

    # --- 1. INCRUSTATION DE LA PHOTO ---
    photo_path = get_player_photo_path(player_name)
    if photo_path and os.path.exists(photo_path):
        try:
            with Image.open(photo_path).convert("RGBA") as photo_img:
                max_photo_w = int(w * 0.75)
                max_photo_h = int(h * 0.50)
                
                p_w, p_h = photo_img.size
                ratio = min(max_photo_w / p_w, max_photo_h / p_h)
                new_p_w = int(p_w * ratio)
                new_p_h = int(p_h * ratio)
                
                photo_resized = photo_img.resize((new_p_w, new_p_h), Image.Resampling.LANCZOS)
                
                paste_x = (w - new_p_w) // 2
                paste_y = int(h * 0.38) - (new_p_h // 2)
                
                card_img.paste(photo_resized, (paste_x, paste_y), photo_resized)
        except Exception:
            pass

    # --- 2. TEXTE DU NOM ---
    draw = ImageDraw.Draw(card_img)
    max_text_width = w * 0.85
    y_pos = int(h * 0.74)
    font_size = max(20, int(w * 0.15))
    stroke_w = max(2, int(font_size * 0.07))
    
    raw_name = player_name.strip()
    if raw_name.lower().startswith("joker"):
        parts = raw_name.split(maxsplit=1)
        lines = ["JOKER", parts[1].upper()] if len(parts) > 1 else ["JOKER"]
    else:
        lines = [raw_name.upper()]
    
    used_font_path = override_font_path or st.session_state.get('active_font_path')
    
    def load_font_obj(sz):
        if used_font_path and os.path.exists(used_font_path):
            try:
                return ImageFont.truetype(used_font_path, sz)
            except Exception:
                pass
        try:
            return ImageFont.truetype(DEFAULT_FONT_PATH, sz)
        except Exception:
            return ImageFont.load_default()

    while font_size > 10:
        font = load_font_obj(font_size)
        widths = [(draw.textbbox((0, 0), line, font=font)[2] - draw.textbbox((0, 0), line, font=font)[0]) for line in lines]
        if max(widths) <= max_text_width:
            break
        font_size -= 2

    font = load_font_obj(font_size)

    if len(lines) == 1:
        text_bbox = draw.textbbox((0, 0), lines[0], font=font)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]
        x_pos = (w - text_w) / 2
        y_pos_centered = y_pos - (text_h / 2)
        draw.text((x_pos, y_pos_centered), lines[0], fill="white", font=font, stroke_width=stroke_w, stroke_fill="black")
    else:
        bbox0 = draw.textbbox((0, 0), lines[0], font=font)
        bbox1 = draw.textbbox((0, 0), lines[1], font=font)
        h0 = bbox0[3] - bbox0[1]
        h1 = bbox1[3] - bbox1[1]
        w0 = bbox0[2] - bbox0[0]
        w1 = bbox1[2] - bbox1[0]
        
        spacing = 4
        total_h = h0 + h1 + spacing
        start_y = y_pos - (total_h / 2)
        
        draw.text(((w - w0) / 2, start_y), lines[0], fill="white", font=font, stroke_width=stroke_w, stroke_fill="black")
        draw.text(((w - w1) / 2, start_y + h0 + spacing), lines[1], fill="white", font=font, stroke_width=stroke_w, stroke_fill="black")

    return card_img

def draw_combined_field(t1, t2, override_cards=None):
    fig, ax = plt.subplots(figsize=(10, 6.5))
    fig.patch.set_facecolor('#226343')
    ax.set_facecolor('#226343')
    
    ax.plot([0, 100, 100, 0, 0], [0, 0, 60, 60, 0], color='white', linewidth=2.0)
    ax.plot([50, 50], [0, 60], color='white', linewidth=2.0)
    center_circle = patches.Circle((50, 30), 9, edgecolor='white', facecolor='none', linewidth=1.5)
    ax.add_patch(center_circle)
    ax.scatter(50, 30, color='white', s=15, zorder=2)
    
    ax.add_patch(patches.Rectangle((0, 15), 12, 30, edgecolor='white', facecolor='none', linewidth=1.5))
    ax.scatter(9, 30, color='white', s=15, zorder=2)
    ax.add_patch(patches.Rectangle((88, 15), 12, 30, edgecolor='white', facecolor='none', linewidth=1.5))
    ax.scatter(91, 30, color='white', s=15, zorder=2)
    
    card_width = 13.5
    card_height = 18.0
    
    default_t1_card = 'card_blue.png'
    default_t2_card = 'card_red.png'
    default_joker_card = 'card_yellow.png'
    
    if override_cards:
        global_card_t1 = override_cards.get('t1', default_t1_card)
        global_card_t2 = override_cards.get('t2', default_t2_card)
        global_card_joker = override_cards.get('joker', default_joker_card)
    else:
        global_card_t1 = st.session_state.get('global_card_t1', default_t1_card)
        global_card_t2 = st.session_state.get('global_card_t2', default_t2_card)
        global_card_joker = st.session_state.get('global_card_joker', default_joker_card)
    
    pos1 = [(7, 30), (23, 13), (23, 47), (40, 17), (40, 43)]
    players1 = t1.copy()
    players1['Gk_Num'] = players1['Gardien'].apply(text_to_score)
    players1 = players1.sort_values(by="Gk_Num", ascending=False).reset_index(drop=True)
    
    for i, row in players1.iterrows():
        if i >= len(pos1): break
        x, y = pos1[i]
        p_name = str(row['Nom du Joueur'])
        is_joker = bool(row.get('is_joker', False))
        
        chosen_path = global_card_joker if is_joker else global_card_t1
        if not os.path.exists(chosen_path):
            chosen_path = default_joker_card if is_joker else default_t1_card
            
        card_img = create_player_card(chosen_path, p_name)
        if card_img:
            ax.imshow(card_img, extent=[x - card_width/2, x + card_width/2, y - card_height/2, y + card_height/2], zorder=3)
        
    pos2 = [(93, 30), (77, 13), (77, 47), (60, 17), (60, 43)]
    players2 = t2.copy()
    players2['Gk_Num'] = players2['Gardien'].apply(text_to_score)
    players2 = players2.sort_values(by="Gk_Num", ascending=False).reset_index(drop=True)
    
    for i, row in players2.iterrows():
        if i >= len(pos2): break
        x, y = pos2[i]
        p_name = str(row['Nom du Joueur'])
        is_joker = bool(row.get('is_joker', False))
        
        chosen_path = global_card_joker if is_joker else global_card_t2
        if not os.path.exists(chosen_path):
            chosen_path = default_joker_card if is_joker else default_t2_card
            
        card_img = create_player_card(chosen_path, p_name)
        if card_img:
            ax.imshow(card_img, extent=[x - card_width/2, x + card_width/2, y - card_height/2, y + card_height/2], zorder=3)
    
    ax.text(25, 64, "ÉQUIPE 1", color='white', fontsize=16, weight='bold', ha='center', va='center')
    ax.text(75, 64, "ÉQUIPE 2", color='white', fontsize=16, weight='bold', ha='center', va='center')
    
    ax.set_xlim(-6, 106)
    ax.set_ylim(-4, 68)
    ax.axis('off')
    plt.tight_layout()
    return fig

@st.dialog("Compositions du Match", width="large")
def show_teams_popup(t1, t2, override_cards=None):
    st.write("Match équilibré généré avec succès ! 📸")
    fig_combined = draw_combined_field(t1, t2, override_cards=override_cards)
    st.pyplot(fig_combined, use_container_width=True)
    
    buf = io.BytesIO()
    fig_combined.savefig(buf, format="png", bbox_inches='tight', dpi=250, facecolor='#226343')
    buf.seek(0)
    
    st.download_button(label="📸 Télécharger l'image (PNG)", data=buf, file_name="Compositions_FFL.png", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    st.write("---")
    
    text_whatsapp = "⚽ *COMPOSITIONS DU MATCH* ⚽\n\n"
    text_whatsapp += "🔵 *ÉQUIPE 1* :\n"
    for _, row in t1.iterrows():
        text_whatsapp += f"• {row['Nom du Joueur']}\n"
        
    text_whatsapp += "\n🔴 *ÉQUIPE 2* :\n"
    for _, row in t2.iterrows():
        text_whatsapp += f"• {row['Nom du Joueur']}\n"
        
    st.markdown("**📋 Texte à copier pour WhatsApp (Noms uniquement) :**")
    st.code(text_whatsapp, language="text")
    if st.button("Fermer"): 
        st.rerun()

def compute_teams(players_list, j1, j2, force_t1_names, force_t2_names):
    best_diff = float('inf')
    best_team1, best_team2 = None, None
    valid_combo_found = False
    
    set_force_t1 = set(force_t1_names)
    set_force_t2 = set(force_t2_names)
    
    for combo in itertools.combinations(players_list, 5):
        t1 = list(combo)
        t2 = [p for p in players_list if p not in t1]
        
        names_t1 = set(p['Nom du Joueur'] for p in t1)
        names_t2 = set(p['Nom du Joueur'] for p in t2)
        
        if not set_force_t1.issubset(names_t1):
            continue
        if not set_force_t2.issubset(names_t2):
            continue

        if j1 != "Aucune restriction" and j2 != "Aucun":
            if (j1 in names_t1 and j2 in names_t1) or (j1 in names_t2 and j2 in names_t2):
                continue
        
        valid_combo_found = True
        df_t1 = pd.DataFrame(t1)
        df_t2 = pd.DataFrame(t2)
        
        t1_att_sum = df_t1['Attaque'].apply(text_to_score).sum()
        t1_def_sum = df_t1['Défense'].apply(text_to_score).sum()
        t1_gk_sum  = df_t1['Gardien'].apply(text_to_score).sum()
        t1_col_sum = df_t1['Collectif'].apply(text_to_score).sum()
        
        t2_att_sum = df_t2['Attaque'].apply(text_to_score).sum()
        t2_def_sum = df_t2['Défense'].apply(text_to_score).sum()
        t2_gk_sum  = df_t2['Gardien'].apply(text_to_score).sum()
        t2_col_sum = df_t2['Collectif'].apply(text_to_score).sum()
        
        total_diff = abs(t1_att_sum - t2_att_sum) + abs(t1_def_sum - t2_def_sum) + abs(t1_gk_sum - t2_gk_sum) + abs(t1_col_sum - t2_col_sum)
        
        if total_diff < best_diff:
            best_diff = total_diff
            best_team1 = df_t1
            best_team2 = df_t2

    return valid_combo_found, best_team1, best_team2

# --- EN-TÊTE PRINCIPAL ---
col_logo, col_title, col_home = st.columns([1, 5, 1])
with col_logo:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=80)
    else:
        st.title("⚽")
with col_title:
    st.header("Soccer FFL Kompo")
with col_home:
    if st.button("🏠 Accueil"):
        if "enter" in st.query_params:
            del st.query_params["enter"]
        st.session_state['show_landing'] = True
        st.rerun()

if st.session_state.get("open_teams_popup", False):
    st.session_state.open_teams_popup = False
    override = st.session_state.get('active_override_cards', None)
    show_teams_popup(st.session_state.last_team1, st.session_state.last_team2, override_cards=override)

tab1, tab_hist, tab_font, tab2 = st.tabs(["⚖️ Équilibrage du Jour", "📜 Historique", "🎨 Police & Cartes", "🏃 Gestion des Bases"])

# ==========================================
# ⚖️ TAB 1 : ÉQUILIBRAGE DU JOUR
# ==========================================
with tab1:
    with st.expander("📋 Analyser une convocation WhatsApp (Optionnel)", expanded=False):
        convoc_text = st.text_area("Colle le texte brut de ta convocation ici :", height=150, key="convoc_text_input")
        if st.button("🔍 Extraire et Valider les Joueurs", key="btn_parse_convoc"):
            if convoc_text.strip():
                match_presents = re.search(r"présents?\b[:\-\s]*(.*)", convoc_text, re.IGNORECASE | re.DOTALL)
                target_text = match_presents.group(1) if match_presents else convoc_text
                stop_pattern = r"\n\s*(jokers?|absents?|infirmerie|en attente|à confirmer|a confirmer)\b"
                target_text = re.split(stop_pattern, target_text, flags=re.IGNORECASE)[0]
                target_text = re.sub(r"\)\s*(?=[a-zA-ZÀ-ÿ])", "), ", target_text)

                raw_segments = re.split(r"[\n,;]+", target_text)
                cleaned_names = []
                for seg in raw_segments:
                    s = re.sub(r"\(\s*\d+\s*\)", "", seg)
                    s = re.sub(r"^\s*[\d\.\-\*\•\:]+\s*", "", s)
                    s = s.strip()
                    if s: cleaned_names.append(s)

                df_db = st.session_state.players_df
                alias_map = {}
                for _, row in df_db.iterrows():
                    real_name = str(row["Nom du Joueur"]).strip()
                    alias_map.setdefault(real_name.lower(), []).append(real_name)
                    for sn in [s.strip().lower() for s in str(row.get("Surnoms", "")).split(",") if s.strip()]:
                        if real_name not in alias_map.setdefault(sn, []): alias_map[sn].append(real_name)

                found_players = set()
                for candidate in cleaned_names:
                    if candidate.lower() in alias_map and len(alias_map[candidate.lower()]) == 1:
                        found_players.add(alias_map[candidate.lower()][0])

                st.session_state.auto_selected = found_players
                for p_name in df_db["Nom du Joueur"].dropna().unique():
                    st.session_state[f"chk_p_{p_name}"] = (p_name in found_players)
                st.rerun()

    st.subheader("1. Sélection des joueurs réguliers présents")
    df_sorted = st.session_state.players_df.sort_values(by="Nom du Joueur").reset_index(drop=True)
    all_names = df_sorted["Nom du Joueur"].tolist()
    
    for name in all_names:
        key = f"chk_p_{name}"
        if key not in st.session_state:
            st.session_state[key] = (name in st.session_state.auto_selected)

    selected_names = []
    cols = st.columns(3)
    for idx, name in enumerate(all_names):
        col = cols[idx % 3]
        key = f"chk_p_{name}"
        has_photo = " 📸" if get_player_photo_path(name) else ""
        if col.checkbox(f"{name}{has_photo}", key=key):
            selected_names.append(name)
            st.session_state.auto_selected.add(name)
        else:
            st.session_state.auto_selected.discard(name)
                
    nb_regulars = len(selected_names)
    nb_jokers = len(st.session_state.match_jokers_list)
    total_players_count = nb_regulars + nb_jokers
    
    st.write("---")
    st.subheader(f"2. Jokers / Invités du Jour ({nb_jokers})")
    
    if st.session_state.match_jokers_list:
        for idx_jk, jk in enumerate(st.session_state.match_jokers_list):
            c_txt, c_del = st.columns([5, 1])
            with c_txt:
                p_status = "📸" if get_player_photo_path(jk['Nom du Joueur']) else ""
                st.info(f"🃏 **{jk['Nom du Joueur']}** {p_status} — Notes : Att {jk['Attaque']} | Déf {jk['Défense']} | Gk {jk['Gardien']} | Col {jk['Collectif']}")
            with c_del:
                if st.button("❌", key=f"del_match_jk_{idx_jk}"):
                    st.session_state.match_jokers_list.pop(idx_jk)
                    st.rerun()

    if total_players_count < 10:
        with st.expander("➕ Ajouter un Joker au match", expanded=True):
            jokers_db = st.session_state.jokers_db
            has_db_jokers = not jokers_db.empty and "Nom Joker" in jokers_db.columns
            mode_choice = st.radio("Source du Joker :", ["Sélectionner depuis la BDD Jokers", "Saisir un nouveau Joker"] if has_db_jokers else ["Saisir un nouveau Joker"], horizontal=True, key="joker_source_mode_tab1")
            
            if mode_choice == "Sélectionner depuis la BDD Jokers":
                db_joker_names = sorted(jokers_db["Nom Joker"].dropna().unique().tolist())
                current_jk_names = [j["Nom du Joueur"] for j in st.session_state.match_jokers_list]
                available_db_names = [n for n in db_joker_names if f"Joker {n}" not in current_jk_names and n not in current_jk_names]
                
                if available_db_names:
                    chosen_jk_name = st.selectbox("Choisir le Joker :", options=available_db_names, key="sel_joker_from_db_tab1")
                    jk_data = jokers_db[jokers_db["Nom Joker"] == chosen_jk_name].iloc[0]
                    if st.button("➕ Ajouter ce Joker au match", key="btn_add_joker_db_tab1", type="primary"):
                        st.session_state.match_jokers_list.append({
                            "Nom du Joueur": f"Joker {chosen_jk_name}" if not chosen_jk_name.startswith("Joker") else chosen_jk_name,
                            "Attaque": text_to_score(jk_data.get("Attaque", 5)),
                            "Défense": text_to_score(jk_data.get("Défense", 5)),
                            "Gardien": text_to_score(jk_data.get("Gardien", 1)),
                            "Collectif": text_to_score(jk_data.get("Collectif", 5)),
                            "Surnoms": "",
                            "is_joker": True
                        })
                        st.rerun()
            else:
                with st.form("form_add_manual_joker_tab1"):
                    new_jk_name = st.text_input("Prénom du Joker", value=f"Joker {nb_jokers + 1}")
                    new_jk_score = st.number_input("Note Globale (1-10)", min_value=1, max_value=10, value=5)
                    save_to_db_chk = st.checkbox("Enregistrer aussi dans la BDD Jokers", value=True)
                    
                    if st.form_submit_button("➕ Ajouter ce Joker au match"):
                        if new_jk_name.strip():
                            clean_jk_name = new_jk_name.strip()
                            final_name = f"Joker {clean_jk_name}" if not clean_jk_name.startswith("Joker") else clean_jk_name
                            num_s = text_to_score(new_jk_score)
                            
                            st.session_state.match_jokers_list.append({
                                "Nom du Joueur": final_name,
                                "Attaque": num_s, "Défense": num_s, "Gardien": 1, "Collectif": num_s,
                                "Surnoms": "", "is_joker": True
                            })
                            
                            if save_to_db_chk:
                                new_entry = pd.DataFrame([{
                                    "Nom Joker": clean_jk_name, "Joueur Rattaché": "Aucun",
                                    "Note Globale": num_s, "Attaque": num_s, "Défense": num_s,
                                    "Gardien": 1, "Collectif": num_s, "Photo": ""
                                }])
                                st.session_state.jokers_db = pd.concat([st.session_state.jokers_db, new_entry], ignore_index=True)
                                save_jokers_db(st.session_state.jokers_db)
                                st.session_state.jokers_editor_version += 1
                            st.rerun()

    regular_players_df = st.session_state.players_df[st.session_state.players_df["Nom du Joueur"].isin(selected_names)].copy()
    regular_players_df['is_joker'] = False
    all_match_players_list = regular_players_df.to_dict(orient='records') + st.session_state.match_jokers_list
    all_match_names = [p["Nom du Joueur"] for p in all_match_players_list]

    st.write("---")
    st.subheader(f"3. Affinités et Oppositions ({total_players_count} / 10 joueurs)")

    col_force_t1, col_force_t2 = st.columns(2)
    with col_force_t1:
        force_t1 = st.multiselect("🔵 Forcer ensemble Équipe 1 :", options=sorted(all_match_names), max_selections=5, key="force_t1_tab1")
    with col_force_t2:
        remaining_for_t2 = [n for n in sorted(all_match_names) if n not in force_t1]
        force_t2 = st.multiselect("🔴 Forcer ensemble Équipe 2 :", options=remaining_for_t2, max_selections=5, key="force_t2_tab1")

    col_j1, col_j2 = st.columns(2)
    with col_j1:
        j1 = st.selectbox("Séparer le joueur...", options=["Aucune restriction"] + sorted(all_match_names), key="sep_j1_tab1")
    with col_j2:
        remaining_options = [n for n in all_match_names if n != j1] if j1 != "Aucune restriction" else []
        j2 = st.selectbox("... d'avec :", options=["Aucun"] + sorted(remaining_options), key="sep_j2_tab1") if j1 != "Aucune restriction" else "Aucun"

    st.write("---")
    st.subheader("4. Cartes pour ce Match")
    main_use_default_cards = st.checkbox("Utiliser les cartes globales configurées", value=True, key="main_use_default_cards_chk")
    
    main_override_cards = None
    if not main_use_default_cards:
        available_cards_list = get_available_cards_list()
        main_card_mode = st.radio("Mode de sélection des cartes :", ["Manuel (Équipe par Équipe)", "Aléatoire complet (Génération FUT / FC)"], key="main_card_mode_select")
        
        if main_card_mode == "Manuel (Équipe par Équipe)":
            mc_t1 = st.selectbox("Carte Équipe 1 :", options=available_cards_list, key="match_sel_t1_card")
            mc_t2 = st.selectbox("Carte Équipe 2 :", options=available_cards_list, key="match_sel_t2_card")
            mc_joker = st.selectbox("Carte Jokers :", options=available_cards_list, key="match_sel_joker_card")
            main_override_cards = {'t1': mc_t1, 't2': mc_t2, 'joker': mc_joker}
        else:
            generations = {}
            for c_path in available_cards_list:
                gen = get_card_generation(c_path)
                generations.setdefault(gen, []).append(c_path)
            selected_gen_main = st.selectbox("Série homogène / Génération :", options=list(generations.keys()), key="main_sel_gen")
            
            if 'main_random_override' not in st.session_state:
                import random
                g_cards = generations[selected_gen_main]
                st.session_state['main_random_override'] = {'t1': random.choice(g_cards), 't2': random.choice(g_cards), 'joker': random.choice(g_cards)}
            
            if st.button("🎲 Tirer un nouveau pack aléatoire", key="main_btn_rnd_gen"):
                import random
                g_cards = generations[selected_gen_main]
                st.session_state['main_random_override'] = {
                    't1': random.choice(g_cards),
                    't2': random.choice(g_cards),
                    'joker': random.choice(g_cards)
                }
                st.rerun()
            main_override_cards = st.session_state.get('main_random_override', None)
    else:
        main_override_cards = {
            't1': st.session_state.get('global_card_t1', 'card_blue.png'),
            't2': st.session_state.get('global_card_t2', 'card_red.png'),
            'joker': st.session_state.get('global_card_joker', 'card_yellow.png')
        }

    # --- PRÉVISUALISATION EN TEMPS RÉEL AVEC PERSONNALISATION DU PRÉNOM ---
    st.markdown("##### 👁️ Aperçu en direct des cartes sélectionnées pour le match :")
    preview_name_tab1 = st.text_input("Modifier le prénom affiché sur l'aperçu :", value=all_match_names[0] if all_match_names else "Antho", key="preview_custom_name_input")
    preview_font_path = st.session_state.get('active_font_path', DEFAULT_FONT_PATH)

    prev_cols = st.columns(3)
    cards_preview_meta = [
        ("🔵 Équipe 1", main_override_cards['t1'] if main_override_cards else 'card_blue.png'),
        ("🔴 Équipe 2", main_override_cards['t2'] if main_override_cards else 'card_red.png'),
        ("🃏 Jokers", main_override_cards['joker'] if main_override_cards else 'card_yellow.png')
    ]

    for idx_p, (c_label, c_path) in enumerate(cards_preview_meta):
        with prev_cols[idx_p]:
            st.caption(f"**{c_label}**")
            prev_file_path = get_preview_card_path(c_path)
            if os.path.exists(prev_file_path):
                img_prev = create_player_card(prev_file_path, preview_name_tab1, is_custom_fut=False, override_font_path=preview_font_path)
                if img_prev:
                    st.image(img_prev, use_container_width=False)
                else:
                    st.warning("Erreur rendu")
            else:
                st.info("Introuvable")

    st.write("---")

    if st.button("⚡ Générer l'Équilibrage Parfait", key="btn_generate_teams_tab1", type="primary"):
        if total_players_count != 10:
            st.error(f"Il faut exactement 10 joueurs (actuellement {total_players_count}/10).")
        else:
            valid_combo, best_team1, best_team2 = compute_teams(all_match_players_list, j1, j2, force_t1, force_t2)
            if not valid_combo:
                st.error("Impossible de générer les équipes avec ces contraintes.")
            else:
                st.session_state.last_team1 = best_team1
                st.session_state.last_team2 = best_team2
                save_match_to_history(best_team1, best_team2)
                st.session_state.open_teams_popup = True
                st.session_state.active_override_cards = main_override_cards if not main_use_default_cards else None
                st.rerun()

# ==========================================
# 📜 TAB HISTORIQUE
# ==========================================
with tab_hist:
    st.header("📜 Historique")
    hist_data = load_history_db()
    if hist_data.empty:
        st.info("Aucun match enregistré.")
    else:
        match_labels = [f"📅 {row['Date']} — T1: {row['T1_Joueurs']} vs T2: {row['T2_Joueurs']}" for _, row in hist_data.iterrows()]
        selected_match_idx = st.selectbox("Sélectionner :", options=range(len(match_labels)), format_func=lambda i: match_labels[i], key="hist_match_select")
        chosen_row = hist_data.iloc[selected_match_idx]
        
        c_hist1, c_hist2 = st.columns(2)
        with c_hist1:
            df_h1 = pd.read_json(io.StringIO(chosen_row['Team1_JSON']))
            st.dataframe(df_h1[["Nom du Joueur", "Attaque", "Défense", "Gardien", "Collectif"]], hide_index=True)
        with c_hist2:
            df_h2 = pd.read_json(io.StringIO(chosen_row['Team2_JSON']))
            st.dataframe(df_h2[["Nom du Joueur", "Attaque", "Défense", "Gardien", "Collectif"]], hide_index=True)

        if st.button("🔄 Re-générer ce match", key="btn_regen_hist_match"):
            st.session_state.last_team1 = df_h1
            st.session_state.last_team2 = df_h2
            st.session_state.open_teams_popup = True
            st.rerun()

# ==========================================
# 🎨 TAB POLICE & CARTES
# ==========================================
with tab_font:
    st.header("🎨 Police & Cartes Globales")
    available_fonts = [f for f in os.listdir(FONTS_DIR) if f.lower().endswith(('.otf', '.ttf'))] if os.path.exists(FONTS_DIR) else []
    if DEFAULT_FONT_PATH not in available_fonts: available_fonts.append(DEFAULT_FONT_PATH)

    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        selected_font_filename = st.selectbox("Police active :", options=available_fonts, key="global_font_select")
        if st.button("💾 Appliquer la Police", key="btn_apply_font_global", type="primary"):
            st.session_state['active_font_path'] = os.path.join(FONTS_DIR, selected_font_filename)
            st.success("✅ Mis à jour !")
            st.rerun()

        uploaded_global_card = st.file_uploader("Ajouter une carte PNG", type=["png"], key="upload_global_card_file")
        if uploaded_global_card:
            if st.button("📤 Enregistrer carte", key="btn_save_uploaded_global_card"):
                target_path = os.path.join(CARTE_FUT_DIR, uploaded_global_card.name)
                with open(target_path, "wb") as f: f.write(uploaded_global_card.getvalue())
                resize_and_save_preview(target_path)
                st.success("✅ Carte ajoutée !")
                st.rerun()

    with col_f2:
        available_cards = get_available_cards_list()
        card_mode_global = st.radio("Mode d'attribution global :", ["Manuel", "Aléatoire par Génération FUT/FC"], key="card_mode_global_radio")

        if card_mode_global == "Manuel":
            sel_t1 = st.selectbox("Carte Équipe 1 :", options=available_cards, key="global_sel_team1_card")
            sel_t2 = st.selectbox("Carte Équipe 2 :", options=available_cards, key="global_sel_team2_card")
            sel_joker = st.selectbox("Carte Jokers :", options=available_cards, key="global_sel_joker_card")
            if st.button("💾 Assigner les cartes globales", key="btn_assign_global_cards"):
                st.session_state['global_card_t1'] = sel_t1
                st.session_state['global_card_t2'] = sel_t2
                st.session_state['global_card_joker'] = sel_joker
                st.success("✅ Enregistré !")
                st.rerun()
        else:
            generations = {}
            for c_path in available_cards:
                gen = get_card_generation(c_path)
                generations.setdefault(gen, []).append(c_path)
            selected_gen_global = st.selectbox("Choisir la génération / série homogène :", options=list(generations.keys()), key="global_gen_select")
            if st.button("🎲 Tirer un pack aléatoire global de cette génération", key="btn_random_global_gen", type="primary"):
                import random
                g_cards = generations[selected_gen_global]
                st.session_state['global_card_t1'] = random.choice(g_cards)
                st.session_state['global_card_t2'] = random.choice(g_cards)
                st.session_state['global_card_joker'] = random.choice(g_cards)
                st.success(f"✅ Pack aléatoire de la génération **{selected_gen_global}** appliqué !")
                st.rerun()

# ==========================================
# 🏃 TAB 2 : GESTION DES BASES & PHOTOS
# ==========================================
with tab2:
    st.header("Gestion des Bases de Données & Liaison des Portraits")
    subtab_players, subtab_jokers, subtab_photos = st.tabs(["📋 Base Joueurs", "🃏 Base Jokers", "📸 Liaison & Upload Portraits"])
    
    with subtab_players:
        with st.expander("➕ Ajouter un joueur"):
            with st.form("form_add_player_tab2"):
                name = st.text_input("Nom / Pseudo")
                att_l = st.selectbox("Attaque", options=NUMERIC_OPTIONS, index=4, key="add_p_att")
                def_l = st.selectbox("Défense", options=NUMERIC_OPTIONS, index=4, key="add_p_def")
                gk_l = st.selectbox("Gardien", options=NUMERIC_OPTIONS, index=0, key="add_p_gk")
                col_l = st.selectbox("Collectif", options=NUMERIC_OPTIONS, index=4, key="add_p_col")
                surnames = st.text_input("Surnoms")
                if st.form_submit_button("Ajouter"):
                    if name.strip():
                        new_p = pd.DataFrame({"Nom du Joueur": [name.strip()], "Attaque": [att_l], "Défense": [def_l], "Gardien": [gk_l], "Collectif": [col_l], "Surnoms": [surnames.strip()], "Photo": [""]})
                        st.session_state.players_df = pd.concat([st.session_state.players_df, new_p], ignore_index=True)
                        save_data(st.session_state.players_df)
                        st.rerun()

        edited_players = st.data_editor(st.session_state.players_df, hide_index=True, use_container_width=True, key=f"editor_players_{st.session_state.db_editor_version}")
        if st.button("💾 Enregistrer modifications joueurs", key="btn_save_players_db", type="primary"):
            st.session_state.players_df = edited_players
            save_data(edited_players)
            st.success("✅ Sauvegardé !")
            st.rerun()

    with subtab_jokers:
        edited_jokers_df = st.data_editor(st.session_state.jokers_db, num_rows="dynamic", hide_index=True, use_container_width=True, key=f"editor_jokers_{st.session_state.jokers_editor_version}")
        if st.button("💾 Enregistrer modifications jokers", key="btn_save_jokers_db", type="primary"):
            save_jokers_db(edited_jokers_df)
            st.success("✅ Sauvegardé !")
            st.rerun()

    with subtab_photos:
        st.subheader("📸 Uploader, Lier ou Remplacer un portrait transparent")
        
        reg_list = st.session_state.players_df["Nom du Joueur"].tolist() if not st.session_state.players_df.empty else []
        jok_list = [f"Joker {j}" for j in st.session_state.jokers_db["Nom Joker"].tolist()] if not st.session_state.jokers_db.empty and "Nom Joker" in st.session_state.jokers_db.columns else []
        all_linkable_players = sorted(list(set(reg_list + jok_list)))

        if all_linkable_players:
            selected_player_to_link = st.selectbox("1. Choisir le joueur ou joker à associer :", options=all_linkable_players, key="select_player_photo_link")
            uploaded_photo = st.file_uploader("2. Sélectionner le portrait PNG transparent :", type=["png", "jpg", "jpeg"], key="upload_player_photo_file")

            if uploaded_photo is not None:
                if st.button("🔗 Enregistrer, lier et remplir l'Excel", key="btn_link_photo_submit", type="primary"):
                    ext = os.path.splitext(uploaded_photo.name)[1].lower()
                    clean_target_name = re.sub(r'^joker\s+', '', selected_player_to_link.strip().lower())
                    file_id = get_player_id(clean_target_name)
                    new_filename = f"{file_id}{ext}"
                    target_photo_path = os.path.join(PHOTO_JOUEUR_DIR, new_filename)
                    
                    photo_bytes = uploaded_photo.getvalue()
                    with open(target_photo_path, "wb") as f:
                        f.write(photo_bytes)
                    
                    if selected_player_to_link in reg_list:
                        idx = st.session_state.players_df[st.session_state.players_df["Nom du Joueur"] == selected_player_to_link].index[0]
                        st.session_state.players_df.loc[idx, "Photo"] = new_filename
                        save_data(st.session_state.players_df)
                        st.session_state.db_editor_version += 1
                    elif selected_player_to_link.startswith("Joker "):
                        joker_real_name = selected_player_to_link.replace("Joker ", "").strip()
                        idx = st.session_state.jokers_db[st.session_state.jokers_db["Nom Joker"] == joker_real_name].index[0]
                        st.session_state.jokers_db.loc[idx, "Photo"] = new_filename
                        save_jokers_db(st.session_state.jokers_db)
                        st.session_state.jokers_editor_version += 1

                    push_file_to_github(target_photo_path, photo_bytes, f"Ajout portrait lié pour {selected_player_to_link}")
                    st.success(f"✅ Portrait lié avec succès à **{selected_player_to_link}** !")
                    st.rerun()
        else:
            st.warning("Veuillez d'abord créer des joueurs dans la base.")

        st.write("---")
        st.markdown("##### 🗑️ Gestion des portraits existants (Supprimer / Remplacer)")
        if os.path.exists(PHOTO_JOUEUR_DIR):
            existing_photos = [f for f in os.listdir(PHOTO_JOUEUR_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            if existing_photos:
                p_cols = st.columns(3)
                for idx_ph, p_file in enumerate(existing_photos):
                    with p_cols[idx_ph % 3]:
                        full_path = os.path.join(PHOTO_JOUEUR_DIR, p_file)
                        st.image(full_path, caption=p_file, width=100)
                        
                        matched_player = "Aucun"
                        for p in reg_list:
                            if get_player_photo_path(p) == full_path:
                                matched_player = f"Joueur: {p}"
                                break
                        if matched_player == "Aucun":
                            for j in jok_list:
                                if get_player_photo_path(j) == full_path:
                                    matched_player = f"Joker: {j}"
                                    break
                        st.caption(f"Lié à : **{matched_player}**")

                        if st.button(f"🗑️ Supprimer", key=f"del_photo_{p_file}_{idx_ph}"):
                            try:
                                os.remove(full_path)
                            except Exception:
                                pass
                            
                            if not st.session_state.players_df.empty and "Photo" in st.session_state.players_df.columns:
                                st.session_state.players_df.loc[st.session_state.players_df["Photo"] == p_file, "Photo"] = ""
                                save_data(st.session_state.players_df)
                                st.session_state.db_editor_version += 1

                            if not st.session_state.jokers_db.empty and "Photo" in st.session_state.jokers_db.columns:
                                st.session_state.jokers_db.loc[st.session_state.jokers_db["Photo"] == p_file, "Photo"] = ""
                                save_jokers_db(st.session_state.jokers_db)
                                st.session_state.jokers_editor_version += 1

                            st.success(f"Portrait **{p_file}** supprimé !")
                            st.rerun()
            else:
                st.info("Aucun portrait enregistré pour le moment.")
