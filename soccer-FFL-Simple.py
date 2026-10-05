import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image, ImageDraw, ImageFont
import io
import itertools
import re
import base64
import json
from github import Github, GithubException

# --- FICHIERS REQUIS ---
DATA_FILE = 'database_joueurs_v2.xlsx'
JOKERS_FILE = 'database_jokers.xlsx'
HISTORY_FILE = 'history_v2.json'
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
        width: 100%;
        max-width: 900px;
        margin: 0 auto;
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    .landing-img {
        width: 100%;
        max-height: 80vh;
        object-fit: contain;
        border-radius: 16px;
        box-shadow: 0 6px 25px rgba(0,0,0,0.6);
        margin-bottom: 15px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- FONCTION DE SYNCHRONISATION GITHUB ---
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
        st.error(f"❌ Erreur de synchronisation GitHub ({file_path}) : {e}")
        return False

# --- UTILITAIRES DE NOTATION ---
NUMERIC_OPTIONS = list(range(1, 11))
GK_OPTIONS = [0, 1]

def text_to_score(val):
    if pd.isna(val):
        return 5
    match = re.search(r'\d+', str(val))
    if match:
        return max(1, min(10, int(match.group())))
    return 5

def text_to_gk_score(val):
    if pd.isna(val):
        return 1
    match = re.search(r'\d+', str(val))
    if match:
        num = int(match.group())
        return 1 if num >= 1 else 0
    return 1

def calculate_global_score(row):
    att = text_to_score(row.get("Attaque", 5))
    defe = text_to_score(row.get("Défense", 5))
    col = text_to_score(row.get("Collectif", 5))
    return round((att + defe + col) / 3.0, 1)

# --- CHARGEMENT / SAUVEGARDE BASE JOUEURS ---
def load_data():
    if os.path.exists(DATA_FILE):
        try: 
            df = pd.read_excel(DATA_FILE)
            if "Surnoms" not in df.columns:
                df["Surnoms"] = ""
            if "Gardien" not in df.columns:
                df["Gardien"] = 0
                
            df["Surnoms"] = df["Surnoms"].fillna("")
            
            for col in ["Attaque", "Défense", "Collectif"]:
                if col in df.columns:
                    df[col] = df[col].apply(text_to_score)
            
            if "Gardien" in df.columns:
                df["Gardien"] = df["Gardien"].apply(text_to_gk_score)
                
            df["Note Globale"] = df.apply(calculate_global_score, axis=1)
            return df
        except Exception: 
            pass
            
    df_default = pd.DataFrame({
        "Nom du Joueur": ["Antho", "Cyril V", "Apou", "Benoit", "Nico P", "Mouyss", "Cédric", "Nico M", "David", "Cyril L"],
        "Attaque": [9, 5, 7, 9, 5, 7, 3, 7, 5, 3],
        "Défense": [5, 9, 5, 3, 9, 3, 9, 5, 7, 7],
        "Gardien": [0, 0, 1, 0, 1, 0, 1, 0, 0, 0],
        "Collectif": [7, 9, 7, 5, 7, 5, 7, 5, 5, 5],
        "Surnoms": ["", "Cyril", "", "beny", "nicop, nico", "mouys", "", "nicom, nico", "Dav, dimeh", "Cyril"]
    })
    df_default["Note Globale"] = df_default.apply(calculate_global_score, axis=1)
    return df_default

def save_data(df):
    clean_df = df.copy()
    if "Note Globale" in clean_df.columns:
        clean_df = clean_df.drop(columns=["Note Globale"])
    if "is_joker" in clean_df.columns:
        clean_df = clean_df.drop(columns=["is_joker"])
        
    for col in ["Attaque", "Défense", "Collectif"]:
        if col in clean_df.columns:
            clean_df[col] = clean_df[col].apply(text_to_score)
            
    if "Gardien" in clean_df.columns:
        clean_df["Gardien"] = clean_df["Gardien"].apply(text_to_gk_score)
            
    ordered_cols = ["Nom du Joueur", "Attaque", "Défense", "Gardien", "Collectif", "Surnoms"]
    existing_cols = [c for c in ordered_cols if c in clean_df.columns]
    other_cols = [c for c in clean_df.columns if c not in ordered_cols]
    clean_df = clean_df[existing_cols + other_cols]
    
    clean_df.to_excel(DATA_FILE, index=False)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        clean_df.to_excel(writer, index=False)
    buffer.seek(0)
    
    if push_file_to_github(DATA_FILE, buffer.getvalue(), "Mise à jour base joueurs"):
        st.toast("Base joueurs enregistrée et synchronisée !", icon="☁️")

# --- CHARGEMENT / SAUVEGARDE BASE JOKERS ---
def load_jokers_db():
    if os.path.exists(JOKERS_FILE):
        try:
            df = pd.read_excel(JOKERS_FILE)
            for col in ["Attaque", "Défense", "Collectif", "Note Globale"]:
                if col in df.columns:
                    df[col] = df[col].apply(text_to_score)
            if "Gardien" not in df.columns:
                df["Gardien"] = 1
            else:
                df["Gardien"] = df["Gardien"].apply(text_to_gk_score)
            return df
        except Exception:
            pass
            
    return pd.DataFrame({
        "Nom Joker": [],
        "Joueur Rattaché": [],
        "Note Globale": [],
        "Attaque": [],
        "Défense": [],
        "Gardien": [],
        "Collectif": []
    })

def save_jokers_db(df):
    clean_df = df.copy()
    clean_df.to_excel(JOKERS_FILE, index=False)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        clean_df.to_excel(writer, index=False)
    buffer.seek(0)

    if push_file_to_github(JOKERS_FILE, buffer.getvalue(), "Mise à jour base jokers"):
        st.toast("Base jokers enregistrée et synchronisée !", icon="☁️")

# --- HISTORIQUE ---
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                history_list = []
                for item in data:
                    history_list.append({
                        't1': pd.DataFrame(item['t1']),
                        't2': pd.DataFrame(item['t2']),
                        'date': item['date']
                    })
                return history_list
        except Exception:
            pass
    return []

def save_history(history_list):
    try:
        data_to_save = []
        for item in history_list:
            data_to_save.append({
                't1': item['t1'].to_dict(orient='records'),
                't2': item['t2'].to_dict(orient='records'),
                'date': item['date']
            })
        json_content = json.dumps(data_to_save, ensure_ascii=False, indent=2)
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            f.write(json_content)

        push_file_to_github(HISTORY_FILE, json_content.encode('utf-8'), "Mise à jour historique matchs")
    except Exception:
        pass

# --- INITIALISATION DE L'ÉTAT ---
if 'show_landing' not in st.session_state:
    st.session_state['show_landing'] = True

if 'players_version' not in st.session_state:
    st.session_state.players_version = 0

if 'jokers_version' not in st.session_state:
    st.session_state.jokers_version = 0

if 'players_df' not in st.session_state:
    st.session_state.players_df = load_data()

if 'jokers_db' not in st.session_state:
    st.session_state.jokers_db = load_jokers_db()

if 'history' not in st.session_state:
    st.session_state.history = load_history()

if 'selected_players_set' not in st.session_state:
    st.session_state.selected_players_set = set()

if 'jokers_list' not in st.session_state:
    st.session_state.jokers_list = []

def update_checkbox(player_name):
    key = f"chk_{player_name}"
    if st.session_state[key]:
        st.session_state.selected_players_set.add(player_name)
    else:
        st.session_state.selected_players_set.discard(player_name)

# ==========================================
# 🖼️ PAGE DE GARDE
# ==========================================
if st.session_state.get('show_landing', True):
    if os.path.exists(IMAGE_PATH):
        with open(IMAGE_PATH, "rb") as f:
            img_bytes = f.read()
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        
        st.markdown('<div class="landing-wrapper">', unsafe_allow_html=True)
        st.markdown(
            f"""
            <img class="landing-img" src="data:image/jpeg;base64,{img_b64}" alt="Soccer FFL Kompo Intro">
            """, 
            unsafe_allow_html=True
        )
        
        if st.button("🚀 ENTRER DANS L'APPLICATION", type="primary", use_container_width=True):
            st.session_state['show_landing'] = False
            st.rerun()
            
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.warning(f"⚠️ Fichier d'image introuvable (`{IMAGE_PATH}`).")
        if st.button("🚀 ENTRER DANS L'APPLICATION", type="primary"):
            st.session_state['show_landing'] = False
            st.rerun()

    st.stop()

# ==========================================
# ⚽ COMPOSITIONS ET RENDU TERRAIN
# ==========================================
def create_player_card(card_path, player_name):
    if not os.path.exists(card_path):
        return None
    
    card_img = Image.open(card_path).convert("RGBA")
    draw = ImageDraw.Draw(card_img)
    w, h = card_img.size
    
    font_size = max(20, int(w * 0.16))
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except Exception:
        font = ImageFont.load_default()
        
    stroke_w = max(2, int(font_size * 0.07))
    
    if player_name.upper().startswith("JOKER"):
        parts = player_name.upper().split(maxsplit=1)
        line1 = parts[0]
        line2 = parts[1] if len(parts) > 1 else ""
        y_center = int(h * (2 / 3))
        
        bbox1 = draw.textbbox((0, 0), line1, font=font)
        w1, h1 = bbox1[2] - bbox1[0], bbox1[3] - bbox1[1]
        x1 = (w - w1) / 2
        
        bbox2 = draw.textbbox((0, 0), line2, font=font)
        w2, h2 = bbox2[2] - bbox2[0], bbox2[3] - bbox2[1]
        x2 = (w - w2) / 2
        
        draw.text((x1, y_center - h1 - 2), line1, fill="black", font=font, stroke_width=stroke_w, stroke_fill="white")
        draw.text((x2, y_center + 2), line2, fill="black", font=font, stroke_width=stroke_w, stroke_fill="white")
    else:
        y_pos = int(h * (2 / 3))
        text_bbox = draw.textbbox((0, 0), player_name.upper(), font=font)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]
        x_pos = (w - text_w) / 2
        y_pos_centered = y_pos - (text_h / 2)
        
        draw.text((x_pos, y_pos_centered), player_name.upper(), fill="white", font=font, stroke_width=stroke_w, stroke_fill="black")
        
    return card_img

