"""Tests de l'interface de messages-ops.html : accueil par message, un écran par message, message en bas de l'écran.

Lancement, depuis la racine du dépôt :  python3 tests/test_interface.py
Référence : tests/reference-2026.11.23g.html, dernière version à onglets. Le moteur de rédaction n'a pas changé
avec la nouvelle interface : à saisie égale, les deux fichiers doivent écrire le même message.
"""
import sys, json
from pathlib import Path
from playwright.sync_api import sync_playwright

ICI = Path(__file__).resolve().parent
V1 = (ICI / "reference-2026.11.23g.html").as_uri()
V2 = (ICI.parent / "messages-ops.html").as_uri()
echecs = []


def verifier(nom, obtenu, attendu):
    ok = obtenu == attendu
    print(("OK   " if ok else "ÉCHEC") + " — " + nom)
    if not ok:
        echecs.append(nom)
        print("  attendu : " + str(attendu).replace("\n", "\n            "))
        print("  obtenu  : " + str(obtenu).replace("\n", "\n            "))


def ouvrir(nav, url, ctx=None):
    ctx = ctx or nav.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=1)
    page = ctx.new_page()
    erreurs = []
    page.on("pageerror", lambda e: erreurs.append(str(e)))
    page.on("console", lambda m: erreurs.append(m.text) if m.type == "error" and "ERR_FILE_NOT_FOUND" not in m.text else None)
    page.goto(url)
    page.wait_for_selector("#ngrid button", state="attached")
    return page, erreurs, ctx


def saisir_arrivee(page):
    """La même saisie sur les deux versions : douleur thoracique, femme de 26 ans, UR, Javrezac, SMUR demandé."""
    page.locator("#ngrid button", has_text="Douleur thoracique").first.click()
    page.fill("#age", "26")
    page.locator("#sxSeg button[data-s=Femme]").click()
    page.locator("#etat .chip[data-v=UR]").click()
    page.fill("#commune", "Javrezac")
    # victime à l'adresse du départ : à cocher dans le programme, déjà cochée dans la référence
    page.evaluate("(()=>{const c=document.querySelector('#adrind .chip');if(c.getAttribute('aria-pressed')!=='true')c.click();})()")
    page.locator("#ctxlieu .chip", has_text="Domicile").first.click()
    page.locator("#surlieux .chip", has_text="Police municipale").first.click()
    page.evaluate("document.querySelector('#renf .chip[data-r=\"SMUR\"]').click()")
    page.locator("#actS .chip", has_text="Bilan").first.click()


def visible(page, sel):
    return page.locator(sel).first.is_visible()


