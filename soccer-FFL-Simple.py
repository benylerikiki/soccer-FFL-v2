import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io

# Configuration de la page Streamlit
st.set_page_config(page_title="Foot 5 - Tactique & Équilibrage", page_icon="⚽", layout="wide")

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


# ==========================================
# ⚙️ CONFIGURATION MODIFIÉE DU TERRAIN
# ==========================================
def draw_tactical_field(team_df, primary_color):
    # Taille globale du terrain réduite (figsize plus petit)
    fig, ax = plt.subplots(figsize=(3.5, 3.8))
    fig.patch.set_alpha(0.0) # Fond transparent
    ax.set_facecolor('#226343') # Pelouse
    
    # Lignes du terrain
    ax.plot([0, 50, 50, 0, 0], [0, 0, 60, 60, 0], color='white', linewidth=2.0)
    penalty_area = patches.Rectangle((0, 15), 12, 30, edgecolor='white', facecolor='none', linewidth=1.5)
    ax.add_patch(penalty_area)
    ax.scatter(9, 30, color='white', s=15, zorder=2)
    center_arc = patches.Arc((50, 30), 18, 18, angle=0, theta1=90, theta2=270, color='white', linewidth=1.5)
    ax.add_patch(center_arc)
    
    # Positions 1-2-2
    positions = [(5, 30), (19, 14), (19, 46), (38, 18), (38, 42)]
    players = team_df.sort_values(by="Poste", ascending=False).reset_index(drop=True)
    
    for i, row in players.iterrows():
        if i >= len(positions): break
        x, y = positions[i]
        
        # Pion plus petit (s=250 au lieu de 550) car il n'y a plus de note textuelle dedans
        ax.scatter(x, y, color=primary_color, s=250, edgecolors='white', linewidths=1.5, zorder=3)
        
        # [NOTE SUPPRIMÉE ICI] -> Plus de texte avec la note au centre du pion
        
        # Noms plus gros (fontsize augmenté à 13) et décalage y ajusté (-4.5)
        ax.text(x, y - 4.5, row['Nom du Joueur'], color='white', fontsize=13, weight='bold', ha='center', va='center',
                bbox=dict(facecolor='#111111', alpha=0.75, edgecolor='none', boxstyle='round,pad=0.25'), zorder=4)
                
    ax.set_xlim(-2, 52)
    ax.set_ylim(-6, 66) # Légèrement élargi pour ne pas couper les grands noms en bord de terrain
    ax.axis('off')
    plt.tight_layout()
    return fig


# ==========================================
# ⚙️ CONFIGURATION DU POP-UP MODAL
# ==========================================
@st.dialog("Compositions du Match ⚽", width="large")
def show_teams_popup(t1, t2):
    st.write("Voici l'équilibrage généré. Prenez votre capture d'écran 📸 !")
    
    pop_col1, pop_col2 = st.columns(2)
    
    with pop_col1:
        st.subheader("🔵 ÉQUIPE 1")
        fig1 = draw_tactical_field(t1, "#1C6CF6")
        # use_container_width=False empêche le terrain de s'étirer et devenir géant
        st.pyplot(fig1, use_container_width=False)
        st.metric("Niveau Moyen", f"{t1['Note (1-10)'].mean():.1f}")
        
    with pop_col2:
        st.subheader("🔴 ÉQUIPE 2")
        fig2 = draw_tactical_field(t2, "#E03131")
        st.pyplot(fig2, use_container_width=False)
        st.metric("Niveau Moyen", f"{t2['Note (1-10)'].mean():.1f}")
        
    if st.button("Fermer"):
        st.rerun()


# --- LOGIQUE INTERFACE ---
st.title("⚽ Foot 5 - Composition & Visualisation Terrain")

tab1, tab2 = st.tabs(["⚖️ Équilibrage du Jour", "🏃 Gestion de la Base"])

# ONGLET 1 : EQUILIBRAGE
with tab1:
    st.header("Sélection des présents")
    pool_df = st.session_state.players_df.copy()
    pool_df.insert(0, "Présent ?", False)
    
    edited_df = st.data_editor(
        pool_df,
        column_config={
            "Présent ?": st.column_config.CheckboxColumn(help="Sélectionnez les 10 joueurs du match"),
            "Note (1-10)": st.column_config.NumberColumn(format="%d"),
        },
        disabled=["Nom du Joueur", "Note (1-10)", "Poste"],
        hide_index=True,
        use_container_width=True
    )
    
    selected_players = edited_df[edited_df["Présent ?"] == True]
    nb_selected = len(selected_players)
    
    if nb_selected == 10:
        st.success("✅ 10 joueurs prêts !")
        
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
