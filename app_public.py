import streamlit as st
import pandas as pd
import os
import json

# 1. Configuration de la page
st.set_page_config(page_title="Pool Elvis LNH", page_icon="🏒", layout="wide")

FICHIER_SAUVEGARDE_PUBLIC = "elvisgithub_sauvegarde.json"
MASSE_SALARIALE_MAX = 115.000  # 115,000$ (en M$)

QUOTAS_POSITIONS = {
    'C': 8,
    'AG': 6,
    'AD': 6,
    'D': 9,
    'G': 3
}

COULEURS_POS = {
    'C': 'orange',
    'AG': 'red',
    'AD': 'blue',
    'D': 'green',
    'G': 'violet'
}

EQUIPES_OFFICIELLES_32 = [
    'ANA', 'BOS', 'BUF', 'CGY', 'CAR', 'CHI', 'COL', 'CLB', 
    'DAL', 'DET', 'EDM', 'FLA', 'L-A', 'MIN', 'MTL', 'NSH', 
    'N-J', 'NYI', 'NYR', 'OTT', 'PHI', 'PIT', 'S J', 'SEA', 
    'STL', 'T-B', 'TOR', 'UTAH', 'VAN', 'VEG', 'WAS', 'WIN'
]

# 2. Analyseur direct sans cache (lecture en temps réel)
def charger_base_publique():
    fichiers_possibles = ['elvisgithub.csv', 'elvisgithub.csv.txt', 'elvispool.csv', 'joueurs.csv']
    dans_dossier = [f for f in os.listdir('.') if 'elvis' in f.lower() or 'github' in f.lower()]
    tous = fichiers_possibles + dans_dossier
    
    fichier = next((f for f in tous if os.path.exists(f)), None)
    
    if not fichier:
        return pd.DataFrame(), [], None

    joueurs = []
    equipes_trouvees = []

    try:
        if fichier.endswith('.xlsx'):
            excel_obj = pd.ExcelFile(fichier)
            df_raw = pd.read_excel(fichier, sheet_name=excel_obj.sheet_names[0], header=None)
            lignes = [";".join([str(val) for val in df_raw.iloc[i].values]) for i in range(len(df_raw))]
        else:
            with open(fichier, "r", encoding="utf-8", errors="ignore") as f:
                lignes = f.readlines()

        for line in lignes:
            sep = ";" if line.count(";") >= line.count(",") else ","
            parts = [p.strip() for p in line.split(sep)]
            line_upper = line.upper()

            if "SALAIRE" in line_upper and "POINTS" in line_upper:
                continue

            idx = 0
            block_num = 0
            while idx < len(parts):
                block = parts[idx:idx+5]
                idx += 6

                if len(block) >= 4:
                    pos, nom, salaire = block[0], block[1], block[2]
                    equipe = block[3] if len(block) > 3 else ""
                    
                    if pos in ['AG', 'C', 'AD', 'D', 'G'] and nom and nom.lower() != 'nan':
                        eq_code = equipe.strip() if equipe else ""
                        
                        if eq_code in ["S J", "SEA"] and block_num == 2:
                            equipe_finale = "SEA"
                        elif eq_code in ["S J"] and block_num == 1:
                            equipe_finale = "S J"
                        else:
                            equipe_finale = eq_code if eq_code else f"EQ_{block_num}"

                        try:
                            sal_clean = float(salaire.replace(',', '.'))
                        except ValueError:
                            sal_clean = 0.0

                        if equipe_finale and equipe_finale not in equipes_trouvees:
                            equipes_trouvees.append(equipe_finale)

                        joueurs.append({
                            'Position': pos,
                            'Nom': nom,
                            'Salaire': sal_clean,
                            'Équipe': equipe_finale,
                            'Affichage': f"{nom} [{pos}] - ${sal_clean:,.3f}M"
                        })
                block_num += 1

        df = pd.DataFrame(joueurs)
        if not df.empty:
            df = df.drop_duplicates(subset=['Nom', 'Équipe']).reset_index(drop=True)
        return df, equipes_trouvees, fichier
    except Exception:
        return pd.DataFrame(), [], None

df_players, liste_equipes, fichier_source = charger_base_publique()

# 3. Sauvegarde et chargement
def sauvegarder_donnees(donnees):
    def convertir_types_numpy(obj):
        if hasattr(obj, 'item'):
            return obj.item()
        return str(obj)

    with open(FICHIER_SAUVEGARDE_PUBLIC, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=4, default=convertir_types_numpy)