def draw_combined_field(t1, t2):
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
    
    pos1 = [(7, 30), (23, 13), (23, 47), (40, 17), (40, 43)]
    players1 = t1.copy()
    players1['Gk_Num'] = players1['Gardien'].apply(text_to_gk_score)
    players1 = players1.sort_values(by="Gk_Num", ascending=False).reset_index(drop=True)
    
    for i, row in players1.iterrows():
        if i >= len(pos1): break
        x, y = pos1[i]
        p_name = str(row['Nom du Joueur'])
        is_joker = bool(row.get('is_joker', False))
        
        card_file = YELLOW_CARD_PATH if (is_joker and os.path.exists(YELLOW_CARD_PATH)) else BLUE_CARD_PATH
        card_img = create_player_card(card_file, p_name)
        
        if card_img:
            ax.imshow(card_img, extent=[x - card_width/2, x + card_width/2, y - card_height/2, y + card_height/2], zorder=3)
        else:
            circle_color = "#FFD700" if is_joker else "#1C6CF6"
            ax.scatter(x, y, color=circle_color, s=350, edgecolors='white', linewidths=2.0, zorder=3)
            ax.text(x, y - 5.5, p_name, color='black' if is_joker else 'white', fontsize=12, weight='bold', ha='center', va='center', zorder=4)
        
    pos2 = [(93, 30), (77, 13), (77, 47), (60, 17), (60, 43)]
    players2 = t2.copy()
    players2['Gk_Num'] = players2['Gardien'].apply(text_to_gk_score)
    players2 = players2.sort_values(by="Gk_Num", ascending=False).reset_index(drop=True)
    
    for i, row in players2.iterrows():
        if i >= len(pos2): break
        x, y = pos2[i]
        p_name = str(row['Nom du Joueur'])
        is_joker = bool(row.get('is_joker', False))
        
        card_file = YELLOW_CARD_PATH if (is_joker and os.path.exists(YELLOW_CARD_PATH)) else RED_CARD_PATH
        card_img = create_player_card(card_file, p_name)
        
        if card_img:
            ax.imshow(card_img, extent=[x - card_width/2, x + card_width/2, y - card_height/2, y + card_height/2], zorder=3)
        else:
            circle_color = "#FFD700" if is_joker else "#E03131"
            ax.scatter(x, y, color=circle_color, s=350, edgecolors='white', linewidths=2.0, zorder=3)
            ax.text(x, y - 5.5, p_name, color='black' if is_joker else 'white', fontsize=12, weight='bold', ha='center', va='center', zorder=4)
    
    ax.text(25, 64, "ÉQUIPE 1", color='white', fontsize=16, weight='bold', ha='center', va='center')
    ax.text(75, 64, "ÉQUIPE 2", color='white', fontsize=16, weight='bold', ha='center', va='center')
    
    ax.set_xlim(-6, 106)
    ax.set_ylim(-4, 68)
    ax.axis('off')
    plt.tight_layout()
    return fig

