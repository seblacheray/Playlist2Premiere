# Third-party components

Copyright (C) 2026 Seb Lacheray applies to Playlist2Premiere contributions owned by the project owner, not to third-party components. Third-party copyrights and license terms remain with their respective holders.

The project is GPL-3.0-or-later. This does not relicense dependencies.

| Component | Applicable terms to verify against the shipped version |
| --- | --- |
| PySide6 / Shiboken6 | GPL-3.0-only is an available licensing option in the locally inspected distributions. Preserve their notices and provide corresponding source. |
| Qt | Module-specific LGPL/GPL/commercial alternatives and third-party notices. The GPL route requires an inventory of the actual shipped modules and sources. |
| FFprobe from BtbN GPL static build | Supplied build logs report --enable-gpl and --enable-version3, without --enable-nonfree. Preserve COPYING.GPLv3 and all applicable library notices; supply matching FFmpeg and statically linked dependency sources/build scripts. |
| CPython runtime | PSF License Agreement and bundled third-party licenses/copyrights. |
| PyInstaller bootloader | GPL-2.0-or-later with Bootloader Exception; preserve its terms. Runtime hooks and supporting runtime modules can be Apache-2.0. |
| Other bundled libraries | Determine from the frozen archive and the vendor distributions; preserve component-specific licenses and notices. |

Development dependencies are not presumed to be shipped. Installed-package metadata alone does not identify frozen contents. No component is attributed to Seb Lacheray merely because it is bundled.

The Windows package includes a frozen-archive inventory, environment versions, collected vendor license files, version-tagged Qt/PySide open-source license texts and attribution records, source archive hashes and build provenance. PySide/Shiboken uses the GPL-3.0-only option; LicenseRef-Qt-Commercial is not the chosen licensing route. Checked-in core texts are in licenses/qt; complete source-header attributions are retained in the source evidence archives. These are evidence for review, not a legal compliance certificate. Missing licenses and exact corresponding sources must be resolved before distribution.