with sync_playwright() as pw:
    nav = pw.chromium.launch(channel="chrome")

    # ── référence : ce que la version actuelle écrit pour cette saisie
    p1, e1, _ = ouvrir(nav, V1)
    saisir_arrivee(p1)
    p1.locator(".tab[data-v=codis]").click()
    ref = {}
    for sup in ("radio", "ecrit"):
        p1.locator(f"#supSeg button[data-s={sup}]").click()
        for m in ("ambiance", "cr"):
            p1.locator(f"#msgSeg button[data-m={m}]").click()
            ref[sup + " " + m] = p1.locator("#out").input_value()
    p1.close()

    # ── accueil
    page, err, ctx = ouvrir(nav, V2)
    verifier("Accueil affiché à l'ouverture", [visible(page, "#v-accueil"), visible(page, "#v-saisie"), visible(page, "#v-codis")], [True, False, False])
    verifier("Quatre messages proposés", page.locator(".carte .ct b").all_inner_texts(), ["Ambiance", "Complément", "Bilan SAMU", "Compte rendu"])
    verifier("États de départ", page.locator(".carte .ce").all_inner_texts(), ["À faire", "Si besoin", "À faire", "À faire"])
    verifier("Le premier message à passer est mis en avant", page.locator(".carte.actif .ct b").all_inner_texts(), ["Ambiance"])
    verifier("Engin et type d'intervention à l'accueil", [visible(page, "#engin"), visible(page, "#typeSeg")], [True, True])
    verifier("Navigation d'origine masquée", [visible(page, ".dock"), visible(page, "#phSeg")], [False, False])

    # ── ambiance : saisie puis message sur le même écran
    page.locator(".carte[data-e=ambiance]").click()
    verifier("Ambiance : saisie et message sur le même écran",
             [visible(page, "#ph-arr"), visible(page, "#ph-bil"), visible(page, "#ph-fin"), visible(page, "#out"), visible(page, "#msgSeg"), visible(page, "#aHome")],
             [True, False, False, True, False, True])
    verifier("Ambiance : titre de l'écran", page.locator(".brand b").inner_text(), "AMBIANCE")
    verifier("Ambiance : étapes numérotées dans l'ordre",
             [t for t in page.locator("#ph-arr .gl").all_text_contents() if t[:1].isdigit()],
             ["1 · Ce que je constate", "2 · La victime", "3 · Où", "4 · Déjà sur les lieux", "5 · Je demande", "6 · Je fais"])
    ordre = page.evaluate("""() => { const y = s => document.querySelector(s).getBoundingClientRect().top;
        return y('#etat') < y('#aggrav') && y('#aggrav') < y('#addxv') && y('#addxv') < y('#commune') && y('#actS') < y('#out'); }""")
    verifier("Ambiance : état de la victime avec la victime, message en bas de page", ordre, True)
    verifier("Rien de coché d'office : ni l'adresse du départ, ni un service sur les lieux",
             page.evaluate("[multi('adrind').length, multi('surlieux').length]"), [0, 0])
    verifier("Sans adresse ni case cochée, le message la réclame",
             ["à l'adresse : [adresse]" in page.locator("#out").input_value(), "Adresse manquante" in page.locator("#wC").inner_text()], [True, True])
    saisir_arrivee(page)
    verifier("Ambiance radio : même message que la version actuelle", page.locator("#out").input_value(), ref["radio ambiance"])
    page.locator("#supSeg button[data-s=ecrit]").click()
    verifier("Ambiance écrite : même message que la version actuelle", page.locator("#out").input_value(), ref["ecrit ambiance"])
    page.locator("#supSeg button[data-s=radio]").click()
    ambiance_passee = page.locator("#out").input_value()
    page.locator("#passeV2").click()
    verifier("Message passé : gardé au journal, bouton de copie à l'accueil",
             [page.evaluate("S.journal.map(m=>m.l)"), page.evaluate("S.journal[0].t") == ambiance_passee, page.locator("#copJ").inner_text()],
             [["Ambiance · radio"], True, "Copier le message passé"])
    verifier("Message passé : retour à l'accueil", [visible(page, "#v-accueil"), visible(page, "#v-saisie")], [True, False])
    verifier("Message passé : l'ambiance est notée, le suivant est mis en avant",
             [page.locator(".carte .ce").all_inner_texts(), page.locator(".carte.actif .ct b").all_inner_texts()],
             [["Passé", "Si besoin", "À faire", "À faire"], ["Bilan SAMU"]])

    # ── compte rendu
    page.locator(".carte[data-e=cr]").click()
    verifier("Compte rendu : saisie de fin, groupe horaire et message",
             [visible(page, "#ph-fin"), visible(page, "#ph-arr"), visible(page, "#ghCBox"), visible(page, "#out"), page.evaluate("S.msg")],
             [True, False, True, True, "cr"])
    verifier("Compte rendu radio : même message que la version actuelle", page.locator("#out").input_value(), ref["radio cr"])
    page.locator("#supSeg button[data-s=ecrit]").click()
    verifier("Compte rendu écrit : même message que la version actuelle", page.locator("#out").input_value(), ref["ecrit cr"])
    page.locator("#supSeg button[data-s=radio]").click()
    page.locator("#aHome").click()

    # ── complément
    page.locator(".carte[data-e=comp]").click()
    verifier("Complément : demande en plus et message, sans la saisie d'arrivée",
             [visible(page, "#compBox"), visible(page, "#v-saisie"), visible(page, "#out"), visible(page, "#passeV2"), page.evaluate("S.msg")],
             [True, False, True, False, "comp"])
    verifier("Complément : catégorie et autres victimes modifiables sur place", [visible(page, "#etat"), visible(page, "#addxv")], [True, True])
    page.locator("#addxv").click()
    verifier("Complément : une victime ajoutée compte pour les messages suivants, sans bilan humain dans le complément",
             [page.evaluate("bilanHumain()"), "Bilan humain" in page.locator("#out").input_value()], ["2 victimes UR", False])
    page.evaluate("document.querySelector('#compRenf .chip').click()")
    page.locator("#compPasse").click()
    page.locator("#aHome").click()
    verifier("Complément passé : compté à l'accueil", page.locator(".carte[data-e=comp] .ce").inner_text(), "1 passé")
    page.locator(".carte[data-e=ambiance]").click()
    ordre = page.evaluate("""() => { const y = s => document.querySelector(s).getBoundingClientRect().top;
        return y('#etat') < y('#aggrav') && y('#aggrav') < y('#addxv') && y('#addxv') < y('#commune'); }""")
    verifier("Retour à l'ambiance : les victimes ont repris leur place, la victime ajoutée est là", [ordre, page.evaluate("S.sapX.length")], [True, 1])
    page.locator("#aHome").click()

    # ── bilan SAMU
    page.locator(".carte[data-e=samu]").click()
    verifier("Bilan SAMU : saisie du bilan, annonce et témoins",
             [visible(page, "#ph-bil"), visible(page, "#scr"), visible(page, ".dock .locks"), visible(page, ".dock .tabs"), visible(page, "#out")],
             [True, True, True, False, False])
    verifier("Bilan SAMU : les sept étapes dans l'ordre de la maquette",
             page.evaluate("""() => Array.from(document.querySelectorAll('#ph-bil > *')).filter(e => !e.hidden && e.offsetParent !== null)
                 .map(e => ((e.querySelector('.sh, summary b, .gl') || {}).textContent || '').replace('verrou', '')).slice(0, 7)"""),
             ["1 · Depuis quand", "2 · Constantes", "3 · Anticoagulant ou antiagrégant", "Examen clinique", "Douleur : PQRST", "Antécédents : MHTAA", "7 · Régulation CRRA 15 : je demande"])
    verifier("Bilan SAMU : examen, douleur et antécédents repliés ; anticoagulant, température et glycémie sous les yeux",
             [visible(page, "#pup"), visible(page, "#pq_r"), visible(page, "#ttt"), visible(page, "#acg"), visible(page, "#temp"), visible(page, "#gly"), visible(page, "#glyu")],
             [False, False, False, True, True, True, True])
    page.locator("#sPQ > summary").click()
    page.locator("#dMh > summary").click()
    verifier("Bilan SAMU : une flèche déplie le PQRST (avec l'échelle de la douleur) et le MHTAA",
             [visible(page, "#pq_p"), visible(page, "#pq_q"), visible(page, "#en"), visible(page, "#hospit"), visible(page, "#fagg"), visible(page, "#allerg")],
             [True, True, True, True, True, True])
    page.locator("#addpq").click()
    page.locator('#pqX input[data-pk=r]').fill("au bras gauche")
    page.locator('#pqX input[data-pk=s]').fill("4")
    verifier("PQRST : une autre douleur s'ajoute avec sa région et sa cotation", page.locator("#pqEtat").inner_text(), "Douleur au bras gauche, cotée 4 sur 10.")
    page.locator('#pqX [data-pd]').click()
    verifier("PQRST : une douleur ajoutée se supprime", [page.locator('#pqX input').count(), page.evaluate("S.pqX.length")], [0, 0])
    page.fill("#en", "6")
    verifier("Bilan SAMU : la ligne repliée résume ce qui est saisi", page.locator("#pqEtat").inner_text(), "Douleur cotée 6 sur 10.")
    page.locator("#passeS").click()
    verifier("Bilan passé : noté à l'accueil", page.locator(".carte .ce").all_inner_texts(), ["Passé", "1 passé", "Passé", "À faire"])
    verifier("Journal : ambiance, complément et bilan, dans l'ordre",
             [page.evaluate("S.journal.map(m=>m.l)"), page.locator("#copJ").inner_text()],
             [["Ambiance · radio", "Complément n° 1 · radio", "Bilan SAMU"], "Copier les 3 messages passés"])

    # ── outils
    page.locator(".acc-outils button[data-e=reglages]").click()
    verifier("Réglages et historique accessibles", [visible(page, "#s10"), visible(page, "#v-saisie")], [True, False])
    page.locator("#aHome").click()
    page.locator(".acc-outils button[data-e=glo]").click()
    verifier("Lexique accessible", visible(page, "#gsearch"), True)
    page.locator("#aHome").click()

    # ── l'accident de la circulation se déclare aussi depuis l'ambiance du secours à personne
    page.locator(".carte[data-e=ambiance]").click()
    verifier("Ambiance SAP : bouton vers le routier, rubriques routières masquées", [visible(page, "#versRoutier"), visible(page, "#vsit"), visible(page, "#axeBox")], [True, False, False])
    page.locator("#versRoutier").click()
    verifier("Accident de la circulation : l'ambiance routier s'ouvre, avec « Dans le véhicule » et les axes fréquents",
             [page.evaluate("S.type"), visible(page, "#sR"), visible(page, "#vsit"), visible(page, "#axeBox"), visible(page, "#versRoutier")],
             ["ROUTIER", True, True, True, False])
    page.locator("#aHome").click()
    page.locator("#typeSeg button[data-t=SAP]").click()
    page.select_option("#engin", "VSR")
    verifier("Engin VSR : l'accueil passe en routier", page.evaluate("S.type"), "ROUTIER")
    page.select_option("#engin", "VSAV 1")
    page.locator("#typeSeg button[data-t=SAP]").click()

    # ── routier depuis l'accueil
    page.locator("#typeSeg button[data-t=ROUTIER]").click()
    page.locator(".carte[data-e=ambiance]").click()
    verifier("Routier : la rubrique accident apparaît dans l'ambiance", [visible(page, "#sR"), visible(page, "#actR")], [True, True])
    page.locator("#aHome").click()
    page.locator("#typeSeg button[data-t=SAP]").click()

    # ── rechargement : l'état est conservé, l'accueil revient
    page.reload()
    page.wait_for_selector("#ngrid button", state="attached")
    verifier("Rechargement : accueil et états conservés",
             [visible(page, "#v-accueil"), page.locator(".carte .ce").all_inner_texts(), page.input_value("#commune")],
             [True, ["Passé", "1 passé", "Passé", "À faire"], "Javrezac"])

    # ── nouvelle intervention
    page.locator("#rst").click()
    page.locator("#rst").click()
    verifier("Nouvelle intervention : tout repart de zéro, à l'accueil",
             [visible(page, "#v-accueil"), page.locator(".carte .ce").all_inner_texts(), page.input_value("#age"), visible(page, "#copJ")],
             [True, ["À faire", "Si besoin", "À faire", "À faire"], "", False])
    page.locator(".acc-outils button[data-e=reglages]").click()
    page.locator("#s10 summary").click()
    archive = page.locator("#hist .hi").first.inner_text()
    verifier("Historique : l'intervention archivée garde tous ses messages passés",
             ["3 MESSAGES PASSÉS" in archive.upper(), "Ambiance · radio" in archive, "Complément n° 1 · radio" in archive, "Bilan SAMU" in archive, ambiance_passee.split("\n")[1] in archive],
             [True, True, True, True, True])
    page.locator("#aHome").click()
    # ── une saisie ancienne restée en mémoire est signalée dès l'accueil
    page.evaluate("document.querySelector('#age').value='40';sauver()")
    # deux heures plus tard : l'horloge de la page rechargée est avancée
    page.add_init_script("(()=>{const r=Date.now.bind(Date);Date.now=()=>r()+2*3600*1000;})()")
    page.reload()
    page.wait_for_selector("#ngrid button", state="attached")
    verifier("Saisie d'une intervention précédente : avertissement visible à l'accueil", [visible(page, "#v-accueil"), visible(page, "#bnPrev")], [True, True])
    page.locator("#bnNew").click()
    verifier("Avertissement : « Nouvelle intervention » remet à zéro", [visible(page, "#bnPrev"), page.input_value("#age")], [False, ""])
    verifier("Aucune erreur JavaScript", json.dumps(err), "[]")

    # ── passage de l'ancienne version à la nouvelle : la saisie et les réglages enregistrés sont repris
    pa, ea, ctx2 = ouvrir(nav, V1)
    pa.fill("#commune", "Cherves-Richemont")
    pa.fill("#age", "63")
    pa.evaluate("document.querySelector('#cis').value='Jarnac';sauver()")
    pa.close()
    pb, eb, _ = ouvrir(nav, V2, ctx2)
    verifier("Reprise des données de l'ancienne version",
             [pb.input_value("#commune"), pb.input_value("#age"), pb.input_value("#cis"), visible(pb, "#v-accueil"), json.dumps(eb)],
             ["Cherves-Richemont", "63", "Jarnac", True, "[]"])
    pb.close()
    nav.close()

print()
print("%d vérification(s) en échec" % len(echecs) if echecs else "Toutes les vérifications passent")
sys.exit(1 if echecs else 0)
