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

# Fichiers requis
DATA_FILE = 'database_joueurs_v2.xlsx'       
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
    """ Convertit n'importe quelle valeur en entier strict entre 1 et 10 """
    if pd.isna(val):
        return 5
    match = re.search(r'\d+', str(val))
    if match:
        return max(1, min(10, int(match.group())))
    return 5

def text_to_gk_score(val):
    """ Convertit une note de gardien en 0 ou 1 (>= 6 devient 1, < 6 devient 0) """
    if pd.isna(val):
        return 0
    match = re.search(r'\d+', str(val))
    if match:
        num = int(match.group())
        return 1 if num >= 6 else 0
    return 0

def load_data():
    if os.path.exists(DATA_FILE):
        try: 
            df = pd.read_excel(DATA_FILE)
            if "Surnoms" not in df.columns:
                df["Surnoms"] = ""
            if "Gardien" not in df.columns:
                df["Gardien"] = 0
                
            df["Surnoms"] = df["Surnoms"].fillna("")
            
            # Conversion des compétences
            for col in ["Attaque", "Défense", "Collectif"]:
                if col in df.columns:
                    df[col] = df[col].apply(text_to_score)
            
            # Conversion Gardien : <6 -> 0 et >=6 -> 1
            if "Gardien" in df.columns:
                df["Gardien"] = df["Gardien"].apply(text_to_gk_score)
                
            return df
        except Exception: 
            pass
            
    return pd.DataFrame({
        "Nom du Joueur": ["Antho", "Cyril V", "Apou", "Benoit", "Nico P", "Mouyss", "Cédric", "Nico M", "David", "Cyril L"],
        "Attaque": [9, 5, 7, 9, 5, 7, 3, 7, 5, 3],
        "Défense": [5, 9, 5, 3, 9, 3, 9, 5, 7, 7],
        "Gardien": [0, 0, 1, 0, 1, 0, 1, 0, 0, 0], # Notes mises à jour (>=6 -> 1, <6 -> 0)
        "Collectif": [7, 9, 7, 5, 7, 5, 7, 5, 5, 5],
        "Surnoms": ["", "Cyril", "", "beny", "nicop, nico", "mouys", "", "nicom, nico", "Dav, dimeh", "Cyril"]
    })

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

if 'players_df' not in st.session_state:
    st.session_state.players_df = load_data()

if 'auto_selected' not in st.session_state:
    st.session_state.auto_selected = set()

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
    if st.button("Fermer"): 
        st.rerun()

