# Brief Codex : renommer Playlist2Premiere en Playlist2XML

## Objectif
Renommer proprement l'application Windows et son identité de Playlist2Premiere vers **Playlist2XML**, puisque les XML FCP7 sont maintenant importés avec succès dans Adobe Premiere Pro 2026 et DaVinci Resolve 21. Ne changer **aucune logique de conversion**.

## Travail demandé
1. Inventorier toutes les occurrences et les points d'entrée (titre fenêtre, texte UI, nom EXE, nom des artefacts ZIP GitHub Actions, scripts PowerShell, PyInstaller, métadonnées du projet, CLI, documentation, exemples, tests, workflow, icône si pertinente).
2. Renommer les noms visibles et les sorties en Playlist2XML. Renommer aussi le paquet Python `playlist2premiere` vers `playlist2xml` et son entry point si faisable de manière cohérente et sûre ; mettre à jour tous les imports et tests. Éviter les changements de comportement. Si un renommage interne est trop risqué, expliquer pourquoi dans la PR et conserver temporairement un alias compatible.
3. Vérifier la prise en charge des chemins Windows, FFprobe embarqué et des formats .pls et .mpcpl ; ne pas modifier le format FCP7 XML xmeml v5 ni le comportement de résolution des chemins.
4. Actualiser le README : état validé manuellement par l'utilisateur sur Windows avec **.pls et .mpcpl dans Premiere Pro 2026 et DaVinci Resolve 21** ; ne pas prétendre que tous les cas médias sont validés. Corriger les commandes d'installation, chemins, noms EXE et noms d'artefacts. Ne pas renommer le dépôt GitHub distant : **seblacheray/Playlist2Premiere** reste inchangé pour cette PR ; un renommage GitHub éventuel se fera séparément.
5. Adapter les tests, y compris un test simple du nom de l'application et du lancement, ainsi que le smoke test Windows du binaire empaqueté. Faire tourner tous les tests disponibles et le workflow Windows si possible.
6. Travailler sur une **nouvelle branche de code** issue de `main` (pas cette branche docs). Fournir le nom de branche, le commit, le récapitulatif des fichiers et les résultats des tests. Ne pas fusionner automatiquement. ChatGPT préparera/reverra la PR et l'utilisateur fera la validation réelle Windows/Premiere/Resolve.

## Critères d'acceptation
- UI, exe et archive Windows : Playlist2XML.
- `.pls` et `.mpcpl` continuent de produire des XML importables dans Premiere Pro 2026 et DaVinci Resolve 21.
- Build GitHub Actions Windows et tests au vert.
- Aucun changement fonctionnel de la conversion ni du XML.
- README fidèle à l'état réel des validations.
