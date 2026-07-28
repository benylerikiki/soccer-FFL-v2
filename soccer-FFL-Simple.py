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

# Fichiers requis
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
    avg = (att + defe + col) / 3.0
    return round(avg, 1)

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

# --- FONCTIONS HISTORIQUE ---
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
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

if 'players_df' not in st.session_state:
    st.session_state.players_df = load_data()

if 'jokers_db' not in st.session_state:
    st.session_state.jokers_db = load_jokers_db()

if 'history' not in st.session_state:
    st.session_state.history = load_history()

# Ensemble des noms de joueurs sélectionnés pour le match
if 'selected_players_set' not in st.session_state:
    st.session_state.selected_players_set = set()

if 'jokers_list' not in st.session_state:
    st.session_state.jokers_list = []

# Synchronisation de l'état des Checkboxes
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
    
    # Équipe 1
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
        
    # Équipe 2
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
                    alias_map.setdefault(real_name.lower(), []).append(real_name)
                    surnoms = [s.strip().lower() for s in str(row["Surnoms"]).split(",") if s.strip()]
                    for s in surnoms:
                        if real_name not in alias_map.setdefault(s, []):
                            alias_map[s].append(real_name)
                
                found_players = set()
                unknown_names = []
                ambiguous_matches = []
                
                for raw_item in cleaned_items:
                    key = raw_item.lower()
                    if key in alias_map:
                        candidates = alias_map[key]
                        if len(candidates) == 1:
                            found_players.add(candidates[0])
                        else:
                            ambiguous_matches.append({"convoc_name": raw_item, "candidates": candidates})
                    else:
                        tokens = [t.strip() for t in raw_item.split() if len(t.strip()) > 1]
                        matched = False
                        for token in tokens:
                            token_key = token.lower()
                            if token_key in alias_map:
                                candidates = alias_map[token_key]
                                if len(candidates) == 1:
                                    found_players.add(candidates[0])
                                    matched = True
                                else:
                                    ambiguous_matches.append({"convoc_name": token, "candidates": candidates})
                                    matched = True
                        if not matched:
                            unknown_names.append(raw_item)
                
                # Mise à jour de l'ensemble source de vérité et réinitialisation des clefs individuelles
                st.session_state.selected_players_set = found_players
                for p in df_db["Nom du Joueur"]:
                    st.session_state[f"chk_{p}"] = (p in found_players)

                st.session_state.unknown_names = unknown_names
                st.session_state.ambiguous_matches = ambiguous_matches
                
                if found_players:
                    st.success(f"✅ {len(found_players)} joueur(s) reconnu(s) et coché(s) : {', '.join(found_players)}")
                    st.rerun()
                else:
                    st.error("Aucun joueur de la base n'a été reconnu dans la liste des présents.")
            else:
                st.warning("Veuillez coller un texte de convocation.")

    if st.session_state.get("unknown_names"):
        st.warning(f"⚠️ Éléments non reconnus : {', '.join(st.session_state.unknown_names)}")
    if st.session_state.get("ambiguous_matches"):
        st.info("ℹ️ Surnoms ambigus détectés. Veuillez ajuster la sélection ci-dessous.")

    st.subheader("1. Sélection des Joueurs Présents")
    df_players = st.session_state.players_df
    
    cols = st.columns(3)
    for idx, row in df_players.iterrows():
        p_name = row["Nom du Joueur"]
        key_chk = f"chk_{p_name}"
        
        # Initialisation si nécessaire
        if key_chk not in st.session_state:
            st.session_state[key_chk] = p_name in st.session_state.selected_players_set
            
        with cols[idx % 3]:
            st.checkbox(
                p_name, 
                key=key_chk, 
                on_change=update_checkbox, 
                args=(p_name,)
            )

    st.markdown("---")
    st.subheader("2. Joueurs Jokers / Invités (Optionnel)")
    
    with st.expander("➕ Ajouter / Sélectionner un Joker", expanded=False):
        jokers_db = st.session_state.jokers_db
        choice_joker_type = st.radio("Type de Joker :", ["Saisir un Nouveau Joker", "Sélectionner un Joker existant dans la base"], horizontal=True, key="radio_jk_type")
        all_regular_players = df_players["Nom du Joueur"].tolist()
        
        if choice_joker_type == "Sélectionner un Joker existant dans la base":
            if jokers_db.empty:
                st.info("Aucun Joker n'est actuellement enregistré dans la base.")
            else:
                joker_options = {}
                for idx, r_jk in jokers_db.iterrows():
                    host_str = str(r_jk['Joueur Rattaché']) if pd.notna(r_jk['Joueur Rattaché']) else "Aucun"
                    j_label = f"{r_jk['Nom Joker']} (Rattaché à {host_str})"
                    joker_options[j_label] = r_jk
                
                selected_j_label = st.selectbox("Choisir le Joker :", options=list(joker_options.keys()), key="sel_exist_jk")
                selected_jk_row = joker_options[selected_j_label]
                
                host_player = str(selected_jk_row.get("Joueur Rattaché", ""))
                score_val = text_to_score(selected_jk_row.get("Note Globale", 5))
                
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.info(f"👤 **Joueur rattaché :** {host_player if host_player else 'Aucun'}")
                with col_info2:
                    st.info(f"⭐ **Note Globale :** {score_val} / 10")
                
                if host_player and host_player not in st.session_state.selected_players_set:
                    st.warning(f"⚠️ **Avertissement :** Le joueur rattaché (**{host_player}**) n'est pas coché dans la liste des présents ci-dessus.")
                
                if st.button("➕ Valider et Ajouter ce Joker", type="primary", key="btn_add_exist_jk"):
                    jk_name_str = str(selected_jk_row['Nom Joker']).strip()
                    final_jk_name = f"Joker {jk_name_str}" if not jk_name_str.startswith("Joker") else jk_name_str
                    
                    st.session_state.jokers_list.append({
                        "Nom du Joueur": final_jk_name,
                        "Attaque": score_val,
                        "Défense": score_val,
                        "Gardien": 1,
                        "Collectif": score_val,
                        "Surnoms": "",
                        "is_joker": True
                    })
                    st.success(f"Joker '{final_jk_name}' ajouté !")
                    st.rerun()

        else:
            with st.form("form_add_new_joker"):
                col_jk1, col_jk2, col_jk3 = st.columns([2, 2, 1])
                with col_jk1:
                    jk_name = st.text_input("Prénom / Nom du Joker", value="Joker")
                with col_jk2:
                    jk_host = st.selectbox("Joueur Rattaché (Hôte)", options=all_regular_players)
                with col_jk3:
                    jk_score = st.number_input("Note Globale (1-10)", min_value=1, max_value=10, value=5)
                
                btn_add_new_joker = st.form_submit_button("➕ Valider et Créer ce Joker", type="primary")
                
                if btn_add_new_joker:
                    clean_name = jk_name.strip()
                    if not clean_name:
                        st.error("Veuillez saisir un nom pour le joker.")
                    else:
                        final_jk_name = f"Joker {clean_name}" if not clean_name.startswith("Joker") else clean_name
                        score_val = text_to_score(jk_score)
                        
                        new_joker_entry = pd.DataFrame([{
                            "Nom Joker": clean_name,
                            "Joueur Rattaché": jk_host,
                            "Note Globale": score_val,
                            "Attaque": score_val,
                            "Défense": score_val,
                            "Gardien": 1,
                            "Collectif": score_val
                        }])
                        st.session_state.jokers_db = pd.concat([st.session_state.jokers_db, new_joker_entry], ignore_index=True)
                        save_jokers_db(st.session_state.jokers_db)

                        st.session_state.jokers_list.append({
                            "Nom du Joueur": final_jk_name,
                            "Attaque": score_val,
                            "Défense": score_val,
                            "Gardien": 1,
                            "Collectif": score_val,
                            "Surnoms": "",
                            "is_joker": True
                        })
                        st.success(f"Joker '{final_jk_name}' créé et sauvegardé dans la base !")
                        st.rerun()

    if st.session_state.jokers_list:
        st.markdown("**Jokers configurés pour ce match :**")
        for jk_idx, jk_item in enumerate(st.session_state.jokers_list):
            c_jk_text, c_jk_del = st.columns([4, 1])
            with c_jk_text:
                st.info(f"🃏 **{jk_item['Nom du Joueur']}** - Note: {jk_item['Attaque']}/10 | Gardien: 1")
            with c_jk_del:
                if st.button("❌", key=f"del_jk_{jk_idx}"):
                    st.session_state.jokers_list.pop(jk_idx)
                    st.rerun()

    all_active_players = list(st.session_state.selected_players_set) + [j["Nom du Joueur"] for j in st.session_state.jokers_list]
    total_count = len(all_active_players)
    st.markdown(f"**Nombre total de joueurs retenus pour le match :** `{total_count} / 10`")

    st.markdown("---")
    st.subheader("3. Restrictions & Affinités (Sur tous les joueurs présents)")
    
    same_team_players = st.multiselect(
        "🤝 Joueurs à Mettre IMPÉRATIVEMENT dans la MÊME ÉQUIPE :",
        options=all_active_players,
        help="Sélectionne 2 joueurs ou plus qui doivent impérativement jouer ensemble."
    )
    
    col_j1, col_j2 = st.columns(2)
    with col_j1:
        j1 = st.selectbox("🚫 Ne pas faire jouer (Joueur 1)", ["Aucune restriction"] + all_active_players, key="j1_select")
    with col_j2:
        j2 = st.selectbox("...dans la même équipe que (Joueur 2)", ["Aucun"] + all_active_players, key="j2_select")

    st.markdown("---")
    if st.button("⚽ Générer les Équipes Équilibrées", type="primary"):
        if total_count != 10:
            st.error(f"Veuillez ajuster la sélection pour avoir exactement 10 joueurs (Actuellement: {total_count}).")
        elif len(same_team_players) > 5:
            st.error("Impossible de forcer plus de 5 joueurs dans la même équipe !")
        else:
            selected_df = df_players[df_players["Nom du Joueur"].isin(st.session_state.selected_players_set)].copy()
            selected_df['is_joker'] = False
            players_list = selected_df.to_dict(orient='records')
            
            for jk in st.session_state.jokers_list:
                players_list.append(jk)
                
            valid_combo, best_t1, best_t2 = compute_best_teams(players_list, j1, j2, same_team_players)
                    
            if valid_combo:
                st.session_state.history.insert(0, {
                    't1': best_t1,
                    't2': best_t2,
                    'date': pd.Timestamp.now().strftime("%d/%m/%Y à %H:%M")
                })
                st.session_state.history = st.session_state.history[:10]
                save_history(st.session_state.history)

                st.session_state.last_team1 = best_t1
                st.session_state.last_team2 = best_t2
                st.session_state.open_teams_popup = True
                st.rerun()
            else:
                st.error("Aucune combinaison valide trouvée respectant l'ensemble de vos contraintes.")

