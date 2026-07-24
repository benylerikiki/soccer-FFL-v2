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

TEXT_OPTIONS = [f"{i} ⭐" for i in range(1, 11)]

def text_to_score(text_value):
    if pd.isna(text_value):
        return 5
    match = re.search(r'\d+', str(text_value))
    if match:
        val = int(match.group())
        return max(1, min(10, val))
    return 5

def format_star_option(val):
    score = text_to_score(val)
    return f"{score} ⭐"

def calculate_global_score(row):
    att = text_to_score(row.get("Attaque", 5))
    defe = text_to_score(row.get("Défense", 5))
    gk = text_to_score(row.get("Gardien", 5))
    col = text_to_score(row.get("Collectif", 5))
    avg = (att + defe + gk + col) / 4.0
    return f"{avg:.1f} ⭐"

def load_data():
    if os.path.exists(DATA_FILE):
        try: 
            df = pd.read_excel(DATA_FILE)
            if "Surnoms" not in df.columns:
                df["Surnoms"] = ""
            if "Gardien" not in df.columns:
                df["Gardien"] = "5 ⭐"
                
            df["Surnoms"] = df["Surnoms"].fillna("")
            
            for col in ["Attaque", "Défense", "Gardien", "Collectif"]:
                if col in df.columns:
                    df[col] = df[col].apply(format_star_option)
            return df
        except Exception: 
            pass
            
    return pd.DataFrame({
        "Nom du Joueur": ["Antho", "Cyril V", "Apou", "Benoit", "Nico P", "Mouyss", "Cédric", "Nico M", "David", "Cyril L"],
        "Attaque": ["9 ⭐", "5 ⭐", "7 ⭐", "9 ⭐", "5 ⭐", "7 ⭐", "3 ⭐", "7 ⭐", "5 ⭐", "3 ⭐"],
        "Défense": ["5 ⭐", "9 ⭐", "5 ⭐", "3 ⭐", "9 ⭐", "3 ⭐", "9 ⭐", "5 ⭐", "7 ⭐", "7 ⭐"],
        "Gardien": ["3 ⭐", "5 ⭐", "7 ⭐", "3 ⭐", "7 ⭐", "5 ⭐", "9 ⭐", "3 ⭐", "5 ⭐", "5 ⭐"],
        "Collectif": ["7 ⭐", "9 ⭐", "7 ⭐", "5 ⭐", "7 ⭐", "5 ⭐", "7 ⭐", "5 ⭐", "5 ⭐", "5 ⭐"],
        "Surnoms": ["", "Cyril", "", "beny", "nicop, nico", "mouys", "", "nicom, nico", "Dav, dimeh", "Cyril"]
    })

def save_data(df):
    clean_df = df.copy()
    if "Note Globale" in clean_df.columns:
        clean_df = clean_df.drop(columns=["Note Globale"])
    if "is_joker" in clean_df.columns:
        clean_df = clean_df.drop(columns=["is_joker"])
        
    for col in ["Attaque", "Défense", "Gardien", "Collectif"]:
        if col in clean_df.columns:
            clean_df[col] = clean_df[col].apply(format_star_option)
            
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
# ⚽ FUNCTIONS DU TERRAIN & DIALOGS
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
    
    # Équipe 1 (Bleu / Jaune si Joker)
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
        
    # Équipe 2 (Rouge / Jaune si Joker)
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

