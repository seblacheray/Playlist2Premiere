# Reproducible assembly of corresponding-source.zip

## Status

This is a repeatable *assembly and declared correspondence check*, not an independently reproduced vendor build. The owner reported a successful Windows build and an inventory containing Qt6Pdf/Qt6Qml/Qt6Quick/Qt6VirtualKeyboard and commercial-only collected Qt notices. Those observations are accepted as owner-supplied evidence. GitHub's API still returns Forbidden in this environment; the actual evidence ZIP and the new Windows executable have not been retrieved or inspected locally.

No archive downloaded from a new `latest` is used to audit the historical binary. Do not combine sources collected for different binaries.

## 1. Obtain the exact new build evidence

Run Windows CI on the licensing branch. The review artifact contains:

- `frozen-inventory.txt`: recursive PyInstaller list of actual shipped entries, not a list of installed packages.
- `installed-packages.json`: a superset of installed versions, not all necessarily shipped.
- `qt-license-provenance.json`: Qt runtime version, PySide/Shiboken version, actual Qt DLL module names, immutable source commits, source archive SHA-256 and collected attribution paths.
- `qt-source-evidence/*.zip`: version-tagged repository source archives, including upstream source-header copyrights.
- `qt-open-source-notices`: complete LICENSES trees and notice/copyright/authors/qt_attribution.json files from those source modules.
- `project-third-party-license-texts/qt`: core open-source texts, not just LicenseRef-Qt-Commercial.
- `ffprobe-configuration.txt`, `ffprobe-license.txt`, FFmpeg distributor notices, build/provenance data and project sources.

`collect_qt_legal.py` maps Core/Gui/Widgets and other qtbase DLLs to qtbase, Svg/SvgWidgets to qtsvg, and retained Qml/Quick DLL dependencies to qtdeclarative. An unrecognized module blocks collection for explicit review. It does not infer shipping from PySide6_Addons installation.

Source tags v6.12.0 were independently resolved during this change:

| Repository | Commit |
| --- | --- |
| qt/qtbase | 025bdad181de241e81bf853c8a2d7bf3d19261a9 |
| qt/qtsvg | 883a58532078d003cefef0a549bfe9f885ce41f5 |
| pyside/pyside-setup | f50facb83fc3dc5f3240c854668c7a6dd93871b2 |

The source/notice download was actually exercised for these modules with a synthetic DLL list. It was NOT a Windows inventory test. If CI installs another version or retains another module, use the recorded provenance from THAT build instead.

## 2. Assemble complete source inputs, without guessing missing components

Create a staging directory outside the checkout. Reuse matching `qt-source-evidence` archives; fetch and include required Git submodules, vendor patches, build configurations and recipes. The codeload archives alone omit Git submodules. Confirm that official PySide wheel source tags actually match its shipped Qt binaries and vendor build patches. `pyside-setup` includes PySide and Shiboken sources, but a matching tag alone is not complete evidence of the wheel toolchain.

For FFprobe, use the full revision corresponding to the `-g...` identifier and the displayed configuration. Historical owner-supplied version N-127388-g615b07170e-20261012 identifies only a shortened revision; it does not identify the full BtbN build recipe or static library revisions. Obtain the exact BtbN recipe commit, patches, library locks/revisions, build logs and toolchain instructions for the archive with SHA-256 4480b1abcae8bb46146e271fe603efaa90f29671ff9013bb0aed2d64d12951c8 if auditing that binary. Do not infer those from today's BtbN master. For a new binary, use its own archive hash/version. Include source and applicable license notices for every statically linked dependency covered by corresponding-source obligations. A list of configure flags is not an exhaustive list of embedded code, and FFmpeg source alone is insufficient. If this information is unavailable, keep portable distribution blocked; consider a separately reviewed reproducible toolchain/source-lock workflow.

Also gather matching CPython source/license material and PyInstaller sources/bootloader and Apache runtime-hook material, with build instructions. Apply the bootloader exception accurately; not every permissively licensed component requires source distribution, but its notices remain necessary. Include any other native library source/terms required by the actual frozen inventory. Wheel installation, Qt source code, or source archive presence is not proof of complete native licensing.

