"""
Main Console Application derived from several examples from pyqtgraph:

DesignerExample.py
VideoSpeedTest.py

"""

import os

import numpy as np

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

from time import perf_counter

from loguru import logger

app = pg.mkQApp("BUM 2.0 Application")

pg.setConfigOption('imageAxisOrder', 'row-major')

try:
    import cupy as cp
    pg.setConfigOption("useCupy", True)
    _has_cupy = True
except ImportError:
    cp = None
    _has_cupy = False

if False and _has_cupy:
    xp = cp
else:
    xp = np

## Define main window class from template
path = os.path.dirname(os.path.abspath(__file__))
uiFile = os.path.join(path, 'app.ui')
WindowTemplate, TemplateBaseClass = pg.Qt.loadUiType(uiFile)


class MainWindow(TemplateBaseClass):  
    def __init__(self):
        TemplateBaseClass.__init__(self)
        self.setWindowTitle('BUM 2.0 App')
        
        # Create the main window
        self.ui = WindowTemplate()
        self.ui.setupUi(self)

        self.setGeometry(0, 0, 3840, 2160)

        self.data = xp.ones((2160, 3840,3),dtype='uint8')

        self.ptr = 0
        self.lastTime = perf_counter()
        self.fps = None

        self.vb = pg.ViewBox()
        self.ui.graphicsView.setCentralItem(self.vb)
        self.vb.setAspectLocked()
        self.img = pg.ImageItem()
        self.vb.addItem(self.img)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(0)

        # show the UI
        self.show()

    def update(self):

        self.img.setImage(self.data * (self.ptr%256), autoLevels=False, lut=None, levels=None)

        self.ptr += 1
        now = perf_counter()
        dt = now - self.lastTime
        self.lastTime = now
        if self.fps is None:
            self.fps = 1.0/dt
        else:
            s = np.clip(dt*3., 0, 1)
            self.fps = self.fps * (1-s) + (1.0/dt) * s
        
        if self.ptr % 10 == 0:
            logger.debug("FPS = " + str(self.fps))
        #self.ui.fpsLabel.setText('%0.2f fps' % self.fps)
        app.processEvents()  ## force complete redraw for every plot
        
win = MainWindow()

if __name__ == '__main__':
    pg.exec()
