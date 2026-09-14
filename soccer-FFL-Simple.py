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

# Fichiers requis
DATA_FILE = 'database_joueurs_v2.xlsx'       
BACKUP_FILE = 'database_joueurs_v2_backup.xlsx'
JOKERS_FILE = 'database_jokers.xlsx'
JOKERS_BACKUP_FILE = 'database_jokers_backup.xlsx'

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

if 'show_landing' not in st.session_state:
    st.session_state['show_landing'] = True

if 'session_jokers' not in st.session_state:
    st.session_state['session_jokers'] = []

NUMERIC_OPTIONS = list(range(1, 11))

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
    gk = text_to_score(row.get("Gardien", 5))
    col = text_to_score(row.get("Collectif", 5))
    return round((att + defe + gk + col) / 4.0, 1)

# --- GESTION BASE PRINCIPALE ---
def load_data():
    if os.path.exists(DATA_FILE):
        try: 
            df = pd.read_excel(DATA_FILE)
            if df.empty or "Nom du Joueur" not in df.columns:
                raise ValueError("Fichier vide ou corrompu")
            if "Surnoms" not in df.columns:
                df["Surnoms"] = ""
            if "Gardien" not in df.columns:
                df["Gardien"] = 5
            df["Surnoms"] = df["Surnoms"].fillna("").astype(str)
            for col in ["Attaque", "Défense", "Gardien", "Collectif"]:
                df[col] = df[col].apply(text_to_score) if col in df.columns else 5
            ordered_cols = ["Nom du Joueur", "Attaque", "Défense", "Gardien", "Collectif", "Surnoms"]
            return df[[c for c in ordered_cols if c in df.columns]]
        except Exception: 
            pass
            
    default_df = pd.DataFrame({
        "Nom du Joueur": ["Antho", "Cyril V", "Apou", "Benoit", "Nico P", "Mouyss", "Cédric", "Nico M", "David", "Cyril L"],
        "Attaque": [9, 5, 7, 9, 5, 7, 3, 7, 5, 3],
        "Défense": [5, 9, 5, 3, 9, 3, 9, 5, 7, 7],
        "Gardien": [3, 5, 7, 3, 7, 5, 9, 3, 5, 5],
        "Collectif": [7, 9, 7, 5, 7, 5, 7, 5, 5, 5],
        "Surnoms": ["", "Cyril", "", "beny", "nicop, nico", "mouys", "", "nicom, nico", "Dav, dimeh", "Cyril"]
    })
    default_df.to_excel(DATA_FILE, index=False)
    return default_df

def save_data(df):
    if os.path.exists(DATA_FILE):
        try: shutil.copyfile(DATA_FILE, BACKUP_FILE)
        except Exception: pass

    clean_df = df.copy()
    for col in ["Note Globale", "is_joker"]:
        if col in clean_df.columns:
            clean_df = clean_df.drop(columns=[col])
    for col in ["Attaque", "Défense", "Gardien", "Collectif"]:
        if col in clean_df.columns:
            clean_df[col] = clean_df[col].apply(text_to_score)
    ordered_cols = ["Nom du Joueur", "Attaque", "Défense", "Gardien", "Collectif", "Surnoms"]
    existing_cols = [c for c in ordered_cols if c in clean_df.columns]
    other_cols = [c for c in clean_df.columns if c not in ordered_cols]
    clean_df[existing_cols + other_cols].to_excel(DATA_FILE, index=False)

# --- GESTION BASE JOKERS ---
def load_jokers():
    if os.path.exists(JOKERS_FILE):
        try:
            df = pd.read_excel(JOKERS_FILE)
            if not df.empty and "Nom du Joueur" in df.columns:
                if "Surnoms" not in df.columns:
                    df["Surnoms"] = ""
                df["Surnoms"] = df["Surnoms"].fillna("").astype(str)
                for col in ["Attaque", "Défense", "Gardien", "Collectif"]:
                    df[col] = df[col].apply(text_to_score) if col in df.columns else 5
                ordered_cols = ["Nom du Joueur", "Attaque", "Défense", "Gardien", "Collectif", "Surnoms"]
                return df[[c for c in ordered_cols if c in df.columns]]
        except Exception:
            pass

    default_jokers = pd.DataFrame({
        "Nom du Joueur": ["Joker 1", "Joker 2"],
        "Attaque": [5, 6],
        "Défense": [5, 6],
        "Gardien": [5, 5],
        "Collectif": [5, 6],
        "Surnoms": ["", ""]
    })
    default_jokers.to_excel(JOKERS_FILE, index=False)
    return default_jokers

