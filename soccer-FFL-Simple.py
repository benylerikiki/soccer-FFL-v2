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
JOKERS_FILE = 'database_jokers.xlsx'
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

# --- INITIALISATION DE L'ÉTAT ---
if 'show_landing' not in st.session_state:
    st.session_state['show_landing'] = True

if 'db_editor_version' not in st.session_state:
    st.session_state['db_editor_version'] = 0

if 'jokers_editor_version' not in st.session_state:
    st.session_state['jokers_editor_version'] = 0

if 'auto_selected' not in st.session_state:
    st.session_state.auto_selected = set()

if 'match_jokers_list' not in st.session_state:
    st.session_state.match_jokers_list = []

NUMERIC_OPTIONS = list(range(1, 11))

def push_file_to_github(file_path: str, content_bytes: bytes, commit_message: str) -> bool:
    """Pousse un fichier binaire (.xlsx) sur GitHub pour persistance."""
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
    avg = (att + defe + gk + col) / 4.0
    return round(avg, 1)

# --- CHARGEMENT / SAUVEGARDE BASE JOUEURS ---
def load_data():
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
    if os.path.exists(DATA_FILE):
        try:
            shutil.copyfile(DATA_FILE, BACKUP_FILE)
        except Exception as e:
            st.warning(f"⚠️️ Impossible de créer le backup : {e}")

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
        st.toast("Base joueurs synchronisée sur GitHub !", icon="☁️")

# --- CHARGEMENT / SAUVEGARDE BASE JOKERS ---
def load_jokers_db():
    if os.path.exists(JOKERS_FILE):
        try:
            df = pd.read_excel(JOKERS_FILE)
            for col in ["Attaque", "Défense", "Gardien", "Collectif", "Note Globale"]:
                if col in df.columns:
                    df[col] = df[col].apply(text_to_score)
            return df
        except Exception:
            pass
            
    return pd.DataFrame(columns=["Nom Joker", "Joueur Rattaché", "Note Globale", "Attaque", "Défense", "Gardien", "Collectif"])

def save_jokers_db(df):
    clean_df = df.copy()
    clean_df.to_excel(JOKERS_FILE, index=False)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        clean_df.to_excel(writer, index=False)
    buffer.seek(0)

    if push_file_to_github(JOKERS_FILE, buffer.getvalue(), "Mise à jour base jokers [via Soccer FFL]"):
        st.toast("Base jokers synchronisée sur GitHub !", icon="☁️")

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
# ⚽ RENDU DU TERRAIN & POPUP
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
            circle_color = "#FFD700" if is_joker else "#1C6CF6"
            ax.scatter(x, y, color=circle_color, s=350, edgecolors='white', linewidths=2.0, zorder=3)
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

def compute_teams(players_list, j1, j2, force_t1_names, force_t2_names):
    """Équilibre les équipes en respectant les affinités T1, T2 et les exclusions."""
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
        st.session_state['show_landing'] = True
        st.rerun()

if st.session_state.get("open_teams_popup", False):
    st.session_state.open_teams_popup = False
    show_teams_popup(st.session_state.last_team1, st.session_state.last_team2)

tab1, tab2 = st.tabs(["⚖️ Équilibrage du Jour", "🏃 Gestion des Bases"])