@st.dialog("🃏 Saisie des Joueurs Jokers", width="medium")
def add_jokers_dialog():
    nb_missing = st.session_state.jokers_info['nb_missing']
    selected_players_df = st.session_state.jokers_info['selected_players'].copy()
    selected_players_df['is_joker'] = False  # Forcer explicitement à False pour la BDD
    
    j1 = st.session_state.jokers_info['j1']
    j2 = st.session_state.jokers_info['j2']

    st.write(f"Il manque **{nb_missing}** joueur(s) pour atteindre 10. Renseignez leurs prénoms et notes :")
    
    jokers_input = []
    with st.form("form_jokers"):
        for k in range(nb_missing):
            st.markdown(f"**Joker {k+1}**")
            col_j_name, col_j_score = st.columns([2, 1])
            with col_j_name:
                j_name = st.text_input(f"Prénom du Joker {k+1}", value=f"Joker {k+1}", key=f"j_name_{k}")
            with col_j_score:
                j_score = st.number_input(f"Note (1 à 10)", min_value=1, max_value=10, value=5, key=f"j_score_{k}")
            jokers_input.append((j_name.strip(), j_score))
        
        submit_jokers = st.form_submit_button("⚡ Valider et Générer avec les Jokers", type="primary")
        
    if submit_jokers:
        jokers_rows = []
        for j_name, j_score in jokers_input:
            formatted_star = f"{j_score} ⭐"
            jokers_rows.append({
                "Nom du Joueur": f"Joker {j_name}" if not j_name.startswith("Joker") else j_name,
                "Attaque": formatted_star,
                "Défense": formatted_star,
                "Gardien": formatted_star,
                "Collectif": formatted_star,
                "Surnoms": "",
                "is_joker": True  # Seuls ces joueurs sont marqués comme Joker
            })
            
        full_group_df = pd.concat([selected_players_df, pd.DataFrame(jokers_rows)], ignore_index=True)
        
        players_list = full_group_df.to_dict(orient='records')
        best_diff = float('inf')
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
                                })
                        else:
                            unknown_names.append(raw_name)
                    
                    st.session_state.auto_selected = found_players
                    st.session_state.unknown_names = unknown_names
                    st.session_state.ambiguous_matches = ambiguous_matches
                    
                    if not unknown_names and not ambiguous_matches:
                        st.success(f"✅ {len(found_players)} joueurs reconnus et cochés sans ambiguïté !")
                        st.rerun()
                else:
                    st.error("Le mot 'Présents :' n'a pas été trouvé dans le texte.")
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
                
                st.session_state.auto_selected.add(linked_name)
                st.session_state.unknown_names.pop(0)
                st.success(f"Surnom '{current_unknown}' enregistré pour {linked_name} !")
                st.rerun()
        else:
            with st.form(f"form_quick_add_{current_unknown}"):
                new_clean_name = st.text_input("Nom officiel pour la BDD", value=current_unknown)
                att_l = st.selectbox("Attaque", options=TEXT_OPTIONS, index=4)
                def_l = st.selectbox("Défense", options=TEXT_OPTIONS, index=4)
                gk_l  = st.selectbox("Gardien", options=TEXT_OPTIONS, index=4)
                col_l = st.selectbox("Collectif", options=TEXT_OPTIONS, index=4)
                
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
                        
                        st.session_state.auto_selected.add(new_clean)
                        st.session_state.unknown_names.pop(0)
                        st.rerun()

    st.write("---")
    st.subheader("Sélection des présents")
    
    df_sorted = st.session_state.players_df.sort_values(by="Nom du Joueur").reset_index(drop=True)
    counter_placeholder = st.empty()
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
                
    selected_players = st.session_state.players_df[st.session_state.players_df["Nom du Joueur"].isin(selected_names)].copy()
    nb_selected = len(selected_players)
    
    if nb_selected == 10:
        counter_placeholder.success("✅ 10 joueurs sélectionnés ! Prêts à configurer les options.")
    elif nb_selected > 10:
        counter_placeholder.error(f"⚠️ Trop de joueurs sélectionnés ({nb_selected}/10). Veuillez en décocher {nb_selected - 10} !")
    else:
        counter_placeholder.info(f"🏃 Joueurs sélectionnés : {nb_selected} / 10 (Si < 10, des Jokers vous seront proposés)")
        
    st.write("---")
    
    if nb_selected <= 10 and nb_selected > 0:
        st.markdown("### ⛔ Restriction d'affinité (Optionnel)")
        j1 = st.selectbox("Sélectionner un joueur...", options=["Aucune restriction"] + sorted(selected_names), index=0)
        remaining_options = [n for n in selected_names if n != j1] if j1 != "Aucune restriction" else []
        j2 = st.selectbox("... à ne surtout pas faire jouer avec :", options=["Aucun"] + sorted(remaining_options), index=0) if j1 != "Aucune restriction" else "Aucun"
        st.write("")
        
        if st.button("⚡ Générer l'Équilibrage Parfait", type="primary"):
            if nb_selected < 10:
                st.session_state.jokers_info = {
                    'nb_missing': 10 - nb_selected,
                    'selected_players': selected_players,
                    'j1': j1,
                    'j2': j2
                }
                st.session_state.show_jokers_modal = True
                st.rerun()
            else:
                selected_players['is_joker'] = False
                players_list = selected_players.to_dict(orient='records')
                best_diff = float('inf')
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
                
                if not valid_combo_found:
                    st.error("Impossible de générer les équipes avec cette contrainte.")
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

