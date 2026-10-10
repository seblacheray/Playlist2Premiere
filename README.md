# Playlist2Premiere

Application Windows Python/PySide6 pour convertir une playlist vidéo `.pls` ou `.mpcpl` en séquence XML Final Cut Pro 7 (`xmeml` v5), destinée à un import dans Adobe Premiere Pro 2026.

**État : première version fonctionnelle du convertisseur ; import dans Premiere non encore validé.** Les tests Linux couvrent le moteur et FFprobe. Le démarrage Qt est contrôlé hors écran ; l’utilisation sur Windows et le packaging Windows restent à tester sur Windows.

## Installation Windows

Installer Python 3.10 ou supérieur (64 bits) et FFmpeg/FFprobe depuis une distribution Windows indiquée par https://ffmpeg.org/download.html. Vérifier la provenance et les sommes de contrôle du distributeur. Ajouter le dossier contenant `ffprobe.exe` au `PATH`, puis ouvrir un nouveau terminal PowerShell.

```powershell
cd Playlist2Premiere
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
ffprobe -version
.\.venv\Scripts\python.exe -m playlist2premiere
```

Choisir une playlist et un dossier de médias, lancer l’analyse, examiner le récapitulatif, ajuster éventuellement la résolution et la cadence, puis exporter le XML. Chaque occurrence de la playlist devient un clip. Tout problème de média bloque l’export ; aucune entrée n’est supprimée silencieusement. L’analyse se déroule dans un thread séparé de l’interface. Les fichiers sources sont ouverts en lecture uniquement.

Les cadences se saisissent exactement : `24`, `25`, `24000/1001`, `30000/1001`, etc. `29.97` n’est pas équivalent à `30000/1001` et n’est pas représentable exactement par le couple `timebase`/`ntsc` de xmeml.

## Architecture

- `playlist.py` : lecture PLS/MPCPL, ordre et doublons, encodages UTF-8/BOM, UTF-16 et repli Windows-1252.
- `paths.py` : chemins absolus, relatifs à la playlist puis au dossier choisi, URI file ; recherche récursive par nom si le chemin original n’existe plus. Plusieurs correspondances entraînent une erreur.
- `probe.py` : FFprobe, durées `duration_ts × time_base` ou durée explicite de piste, cadence rationnelle, pistes audio, horodatages.
- `timeline.py` : accumulation avec `Fraction` ; arrondi des bornes cumulées sur la grille de la séquence, sans somme d’arrondis individuels.
- `xml_export.py` : références de fichiers réutilisées, occurrences distinctes, vidéo et audio liés, canaux audio sur pistes séparées, écriture atomique du XML.
- `gui.py` : sélection, analyse, récapitulatif et export.

Les positions `start/end` utilisent la cadence séquence ; `in/out` utilisent la cadence source. L’entrée zéro désigne le début relatif du média, **pas un timecode source inventé**. Aucun élément `timecode` n’est fabriqué. Les horodatages FFprobe servent à préserver les décalages audio relativement à la vidéo. L’audio est limité à la fenêtre vidéo : une piste commençant plus tard laisse le silence mesuré au début, une piste plus courte s’arrête à sa fin. La quantification temporelle est limitée à la précision d’une image. Les clips vidéo restent contigus même avec des cadences différentes ; Premiere effectue la conversion de cadence et la conformation visuelle.