def save_jokers(df):
    if os.path.exists(JOKERS_FILE):
        try: shutil.copyfile(JOKERS_FILE, JOKERS_BACKUP_FILE)
        except Exception: pass

    clean_df = df.copy()
    for col in ["Note Globale", "is_joker"]:
        if col in clean_df.columns:
            clean_df = clean_df.drop(columns=[col])
    for col in ["Attaque", "Défense", "Gardien", "Collectif"]:
        if col in clean_df.columns:
            clean_df[col] = clean_df[col].apply(text_to_score)
    ordered_cols = ["Nom du Joueur", "Attaque", "Défense", "Gardien", "Collectif", "Surnoms"]
    existing_cols = [c for c in ordered_cols if c in clean_df.columns]
    other_cols = [c for c in clean_df.columns if c not in ordered_cols]
    clean_df[existing_cols + other_cols].to_excel(JOKERS_FILE, index=False)

st.session_state.players_df = load_data()
st.session_state.jokers_df = load_jokers()

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
# ⚽ FONCTIONS TERRAIN & DIALOGS
# ==========================================
def create_player_card(card_path, player_name):
    if not os.path.exists(card_path):
        return None
    card_img = Image.open(card_path).convert("RGBA")
    draw = ImageDraw.Draw(card_img)
    w, h = card_img.size
    y_pos = int(h * (2 / 3))
    font_size = max(24, int(w * 0.18))
    try: font = ImageFont.truetype(FONT_PATH, font_size)
    except Exception: font = ImageFont.load_default()
    text_bbox = draw.textbbox((0, 0), player_name.upper(), font=font)
    x_pos = (w - (text_bbox[2] - text_bbox[0])) / 2
    y_pos_centered = y_pos - ((text_bbox[3] - text_bbox[1]) / 2)
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
    
    card_width, card_height = 13.5, 18.0
    
    # Équipe 1
    pos1 = [(7, 30), (23, 13), (23, 47), (40, 17), (40, 43)]
    players1 = t1.copy()
    players1['Gk_Num'] = players1['Gardien'].apply(text_to_score)
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
            ax.scatter(x, y, color="#FFD700" if is_joker else "#1C6CF6", s=350, edgecolors='white', linewidths=2.0, zorder=3)
            ax.text(x, y - 5.5, p_name, color='black' if is_joker else 'white', fontsize=12, weight='bold', ha='center', va='center', zorder=4)

    # Équipe 2
    pos2 = [(93, 30), (77, 13), (77, 47), (60, 17), (60, 43)]
    players2 = t2.copy()
    players2['Gk_Num'] = players2['Gardien'].apply(text_to_score)
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
            ax.scatter(x, y, color="#FFD700" if is_joker else "#E03131", s=350, edgecolors='white', linewidths=2.0, zorder=3)
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
    
    text_whatsapp = "⚽ *COMPOSITIONS DU MATCH* ⚽\n\n🔵 *ÉQUIPE 1* :\n"
    for _, row in t1.iterrows(): 
        text_whatsapp += f"• {row['Nom du Joueur']}\n"
    text_whatsapp += "\n🔴 *ÉQUIPE 2* :\n"
    for _, row in t2.iterrows(): 
        text_whatsapp += f"• {row['Nom du Joueur']}\n"
    st.markdown("**📋 Texte à copier pour WhatsApp (Noms uniquement) :**")
    st.code(text_whatsapp, language="text")
    if st.button("Fermer"): 
        st.rerun()

