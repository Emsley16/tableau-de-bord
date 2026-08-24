# Relevé — installation et mode d'emploi

Application d'états des lieux d'entrée et de sortie, avec photos comparées,
réserves permanentes et signature des deux parties. Tout reste sur l'appareil :
aucun serveur, aucun compte, aucun abonnement.

---

## 1. Les fichiers

Sept fichiers, tous dans le **même dossier**, sans sous-dossier :

| Fichier | Rôle |
|---|---|
| `index.html` | l'application entière |
| `sw.js` | fonctionnement hors ligne et détection des mises à jour |
| `manifest.webmanifest` | déclaration d'installation |
| `icon-180.png` | icône iPhone / iPad |
| `icon-192.png` | icône Android et navigateur |
| `icon-512.png` | icône haute définition |
| `icon-512-maskable.png` | icône recadrable Android |

Si un seul manque, l'installation sur l'écran d'accueil échoue silencieusement.

---

## 2. Mise en ligne sur GitHub Pages

À faire depuis le MacBook, pas depuis le téléphone.

1. Rassembler les sept fichiers dans un dossier nommé **`edl`** sur le bureau.
2. Ouvrir <https://github.com> et se rendre sur le dépôt **`emsley16.github.io`**.
3. Bouton **Add file** → **Upload files**.
4. Glisser le **dossier `edl` entier** dans la zone de dépôt. GitHub conserve
   le nom du dossier ; les sept fichiers apparaissent sous `edl/`.
5. En bas, dans *Commit changes*, écrire par exemple `Application états des lieux v1.2`,
   puis **Commit changes**.
6. Attendre une à deux minutes le temps de la publication.

L'adresse est alors :

```
https://emsley16.github.io/edl/
```

> Le dépôt doit rester **public** : GitHub Pages n'est gratuit qu'à cette condition.
> Cela ne publie que le code de l'application — aucun état des lieux, aucune photo
> ne part sur GitHub. Les relevés restent sur les appareils.

**Vérification** : ouvrir l'adresse dans un navigateur. En bas de l'écran d'accueil
doit s'afficher `Relevé 1.2.0`. Si la mention `mode local` apparaît, c'est que le
fichier a été ouvert depuis le disque et non depuis l'adresse — dans ce cas, ni le
hors-ligne ni les empreintes SHA-256 ne fonctionnent.

---

## 3. Installation sur les appareils

### iPhone
1. Ouvrir l'adresse **dans Safari** (pas Chrome : iOS n'autorise que Safari à installer).
2. Bouton **Partager** → **Sur l'écran d'accueil** → **Ajouter**.
3. L'icône apparaît. **Lancer l'application depuis cette icône**, jamais depuis Safari.

Cette étape n'est pas cosmétique : Safari efface le stockage des sites non installés
après quelques semaines d'inactivité. Une application installée en est exemptée.

### MacBook
- **Chrome** : icône d'installation à droite de la barre d'adresse.
- **Safari** : menu **Fichier** → **Ajouter au Dock**.

### Autre ordinateur
L'adresse suffit, sans installation. Les données créées sur cet ordinateur y
resteront : voir la sauvegarde ci-dessous.

---

## 4. Passer d'un appareil à l'autre

Il n'y a **pas de synchronisation automatique** — ce serait un serveur, donc
l'hébergement de données de locataires et les obligations qui vont avec.

Le transfert est manuel et complet :

1. Sur l'appareil de départ : accueil → **Sauvegarde complète**. Une archive `.zip`
   est produite, contenant logements, relevés, réserves et photos en original.
