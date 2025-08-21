import pytest
from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication

from aiwand.ui.widgets import RoundedWidget


@pytest.fixture(scope="session")
def qapp_session():
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


def test_rounded_widget_instantiates_and_paints(qapp_session):
    w = RoundedWidget(radius=12, bg_color="#FFAABB", border_color="#112233", shadow=True)
    w.resize(120, 80)
    # Render to an offscreen pixmap to exercise paintEvent
    pm = QtGui.QPixmap(w.size())
    pm.fill(QtGui.QColor("white"))
    painter = QtGui.QPainter(pm)
    w.render(painter)
    painter.end()
    # Basic sanity: pixmap should have non-zero size
    assert pm.width() == 120 and pm.height() == 80


# Intentionally no qtbot usage to avoid pytest-qt dependency.
