"""Widgets-only application: avoid optional PDF and virtual-keyboard plugins.

Use PyInstaller's supported Qt dependency collector, then filter only plugins
that this application never uses, before binary dependency analysis. Do not
remove DLLs required by surviving plugins or extensions.
"""
from pathlib import PurePath
from PyInstaller.utils.hooks.qt import add_qt6_dependencies

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
_unused_plugins = {'qpdf', 'qvirtualkeyboard', 'qtvirtualkeyboardplugin'}
binaries = [entry for entry in binaries if PurePath(entry[0]).stem.lower() not in _unused_plugins]
excludedimports = ['PySide6.QtPdf', 'PySide6.QtPdfWidgets', 'PySide6.QtQml',
                   'PySide6.QtQuick', 'PySide6.QtQuickWidgets', 'PySide6.QtVirtualKeyboard']
