import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io  # <-- Nécessaire pour la gestion du téléchargement Excel

# Configuration de la page Streamlit
st.set_page_config(page_title="Foot 5 - Tactique & Équilibrage", page_icon="⚽", layout="wide")

EXCEL_FILE = 'Gestion_Equipes_Foot5 - Copie.xlsx'

# --- CHARGEMENT DES DONNÉES INITIALES ---
def load_data():
    if os.path.exists(EXCEL_FILE):
        try:
            df = pd.read_excel(EXCEL_FILE, sheet_name='Liste des Joueurs', skiprows=3)
            df = df.dropna(subset=["Nom du Joueur"])
            df = df[["Nom du Joueur", "Note (1-10)", "Poste"]]
            return df.reset_index(drop=True)
        except Exception:
            pass
            
    return pd.DataFrame({
        "Nom du Joueur": ["Antho", "Cyril V", "Apou", "Benoit", "Nico P", "Mouyss", "Cédric", "Nico M", "David", "Cyril L"],
        "Note (1-10)": [9, 9, 6, 6, 6, 5, 5, 4, 4, 3],
        "Poste": ["Attaque", "Défense", "Attaque", "Attaque", "Défense", "Attaque", "Défense", "Attaque", "Défense", "Défense"]
    })

if 'players_df' not in st.session_state:
    st.session_state.players_df = load_data()

# --- FONCTION POUR DESSINER LE DEMI-TERRAIN ---
def draw_tactical_field(team_df, team_title, primary_color):
    fig, ax = plt.subplots(figsize=(5, 5.5))
    fig.patch.set_alpha(0.0) # Fond transparent
    ax.set_facecolor('#226343') # Pelouse
    
    # Lignes du terrain
    ax.plot([0, 50, 50, 0, 0], [0, 0, 60, 60, 0], color='white', linewidth=2.5)
    penalty_area = patches.Rectangle((0, 15), 12, 30, edgecolor='white', facecolor='none', linewidth=2)
    ax.add_patch(penalty_area)
    ax.scatter(9, 30, color='white', s=25, zorder=2)
    center_arc = patches.Arc((50, 30), 18, 18, angle=0, theta1=90, theta2=270, color='white', linewidth=2)
    ax.add_patch(center_arc)
    
    # Positions 1-2-2
    positions = [(5, 30), (19, 14), (19, 46), (38, 18), (38, 42)]
    players = team_df.sort_values(by="Poste", ascending=False).reset_index(drop=True)
    
    for i, row in players.iterrows():
        if i >= len(positions): break
        x, y = positions[i]
        ax.scatter(x, y, color=primary_color, s=550, edgecolors='white', linewidths=2, zorder=3)
        ax.text(x, y, str(int(row['Note (1-10)'])), color='white', fontsize=9, weight='bold', ha='center', va='center', zorder=4)
        ax.text(x, y - 3.8, row['Nom du Joueur'], color='white', fontsize=10, weight='bold', ha='center', va='center',
                bbox=dict(facecolor='#111111', alpha=0.75, edgecolor='none', boxstyle='round,pad=0.25'), zorder=4)

    ax.set_xlim(-2, 52)
    ax.set_ylim(-2, 62)
    ax.axis('off')
    plt.tight_layout()
    return fig

# --- LOGIQUE DE L'APPLICATION ---
st.title("⚽ Foot 5 - Composition & Visualisation Terrain")

tab1, tab2 = st.tabs(["⚖️ Équilibrage du Jour", "🏃 Gestion de la Base"])

# ==========================================
# ONGLET 1 : ÉQUILIBRAGE & TERRAINS
# ==========================================
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
            
            st.write("---")
            col_field1, col_field2 = st.columns(2)
            
            with col_field1:
                st.subheader("🔵 ÉQUIPE 1")
                fig1 = draw_tactical_field(team1, "Équipe 1", "#1C6CF6")
                st.pyplot(fig1)
                avg_1 = team1["Note (1-10)"].mean()
                st.metric("Niveau Moyen", f"{avg_1:.1f}")
                st.dataframe(team1[["Nom du Joueur", "Note (1-10)", "Poste"]], hide_index=True, use_container_width=True)
                
            with col_field2:
                st.subheader("🔴 ÉQUIPE 2")
                fig2 = draw_tactical_field(team2, "Équipe 2", "#E03131")
                st.pyplot(fig2)
                avg_2 = team2["Note (1-10)"].mean()
                st.metric("Niveau Moyen", f"{avg_2:.1f}")
                st.dataframe(team2[["Nom du Joueur", "Note (1-10)", "Poste"]], hide_index=True, use_container_width=True)
    else:
        st.info(f"🏃 Sélectionnez exactement 10 joueurs (Actuel : {nb_selected}/10)")


