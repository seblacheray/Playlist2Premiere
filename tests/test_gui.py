from fractions import Fraction
from PySide6.QtWidgets import QApplication
from playlist2premiere.gui import Window
from playlist2premiere.probe import Media


def test_gui_summary_and_export_gating(tmp_path, monkeypatch):
    monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    app = QApplication.instance() or QApplication([])
    window = Window()
    assert not window.export.isEnabled()
    source = Media(tmp_path / 'clip.mp4', Fraction(2), Fraction(24000, 1001), 640, 360, 0, Fraction(0), ())
    window.complete([source, source], [])
    assert window.export.isEnabled()
    assert window.fps.text() == '24000/1001'
    assert 'Clips analysés : 2' in window.summary.toPlainText()
    window.fps.setText('29.97')
    assert not window.export.isEnabled()
    window.complete([source], ['Fichier manquant'])
    assert not window.export.isEnabled()
    assert 'Fichier manquant' in window.summary.toPlainText()
    window.close()
    app.processEvents()
