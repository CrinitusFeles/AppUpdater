import os
import sys
import asyncio
from pathlib import Path
import qasync
from loguru import logger
from app_updater.check_for_update import (Release, check_for_updates,
                                          download_release)
from PyQt6 import QtWidgets
from PyQt6 import QtGui
from PyQt6.QtCore import Qt
from PyQt6.QtCore import pyqtSignal as Signal



class UpdateCheckerDialog(QtWidgets.QWidget): # type: ignore
    download_finished: Signal = Signal(int)

    progress_bar: QtWidgets.QProgressBar
    label: QtWidgets.QLabel
    changelog_viewer: QtWidgets.QTextBrowser
    close_button: QtWidgets.QPushButton
    update_button: QtWidgets.QPushButton

    def __init__(self, release: Release) -> None:
        super().__init__()
        font = QtGui.QFont()
        font.setPixelSize(25)
        font.setBold(True)
        self.title_label = QtWidgets.QLabel('Обнаружена новая версия программы')
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.title_label.setFont(font)
        self.version_label = QtWidgets.QLabel()
        self.changelog_viewer = QtWidgets.QTextBrowser()
        self.progress_bar = QtWidgets.QProgressBar()
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.addWidget(self.title_label)
        self.main_layout.addWidget(self.version_label)
        self.main_layout.addWidget(self.changelog_viewer)
        self.main_layout.addWidget(self.progress_bar)
        self.buttons_layout = QtWidgets.QHBoxLayout()
        self.close_button = QtWidgets.QPushButton('Закрыть')
        self.update_button = QtWidgets.QPushButton('Обновить')
        self.buttons_layout.addWidget(self.update_button)
        self.buttons_layout.addWidget(self.close_button)
        self.main_layout.addLayout(self.buttons_layout)
        self.setLayout(self.main_layout)

        self.progress_bar.setVisible(False)
        self.release: Release = release
        self.version_label.setText(f'Список изменений {self.release.tag_name}:')
        self.changelog_viewer.setMarkdown(self.release.body)
        self.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint, False)
        self.setWindowFlag(Qt.WindowType.WindowShadeButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.close_button.pressed.connect(self.close)
        self.update_button.pressed.connect(self.on_download)

    def downoad_finished(self) -> None:
        dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Information,
                                       "Обновление успешно завершено",
                                       "Программа будет перезапущена")
        dialog.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        dialog.setWindowIcon(self.windowIcon())
        if dialog.exec():
            path: str = sys.argv[0]
            filename: str = os.path.basename(path)
            exe_path: str = sys.executable
            try:
                if ".exe" in filename:
                    new_exe_path = exe_path.replace(filename,
                                                    self.release.exe_name)
                    logger.debug(f'{new_exe_path=}')
                    os.execv(new_exe_path, [new_exe_path])
                else:
                    new_exe_path: str = str(Path.cwd() / self.release.exe_name)
                    logger.debug(f'You run script from sources. '\
                                 f'For running exe open: {new_exe_path}')
                #     logger.debug(f'{new_exe_path=}')
                #     self.close()
                #     os.system(new_exe_path)
            except Exception as err:
                logger.exception(err)

    @qasync.asyncSlot()
    async def on_download(self) -> None:
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        async for progress in download_release(self.release):
            self.progress_bar.setValue(progress)
        self.progress_bar.setVisible(False)
        self.downoad_finished()


if __name__ == '__main__':
    url: str = ''
    token: str = ''
    update: Release | None = asyncio.run(check_for_updates(url, token))
    if update:
        app: QtWidgets.QApplication = QtWidgets.QApplication([])
        event_loop = qasync.QEventLoop(app)
        asyncio.set_event_loop(event_loop)
        app_close_event = asyncio.Event()
        app.aboutToQuit.connect(app_close_event.set)
        w: UpdateCheckerDialog = UpdateCheckerDialog(update)
        w.show()

        with event_loop:
            event_loop.run_until_complete(app_close_event.wait())