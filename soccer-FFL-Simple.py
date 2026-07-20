import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io

# Configuration de la page Streamlit
st.set_page_config(page_title="Soccer FFL Kompo", page_icon="⚽", layout="wide")

# 📳 STYLE CSS : Force l'affichage sur 2 colonnes sur mobile portrait (uniquement pour les cases à cocher)
st.markdown(
    """
    <style>
    @media (max-width: 768px) {
        div[data-testid="stHorizontalBlock"]:has(div[data-testid="stCheckbox"]) {
            flex-direction: row !important;
            gap: 10px !important;
        }
        div[data-testid="stHorizontalBlock"]:has(div[data-testid="stCheckbox"]) div[data-testid="column"] {
            width: 50% !important;
            flex: 1 1 50% !important;
            min-width: 0 !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- FICHIERS DE STOCKAGE ---
DATA_FILE = 'database_joueurs.xlsx'       
EXCEL_FILE = 'Gestion_Equipes_Foot5 - Copie.xlsx' 

# --- FONCTION DE CHARGEMENT ---
def load_data():
    if os.path.exists(DATA_FILE):
        try: return pd.read_excel(DATA_FILE)
        except Exception: pass
    if os.path.exists(EXCEL_FILE):
        try:
            df = pd.read_excel(EXCEL_FILE, sheet_name='Liste des Joueurs', skiprows=3)
            df = df.dropna(subset=["Nom du Joueur"])
            return df[["Nom du Joueur", "Note (1-10)", "Poste"]].reset_index(drop=True)
        except Exception: pass
    return pd.DataFrame({
        "Nom du Joueur": ["Antho", "Cyril V", "Apou", "Benoit", "Nico P", "Mouyss", "Cédric", "Nico M", "David", "Cyril L"],
        "Note (1-10)": [9, 9, 6, 6, 6, 5, 5, 4, 4, 3],
        "Poste": ["Attaque", "Défense", "Attaque", "Attaque", "Défense", "Attaque", "Défense", "Attaque", "Défense", "Défense"]
    })

def save_data(df):
    df.to_excel(DATA_FILE, index=False)

if 'players_df' not in st.session_state:
    st.session_state.players_df = load_data()


# --- CONFIGURATION DU TERRAIN UNIQUE ET UNIFIÉ (FACES À FACES) ---
def draw_combined_field(t1, t2):
    fig, ax = plt.subplots(figsize=(8, 5.2))
    fig.patch.set_facecolor('#226343')
    ax.set_facecolor('#226343')
    
    ax.plot([0, 100, 100, 0, 0], [0, 0, 60, 60, 0], color='white', linewidth=2.0)
    ax.plot([50, 50], [0, 60], color='white', linewidth=2.0)
    center_circle = patches.Circle((50, 30), 9, edgecolor='white', facecolor='none', linewidth=1.5)
    ax.add_patch(center_circle)
    ax.scatter(50, 30, color='white', s=15, zorder=2)
    
    penalty_left = patches.Rectangle((0, 15), 12, 30, edgecolor='white', facecolor='none', linewidth=1.5)
    ax.add_patch(penalty_left)
    ax.scatter(9, 30, color='white', s=15, zorder=2)
    
    penalty_right = patches.Rectangle((88, 15), 12, 30, edgecolor='white', facecolor='none', linewidth=1.5)
    ax.add_patch(penalty_right)
    ax.scatter(91, 30, color='white', s=15, zorder=2)
    
    pos1 = [(5, 30), (19, 14), (19, 46), (38, 18), (38, 42)]
    players1 = t1.sort_values(by="Poste", ascending=False).reset_index(drop=True)
    for i, row in players1.iterrows():
        if i >= len(pos1): break
        x, y = pos1[i]
        ax.scatter(x, y, color="#1C6CF6", s=220, edgecolors='white', linewidths=1.5, zorder=3)
        ax.text(x, y - 4.2, row['Nom du Joueur'], color='white', fontsize=12, weight='bold', ha='center', va='center', zorder=4)
        
    pos2 = [(95, 30), (81, 14), (81, 46), (62, 18), (62, 42)]
    players2 = t2.sort_values(by="Poste", ascending=False).reset_index(drop=True)
    for i, row in players2.iterrows():
        if i >= len(pos2): break
        x, y = pos2[i]
        ax.scatter(x, y, color="#E03131", s=220, edgecolors='white', linewidths=1.5, zorder=3)
        ax.text(x, y - 4.2, row['Nom du Joueur'], color='white', fontsize=12, weight='bold', ha='center', va='center', zorder=4)
    
    ax.text(25, 64, "EQUIPE 1", color='#1C6CF6', fontsize=15, weight='bold', ha='center', va='center')
    ax.text(75, 64, "EQUIPE 2", color='#E03131', fontsize=15, weight='bold', ha='center', va='center')
    
    ax.set_xlim(-4, 104)
    ax.set_ylim(-6, 68)
    ax.axis('off')
    plt.tight_layout()
    return fig


# --- CONFIGURATION DU POP-UP MODAL ---
@st.dialog("Compositions du Match ⚽", width="large")
def show_teams_popup(t1, t2):
    st.write("Voici la composition sous forme de match. Cliquez sur le bouton ci-dessous pour enregistrer l'image ! 📸")
    
    fig_combined = draw_combined_field(t1, t2)
    st.pyplot(fig_combined, use_container_width=True)
    
    buf = io.BytesIO()
    fig_combined.savefig(buf, format="png", bbox_inches='tight', dpi=250, facecolor='#226343')
    buf.seek(0)
    
    st.download_button(
        label="📸 Télécharger l'image des compositions (PNG)",
        data=buf,
        file_name="Compositions_FFL.png",
        mime="image/png",
        type="primary" 
    )
    
    st.write("---")
    
    text_whatsapp = "⚽ *COMPOSITIONS DU MATCH* ⚽\n\n"
    text_whatsapp += "🔵 *ÉQUIPE 1* :\n"
    for _, row in t1.iterrows():
        text_whatsapp += f"• {row['Nom du Joueur']}\n"
        
    text_whatsapp += "\n🔴 *ÉQUIPE 2* :\n"
    for _, row in t2.iterrows():
        text_whatsapp += f"• {row['Nom du Joueur']}\n"
        
    st.markdown("**📋 Copier le texte brut pour votre groupe :**")
    st.caption("💡 Survolez le bloc de texte ci-dessous et cliquez sur la petite icône en haut à droite pour tout copier d'un coup.")
    
    st.code(text_whatsapp, language="text")
        
    if st.button("Fermer"):
        st.rerun()


# --- LOGIQUE INTERFACE ---
st.header("⚽ Soccer FFL Kompo")

tab1, tab2 = st.tabs(["⚖️ Équilibrage du Jour", "🏃 Gestion de la Base"])

# ONGLET 1 : EQUILIBRAGE
with tab1:
    st.subheader("Sélection des présents")
    st.write("Cochez les 10 joueurs du jour (triés par ordre alphabétique) :")
    
    df_sorted = st.session_state.players_df.sort_values(by="Nom du Joueur").reset_index(drop=True)
    selected_names = []
    
    # Affichage épuré strict 2 par 2 par ligne (Bloqué sur 2 colonnes grâce au CSS)
    for i in range(0, len(df_sorted), 2):
        cols = st.columns(2)
        
        # Premier joueur (gauche)
        row1 = df_sorted.iloc[i]
        name1 = row1["Nom du Joueur"]
        with cols[0]:
            if st.checkbox(name1, key=f"select_{name1}"):
                selected_names.append(name1)
                
        # Deuxième joueur (droite)
        if i + 1 < len(df_sorted):
            row2 = df_sorted.iloc[i + 1]
            name2 = row2["Nom du Joueur"]
            with cols[1]:
                if st.checkbox(name2, key=f"select_{name2}"):
                    selected_names.append(name2)
                
    selected_players = st.session_state.players_df[st.session_state.players_df["Nom du Joueur"].isin(selected_names)]
    nb_selected = len(selected_players)
    
    st.write("---")
    
    if nb_selected == 10:
        st.success("✅ 10 joueurs sélectionnés ! Prêts à générer.")
        
        if st.button("⚡ Générer les Compositions Tactiques", type="primary"):
            selected_players = selected_players.copy()
            selected_players["Score Tri"] = selected_players["Note (1-10)"] + selected_players["Poste"].apply(lambda x: 0.1 if x == "Attaque" else 0.0)
            sorted_players = selected_players.sort_values(by="Score Tri", ascending=False).reset_index(drop=True)
            
            idx_team1 = [0, 3, 4, 7, 8]
            idx_team2 = [1, 2, 5, 6, 9]
            
            team1 = sorted_players.iloc[idx_team1].copy()
            team2 = sorted_players.iloc[idx_team2].copy()
            
            st.session_state.last_team1 = team1
            st.session_state.last_team2 = team2
            
            show_teams_popup(team1, team2)
            
    elif nb_selected > 10:
        st.error(f"⚠️ Trop de joueurs sélectionnés ({nb_selected}/10). Veuillez en décocher {nb_selected - 10} !")
    else:
        st.info(f"🏃 Sélectionnez exactement 10 joueurs (Actuel : {nb_selected}/10)")

    if 'last_team1' in st.session_state and 'last_team2' in st.session_state:
        st.write("---")
        st.markdown("### 📊 Dernières équipes générées")
        c1, c2 = st.columns(2)
        with c1:
            st.dataframe(st.session_state.last_team1[["Nom du Joueur", "Note (1-10)", "Poste"]], hide_index=True)
        with c2:
            st.dataframe(st.session_state.last_team2[["Nom du Joueur", "Note (1-10)", "Poste"]], hide_index=True)


# ONGLET 2 : GESTION DES JOUEURS
with tab2:
    st.header("Gestion de la base des joueurs")
    
    st.subheader("📥 Sauvegarde & Mise à jour externe")
    col_dl, col_ul = st.columns(2)
    with col_dl:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            st.session_state.players_df.to_excel(writer, index=False, sheet_name='Liste des Joueurs')
        buffer.seek(0)
        st.download_button(label="📥 Télécharger l'effectif (.xlsx)", data=buffer, file_name="Effectif_Foot5.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
    with col_ul:
        uploaded_file = st.file_uploader("Choisir un fichier Excel (.xlsx)", type=["xlsx"])
        if uploaded_file is not None:
            try:
                uploaded_df = pd.read_excel(uploaded_file)
                required_cols = ["Nom du Joueur", "Note (1-10)", "Poste"]
                if all(col in uploaded_df.columns for col in required_cols):
                    st.session_state.players_df = uploaded_df[required_cols].dropna(subset=["Nom du Joueur"]).reset_index(drop=True)
                    save_data(st.session_state.players_df)
                    st.success("✅ Mis à jour !")
                    st.rerun()
            except Exception as e: st.error(f"Erreur : {e}")

    st.write("---")
    with st.expander("➕ Ajouter manuellement un joueur"):
        with st.form("form_add"):
            name = st.text_input("Nom / Pseudo")
            note = st.slider("Note (1 à 10)", 1, 10, 5)
            poste = st.radio("Poste", ["Attaque", "Défense"], horizontal=True)
            if st.form_submit_button("Ajouter"):
                if name.strip() and name.strip() not in st.session_state.players_df["Nom du Joueur"].values:
                    new_player = pd.DataFrame({"Nom du Joueur": [name.strip()], "Note (1-10)": [note], "Poste": [poste]})
                    st.session_state.players_df = pd.concat([st.session_state.players_df, new_player], ignore_index=True)
                    save_data(st.session_state.players_df)
                    st.rerun()
                    
    st.subheader("Modification rapide sur l'application")
    edited_players = st.data_editor(st.session_state.players_df, column_config={"Note (1-10)": st.column_config.NumberColumn(min_value=1, max_value=10), "Poste": st.column_config.SelectboxColumn(options=["Attaque", "Défense"])}, hide_index=True, use_container_width=True)
    if st.button("💾 Enregistrer les modifications du tableau", type="primary"):
        st.session_state.players_df = edited_players
        save_data(edited_players)
        st.success("✅ Enregistré !")
        st.rerun()