with tab2:
    st.header("Gestion de la base des joueurs")
    
    col_add, col_del = st.columns(2)
    
    with col_add:
        with st.expander("➕ Ajouter un nouveau joueur"):
            with st.form("form_add"):
                name = st.text_input("Nom / Pseudo du joueur")
                att_label = st.selectbox("Niveau en Attaque", options=TEXT_OPTIONS, index=4)
                def_label = st.selectbox("Niveau en Défense", options=TEXT_OPTIONS, index=4)
                gk_label  = st.selectbox("Niveau en Gardien", options=TEXT_OPTIONS, index=4)
                col_label = st.selectbox("Niveau en Collectif", options=TEXT_OPTIONS, index=4)
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
                        st.success(f"✅ {name.strip()} ajouté dans la base Excel !")
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
                    st.session_state.auto_selected.discard(player_to_delete)
                    st.success(f"✅ {player_to_delete} a été supprimé de la base Excel !")
                    st.rerun()
            else:
                st.info("Aucun joueur dans la base.")
                    
    st.write("---")
    st.subheader("📝 Modification et édition directe de l'effectif")
    
    btn_save_top = st.button("💾 Enregistrer les modifications", type="primary", key="save_btn_top")
    
    df_to_edit = st.session_state.players_df.copy()
    if "Note Globale" in df_to_edit.columns:
        df_to_edit = df_to_edit.drop(columns=["Note Globale"])
    if "is_joker" in df_to_edit.columns:
        df_to_edit = df_to_edit.drop(columns=["is_joker"])

    for col in ["Attaque", "Défense", "Gardien", "Collectif"]:
        if col in df_to_edit.columns:
            df_to_edit[col] = df_to_edit[col].apply(format_star_option)

    column_order = ["Nom du Joueur", "Attaque", "Défense", "Gardien", "Collectif", "Surnoms"]
    df_to_edit = df_to_edit[[c for c in column_order if c in df_to_edit.columns]]

    edited_players = st.data_editor(
        df_to_edit, 
        column_config={
            "Nom du Joueur": st.column_config.TextColumn("Nom du Joueur", required=True),
            "Attaque": st.column_config.SelectboxColumn("Attaque", options=TEXT_OPTIONS, required=True),
            "Défense": st.column_config.SelectboxColumn("Défense", options=TEXT_OPTIONS, required=True),
            "Gardien": st.column_config.SelectboxColumn("Gardien", options=TEXT_OPTIONS, required=True),
            "Collectif": st.column_config.SelectboxColumn("Collectif", options=TEXT_OPTIONS, required=True),
            "Surnoms": st.column_config.TextColumn("Surnoms (séparés par des virgules)", help="Ex: Nico, Nick, Ptit Nico"),
        }, 
        hide_index=True, 
        use_container_width=True
    )

    st.markdown("##### 📊 Aperçu des Notes Globales (Moyennes calculées)")
    view_df = edited_players.copy()
    view_df["Note Globale"] = view_df.apply(calculate_global_score, axis=1)
    st.dataframe(view_df[["Nom du Joueur", "Note Globale"]], hide_index=True, use_container_width=True)

    btn_save_bottom = st.button("💾 Enregistrer les modifications", type="primary", key="save_btn_bottom")

    if btn_save_top or btn_save_bottom:
        st.session_state.players_df = edited_players
        save_data(edited_players)
        st.success("✅ Fichier Excel sauvegardé avec succès !")
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
        
    with col_ul:
        st.markdown("**2. Remplacer avec un fichier Excel modifié**")
        uploaded_file = st.file_uploader("Importer une nouvelle base (.xlsx)", type=["xlsx"])
        if uploaded_file is not None:
            try:
                new_df = pd.read_excel(uploaded_file)
                required_cols = ["Nom du Joueur", "Attaque", "Défense", "Gardien", "Collectif"]
                if all(col in new_df.columns for col in required_cols):
                    if "Surnoms" not in new_df.columns:
                        new_df["Surnoms"] = ""
                    new_df["Surnoms"] = new_df["Surnoms"].fillna("")
                    
                    if "Note Globale" in new_df.columns:
                        new_df = new_df.drop(columns=["Note Globale"])
                    if "is_joker" in new_df.columns:
                        new_df = new_df.drop(columns=["is_joker"])
                        
                    for col in ["Attaque", "Défense", "Gardien", "Collectif"]:
                        new_df[col] = new_df[col].apply(format_star_option)
                        
                    st.session_state.players_df = new_df
                    save_data(new_df)
                    st.success("✅ Base de données mise à jour avec succès depuis le fichier téléversé !")
                    st.rerun()
                else:
                    st.error("Le fichier importé doit contenir au moins les colonnes : Nom du Joueur, Attaque, Défense, Gardien, Collectif")
            except Exception as e:
                st.error(f"Erreur lors de la lecture du fichier Excel : {e}")