2. La déposer dans iCloud Drive (ou l'envoyer par courriel).
3. Sur l'appareil d'arrivée : accueil → **Restaurer une sauvegarde** → choisir l'archive.

Les relevés portant le même identifiant sont remplacés par la version de l'archive,
les autres sont conservés. En pratique : faire le relevé sur l'iPhone, sauvegarder,
restaurer sur le Mac pour l'impression et l'archivage.

---

## 5. Les photos

### Sur place, pendant l'état des lieux
Sous chaque élément, le carré **`+`**. iOS propose alors *Prendre une photo*,
*Photothèque* ou *Choisir un fichier*. La sélection multiple fonctionne.

Chaque photo est enregistrée en trois exemplaires : l'**original intact** avec ses
métadonnées, une version 1 200 px pour le PDF, une vignette pour l'affichage.
Une empreinte SHA-256 est calculée à l'import.

Quelques règles qui font la différence en cas de litige :

- Photographier **tout**, pas seulement les défauts. Une pièce sans photo à
  l'entrée, c'est un élément qu'on ne pourra jamais imputer à la sortie.
- Lumière suffisante, cadrage large puis rapproché sur le défaut.
- **Aucune retouche** : ni recadrage, ni correction de luminosité, ni filtre.
  Une photo manifestement retouchée décrédibilise l'ensemble du constat.
- Les photos prises lors d'un état des lieux **d'entrée** deviennent les photos
  de référence : elles s'afficheront automatiquement en vis-à-vis lors de la
  sortie du même locataire.

### Reprendre la base photo des anciens états des lieux Excel
Un fichier `.xlsx` ou `.xlsm` est une archive : les images y sont stockées en clair
dans `xl/media/`, et le fichier `xl/drawings/drawing1.xml` contient l'ancrage de
chaque image — la ligne et la colonne où elle a été posée. En croisant les deux,
on reconstitue l'association « photo ↔ élément ».

Marche à suivre : m'envoyer les fichiers Excel. Je fournis en retour un dossier de
photos déjà nommées (`cuisine_plan-travail_01.jpg` plutôt que `image37.png`), qu'il
suffit d'attacher élément par élément avec le bouton `+`. Compter 10 à 20 % de
rattachements à corriger à la main, une fois pour toutes.

---

## 6. Déroulé d'un état des lieux

1. **Logements** → *Nouveau logement*. Ajuster le gabarit : renommer, ajouter,
   supprimer les pièces et les éléments. Une seule fois par bien.
2. Accueil → *Nouvel état des lieux* → logement, type **Entrée**.
3. **En-tête et compteurs** : les mentions du décret n° 2016-382. Tant qu'une
   manque, la signature reste bloquée.
4. Parcourir les pièces. Les valeurs pré-remplies s'affichent en gris hachuré :
   elles ne sont **pas** un constat. Toucher un cran le confirme ; le bouton
   *Confirmer la pièce* traite toute une pièce parcourue sans écart.
5. Photographier au fil de l'eau.
6. Pour un désordre qui ne sera pas réparé : *Passer en réserve permanente*.
   Il suivra le logement d'un locataire à l'autre et le prochain occupant
   n'en sera pas tenu responsable.
7. Quand la jauge est pleine : **Signer**. Les deux parties signent à l'écran.
   Le document se verrouille définitivement.
8. **Exporter** → PDF et archive. Remettre le PDF au locataire immédiatement,
   par courriel depuis le logement, et lui demander d'accuser réception depuis
   sa propre adresse.
9. Conserver l'archive `.zip` et l'empreinte SHA-256 affichée, au moins trois ans
   après la fin du bail, en trois exemplaires : appareil, cloud, disque externe.

### État des lieux de sortie
Le créer avec le type **Sortie** en désignant l'entrée du locataire concerné.
Chaque élément affiche alors l'état et les photos d'entrée en vis-à-vis, et
l'état du jour est pré-rempli sur « inchangé ». La propreté, elle, n'est jamais
pré-remplie à la sortie : elle doit être constatée, sans quoi un élément oublié
partirait en « propre » et le nettoyage ne pourrait plus être facturé.

---

## 7. Mises à jour

L'application vérifie l'existence d'une nouvelle version à chaque lancement, à
chaque retour au premier plan et toutes les trente minutes. Un bandeau apparaît
en haut de l'écran — la mise à jour **ne s'installe jamais d'elle-même**, pour
qu'elle ne tombe pas au milieu d'un relevé, devant un locataire.

Pour publier une nouvelle version : remplacer les fichiers concernés sur GitHub.
Le bandeau apparaîtra au prochain lancement.

---

## 8. Limites connues

- **Volume** : un état des lieux d'une soixantaine de photos pèse environ 200 Mo
  en stockage, originaux compris. Exporter l'archive après chaque signature.
- **Signature** : signature électronique simple. Valable, mais si un locataire
  conteste un jour avoir signé, l'accusé de réception par courriel est ce qui
  fera la différence. Pour un enjeu élevé, passer par une signature avancée
  conforme eIDAS.
- **Horodatage** : la date affichée provient de l'appareil. L'empreinte SHA-256
  de l'archive, envoyée par courriel le jour même, constitue la preuve d'intégrité
  et de date. Un jeton d'horodatage RFC 3161 pourra être ajouté par la suite.
- **Import Excel** : à venir, une fois les anciens fichiers récupérés.