# ==========================================
# ONGLET 2 : GESTION, IMPORT & EXPORT
# ==========================================
with tab2:
    st.header("Gestion de la base des joueurs")
    
    # --- SECTION IMPORT / EXPORT (NOUVEAU) ---
    st.subheader("📥 Sauvegarde & Mise à jour externe")
    col_dl, col_ul = st.columns(2)
    
    with col_dl:
        st.write("1. Téléchargez la base actuelle pour la modifier sur votre ordinateur (Excel) :")
        # Conversion du DataFrame en fichier Excel virtuel (en mémoire)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            st.session_state.players_df.to_excel(writer, index=False, sheet_name='Liste des Joueurs')
        buffer.seek(0)
        
        st.download_button(
            label="📥 Télécharger l'effectif (.xlsx)",
            data=buffer,
            file_name="Effectif_Foot5.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    with col_ul:
        st.write("2. Réuploadez votre fichier Excel une fois modifié :")
        uploaded_file = st.file_uploader("Choisir un fichier Excel (.xlsx)", type=["xlsx"])
        
        if uploaded_file is not None:
            try:
                # Lecture du fichier mis à jour par l'utilisateur
                uploaded_df = pd.read_excel(uploaded_file)
                
                # Vérification des colonnes pour éviter les crashs
                required_cols = ["Nom du Joueur", "Note (1-10)", "Poste"]
                if all(col in uploaded_df.columns for col in required_cols):
                    # Nettoyage et application à l'application
                    cleaned_df = uploaded_df[required_cols].dropna(subset=["Nom du Joueur"])
                    st.session_state.players_df = cleaned_df.reset_index(drop=True)
                    st.success("✅ Base de données mise à jour avec succès depuis le fichier !")
                    st.rerun() # Recharge l'application pour appliquer les changements partout
                else:
                    st.error(f"Erreur : Le fichier doit obligatoirement contenir les colonnes : {', '.join(required_cols)}")
            except Exception as e:
                st.error(f"Une erreur est survenue lors de la lecture : {e}")

    st.write("---")
    
    # Formulaire d'ajout manuel rapide
    with st.expander("➕ Ajouter manuellement un joueur"):
        with st.form("form_add"):
            name = st.text_input("Nom de famille / Pseudo")
            note = st.slider("Note globale (1 à 10)", 1, 10, 5)
            poste = st.radio("Poste préférentiel", ["Attaque", "Défense"], horizontal=True)
            
            if st.form_submit_button("Ajouter à l'effectif"):
                if not name.strip():
                    st.error("Veuillez saisir un nom valide.")
                elif name.strip() in st.session_state.players_df["Nom du Joueur"].values:
                    st.error("Ce joueur existe déjà.")
                else:
                    new_player = pd.DataFrame({"Nom du Joueur": [name.strip()], "Note (1-10)": [note], "Poste": [poste]})
                    st.session_state.players_df = pd.concat([st.session_state.players_df, new_player], ignore_index=True)
                    st.success(f"⚽ {name.strip()} ajouté !")
                    st.rerun()
                    
    # Éditeur de tableau en direct
    st.subheader("Modification rapide sur l'application")
    edited_players = st.data_editor(
        st.session_state.players_df,
        column_config={
            "Note (1-10)": st.column_config.NumberColumn(min_value=1, max_value=10, step=1),
            "Poste": st.column_config.SelectboxColumn(options=["Attaque", "Défense"])
        },
        hide_index=True,
        use_container_width=True
    )
    st.session_state.players_df = edited_players
