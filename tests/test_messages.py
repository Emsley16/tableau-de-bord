"""Tests réels du programme Messages ops dans Chrome (clics et saisies comme sur le téléphone).

Lancement, depuis la racine du dépôt :  python3 tests/test_messages.py
Prérequis : Python 3, le paquet « playwright » et Google Chrome installés.

NOUVEAU : le programme du dépôt, messages-ops.html.
ANCIEN  : la version du 14/10/2026, gardée comme référence. À saisie égale, les messages
          radio et l'annonce SAMU du programme doivent rester identiques à cette référence,
          sauf changement demandé par Anthony (mettre alors à jour le test concerné).
"""
import sys, json, re
from pathlib import Path
from playwright.sync_api import sync_playwright

ICI = Path(__file__).resolve().parent
NOUVEAU = (ICI.parent / "messages-ops.html").as_uri()
ANCIEN = (ICI / "reference-2026.10.14f.html").as_uri()
echecs = []


def verifier(nom, obtenu, attendu):
    ok = obtenu == attendu
    print(("OK   " if ok else "ÉCHEC") + " — " + nom)
    if not ok:
        echecs.append(nom)
        print("  attendu :\n    " + attendu.replace("\n", "\n    "))
        print("  obtenu  :\n    " + obtenu.replace("\n", "\n    "))


def ouvrir(nav, url):
    # un contexte neuf par scénario : stockage local vierge, comme une première ouverture
    ctx = nav.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    page = ctx.new_page()
    erreurs = []
    page.on("pageerror", lambda e: erreurs.append(str(e)))
    # la référence est rangée sans ses icônes ni son manifeste : leur absence n'est pas une erreur du programme
    page.on("console", lambda m: erreurs.append(m.text) if m.type == "error" and "ERR_FILE_NOT_FOUND" not in m.text else None)
    page.goto(url)
    page.wait_for_selector("#ngrid button", state="attached")
    return page, erreurs


def puce(page, groupe, texte):
    """Appuie sur une puce d'un groupe, repérée par son libellé exact."""
    page.locator(f"#{groupe} .chip", has_text=texte).first.click()


def assurer(page, groupe, texte):
    """Appuie sur la puce seulement si elle n'est pas déjà active."""
    c = page.locator(f"#{groupe} .chip", has_text=texte).first
    if c.get_attribute("aria-pressed") != "true":
        c.click()


def retirer(page, groupe, texte):
    c = page.locator(f"#{groupe} .chip", has_text=texte).first
    if c.get_attribute("aria-pressed") == "true":
        c.click()


def ecran(page, p):
    page.locator(f"#phSeg button[data-p={p}]").click()


def vue(page, v):
    page.locator(f".tab[data-v={v}]").click()


def message(page, mode, support="ecrit"):
    vue(page, "codis")
    if page.locator("#supSeg").count():
        page.locator(f"#supSeg button[data-s={support}]").click()
    page.locator(f"#msgSeg button[data-m={mode}]").click()
    return page.locator("#out").input_value()


def nature(page, libelle):
    vue(page, "saisie")
    ecran(page, "arr")
    page.locator("#ngrid button", has_text=libelle).first.click()


def victime(page, age, sexe):
    page.fill("#age", str(age))
    page.locator(f"#sxSeg button[data-s={sexe}]").click()