# --- POP-UP DÉDIÉ POUR RENSEIGNER LES JOKERS EN AMONT ---
@st.dialog("🃏 Configuration des Jokers", width="medium")
def configure_jokers_dialog(target_count):
    st.write(f"Renseignez les **{target_count}** Jokers pour ce match :")
    
    jokers_source = st.session_state.jokers_df
    saved_jokers_names = list(jokers_source["Nom du Joueur"].unique()) if "Nom du Joueur" in jokers_source.columns else []
    saved_jokers_list = ["-- Saisir un invité libre --"] + saved_jokers_names
    
    current_jokers = st.session_state.get('session_jokers', [])
    temp_inputs = []
    
    with st.form("form_configure_jokers"):
        for k in range(target_count):
            st.markdown(f"**Joker {k+1}**")
            
            # Pré-remplissage si déjà renseigné auparavant
            preset_name = current_jokers[k]['Nom du Joueur'] if k < len(current_jokers) else f"Joker {k+1}"
            preset_score = current_jokers[k]['Attaque'] if k < len(current_jokers) else 5
            
            choice = st.selectbox(f"Depuis la base des Jokers :", options=saved_jokers_list, key=f"cfg_preset_{k}")
            c_name, c_score = st.columns([2, 1])
            with c_name:
                final_name = choice if choice != "-- Saisir un invité libre --" else preset_name
                j_name = st.text_input("Nom / Prénom", value=final_name, key=f"cfg_name_{k}")
            with c_score:
                if choice != "-- Saisir un invité libre --":
                    row_j = jokers_source[jokers_source["Nom du Joueur"] == choice]
                    if not row_j.empty:
                        preset_score = int(calculate_global_score(row_j.iloc[0]))
                j_score = st.number_input("Note (1-10)", min_value=1, max_value=10, value=preset_score, key=f"cfg_score_{k}")
                
            temp_inputs.append((j_name.strip(), j_score))
            st.write("---")
            
        btn_valid = st.form_submit_button("✅ Valider et intégrer les Jokers", type="primary")
        
    if btn_valid:
        new_jokers = []
        for j_name, j_score in temp_inputs:
            num = text_to_score(j_score)
            display_name = f"Joker {j_name}" if not j_name.lower().startswith("joker") else j_name
            new_jokers.append({
                "Nom du Joueur": display_name,
                "Attaque": num, "Défense": num, "Gardien": num, "Collectif": num,
                "Surnoms": "", "is_joker": True
            })
        st.session_state.session_jokers = new_jokers
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

if st.session_state.get("show_jokers_modal", False):
    configure_jokers_dialog(st.session_state.get('jokers_needed_count', 1))

if st.session_state.get("open_teams_popup", False):
    st.session_state.open_teams_popup = False
    show_teams_popup(st.session_state.last_team1, st.session_state.last_team2)

# ==========================================
# 📑 LES 3 ONGLETS
# ==========================================
tab1, tab2, tab3 = st.tabs(["⚖️ Équilibrage du Jour", "🏃 Gestion de la Base", "🃏 Base des Jokers"])

