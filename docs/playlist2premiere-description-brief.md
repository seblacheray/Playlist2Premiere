# Brief Codex : actualiser uniquement la présentation de Playlist2Premiere

## Décision
**Conserver le nom Playlist2Premiere partout.** Le projet de renommage Playlist2XML est abandonné. Ne pas appliquer le brief de la branche `docs/playlist2xml-rename-brief`.

## Objectif
Clarifier dans le README et, si elle existe, dans la description affichée par l'application que :
- L'application importe les playlists vidéo **PLS (.pls)** et **MPCPL (.mpcpl)**.
- Elle exporte une séquence **Final Cut Pro 7 XML (xmeml v5)** importable dans **Adobe Premiere Pro 2026** et **DaVinci Resolve 21**.
- Ces quatre combinaisons (2 formats de playlist × 2 logiciels) ont été **testées manuellement avec succès sur Windows par l'utilisateur**, sur ses médias de test. Ne pas généraliser à tous les formats médias et cas complexes.

## Travail demandé
1. Mettre à jour la présentation du README, notamment son ancien statut « import dans Premiere non encore validé » devenu obsolète, et les références à une absence totale de validation réelle. Préserver les limites techniques et précautions encore valides.
2. Vérifier si la description courte du dépôt GitHub peut être mise à jour via les outils disponibles ; sinon, fournir au propriétaire ce texte à copier : « Convertit les playlists vidéo PLS et MPCPL en séquences XML compatibles avec Adobe Premiere Pro et DaVinci Resolve. »
3. Si une courte description existe dans l'interface de l'application, la mettre en cohérence sans changer sa structure ni son comportement. Sinon, ne pas ajouter de nouvelle interface juste pour cela.
4. Ne modifier **ni nom, ni package Python, ni commande, ni nom d'exécutable, ni workflow de build, ni moteur XML, ni résolution de chemins**.
5. Faire les changements sur une **nouvelle branche issue de main**, exécuter les vérifications utiles, puis communiquer branche, commit, fichiers modifiés et tests. Ne pas fusionner. ChatGPT examinera la PR avant validation par l'utilisateur.

## Critère
Modification documentaire/minimale, aucun changement fonctionnel.