@st.dialog("🃏 Saisie des Joueurs Jokers", width="medium")
def add_jokers_dialog():
    nb_missing = st.session_state.jokers_info['nb_missing']
    selected_players_df = st.session_state.jokers_info['selected_players'].copy()
    selected_players_df['is_joker'] = False
    
    j1 = st.session_state.jokers_info['j1']
    j2 = st.session_state.jokers_info['j2']

    st.write(f"Il manque **{nb_missing}** joueur(s) pour atteindre 10. Renseignez leurs prénoms et notes :")
    
    jokers_input = []
    with st.form("form_jokers"):
        for k in range(nb_missing):
            st.markdown(f"**Joker {k+1}**")
            col_j_name, col_j_score, col_j_gk = st.columns([2, 1, 1])
            with col_j_name:
                j_name = st.text_input(f"Prénom du Joker {k+1}", value=f"Joker {k+1}", key=f"j_name_{k}")
            with col_j_score:
                j_score = st.number_input(f"Note (1 à 10)", min_value=1, max_value=10, value=5, key=f"j_score_{k}")
            with col_j_gk:
                j_gk = st.selectbox(f"Gardien ?", options=[0, 1], index=0, key=f"j_gk_{k}")
            jokers_input.append((j_name.strip(), j_score, j_gk))
        
        submit_jokers = st.form_submit_button("⚡ Valider et Générer avec les Jokers", type="primary")
        
    if submit_jokers:
        jokers_rows = []
        for j_name, j_score, j_gk in jokers_input:
            num_score = text_to_score(j_score)
            jokers_rows.append({
                "Nom du Joueur": f"Joker {j_name}" if not j_name.startswith("Joker") else j_name,
                "Attaque": num_score,
                "Défense": num_score,
                "Gardien": text_to_gk_score(j_gk),
                "Collectif": num_score,
                "Surnoms": "",
                "is_joker": True
            })
            
        full_group_df = pd.concat([selected_players_df, pd.DataFrame(jokers_rows)], ignore_index=True)
        
        players_list = full_group_df.to_dict(orient='records')
        best_diff = float('inf')
        best_gk_diff = float('inf')
        best_team1, best_team2 = None, None
        valid_combo_found = False
        
        for combo in itertools.combinations(players_list, 5):
            t1 = list(combo)
            t2 = [p for p in players_list if p not in t1]
            
            names_t1 = [p['Nom du Joueur'] for p in t1]
            names_t2 = [p['Nom du Joueur'] for p in t2]
            
            if j1 != "Aucune restriction" and j2 != "Aucun":
                if (j1 in names_t1 and j2 in names_t1) or (j1 in names_t2 and j2 in names_t2):
                    continue
            
            valid_combo_found = True
            df_t1 = pd.DataFrame(t1)
            df_t2 = pd.DataFrame(t2)
            
            t1_gk_sum  = df_t1['Gardien'].apply(text_to_gk_score).sum()
            t2_gk_sum  = df_t2['Gardien'].apply(text_to_gk_score).sum()
            gk_diff = abs(t1_gk_sum - t2_gk_sum)
            
            t1_att_sum = df_t1['Attaque'].apply(text_to_score).sum()
            t1_def_sum = df_t1['Défense'].apply(text_to_score).sum()
            t1_col_sum = df_t1['Collectif'].apply(text_to_score).sum()
            
            t2_att_sum = df_t2['Attaque'].apply(text_to_score).sum()
            t2_def_sum = df_t2['Défense'].apply(text_to_score).sum()
            t2_col_sum = df_t2['Collectif'].apply(text_to_score).sum()
            
            field_diff = abs(t1_att_sum - t2_att_sum) + abs(t1_def_sum - t2_def_sum) + abs(t1_col_sum - t2_col_sum)
            
            # Priorité 1: Même nombre de gardiens (diff gardiens min). Priorité 2: Différence globale min.
            if (gk_diff < best_gk_diff) or (gk_diff == best_gk_diff and field_diff < best_diff):
                best_gk_diff = gk_diff
                best_diff = field_diff
                best_team1 = df_t1
                best_team2 = df_t2
                
        if valid_combo_found:
            st.session_state.last_team1 = best_team1
            st.session_state.last_team2 = best_team2
            st.session_state.open_teams_popup = True
            st.session_state.show_jokers_modal = False
            st.rerun()

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

# --- GESTION DES POP-UPS DEPUIS LE FLUX PRINCIPAL ---
if st.session_state.get("show_jokers_modal", False):
    add_jokers_dialog()

if st.session_state.get("open_teams_popup", False):
    st.session_state.open_teams_popup = False
    show_teams_popup(st.session_state.last_team1, st.session_state.last_team2)

tab1, tab2 = st.tabs(["⚖️ Équilibrage du Jour", "🏃 Gestion de la Base"])

with tab1:
    with st.expander("📋 Analyser une convocation WhatsApp (Optionnel)", expanded=False):
        convoc_text = st.text_area("Colle le texte brut de ta convocation ici :", height=150, placeholder="Présents : nicoP (1) , dimeh(2)...")
        
        if st.button("🔍 Extraire et Valider les Joueurs"):
            if convoc_text.strip():
                match = re.search(r"Présents\s*:\s*(.*)", convoc_text, re.IGNORECASE)
                if match:
                    raw_presents = match.group(1).split("\n")[0]
                    cleaned_line = re.sub(r"\(\s*\d+\s*\)", "", raw_presents)
                    extracted_names = [n.strip() for n in re.split(r"[, ]+", cleaned_line) if n.strip()]
                    
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
                    
                    for raw_name in extracted_names:
                        key = raw_name.lower()
                        if key in alias_map:
                            candidates = alias_map[key]
                            if len(candidates) == 1:
                                found_players.add(candidates[0])
                            else:
                                ambiguous_matches.append({
                                    "convoc_name": raw_name,
                                    "candidates": candidates
                              