def render_teams_summary(t1, t2):
    att1, att2 = t1['Attaque'].apply(text_to_score).sum(), t2['Attaque'].apply(text_to_score).sum()
    def1, def2 = t1['Défense'].apply(text_to_score).sum(), t2['Défense'].apply(text_to_score).sum()
    col1, col2 = t1['Collectif'].apply(text_to_score).sum(), t2['Collectif'].apply(text_to_score).sum()
    gk1, gk2 = t1['Gardien'].apply(text_to_gk_score).sum(), t2['Gardien'].apply(text_to_gk_score).sum()
    
    avg_att1, avg_att2 = att1 / len(t1), att2 / len(t2)
    avg_def1, avg_def2 = def1 / len(t1), def2 / len(t2)
    avg_col1, avg_col2 = col1 / len(t1), col2 / len(t2)
    
    st.markdown("### 📊 Récapitulatif des Niveaux d'Équipe")
    
    summary_data = {
        "Compétence": ["Attaque (Moyenne)", "Défense (Moyenne)", "Collectif (Moyenne)", "Gardien(s) Spécialisé(s)"],
        "🔵 Équipe 1": [f"{avg_att1:.1f} / 10 (Total: {att1})", f"{avg_def1:.1f} / 10 (Total: {def1})", f"{avg_col1:.1f} / 10 (Total: {col1})", f"{gk1} joueur(s)"],
        "🔴 Équipe 2": [f"{avg_att2:.1f} / 10 (Total: {att2})", f"{avg_def2:.1f} / 10 (Total: {def2})", f"{avg_col2:.1f} / 10 (Total: {col2})", f"{gk2} joueur(s)"]
    }
    st.table(pd.DataFrame(summary_data))

