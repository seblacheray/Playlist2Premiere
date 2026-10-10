from fractions import Fraction
from pathlib import Path
import sys
from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QFileDialog, QSpinBox, QMessageBox, QTextEdit)
from .playlist import read_playlist
from .paths import MediaResolver
from .probe import probe
from .timeline import Settings, build_timeline
from .xml_export import write_xml


class Analyze(QObject):
    completed = Signal(object, object)
    progress = Signal(str)
    finished = Signal()

    def __init__(self, playlist, directory):
        super().__init__()
        self.playlist, self.directory = playlist, directory

    @Slot()
    def run(self):
        media, errors, cache = [], [], {}
        try:
            entries = read_playlist(self.playlist)
            resolver = MediaResolver(self.playlist.parent, self.directory)
            for position, entry in enumerate(entries, 1):
                self.progress.emit(f'Analyse {position}/{len(entries)} : {entry.path}')
                try:
                    path = resolver.resolve(entry.path)
                    if path not in cache:
                        cache[path] = probe(path)
                    media.append(cache[path])
                except Exception as exc:
                    errors.append(f'Entrée {entry.index} — {entry.path} : {exc}')
        except Exception as exc:
            errors.append(str(exc))
        self.completed.emit(media, errors)
        self.finished.emit()


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Playlist2Premiere')
        self.resize(800, 580)
        self.media, self.errors = [], []
        self.thread = None
        self.browse_buttons = []
        widget = QWidget()
        self.setCentralWidget(widget)
        layout = QVBoxLayout(widget)
        self.playlist = QLineEdit()
        self.directory = QLineEdit()
        for label, field, callback in [('Playlist', self.playlist, self.choose_playlist), ('Dossier des médias', self.directory, self.choose_directory)]:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            row.addWidget(field)
            button = QPushButton('Parcourir…')
            button.clicked.connect(callback)
            self.browse_buttons.append(button)
            row.addWidget(button)
            layout.addLayout(row)
            field.textChanged.connect(self.invalidate)
        self.analyze = QPushButton('Analyser la playlist')
        self.analyze.clicked.connect(self.start_analysis)
        layout.addWidget(self.analyze)
        row = QHBoxLayout()
        self.width, self.height = QSpinBox(), QSpinBox()
        for spin, value in [(self.width, 1920), (self.height, 1080)]:
            spin.setRange(1, 32768)
            spin.setValue(value)
            spin.valueChanged.connect(self.refresh)
        self.fps = QLineEdit('30000/1001')
        self.fps.setToolTip('Cadence exacte : 24, 25, 24000/1001 ou 30000/1001. 29.97 est une approximation non acceptée.')
        self.fps.textChanged.connect(self.refresh)
        for label, control in [('Largeur', self.width), ('Hauteur', self.height), ('Cadence', self.fps)]:
            row.addWidget(QLabel(label))
            row.addWidget(control)
        layout.addLayout(row)
        self.auto = QPushButton('Reprendre les paramètres de la première vidéo')
        self.auto.clicked.connect(self.auto_settings)
        layout.addWidget(self.auto)
        self.summary = QTextEdit()
        self.summary.setReadOnly(True)
        layout.addWidget(self.summary)
        self.status = QLabel('Choisissez une playlist et un dossier, puis lancez l’analyse.')
        layout.addWidget(self.status)
        self.export = QPushButton('Exporter le XML…')
        self.export.setEnabled(False)
        self.export.clicked.connect(self.save)
        layout.addWidget(self.export)

    def choose_playlist(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Playlist', '', 'Playlists (*.pls *.mpcpl)')
        if path:
            self.playlist.setText(path)

    def choose_directory(self):
        path = QFileDialog.getExistingDirectory(self, 'Dossier des médias')
        if path:
            self.directory.setText(path)

    def invalidate(self):
        self.media, self.errors = [], []
        self.export.setEnabled(False)
        self.summary.clear()

    def start_analysis(self):
        playlist, directory = Path(self.playlist.text()), Path(self.directory.text())
        if not playlist.is_file() or not directory.is_dir():
            QMessageBox.warning(self, 'Sélection invalide', 'Sélectionnez une playlist existante et un dossier de médias.')
            return
        self.invalidate()
        self.thread = QThread(self)
        self.worker = Analyze(playlist, directory)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.status.setText)
        self.worker.completed.connect(self.complete)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.analysis_finished)
        self.analyze.setEnabled(False)
        for button in self.browse_buttons:
            button.setEnabled(False)
        self.playlist.setEnabled(False)
        self.directory.setEnabled(False)
        self.thread.start()

    def analysis_finished(self):
        self.analyze.setEnabled(True)
        for button in self.browse_buttons:
            button.setEnabled(True)
        self.playlist.setEnabled(True)
        self.directory.setEnabled(True)

    def complete(self, media, errors):
        self.media, self.errors = media, errors
        self.auto_settings()
        self.status.setText('Analyse terminée.' if not errors else 'Export bloqué : corrigez les erreurs, puis relancez l’analyse.')

    def auto_settings(self):
        if self.media:
            first = self.media[0]
            self.width.setValue(first.width)
            self.height.setValue(first.height)
            self.fps.setText(str(first.fps))
        self.refresh()

    def timeline(self):
        return build_timeline(self.media, Settings(self.width.value(), self.height.value(), Fraction(self.fps.text())))

    def refresh(self):
        if not hasattr(self, 'summary'):
            return
        self.export.setEnabled(False)
        lines = [f'Clips analysés : {len(self.media)}', f'Médias manquants / illisibles / erreurs : {len(self.errors)}']
        if self.media:
            try:
                timeline = self.timeline()
                lines += [f'Séquence : {timeline.settings.width} × {timeline.settings.height}, {timeline.settings.fps} images/s', f'Durée estimée : {float(timeline.exact_duration):.3f} s ; montage : {timeline.duration} images', 'Cadences sources : ' + ', '.join(sorted({str(m.fps) for m in self.media})), f'Pistes audio sources : {sum(len(m.audio) for m in self.media)} (canaux conservés séparément)']
                self.export.setEnabled(not self.errors)
            except Exception as exc:
                lines.append(f'Paramètres invalides : {exc}')
            lines.extend(dict.fromkeys(w for m in self.media for w in m.warnings))
        lines.extend(self.errors)
        self.summary.setPlainText('\n'.join(lines))

    def save(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Exporter', 'sequence.xml', 'XML (*.xml)')
        if not path:
            return
        destination = Path(path)
        if destination.suffix.lower() != '.xml':
            destination = destination.with_suffix('.xml')
        if destination.exists() and QMessageBox.question(self, 'Remplacer le XML', 'Ce fichier existe déjà. Le remplacer ?') != QMessageBox.StandardButton.Yes:
            return
        try:
            write_xml(self.timeline(), destination, Path(self.playlist.text()).stem)
            QMessageBox.information(self, 'Export terminé', 'XML écrit. L’import doit être vérifié dans Premiere Pro 2026.')
        except Exception as exc:
            QMessageBox.critical(self, 'Export impossible', str(exc))

    def closeEvent(self, event):
        if self.thread and self.thread.isRunning():
            QMessageBox.information(self, 'Analyse en cours', 'Attendez la fin de l’analyse avant de fermer.')
            event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec())
