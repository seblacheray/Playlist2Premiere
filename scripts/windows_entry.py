"""Frozen entry point, with a CI-only packaging verification path."""
import sys


def packaging_smoke_test(source, destination):
    from pathlib import Path
    from PySide6.QtWidgets import QApplication, QFileDialog
    from playlist2premiere.gui import Window
    from playlist2premiere.probe import find_ffprobe, probe
    from playlist2premiere.timeline import build_timeline
    from playlist2premiere.xml_export import write_xml
    app = QApplication([])
    window = Window()
    window.show()
    app.processEvents()
    window.playlist.setText(str(source))
    window.directory.setText(str(Path(source).parent))
    dialog = QFileDialog(window)
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    dialog.setDirectory(str(Path(source).parent))
    dialog.show()
    app.processEvents()
    if not window.isVisible() or not dialog.isVisible():
        raise RuntimeError('Qt Widgets window/dialog failed to start')
    dialog.close()
    bundled = Path(sys._MEIPASS) / 'ffprobe.exe'
    if Path(find_ffprobe()) != bundled or not bundled.is_file():
        raise RuntimeError('Embedded FFprobe was not selected')
    media = probe(Path(source))
    if not media.audio:
        raise RuntimeError('Audio missing in smoke fixture')
    write_xml(build_timeline([media]), Path(destination))
    window.close()
    app.processEvents()


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--packaging-smoke-test':
        try:
            packaging_smoke_test(sys.argv[2], sys.argv[3])
        except Exception:
            import traceback
            from pathlib import Path
            Path(sys.argv[3] + '.error.txt').write_text(traceback.format_exc(), encoding='utf-8')
            sys.exit(1)
    else:
        from playlist2premiere.gui import main
        main()