@st.dialog("Compositions du Match", width="large")
def show_teams_popup(t1, t2):
    st.write("Match équilibré généré avec succès ! 📸")
    fig_combined = draw_combined_field(t1, t2)
    st.pyplot(fig_combined, use_container_width=True)
    
    buf = io.BytesIO()
    fig_combined.savefig(buf, format="png", bbox_inches='tight', dpi=250, facecolor='#226343')
    buf.seek(0)
    
    st.download_button(label="📸 Télécharger l'image (PNG)", data=buf, file_name="Compositions_FFL.png", mime="image/png", type="primary")
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
    
    render_teams_summary(t1, t2)
    
    if st.button("Fermer"): 
        st.rerun()

def compute_best_teams(players_list, j1, j2, same_team_players):
    best_diff = float('inf')
    best_gk_diff = float('inf')
    best_team1, best_team2 = None, None
    valid_combo_found = False
    
    for combo in itertools.combinations(players_list, 5):
        t1 = list(combo)
        t2 = [p for p in players_list if p not in t1]
        
        names_t1 = set(p['Nom du Joueur'] for p in t1)
        names_t2 = set(p['Nom du Joueur'] for p in t2)
        
        if same_team_players:
            st_set = set(same_team_players)
            if not (st_set.issubset(names_t1) or st_set.issubset(names_t2)):
                continue

        if j1 != "Aucune restriction" and j2 != "Aucun":
            if (j1 in names_t1 and j2 in names_t1) or (j1 in names_t2 and j2 in names_t2):
                continue
        
        valid_combo_found = True
        df_t1 = pd.DataFrame(t1)
        df_t2 = pd.DataFrame(t2)
        
        t1_gk_sum = df_t1['Gardien'].apply(text_to_gk_score).sum()
        t2_gk_sum = df_t2['Gardien'].apply(text_to_gk_score).sum()
        gk_diff = abs(t1_gk_sum - t2_gk_sum)
        
        t1_att_sum = df_t1['Attaque'].apply(text_to_score).sum()
        t1_def_sum = df_t1['Défense'].apply(text_to_score).sum()
        t1_col_sum = df_t1['Collectif'].apply(text_to_score).sum()
        
        t2_att_sum = df_t2['Attaque'].apply(text_to_score).sum()
        t2_def_sum = df_t2['Défense'].apply(text_to_score).sum()
        t2_col_sum = df_t2['Collectif'].apply(text_to_score).sum()
        
        field_diff = abs(t1_att_sum - t2_att_sum) + abs(t1_def_sum - t2_def_sum) + abs(t1_col_sum - t2_col_sum)
        
        if (gk_diff < best_gk_diff) or (gk_diff == best_gk_diff and field_diff < best_diff):
            best_gk_diff = gk_diff
            best_diff = field_diff
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
        st.session_state['show_landing'] = True
        st.rerun()

