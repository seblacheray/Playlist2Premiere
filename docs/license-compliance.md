# GPL adoption and Windows distribution review

## Project decision

Copyright (C) 2026 Seb Lacheray. Playlist2Premiere project code is GNU GPL version 3 or, at the recipient's option, any later version (GPL-3.0-or-later). This declaration does not claim ownership of third-party code or override third-party terms. The owner's licensing decision is relied upon; Git author names alone do not prove title to every contribution.

## Exact historical build

- Commit: 9c0bd546f2b7ec36358de00c17eb032b25ddb1f9
- Actions run: 38316676323
- Artifact: Playlist2Premiere-Windows-x64-portable
- Reported FFprobe: N-127388-g615b07170e-20261012
- Reported FFmpeg archive SHA-256: 4480b1abcae8bb46146e271fe603efaa90f29671ff9013bb0aed2d64d12951c8
- Owner-supplied logs: --enable-gpl, --enable-version3, no --enable-nonfree in the displayed configuration.

The artifact API returned Forbidden during this review. Embedded binaries, Qt versions/modules, runtime libraries and complete FFprobe configuration were therefore NOT independently inspected. No replacement latest archive was substituted. The available evidence indicates GPL v3 for FFprobe, but the exact statically linked component set remains unverified. A build using --enable-nonfree must not be redistributed without resolving licensing; the updated workflow rejects that flag.

## Distribution mechanism

Automatic CI builds run tests and build an executable for validation. They upload review evidence, not a portable executable for public distribution, when source inputs are absent. A manually dispatched portable package requires a matching source archive URL, SHA-256 and explicit owner review confirmation. The source archive is included alongside the binary in the SAME downloadable artifact (GPLv3 section 6(a) distribution approach). A URL alone is not treated as fulfillment. Inputs are not secrets.

Before approving the source archive, verify it contains:

1. Exact Playlist2Premiere sources for the build commit and its build/install scripts (also archived by CI).
2. Exact Qt/PySide6/Shiboken sources, modifications and necessary build scripts for every relevant embedded module, plus third-party sources/terms as applicable.
3. Exact FFmpeg revision and every statically linked library requiring corresponding source, modifications, configuration, toolchain instructions and the matching BtbN build recipe/revisions. The FFmpeg commit alone is insufficient.
4. Python and PyInstaller runtime/bootloader license notices and any source requirements applicable to the chosen licensing route.
5. A root SOURCE-MANIFEST.json identifying components, versions, exact upstream revisions, license choices and archive paths. The automated gate now checks the structured manifest, included file hashes, declared versions and Qt module revisions, not legal completeness. See corresponding-sources.md.

The reviewer must inspect the frozen inventory, ensure collected license texts cover actual shipped components, supply any missing vendor notices, and confirm build correspondence. GPLv3 also requires preserving notices, no additional restrictions, and installation information when section 6 requires it for a User Product. A complete general-purpose toolchain need not always be supplied; the corresponding-source definition and system-library exclusions must be applied per component.

## Remaining obligations / limits

No exact historical artifact inspection, no independent validation of corresponding-source completeness, no native Windows build in this environment, and no legal compliance certification. Metadata license labels do not replace full texts. Onefile embedding does not remove GPL obligations. The owner must review rights in any external contributions before licensing them. The build inventory and collected notices require human comparison; some vendor notices may not be present in Python package RECORD lists.

Recommended next step: use immutable BtbN release assets and record expected hashes, build recipe revisions and source bundles. The current workflow records the resolved archive hash and FFprobe version/configuration, but retains latest to avoid pretending a historical immutable asset URL is known. Each manually distributed build needs sources corresponding to THAT build; sources from another latest build are not acceptable. Do not publish a Release until these obligations are satisfied.


## Follow-up: Qt notices and source verification

The owner reported a successful Windows evidence build, with commercial-only collected Qt notices and PDF/QML/Quick/VirtualKeyboard DLLs. This was not independently retrieved (API Forbidden). The updated collector fetches version-tagged immutable Qt/PySide source archives and their open-source license texts, copyright notices and attributions based on the actual frozen DLL inventory. Commercial terms are retained only as unused alternatives, never as proof for GPL licensing. Checked-in core Qt open-source texts are copied into packaging as well.

A Widgets-specific PyInstaller hook removes optional PDF/virtual-keyboard plugins before dependency analysis. Required DLLs are not forcibly deleted; QML/Quick may remain as link-time dependencies and then require qtdeclarative source/notice evidence. Windows CI adds platform and file-dialog smoke tests and generates a fresh inventory. Local source lookup succeeded for qtbase/qtsvg/pyside-setup v6.12.0; this is not an inspection of the user's Windows binary. Full corresponding sources and vendor build recipes, including exact FFprobe static dependency revisions, remain subject to verification. See [reproducible assembly procedure](corresponding-sources.md).