# ----------------- ONGLET 1 : COMPOS -----------------
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
                        for s in [x.strip().lower() for x in str(row["Surnoms"]).split(",") if x.strip()]:
                            if real_name not in alias_map.setdefault(s, []): 
                                alias_map[s].append(real_name)
                    
                    found_players, unknown_names, ambiguous_matches = set(), [], []
                    for raw_name in extracted_names:
                        key = raw_name.lower()
                        if key in alias_map:
                            candidates = alias_map[key]
                            if len(candidates) == 1: 
                                found_players.add(candidates[0])
                            else: 
                                ambiguous_matches.append({"convoc_name": raw_name, "candidates": candidates})
                        else:
                            unknown_names.append(raw_name)
                    
                    st.session_state.auto_selected = found_players
                    st.session_state.unknown_names = unknown_names
                    st.session_state.ambiguous_matches = ambiguous_matches
                    if not unknown_names and not ambiguous_matches:
                        st.success(f"✅ {len(found_players)} joueurs reconnus et cochés !")
                        st.rerun()

    st.subheader("Sélection des présents")
    df_sorted = st.session_state.players_df.sort_values(by="Nom du Joueur").reset_index(drop=True)
    counter_placeholder = st.empty()
    selected_names = []
    
    for i in range(0, len(df_sorted), 3):
        cols = st.columns(3)
        for c_idx in range(3):
            if i + c_idx < len(df_sorted):
                name = df_sorted.iloc[i + c_idx]["Nom du Joueur"]
                with cols[c_idx]:
                    if st.checkbox(name, key=f"chk_{name}_{i+c_idx}", value=(name in st.session_state.auto_selected)):
                        selected_names.append(name)
                        st.session_state.auto_selected.add(name)
                    else:
                        st.session_state.auto_selected.discard(name)
                
    selected_players = st.session_state.players_df[st.session_state.players_df["Nom du Joueur"].isin(selected_names)].copy()
    nb_regulars = len(selected_players)
    
    # Gestion des Jokers préparatoires
    current_jokers = st.session_state.get('session_jokers', [])
    nb_jokers = len(current_jokers)
    total_effective = nb_regulars + nb_jokers

    # Bouton direct pour configurer ou ajuster les jokers en amont
    col_jk_btn1, col_jk_btn2 = st.columns([3, 1])
    with col_jk_btn1:
        if nb_regulars < 10:
            manquants = 10 - nb_regulars
            btn_lbl = f"🃏 Ajouter / Modifier les Jokers ({nb_jokers}/{manquants} défini(s))"
            if st.button(btn_lbl, type="secondary"):
                st.session_state.jokers_needed_count = manquants
                st.session_state.show_jokers_modal = True
                st.rerun()
    with col_jk_btn2:
        if nb_jokers > 0:
            if st.button("❌ Réinitialiser les Jokers"):
                st.session_state.session_jokers = []
                st.rerun()

    # Affichage dynamique du statut des effectifs
    if total_effective == 10:
        if nb_jokers > 0:
            counter_placeholder.success(f"✅ 10 joueurs prêts ! ({nb_regulars} titulaires + {nb_jokers} Jokers)")
        else:
            counter_placeholder.success("✅ 10 joueurs sélectionnés !")
    elif total_effective > 10:
        counter_placeholder.error(f"⚠️ Trop de joueurs ({total_effective}/10). Décochez des titulaires ou ajustez les Jokers !")
    else:
        counter_placeholder.info(f"🏃 Joueurs actuels : {total_effective} / 10 ({nb_regulars} titulaires + {nb_jokers} Jokers)")
        
    st.write("---")
    
    # Rassemblement de tous les noms disponibles pour les restrictions (Titulaires + Jokers déjà saisis)
    jokers_names = [j['Nom du Joueur'] for j in current_jokers]
    all_active_names = sorted(selected_names + jokers_names)

    if len(all_active_names) > 0:
        st.markdown("### ⚙️ Restrictions et Affinités (Titulaires & Jokers)")
        
        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.markdown("**⛔ Séparer deux joueurs (Ne pas faire jouer ensemble)**")
            sep_j1 = st.selectbox("Sélectionner un joueur...", options=["Aucune restriction"] + all_active_names, index=0, key="sep_j1")
            remaining_sep = [n for n in all_active_names if n != sep_j1] if sep_j1 != "Aucune restriction" else []
            sep_j2 = st.selectbox("... à séparer de :", options=["Aucun"] + sorted(remaining_sep), index=0, key="sep_j2") if sep_j1 != "Aucune restriction" else "Aucun"
        
        with col_res2:
            st.markdown("**🤝 Associer deux joueurs (Forcer à jouer ensemble)**")
            pair_j1 = st.selectbox("Sélectionner un joueur...", options=["Aucune restriction"] + all_active_names, index=0, key="pair_j1")
            remaining_pair = [n for n in all_active_names if n != pair_j1] if pair_j1 != "Aucune restriction" else []
            pair_j2 = st.selectbox("... à faire jouer avec :", options=["Aucun"] + sorted(remaining_pair), index=0, key="pair_j2") if pair_j1 != "Aucune restriction" else "Aucun"

        conflict = False
        if (sep_j1 != "Aucune restriction" and sep_j2 != "Aucun") and (pair_j1 != "Aucune restriction" and pair_j2 != "Aucun"):
            if {sep_j1, sep_j2} == {pair_j1, pair_j2}:
                st.error("⚠️ Incohérence : vous demandez à la fois de séparer et d'associer les deux mêmes joueurs !")
                conflict = True

        st.write("")
        
        if st.button("⚡ Générer l'Équilibrage Parfait", type="primary", disabled=conflict):
            if total_effective < 10:
                # Ouvre le dialogue s'il manque encore des jokers non renseignés
                st.session_state.jokers_needed_count = 10 - nb_regulars
                st.session_state.show_jokers_modal = True
                st.rerun()
            elif total_effective == 10:
                selected_players['is_joker'] = False
                
                # Fusion des réguliers et des jokers enregistrés
                if nb_jokers > 0:
                    df_jokers = pd.DataFrame(current_jokers)
                    full_group_df = pd.concat([selected_players, df_jokers], ignore_index=True)
                else:
                    full_group_df = selected_players
                
                players_list = full_group_df.to_dict(orient='records')
                best_diff = float('inf')
                best_team1, best_team2 = None, None
                valid_combo_found = False
                
                for combo in itertools.combinations(players_list, 5):
                    t1 = list(combo)
                    t2 = [p for p in players_list if p not in t1]
                    names_t1, names_t2 = [p['Nom du Joueur'] for p in t1], [p['Nom du Joueur'] for p in t2]
                    
                    # Contrainte 1 : Ne pas jouer ensemble
                    if sep_j1 != "Aucune restriction" and sep_j2 != "Aucun":
                        if (sep_j1 in names_t1 and sep_j2 in names_t1) or (sep_j1 in names_t2 and sep_j2 in names_t2): 
                            continue
                    
                    # Contrainte 2 : Forcer à jouer ensemble
                    if pair_j1 != "Aucune restriction" and pair_j2 != "Aucun":
                        if (pair_j1 in names_t1 and pair_j2 not in names_t1) or (pair_j1 in names_t2 and pair_j2 not in names_t2):
                            continue

                    valid_combo_found = True
                    df_t1, df_t2 = pd.DataFrame(t1), pd.DataFrame(t2)
                    t1_att, t1_def = df_t1['Attaque'].apply(text_to_score).sum(), df_t1['Défense'].apply(text_to_score).sum()
                    t1_gk, t1_col  = df_t1['Gardien'].apply(text_to_score).sum(), df_t1['Collectif'].apply(text_to_score).sum()
                    t2_att, t2_def = df_t2['Attaque'].apply(text_to_score).sum(), df_t2['Défense'].apply(text_to_score).sum()
                    t2_gk, t2_col  = df_t2['Gardien'].apply(text_to_score).sum(), df_t2['Collectif'].apply(text_to_score).sum()
                    total_diff = abs(t1_att - t2_att) + abs(t1_def - t2_def) + abs(t1_gk - t2_gk) + abs(t1_col - t2_col)
                    if total_diff < best_diff:
                        best_diff, best_team1, best_team2 = total_diff, df_t1, df_t2
                
                if valid_combo_found:
                    st.session_state.last_team1 = best_team1
                    st.session_state.last_team2 = best_team2
                    st.session_state.open_teams_popup = True
                    st.rerun()
                else:
                    st.error("Impossible de trouver une combinaison respectant toutes les contraintes imposées.")

    if 'last_team1' in st.session_state and 'last_team2' in st.session_state:
        st.write("---")
        st.markdown("### 📊 Dernières équipes générées")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**🔵 Équipe 1**")
            t1_display = st.session_state.last_team1.copy()
            t1_display["Note Globale"] = t1_display.apply(calculate_global_score, axis=1)
            st.dataframe(t1_display[[c for c in ["Nom du Joueur", "Attaque", "Défense", "Gardien", "Collectif", "Note Globale"] if c in t1_display.columns]], hide_index=True)
        with c2:
            st.markdown("**🔴 Équipe 2**")
            t2_display = st.session_state.last_team2.copy()
            t2_display["Note Globale"] = t2_display.apply(calculate_global_score, axis=1)
            st.dataframe(t2_display[[c for c in ["Nom du Joueur", "Attaque", "Défense", "Gardien", "Collectif", "Note Globale"] if c in t2_display.columns]], hide_index=True)

