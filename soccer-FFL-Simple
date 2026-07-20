import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Configuration de la page Streamlit
st.set_page_config(page_title="Foot 5 - Tactique & Équilibrage", page_icon="⚽", layout="wide")

EXCEL_FILE = 'Gestion_Equipes_Foot5 - Copie.xlsx'

# --- CHARGEMENT DES DONNÉES ---
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
    # Création de la figure graphique
    fig, ax = plt.subplots(figsize=(5, 5.5))
    
    # Fond transparent pour s'adapter au thème Streamlit (Clair/Sombre)
    fig.patch.set_alpha(0.0)
    
    # Couleur verte de la pelouse
    ax.set_facecolor('#226343')
    
    # Lignes extérieures du demi-terrain (0 à 50 en X, 0 à 60 en Y)
    ax.plot([0, 50, 50, 0, 0], [0, 0, 60, 60, 0], color='white', linewidth=2.5)
    
    # Surface de réparation (Foot 5)
    penalty_area = patches.Rectangle((0, 15), 12, 30, edgecolor='white', facecolor='none', linewidth=2)
    ax.add_patch(penalty_area)
    
    # Point de penalty
    ax.scatter(9, 30, color='white', s=25, zorder=2)
    
    # Arc de cercle du milieu de terrain (ligne médiane à X=50)
    center_arc = patches.Arc((50, 30), 18, 18, angle=0, theta1=90, theta2=270, color='white', linewidth=2)
    ax.add_patch(center_arc)
    
    # Positionnement tactique fixe pour un 5v5 (Configuration standard 1-2-2)
    positions = [
        (5, 30),   # Joueur 1 : Gardien / Dernier défenseur
        (19, 14),  # Joueur 2 : Défenseur Gauche
        (19, 46),  # Joueur 3 : Défenseur Droit
        (38, 18),  # Joueur 4 : Attaquant Gauche
        (38, 42)   # Joueur 5 : Attaquant Droit
    ]
    
    # Tri optionnel pour mettre les défenseurs derrière et attaquants devant visuellement
    players = team_df.sort_values(by="Poste", ascending=False).reset_index(drop=True)
    
    for i, row in players.iterrows():
        if i >= len(positions):
            break
        x, y = positions[i]
        
        # Dessin du maillot/pion du joueur
        ax.scatter(x, y, color=primary_color, s=550, edgecolors='white', linewidths=2, zorder=3)
        
        # Affichage du numéro ou de la note à l'intérieur du pion
        ax.text(x, y, str(int(row['Note (1-10)'])), color='white', fontsize=9, weight='bold', 
                ha='center', va='center', zorder=4)
        
        # Affichage du nom du joueur dans un petit encadré lisible sous le pion
        ax.text(x, y - 3.8, row['Nom du Joueur'], color='white', fontsize=10, weight='bold',
                ha='center', va='center',
                bbox=dict(facecolor='#111111', alpha=0.75, edgecolor='none', boxstyle='round,pad=0.25'),
                zorder=4)

    # Paramétrages des axes graphiques
    ax.set_xlim(-2, 52)
    ax.set_ylim(-2, 62)
    ax.axis('off')
    plt.tight_layout()
    return fig

# --- LOGIQUE DE L'APPLICATION ---
st.title("⚽ Foot 5 - Composition & Visualisation Terrain")

tab1, tab2 = st.tabs(["⚖️ Équilibrage du Jour", "🏃 Effectif"])

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
            
            # Algorithme Excel
            selected_players = selected_players.copy()
            selected_players["Score Tri"] = selected_players["Note (1-10)"] + selected_players["Poste"].apply(lambda x: 0.1 if x == "Attaque" else 0.0)
            sorted_players = selected_players.sort_values(by="Score Tri", ascending=False).reset_index(drop=True)
            
            # Répartition Snake Draft
            idx_team1 = [0, 3, 4, 7, 8]
            idx_team2 = [1, 2, 5, 6, 9]
            
            team1 = sorted_players.iloc[idx_team1].copy()
            team2 = sorted_players.iloc[idx_team2].copy()
            
            # --- AFFICHAGE DES TERRAINS TACTIQUES ---
            st.write("---")
            col_field1, col_field2 = st.columns(2)
            
            with col_field1:
                st.subheader("🔵 ÉQUIPE 1")
                # Affichage du graphique Matplotlib créé dynamiquement
                fig1 = draw_tactical_field(team1, "Équipe 1", "#1C6CF6")
                st.pyplot(fig1)
                
                avg_1 = team1["Note (1-10)"].mean()
                st.metric("Niveau Moyen", f"{avg_1:.1f}")
                st.dataframe(team1[["Nom du Joueur", "Note (1-10)", "Poste"]], hide_index=True, use_container_width=True)
                
            with col_field2:
                st.subheader("🔴 ÉQUIPE 2")
                # Affichage du graphique Matplotlib créé dynamiquement
                fig2 = draw_tactical_field(team2, "Équipe 2", "#E03131")
                st.pyplot(fig2)
                
                avg_2 = team2["Note (1-10)"].mean()
                st.metric("Niveau Moyen", f"{avg_2:.1f}")
                st.dataframe(team2[["Nom du Joueur", "Note (1-10)", "Poste"]], hide_index=True, use_container_width=True)
    else:
        st.info(f"🏃 Sélectionnez exactement 10 joueurs (Actuel : {nb_selected}/10)")

# (L'onglet 2 reste identique pour la gestion de l'effectif)
with tab2:
    st.header("Gestion de la base")
    st.data_editor(st.session_state.players_df, hide_index=True, use_container_width=True)
