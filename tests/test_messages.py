"""Tests réels du programme Messages ops dans Chrome (clics et saisies comme sur le téléphone).

Lancement, depuis la racine du dépôt :  python3 tests/test_messages.py
Prérequis : Python 3, le paquet « playwright » et Google Chrome installés.

NOUVEAU : le programme du dépôt, messages-ops.html. Depuis le 23/11/2026 son interface est organisée par
          message (accueil, puis un écran par message). Ces tests portent sur le moteur de rédaction : ils
          appellent modeEssai(), qui rend la navigation d'origine (onglets et écrans 1, 2, 3) le temps du test.
          L'interface elle-même est vérifiée par tests/test_interface.py.
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


def adresse_du_depart(page):
    """Depuis le 23/11 (version i), « adresse indiquée au départ » n'est plus cochée d'office.
    Les scénarios ont été écrits pour une victime à l'adresse du départ : ils la cochent à l'ouverture
    et après une remise à zéro. Sans effet sur la référence, où la case est déjà cochée."""
    page.evaluate("(()=>{const c=document.querySelector('#adrind .chip');if(c&&c.getAttribute('aria-pressed')!=='true')c.click();})()")


def incarceree(page):
    """Depuis le 23/11 (version n), « incarcérée » se choisit dans la rubrique « Dans le véhicule » ;
    dans la référence, c'est encore un constat parmi les autres."""
    if page.locator("#vsit").count():
        page.locator("#vsit .chip", has_text="Incarcérée").first.click()
    else:
        page.locator("#aggrav .chip", has_text="Incarcérée").first.click()


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
    page.evaluate("typeof modeEssai==='function'&&modeEssai()")
    adresse_du_depart(page)
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
    verifier("Compte rendu radio — régulation puis transport", "\n".join(message(page, "cr", "radio").split("\n")[2:]),
             "Nous sommes confrontés à une douleur thoracique chez une femme de 26 ans ; bilan humain définitif : 1 victime UR\n"
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
    page.evaluate("typeof modeEssai==='function'&&modeEssai()")
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
             "Opération de secours sur la commune de Gensac la pallue à l'adresse indiquée\n"
             "Nous sommes confrontés à un arrêt cardio-respiratoire chez une femme de 63 ans à son domicile ; bilan humain définitif : 1 victime décédée\n"
             "Sur les lieux : SMUR\n"
             "RCP arrêtée sur décision du médecin du SMUR de COGNAC, qui déclare la victime décédée (DCD) à 11h52. Certificat de décès établi sans obstacle médico-légal. Aucune manœuvre de réanimation engagée par les moyens sapeurs-pompiers.\n"
             "Le corps est laissé à la responsabilité de la famille, qui ne souhaite pas le déplacement d'un élu.\n"
             "Fin d'intervention pour les moyens sapeurs-pompiers")
    verifier("Cas n° 2 — ambiance radio : la nature dit l'ACR, le bilan humain dit UA", message(page, "ambiance", "radio").split("\n")[3],
             "Nous sommes confrontés à un arrêt cardio-respiratoire chez une femme de 63 ans à son domicile ; bilan humain provisoire : 1 victime UA")
    # ACR constaté sur une autre nature : l'état suit le sexe, il ne figure pas au bilan humain
    nature(page, "Chute")
    puce(page, "aggrav", "ACR")
    verifier("Radio — « une femme en ACR, de 63 ans », bilan humain limité à la catégorie", message(page, "ambiance", "radio").split("\n")[3],
             "Nous sommes confrontés à une chute, à domicile. La victime est une femme en ACR, de 63 ans ; bilan humain provisoire : 1 victime UA")
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
             "Nous sommes confrontés à une suspicion intoxication co, à domicile. La première victime est un homme UA de 54 ans, somnolent\nBilan humain provisoire : 1 victime UA, 2 victimes UR\n"
             "En cours de bilan")
    verifier("Cas n° 3 — ambiance écrite", message(page, "ambiance"),
             "Opération de secours sur la commune de CHATEAUBERNARD.\n"
             "Secours à une victime de sexe masculin, UA, âgée de 54 ans, à son domicile, présentant une suspicion intoxication co, somnolente, bilan et régulation en cours.\n"
             "Bilan humain provisoire : 1 victime UA, 2 victimes UR.\n"
             "Je demande : SMUR, Chef de Groupe, GRDF et VSAV supplémentaire.")
    # une demande après l'ambiance : message complémentaire
    vue(page, "codis")
    page.locator("#msgSeg button[data-m=comp]").click()
    verifier("Message complémentaire — rappel de ce qui est déjà demandé", page.locator("#compDeja").inner_text(),
             "Déjà demandé : SMUR, Chef de Groupe, GRDF et VSAV supplémentaire. Inutile de le recocher.")
    page.locator("#compRenf .chip", has_text="Forces de l'ordre").first.click()
    page.locator("#compRenf .chip", has_text="VSAV supplémentaire").first.click()
    page.fill("#compLib", "aggravation du père")
    verifier("Cas n° 3 — message complémentaire radio : seulement la nouvelle demande", message(page, "comp", "radio"),
             "CODIS 16 de VSAV 1 Cognac — message complémentaire\n"
             "Opération de secours sur la commune de Chateaubernard à l'adresse indiquée\n"
             "Je demande : Forces de l'ordre et VSAV supplémentaire\n"
             "Aggravation du père")
    verifier("Cas n° 3 — message complémentaire écrit", message(page, "comp"),
             "Message complémentaire — Opération de secours sur la commune de CHATEAUBERNARD.\n"
             "Je demande : Forces de l'ordre et VSAV supplémentaire.\n"
             "Aggravation du père.")
    verifier("Message complémentaire — la demande initiale n'est pas modifiée",
             message(page, "ambiance", "radio").split("\n")[1], "Je demande : SMUR, Chef de Groupe, GRDF et VSAV supplémentaire")
    page.locator("#msgSeg button[data-m=comp]").click()
    page.locator("#compPasse").click()
    verifier("Message complémentaire — « message passé » : demande enregistrée, zone prête pour la suivante",
             json.dumps(page.evaluate("[S.comp,S.demFaites,raw('compLib')]"), ensure_ascii=False),
             '[[], ["Forces de l\'ordre", "VSAV supplémentaire"], ""]')
    # compte rendu : les renforts sont arrivés, chaque groupe a son transport
    message(page, "cr", "radio")
    verifier("Compte rendu — renforts encore cochés : le programme propose de les dire sur les lieux",
             str("Les renforts demandés sont arrivés" in page.locator("#wC").inner_text()), "True")
    vue(page, "saisie")
    ecran(page, "fin")
    page.locator(".renfArrBox .renfArr").click()
    verifier("Renforts arrivés — passés dans « Sur les lieux », demande remise à zéro",
             json.dumps(page.evaluate("[multi('surlieux'),raw('surlieuxLib'),S.renf.SAP]"), ensure_ascii=False),
             '[["SMUR", "forces de l\'ordre", "chef de groupe", "GRDF"], "2 VSAV supplémentaires", ["secours suffisants"]]')
    ecran(page, "arr")
    page.fill("#surlieuxLib", "VSAV de Jarnac")
    ecran(page, "fin")
    page.fill("#gh", "1310")
    puce(page, "finInter", "Intervention terminée")
    puce(page, "actFin", "Régulation CRRA 15")
    puce(page, "devenir", "Transportée")
    page.fill("#vect", "SMUR")
    page.fill("#dest", "CH Angoulême")
    page.locator("#trX input[data-xk=vecteur]").fill("VSAV de Jarnac")
    page.locator("#trX input[data-xk=ch]").fill("CH Cognac")
    verifier("Cas n° 3 — compte rendu écrit", message(page, "cr"),
             "GH 1310 — Opération de secours sur la commune de CHATEAUBERNARD, à l'adresse indiquée.\n"
             "À notre arrivée, nous sommes confrontés à une victime de sexe masculin, UA, âgée de 54 ans, à son domicile, présentant une suspicion intoxication co, somnolente.\n"
             "Bilan humain définitif : 1 victime UA, 2 victimes UR.\n"
             "Sur les lieux : SMUR, forces de l'ordre, chef de groupe, GRDF et VSAV de Jarnac.\n"
             "La régulation CRRA 15 a été effectuée et la première victime, de sexe masculin, UA, est transportée par SMUR sur CH Angoulême. 2 victimes UR sont transportées par VSAV de Jarnac sur CH Cognac.\n"
             "Fin d'intervention pour les moyens sapeurs-pompiers.")
    verifier("Cas n° 3 — compte rendu radio : plus de demande, on dit qui était là", message(page, "cr", "radio"),
             "CODIS 16 de VSAV 1 Cognac — compte rendu, groupe horaire 1310\n"
             "Opération de secours sur la commune de Chateaubernard à l'adresse indiquée\n"
             "Nous sommes confrontés à une suspicion intoxication co, à domicile. La première victime est un homme UA de 54 ans, somnolent\nBilan humain définitif : 1 victime UA, 2 victimes UR\n"
             "Sur les lieux : SMUR, forces de l'ordre, chef de groupe, GRDF et VSAV de Jarnac\n"
             "Après régulation CRRA 15, la première victime, de sexe masculin, UA, est transportée par SMUR sur CH Angoulême\n"
             "2 victimes UR sont transportées par VSAV de Jarnac sur CH Cognac\n"
             "Fin d'intervention pour les moyens sapeurs-pompiers")
    verifier("Cas n° 3 — compte rendu cohérent", page.locator("#wC").inner_text().strip(), "Message cohérent. Ordre et contenu conformes.")
    # persistance du transport des autres victimes
    page.reload()
    page.wait_for_selector("#ngrid button", state="attached")
    page.evaluate("typeof modeEssai==='function'&&modeEssai()")
    verifier("Transport des autres victimes — conservé au rechargement",
             json.dumps(page.evaluate("[S.sapX[0].vecteur,S.sapX[0].ch,document.querySelector('#trX input[data-xk=vecteur]').value]")),
             '["VSAV de Jarnac", "CH Cognac", "VSAV de Jarnac"]')
    verifier("Aucune erreur JavaScript (cas n° 3)", json.dumps(err), "[]")
    page.close()

    # Cas n° 5 du 23/11 : deux victimes de même catégorie, chacune vers un hôpital différent
    page, err = ouvrir(nav, NOUVEAU)
    nature(page, "Chute")
    victime(page, 58, "Homme")
    page.fill("#commune", "Merpins")
    page.locator("#etat .chip[data-v=UR]").click()
    page.locator("#addxv").click()
    page.locator("#xv select[data-xk=sexe]").select_option("féminin")
    ecran(page, "fin")
    page.fill("#vect", "SMUR")
    page.fill("#dest", "CH Angoulême")
    page.locator("#trX input[data-xk=vecteur]").fill("VSAV 2")
    page.locator("#trX input[data-xk=ch]").fill("CH Cognac")
    puce(page, "finInter", "Intervention terminée")
    page.fill("#gh", "1510")
    cr = message(page, "cr", "radio").split("\n")
    verifier("Cas n° 5 — compte rendu radio : chaque victime désignée par son sexe", "\n".join(cr[-3:]),
             "La première victime, de sexe masculin, UR, est transportée par SMUR sur CH Angoulême\n"
             "La deuxième victime, de sexe féminin, UR, est transportée par VSAV 2 sur CH Cognac\n"
             "Fin d'intervention pour les moyens sapeurs-pompiers")
    cr = message(page, "cr").split("\n")
    verifier("Cas n° 5 — compte rendu écrit : même précision", cr[-2],
             "La première victime, de sexe masculin, UR, est transportée par SMUR sur CH Angoulême. La deuxième victime, de sexe féminin, UR, est transportée par VSAV 2 sur CH Cognac.")
    verifier("Cas n° 5 — bilan humain inchangé : deux victimes UR", [l for l in cr if l.startswith("Bilan humain")][0], "Bilan humain définitif : 2 victimes UR.")
    # 23/11, version j : état de la victime en texte libre, anticoagulant, vecteurs et destinations en un appui
    vue(page, "saisie")
    ecran(page, "arr")
    page.fill("#aggravlib", "Une plaie du cuir chevelu avec saignement important")
    verifier("État libre commençant par un article : introduit par « présentant » (radio)",
             "La première victime est un homme UR de 58 ans, présentant une plaie du cuir chevelu avec saignement important. La deuxième victime est une femme UR" in message(page, "ambiance", "radio"), True)
    verifier("État libre commençant par un article : « présentant » (écrit, après une chute)",
             "à la suite d'une chute, présentant une plaie du cuir chevelu avec saignement important" in message(page, "ambiance"), True)
    vue(page, "saisie")
    page.fill("#aggravlib", "présente une plaie")
    verifier("État libre : un « présente » saisi par habitude n'est pas doublé",
             "UR de 58 ans, présentant une plaie. La deuxième victime" in message(page, "ambiance", "radio"), True)
    vue(page, "saisie")
    page.fill("#aggravlib", "Agité")
    verifier("État libre sans article (adjectif) : laissé tel quel", "UR de 58 ans, agité. La deuxième victime" in message(page, "ambiance", "radio"), True)
    vue(page, "saisie")
    page.fill("#aggravlib", "")
    ecran(page, "bil")
    page.evaluate("(()=>{const c=document.querySelector('#acg .chip[data-v=oui]');if(c.getAttribute('aria-pressed')!=='true')c.click();})()")
    verifier("Anticoagulant : absent des messages CODIS, présent dans l'annonce SAMU",
             ["anticoagulant" in message(page, "cr", "radio").lower(), "anticoagulant" in message(page, "cr").lower(), "anticoagulant" in page.evaluate("bAnnonce()").lower()],
             [False, False, True])
    annonce = page.evaluate("bAnnonce()")
    verifier("Annonce SAMU : l'anticoagulant a sa phrase et son sujet",
             ["Victime sous anticoagulant." in annonce, ". Sous anticoagulant" in annonce, annonce.index("pour chute") < annonce.index("Victime sous anticoagulant.")],
             [True, False, True])
    page.evaluate("document.querySelector('#h_les').value='douleur au dos et plaie du cuir chevelu avec saignement important';document.querySelector('#en').value='7';rendre()")
    verifier("Annonce SAMU : la cotation suit le mot « douleur », pas toute la description",
             "douleur cotée 7 sur 10 au dos et plaie du cuir chevelu avec saignement important" in page.evaluate("bAnnonce()"), True)
    vue(page, "saisie")
    ecran(page, "fin")
    page.locator('.pk[data-pour=vect] button', has_text="Hélitransport").click()
    page.locator('.pk[data-pour=dest] button', has_text="Urgences CH Bordeaux").click()
    page.locator('#trX .pk[data-xk=vecteur] button', has_text="VSAV").click()
    page.locator('#trX .pk[data-xk=ch] button', has_text="Urgences pédiatriques CH Saintes").click()
    cr = message(page, "cr", "radio").split("\n")
    verifier("Vecteurs et destinations en un appui", "\n".join(cr[-3:-1]),
             "La première victime, de sexe masculin, UR, est transportée par hélicoptère sur les urgences du CH Bordeaux\n"
             "La deuxième victime, de sexe féminin, UR, est transportée par VSAV sur les urgences pédiatriques du CH Saintes")
    # 23/11, version k : une précision sous la tuile complète la nature dans tous les messages
    vue(page, "saisie")
    ecran(page, "arr")
    page.fill("#natprec", "D'une échelle, d'environ 3 mètres")
    verifier("Précision de la nature — radio",
             "Nous sommes confrontés à une chute d'une échelle, d'environ 3 mètres. La première victime est un homme UR de 58 ans" in message(page, "ambiance", "radio"), True)
    verifier("Précision de la nature — écrit",
             "à la suite d'une chute d'une échelle, d'environ 3 mètres" in message(page, "ambiance"), True)
    verifier("Précision de la nature — annonce SAMU", "pour chute d'une échelle, d'environ 3 mètres" in page.evaluate("bAnnonce()"), True)
    vue(page, "saisie")
    nature(page, "Malaise")
    verifier("Précision de la nature — effacée quand la nature change, case toujours proposée",
             [page.input_value("#natprec"), page.locator("#natprec").is_visible()], ["", True])
    nature(page, "Préciser")
    verifier("Précision de la nature — masquée en saisie libre", page.locator("#natprec").is_visible(), False)
    # 23/11, version m : bilan SAMU — PQRST, unité de glycémie, MHTAA, nouvelles demandes
    page.evaluate("""() => { $('#pq_r').value='Au poignet gauche'; $('#pq_p').value="Par le mouvement"; $('#en').value='8';
        document.querySelector('#pq_q .chip[data-v="pulsatile"]').click(); rendre(); }""")
    verifier("PQRST : la douleur a sa phrase dans l'annonce",
             "Douleur pulsatile au poignet gauche, cotée 8 sur 10, provoquée par le mouvement." in page.evaluate("bAnnonce()"), True)
    page.evaluate("""() => { $('#pq_r').value=''; $('#pq_p').value=''; document.querySelector('#pq_q .chip[data-v="pulsatile"]').click(); rendre(); }""")
    verifier("PQRST : cotée seule, la douleur est quand même annoncée", "Douleur cotée 8 sur 10." in page.evaluate("bAnnonce()"), True)
    verifier("Glycémie : même seuil dans les trois unités",
             json.dumps(page.evaluate("""() => [['0,6','g'],['60','mg'],['3,3','mmol'],['5,2','mmol'],['45','mg']].map(x => { $('#gly').value=x[0]; $('#glyu').value=x[1]; return qual('gly',glyGL()).m; })"""), ensure_ascii=False),
             '["hypoglycémie à 0,6 gramme par litre", "hypoglycémie à 60 milligrammes par décilitre", "hypoglycémie à 3,3 millimoles par litre", "glycémie normale", "hypoglycémie sévère à 45 milligrammes par décilitre"]')
    page.evaluate("""() => { $('#gly').value=''; $('#glyu').value='g'; $('#hospit').value='Pontage en 2019';
        document.querySelector('#fagg .chip[data-v="tabagisme"]').click(); document.querySelector('#dem .chip[data-v="la mise en œuvre du protocole anti-douleur"]').click(); rendre(); }""")
    verifier("MHTAA : hospitalisations et facteurs aggravants dans les réponses de réserve",
             json.dumps(page.evaluate("reserve().filter(x=>/Hospitalisations|Facteurs/.test(x.q)).map(x=>x.q+' : '+x.r)"), ensure_ascii=False),
             '["Hospitalisations : Pontage en 2019", "Facteurs aggravants : tabagisme"]')
    verifier("Demande au SAMU : protocole anti-douleur",
             page.evaluate("bAnnonce()").endswith("Je demande la mise en œuvre du protocole anti-douleur."), True)
    # 23/11, version m : les victimes suivantes sont décrites comme la première, avant le bilan humain
    vue(page, "saisie")
    nature(page, "Chute")
    page.locator("#xv input[data-xk=age]").fill("72")
    page.locator("#xv input[data-xk=pb]").fill("Une douleur à la poitrine")
    page.locator("#xv select[data-xk=gravite]").select_option("UA")
    verifier("Victimes suivantes décrites avant le bilan humain — radio",
             "La première victime est un homme UR de 58 ans. La deuxième victime est une femme UA de 72 ans, présentant une douleur à la poitrine\nBilan humain définitif : 1 victime UA, 1 victime UR" in message(page, "cr", "radio"), True)
    verifier("Victimes suivantes décrites avant le bilan humain — écrit",
             [l for l in message(page, "cr").split("\n") if l.startswith("À notre arrivée")][0].endswith("La deuxième victime est de sexe féminin, UA, âgée de 72 ans, présentant une douleur à la poitrine."), True)
    verifier("Message complémentaire : plus de bilan humain",
             ["Bilan humain" in message(page, "comp", "radio"), "Bilan humain" in message(page, "comp")], [False, False])
    verifier("Aucune erreur JavaScript (cas n° 5)", json.dumps(err), "[]")
    page.close()

    # Cas n° 6 du 23/11 au soir : chaque victime décrite avec sa catégorie, puis le bilan humain sur sa ligne
    page, err = ouvrir(nav, NOUVEAU)
    nature(page, "Chute")
    page.fill("#natprec", "dans un escalier, d'une hauteur de 2 m environ")
    victime(page, 9, "Femme")
    page.fill("#commune", "Chateaubernard")
    page.locator("#etat .chip[data-v=UR]").click()
    puce(page, "ctxlieu", "ERP")
    page.fill("#aggravlib", "déformation au poignet gauche")
    page.locator("#addxv").click()
    page.locator("#xv select[data-xk=gravite]").select_option("UA")
    page.locator("#xv select[data-xk=sexe]").select_option("masculin")
    page.locator("#xv input[data-xk=age]").fill("72")
    page.locator("#xv input[data-xk=pb]").fill("douleur à la poitrine")
    cr = message(page, "cr", "radio").split("\n")
    verifier("Cas n° 6 — compte rendu radio : les deux victimes décrites, puis le bilan humain", "\n".join(cr[2:4]),
             "Nous sommes confrontés à une chute dans un escalier, d'une hauteur de 2 m environ, dans un établissement recevant du public. "
             "La première victime est une fille UR de 9 ans, présentant une déformation au poignet gauche. "
             "La deuxième victime est un homme UA de 72 ans, présentant une douleur à la poitrine\n"
             "Bilan humain définitif : 1 victime UA, 1 victime UR")
    verifier("Cas n° 6 — une seule victime : rien ne change",
             page.evaluate("(()=>{const x=S.sapX;S.sapX=[];const t=buildCodis();S.sapX=x;return t.split('\\n')[2];})()"),
             "Nous sommes confrontés à une chute dans un escalier, d'une hauteur de 2 m environ, dans un établissement recevant du public. La victime est une fille de 9 ans, présentant une déformation au poignet gauche ; bilan humain définitif : 1 victime UR")
    verifier("Aucune erreur JavaScript (cas n° 6)", json.dumps(err), "[]")
    page.close()

    # Cas n° 4 du 23/11 : événement, plusieurs victimes, complément de demande, compte rendu
    page, err = ouvrir(nav, NOUVEAU)
    nature(page, "Préciser")
    page.fill("#natlib", "effondrement d'une estrade à la salle des fêtes")
    victime(page, 38, "Femme")
    page.locator("#etat .chip[data-v=UA]").click()
    page.locator("#addxv").click()
    page.locator("#addxv").click()
    page.locator("#xv input[data-xk=nb]").nth(0).fill("2")
    page.locator("#xv input[data-xk=nb]").nth(1).fill("3")
    page.locator("#xv select[data-xk=gravite]").nth(1).select_option("IMP")
    page.fill("#commune", "Cherves Richemont")
    puce(page, "ctxlieu", "ERP")
    puce(page, "aggrav", "Inconsciente")
    puce(page, "surlieux", "Police municipale")
    for r in ("SMUR", "Chef de Groupe", "VSAV supplémentaire"):
        page.evaluate("r=>document.querySelector('#renf .chip[data-r=\"'+r+'\"]').click()", r)
    puce(page, "actS", "Poursuivons reconnaissance")
    verifier("Cas n° 4 — ambiance radio : l'événement et son lieu, puis la victime", message(page, "ambiance", "radio"),
             "CODIS 16 de VSAV 1 Cognac\n"
             "Je demande : SMUR, Chef de Groupe et VSAV supplémentaire\n"
             "Opération de secours sur la commune de Cherves Richemont à l'adresse indiquée\n"
             "Nous sommes confrontés à un effondrement d'une estrade à la salle des fêtes, dans un établissement recevant du public. La première victime est une femme UA de 38 ans, inconsciente\nBilan humain provisoire : 1 victime UA, 2 victimes UR, 3 victimes impliquées\n"
             "Sur les lieux : police municipale\n"
             "Poursuivons reconnaissance, en cours de bilan")
    verifier("Cas n° 4 — ambiance écrite, même cohérence", message(page, "ambiance"),
             "Opération de secours sur la commune de CHERVES RICHEMONT.\n"
             "Secours à une victime de sexe féminin, UA, âgée de 38 ans, dans un établissement recevant du public, à la suite d'un effondrement d'une estrade à la salle des fêtes, inconsciente, reconnaissance en cours, bilan et régulation en cours.\n"
             "Bilan humain provisoire : 1 victime UA, 2 victimes UR, 3 victimes impliquées.\n"
             "Sur les lieux : police municipale.\n"
             "Je demande : SMUR, Chef de Groupe et VSAV supplémentaire.")
    # temps 2 : une victime de plus, demande complémentaire
    vue(page, "saisie")
    page.locator("#xv input[data-xk=nb]").nth(0).fill("3")
    vue(page, "codis")
    page.locator("#msgSeg button[data-m=comp]").click()
    page.locator("#compRenf .chip", has_text="Forces de l'ordre").first.click()
    page.locator("#compRenf .chip", has_text="VSAV supplémentaire").first.click()
    page.fill("#compLib", "Après dégagement de l'estrade, avons découvert une troisième victime, UR")
    verifier("Cas n° 4 — message complémentaire radio", message(page, "comp", "radio"),
             "CODIS 16 de VSAV 1 Cognac — message complémentaire\n"
             "Opération de secours sur la commune de Cherves Richemont à l'adresse indiquée\n"
             "Je demande : Forces de l'ordre et VSAV supplémentaire\n"
             "Après dégagement de l'estrade, avons découvert une troisième victime, UR")
    page.locator("#compPasse").click()
    # temps 3 : tout le monde est arrivé, chacun a son devenir
    vue(page, "saisie")
    ecran(page, "fin")
    page.locator(".renfArrBox .renfArr").click()
    page.fill("#gh", "1545")
    puce(page, "finInter", "Intervention terminée")
    puce(page, "actFin", "Régulation CRRA 15")
    puce(page, "devenir", "Transportée")
    page.fill("#vect", "SMUR")
    page.fill("#dest", "Urgences CH Angoulême")
    page.locator("#trX input[data-xk=vecteur]").nth(0).fill("VSAV Cognac, Jarnac et Segonzac")
    page.locator("#trX input[data-xk=ch]").nth(0).fill("Urgences CH Cognac")
    page.locator("#trX input[data-xk=devenir]").nth(1).fill("Restent sur place, prises en charge par l'association.")
    verifier("Cas n° 4 — compte rendu radio", message(page, "cr", "radio"),
             "CODIS 16 de VSAV 1 Cognac — compte rendu, groupe horaire 1545\n"
             "Opération de secours sur la commune de Cherves Richemont à l'adresse indiquée\n"
             "Nous sommes confrontés à un effondrement d'une estrade à la salle des fêtes, dans un établissement recevant du public. La première victime est une femme UA de 38 ans, inconsciente\nBilan humain définitif : 1 victime UA, 3 victimes UR, 3 victimes impliquées\n"
             "Sur les lieux : SMUR, forces de l'ordre, chef de groupe, police municipale et 2 VSAV supplémentaires\n"
             "Après régulation CRRA 15, la première victime, de sexe féminin, UA, est transportée par SMUR sur Urgences CH Angoulême\n"
             "3 victimes UR sont transportées par VSAV Cognac, Jarnac et Segonzac sur Urgences CH Cognac\n"
             "3 victimes impliquées restent sur place, prises en charge par l'association\n"
             "Fin d'intervention pour les moyens sapeurs-pompiers")
    verifier("Cas n° 4 — compte rendu écrit, même cohérence", message(page, "cr"),
             "GH 1545 — Opération de secours sur la commune de CHERVES RICHEMONT, à l'adresse indiquée.\n"
             "À notre arrivée, nous sommes confrontés à une victime de sexe féminin, UA, âgée de 38 ans, dans un établissement recevant du public, à la suite d'un effondrement d'une estrade à la salle des fêtes, inconsciente.\n"
             "Bilan humain définitif : 1 victime UA, 3 victimes UR, 3 victimes impliquées.\n"
             "Sur les lieux : SMUR, forces de l'ordre, chef de groupe, police municipale et 2 VSAV supplémentaires.\n"
             "La régulation CRRA 15 a été effectuée et la première victime, de sexe féminin, UA, est transportée par SMUR sur Urgences CH Angoulême. 3 victimes UR sont transportées par VSAV Cognac, Jarnac et Segonzac sur Urgences CH Cognac. 3 victimes impliquées restent sur place, prises en charge par l'association.\n"
             "Fin d'intervention pour les moyens sapeurs-pompiers.")
    verifier("Aucune erreur JavaScript (cas n° 4)", json.dumps(err), "[]")
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
             "Secours à une victime de sexe masculin, UR, âgée de 82 ans, sur la voie publique, à la suite d'une piqûre de guêpe, inconsciente, relevage difficile, bilan et régulation en cours.")
    # Nourrisson, autre victime
    vue(page, "saisie")
    page.fill("#age", "8")
    page.select_option("#ageu", "mois")
    page.locator("#addxv").click()            # bouton placé sous la victime, sans rien déplier
    page.locator("#addxv").click()
    page.locator("#xv input[data-xk=nb]").nth(1).fill("2")
    page.locator("#xv select[data-xk=gravite]").nth(1).select_option("IMP")
    amb = message(page, "ambiance").split("\n")
    verifier("Nourrisson", amb[1], "Secours à une victime de sexe masculin, UR, âgée de 8 mois, sur la voie publique, à la suite d'une piqûre de guêpe, inconsciente, relevage difficile, bilan et régulation en cours.")
    verifier("Plusieurs victimes — bilan humain récapitulé et regroupé", amb[2], "Bilan humain provisoire : 2 victimes UR, 2 victimes impliquées.")
    verifier("Autres victimes — bouton sous la victime, hors rubrique repliée",
             str(page.evaluate("!document.getElementById('addxv').closest('details') && document.getElementById('age').closest('.sec').contains(document.getElementById('addxv'))")), "True")
    verifier("Aucune erreur JavaScript (scénario 3)", json.dumps(err), "[]")
    page.close()

    # ───── 4 bis. Routier, rédaction du 23/11 au soir : une victime, RN 141, contrôle du VSR ─────
    page, err = ouvrir(nav, NOUVEAU)
    page.locator("#typeSeg button[data-t=ROUTIER]").click()
    victime(page, 40, "Homme")
    page.fill("#commune", "Châteaubernard")
    page.locator(".vtile[data-veh=vl]").click()
    page.fill("#antag", "un poids lourd")
    page.locator("#etat .chip[data-v=UA]").click()
    puce(page, "ctxlieu", "Hors agglomération")
    puce(page, "vsit", "Incarcérée")
    page.evaluate("document.querySelector('#renf .chip[data-r=\"VSR\"]').click()")   # le VSR n'est pas demandé
    page.locator('#axeBox .pk button', has_text="sens Angoulême-Saintes").click()
    page.fill("#hautR", "du PR 12")
    amb = message(page, "ambiance", "radio").split("\n")
    verifier("Routier — ambiance radio : cinétique après la demande, lieu sur la RN 141, victime incarcérée, bilan à quatre catégories", "\n".join(amb[:6]),
             "CODIS 16 de VSAV 1 Cognac\n"
             "Je demande : SMUR\n"
             "Accident à forte cinétique\n"
             "Opération de secours sur la commune de Châteaubernard à l'adresse : RN 141, sens Angoulême-Saintes, à la hauteur du PR 12\n"
             "Nous sommes confrontés à un accident de la circulation hors agglomération mettant en cause un véhicule léger dans une collision frontale contre un poids lourd. La victime est incarcérée\n"
             "Bilan humain provisoire : 1 victime UA")
    verifier("Routier — contrôle : victime incarcérée, VSR ni sur les lieux ni demandé",
             "Victime incarcérée : aucun VSR sur les lieux ni demandé." in page.locator("#wC").inner_text(), True)
    page.locator("#ajVsr").click()
    verifier("Routier — contrôle : un appui ajoute le VSR à la demande, l'alerte disparaît",
             [message(page, "ambiance", "radio").split("\n")[1], page.locator("#wVsr").count()], ["Je demande : SMUR et VSR", 0])
    vue(page, "saisie")
    for choix, attendu in (("Piégée", "La victime est piégée"), ("Restée à bord", "La victime est restée à bord, ni incarcérée ni piégée"), ("Sortie seule", "La victime est sortie seule du véhicule")):
        puce(page, "vsit", choix)
        verifier("Routier — dans le véhicule : " + choix.lower(), message(page, "ambiance", "radio").split("\n")[4].split(". ")[-1], attendu)
        vue(page, "saisie")
    verifier("Routier — écrit : la cinétique en tête de phrase",
             message(page, "ambiance").split("\n")[1],
             "Secours routier pour un accident de la circulation à forte cinétique, hors agglomération, mettant en cause un véhicule léger dans une collision frontale contre un poids lourd. La victime est sortie seule du véhicule.")
    vue(page, "saisie")
    page.select_option("#engin", "VSR")
    puce(page, "vsit", "Incarcérée")
    page.evaluate("document.querySelector('#renf .chip[data-r=\"VSR\"]').click()")
    verifier("Routier — au VSR, pas d'alerte sur le VSR", [message(page, "ambiance", "radio").split("\n")[0], page.locator("#wVsr").count()], ["CODIS 16 de VSR Cognac", 0])
    verifier("Aucune erreur JavaScript (routier, version n)", json.dumps(err), "[]")
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
    incarceree(page)
    puce(page, "adrind", "Adresse indiquée au départ")  # décoche : la localisation est annoncée
    verifier("Ambiance routier — une victime", message(page, "ambiance"),
             "Opération de secours sur la commune de CHÂTEAUBERNARD, RN141, sens Cognac-Angoulême, PR 12.\n"
             "Secours routier pour un accident de la circulation à forte cinétique mettant en cause un véhicule léger électrique dans une collision frontale contre un poids lourd. La victime est incarcérée.\n"
             "Chargement endommagé — risques particuliers liés au chargement : fuite d'hydrocarbures.\n"
             "Bilan provisoire : une victime de sexe masculin, âgée de 40 ans, UA.\n"
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
             "Secours routier pour un accident de la circulation à forte cinétique, hors agglomération, mettant en cause un véhicule léger électrique dans une collision frontale contre un poids lourd, véhicule en contrebas de la chaussée. 1 victime incarcérée.")
    verifier("Ambiance routier — deux victimes", amb[3] + "\n" + amb[4],
             "Bilan provisoire : 1 victime UA, 1 victime UR.\n"
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
             "À notre arrivée, nous sommes confrontés à un accident de la circulation à forte cinétique, hors agglomération, mettant en cause un véhicule léger électrique dans une collision frontale contre un poids lourd, véhicule en contrebas de la chaussée. 1 victime incarcérée. Victime évacuée du véhicule par des témoins. Véhicule sur le toit.\n"
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
    verifier("Radio routier — contexte repris", radio_cr[2],
             "Nous sommes confrontés à un accident de la circulation à forte cinétique, hors agglomération, mettant en cause un véhicule léger électrique dans une collision frontale contre un poids lourd, véhicule en contrebas de la chaussée. 1 victime incarcérée")
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
    verifier("Routier — constats : ACR présent, relevage difficile absent ; « incarcérée » a sa rubrique « Dans le véhicule »",
             json.dumps(page.evaluate("[[...document.querySelectorAll('#aggrav .chip')].map(c=>c.textContent), [...document.querySelectorAll('#vsit .chip')].map(c=>c.textContent)]"), ensure_ascii=False),
             '[["Inconsciente", "ACR", "Détresse vitale", "Hémorragie active", "Accès difficile"], ["Incarcérée", "Piégée", "Restée à bord", "Sortie seule"]]')
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
             "Opération de secours sur la commune de CHÂTEAUBERNARD, [adresse].\n"
             "Secours à une victime malade, bilan et régulation en cours.")
    verifier("Nouvelle intervention — rien de coché pour l'adresse ni pour les services sur les lieux",
             json.dumps(page.evaluate("[multi('adrind').length, multi('surlieux').length]")), "[0, 0]")
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
    verifier("SAP radio — impliqué", message(page, "ambiance", "radio").split("\n")[3].split(" ; ")[1], "bilan humain provisoire : 1 victime impliquée")
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
        R["_vide ambiance"] = message(page, "ambiance", "radio")
        nature(page, "Douleur thoracique")
        victime(page, 26, "Femme")
        page.fill("#commune", "Javrezac")
        page.locator("#etat .chip[data-v=UR]").click()
        assurer(page, "ctxlieu", "Domicile")
        puce(page, "aggrav", "Relevage difficile")
        R["_SAP ambiance"] = message(page, "ambiance", "radio")
        R["_SAP ambiance — contrôles"] = page.locator("#wC").inner_text()
        vue(page, "saisie")
        page.locator("#renf .chip", has_text="SMUR").first.click()
        puce(page, "adrind", "Adresse indiquée au départ")
        page.fill("#adresse", "12 rue des Vignes")
        puce(page, "actS", "Procédons à la RCP")
        page.locator("#codDet summary").click()
        puce(page, "qual", "En ACR")
        page.locator("#addxv").click()
        if page.locator("#xv select[data-xk=qualif]").count():   # la référence demandait une qualification
            page.locator("#xv select[data-xk=qualif]").select_option("victime indemne")
        page.locator("#xv select[data-xk=gravite]").select_option("")
        page.fill("#faisMan", "Protection thermique de la victime")
        R["_SAP ambiance ACR"] = message(page, "ambiance", "radio")
        R["_SAP ambiance ACR — contrôles"] = page.locator("#wC").inner_text()
        vue(page, "saisie")
        ecran(page, "fin")
        page.fill("#vect", "VSAV")
        page.fill("#dest", "CH Cognac")
        R["_cr_sap"] = message(page, "cr", "radio")
        # routier
        vue(page, "saisie")
        page.locator("#rst").click()
        page.locator("#rst").click()
        adresse_du_depart(page)
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
        incarceree(page)
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
    ROUTIER_23N = {
        "Routier vide":
            "CODIS 16 de VSAV 1 Cognac\nJe demande : SMUR et VSR\nAccident à forte cinétique\n"
            "Opération de secours sur la commune de Javrezac à l'adresse indiquée\n"
            "Nous sommes confrontés à un accident de la circulation mettant en cause [véhicule mis en cause] dans une collision frontale\n"
            "Bilan humain provisoire : 1 victime\nNous procédons à la prise en charge de la victime",
        "Routier ambiance":
            "CODIS 16 de VSAV 1 Cognac\nJe demande : SMUR et VSR\nAccident à forte cinétique\n"
            "Opération de secours sur la commune de Châteaubernard à l'adresse : RN141, sens Cognac-Angoulême, PR 12\n"
            "Nous sommes confrontés à un accident de la circulation mettant en cause un véhicule léger électrique dans une collision frontale contre un poids lourd. 1 victime incarcérée\n"
            "Chargement endommagé — risques particuliers liés au chargement : fuite d'hydrocarbures\n"
            "Bilan humain provisoire : 1 victime UA, 1 victime UR\n"
            "Nous procédons à la sécurisation du site et à la prise en charge des victimes",
        "Routier compte rendu":
            "CODIS 16 de VSAV 1 Cognac — compte rendu\n"
            "Opération de secours sur la commune de Châteaubernard à l'adresse : RN141, sens Cognac-Angoulême, PR 12\n"
            "Nous sommes confrontés à un accident de la circulation à forte cinétique mettant en cause un véhicule léger électrique dans une collision frontale contre un poids lourd. 1 victime incarcérée\n"
            "Chargement endommagé — risques particuliers liés au chargement : fuite d'hydrocarbures\n"
            "Bilan humain définitif : 2 victimes — masculin, 40 ans, UA, transporté par SMUR sur CH Angoulême ; féminin, 35 ans, UR, transportée par VSAV 2 sur CH Cognac\n"
            "Nous procédons à la sécurisation du site et à la prise en charge des victimes",
    }
    (r1, e1), (r2, e2) = radio(ANCIEN), radio(NOUVEAU)
    for k in r1:
        if not k.startswith("_"):
            # depuis le 23/11, la demande n'est plus répétée au compte rendu : on retire cette ligne de la référence
            ref = r1[k].split("\n")
            if "compte rendu" in k and not k.endswith("contrôles"):
                ref = [ref[0]] + ref[2:]
            # depuis le 23/11 (version n), le routier a sa propre rédaction : cinétique après la demande,
            # situation dans le véhicule à part, bilan humain limité aux quatre catégories
            verifier("Radio routier — " + k, r2[k], ROUTIER_23N.get(k, "\n".join(ref)))
    verifier("Radio SAP — message vide", r2["_vide ambiance"],
             "CODIS 16 de VSAV 1 Cognac\n"
             "Secours suffisants\n"
             "Opération de secours sur la commune de [commune] à l'adresse indiquée\n"
             "Nous sommes confrontés à [description] ; bilan humain provisoire : 1 victime\n"
             "En cours de bilan")
    verifier("Radio SAP — ambiance", r2["_SAP ambiance"],
             "CODIS 16 de VSAV 1 Cognac\n"
             "Secours suffisants\n"
             "Opération de secours sur la commune de Javrezac à l'adresse indiquée\n"
             "Nous sommes confrontés à une douleur thoracique chez une femme de 26 ans à son domicile, relevage difficile ; bilan humain provisoire : 1 victime UR\n"
             "En cours de bilan")
    verifier("Radio SAP — ambiance, ACR constaté et seconde victime", r2["_SAP ambiance ACR"],
             "CODIS 16 de VSAV 1 Cognac\n"
             "Je demande : SMUR\n"
             "Opération de secours sur la commune de Javrezac à l'adresse : 12 rue des Vignes\n"
             "Nous sommes confrontés à une douleur thoracique, à domicile, relevage difficile. La première victime est une femme UR en ACR, de 26 ans\nBilan humain provisoire : 1 victime UR, 1 victime\n"
             "En cours de bilan, procédons à la RCP, protection thermique de la victime")
    verifier("Radio — compte rendu SAP : le devenir remplace l'action en cours", r2["_cr_sap"],
             "CODIS 16 de VSAV 1 Cognac — compte rendu\n"
             "Opération de secours sur la commune de Javrezac à l'adresse : 12 rue des Vignes\n"
             "Nous sommes confrontés à une douleur thoracique, à domicile, relevage difficile. La première victime est une femme UR en ACR, de 26 ans\nBilan humain définitif : 1 victime UR, 1 victime\n"
             "La première victime, de sexe féminin, UR, est transportée par VSAV sur CH Cognac")
    verifier("Aucune erreur JavaScript (scénario 6)", json.dumps(e1 + e2), "[]")

    # Bascule Radio / Écrit : par défaut radio, retour à radio à chaque nouvelle intervention
    page, err = ouvrir(nav, NOUVEAU)
    vue(page, "codis")
    verifier("Support par défaut : radio", page.evaluate("S.sup"), "radio")
    page.locator("#supSeg button[data-s=ecrit]").click()
    verifier("Bascule vers l'écrit", page.locator("#out").input_value().split("\n")[1][:10], "Secours à ")
    page.reload()
    page.wait_for_selector("#ngrid button", state="attached")
    page.evaluate("typeof modeEssai==='function'&&modeEssai()")
    verifier("Support mémorisé au rechargement", page.evaluate("S.sup"), "ecrit")
    page.locator("#rst").click()
    page.locator("#rst").click()
    verifier("Nouvelle intervention : retour à la radio", page.evaluate("S.sup"), "radio")
    page.close()

    nav.close()

print()
print("RÉSULTAT :", "tous les tests passent" if not echecs else f"{len(echecs)} échec(s) : " + " | ".join(echecs))
sys.exit(1 if echecs else 0)