def charger_donnees():
    if os.path.exists(FICHIER_SAUVEGARDE_PUBLIC):
        try:
            with open(FICHIER_SAUVEGARDE_PUBLIC, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception):
            return {}
    return {}

if 'mes_equipes_public' not in st.session_state:
    st.session_state['mes_equipes_public'] = charger_donnees()

# 4. Calcul des points (28 meilleurs retenus selon les points FICTIFS)
def calculer_points_elvis_28(df_choix):
    if df_choix.empty:
        return 0
    
    df_attaquants = df_choix[df_choix['Position'].isin(['C', 'AG', 'AD'])].sort_values(by='Points Fictifs', ascending=False)
    df_defenseurs = df_choix[df_choix['Position'] == 'D'].sort_values(by='Points Fictifs', ascending=False)
    df_gardiens = df_choix[df_choix['Position'] == 'G'].sort_values(by='Points Fictifs', ascending=False)

    top_attaquants = df_attaquants.head(18)
    top_defenseurs = df_defenseurs.head(8)
    top_gardiens = df_gardiens.head(2)

    pts_totaux = int(top_attaquants['Points Fictifs'].sum() + top_defenseurs['Points Fictifs'].sum() + top_gardiens['Points Fictifs'].sum())
    return pts_totaux

# --- INTERFACE GRAPHIQUE ---
st.title("🏒 Pool Elvis LNH")

# ✅ EN-TÊTE ÉPURÉ AVEC LA NOTE EXPLICATIVE
st.info("""
📋 **Règlements du Pool :**
* **32 Choix :** Exactement **1 joueur par équipe** LNH (Masse Salariale Max : **115,000$**).
* **Quotas de Positions :** **8** :orange[C] | **6** :red[AG] | **6** :blue[AD] | **9** :green[D] | **3** :violet[G].
* 🏆 **Calcul (28 Meilleurs) :** Seuls tes **18** meilleurs Attaquants, **8** meilleurs Défenseurs et **2** meilleurs Gardiens seront comptabilisés à la fin !

💡 **Projections personnelles :** Si vous désirez projeter vos propres points pour chaque joueur, inscrivez simplement votre prédiction dans la petite case située **en haut à droite de la boîte de chaque équipe** !
""")

