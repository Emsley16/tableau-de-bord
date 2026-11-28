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
    # « En cours de bilan » : coché d'office dans la référence, à cocher dans le programme
    page.evaluate("(()=>{const c=[...document.querySelectorAll('#actS .chip')].find(x=>/bilan/i.test(x.textContent));if(c.getAttribute('aria-pressed')!=='true')c.click();})()")


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
    verifier("Rien de coché d'office : ni l'adresse du départ, ni un service sur les lieux, ni une action",
             page.evaluate("[multi('adrind').length, multi('surlieux').length, multi('actS').length]"), [0, 0, 0])
    verifier("Sans adresse ni case cochée, le message la réclame",
             ["à l'adresse : [adresse]" in page.locator("#out").input_value(), "Adresse manquante" in page.locator("#wC").inner_text()], [True, True])
    # ── l'âge calculé depuis une date de naissance
    from datetime import date
    auj = date.today()
    def age_attendu(j, m, a):
        mois = (auj.year - a) * 12 + (auj.month - m) - (1 if auj.day < j else 0)
        return [str(mois), "mois"] if mois < 24 else [str(mois // 12), "ans"]
    page.locator(".ddn").fill("12031968")
    verifier("Date de naissance : huit chiffres suffisent, l'âge est calculé et la date effacée",
             [page.input_value("#age"), page.input_value("#ageu"), page.input_value(".ddn"), "calculé depuis le 12/03/1968" in page.locator("#ddnInfo").inner_text()],
             age_attendu(12, 3, 1968) + ["", True])
    verifier("Date de naissance : l'âge calculé passe dans le message", ("de " + age_attendu(12, 3, 1968)[0] + " ans") in page.locator("#out").input_value(), True)
    page.locator(".ddn").fill("15/06/25")
    page.locator(".ddn").blur()
    verifier("Date de naissance : année sur deux chiffres, nourrisson compté en mois", [page.input_value("#age"), page.input_value("#ageu")], age_attendu(15, 6, 2025))
    page.locator(".ddn").fill("32131990")
    verifier("Date de naissance : une date impossible est signalée, l'âge ne bouge pas",
             ["Date non reconnue" in page.locator("#ddnInfo").inner_text(), page.input_value("#age")], [True, age_attendu(15, 6, 2025)[0]])
    page.locator(".ddn").fill("")
    verifier("Date de naissance : rien n'en est enregistré", "1968" in page.evaluate("localStorage.getItem('msgops.v1')||''"), False)
    page.fill("#age", "")
    page.select_option("#ageu", "ans")
    saisir_arrivee(page)
    page.evaluate("document.querySelector('#renf .chip[data-r=\"Chef de Groupe\"]').click()")
    verifier("Chef de groupe demandé : le choix « pour action » ou « pour information » apparaît, juste sous les demandes",
             [visible(page, "#cdgMode"), page.evaluate("document.querySelector('#cdgMode').previousElementSibling.id")], [True, "renf"])
    page.locator("#cdgMode .chip", has_text="pour information").click()
    verifier("Chef de groupe pour information : dit dans la demande", page.locator("#out").input_value().split("\n")[1], "Je demande : SMUR et Chef de Groupe pour information")
    page.evaluate("document.querySelector('#renf .chip[data-r=\"Chef de Groupe\"]').click()")
    verifier("Chef de groupe retiré : le choix disparaît", [visible(page, "#cdgMode"), page.locator("#out").input_value().split("\n")[1]], [False, "Je demande : SMUR"])
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
    page.locator("#dEx > summary").click()
    verifier("Examen clinique : respiration et FAST présents, ictère retiré",
             [visible(page, "#resp"), visible(page, "#fast"), page.locator("#teg .chip", has_text="Ictère").count()], [True, True, 0])
    page.locator("#fast .chip", has_text="Visage").click()
    page.locator("#resp .chip", has_text="Tirage").click()
    verifier("Examen clinique : les signes cochés passent dans l'annonce", ["paralysie faciale" in page.evaluate("bAnnonce()").lower(), "tirage" in page.evaluate("bAnnonce()").lower()], [True, True])
    page.locator("#exRas").click()
    verifier("Examen sans particularité : tout passe à « normal »",
             page.evaluate("[multi('pup'), multi('teg'), multi('resp'), multi('fast'), one('abdo')].map(x=>String(x)).join('|')"), "__norm|__norm|__norm|__norm|__norm")
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
    verifier("Routier : le chargement est une rubrique à part, après « Je fais »",
             page.evaluate("(()=>{const y=q=>document.querySelector(q).getBoundingClientRect().top;return y('#actR')<y('#charg')&&!!document.querySelector('#secCharg #charg');})()"), True)
    page.evaluate("document.querySelector('#renf .chip[data-r=\"Chef de Groupe\"]').click()")
    ecart = page.evaluate("(()=>{const y=q=>document.querySelector(q).getBoundingClientRect();return Math.round(y('#cdgMode').top-y('#renf').bottom);})()")
    verifier("Routier : le choix du chef de groupe apparaît collé aux demandes", [visible(page, "#cdgMode"), 0 <= ecart < 40], [True, True])
    page.locator("#cdgMode .chip", has_text="pour action").click()
    verifier("Routier : chef de groupe pour action, dit dans la demande", page.locator("#out").input_value().split("\n")[1], "Je demande : Chef de Groupe pour action")
    page.evaluate("document.querySelector('#renf .chip[data-r=\"Chef de Groupe\"]').click()")
    verifier("Routier : rien de coché d'office, ni demande ni action",
             [page.locator("#out").input_value().split("\n")[1], page.evaluate("multi('actR').length + multi('actRf').length")], ["Secours suffisants", 0])
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

    # ── photo d'ordonnance : le programme interroge Claude lui-même (le service est simulé, aucun appel réel)
    import base64, struct, zlib, tempfile
    def png(larg, haut):
        ligne = b"\x00" + b"\xff\xff\xff" * larg
        def bloc(t, d):
            return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
        return (b"\x89PNG\r\n\x1a\n" + bloc(b"IHDR", struct.pack(">IIBBBBB", larg, haut, 8, 2, 0, 0, 0))
                + bloc(b"IDAT", zlib.compress(ligne * haut)) + bloc(b"IEND", b""))
    photo = Path(tempfile.mkdtemp()) / "ordonnance.png"
    photo.write_bytes(png(2400, 1200))
    SYNTHESE = ("TRAITEMENT : riluzole 50 mg, fluoxétine 20 mg, dantrolène 100 mg.\n\n"
                "LIGNE PAR LIGNE\n— Rilutek (riluzole) 50 mg, matin et soir : neuroprotecteur\n— ligne illisible, à faire préciser\n\n"
                "CE QUE CE TRAITEMENT ÉVOQUE\nTraitement évocateur d'une sclérose latérale amyotrophique, à faire confirmer.\n\n"
                "ANTICOAGULANT OU ANTIAGRÉGANT : aucun repéré")
    ctx3 = nav.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=1)
    pc = ctx3.new_page()
    ec, appels, reponse = [], [], {"mode": "ok"}
    pc.on("pageerror", lambda e: ec.append(str(e)))
    CORS = {"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST, OPTIONS"}
    def service(route):
        rq = route.request
        if rq.method == "OPTIONS":
            return route.fulfill(status=204, headers=CORS)
        appels.append({"url": rq.url, "methode": rq.method, "entetes": rq.headers, "corps": json.loads(rq.post_data)})
        m = reponse["mode"]
        if m == "coupure":
            return route.abort()
        if m == "refus":
            return route.fulfill(status=401, headers=CORS, content_type="application/json",
                                 body=json.dumps({"type": "error", "error": {"type": "authentication_error", "message": "invalid x-api-key"}}))
        texte = "L'image n'est pas lisible." if m == "illisible" else "**" + SYNTHESE
        route.fulfill(status=200, headers=CORS, content_type="application/json",
                      body=json.dumps({"type": "message", "role": "assistant", "stop_reason": "end_turn",
                                       "content": [{"type": "thinking", "thinking": "réflexion à ne pas afficher", "signature": "x"},
                                                   {"type": "text", "text": texte}]}))
    pc.route("https://api.anthropic.com/**", service)
    pc.add_init_script("window.__copie=null;try{navigator.clipboard.writeText=t=>{window.__copie=t;return Promise.resolve();};}catch(e){}")
    pc.goto(V2)
    pc.wait_for_selector("#ngrid button", state="attached")
    pc.locator(".carte[data-e=samu]").click()
    ouvrir_photo = "(()=>{const e=document.getElementById('s9');e.open=true;for(let p=e.parentElement;p;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true;})()"
    pc.evaluate(ouvrir_photo)
    verifier("Photo : plus de point d'accès à saisir, la clé est dans les réglages",
             [pc.locator("#phurl").count(), pc.locator("#s10 #phcle").count(), pc.get_attribute("#phcle", "type")], [0, 1, "password"])
    pc.locator("#phgo").click()
    verifier("Photo sans clé : le programme le dit et propose la consigne pour l'application Claude",
             [pc.locator("#phout").inner_text()[:36], "err" in pc.get_attribute("#phout", "class"), visible(pc, "#phcons"),
              pc.get_attribute("#phouvre", "href"), len(appels)],
             ["Aucune clé d'accès à Claude dans les", True, True, "https://claude.ai/new", 0])
    pc.locator("#phcons").click()
    copie = pc.evaluate("window.__copie") or ""
    verifier("Photo sans clé : la consigne copiée demande une synthèse et la ligne des traitements",
             [copie[:28], "TRAITEMENT :" in copie, "synthèse" in copie, copie.endswith("La photo est jointe à ce message.")],
             ["Tu aides un sapeur-pompier e", True, True, True])
    # la clé se saisit dans les réglages
    pc.locator("#aHome").click()
    pc.locator(".acc-outils button[data-e=reglages]").click()
    pc.locator("#s10 summary").click()
    pc.fill("#phcle", "sk-ant-essai-123")
    pc.locator("#aHome").click()
    pc.locator(".carte[data-e=samu]").click()
    pc.evaluate(ouvrir_photo)
    pc.locator("#phgo").click()
    verifier("Photo avec clé, sans image : rien n'est envoyé", [pc.locator("#phout").inner_text(), len(appels)], ["Aucune image sélectionnée.", 0])
    pc.set_input_files("#phfile", str(photo))
    pc.wait_for_selector("#phprev img")
    pc.locator("#phgo").click()
    verifier("Photo sans la confirmation : rien n'est envoyé",
             [pc.locator("#phout").inner_text(), len(appels)], ["Confirmation de non-identification requise avant tout envoi.", 0])
    pc.check("#phrgpd")
    pc.locator("#phgo").click()
    pc.wait_for_selector("#phins")
    a = appels[-1] if appels else {"url": "", "methode": "", "entetes": {}, "corps": {"messages": [{"content": [{}, {}]}]}}
    c = a["corps"]
    img = c["messages"][0]["content"][0]
    verifier("Photo : l'appel part chez Claude avec la clé et les en-têtes attendus",
             [a["url"], a["methode"], a["entetes"].get("x-api-key"), a["entetes"].get("anthropic-version"),
              a["entetes"].get("anthropic-dangerous-direct-browser-access"), len(appels)],
             ["https://api.anthropic.com/v1/messages", "POST", "sk-ant-essai-123", "2023-06-01", "true", 1])
    verifier("Photo : modèle, consigne de synthèse et image en JPEG, sans réglage que le modèle refuse",
             [c.get("model"), c.get("max_tokens"), "synthèse" in c.get("system", ""), sorted(k for k in c if k in ("temperature", "top_p", "top_k", "thinking")),
              img.get("type"), img.get("source", {}).get("type"), img.get("source", {}).get("media_type"),
              base64.b64decode(img.get("source", {}).get("data", "")[:8])[:3] == b"\xff\xd8\xff", c["messages"][0]["content"][1].get("type")],
             ["claude-sonnet-5-5", 8000, True, [], "image", "base64", "image/jpeg", True, "text"])
    verifier("Photo : l'image est réduite à 1600 points de large avant l'envoi",
             pc.evaluate("(()=>{const i=document.querySelector('#phprev img');return [i.naturalWidth,i.naturalHeight];})()"), [1600, 800])
    verifier("Photo : la synthèse s'affiche, sans la réflexion ni les astérisques",
             [pc.locator("#phout").inner_text(), "err" in pc.get_attribute("#phout", "class")], [SYNTHESE, False])
    pc.locator("#phins").click()
    pc.locator("#phins").click()
    verifier("Photo : seule la ligne des traitements est reportée dans les réponses prêtes pour le régulateur, une seule fois",
             [pc.input_value("#ttt"), pc.evaluate("reserve().filter(x=>x.q==='Traitement').map(x=>x.r)"), pc.locator("#phact button").count()],
             ["riluzole 50 mg, fluoxétine 20 mg, dantrolène 100 mg", ["riluzole 50 mg, fluoxétine 20 mg, dantrolène 100 mg"], 1])
    reponse["mode"] = "illisible"
    pc.locator("#phgo").click()
    pc.wait_for_function("document.querySelector('#phout').textContent.startsWith(\"L'image\")")
    verifier("Photo illisible : la phrase s'affiche, rien à reporter", [pc.locator("#phout").inner_text(), pc.locator("#phins").count()], ["L'image n'est pas lisible.", 0])
    reponse["mode"] = "refus"
    pc.locator("#phgo").click()
    pc.wait_for_selector("#phout.err")
    verifier("Photo : clé refusée, le message le dit",
             [pc.locator("#phout").inner_text(), pc.locator("#phins").count(), pc.locator("#phgo").inner_text().lower(), pc.locator("#phgo").is_enabled()],
             ["Analyse impossible : clé d'accès refusée. La vérifier dans les réglages. La trame manuelle reste disponible.", 0, "analyser l'image", True])
    reponse["mode"] = "coupure"
    pc.evaluate("phOut('',false)")
    pc.locator("#phgo").click()
    pc.wait_for_selector("#phout.err")
    verifier("Photo : sans réseau, le message le dit", pc.locator("#phout").inner_text(),
             "Analyse impossible : service injoignable, vérifier la connexion. La trame manuelle reste disponible.")
    # lésion : une autre consigne, la description va dans l'examen
    reponse["mode"] = "ok"
    pc.locator("#phmode .chip[data-v=lesion]").click()
    pc.locator("#phgo").click()
    pc.wait_for_selector("#phins")
    verifier("Photo d'une lésion : consigne de description, sans avis sur la conduite à tenir",
             ["Décris la lésion" in appels[-1]["corps"]["system"], "aucune conduite à tenir" in appels[-1]["corps"]["system"], pc.locator("#phins").inner_text().lower()],
             [True, True, "insérer dans l'examen"])
    # consigne : conséquences pour l'intervention, médicament non lu annoncé, ligne des traitements sans renvoi
    consigne = pc.evaluate("CONSIGNES.ordo")
    verifier("Consigne d'ordonnance : conséquences pour l'intervention des sapeurs-pompiers, sans acte médical ; médicament non lu annoncé",
             ["CONSÉQUENCES POUR L'INTERVENTION" in consigne, "À SURVEILLER" in consigne, "et un médicament non lu" in consigne,
              "Aucun acte médical" in consigne, "écran de téléphone" in consigne, "avec ce niveau de précision" in consigne],
             [True, False, True, True, False, True])
    verifier("Ligne des traitements : le renvoi entre parenthèses est retiré, « et un médicament non lu » est gardé",
             pc.evaluate("""[
               "TRAITEMENT : riluzole 50 mg, fluoxétine 20 mg, dantrolène 100 mg (4e ligne non incluse, voir plus bas)\\n\\nLIGNE PAR LIGNE",
               "TRAITEMENT : riluzole 50 mg, fluoxétine 20 mg, dantrolène 100 mg, et un médicament non lu.\\n\\nLIGNE PAR LIGNE",
               "TRAITEMENT : morphine (LP) 30 mg, paracétamol 1 g\\nLIGNE PAR LIGNE",
               "L'image n'est pas lisible."].map(phTraitement)"""),
             ["riluzole 50 mg, fluoxétine 20 mg, dantrolène 100 mg", "riluzole 50 mg, fluoxétine 20 mg, dantrolène 100 mg, et un médicament non lu",
              "morphine (LP) 30 mg, paracétamol 1 g", ""])
    # photothèque : une deuxième entrée pour la même image, sans passer par l'appareil photo
    verifier("Photo : deux boutons, appareil photo et photothèque ; les champs de fichier ne se voient plus",
             [pc.locator("#phcam").inner_text(), pc.locator("#phpick").inner_text(), pc.get_attribute("#phfile", "capture"),
              pc.get_attribute("#phlib", "capture"), pc.get_attribute("#phlib", "accept"),
              pc.evaluate("['phfile','phlib'].map(i=>getComputedStyle(document.getElementById(i)).opacity)")],
             ["Prendre une photo", "Photothèque", "environment", None, "image/*", ["0", "0"]])
    with pc.expect_file_chooser() as choix:
        pc.locator("#phpick").click()
    verifier("Photo : « Photothèque » ouvre le choix d'image sans imposer l'appareil photo",
             pc.evaluate("e=>e.id", choix.value.element), "phlib")
    with pc.expect_file_chooser() as choix:
        pc.locator("#phcam").click()
    verifier("Photo : « Prendre une photo » ouvre l'appareil photo", pc.evaluate("e=>e.id", choix.value.element), "phfile")
    photo2 = photo.parent / "phototheque.png"
    photo2.write_bytes(png(900, 1300))
    pc.locator("#phmode .chip[data-v=ordo]").click()
    avant = len(appels)
    pc.set_input_files("#phlib", str(photo2))
    pc.wait_for_function("(()=>{const i=document.querySelector('#phprev img');return i&&i.naturalWidth===900;})()")
    verifier("Photothèque : l'image choisie remplace la précédente, la synthèse et la confirmation repartent de zéro",
             [pc.evaluate("(()=>{const i=document.querySelector('#phprev img');return [i.naturalWidth,i.naturalHeight];})()"),
              pc.locator("#phout").inner_text(), pc.locator("#phins").count(), pc.is_checked("#phrgpd")],
             [[900, 1300], "", 0, False])
    pc.check("#phrgpd")
    pc.locator("#phgo").click()
    pc.wait_for_selector("#phins")
    verifier("Photothèque : l'image choisie est analysée comme une photo prise",
             [len(appels) - avant, appels[-1]["corps"]["messages"][0]["content"][0]["source"]["media_type"], pc.locator("#phout").inner_text()[:24]],
             [1, "image/jpeg", "TRAITEMENT : riluzole 50"])
    pc.set_input_files("#phlib", str(photo2))
    pc.wait_for_function("document.querySelector('#phout').textContent===''")
    verifier("Photothèque : la même image peut être choisie une deuxième fois",
             [pc.locator("#phprev img").count(), pc.is_checked("#phrgpd")], [1, False])
    mauvais = photo.parent / "abimee.png"
    mauvais.write_bytes(b"ceci n'est pas une image")
    pc.set_input_files("#phlib", str(mauvais))
    pc.wait_for_selector("#phout.err")
    verifier("Photothèque : une image illisible est signalée, rien à envoyer",
             [pc.locator("#phout").inner_text(), pc.locator("#phprev img").count(), pc.evaluate("phData")],
             ["Image illisible par le téléphone. En choisir une autre ou la reprendre en photo.", 0, None])
    # depuis les traitements du bilan : photographier ou prendre dans la photothèque
    pc.evaluate("document.getElementById('s9').open=false;document.querySelector('#phmode .chip[data-v=lesion]').click()")
    pc.evaluate("(()=>{for(let p=document.getElementById('phOrdoLib').parentElement;p;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true;})()")
    with pc.expect_file_chooser() as choix:
        pc.locator("#phOrdoLib").click()
    verifier("Traitements : le bouton « Photothèque » ouvre la rubrique Photo en mode ordonnance et le choix d'image",
             [pc.evaluate("e=>e.id", choix.value.element), pc.evaluate("document.getElementById('s9').open"), pc.evaluate("phm()"),
              pc.locator("#phOrdo").inner_text(), pc.locator("#phOrdoLib").inner_text()],
             ["phlib", True, "ordo", "Photographier l'ordonnance", "Photothèque"])
    # la clé reste un réglage : gardée d'une intervention à l'autre, jamais dans les messages ni l'historique
    pc.evaluate("document.querySelector('#age').value='60';sauver()")
    pc.locator("#aHome").click()
    pc.evaluate("archiver();reinitialiser();afficherHist();sauver()")
    pc.reload()
    pc.wait_for_selector("#ngrid button", state="attached")
    verifier("Clé : gardée après une nouvelle intervention et un rechargement ; la photo et la synthèse sont effacées",
             [pc.input_value("#phcle"), pc.input_value("#ttt"), pc.locator("#phout").inner_text(), pc.locator("#phprev img").count(),
              "sk-ant" in pc.evaluate("localStorage.getItem('msgops.v1.hist')||''")],
             ["sk-ant-essai-123", "", "", 0, False])
    verifier("Photo : aucune erreur JavaScript", json.dumps(ec), "[]")
    pc.close()
    nav.close()

print()
print("%d vérification(s) en échec" % len(echecs) if echecs else "Toutes les vérifications passent")
sys.exit(1 if echecs else 0)
