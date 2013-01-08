import sys
from PyQt4 import QtGui, QtCore
import string

from nibbles.nibble import Nibble


class BoardRenderer(QtGui.QWidget):
    def __init__(self, parent = None):
        QtGui.QWidget.__init__(self, parent)
        self.pen = QtGui.QPen(QtGui.QColor(0,0,0,0))
        self.pen.setWidth(3)
        self.brush = QtGui.QBrush(QtGui.QColor(255,255,255,20))

        self.char_001 = QtGui.QImage("./nibbles/gui/img/char_001.png")
        self.char_001active = QtGui.QImage("./nibbles/gui/img/char_001active.png")
        self.food = QtGui.QImage("./nibbles/gui/img/food.png")

        self.ziel1 = QtCore.QRect(165, 66, 30, 30)
        self.ziel2 = QtCore.QRect(264, 132, 30, 30)
        self.ziel3 = QtCore.QRect(297, 165, 30, 30)

        self.quelle = QtCore.QRect(0, 0,
            self.char_001.width(),
            self.char_001.height())

        #dimensions of a rectangle that's rendered on the board
        self.rectdim = 33

        self._board = None

    def setboard(self, board):
        self._board = board

    def paintEvent(self, event):
        if self._board is None:
            self._renderempty()
        else:
            widgetsize = min(self.width(), self.height())
            print widgetsize
            self.rectdim = widgetsize / self._board.getheight()
            self._render()

    def _render(self):
        painter = QtGui.QPainter(self)
        painter.setPen(self.pen)
        painter.setBrush(self.brush)

        for y in range(self._board.getheight()):
            for x in range(self._board.getwidth()):
                # Draw empty field
                painter.drawRect((self.rectdim*x),
                    (self.rectdim*y), self.rectdim - 3, self.rectdim - 3)
                token = self._board.gettoken(x, y)
                # Draw food
                if token == '*':
                    painter.drawImage(QtCore.QRect((self.rectdim*x),(self.rectdim*y),self.rectdim - 3,self.rectdim - 3), self.food, QtCore.QRect(0, 0,
                        self.food.width(),
                        self.food.height()))
                # Draw nibble
                elif isinstance(token, Nibble):
                    painter.drawImage(QtCore.QRect((self.rectdim*x),(self.rectdim*y),self.rectdim - 3,self.rectdim - 3), self.char_001, QtCore.QRect(0, 0,
                        self.char_001.width(),
                        self.char_001.height()))


    def _renderempty(self):
        painter = QtGui.QPainter(self)
        painter.setPen(self.pen)
        painter.setBrush(self.brush)

        #range in rectangles
        for y in range(10):
            for x in range(10):
                painter.drawRect((33 * x), (33 * y), 30 ,30)

#        painter.drawImage(self.ziel1, self.char_001, self.quelle)
#        painter.drawImage(self.ziel2, self.char_001active, self.quelle)
#        painter.drawImage(self.ziel3, self.food, self.quelle)