if st.session_state.get("open_teams_popup", False):
    st.session_state.open_teams_popup = False
    show_teams_popup(st.session_state.last_team1, st.session_state.last_team2)

tab1, tab2, tab3 = st.tabs(["⚖️ Équilibrage du Jour", "🏃 Gestion des Bases", "📜 Historique"])

# ==========================================
# ⚖️ TAB 1 : ÉQUILIBRAGE
# ==========================================
with tab1:
    with st.expander("📋 Analyser une convocation WhatsApp (Optionnel)", expanded=True):
        convoc_text = st.text_area("Colle le texte brut de ta convocation ici :", height=150, placeholder="Présents :\n1. Cyril V\n2. Nico P\n3. Benoit...")
        
        if st.button("🔍 Extraire et Valider les Joueurs"):
            if convoc_text.strip():
                match_presents = re.search(r"présents?\b[:\-\s]*(.*)", convoc_text, re.IGNORECASE | re.DOTALL)
                target_text = match_presents.group(1) if match_presents else convoc_text

                stop_pattern = r"(jokers?|à\s*confirmer|a\s*confirmer|absents?|infirmerie)"
                split_parts = re.split(stop_pattern, target_text, flags=re.IGNORECASE)
                valid_presents_text = split_parts[0]

                raw_lines = re.split(r"[\n,;]+", valid_presents_text)
                cleaned_items = []
                
                for line in raw_lines:
                    clean = re.sub(r"^\s*[\d\.\-\*\•\(\)\:]+\s*", "", line.strip())
                    clean = re.sub(r"\(\s*\d+\s*\)", "", clean).strip()
                    if clean:
                        cleaned_items.append(clean)

                df_db = st.session_state.players_df
                alias_map = {}
                for _, row in df_db.iterrows():
                    real_name = row["Nom du Joueur"]
                    alias_