# ==========================================
# ⚖️ TAB 1 : ÉQUILIBRAGE DU JOUR
# ==========================================
with tab1:
    with st.expander("📋 Analyser une convocation WhatsApp (Optionnel)", expanded=False):
        convoc_text = st.text_area(
            "Colle le texte brut de ta convocation ici :", 
            height=150, 
            placeholder="Présents :\nNico P (1), Cédric (2), Invité mystère (3)..."
        )
        
        if st.button("🔍 Extraire et Valider les Joueurs"):
            if convoc_text.strip():
                match_presents = re.search(r"présents?\b[:\-\s]*(.*)", convoc_text, re.IGNORECASE | re.DOTALL)
                target_text = match_presents.group(1) if match_presents else convoc_text

                stop_pattern = r"\n\s*(jokers?|absents?|infirmerie|en attente|à confirmer|a confirmer)\b"
                target_text = re.split(stop_pattern, target_text, flags=re.IGNORECASE)[0]

                raw_segments = re.split(r"[\n,;]+", target_text)
                cleaned_names = []
                for seg in raw_segments:
                    s = re.sub(r"\(\s*\d+\s*\)", "", seg)
                    s = re.sub(r"^\s*[\d\.\-\*\•\:]+\s*", "", s)
                    s = s.strip()
                    if s:
                        cleaned_names.append(s)

                df_db = st.session_state.players_df
                alias_map = {}
                for _, row in df_db.iterrows():
                    real_name = str(row["Nom du Joueur"]).strip()
                    alias_map.setdefault(real_name.lower(), []).append(real_name)
                    surnoms = [sn.strip().lower() for sn in str(row.get("Surnoms", "")).split(",") if sn.strip()]
                    for sn in surnoms:
                        if real_name not in alias_map.setdefault(sn, []):
                            alias_map[sn].append(real_name)

                found_players = set()
                unknown_names = []
                ambiguous_matches = []

                for candidate in cleaned_names:
                    key = candidate.lower()
                    if key in alias_map:
                        matches = alias_map[key]
                        if len(matches) == 1:
                            found_players.add(matches[0])
                        else:
                            ambiguous_matches.append({
                                "convoc_name": candidate,
                                "candidates": matches
                            })
                    else:
                        unknown_names.append(candidate)

                st.session_state.auto_selected = found_players
                st.session_state.unknown_names = unknown_names
                st.session_state.ambiguous_matches = ambiguous_matches

                if found_players:
                    st.success(f"✅ {len(found_players)} joueur(s) reconnu(s) : {', '.join(found_players)}")
                if unknown_names:
                    st.warning(f"⚠️ {len(unknown_names)} joueur(s) non reconnu(s) : {', '.join(unknown_names)}")
                st.rerun()
            else:
                st.error("Le texte est vide.")

    if 'ambiguous_matches' in st.session_state and st.session_state.ambiguous_matches:
        st.warning("⚠️ **Garde-fou : Surnom partagé par plusieurs joueurs**")
        current_amb = st.session_state.ambiguous_matches[0]
        convoc_n = current_amb.get("convoc_name", current_amb.get("convoc_n"))
        candidates = current_amb["candidates"]
        
        st.markdown(f"Dans la convocation, le nom **'{convoc_n}'** peut correspondre à plusieurs joueurs de la base :")
        selected_candidate = st.radio(
            f"Qui est réellement '{convoc_n}' ?",
            options=candidates,
            key=f"amb_radio_{convoc_n}"
        )
        
        if st.button(f"Confirmé : c'est {selected_candidate}"):
            st.session_state.auto_selected.add(selected_candidate)
            st.session_state.ambiguous_matches.pop(0)
            st.rerun()

    if ('ambiguous_matches' not in st.session_state or not st.session_state.ambiguous_matches) and ('unknown_names' in st.session_state and st.session_state.unknown_names):
        st.info("💡 **Résolution des joueurs inconnus :**")
        db_names = sorted(list(st.session_state.players_df["Nom du Joueur"].values))
        current_unknown = st.session_state.unknown_names[0]
        st.markdown(f"Le nom **'{current_unknown}'** de la convocation n'est pas reconnu.")
        
        choice = st.radio(
            f"Que faire pour '{current_unknown}' ?", 
            ["Associer ce surnom à un joueur existant dans la BDD", "Créer un tout nouveau joueur"], 
            key=f"choice_{current_unknown}"
        )
        
        if choice == "Associer ce surnom à un joueur existant dans la BDD":
            linked_name = st.selectbox("Sélectionner le profil existant :", options=db_names)
            if st.button(f"Associer '{current_unknown}' comme surnom de {linked_name}"):
                idx = st.session_state.players_df[st.session_state.players_df["Nom du Joueur"] == linked_name].index[0]
                existing_surnames = str(st.session_state.players_df.loc[idx, "Surnoms"]).strip()
                updated_surnames = f"{existing_surnames}, {current_unknown}" if existing_surnames else current_unknown
                    
                st.session_state.players_df.loc[idx, "Surnoms"] = updated_surnames
                save_data(st.session_state.players_df)
                st.session_state.db_editor_version += 1
                
                st.session_state.auto_selected.add(linked_name)
                st.session_state.unknown_names.pop(0)
                st.success(f"Surnom '{current_unknown}' enregistré pour {linked_name} !")
                st.rerun()
        else:
            with st.form(f"form_quick_add_{current_unknown}"):
                new_clean_name = st.text_input("Nom officiel pour la BDD", value=current_unknown)
                att_l = st.selectbox("Attaque", options=NUMERIC_OPTIONS, index=4)
                def_l = st.selectbox("Défense", options=NUMERIC_OPTIONS, index=4)
                gk_l  = st.selectbox("Gardien", options=NUMERIC_OPTIONS, index=4)
                col_l = st.selectbox("Collectif", options=NUMERIC_OPTIONS, index=4)
                
                if st.form_submit_button("💾 Enregistrer et Cocher"):
                    if new_clean_name.strip():
                        new_clean = new_clean_name.strip()
                        new_p = pd.DataFrame({
                            "Nom du Joueur": [new_clean], 
                            "Attaque": [att_l], "Défense": [def_l], "Gardien": [gk_l], "Collectif": [col_l],
                            "Surnoms": [current_unknown if new_clean != current_unknown else ""]
                        })
                        st.session_state.players_df = pd.concat([st.session_state.players_df, new_p], ignore_index=True)
                        save_data(st.session_state.players_df)
                        st.session_state.db_editor_version += 1
                        
                        st.session_state.auto_selected.add(new_clean)
                        st.session_state.unknown_names.pop(0)
                        st.rerun()

    st.write("---")
    # --- 1. SÉLECTION DES TITULAIRES ---
    st.subheader("1. Sélection des joueurs réguliers présents")
    
    df_sorted = st.session_state.players_df.sort_values(by="Nom du Joueur").reset_index(drop=True)
    selected_names = []
    
    for i in range(0, len(df_sorted), 3):
        cols = st.columns(3)
        row1 = df_sorted.iloc[i]
        name1 = row1["Nom du Joueur"]
        is_checked1 = name1 in st.session_state.auto_selected
        with cols[0]:
            if st.checkbox(name1, key=f"chk_{name1}_{i}", value=is_checked1): 
                selected_names.append(name1)
                st.session_state.auto_selected.add(name1)
            else:
                st.session_state.auto_selected.discard(name1)
                
        if i + 1 < len(df_sorted):
            row2 = df_sorted.iloc[i + 1]
            name2 = row2["Nom du Joueur"]
            is_checked2 = name2 in st.session_state.auto_selected
            with cols[1]:
                if st.checkbox(name2, key=f"chk_{name2}_{i+1}", value=is_checked2): 
                    selected_names.append(name2)
                    st.session_state.auto_selected.add(name2)
                else:
                    st.session_state.auto_selected.discard(name2)
                    
        if i + 2 < len(df_sorted):
            row3 = df_sorted.iloc[i + 2]
            name3 = row3["Nom du Joueur"]
            is_checked3 = name3 in st.session_state.auto_selected
            with cols[2]:
                if st.checkbox(name3, key=f"chk_{name3}_{i+2}", value=is_checked3): 
                    selected_names.append(name3)
                    st.session_state.auto_selected.add(name3)
                else:
                    st.session_state.auto_selected.discard(name3)
                
    nb_regulars = len(selected_names)
    nb_jokers = len(st.session_state.match_jokers_list)
    total_players_count = nb_regulars + nb_jokers
    
    st.write("---")

    # --- 2. AJOUT DES JOKERS (AVANT LES RESTRICTIONS) ---
    st.subheader(f"2. Jokers / Invités du Jour ({nb_jokers} ajouté{'s' if nb_jokers > 1 else ''})")
    
    if st.session_state.match_jokers_list:
        for idx_jk, jk in enumerate(st.session_state.match_jokers_list):
            c_txt, c_del = st.columns([5, 1])
            with c_txt:
                st.info(f"🃏 **{jk['Nom du Joueur']}** — Notes : Att {jk['Attaque']} | Déf {jk['Défense']} | Gk {jk['Gardien']} | Col {jk['Collectif']}")
            with c_del:
                if st.button("❌", key=f"del_match_jk_{idx_jk}"):
                    st.session_state.match_jokers_list.pop(idx_jk)
                    st.rerun()

    if total_players_count < 10:
        places_needed = 10 - total_players_count
        st.write(f"👉 Il manque encore **{places_needed}** joueur(s) pour compléter le match.")
        
        with st.expander("➕ Ajouter un Joker au match", expanded=True):
            jokers_db = st.session_state.jokers_db
            has_db_jokers = not jokers_db.empty and "Nom Joker" in jokers_db.columns
            
            mode_choice = st.radio(
                "Source du Joker :",
                ["Sélectionner depuis la BDD Jokers", "Saisir un nouveau Joker"] if has_db_jokers else ["Saisir un nouveau Joker"],
                horizontal=True,
                key="jk_add_mode"
            )
            
            if mode_choice == "Sélectionner depuis la BDD Jokers":
                db_joker_names = sorted(jokers_db["Nom Joker"].dropna().unique().tolist())
                current_jk_names = [j["Nom du Joueur"] for j in st.session_state.match_jokers_list]
                available_db_names = [n for n in db_joker_names if f"Joker {n}" not in current_jk_names and n not in current_jk_names]
                
                if available_db_names:
                    chosen_jk_name = st.selectbox("Choisir le Joker :", options=available_db_names, key="sel_jk_pick")
                    jk_data = jokers_db[jokers_db["Nom Joker"] == chosen_jk_name].iloc[0]
                    
                    c_info1, c_info2 = st.columns(2)
                    with c_info1:
                        st.caption(f"Hôte rattaché : **{jk_data.get('Joueur Rattaché', 'Aucun')}**")
                    with c_info2:
                        st.caption(f"Note Globale : **{jk_data.get('Note Globale', 5)}/10**")

                    if st.button("➕ Ajouter ce Joker au match", type="primary", key="btn_add_db_jk"):
                        st.session_state.match_jokers_list.append({
                            "Nom du Joueur": f"Joker {chosen_jk_name}" if not chosen_jk_name.startswith("Joker") else chosen_jk_name,
                            "Attaque": text_to_score(jk_data.get("Attaque", 5)),
                            "Défense": text_to_score(jk_data.get("Défense", 5)),
                            "Gardien": text_to_score(jk_data.get("Gardien", 5)),
                            "Collectif": text_to_score(jk_data.get("Collectif", 5)),
                            "Surnoms": "",
                            "is_joker": True
                        })
                        st.rerun()
                else:
                    st.info("Tous les jokers enregistrés dans la BDD sont déjà sélectionnés.")
            else:
                with st.form("form_add_manual_joker"):
                    c_n, c_s, c_save = st.columns([2, 1, 2])
                    with c_n:
                        new_jk_name = st.text_input("Prénom du Joker", value=f"Joker {nb_jokers + 1}")
                    with c_s:
                        new_jk_score = st.number_input("Note Globale (1-10)", min_value=1, max_value=10, value=5)
                    with c_save:
                        save_to_db_chk = st.checkbox("Enregistrer aussi dans la BDD Jokers", value=True)
                    
                    if st.form_submit_button("➕ Ajouter ce Joker au match", type="primary"):
                        if new_jk_name.strip():
                            clean_jk_name = new_jk_name.strip()
                            final_name = f"Joker {clean_jk_name}" if not clean_jk_name.startswith("Joker") else clean_jk_name
                            num_s = text_to_score(new_jk_score)
                            
                            st.session_state.match_jokers_list.append({
                                "Nom du Joueur": final_name,
                                "Attaque": num_s,
                                "Défense": num_s,
                                "Gardien": num_s,
                                "Collectif": num_s,
                                "Surnoms": "",
                                "is_joker": True
                            })
                            
                            if save_to_db_chk:
                                new_entry = pd.DataFrame([{
                                    "Nom Joker": clean_jk_name,
                                    "Joueur Rattaché": "Aucun",
                                    "Note Globale": num_s,
                                    "Attaque": num_s,
                                    "Défense": num_s,
                                    "Gardien": num_s,
                                    "Collectif": num_s
                                }])
                                st.session_state.jokers_db = pd.concat([st.session_state.jokers_db, new_entry], ignore_index=True)
                                save_jokers_db(st.session_state.jokers_db)
                                st.session_state.jokers_editor_version += 1
                                
                            st.rerun()
    elif total_players_count > 10:
        st.error(f"⚠️ Trop de joueurs au total ({total_players_count}/10). Retirez des Jokers ou décochez des titulaires.")

    regular_players_df = st.session_state.players_df[st.session_state.players_df["Nom du Joueur"].isin(selected_names)].copy()
    regular_players_df['is_joker'] = False
    
    all_match_players_list = regular_players_df.to_dict(orient='records') + st.session_state.match_jokers_list
    all_match_names = [p["Nom du Joueur"] for p in all_match_players_list]

    st.write("---")

    # --- 3. RESTRICTIONS D'AFFINITÉ & OPPOSITION ---
    st.subheader(f"3. Affinités et Oppositions ({len(all_match_names)} / 10 joueurs retenus)")

    if total_players_count == 10:
        st.success("✅ Exactement 10 joueurs retenus. Vous pouvez configurer les équipes.")
    else:
        st.warning(f"Total actuel : {total_players_count}/10. Vous pourrez générer les équipes dès que l'effectif sera de 10.")

    col_force_t1, col_force_t2 = st.columns(2)
    with col_force_t1:
        force_t1 = st.multiselect(
            "🔵 Forcer ensemble dans l'ÉQUIPE 1 (max 5) :",
            options=sorted(all_match_names),
            max_selections=5,
            key="force_t1_all"
        )
    with col_force_t2:
        remaining_for_t2 = [n for n in sorted(all_match_names) if n not in force_t1]
        force_t2 = st.multiselect(
            "🔴 Forcer ensemble dans l'ÉQUIPE 2 (max 5) :",
            options=remaining_for_t2,
            max_selections=5,
            key="force_t2_all"
        )

    st.markdown("##### ⛔ Restriction d'opposition (Optionnel)")
    col_j1, col_j2 = st.columns(2)
    with col_j1:
        j1 = st.selectbox("Sélectionner un joueur...", options=["Aucune restriction"] + sorted(all_match_names), index=0, key="j1_all")
    with col_j2:
        remaining_options = [n for n in all_match_names if n != j1] if j1 != "Aucune restriction" else []
        j2 = st.selectbox("... à ne surtout pas faire jouer avec :", options=["Aucun"] + sorted(remaining_options), index=0, key="j2_all") if j1 != "Aucune restriction" else "Aucun"

    st.write("")

    # --- 4. BOUTON DE GÉNÉRATION DIRECT ---
    if st.button("⚡ Générer l'Équilibrage Parfait", type="primary"):
        if total_players_count != 10:
            st.error(f"Veuillez ajuster pour avoir exactement 10 joueurs au total (actuellement {total_players_count}/10).")
        else:
            valid_combo, best_team1, best_team2 = compute_teams(all_match_players_list, j1, j2, force_t1, force_t2)
            
            if not valid_combo:
                st.error("Impossible de générer les équipes respectant l'ensemble de vos contraintes.")
            else:
                st.session_state.last_team1 = best_team1
                st.session_state.last_team2 = best_team2
                st.session_state.open_teams_popup = True
                st.rerun()

    if 'last_team1' in st.session_state and 'last_team2' in st.session_state:
        st.write("---")
        st.markdown("### 📊 Dernières équipes générées")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**🔵 Équipe 1**")
            t1_display = st.session_state.last_team1.copy()
            t1_display["Note Globale"] = t1_display.apply(calculate_global_score, axis=1)
            display_cols = [c for c in ["Nom du Joueur", "Attaque", "Défense", "Gardien", "Collectif", "Note Globale"] if c in t1_display.columns]
            st.dataframe(t1_display[display_cols], hide_index=True)
            
            t1 = st.session_state.last_team1
            att1 = t1['Attaque'].apply(text_to_score).sum()
            def1 = t1['Défense'].apply(text_to_score).sum()
            gk1  = t1['Gardien'].apply(text_to_score).sum()
            col1 = t1['Collectif'].apply(text_to_score).sum()
            
            st.caption(f"Attaque ({att1}/50)")
            st.progress(att1 / 50)
            st.caption(f"Défense ({def1}/50)")
            st.progress(def1 / 50)
            st.caption(f"Gardien ({gk1}/50)")
            st.progress(gk1 / 50)
            st.caption(f"Collectif ({col1}/50)")
            st.progress(col1 / 50)

        with c2:
            st.markdown("**🔴 Équipe 2**")
            t2_display = st.session_state.last_team2.copy()
            t2_display["Note Globale"] = t2_display.apply(calculate_global_score, axis=1)
            display_cols = [c for c in ["Nom du Joueur", "Attaque", "Défense", "Gardien", "Collectif", "Note Globale"] if c in t2_display.columns]
            st.dataframe(t2_display[display_cols], hide_index=True)
            
            t2 = st.session_state.last_team2
            att2 = t2['Attaque'].apply(text_to_score).sum()
            def2 = t2['Défense'].apply(text_to_score).sum()
            gk2  = t2['Gardien'].apply(text_to_score).sum()
            col2 = t2['Collectif'].apply(text_to_score).sum()
            
            st.caption(f"Attaque ({att2}/50)")
            st.progress(att2 / 50)
            st.caption(f"Défense ({def2}/50)")
            st.progress(def2 / 50)
            st.caption(f"Gardien ({gk2}/50)")
            st.progress(gk2 / 50)
            st.caption(f"Collectif ({col2}/50)")
            st.progress(col2 / 50)

