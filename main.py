from __future__ import annotations

import sys

from PySide6 import QtWidgets

from atlas.config import load_config
from atlas.data.repository import MapRepository
from atlas.logger import configure_logging, get_logger
from atlas.services.hotkey_service import HotkeyService
from atlas.services.ocr_service import OcrService
from atlas.services.search_service import MapSearchService
from atlas.ui.main_window import MainWindow
from atlas.ui.resource_loader import ResourceLoader

logger = get_logger(__name__)


def main() -> int:
    configure_logging()
    config = load_config()

    repository = MapRepository(config.maps_data_path)
    repository.load()

    search_service = MapSearchService(repository)
    search_service.refresh()

    ocr_service = OcrService(config, repository=repository)
    hotkey_service = HotkeyService(config, ocr_service)
    resource_loader = ResourceLoader(config.static_root)

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow(
        config=config,
        search_service=search_service,
        hotkey_service=hotkey_service,
        ocr_service=ocr_service,
        resource_loader=resource_loader,
    )
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
