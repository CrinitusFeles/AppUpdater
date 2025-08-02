from .check_for_update import (check_for_updates, get_releases_list,  # noqa: F401
                               get_latest_release)

__version__ = '0.1.2'

try:
    import PyQt6  # noqa: F401
    from .pyqt_widget import UpdateCheckerDialog  # noqa: F401
except ImportError:
    import PySide6  # noqa: F401
    from .pyside_widget import UpdateCheckerDialog  # noqa: F401