# ----------------- ONGLET 2 : BDD JOUEURS -----------------
with tab2:
    st.header("Gestion de la base des joueurs")
    col_add, col_del = st.columns(2)
    with col_add:
        with st.expander("➕ Ajouter un nouveau joueur"):
            with st.form("form_add"):
                name = st.text_input("Nom / Pseudo du joueur")
                att_l = st.selectbox("Attaque (1-10)", options=NUMERIC_OPTIONS, index=4)
                def_l = st.selectbox("Défense (1-10)", options=NUMERIC_OPTIONS, index=4)
                gk_l  = st.selectbox("Gardien (1-10)", options=NUMERIC_OPTIONS, index=4)
                col_l = st.selectbox("Collectif (1-10)", options=NUMERIC_OPTIONS, index=4)
                surnames = st.text_input("Surnoms séparés par des virgules")
                if st.form_submit_button("Ajouter le joueur"):
                    if name.strip() and name.strip() not in st.session_state.players_df["Nom du Joueur"].values:
                        new_p = pd.DataFrame({"Nom du Joueur": [name.strip()], "Attaque": [att_l], "Défense": [def_l], "Gardien": [gk_l], "Collectif": [col_l], "Surnoms": [surnames.strip()]})
                        st.session_state.players_df = pd.concat([st.session_state.players_df, new_p], ignore_index=True)
                        save_data(st.session_state.players_df)
                        st.success(f"✅ {name.strip()} ajouté !")
                        st.rerun()

    with col_del:
        with st.expander("🗑️ Supprimer un joueur de la BDD"):
            all_p = sorted(list(st.session_state.players_df["Nom du Joueur"].values))
            if all_p:
                p_del = st.selectbox("Sélectionner :", options=all_p)
                if st.button("🗑️ Supprimer définitivement"):
                    st.session_state.players_df = st.session_state.players_df[st.session_state.players_df["Nom du Joueur"] != p_del].reset_index(drop=True)
                    save_data(st.session_state.players_df)
                    st.session_state.auto_selected.discard(p_del)
                    st.success(f"✅ {p_del} supprimé !")
                    st.rerun()
                    
    st.write("---")
    st.subheader("📝 Modification et édition directe de l'effectif")
    col_save, col_restore = st.columns([2, 2])
    with col_save: 
        btn_save_top = st.button("💾 Enregistrer les modifications", type="primary", key="save_btn_top")
    with col_restore:
        if os.path.exists(BACKUP_FILE):
            if st.button("⏪ Restaurer le dernier backup"):
                shutil.copyfile(BACKUP_FILE, DATA_FILE)
                st.success("✅ Base restaurée !")
                st.rerun()
    
    df_to_edit = st.session_state.players_df.copy()
    for c in ["Note Globale", "is_joker"]:
        if c in df_to_edit.columns: 
            df_to_edit = df_to_edit.drop(columns=[c])
    for c in ["Attaque", "Défense", "Gardien", "Collectif"]:
        df_to_edit[c] = df_to_edit[c].apply(text_to_score)
        
    edited_players = st.data_editor(
        df_to_edit[["Nom du Joueur", "Attaque", "Défense", "Gardien", "Collectif", "Surnoms"]],
        column_config={
            "Nom du Joueur": st.column_config.TextColumn("Nom du Joueur", required=True),
            "Attaque": st.column_config.SelectboxColumn("Attaque", options=NUMERIC_OPTIONS, required=True),
            "Défense": st.column_config.SelectboxColumn("Défense", options=NUMERIC_OPTIONS, required=True),
            "Gardien": st.column_config.SelectboxColumn("Gardien", options=NUMERIC_OPTIONS, required=True),
            "Collectif": st.column_config.SelectboxColumn("Collectif", options=NUMERIC_OPTIONS, required=True),
            "Surnoms": st.column_config.TextColumn("Surnoms (virgules)"),
        }, hide_index=True, use_container_width=True
    )

    if btn_save_top or st.button("💾 Enregistrer les modifications", type="primary", key="save_btn_bottom"):
        st.session_state.players_df = edited_players
        save_data(edited_players)
        st.success("✅ Fichier Excel sauvegardé avec backup !")
        st.rerun()