with tab2:
    st.subheader("🏃 Gestion des Bases de Données")
    
    tab_db1, tab_db2 = st.tabs(["📋 Base Principale Joueurs", "🃏 Base Dédiée Jokers"])
    
    with tab_db1:
        col_add_p, col_del_p = st.columns(2)
        
        with col_add_p:
            with st.expander("➕ Ajouter un Joueur à la Base", expanded=False):
                with st.form("form_add_new_player"):
                    new_p_name = st.text_input("Nom du Joueur *")
                    c_att, c_def, c_col = st.columns(3)
                    with c_att:
                        new_p_att = st.selectbox("Attaque", options=NUMERIC_OPTIONS, index=4)
                    with c_def:
                        new_p_def = st.selectbox("Défense", options=NUMERIC_OPTIONS, index=4)
                    with c_col:
                        new_p_col = st.selectbox("Collectif", options=NUMERIC_OPTIONS, index=4)
                    new_p_gk = st.selectbox("Gardien (0 ou 1)", options=GK_OPTIONS, index=0)
                    new_p_surnoms = st.text_input("Surnoms (séparés par des virgules)", placeholder="ex: Nico, Nicop")
                    
                    btn_confirm_add_p = st.form_submit_button("➕ Valider l'ajout du joueur", type="primary")
                    
                    if btn_confirm_add_p:
                        if not new_p_name.strip():
                            st.error("Veuillez saisir un nom de joueur.")
                        else:
                            clean_p_name = new_p_name.strip()
                            new_row = pd.DataFrame([{
                                "Nom du Joueur": clean_p_name,
                                "Attaque": new_p_att,
                                "Défense": new_p_def,
                                "Gardien": new_p_gk,
                                "Collectif": new_p_col,
                                "Surnoms": new_p_surnoms.strip()
                            }])
                            st.session_state.players_df = pd.concat([st.session_state.players_df, new_row], ignore_index=True)
                            save_data(st.session_state.players_df)
                            st.session_state.players_df = load_data()
                            st.success(f"Joueur '{clean_p_name}' ajouté avec succès !")
                            st.rerun()

        with col_del_p:
            with st.expander("❌ Supprimer un Joueur de la Base", expanded=False):
                existing_p_names = sorted(st.session_state.players_df["Nom du Joueur"].dropna().unique().tolist())
                if existing_p_names:
                    p_to_del = st.selectbox("Choisir le joueur à supprimer :", options=existing_p_names, key="sel_del_p")
                    if st.button("🗑️ Confirmer la suppression", type="secondary", key="btn_del_p"):
                        st.session_state.players_df = st.session_state.players_df[st.session_state.players_df["Nom du Joueur"] != p_to_del].reset_index(drop=True)
                        save_data(st.session_state.players_df)
                        st.session_state.players_df = load_data()
                        st.success(f"Joueur '{p_to_del}' supprimé de la base.")
                        st.rerun()
                else:
                    st.info("Aucun joueur dans la base.")

        st.markdown("---")
        
        col_exp, col_imp = st.columns(2)
        with col_exp:
            st.markdown("**📥 Exporter la base joueurs**")
            output_buffer = io.BytesIO()
            with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
                st.session_state.players_df.to_excel(writer, index=False)
            output_buffer.seek(0)
            
            st.download_button(
                label="⬇️ Télécharger la base (.xlsx)",
                data=output_buffer,
                file_name="database_joueurs_v2.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        with col_imp:
            st.markdown("**📤 Importer un fichier Excel Joueurs**")
            uploaded_file = st.file_uploader("Charger un fichier .xlsx", type=["xlsx"], key="up_players")
            if uploaded_file is not None:
                try:
                    new_df = pd.read_excel(uploaded_file)
                    save_data(new_df)
                    st.session_state.players_df = load_data()
                    st.success("✅ Base de données mise à jour !")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")

        st.markdown("---")
        st.session_state.players_df["Note Globale"] = st.session_state.players_df.apply(calculate_global_score, axis=1)
        
        edited_df = st.data_editor(
            st.session_state.players_df,
            num_rows="dynamic",
            column_config={
                "Attaque": st.column_config.SelectboxColumn("Attaque", options=NUMERIC_OPTIONS, default=5),
                "Défense": st.column_config.SelectboxColumn("Défense", options=NUMERIC_OPTIONS, default=5),
                "Gardien": st.column_config.SelectboxColumn("Gardien (0 ou 1)", options=GK_OPTIONS, default=0),
                "Collectif": st.column_config.SelectboxColumn("Collectif", options=NUMERIC_OPTIONS, default=5),
                "Note Globale": st.column_config.NumberColumn("Note Globale", format="%.1f", disabled=True),
            },
            key="data_editor_players"
        )
        
        if st.button("💾 Enregistrer la base joueurs", type="primary"):
            save_data(edited_df)
            st.session_state.players_df = load_data()
            st.success("Base enregistrée !")
            st.rerun()

    with tab_db2:
        col_add_j, col_del_j = st.columns(2)
        
        with col_add_j:
            with st.expander("➕ Ajouter un Joker à la Base", expanded=False):
                with st.form("form_add_new_joker_db"):
                    new_j_name = st.text_input("Nom du Joker *")
                    all_hosts = sorted(st.session_state.players_df["Nom du Joueur"].dropna().unique().tolist())
                    new_j_host = st.selectbox("Joueur Rattaché (Hôte)", options=all_hosts if all_hosts else ["Aucun"])
                    new_j_score = st.selectbox("Note Globale (1-10)", options=NUMERIC_OPTIONS, index=4)
                    
                    btn_confirm_add_j = st.form_submit_button("➕ Valider l'ajout du joker", type="primary")
                    
                    if btn_confirm_add_j:
                        if not new_j_name.strip():
                            st.error("Veuillez saisir un nom de joker.")
                        else:
                            clean_j_name = new_j_name.strip()
                            new_j_row = pd.DataFrame([{
                                "Nom Joker": clean_j_name,
                                "Joueur Rattaché": new_j_host,
                                "Note Globale": new_j_score,
                                "Attaque": new_j_score,
                                "Défense": new_j_score,
                                "Gardien": 1,
                                "Collectif": new_j_score
                            }])
                            st.session_state.jokers_db = pd.concat([st.session_state.jokers_db, new_j_row], ignore_index=True)
                            save_jokers_db(st.session_state.jokers_db)
                            st.session_state.jokers_db = load_jokers_db()
                            st.success(f"Joker '{clean_j_name}' ajouté à la base !")
                            st.rerun()

        with col_del_j:
            with st.expander("❌ Supprimer un Joker de la Base", expanded=False):
                existing_j_names = sorted(st.session_state.jokers_db["Nom Joker"].dropna().unique().tolist()) if not st.session_state.jokers_db.empty else []
                if existing_j_names:
                    j_to_del = st.selectbox("Choisir le joker à supprimer :", options=existing_j_names, key="sel_del_j")
                    if st.button("🗑️ Confirmer la suppression", type="secondary", key="btn_del_j"):
                        st.session_state.jokers_db = st.session_state.jokers_db[st.session_state.jokers_db["Nom Joker"] != j_to_del].reset_index(drop=True)
                        save_jokers_db(st.session_state.jokers_db)
                        st.session_state.jokers_db = load_jokers_db()
                        st.success(f"Joker '{j_to_del}' supprimé de la base.")
                        st.rerun()
                else:
                    st.info("Aucun joker dans la base.")

        st.markdown("---")

        col_exp_j, col_imp_j = st.columns(2)
        
        with col_exp_j:
            st.markdown("**📥 Exporter la base Jokers**")
            output_buffer_j = io.BytesIO()
            with pd.ExcelWriter(output_buffer_j, engine='openpyxl') as writer:
                st.session_state.jokers_db.to_excel(writer, index=False)
            output_buffer_j.seek(0)
            
            st.download_button(
                label="⬇️ Télécharger la base Jokers (.xlsx)",
                data=output_buffer_j,
                file_name="database_jokers.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        with col_imp_j:
            st.markdown("**📤 Importer un fichier Excel Jokers**")
            uploaded_j_file = st.file_uploader("Charger un fichier database_jokers.xlsx", type=["xlsx"], key="up_jokers")
            if uploaded_j_file is not None:
                try:
                    new_j_df = pd.read_excel(uploaded_j_file)
                    save_jokers_db(new_j_df)
                    st.session_state.jokers_db = load_jokers_db()
                    st.success("✅ Base de données Jokers mise à jour avec succès !")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur lors de la lecture du fichier : {e}")

        st.markdown("---")
        st.markdown("**📋 Base de données enregistrée des Jokers :**")
        edited_jokers_df = st.data_editor(
            st.session_state.jokers_db,
            num_rows="dynamic",
            column_config={
                "Joueur Rattaché": st.column_config.SelectboxColumn("Joueur Rattaché", options=st.session_state.players_df["Nom du Joueur"].tolist()),
                "Note Globale": st.column_config.SelectboxColumn("Note Globale", options=NUMERIC_OPTIONS, default=5),
                "Attaque": st.column_config.SelectboxColumn("Attaque", options=NUMERIC_OPTIONS, default=5),
                "Défense": st.column_config.SelectboxColumn("Défense", options=NUMERIC_OPTIONS, default=5),
                "Gardien": st.column_config.SelectboxColumn("Gardien", options=[1], default=1),
                "Collectif": st.column_config.SelectboxColumn("Collectif", options=NUMERIC_OPTIONS, default=5),
            },
            key="data_editor_jokers"
        )
        
        if st.button("💾 Enregistrer la base des Jokers", type="primary"):
            save_jokers_db(edited_jokers_df)
            st.session_state.jokers_db = load_jokers_db()
            st.success("Base des Jokers enregistrée !")
            st.rerun()

with tab3:
    st.subheader("📜 Historique des 10 Dernières Compositions (Sauvegardé)")
    
    if st.button("🗑️ Effacer l'historique"):
        st.session_state.history = []
        save_history([])
        st.success("Historique effacé !")
        st.rerun()

    if not st.session_state.history:
        st.info("Aucune composition n'est actuellement enregistrée dans l'historique.")
    else:
        for idx, match_data in enumerate(st.session_state.history):
            with st.expander(f"⚽ Composition {idx+1} — Générée le {match_data['date']}", expanded=(idx==0)):
                h_t1 = match_data['t1']
                h_t2 = match_data['t2']
                
                fig_hist = draw_combined_field(h_t1, h_t2)
                st.pyplot(fig_hist, use_container_width=True)
                
                buf_h = io.BytesIO()
                fig_hist.savefig(buf_h, format="png", bbox_inches='tight', dpi=250, facecolor='#226343')
                buf_h.seek(0)
                
                st.download_button(
                    label=f"📸 Télécharger le PNG (Match {idx+1})",
                    data=buf_h,
                    file_name=f"Compositions_FFL_{idx+1}.png",
                    mime="image/png",
                    key=f"dl_hist_{idx}"
                )
                
                txt_wa = "⚽ *COMPOSITIONS DU MATCH* ⚽\n\n🔵 *ÉQUIPE 1* :\n"
                for _, r in h_t1.iterrows():
                    txt_wa += f"• {r['Nom du Joueur']}\n"
                txt_wa += "\n🔴 *ÉQUIPE 2* :\n"
                for _, r in h_t2.iterrows():
                    txt_wa += f"• {r['Nom du Joueur']}\n"
                
                st.markdown("**📋 Texte WhatsApp :**")
                st.code(txt_wa, language="text")
                
                render_teams_summary(h_t1, h_t2)
