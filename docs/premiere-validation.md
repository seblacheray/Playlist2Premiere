# Test réel dans Adobe Premiere Pro 2026 sous Windows

**Résultats rapportés par l’utilisateur :** imports réussis sous Windows pour PLS et MPCPL dans Adobe Premiere Pro 2026, ainsi que dans DaVinci Resolve 21, sur ses médias de test. Ce protocole reste à appliquer pour de nouveaux médias, les cas complexes et les nouvelles versions ; le succès des quatre combinaisons ne signifie pas que chaque étape ci-dessous a été validée. Consigner version exacte des logiciels, Windows, Python/FFmpeg, date et résultats pour chaque nouvel essai.

1. Installer l’application et FFmpeg sur Windows. Exécuter `scripts/make_example.py` pour créer les trois médias et un XML avec des chemins locaux Windows. Ne pas utiliser les chemins Linux du XML livré sans relier les médias.
2. Dans Premiere Pro 2026, créer un projet vide puis utiliser **Fichier > Importer** pour sélectionner `examples/three_clips.xml`. Noter toute boîte de dialogue, erreur d’import ou demande de localisation des médias.
3. Ouvrir la séquence importée. Vérifier trois clips, dans l’ordre rouge/vert/bleu, sans transition ni trou vidéo. Vérifier la résolution 640 × 360 et la cadence 24000/1001 (affichage usuel 23,976).
4. Comparer les points de coupe et la durée finale avec le XML (`sequence/duration`, `clipitem/start/end`) en affichage images. Les clips sources ont des cadences différentes ; vérifier que les points de sortie ne coupent pas une image de manière inattendue et que les images sont conformées correctement.
5. Écouter les sons à 440, 880 et 1320 Hz. Vérifier deux canaux par clip, leur synchronisation, les liaisons vidéo/audio et l’absence de doublage ou de canal perdu. Comparer aussi avec la lecture des MP4 sources.
6. Importer une playlist répétant deux fois le premier média. Vérifier les deux occurrences et les liens audio de chaque occurrence.
7. Déplacer les médias dans un chemin avec accents, espaces, `&` et `#`, relancer l’analyse et l’export, puis vérifier l’import. Tester aussi un chemin réseau UNC si ce workflow est requis.
8. Refaire l’export à 1920 × 1080 et 30000/1001. Vérifier paramètres, conformation et continuité. Utiliser des vidéos réelles de résolutions différentes pour évaluer cadrage et mise à l’échelle ; aucun effet de mise à l’échelle explicite n’est ajouté par le convertisseur.
9. Tester un fichier sans audio, puis un fichier multicanal et plusieurs flux audio : vérifier chaque canal source dans Premiere et les indices `sourcetrack`. Tester également des décalages de début audio mesurés. Cette étape est indispensable avant de déclarer la prise en charge multistream validée dans Premiere.
10. Renommer temporairement un média et confirmer que l’application bloque l’export avec une erreur, sans supprimer silencieusement le clip. Vérifier qu’aucun média source n’a changé, par exemple en comparant les SHA-256 avant/après.

Consigner pour chaque étape : réussi / échoué / non exécuté, observations, durée en images et captures utiles. Un XML bien formé et des tests Python réussis ne constituent pas une validation d’import Premiere.