Add each component's source archives, patches, attribution texts and build instructions to the staging directory. Create `SOURCE-MANIFEST.json` with this schema (one record per component):

```json
{
  "schema_version": 1,
  "components": [
    {
      "id": "qt",
      "version": "6.12.0",
      "revision": "full reviewed upstream revision or multi-module identifier",
      "module_revisions": {"qtbase": "025bdad181de241e81bf853c8a2d7bf3d19261a9"},
      "license": "module-specific reviewed license choices",
      "source_origin": "immutable source URL",
      "modified": false,
      "build_instructions": "recipes/qt-build.txt",
      "files": [
        {"path": "sources/qtbase.zip", "sha256": "64 hexadecimal digits"},
        {"path": "recipes/qt-build.txt", "sha256": "64 hexadecimal digits"}
      ]
    }
  ]
}
```

This abbreviated schema example intentionally cannot pass validation. Required IDs are `qt`, `pyside`, `ffmpeg`, `btbn-build`, `python`, `pyinstaller`. Additional IDs must describe every relevant static library; the `ffmpeg` record needs a nonempty `statically_linked_components` list referencing those IDs and a full 40-digit FFmpeg Git revision. Record Shiboken in pyside build instructions and notices. `module_revisions` for qt/pyside must cover every repository in `qt-license-provenance.json`. Versions must match that build's evidence. All referenced files, including build instructions, must have real hashes, not placeholders.

## 3. Create and check the archive

```powershell
python scripts/prepare_corresponding_source.py assemble C:\source-staging\SOURCE-MANIFEST.json C:\source-staging\corresponding-source.zip
python scripts/prepare_corresponding_source.py verify C:\source-staging\corresponding-source.zip C:\review-evidence\legal
```

The assembly refuses missing files, unsafe paths, hash mismatches, incomplete component records, absent build recipes and undeclared static libraries. It produces deterministically ordered ZIP entries with fixed timestamps. Identical inputs produce identical hashes. It does not download substitute sources or overwrite an existing output.

Verification checks included file hashes, PySide/Qt/Python/PyInstaller versions, Qt source module revisions and the declared FFprobe version/short revision against the exact build evidence. It cannot prove that a declared static-library list is exhaustive, source corresponds at the patch level, or recipes reproduce vendor binaries. Review these manually and document the result before confirming `sources_reviewed`.

## 4. Publish only after review

Provide the exact source ZIP URL and SHA-256 to manual dispatch. The workflow includes the bundle alongside the binary and project source archive, and rejects version/hash/revision mismatches. Since rebuilding from latest or unpinned Python packages can change inputs between runs, mismatches must be resolved by obtaining sources for the new binary, never by changing expected hashes to conceal a mismatch. Pinning a reviewed binary/source build is recommended as separate reproducibility work. No Release is created.

## Qt reduction and validation

The GUI imports QtCore/QtWidgets. The custom QtGui hook removes only `qpdf` and virtual-keyboard plugins before dependency analysis, excludes unused Python PDF/QML/Quick/VirtualKeyboard imports and preserves ordinary image plugins, styles, Windows/offscreen platforms and dependencies of retained binaries. It never forcibly deletes a required Qt DLL. QML/Quick DLLs can remain as binding/plugin link dependencies; the inventory records them and includes qtdeclarative sources rather than falsely claiming their removal. PDF/VirtualKeyboard or an unmapped module still in the final inventory blocks legal collection.

Windows CI produces a NEW frozen inventory after the reduced build, exercises the GUI and a non-native file dialog, Unicode text, embedded FFprobe and XML export both offscreen and with the retained Windows platform plugin. That run, plus interactive Windows testing, must confirm the reduction. This environment cannot produce an authentic Windows inventory; none is fabricated. The absence of unused Qt modules must be read from the new artifact, not assumed from exclusion settings.
