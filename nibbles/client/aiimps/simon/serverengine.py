# import circular list here. -.-
import string
import threading
import datetime
from nibbles.circularlist import *
from nibbles.nibble import *
from nibbles.client.aiimps.simon.boardcopy import *
from nibbles.server.serverexceptions import *


""" Engine stats:
        INIT = 0
        RUNNING = 1
        ENDED = 2"""
INIT = 0
RUNNING = 1
ENDED = 2


class Engine():
    """This is a hard copy of the server engine. It is modified to
        grant higher execution speed which is necessary for the
        training simulation."""
    def __init__(self, randobj):
        """Initialize the engine.
            Arguments:
                random -- object which proviedes a randint method that
                clones bahaviour of random.randint(...)"""

        # Initializes the engine.
        self._nibblelist = CircularList()
        # Create a list which holds all nibble ids.
        self._idlist = string.ascii_letters

        self._nibblestartenergy = 35
        self._fieldspernibble = 3
        self._foodpernibble = 1
        self._energyperfood = 5
        self._turntimeout = 5
        self._status = INIT
        self._currentnibbleid = None
        self._currentround = 0
        self._starttimer = None
        self._energycostlist = [1, 2, 5, 2, 3, 6, 5, 6, 7]
        self._rounds = 10

        # Create the board
        self._board = None
        # Create CMPDummy. Hsa to be replaced!
        self._cmp = None
        # Set the random object
        self._random = randobj
        # Lock object
        self._lock = threading.RLock()

    def register(self):
        """Registeres a new nibble.
            Return:
                The id (char) of new nibble.
            Raises:
                RegisterNibbleFailedException"""
      #  with self._lock:
       #     print "Hallo!"

        self._lock.acquire()
        if len(self._nibblelist) == len(self._idlist):
            raise RegisterNibbleFailedException("No more IDs left."
                        + "Cannot register more nibbles!")

        if self._status == RUNNING:
            raise RegisterNibbleFailedException("Game is running."
                        + " Registration disabled.")

        nibbleid = self._idlist[len(self._nibblelist)]
        nibble = Nibble(nibbleid, self._nibblestartenergy)
        self._nibblelist.append(nibble)
        self._lock.release()
        return nibbleid

    def killnibble(self, nibbleid):
        """Kills a nibble (set energy to zero) and remove it from the board.
            Argument:
                nibbleid -- (char) The id of the nibble to kill.
            Raises:
                NoSuchNibbleIDException"""
        nibble = None
        try:
            nibble = self.getnibblebyid(nibbleid)
        except NoSuchNibbleIDException, e:
            raise e
        else:
            nibble._energy = 0
            self._board.settoken(".", nibble._xpos, nibble._ypos)

    def getnibblebyid(self, nibbleid):
        """Returns a reference to the nibble with nibbleid.
            Arguments:
                nibbleid -- (char) The id of the nibble.
            Return:
                Reference to the nibble.
            Raises:
                NoSuchNibbleIDException"""
        searchednibble = None
        for nibble in self._nibblelist:
            if nibble.getname() == nibbleid:
                searchednibble = nibble
                break
        if not searchednibble:
            msg = "No such nibble with ID %s" % (nibbleid)
            raise NoSuchNibbleIDException(msg)
        else:
            return searchednibble

    def getcurrentnibbleid(self):
        """Get the current nibble.
            Return:
                Reference to the nibble. None if the game is not running."""
        if self._status != RUNNING:
            return None
        else:
            return self.getnibblebyid(self._currentnibbleid)._NAME

    def getgamestatus(self):
        """Get the status of the game.
            Return: INIT, RUNNING or ENDED"""
        return self._status

    def setfoodpernibble(self, number):
        """Sets the amount of food to be dropped per nibble each round.
            Arguments:
                number --  (integer) the amount of the food."""
        self._foodpernibble = number

    def setfieldspernibble(self, number):
        """Sets the number of fields to be added to the board per nibble.
            Arguments:
                number -- (integer) the number of fields
                (both, x and y directoin)"""
        self._fieldspernibble = number

    def setrounds(self, number):
        """Sets the number of rounds the game should last.
            Arguments:
                number -- (integer) the number of rounds"""
        self._rounds = number

    def setturntimeout(self, seconds):
        """Sets the timeout of one turn in seconds. When it's nibble X's turn
            and X does not move within the given period, the engine assumes
            that X does not want to move and continues.
            Arguments:
                seconds -- (integer) the timeout as integer"""
        self._turntimeout = seconds

    def setcmp(self, cmp):
        """Sets the command processor of the engine.
            Arguments:
                cmp -- (CommandProcessor) The CMP to use. Can also be a dummy
                       Which implements the behaviour of the cmp that is
                       called by the engine."""
        self._cmp = cmp

    def getboard(self):
        """Get the board.
            Return:
                board -- (Board) The instance of board that is used
                         in the engine."""
        return self._board

    def setgamestart(self, date):
        """Sets the time when the game begins and executes the timer which
            calls self.run() when the game begins.
            Arguments:
                date -- (datetime.datetime) the time"""
        self._gamestart = date
        now = datetime.datetime.now()
        waittime = (date - now).total_seconds()
        self._timer = threading.Timer(waittime, self._startgame)
        self._timer.start()

    def _startgame(self):
        """Starts the game"""
        # Create board
        boardsize = self._fieldspernibble * len(self._nibblelist)
        self._board = Board(boardsize, boardsize)
        # set first round
        self._currentround = 1
        # Place nibbles randomly on the board TODO
        for n in self._nibblelist:
            x, y = 0, 0
            while True:
                x = self._random.randint(0, self._board.getwidth())
                y = self._random.randint(0, self._board.getheight())
                if self._board.gettoken(x, y) == '.':
                    break
            self._board.settoken(n, x, y)
            n.setpos(x, y)

        # Set first player
        self._currentnibbleid = self._nibblelist.current().getname()
        # send board information to first nibble
        self._sendtocmp()
        self._status = RUNNING

    def execturn(self, nibbleid, direction):
        """Moves a nibble aka execute one game turn:
            1.) Get the direction in which current nibble moves.
            2.) Use up energy for move
            3.) Combat / Food consumption
            4.) Move the nibble on the actual board
            5.) Set new current nibble"""

        # Wrong player wanted to move
        if not nibbleid == self._currentnibbleid:
            return -1
        if not self._status == RUNNING:
            return -1

        nibble = self.getnibblebyid(self._currentnibbleid)

        # Nibble regenerates stamina:
        if nibble.getstamina() < 3:
            nibble.setstamina(nibble.getstamina() + 1)

        # 1.) direction
        deltas = self._calcdirectionoffset(direction)
        # use up stamina
        if len(deltas) >= 2 and nibble.getstamina() >= 3:
            nibble.setstamina(0)
        # if nibble wants to sprint but has not enough stamina just
        # doe a single step.
        elif len(deltas) >= 2 and nibble.getstamina() < 3:
            deltas = (deltas[0],)

        for (dx, dy) in deltas:
            self._nibblestep(nibble, dx, dy)

        #Use up energy for move
        energycosts = self._calcenergycosts(direction)
        nibble.setenergy(nibble.getenergy() - energycosts)

        # 5.) set next player
        self._nextnibble()
        return 0

    def _nibblestep(self, nibble, dx, dy):
        """Moves the nibble one step wide. This is needed if the nibble does a
            knight like chess move.
            Arguments:
                nibble -- (Nibble) The current moving nibble
                dx, dy -- (int) The directino offsets calculated
                          by engine._calcdirectionoffset()."""

        #todo: nibble alive?
        (oldx, oldy) = nibble.getpos()
        newx = oldx + dx
        newy = oldy + dy

        #combat / food consumption
        token = self._board.gettoken(newx, newy)
        if token in self._nibblelist and token != nibble:
            self._fight(nibble, token)
        elif token == "*":
            nibble.setenergy(nibble.getenergy() + self._energyperfood)

        # if not killed, move the nibble
        if nibble.isalive():
            self._board.movetoken(oldx, oldy, newx, newy)
            nibble.setpos(newx, newy)
        # if killed, remove nibble from the board
        else:
            self._board.settoken('.', oldx, oldy)

    def _endgame(self):
        """"""
        self._status = ENDED

    def _calcdirectionoffset(self, number):
        """Takes a direction number between 0 and 24 to calculate the x and
            y offsets of the given direction.
            Argument:
                number - (int) between 0 and 24 which describes the direction.
            Return:
                ((dx1, dy1), (dx2, dy2) -- touple of two int tuples which hold
                the realtive x and y offsets to perform the move. If only one
                step is needed to perform this step, the second touple is None.
            Raises:
                ValueError"""
        if not 0 <= number <= 24:
            msg = (("No such direction description: %d. Must "
                  + "be between 0 and 24!") % number)
            raise ValueError(msg)

        (x, y) = (number % 5 - 2, number / 5 - 2)

        # break up double steps into single steps
        # if it's just a single step
        if max(abs(x), abs(y)) == 1:
            return((x, y),)
        # 'knight' like step
        elif abs(x * y) == 2:
            if abs(x) == 2:
                return ((x / 2, 0), (x / 2, y))
            else:
                return ((0, y / 2), (x, y / 2))
        # double step to the corners or in one direction
        else:
            return ((x / 2, y / 2), (x / 2, y / 2))

    def _calcenergycosts(self, number):
        """Calculate the energy that the nibble has to spend to move to the
            field given by dx and dy.
            Argument:
                number - (int) between 0 and 24 which describes the direction.
            Return:
                energycosts -- (int) the energy costs as interger"""

        if not 0 <= number <= 24:
            msg = (("No such direction description: %d. Must "
                  + "be between 0 and 24!") % number)
            raise ValueError(msg)

        (x, y) = (number % 5 - 2, number / 5 - 2)
        x = abs(x)
        y = abs(y)
        return self._energycostlist[y + x * 3]

    def _fight(self, attacker, defender):
        """Simulates the fight between two nibbles. Kills the nibble
            that looses the fight and calculate energy for the winner.
            Arguments:
                attacker -- (nibble) the attacking nibble
                defender -- (nibble) the defending nibble"""
        if defender.getenergy() > attacker.getenergy():
            defender.setenergy(defender.getenergy() + attacker.getenergy())
            self.killnibble(attacker.getname())

        else:
            attacker.setenergy(defender.getenergy() + attacker.getenergy())
            self.killnibble(defender.getname())

    def _dropfood(self):
        """Place food on the baord randomly. The amount of food dropped is
            the number of nibbles * self._foodpernibble. If food drops on a
            nibble the lucky one can eat at once."""
        for i in xrange(self._foodpernibble * len(self._nibblelist)):
            rx = self._random.randint(0, self._board._width - 1)
            ry = self._random.randint(0, self._board._height - 1)
            # if a nibble is on the chosen location, feed it
            token = self._board.gettoken(rx, ry)
            if isinstance(token, Nibble):
                token.setenergy(token.getenergy() + self._energyperfood)
            else:
                self._board.settoken("*", rx, ry)

    def _nextnibble(self):
        """Sets the next nibble and restarts the timer."""
        while 1:
            nibble = self._nibblelist.next()

            # if first nibble is reached, one turn has passed
            if(self._nibblelist[0] == nibble):
                # if this was the last round stop the game
                if self._currentround >= self._rounds:
                    self._endgame()
                    return

                self._currentround += 1
                self._dropfood()

            # if nibble is dead, continue with loop
            if not nibble.isalive():
                self._currentnibbleid = nibble.getname()
                self._sendtocmp()
            else:
                break

        self._currentnibbleid = nibble.getname()
        self._sendtocmp()

    def _sendtocmp(self):
        """Sends a message to the cmp which holds nibbleid,
            the part of the board that's visible to the nibble
            and its energy."""
        nibble = self.getnibblebyid(self._currentnibbleid)
        energy = 0
        boardview = ""
        if nibble.isalive():
            energy = nibble.getenergy()
            (x, y) = nibble.getpos()
            boardview = self._board.getnibbleview(nibble, True)
        self._cmp.send(self._currentnibbleid, boardview, energy)