# ----------------- ONGLET 3 : BASE JOKERS PROTÉGÉE -----------------
with tab3:
    st.header("Gestion de la Base des Jokers")
    st.caption("Cette base répertorie les joueurs externes récurrents pour faciliter leur sélection le jour du match.")
    
    col_add_j, col_del_j = st.columns(2)
    with col_add_j:
        with st.expander("➕ Ajouter un Joker à la base"):
            with st.form("form_add_joker"):
                j_name = st.text_input("Nom / Prénom du Joker")
                j_att = st.selectbox("Attaque (1-10)", options=NUMERIC_OPTIONS, index=4, key="jadd_att")
                j_def = st.selectbox("Défense (1-10)", options=NUMERIC_OPTIONS, index=4, key="jadd_def")
                j_gk  = st.selectbox("Gardien (1-10)", options=NUMERIC_OPTIONS, index=4, key="jadd_gk")
                j_col = st.selectbox("Collectif (1-10)", options=NUMERIC_OPTIONS, index=4, key="jadd_col")
                j_surnames = st.text_input("Surnoms éventuels", key="jadd_surnames")
                if st.form_submit_button("Ajouter le Joker"):
                    current_names = st.session_state.jokers_df["Nom du Joueur"].values if "Nom du Joueur" in st.session_state.jokers_df.columns else []
                    if j_name.strip() and j_name.strip() not in current_names:
                        new_j = pd.DataFrame({"Nom du Joueur": [j_name.strip()], "Attaque": [j_att], "Défense": [j_def], "Gardien": [j_gk], "Collectif": [j_col], "Surnoms": [j_surnames.strip()]})
                        st.session_state.jokers_df = pd.concat([st.session_state.jokers_df, new_j], ignore_index=True)
                        save_jokers(st.session_state.jokers_df)
                        st.success(f"✅ Joker {j_name.strip()} enregistré !")
                        st.rerun()
    with col_del_j:
        with st.expander("🗑️ Supprimer un Joker"):
            all_j = sorted(list(st.session_state.jokers_df["Nom du Joueur"].values)) if "Nom du Joueur" in st.session_state.jokers_df.columns else []
            if all_j:
                j_to_del = st.selectbox("Sélectionner :", options=all_j, key="jdel_select")
                if st.button("🗑️ Supprimer ce Joker"):
                    st.session_state.jokers_df = st.session_state.jokers_df[st.session_state.jokers_df["Nom du Joueur"] != j_to_del].reset_index(drop=True)
                    save_jokers(st.session_state.jokers_df)
                    st.success(f"✅ Joker {j_to_del} supprimé !")
                    st.rerun()

    st.write("---")
    st.subheader("📝 Édition directe de la table des Jokers")
    col_j_save, col_j_restore = st.columns([2, 2])
    with col_j_save: 
        btn_save_j_top = st.button("💾 Enregistrer la base des Jokers", type="primary", key="save_j_top")
    with col_j_restore:
        if os.path.exists(JOKERS_BACKUP_FILE):
            if st.button("⏪ Restaurer le backup Jokers"):
                shutil.copyfile(JOKERS_BACKUP_FILE, JOKERS_FILE)
                st.success("✅ Base des Jokers restaurée !")
                st.rerun()

    df_j_edit = st.session_state.jokers_df.copy()
    for c in ["Note Globale", "is_joker"]:
        if c in df_j_edit.columns: 
            df_j_edit = df_j_edit.drop(columns=[c])
    for c in ["Attaque", "Défense", "Gardien", "Collectif"]:
        if c in df_j_edit.columns:
            df_j_edit[c] = df_j_edit[c].apply(text_to_score)

    display_cols_j = [c for c in ["Nom du Joueur", "Attaque", "Défense", "Gardien", "Collectif", "Surnoms"] if c in df_j_edit.columns]
    edited_jokers = st.data_editor(
        df_j_edit[display_cols_j],
        column_config={
            "Nom du Joueur": st.column_config.TextColumn("Nom du Joueur", required=True),
            "Attaque": st.column_config.SelectboxColumn("Attaque", options=NUMERIC_OPTIONS, required=True),
            "Défense": st.column_config.SelectboxColumn("Défense", options=NUMERIC_OPTIONS, required=True),
            "Gardien": st.column_config.SelectboxColumn("Gardien", options=NUMERIC_OPTIONS, required=True),
            "Collectif": st.column_config.SelectboxColumn("Collectif", options=NUMERIC_OPTIONS, required=True),
            "Surnoms": st.column_config.TextColumn("Surnoms"),
        }, hide_index=True, use_container_width=True, key="data_editor_jokers"
    )

    st.markdown("##### 📊 Moyennes des Jokers")
    view_j_df = edited_jokers.copy()
    view_j_df["Note Globale"] = view_j_df.apply(calculate_global_score, axis=1)
    st.dataframe(view_j_df[["Nom du Joueur", "Note Globale"]], hide_index=True, use_container_width=True)

    if btn_save_j_top or st.button("💾 Enregistrer la base des Jokers", type="primary", key="save_j_bottom"):
        st.session_state.jokers_df = edited_jokers
        save_jokers(edited_jokers)
        st.success("✅ Base Jokers sauvegardée !")
        st.rerun()

    st.write("---")
    j_buf = io.BytesIO()
    st.session_state.jokers_df.to_excel(j_buf, index=False)
    j_buf.seek(0)
    st.download_button("💾 Télécharger database_jokers.xlsx", data=j_buf, file_name="database_jokers.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