with sync_playwright() as pw:
    nav = pw.chromium.launch(channel="chrome")

    # ───── 1. Malade UR : votre exemple d'ambiance, avec le motif ─────
    page, err = ouvrir(nav, NOUVEAU)
    nature(page, "Douleur thoracique")
    victime(page, 26, "Femme")
    page.fill("#commune", "Javrezac")
    page.locator("#etat .chip[data-v=UR]").click()
    verifier("Ambiance SAP — malade UR avec motif", message(page, "ambiance"),
             "Opération de secours sur la commune de JAVREZAC.\n"
             "Secours à une victime malade de sexe féminin, UR, âgée de 26 ans, présentant une douleur thoracique, bilan et régulation en cours.")
    verifier("Aucun contexte présélectionné en SAP", page.evaluate("one('ctxlieu')"), "")
    vue(page, "saisie")

    # Sans motif : exactement votre phrase
    vue(page, "saisie")
    page.locator("#ngrid button", has_text="Douleur thoracique").first.click()  # second appui : rien ne change, on désélectionne via le motif
    page.evaluate("document.querySelectorAll('#titrec .chip').forEach(c=>c.setAttribute('aria-pressed','false'));rendre()")
    verifier("Ambiance SAP — sans motif ni contexte (votre exemple)", message(page, "ambiance").split("\n")[1],
             "Secours à une victime malade de sexe féminin, UR, âgée de 26 ans, bilan et régulation en cours.")

    # Demande de renfort + adresse différente de celle du départ
    nature(page, "Douleur thoracique")
    page.locator("#renf .chip", has_text="SMUR").first.click()
    page.locator("#renf .chip", has_text="Forces de l'ordre").first.click()
    puce(page, "adrind", "Adresse indiquée au départ")  # décoche
    page.fill("#adresse", "12 rue des Vignes")
    verifier("Ambiance SAP — renfort et adresse différente", message(page, "ambiance"),
             "Opération de secours sur la commune de JAVREZAC, au 12 rue des Vignes.\n"
             "Secours à une victime malade de sexe féminin, UR, âgée de 26 ans, présentant une douleur thoracique, bilan et régulation en cours.\n"
             "Je demande : SMUR et Forces de l'ordre.")

    # Compte rendu de la même intervention : transport
    vue(page, "saisie")
    ecran(page, "fin")
    puce(page, "medqui", "Médecin du SMUR")
    puce(page, "actFin", "Régulation CRRA 15")
    puce(page, "actFin", "Oxygène")
    puce(page, "devenir", "Transportée")
    page.fill("#vect", "VSAV médicalisé")
    page.fill("#dest", "CH Cognac")
    page.fill("#gh", "1415")
    verifier("Compte rendu SAP — transport médicalisé, groupe horaire", message(page, "cr"),
             "GH 1415 — Opération de secours sur la commune de JAVREZAC, au 12 rue des Vignes.\n"
             "À notre arrivée, nous sommes confrontés à une victime malade de sexe féminin, UR, âgée de 26 ans, présentant une douleur thoracique.\n"
             "Victime médicalisée par le médecin du SMUR de COGNAC. Actions des moyens sapeurs-pompiers : mise sous oxygène.\n"
             "La régulation CRRA 15 a été effectuée et la victime est transportée par VSAV médicalisé sur CH Cognac.\n"
             "Fin d'intervention pour les moyens sapeurs-pompiers.")

    # Radio, même intervention : groupe horaire en tête, régulation et transport en dernière ligne
    verifier("Compte rendu radio — régulation puis transport", "\n".join(message(page, "cr", "radio").split("\n")[3:]),
             "Nous sommes confrontés à une douleur thoracique chez une femme, UR, de 26 ans ; bilan humain définitif : 1 malade\n"
             "Après régulation CRRA 15, la victime est transportée par VSAV médicalisé sur CH Cognac")
    verifier("Compte rendu radio — en-tête", message(page, "cr", "radio").split("\n")[0], "CODIS 16 de VSAV 1 Cognac — compte rendu, groupe horaire 1415")
    vue(page, "saisie")
    puce(page, "finInter", "Intervention terminée")
    verifier("Compte rendu radio SAP — intervention terminée", message(page, "cr", "radio").split("\n")[-1], "Fin d'intervention pour les moyens sapeurs-pompiers")
    vue(page, "saisie")
    puce(page, "finInter", "Encore du travail en cours")
    verifier("Compte rendu écrit SAP — encore en cours", message(page, "cr").split("\n")[-1], "Bilan et régulation en cours.")
    vue(page, "saisie")
    page.locator("#finInter .chip", has_text="Encore du travail en cours").click()   # retire le choix
    # Laissée sur place, refus
    vue(page, "saisie")
    puce(page, "devenir", "Laissée sur place")
    page.fill("#devPrec", "Confiée à sa famille")
    verifier("Compte rendu SAP — laissée sur place", message(page, "cr").split("\n")[3],
             "La régulation CRRA 15 a été effectuée et la victime est laissée sur place sur décision du médecin du SMUR de COGNAC, confiée à sa famille.")
    vue(page, "saisie")
    page.fill("#devPrec", "la victime est confié à la famille.")
    verifier("Devenir — une précision commençant par « la victime est » ne crée pas de redite", message(page, "cr").split("\n")[3],
             "La régulation CRRA 15 a été effectuée et la victime est laissée sur place sur décision du médecin du SMUR de COGNAC, confié à la famille.")
    vue(page, "saisie")
    puce(page, "medqui", "Médecin du SMUR")   # retire le médecin : la décision revient au régulateur
    page.locator(".chip[data-fill=devPrec]", has_text="Confiée à la famille").click()
    verifier("Devenir — sans médecin sur place, décision du médecin régulateur", message(page, "cr").split("\n")[3],
             "La régulation CRRA 15 a été effectuée et la victime est laissée sur place sur décision du médecin régulateur, confiée à sa famille.")
    vue(page, "saisie")
    puce(page, "medqui", "Médecin du SMUR")
    vue(page, "saisie")
    puce(page, "devenir", "Refus de transport")
    page.fill("#devPrec", "")
    verifier("Compte rendu SAP — refus de transport", message(page, "cr").split("\n")[3],
             "La régulation CRRA 15 a été effectuée et la victime refuse le transport et est laissée sur place.")

    # Persistance : rechargement de la page, le message doit être identique
    avant = page.locator("#out").input_value()
    page.reload()
    page.wait_for_selector("#ngrid button", state="attached")
    vue(page, "codis")
    verifier("Persistance après rechargement", page.locator("#out").input_value(), avant)
    verifier("Aucune erreur JavaScript (scénario 1)", json.dumps(err), "[]")
    page.close()

    # ───── 2. Votre compte rendu de ce matin (décès) ─────
    page, err = ouvrir(nav, NOUVEAU)
    victime(page, 63, "Femme")
    page.fill("#commune", "Gensac-la-Pallue")
    page.fill("#adresse", "7 rue des Gascards")
    page.locator("#ngrid button", has_text="ACR").first.click()   # nature ACR : qualification et UA suivent
    verifier("Nature ACR — catégorie UA posée seule", page.evaluate("one('etat')"), "UA")
    verifier("Nature ACR — qualification automatique", page.evaluate("qualifP()"), "victime en ACR")
    retirer(page, "ctxlieu", "Domicile")
    ecran(page, "fin")
    page.locator("#gestesChips .chip", has_text="RCP · témoin").click()
    puce(page, "medqui", "Médecin du SMUR")
    puce(page, "actFin", "Aucune manœuvre de réanimation")
    puce(page, "devenir", "Décédée")
    page.fill("#hdc", "07:23")
    puce(page, "dcdoc", "Certificat de décès établi")
    puce(page, "corps", "La famille")
    puce(page, "eluNon", "La famille ne souhaite pas")
    puce(page, "finInter", "Intervention terminée")
    verifier("Compte rendu SAP — décès (votre texte de référence)", message(page, "cr"),
             "Opération de secours sur la commune de GENSAC-LA-PALLUE, au 7 rue des Gascards.\n"
             "À notre arrivée, nous sommes confrontés à une victime de sexe féminin, âgée de 63 ans, en ACR. RCP en cours par un témoin.\n"
             "Victime déclarée décédée (DCD) par le médecin du SMUR de COGNAC à 7h23. Certificat de décès établi. Aucune manœuvre de réanimation engagée par les moyens sapeurs-pompiers.\n"
             "Le corps est laissé à la responsabilité de la famille, qui ne souhaite pas le déplacement d'un élu.\n"
             "Fin d'intervention pour les moyens sapeurs-pompiers.")
    verifier("Contrôles de cohérence — décès complet", page.locator("#wC").inner_text().strip(),
             "Message cohérent. Ordre et contenu conformes.")

    # Élu sur les lieux + forces de l'ordre + obstacle médico-légal
    vue(page, "saisie")
    puce(page, "eluNon", "La famille ne souhaite pas")
    puce(page, "corps", "La famille")
    puce(page, "corps", "Les forces de l'ordre")
    puce(page, "corps", "L'élu sur les lieux")
    puce(page, "dcdoc", "Avec obstacle médico-légal")
    page.fill("#crLib", "RCP arrêtée sur décision du médecin du SMUR")
    lignes = message(page, "cr").split("\n")
    verifier("Compte rendu SAP — décès, OML, phrase libre", lignes[2],
             "Victime déclarée décédée (DCD) par le médecin du SMUR de COGNAC à 7h23. Certificat de décès établi avec obstacle médico-légal. Aucune manœuvre de réanimation engagée par les moyens sapeurs-pompiers. RCP arrêtée sur décision du médecin du SMUR.")
    verifier("Compte rendu SAP — corps aux forces de l'ordre et à l'élu", lignes[3],
             "Le corps est laissé à la responsabilité des forces de l'ordre et de l'élu sur les lieux.")

    # Ambiance d'un ACR : RCP en tête, alerte si RCP non cochée
    vue(page, "saisie")
    ecran(page, "arr")
    amb = message(page, "ambiance")
    verifier("Ambiance SAP — ACR sans RCP cochée", amb.split("\n")[1],
             "Secours à une victime de sexe féminin, UA, âgée de 63 ans, en ACR, bilan et régulation en cours.")
    verifier("Alerte ACR sans RCP présente", str("ACR annoncé sans RCP" in page.locator("#wC").inner_text()), "True")
    vue(page, "saisie")
    puce(page, "actS", "Procédons à la RCP")
    verifier("Ambiance SAP — ACR avec RCP", message(page, "ambiance").split("\n")[1],
             "Secours à une victime de sexe féminin, UA, âgée de 63 ans, en ACR, RCP en cours, bilan et régulation en cours.")
    verifier("Aucune erreur JavaScript (scénario 2)", json.dumps(err), "[]")
    page.close()

    # Cas n° 2 du 23/11 : nature saisie à la main, SMUR déjà sur les lieux
    page, err = ouvrir(nav, NOUVEAU)
    nature(page, "Préciser")
    page.fill("#natlib", "Personne ne répondant pas aux appels")
    victime(page, 63, "Femme")
    puce(page, "aggrav", "ACR")
    puce(page, "surlieux", "SMUR")
    puce(page, "surlieux", "Forces de l'ordre")
    page.fill("#surlieuxLib", "Voisin infirmier")
    amb = message(page, "ambiance", "radio").split("\n")
    verifier("Nature libre — article accordé (« une personne »)", amb[3][:54], "Nous sommes confrontés à une personne ne répondant pas")
    verifier("Services sur les lieux — radio", amb[4], "Sur les lieux : SMUR, forces de l'ordre et voisin infirmier")
    verifier("Services sur les lieux — pas d'alerte « secours suffisants » quand le SMUR est là",
             str("Gravité élevée" in page.locator("#wC").inner_text()), "False")
    verifier("Services sur les lieux — écrit", message(page, "ambiance").split("\n")[2], "Sur les lieux : SMUR, forces de l'ordre et voisin infirmier.")
    vue(page, "saisie")
    page.locator("#renf .chip", has_text="SMUR").first.click()
    message(page, "ambiance", "radio")
    verifier("Services sur les lieux — alerte si le même service est demandé", str("à la fois demandé et déjà sur les lieux" in page.locator("#wC").inner_text()), "True")
    page.close()

    # Cas n° 2 du 23/11, compte rendu : ACR, RCP arrêtée par le SMUR, décès, corps laissé à la famille
    page, err = ouvrir(nav, NOUVEAU)
    page.locator("#ngrid button", has_text="ACR").first.click()
    victime(page, 63, "Femme")
    page.fill("#commune", "Gensac la pallue")
    page.fill("#adresse", "7 rue des gascards")
    puce(page, "ctxlieu", "Domicile")
    puce(page, "surlieux", "SMUR")
    ecran(page, "fin")
    page.fill("#gh", "1205")
    puce(page, "finInter", "Intervention terminée")
    page.locator("#gestesChips .chip", has_text="RCP · famille").click()
    puce(page, "medqui", "Médecin du SMUR")
    puce(page, "actFin", "Aucune manœuvre de réanimation")
    puce(page, "devenir", "Laissée sur place")
    message(page, "cr")
    verifier("Contrôle — ACR « laissée sur place » : le programme oriente vers « Décédée »", str("choisir « Décédée »" in page.locator("#wC").inner_text()), "True")
    vue(page, "saisie")
    puce(page, "devenir", "Décédée")
    page.fill("#hdc", "11:52")
    puce(page, "dcdoc", "RCP arrêtée sur décision du médecin")
    puce(page, "dcdoc", "Certificat de décès établi")
    puce(page, "dcdoc", "Sans obstacle médico-légal")
    puce(page, "corps", "La famille")
    puce(page, "eluNon", "La famille ne souhaite pas")
    verifier("Cas n° 2 — compte rendu écrit d'un décès", message(page, "cr"),
             "GH 1205 — Opération de secours sur la commune de GENSAC LA PALLUE, au 7 rue des gascards.\n"
             "À notre arrivée, nous sommes confrontés à une victime de sexe féminin, âgée de 63 ans, à son domicile, en ACR. RCP en cours par la famille.\n"
             "Sur les lieux : SMUR.\n"
             "RCP arrêtée sur décision du médecin du SMUR de COGNAC, qui déclare la victime décédée (DCD) à 11h52. Certificat de décès établi sans obstacle médico-légal. Aucune manœuvre de réanimation engagée par les moyens sapeurs-pompiers.\n"
             "Le corps est laissé à la responsabilité de la famille, qui ne souhaite pas le déplacement d'un élu.\n"
             "Fin d'intervention pour les moyens sapeurs-pompiers.")
    verifier("Cas n° 2 — compte rendu radio d'un décès", message(page, "cr", "radio"),
             "CODIS 16 de VSAV 1 Cognac — compte rendu, groupe horaire 1205\n"
             "Secours suffisants\n"
             "Opération de secours sur la commune de Gensac la pallue à l'adresse indiquée\n"
             "Nous sommes confrontés à un arrêt cardio-respiratoire chez une femme de 63 ans à son domicile ; bilan humain définitif : 1 décédé\n"
             "Sur les lieux : SMUR\n"
             "RCP arrêtée sur décision du médecin du SMUR de COGNAC, qui déclare la victime décédée (DCD) à 11h52. Certificat de décès établi sans obstacle médico-légal. Aucune manœuvre de réanimation engagée par les moyens sapeurs-pompiers.\n"
             "Le corps est laissé à la responsabilité de la famille, qui ne souhaite pas le déplacement d'un élu.\n"
             "Fin d'intervention pour les moyens sapeurs-pompiers")
    verifier("Cas n° 2 — ambiance radio : UA après « femme »", message(page, "ambiance", "radio").split("\n")[3],
             "Nous sommes confrontés à un arrêt cardio-respiratoire chez une femme, UA, de 63 ans à son domicile ; bilan humain provisoire : 1 victime en ACR")
    verifier("Aucune erreur JavaScript (cas n° 2)", json.dumps(err), "[]")
    page.close()

    # Cas n° 3 du 23/11 : trois victimes, demande de renfort dès l'ambiance
    page, err = ouvrir(nav, NOUVEAU)
    nature(page, "Préciser")
    page.fill("#natlib", "suspicion intoxication co")
    page.locator("#natType button[data-m=autre]").click()
    victime(page, 54, "Homme")
    page.locator("#etat .chip[data-v=UA]").click()
    page.fill("#commune", "Chateaubernard")
    puce(page, "ctxlieu", "Domicile")
    page.fill("#aggravlib", "somnolent")
    page.locator("#addxv").click()
    page.locator("#xv input[data-xk=nb]").fill("2")
    for r in ("SMUR", "Chef de Groupe", "GRDF", "VSAV supplémentaire"):
        # certains renforts sont dans la partie repliée de la liste : appui déclenché directement
        page.evaluate("r=>document.querySelector('#renf .chip[data-r=\"'+r+'\"]').click()", r)
    verifier("Cas n° 3 — ambiance radio", message(page, "ambiance", "radio"),
             "CODIS 16 de VSAV 1 Cognac\n"
             "Je demande : SMUR, Chef de Groupe, GRDF et VSAV supplémentaire\n"
             "Opération de secours sur la commune de Chateaubernard à l'adresse indiquée\n"
             "Nous sommes confrontés à une suspicion intoxication co chez un homme, UA, de 54 ans à son domicile, somnolent ; bilan humain provisoire : 1 malade UA, 2 malades UR\n"
             "En cours de bilan")
    verifier("Cas n° 3 — ambiance écrite", message(page, "ambiance"),
             "Opération de secours sur la commune de CHATEAUBERNARD.\n"
             "Secours à une victime malade de sexe masculin, UA, âgée de 54 ans, à son domicile, présentant une suspicion intoxication co, somnolente, bilan et régulation en cours.\n"
             "Bilan humain provisoire : 1 malade UA, 2 malades UR.\n"
             "Je demande : SMUR, Chef de Groupe, GRDF et VSAV supplémentaire.")
    verifier("Aucune erreur JavaScript (cas n° 3)", json.dumps(err), "[]")
    page.close()

    # ───── 3. Formulations du motif ─────
    page, err = ouvrir(nav, NOUVEAU)
    victime(page, 82, "Homme")
    page.fill("#commune", "Cognac")
    page.locator("#etat .chip[data-v=UR]").click()
    retirer(page, "ctxlieu", "Domicile")
    attendus = {
        "Malaise": "Secours à une victime malade de sexe masculin, UR, âgée de 82 ans, présentant un malaise, bilan et régulation en cours.",
        "Signes d'AVC": "Secours à une victime malade de sexe masculin, UR, âgée de 82 ans, présentant des signes évocateurs d'un AVC, bilan et régulation en cours.",
        "Chute": "Secours à une victime blessée de sexe masculin, UR, âgée de 82 ans, à la suite d'une chute, bilan et régulation en cours.",
        "Hémorragie": "Secours à une victime malade de sexe masculin, UR, âgée de 82 ans, présentant une hémorragie, bilan et régulation en cours.",
        "Convulsions": "Secours à une victime malade de sexe masculin, UR, âgée de 82 ans, présentant une crise convulsive, bilan et régulation en cours.",
        "Détresse respiratoire": "Secours à une victime malade de sexe masculin, UR, âgée de 82 ans, présentant une détresse respiratoire, bilan et régulation en cours.",
        "Traumatisme": "Secours à une victime blessée de sexe masculin, UR, âgée de 82 ans, présentant un traumatisme, bilan et régulation en cours.",
    }
    for lib, att in attendus.items():
        nature(page, lib)
        verifier("Motif — " + lib, message(page, "ambiance").split("\n")[1], att)
    # Nature libre + contexte + constats
    nature(page, "Préciser")
    page.fill("#natlib", "Piqûre de guêpe")
    page.locator("#natType button[data-m=autre]").click()  # motif médical : la victime est un malade
    puce(page, "ctxlieu", "Voie publique")
    puce(page, "aggrav", "Inconsciente")
    puce(page, "aggrav", "Relevage difficile")
    verifier("Motif libre, contexte et constats", message(page, "ambiance").split("\n")[1],
             "Secours à une victime malade de sexe masculin, UR, âgée de 82 ans, sur la voie publique, à la suite d'une piqûre de guêpe, inconsciente, relevage difficile, bilan et régulation en cours.")
    # Nourrisson, autre victime
    vue(page, "saisie")
    page.fill("#age", "8")
    page.select_option("#ageu", "mois")
    page.locator("#addxv").click()            # bouton placé sous la victime, sans rien déplier
    page.locator("#addxv").click()
    page.locator("#xv input[data-xk=nb]").nth(1).fill("2")
    page.locator("#xv select[data-xk=gravite]").nth(1).select_option("IMP")
    amb = message(page, "ambiance").split("\n")
    verifier("Nourrisson", amb[1], "Secours à une victime malade de sexe masculin, UR, âgée de 8 mois, sur la voie publique, à la suite d'une piqûre de guêpe, inconsciente, relevage difficile, bilan et régulation en cours.")
    verifier("Plusieurs victimes — bilan humain récapitulé et regroupé", amb[2], "Bilan humain provisoire : 2 malades UR, 2 impliqués.")
    verifier("Autres victimes — bouton sous la victime, hors rubrique repliée",
             str(page.evaluate("!document.getElementById('addxv').closest('details') && document.getElementById('age').closest('.sec').contains(document.getElementById('addxv'))")), "True")
    verifier("Aucune erreur JavaScript (scénario 3)", json.dumps(err), "[]")
    page.close()

    # ───── 4. Accident de circulation ─────
    page, err = ouvrir(nav, NOUVEAU)
    page.locator("#typeSeg button[data-t=ROUTIER]").click()
    victime(page, 40, "Homme")
    page.fill("#commune", "Châteaubernard")
    page.fill("#adresse", "RN141, sens Cognac-Angoulême, PR 12")
    page.locator(".vtile[data-veh=vl]").click()
    puce(page, "energ", "Électrique")
    page.fill("#antag", "un poids lourd")
    puce(page, "charg", "Chargement endommagé")
    puce(page, "chargRisk", "Risques particuliers")
    page.fill("#chargPrec", "Fuite d'hydrocarbures")
    page.locator("#etat .chip[data-v=UA]").click()
    puce(page, "aggrav", "Incarcérée")
    puce(page, "adrind", "Adresse indiquée au départ")  # décoche : la localisation est annoncée
    verifier("Ambiance routier — une victime", message(page, "ambiance"),
             "Opération de secours sur la commune de CHÂTEAUBERNARD, RN141, sens Cognac-Angoulême, PR 12.\n"
             "Secours routier pour un accident de la circulation mettant en cause un véhicule léger électrique dans une collision frontale à forte cinétique contre un poids lourd.\n"
             "Chargement endommagé — risques particuliers liés au chargement : fuite d'hydrocarbures.\n"
             "Bilan provisoire : une victime de sexe masculin, âgée de 40 ans, UA, incarcérée.\n"
             "Prise en charge de la victime en cours.\n"
             "Je demande : SMUR et VSR.")
    # Deuxième victime
    vue(page, "saisie")
    page.locator("#addxv").click()
    page.locator("#xv select[data-xk=sexe]").select_option("féminin")
    page.locator("#xv input[data-xk=age]").fill("35")
    page.locator("#xv input[data-xk=vecteur]").fill("VSAV 2")
    page.locator("#xv input[data-xk=ch]").fill("CH Cognac")
    puce(page, "actR", "Sécurisation du site")
    puce(page, "actR", "Désincarcération")
    puce(page, "ctxlieu", "Hors agglomération")
    page.fill("#ctxdet", "Véhicule en contrebas de la chaussée")
    amb = message(page, "ambiance").split("\n")
    verifier("Ambiance routier — contexte routier", amb[1],
             "Secours routier pour un accident de la circulation hors agglomération mettant en cause un véhicule léger électrique dans une collision frontale à forte cinétique contre un poids lourd, véhicule en contrebas de la chaussée.")
    verifier("Ambiance routier — deux victimes", amb[3] + "\n" + amb[4],
             "Bilan provisoire : 2 victimes dont 1 UA et 1 incarcérée.\n"
             "Sécurisation du site, prise en charge des victimes et désincarcération des victimes en cours.")
    vue(page, "saisie")
    ecran(page, "fin")
    page.fill("#vect", "SMUR")
    page.fill("#dest", "CH Angoulême")
    puce(page, "rFin", "Site laissé aux forces de l'ordre")
    puce(page, "rFin", "Circulation rétablie")
    page.locator("#gestesChips .chip", has_text="Évacuée par des témoins").click()
    page.locator("#gestesChips .chip", has_text="Véhicule sur le toit").click()
    page.fill("#gh", "8h30")
    ecran(page, "arr")
    puce(page, "actR", "Extraction victime(s)")
    puce(page, "actR", "Nettoyage de chaussée")
    verifier("Compte rendu routier — deux victimes", message(page, "cr"),
             "GH 830 — Opération de secours sur la commune de CHÂTEAUBERNARD, RN141, sens Cognac-Angoulême, PR 12.\n"
             "À notre arrivée, nous sommes confrontés à un accident de la circulation hors agglomération mettant en cause un véhicule léger électrique dans une collision frontale à forte cinétique contre un poids lourd, véhicule en contrebas de la chaussée. 1 victime incarcérée. Victime évacuée du véhicule par des témoins. Véhicule sur le toit.\n"
             "Chargement endommagé — risques particuliers liés au chargement : fuite d'hydrocarbures.\n"
             "Bilan définitif : 2 victimes : une victime de sexe masculin, âgée de 40 ans, UA, transportée par SMUR sur CH Angoulême ; une victime de sexe féminin, âgée de 35 ans, UR, transportée par VSAV 2 sur CH Cognac.\n"
             "Les moyens sapeurs-pompiers ont procédé à la sécurisation du site, à la prise en charge des victimes, à la désincarcération des victimes, à l'extraction des victimes et au nettoyage de la chaussée.\n"
             "Site laissé à la responsabilité des forces de l'ordre. Circulation rétablie.\n"
             "Fin d'intervention pour les moyens sapeurs-pompiers.")
    page.evaluate("document.getElementById('gh').value='';rendre()")
    vue(page, "codis")
    page.locator("#msgSeg button[data-m=ambiance]").click()
    verifier("Onglet CODIS — groupe horaire masqué en ambiance", str(page.locator("#ghCBox").is_hidden()), "True")
    page.locator("#msgSeg button[data-m=cr]").click()
    page.fill("#ghC", "830")
    verifier("Onglet CODIS — groupe horaire saisi au-dessus du compte rendu", page.locator("#out").input_value().split("\n")[0][:9], "GH 830 — ")
    verifier("Onglet CODIS — groupe horaire synchronisé avec l'écran Fin", page.evaluate("raw('gh')"), "830")
    page.locator("#ghCNow").click()
    verifier("Onglet CODIS — bouton heure actuelle", str(bool(__import__("re").fullmatch(r"\d{3,4}", page.input_value("#ghC")))), "True")
    page.fill("#ghC", "830")
    radio_cr = message(page, "cr", "radio").split("\n")
    verifier("Radio routier — groupe horaire dans le compte rendu", radio_cr[0], "CODIS 16 de VSAV 1 Cognac — compte rendu, groupe horaire 830")
    verifier("Radio routier — contexte repris", radio_cr[3],
             "Nous sommes confrontés à un accident de la circulation hors agglomération mettant en cause un véhicule léger électrique dans une collision frontale à forte cinétique contre un poids lourd, véhicule en contrebas de la chaussée")
    verifier("Radio routier — encore du travail : « Nous procédons à… »", radio_cr[-1][:16], "Nous procédons à")
    verifier("Contrôle — état de l'intervention à préciser", str("terminée ou encore en cours" in page.locator("#wC").inner_text()), "True")
    vue(page, "saisie"); ecran(page, "fin")
    puce(page, "finInter", "Intervention terminée")
    verifier("Radio routier — intervention terminée", message(page, "cr", "radio").split("\n")[-1], "Fin d'intervention pour les moyens sapeurs-pompiers")
    vue(page, "saisie")
    puce(page, "finInter", "Encore du travail en cours")
    ecrit = message(page, "cr").split("\n")
    verifier("Écrit routier — encore en cours : actions au présent, pas de fin d'intervention",
             ecrit[-2][:41] + " | " + ecrit[-1], "Les moyens sapeurs-pompiers procèdent à l | Site laissé à la responsabilité des forces de l'ordre. Circulation rétablie.")
    vue(page, "saisie")
    page.locator("#finInter .chip", has_text="Encore du travail en cours").click()   # retire le choix
    verifier("Radio routier — pas de groupe horaire dans l'ambiance", message(page, "ambiance", "radio").split("\n")[0], "CODIS 16 de VSAV 1 Cognac")
    verifier("Aucun contexte présélectionné en routier (après choix manuel, seul celui-ci reste)", page.evaluate("one('ctxlieu')"), "hors agglomération")
    vue(page, "saisie")
    verifier("Écran Fin routier — champs SAP masqués",
             json.dumps(page.evaluate("['gestesBox','medBox','actFinBox','devBox','dcdBox','devPrecBox','rFinBox','trBox'].map(i=>document.getElementById(i).hidden)")),
             "[false, true, true, true, true, true, false, false]")
    verifier("Routier — constats : incarcérée et ACR présents, relevage difficile absent",
             json.dumps(page.evaluate("[...document.querySelectorAll('#aggrav .chip')].map(c=>c.textContent)"), ensure_ascii=False),
             '["Inconsciente", "ACR", "Détresse vitale", "Hémorragie active", "Incarcérée", "Accès difficile"]')
    verifier("Routier — contextes adaptés",
             json.dumps(page.evaluate("[...document.querySelectorAll('#ctxlieu .chip')].map(c=>c.textContent)"), ensure_ascii=False),
             '["Voie publique", "En agglomération", "Hors agglomération", "Voie rapide", "Intersection", "Giratoire", "Parking", "Voie privée"]')
    verifier("Routier — exemple de précision adapté", page.get_attribute("#ctxdet", "placeholder"),
             "Précision : véhicule sur le toit, en contrebas de la chaussée…")
    verifier("Routier — natures : accident de la route présent, ACR absent",
             json.dumps(page.evaluate("[...document.querySelectorAll('#ngrid button')].map(c=>c.textContent)"), ensure_ascii=False),
             '["Malaise", "Douleur thoracique", "Détresse respiratoire", "Signes d\'AVC", "Convulsions", "Chute", "Accident de la route", "Hémorragie", "Traumatisme", "Préciser"]')
    verifier("Aucune erreur JavaScript (scénario 4)", json.dumps(err), "[]")

    # Nouvelle intervention : tout repart à zéro, valeurs par défaut en place
    vue(page, "saisie")
    page.locator("#rst").click()
    page.locator("#rst").click()
    verifier("Nouvelle intervention — message remis à zéro", message(page, "ambiance"),
             "Opération de secours sur la commune de CHÂTEAUBERNARD.\n"
             "Secours à une victime malade, bilan et régulation en cours.")
    verifier("SAP — constats : ACR et relevage difficile présents, incarcérée absente",
             json.dumps(page.evaluate("[...document.querySelectorAll('#aggrav .chip')].map(c=>c.textContent)"), ensure_ascii=False),
             '["Inconsciente", "ACR", "Détresse vitale", "Hémorragie active", "Accès difficile", "Relevage difficile"]')
    verifier("SAP — natures : ACR présent, accident de la route absent",
             json.dumps(page.evaluate("[...document.querySelectorAll('#ngrid button')].map(c=>c.textContent)"), ensure_ascii=False),
             '["ACR", "Malaise", "Douleur thoracique", "Détresse respiratoire", "Signes d\'AVC", "Convulsions", "Chute", "Hémorragie", "Traumatisme", "Préciser"]')
    verifier("Catégorie placée sous la victime, avant les autres victimes",
             str(page.evaluate("(()=>{const e=document.getElementById('etat'),a=document.getElementById('age'),x=document.getElementById('addxv');return !!(a.compareDocumentPosition(e)&4)&&!!(e.compareDocumentPosition(x)&4)&&!e.closest('details')})()")), "True")
    vue(page, "saisie")
    page.fill("#commune", "Javrezac")
    page.locator("#age").click()
    page.locator("#commune").click()
    page.wait_for_timeout(150)
    verifier("Case déjà remplie — le premier appui sélectionne tout le contenu",
             page.evaluate("(()=>{const c=document.getElementById('commune');return c.value.substring(c.selectionStart,c.selectionEnd)})()"), "Javrezac")
    page.keyboard.type("Cognac")
    verifier("Case déjà remplie — la saisie remplace l'ancien contenu", page.input_value("#commune"), "Cognac")
    page.fill("#commune", "Châteaubernard")
    verifier("SAP — catégories : impliqué, UR, UA, décédé",
             json.dumps(page.evaluate("[...document.querySelectorAll('#etat .chip')].map(c=>c.dataset.v)")), '["IMP", "UR", "UA", "DCD"]')
    verifier("SAP — rien de présélectionné dans le contexte après remise à zéro", page.evaluate("one('ctxlieu')"), "")
    # impliqué, constat ACR, groupe horaire, photo d'ordonnance
    vue(page, "saisie")
    victime(page, 30, "Homme")
    page.locator("#etat .chip[data-v=IMP]").click()
    verifier("SAP écrit — impliqué", message(page, "ambiance").split("\n")[1],
             "Secours à une victime impliquée de sexe masculin, âgée de 30 ans, bilan et régulation en cours.")
    verifier("SAP radio — impliqué", message(page, "ambiance", "radio").split("\n")[3][-36:], "bilan humain provisoire : 1 impliqué")
    vue(page, "saisie")
    page.locator("#etat .chip[data-v=IMP]").click()   # retire la catégorie
    puce(page, "aggrav", "ACR")
    verifier("SAP écrit — ACR coché dans « constaté sur place »", message(page, "ambiance").split("\n")[1],
             "Secours à une victime de sexe masculin, UA, âgée de 30 ans, en ACR, bilan et régulation en cours.")
    vue(page, "saisie")
    ecran(page, "fin")
    for saisi, attendu in (("830", "830"), ("0830", "830"), ("1415", "1415"), ("14:15", "1415"), ("0005", "0005"), ("2560", ""), ("83", "")):
        page.fill("#gh", saisi)
        verifier(f"Groupe horaire — saisie « {saisi} »", page.evaluate("ghTxt()"), attendu)
    page.locator("#ghNow").click()
    verifier("Groupe horaire — heure actuelle au bon format", str(bool(__import__("re").fullmatch(r"\d{3,4}", page.input_value("#gh")))), "True")
    ecran(page, "bil")
    page.locator("#terrainRas").click()
    verifier("Terrain — « rien à signaler » en un appui",
             json.dumps(page.evaluate("[one('acg'),raw('atcd'),raw('ttt'),raw('allerg')]"), ensure_ascii=False),
             '["non", "Aucun antécédent connu", "Aucun traitement", "Aucune connue"]')
    verifier("Terrain — repris dans la réserve du régulateur",
             json.dumps([x for x in page.evaluate("reserve()") if x["q"] in ("Antécédents", "Traitement", "Allergies", "Anticoagulant / antiagrégant")], ensure_ascii=False),
             '[{"q": "Antécédents", "r": "Aucun antécédent connu"}, {"q": "Traitement", "r": "Aucun traitement"}, {"q": "Anticoagulant / antiagrégant", "r": "Non"}, {"q": "Allergies", "r": "Aucune connue"}]')
    page.fill("#ttt", "Ramipril")
    page.fill("#allerg", "")
    page.locator("#terrainRas").click()
    verifier("Terrain — « rien à signaler » n'écrase pas une saisie", json.dumps(page.evaluate("[raw('ttt'),raw('allerg')]")), '["Ramipril", "Aucune connue"]')
    page.locator("#s5 summary").first.click()
    verifier("Histoire — malaise : trois questions visibles, le reste replié",
             json.dumps(page.evaluate("[[...document.querySelectorAll('#histoire .gl, #histoire label')].map(e=>e.textContent), document.querySelectorAll('#histoirePlus .f').length, document.getElementById('histPlus').open, document.getElementById('negDet').open]"), ensure_ascii=False),
             '[["Perte de connaissance initiale (PCI)", "Nombre d\'épisodes", "Durée de la perte de connaissance", "Chute associée"], 5, false, false]')
    for g, t in (("h_pc", "Oui, brève, reprise spontanée"), ("h_nb", "Deux"), ("h_duree", "Moins d'une minute"), ("h_chute", "Chute sans blessure")):
        page.locator(f"#{g} .chip", has_text=t).first.click()
    verifier("Histoire — malaise : contenu", page.evaluate("histoire()"),
             "perte de connaissance brève avec retour spontané, deux épisodes, durée inférieure à une minute, chute sans traumatisme.")
    puce(page, "pup", "Inégales")
    verifier("Pupilles — anomalie reprise dans l'annonce SAMU", str("anisocorie" in page.evaluate("bAnnonce()").lower()), "True")
    verifier("Pupilles — terme expliqué sous l'annonce", str(any("anisocorie" in g for g in page.evaluate("gloses(bAnnonce())"))), "True")
    page.fill("#spo2", "92"); page.fill("#o2", "9"); page.select_option("#disp", "masque à haute concentration")
    verifier("Oxygène — formulation dans l'annonce", str("sous 9 litres au masque à haute concentration" in page.evaluate("bAnnonce()")), "True")
    page.fill("#histlibre", "Malaise au lever, sans perte de connaissance")
    verifier("Histoire — la phrase dictée arrive dans la réserve",
             json.dumps([x for x in page.evaluate("reserve()") if x["q"] == "Complément"], ensure_ascii=False),
             '[{"q": "Complément", "r": "Malaise au lever, sans perte de connaissance"}]')
    with page.expect_file_chooser() as fc:
        page.locator("#phOrdo").click()
    verifier("Photo d'ordonnance — bouton sous les traitements : ouvre l'appareil photo", str(fc.value is not None), "True")
    verifier("Photo d'ordonnance — rubrique ouverte, en mode ordonnance, placée après le terrain",
             json.dumps(page.evaluate("[document.getElementById('s9').open, one('phmode'), !!(document.getElementById('ttt').compareDocumentPosition(document.getElementById('s9')) & 4), !!(document.getElementById('s9').compareDocumentPosition(document.getElementById('teg')) & 4)]")),
             '[true, "ordo", true, true]')
    verifier("Nouvelle intervention — champs du compte rendu vidés",
             json.dumps(page.evaluate("[raw('gestes'),raw('hdc'),raw('crLib'),raw('devPrec'),one('devenir'),one('medqui'),multi('actFin').length,raw('smurVille')]")),
             '["", "", "", "", "", "", 0, "Cognac"]')
    page.close()

    # ───── 5. Non-régression : l'annonce SAMU ne doit pas avoir bougé ─────
    def annonce(url):
        page, err = ouvrir(nav, url)
        nature(page, "Douleur thoracique")
        victime(page, 58, "Homme")
        page.fill("#commune", "Javrezac")
        ecran(page, "bil")
        puce(page, "delaic", "30 min")
        for i, v in {"spo2": "96", "fc": "104", "fr": "18", "pas": "145", "pad": "85"}.items():
            page.fill("#" + i, v)
        # puces situées dans une rubrique repliée : appui déclenché directement
        for g, t in (("h_siege", "Milieu de la poitrine"), ("h_type", "Serrement, étau"), ("h_irr", "Bras gauche")):
            page.evaluate("([g,t])=>[...document.querySelectorAll('#'+g+' .chip')].find(c=>c.textContent===t).click()", [g, t])
        r = page.evaluate("[bAnnonce(), JSON.stringify(reserve())]")
        page.close()
        return r, err
    (a1, e1), (a2, e2) = annonce(ANCIEN), annonce(NOUVEAU)
    verifier("Annonce SAMU identique à la version précédente", a2[0], a1[0])
    verifier("Réserve SAMU identique à la version précédente", a2[1], a1[1])
    verifier("Annonce SAMU non vide", str(len(a2[0]) > 80), "True")
    verifier("Aucune erreur JavaScript (scénario 5)", json.dumps(e1 + e2), "[]")

    # ───── 6. Radio : architecture d'origine, comparée à la version en ligne ─────
    def radio(url):
        R = {}
        page, err = ouvrir(nav, url)
        # état de départ, sans rien saisir
        R["vide ambiance"] = message(page, "ambiance", "radio")
        nature(page, "Douleur thoracique")
        victime(page, 26, "Femme")
        page.fill("#commune", "Javrezac")
        page.locator("#etat .chip[data-v=UR]").click()
        assurer(page, "ctxlieu", "Domicile")
        puce(page, "aggrav", "Relevage difficile")
        R["SAP ambiance"] = message(page, "ambiance", "radio")
        R["SAP ambiance — contrôles"] = page.locator("#wC").inner_text()
        vue(page, "saisie")
        page.locator("#renf .chip", has_text="SMUR").first.click()
        puce(page, "adrind", "Adresse indiquée au départ")
        page.fill("#adresse", "12 rue des Vignes")
        puce(page, "actS", "Procédons à la RCP")
        page.locator("#codDet summary").click()
        puce(page, "qual", "En ACR")
        page.locator("#addxv").click()
        page.locator("#xv select[data-xk=qualif]").select_option("victime indemne")
        page.locator("#xv select[data-xk=gravite]").select_option("")
        page.fill("#faisMan", "Protection thermique de la victime")
        R["SAP ambiance ACR"] = message(page, "ambiance", "radio")
        R["SAP ambiance ACR — contrôles"] = page.locator("#wC").inner_text()
        vue(page, "saisie")
        ecran(page, "fin")
        page.fill("#vect", "VSAV")
        page.fill("#dest", "CH Cognac")
        R["_cr_sap"] = message(page, "cr", "radio")
        # routier
        vue(page, "saisie")
        page.locator("#rst").click()
        page.locator("#rst").click()
        page.locator("#typeSeg button[data-t=ROUTIER]").click()
        R["Routier vide"] = message(page, "ambiance", "radio")
        vue(page, "saisie")
        victime(page, 40, "Homme")
        page.fill("#commune", "Châteaubernard")
        puce(page, "adrind", "Adresse indiquée au départ")  # décoche : le champ adresse apparaît dans l'ancienne version
        page.fill("#adresse", "RN141, sens Cognac-Angoulême, PR 12")
        page.locator(".vtile[data-veh=vl]").click()
        puce(page, "energ", "Électrique")
        page.fill("#antag", "un poids lourd")
        puce(page, "charg", "Chargement endommagé")
        puce(page, "chargRisk", "Risques particuliers")
        page.fill("#chargPrec", "Fuite d'hydrocarbures")
        page.locator("#etat .chip[data-v=UA]").click()
        puce(page, "aggrav", "Incarcérée")
        page.locator("#codDet summary").click()
        page.locator("#addxv").click()
        page.locator("#xv select[data-xk=sexe]").select_option("féminin")
        page.locator("#xv input[data-xk=age]").fill("35")
        page.locator("#xv input[data-xk=vecteur]").fill("VSAV 2")
        page.locator("#xv input[data-xk=ch]").fill("CH Cognac")
        puce(page, "actR", "Sécurisation du site")
        R["Routier ambiance"] = message(page, "ambiance", "radio")
        R["Routier ambiance — contrôles"] = page.locator("#wC").inner_text()
        vue(page, "saisie")
        ecran(page, "fin")
        page.fill("#vect", "SMUR")
        page.fill("#dest", "CH Angoulême")
        R["Routier compte rendu"] = message(page, "cr", "radio")
        R["_cr_routier_controles"] = page.locator("#wC").inner_text()
        page.close()
        return R, err
    (r1, e1), (r2, e2) = radio(ANCIEN), radio(NOUVEAU)
    for k in r1:
        if not k.startswith("_"):
            # la référence ne plaçait pas la catégorie après le sexe et la répétait dans le bilan : on compare hors catégorie
            sans = lambda t: re.sub(r",? \b(UA|UR)\b,?", "", t)
            verifier("Radio inchangée (hors place de la catégorie) — " + k, sans(r2[k]), sans(r1[k]))
    verifier("Radio — catégorie après le sexe", r2["SAP ambiance"].split("\n")[3],
             "Nous sommes confrontés à une douleur thoracique chez une femme, UR, de 26 ans à son domicile, relevage difficile ; bilan humain provisoire : 1 malade")
    verifier("Radio — compte rendu SAP : le devenir remplace l'action en cours", r2["_cr_sap"],
             "CODIS 16 de VSAV 1 Cognac — compte rendu\n"
             "Je demande : SMUR\n"
             "Opération de secours sur la commune de Javrezac à l'adresse : 12 rue des Vignes\n"
             "Nous sommes confrontés à une douleur thoracique chez une femme, UR, de 26 ans à son domicile, relevage difficile ; bilan humain définitif : 1 victime en ACR UR, 1 victime indemne\n"
             "La victime est transportée par VSAV sur CH Cognac")
    print("\n  Exemple, message radio conservé :\n    " + r2["SAP ambiance"].replace("\n", "\n    "))
    verifier("Aucune erreur JavaScript (scénario 6)", json.dumps(e1 + e2), "[]")

    # Bascule Radio / Écrit : par défaut radio, retour à radio à chaque nouvelle intervention
    page, err = ouvrir(nav, NOUVEAU)
    vue(page, "codis")
    verifier("Support par défaut : radio", page.evaluate("S.sup"), "radio")
    page.locator("#supSeg button[data-s=ecrit]").click()
    verifier("Bascule vers l'écrit", page.locator("#out").input_value().split("\n")[1][:10], "Secours à ")
    page.reload()
    page.wait_for_selector("#ngrid button", state="attached")
    verifier("Support mémorisé au rechargement", page.evaluate("S.sup"), "ecrit")
    page.locator("#rst").click()
    page.locator("#rst").click()
    verifier("Nouvelle intervention : retour à la radio", page.evaluate("S.sup"), "radio")
    page.close()

    nav.close()

print()
print("RÉSULTAT :", "tous les tests passent" if not echecs else f"{len(echecs)} échec(s) : " + " | ".join(echecs))
sys.exit(1 if echecs else 0)
