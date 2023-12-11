import os
import sys
import time
from threading import Thread
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6 import QtWidgets
from PyQt6.uic.load_ui import loadUi
from app_updater.check_for_update import Release, check_for_updates, download_release


class UpdateCheckerDialog(QtWidgets.QWidget):
    disable_updates: pyqtSignal = pyqtSignal()
    redraw_progress_bar: pyqtSignal = pyqtSignal(int)
    download_finished: pyqtSignal = pyqtSignal(int)

    progress_bar: QtWidgets.QProgressBar
    label: QtWidgets.QLabel
    changelog_viewer: QtWidgets.QPlainTextEdit
    close_button: QtWidgets.QPushButton
    update_button: QtWidgets.QPushButton
    disable_updater_checkbox: QtWidgets.QCheckBox
    def __init__(self, release: Release, frontend_file_name: str = 'frontend.ui') -> None:
        super().__init__()
        loadUi(os.path.join(os.path.dirname(__file__), f'{frontend_file_name}'), self)
        self.progress_bar.setVisible(False)
        self.release_data: Release = release
        self.label.setText(self.label.text()[:-1] + ' ' + self.release_data.name + ":")
        self.changelog_viewer.setPlainText(self.release_data.body)
        self.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint, False)
        self.setWindowFlag(Qt.WindowType.WindowShadeButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.update_button.pressed.connect(self.download_update)
        self.close_button.pressed.connect(self.close)  # type: ignore
        self.disable_updater_checkbox.stateChanged.connect(self.checkbox_handler)
        # self.download_process = DownloadProcess(self.release_data)
        self.download_finished.connect(self.downoad_finished)
        self.redraw_progress_bar.connect(self.progress_bar.setValue)

        self.downloader: Thread = Thread(name='downloader', target=self.__download_release)
        self.progress_bar_thread: Thread = Thread(name='progress_bar', target=self.__update_progress_bar)

        self.new_name = f"KPA-{self.release_data.name}.exe"

    def __download_release(self) -> None:
        download_release(self.release_data, rename=self.new_name)
        self.progress_bar.setVisible(False)
        self.download_finished.emit(0)

    def __update_progress_bar(self) -> None:
        while self.release_data.download_progress < 100:
            self.redraw_progress_bar.emit(self.release_data.download_progress)
            time.sleep(0.2)

    def downoad_finished(self) -> None:
        dialog: QtWidgets.QMessageBox = QtWidgets.QMessageBox(icon=QtWidgets.QMessageBox.Icon.Information,
                                                              title="Обновление успешно завершено",
                                                              text="Программа будет перезапущена")
        dialog.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        dialog.setWindowIcon(self.windowIcon())
        if dialog.exec():
            path: str = sys.argv[0]
            filename: str = os.path.basename(path)
            exe_path: str = sys.executable
            exe_filename: str = os.path.basename(exe_path)
            if ".exe" not in filename:
                os.execv(sys.executable, ['python'] + sys.argv)
            else:
                os.execv(exe_path.replace(exe_filename, self.new_name), ['python' + path.replace(filename,
                                                                                                 self.new_name)])

    def download_update(self) -> None:
        self.downloader.start()
        self.progress_bar_thread.start()
        self.progress_bar.setVisible(True)

    def save_checkbox_state(self) -> None:
        if self.disable_updater_checkbox.isChecked():
            self.disable_updates.emit()

    def checkbox_handler(self, state: int) -> None:
        if state:
            print('automatic update check is disabled')
        else:
            print('automatic update check is enabled ')

    def closeEvent(self, event) -> None:
        self.save_checkbox_state()

        # if self.downloader.is_alive():
        #     terminate thread
        event.accept()



if __name__ == '__main__':
    update = check_for_updates("OAI-NSU", "KPA-GUI")
    if update:
        app: QtWidgets.QApplication = QtWidgets.QApplication(sys.argv)
        w: UpdateCheckerDialog = UpdateCheckerDialog(update)
        w.show()
        app.exec()