## Tests et exemple

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\make_example.py
```

Le test d’intégration nécessite `ffmpeg` et `ffprobe`, sinon il est explicitement ignoré. Le générateur produit trois MP4 colorés avec audio stéréo, cadences 24000/1001, 30000/1001 et 25, résolutions différentes, ainsi que `examples/three_clips.pls` et `examples/three_clips.xml`. Il refuse d’écraser des médias existants : pour recommencer, déplacer les exemples précédents. L’XML fourni référence les chemins absolus de la machine de génération ; régénérer sur Windows ou relier les médias dans Premiere.

Voir [le protocole Premiere 2026](docs/premiere-validation.md) pour le test réel requis.

## Créer un exécutable Windows

PyInstaller doit tourner **sur Windows** ; il ne produit pas un `.exe` Windows depuis Linux.

```powershell
.\.venv\Scripts\Activate.ps1
.\scripts\build_windows.ps1
# Variante autonome : inclure votre distribution de FFprobe
.\scripts\build_windows.ps1 -FFprobe 'C:\ffmpeg\bin\ffprobe.exe'
```

Résultat attendu : `dist/Playlist2Premiere.exe`. Sans inclusion, FFprobe doit rester dans le PATH du poste cible. Avec inclusion, le programme cherche d’abord la copie intégrée. Pour une distribution FFprobe partagée, les DLL associées devront également être empaquetées ; préférer une distribution autonome et respecter ses obligations de licence. Tester le `.exe` sur un poste Windows sans Python, y compris avec chemins accentués et sans FFprobe dans le PATH pour la variante autonome.

## Limites explicites

Les médias doivent être des vidéos à cadence constante, pixels carrés, progressifs, sans rotation ; une seule piste vidéo est acceptée. Une cadence moyenne différente de la cadence nominale est refusée. Ce contrôle ne prouve pas à lui seul qu’un fichier est exempt de toute variation de cadence : les vidéos connues comme VFR doivent être normalisées avant import. Les durées et débuts de pistes doivent être présents dans FFprobe ; la durée globale du conteneur et les indications de durée des playlists ne remplacent pas une durée vidéo manquante. Aucune durée n’est extrapolée.

Les flux distants, périphériques MPCPL, fichiers de doublage externe, points cue et découpage source ne sont pas interprétés. Les playlists servent à sélectionner des fichiers complets, pas des sous-clips. La correspondance entre plusieurs flux audio, leurs canaux et l’importeur Premiere doit être vérifiée sur des médias représentatifs ; le cas de référence est vidéo + un flux stéréo. Aucune validation par DTD Apple ou dans Premiere n’a été effectuée dans cet environnement.

## Développement Linux

```sh
python -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q
.venv/bin/python -m playlist2premiere
```

Installer FFmpeg via le gestionnaire système pour l’intégration. Pour un contrôle Qt sans affichage : `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_gui.py -q`.

## Télécharger la version portable depuis GitHub Actions

Le workflow **Windows portable** s’exécute à chaque push sur `main`, pour les pull requests et manuellement via **Run workflow**. Il utilise Windows x64, Python 3.12, teste l’application avec FFmpeg/FFprobe, puis crée un exécutable PyInstaller contenant FFprobe. FFmpeg sert uniquement à générer les médias des tests : l’application n’en a pas besoin pour convertir les playlists, il n’est donc pas distribué dans l’exécutable.

1. Ouvrir l’onglet **Actions** du dépôt GitHub et choisir **Windows portable**.
2. Ouvrir une exécution réussie de la branche `main` (ou lancer **Run workflow** sur cette branche).
3. Dans **Artifacts**, télécharger **Playlist2Premiere-Windows-x64-portable**. Une connexion GitHub peut être nécessaire.
4. Extraire le ZIP dans un dossier, conserver les notices fournies, puis lancer **Playlist2Premiere.exe**. Python, FFmpeg et FFprobe n’ont pas à être installés.

Les artefacts sont conservés 30 jours. Le téléchargement comprend le SHA-256 de l’exécutable. Ce build n’est pas signé ; Windows peut afficher une notification SmartScreen. Il ne s’agit pas d’un installeur ni d’une publication GitHub Releases.

Le workflow vérifie aussi l’exécutable compilé avec un PATH limité aux dossiers Windows : démarrage Qt hors écran, sélection du FFprobe embarqué, analyse d’un média avec accents/caractères spéciaux, puis export XML avec vidéo et deux canaux audio. Ce contrôle ne remplace pas l’essai interactif sur Windows ni l’import réel dans Premiere. FFprobe est téléchargé depuis la distribution Gyan 7.1.1 et comparé à son SHA-256 publié avant utilisation ; si le téléchargement ou la vérification échoue, la compilation est bloquée.