if not df_players.empty:
    
    equipes_manquantes = [e for e in EQUIPES_OFFICIELLES_32 if e not in liste_equipes]
    if len(liste_equipes) < 32:
        st.warning(f"⚠️ **Attention : seulement {len(liste_equipes)} équipes détectées sur 32 !**")

    st.subheader("🎯 Faites vos choix et vos prédictions pour chaque équipe LNH")

    nom_participant = "Mon Alignement"
    alignement_sauve = st.session_state['mes_equipes_public'].get(nom_participant, {}).get("joueurs", {})

    choix_actuels = []
    cols_ui = st.columns(4)
    
    for i, eq in enumerate(sorted(liste_equipes)):
        col_target = cols_ui[i % 4]
        df_eq = df_players[df_players['Équipe'] == eq]
        options_eq = df_eq['Affichage'].tolist()
        
        index_defaut = 0
        points_defaut = 0
        if eq in alignement_sauve:
            nom_sauve = alignement_sauve[eq]["nom"]
            points_defaut = alignement_sauve[eq]["points_fictifs"]
            row_sauve = df_eq[df_eq['Nom'] == nom_sauve]
            if not row_sauve.empty:
                index_defaut = options_eq.index(row_sauve['Affichage'].iloc[0])

        with col_target:
            with st.container(border=True):
                sel_key = f"sel_{nom_participant}_{eq}"
                if sel_key in st.session_state:
                    choix_courant = st.session_state[sel_key]
                    row_courante = df_eq[df_eq['Affichage'] == choix_courant].iloc[0]
                else:
                    row_courante = df_eq.iloc[index_defaut]
                    
                pos_courante = row_courante['Position']
                c_pos = COULEURS_POS.get(pos_courante, 'gray')

                # LIGNE DU HAUT : NOM CLUB À GAUCHE, PTS PRÉVUS À DROITE
                c_nom, c_pts = st.columns([1.2, 1])
                with c_nom:
                    st.markdown(f"**{eq}** | :{c_pos}[**{pos_courante}**]")
                with c_pts:
                    pts_fictifs = st.number_input(
                        "Pts", 
                        min_value=0, 
                        max_value=250, 
                        value=points_defaut, 
                        step=1, 
                        key=f"pts_{nom_participant}_{eq}",
                        label_visibility="collapsed",
                        help="Inscrivez votre prédiction de points"
                    )

                # MENU DÉROULANT DU JOUEUR
                choix_aff = st.selectbox(
                    label=f"Joueur {eq}", 
                    options=options_eq, 
                    index=index_defaut, 
                    label_visibility="collapsed",
                    key=sel_key
                )
                
                row_choisi = df_eq[df_eq['Affichage'] == choix_aff].iloc[0]

                choix_actuels.append({
                    'Nom': row_choisi['Nom'],
                    'Équipe': eq,
                    'Position': row_choisi['Position'],
                    'Salaire': row_choisi['Salaire'],
                    'Points Fictifs': pts_fictifs
                })

    # Calculs en temps réel
    df_choix = pd.DataFrame(choix_actuels)
    tot_salaire = float(df_choix['Salaire'].sum()) if not df_choix.empty else 0.0
    tot_points_fictifs = calculer_points_elvis_28(df_choix)
    
    counts_pos = df_choix['Position'].value_counts() if not df_choix.empty else {}
    nb_c = int(counts_pos.get('C', 0))
    nb_ag = int(counts_pos.get('AG', 0))
    nb_ad = int(counts_pos.get('AD', 0))
    nb_d = int(counts_pos.get('D', 0))
    nb_g = int(counts_pos.get('G', 0))

    respect_cap = tot_salaire <= MASSE_SALARIALE_MAX
    respect_c = nb_c == QUOTAS_POSITIONS['C']
    respect_ag = nb_ag == QUOTAS_POSITIONS['AG']
    respect_ad = nb_ad == QUOTAS_POSITIONS['AD']
    respect_d = nb_d == QUOTAS_POSITIONS['D']
    respect_g = nb_g == QUOTAS_POSITIONS['G']
    respect_nb_equipes = len(choix_actuels) == 32
    
    alignement_valide = respect_cap and respect_c and respect_ag and respect_ad and respect_d and respect_g and respect_nb_equipes

    st.markdown("---")
    st.subheader("📊 Validation de votre Alignement")
    
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("💰 Masse Salariale", f"${tot_salaire:,.3f}M", delta=f"${MASSE_SALARIALE_MAX - tot_salaire:,.3f}M dispo", delta_color="normal" if respect_cap else "inverse")
    m2.metric("🏒 C", f"{nb_c} / 8", delta="OK" if respect_c else "Erreur", delta_color="normal" if respect_c else "off")
    m3.metric("🏃 AG", f"{nb_ag} / 6", delta="OK" if respect_ag else "Erreur", delta_color="normal" if respect_ag else "off")
    m4.metric("🏃 AD", f"{nb_ad} / 6", delta="OK" if respect_ad else "Erreur", delta_color="normal" if respect_ad else "off")
    m5.metric("🛡️ D", f"{nb_d} / 9", delta="OK" if respect_d else "Erreur", delta_color="normal" if respect_d else "off")
    m6.metric("🧱 G", f"{nb_g} / 3", delta="OK" if respect_g else "Erreur", delta_color="normal" if respect_g else "off")

    st.markdown(f"### 🏆 Projection Totale (Vos 28 meilleurs) : **{tot_points_fictifs} pts**")

    if not alignement_valide:
        st.error("⚠️ **Contraintes non respectées :** Vérifiez votre Masse Salariale et vos quotas de positions.")
    else:
        st.success("✅ **Alignement 100% Valide !** Vous pouvez enregistrer votre sélection.")

    if st.button("🚀 Enregistrer mon Alignement", type="primary", use_container_width=True, disabled=not alignement_valide):
        dict_enregistre = {
            "participant": nom_participant,
            "salaire_total": tot_salaire,
            "points_projetes": tot_points_fictifs,
            "joueurs": {row['Équipe']: {"nom": row['Nom'], "points_fictifs": row['Points Fictifs']} for row in choix_actuels}
        }
        st.session_state['mes_equipes_public'][nom_participant] = dict_enregistre
        sauvegarder_donnees(st.session_state['mes_equipes_public'])
        st.success("🎉 Ton alignement a été enregistré avec succès !")
        st.balloons()

else:
    st.error("🚨 Le fichier 'elvisgithub.csv' n'a pas été trouvé. Veuillez vérifier qu'il est bien dans le dossier.")