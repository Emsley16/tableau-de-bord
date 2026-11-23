# Tests de Messages ops

Ce dossier ne sert pas en intervention. Il contient le programme de vérification
à relancer avant toute modification de `messages-ops.html`.

## Ce qu'il fait

Il ouvre le programme dans Chrome au format téléphone, appuie sur les boutons,
remplit les champs et compare chaque message obtenu au message attendu :
messages CODIS radio et écrits (ambiance et compte rendu, secours à personne et
routier), groupe horaire, catégories, écran Fin, terrain, histoire, annonce SAMU.

## Lancement

Depuis la racine du dépôt :

    python3 tests/test_messages.py
    python3 tests/test_interface.py

Prérequis : Python 3, le paquet `playwright` (`pip install playwright`) et Google Chrome.
La dernière ligne affiche `RÉSULTAT : tous les tests passent` ou la liste des échecs.

## Fichiers

- `test_messages.py` : les vérifications du moteur de rédaction (les messages).
- `test_interface.py` : les vérifications de l'interface (accueil, un écran par message, états, rechargement).
- `reference-2026.11.23g.html` : la dernière version à onglets, du 23/11/2026. Même moteur de rédaction :
  à saisie égale, elle et le programme doivent écrire le même message.
- `reference-2026.10.14f.html` : la version du 14/10/2026, gardée comme référence.
  À saisie égale, les messages radio et l'annonce SAMU doivent lui rester identiques,
  sauf changement demandé. Dans ce cas, mettre à jour le test concerné, pas la référence.

## Règle

Toute modification du programme s'accompagne d'une vérification ajoutée ou mise à jour ici.