# ==========================================
# 🏃 TAB 2 : GESTION DES BASES (JOUEURS & JOKERS)
# ==========================================
with tab2:
    st.header("Gestion des Bases de Données")
    
    subtab_players, subtab_jokers = st.tabs(["📋 Base Principale Joueurs", "🃏 Base Dédiée Jokers"])
    
    # --- SOUS-ONGLET 1 : JOUEURS ---
    with subtab_players:
        col_add, col_del = st.columns(2)
        
        with col_add:
            with st.expander("➕ Ajouter un nouveau joueur"):
                with st.form("form_add"):
                    name = st.text_input("Nom / Pseudo du joueur")
                    att_label = st.selectbox("Niveau en Attaque (1-10)", options=NUMERIC_OPTIONS, index=4)
                    def_label = st.selectbox("Niveau en Défense (1-10)", options=NUMERIC_OPTIONS, index=4)
                    gk_label  = st.selectbox("Niveau en Gardien (1-10)", options=NUMERIC_OPTIONS, index=4)
                    col_label = st.selectbox("Niveau en Collectif (1-10)", options=NUMERIC_OPTIONS, index=4)
                    surnames = st.text_input("Surnoms séparés par des virgules (Optionnel)", placeholder="ex: Nico, Nick")
                    
                    if st.form_submit_button("Ajouter le joueur"):
                        if name.strip() and name.strip() not in st.session_state.players_df["Nom du Joueur"].values:
                            new_player = pd.DataFrame({
                                "Nom du Joueur": [name.strip()], 
                                "Attaque": [att_label], "Défense": [def_label], "Gardien": [gk_label], "Collectif": [col_label],
                                "Surnoms": [surnames.strip()]
                            })
                            st.session_state.players_df = pd.concat([st.session_state.players_df, new_player], ignore_index=True)
                            save_data(st.session_state.players_df)
                            st.session_state.db_editor_version += 1
                            st.success(f"✅ {name.strip()} ajouté et synchronisé sur GitHub !")
                            st.rerun()
                        else:
                            st.error("Le nom est vide ou existe déjà.")

        with col_del:
            with st.expander("🗑️ Supprimer un joueur de la BDD"):
                all_players = sorted(list(st.session_state.players_df["Nom du Joueur"].values))
                if all_players:
                    player_to_delete = st.selectbox("Sélectionner le joueur à supprimer :", options=all_players)
                    if st.button("🗑️ Supprimer définitivement", type="secondary"):
                        st.session_state.players_df = st.session_state.players_df[st.session_state.players_df["Nom du Joueur"] != player_to_delete].reset_index(drop=True)
                        save_data(st.session_state.players_df)
                        st.session_state.db_editor_version += 1
                        st.session_state.auto_selected.discard(player_to_delete)
                        st.success(f"✅ {player_to_delete} supprimé et synchronisé sur GitHub !")
                        st.rerun()
                else:
                    st.info("Aucun joueur dans la base.")
                        
        st.write("---")
        st.subheader("📝 Modification et édition directe de l'effectif")
        
        col_btn_save, col_btn_restore = st.columns([2, 2])
        with col_btn_save:
            btn_save_top = st.button("💾 Enregistrer les modifications", type="primary", key="save_btn_top")
        with col_btn_restore:
            if os.path.exists(BACKUP_FILE):
                if st.button("⏪ Restaurer le dernier backup", help="Annule la dernière sauvegarde et restaure la base précédente"):
                    shutil.copyfile(BACKUP_FILE, DATA_FILE)
                    st.session_state.players_df = load_data()
                    st.session_state.db_editor_version += 1
                    save_data(st.session_state.players_df)
                    st.success("✅ Base restaurée depuis le backup avec succès !")
                    st.rerun()
        
        df_to_edit = st.session_state.players_df.copy()
        if "Note Globale" in df_to_edit.columns:
            df_to_edit = df_to_edit.drop(columns=["Note Globale"])
        if "is_joker" in df_to_edit.columns:
            df_to_edit = df_to_edit.drop(columns=["is_joker"])

        for col in ["Attaque", "Défense", "Gardien", "Collectif"]:
            if col in df_to_edit.columns:
                df_to_edit[col] = df_to_edit[col].apply(text_to_score)

        column_order = ["Nom du Joueur", "Attaque", "Défense", "Gardien", "Collectif", "Surnoms"]
        df_to_edit = df_to_edit[[c for c in column_order if c in df_to_edit.columns]]

        edited_players = st.data_editor(
            df_to_edit, 
            column_config={
                "Nom du Joueur": st.column_config.TextColumn("Nom du Joueur", required=True),
                "Attaque": st.column_config.SelectboxColumn("Attaque", options=NUMERIC_OPTIONS, required=True),
                "Défense": st.column_config.SelectboxColumn("Défense", options=NUMERIC_OPTIONS, required=True),
                "Gardien": st.column_config.SelectboxColumn("Gardien", options=NUMERIC_OPTIONS, required=True),
                "Collectif": st.column_config.SelectboxColumn("Collectif", options=NUMERIC_OPTIONS, required=True),
                "Surnoms": st.column_config.TextColumn("Surnoms (séparés par des virgules)", help="Ex: Nico, Nick, Ptit Nico"),
            }, 
            hide_index=True, 
            use_container_width=True,
            key=f"editor_players_{st.session_state.db_editor_version}"
        )

        st.markdown("##### 📊 Aperçu des Notes Globales (Moyennes calculées)")
        view_df = edited_players.copy()
        view_df["Note Globale"] = view_df.apply(calculate_global_score, axis=1)
        st.dataframe(view_df[["Nom du Joueur", "Note Globale"]], hide_index=True, use_container_width=True)

        btn_save_bottom = st.button("💾 Enregistrer les modifications", type="primary", key="save_btn_bottom")

        if btn_save_top or btn_save_bottom:
            st.session_state.players_df = edited_players
            save_data(edited_players)
            st.session_state.db_editor_version += 1
            st.success("✅ Fichier Excel sauvegardé et synchronisé sur GitHub !")
            st.rerun()

        st.write("---")

        st.subheader("📥 / 📤 Import & Export de la Base Excel")
        col_dl, col_ul = st.columns(2)
        
        with col_dl:
            st.markdown("**1. Télécharger la BDD actuelle**")
            excel_buffer = io.BytesIO()
            
            export_df = st.session_state.players_df.copy()
            if "Note Globale" in export_df.columns:
                export_df = export_df.drop(columns=["Note Globale"])
            if "is_joker" in export_df.columns:
                export_df = export_df.drop(columns=["is_joker"])
                
            export_df.to_excel(excel_buffer, index=False)
            excel_buffer.seek(0)
            
            st.download_button(
                label="💾 Télécharger database_joueurs_v2.xlsx",
                data=excel_buffer,
                file_name="database_joueurs_v2.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            if os.path.exists(BACKUP_FILE):
                with open(BACKUP_FILE, "rb") as f_b:
                    backup_data = f_b.read()
                st.download_button(
                    label="💾 Télécharger la version Backup (.xlsx)",
                    data=backup_data,
                    file_name="database_joueurs_v2_backup.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
        with col_ul:
            st.markdown("**2. Remplacer avec un fichier Excel modifié**")
            uploaded_file = st.file_uploader("Importer une nouvelle base (.xlsx)", type=["xlsx"], key="up_p")
            if uploaded_file is not None:
                try:
                    new_df = pd.read_excel(uploaded_file)
                    required_cols = ["Nom du Joueur", "Attaque", "Défense", "Gardien", "Collectif"]
                    if all(col in new_df.columns for col in required_cols):
                        if "Surnoms" not in new_df.columns:
                            new_df["Surnoms"] = ""
                        new_df["Surnoms"] = new_df["Surnoms"].fillna("").astype(str)
                        
                        if "Note Globale" in new_df.columns:
                            new_df = new_df.drop(columns=["Note Globale"])
                        if "is_joker" in new_df.columns:
                            new_df = new_df.drop(columns=["is_joker"])
                            
                        for col in ["Attaque", "Défense", "Gardien", "Collectif"]:
                            new_df[col] = new_df[col].apply(text_to_score)
                            
                        save_data(new_df)
                        st.session_state.players_df = new_df
                        st.session_state.db_editor_version += 1
                        st.success("✅ Base mise à jour et envoyée sur GitHub !")
                        st.rerun()
                    else:
                        st.error("Le fichier importé doit contenir au moins les colonnes : Nom du Joueur, Attaque, Défense, Gardien, Collectif")
                except Exception as e:
                    st.error(f"Erreur lors de la lecture du fichier Excel : {e}")

    # --- SOUS-ONGLET 2 : JOKERS ---
    with subtab_jokers:
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
                                "Gardien": new_j_score,
                                "Collectif": new_j_score
                            }])
                            st.session_state.jokers_db = pd.concat([st.session_state.jokers_db, new_j_row], ignore_index=True)
                            save_jokers_db(st.session_state.jokers_db)
                            st.session_state.jokers_editor_version += 1
                            st.session_state.jokers_db = load_jokers_db()
                            st.success(f"Joker '{clean_j_name}' ajouté et synchronisé sur GitHub !")
                            st.rerun()

        with col_del_j:
            with st.expander("❌ Supprimer un Joker de la Base", expanded=False):
                existing_j_names = sorted(st.session_state.jokers_db["Nom Joker"].dropna().unique().tolist()) if not st.session_state.jokers_db.empty else []
                if existing_j_names:
                    j_to_del = st.selectbox("Choisir le joker à supprimer :", options=existing_j_names, key="sel_del_j")
                    if st.button("🗑️ Confirmer la suppression", type="secondary", key="btn_del_j"):
                        st.session_state.jokers_db = st.session_state.jokers_db[st.session_state.jokers_db["Nom Joker"] != j_to_del].reset_index(drop=True)
                        save_jokers_db(st.session_state.jokers_db)
                        st.session_state.jokers_editor_version += 1
                        st.session_state.jokers_db = load_jokers_db()
                        st.success(f"Joker '{j_to_del}' supprimé et synchronisé sur GitHub !")
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
                    st.session_state.jokers_editor_version += 1
                    st.session_state.jokers_db = load_jokers_db()
                    st.success("✅ Base Jokers mise à jour et envoyée sur GitHub !")
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
                "Gardien": st.column_config.SelectboxColumn("Gardien", options=NUMERIC_OPTIONS, default=5),
                "Collectif": st.column_config.SelectboxColumn("Collectif", options=NUMERIC_OPTIONS, default=5),
            },
            hide_index=True,
            use_container_width=True,
            key=f"editor_jokers_{st.session_state.jokers_editor_version}"
        )
        
        if st.button("💾 Enregistrer la base des Jokers", type="primary", key="btn_save_jokers_db"):
            save_jokers_db(edited_jokers_df)
            st.session_state.jokers_editor_version += 1
            st.session_state.jokers_db = load_jokers_db()
            st.success("Base des Jokers sauvegardée et synchronisée sur GitHub !")
            st.rerun()
