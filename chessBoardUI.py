import configparser
import chess
import PySimpleGUI as sg
import threading
import os
import copy

class ChessBoardUI :
    def __init__(self,configFile) :
        config = configparser.RawConfigParser()
        config.read(configFile)
        piecesPath=config.get('chessBoard','piecesPath')

        blank = os.path.join(piecesPath, config.get('chessBoard','blank'))
        bishopB = os.path.join(piecesPath, config.get('chessBoard','bishopB'))
        bishopW = os.path.join(piecesPath, config.get('chessBoard','bishopW'))
        pawnB = os.path.join(piecesPath, config.get('chessBoard','pawnB'))
        pawnW = os.path.join(piecesPath, config.get('chessBoard','pawnW'))
        knightB = os.path.join(piecesPath, config.get('chessBoard','knightB'))
        knightW = os.path.join(piecesPath, config.get('chessBoard','knightW'))
        rookB = os.path.join(piecesPath, config.get('chessBoard','rookB'))
        rookW = os.path.join(piecesPath, config.get('chessBoard','rookW'))
        queenB = os.path.join(piecesPath, config.get('chessBoard','queenB'))
        queenW = os.path.join(piecesPath, config.get('chessBoard','queenW'))
        kingB = os.path.join(piecesPath, config.get('chessBoard','kingB'))
        kingW = os.path.join(piecesPath, config.get('chessBoard','kingW'))

        # map from pieces (in chess respresentation) to images 
        self.images = {
            (chess.BISHOP,chess.BLACK): bishopB,
            (chess.BISHOP,chess.WHITE): bishopW,
            (chess.PAWN,chess.BLACK): pawnB,
            (chess.PAWN,chess.WHITE): pawnW,
            (chess.KNIGHT,chess.BLACK): knightB,
            (chess.KNIGHT,chess.WHITE): knightW,
            (chess.ROOK,chess.BLACK): rookB,
            (chess.ROOK,chess.WHITE): rookW,
            (chess.KING,chess.BLACK): kingB,
            (chess.KING,chess.WHITE): kingW,
            (chess.QUEEN,chess.BLACK): queenB,
            (chess.QUEEN,chess.WHITE) : queenW,
            (None,None) : blank
        }

        self.empty_board=[
            [[None,None],[None,None],[None,None],[None,None],[None,None],[None,None],[None,None],[None,None]],
            [[None,None],[None,None],[None,None],[None,None],[None,None],[None,None],[None,None],[None,None]],
            [[None,None],[None,None],[None,None],[None,None],[None,None],[None,None],[None,None],[None,None]],
            [[None,None],[None,None],[None,None],[None,None],[None,None],[None,None],[None,None],[None,None]],
            [[None,None],[None,None],[None,None],[None,None],[None,None],[None,None],[None,None],[None,None]],
            [[None,None],[None,None],[None,None],[None,None],[None,None],[None,None],[None,None],[None,None]],
            [[None,None],[None,None],[None,None],[None,None],[None,None],[None,None],[None,None],[None,None]],
            [[None,None],[None,None],[None,None],[None,None],[None,None],[None,None],[None,None],[None,None]]
        ]

        self.chess_board_square1=None
        self.flipped=False
        self.timeStamp=0
        self.drawnTimestamp=0
        self.lastBoardToRedraw=None
        self.window=None
        self.lock = threading.Lock()
        self.semaphore=threading.Semaphore(value=0)
        self.threadObject=None
        self.stopThread=False

    def redrawBoard(self, window, chessBoard):
        if self.threadObject == None:
            self.threadObject=threading.Thread(target=self.redrawBoardThread, args=[])
            self.threadObject.start()

        with self.lock:
            self.window=window
            self.timeStamp=self.timeStamp+1
            self.lastBoardToRedraw=copy.deepcopy(chessBoard)
        self.semaphore.release()

    def redrawBoardThread(self):
        while True:
            self.semaphore.acquire()
            with self.lock:
                chessBoard=self.lastBoardToRedraw
                window=self.window
                timeStamp=self.timeStamp
                drawnTimestamp=self.drawnTimestamp
                chess_board_square1=self.chess_board_square1
                flipped = self.flipped
                stopThread=self.stopThread

            if stopThread:
                break

            # We drawed last board
            if drawnTimestamp == timeStamp:
                continue

            ## Render board
            board = self.chessBoardToUI(chessBoard,flipped)
            try:
                for i in range(8):
                    for j in range(8):
                        color = '#B58863' if (i + j) % 2 else '#F0D9B5'

                        piece_image = self.images[tuple(board[i][j])]
                        elem = window.FindElement(key=(i, j))
                        elem.Update(button_color=('white', color), image_filename=piece_image)

                        if (chess_board_square1 != None) and (self.fromGuiToChess([i, j],flipped) == chess_board_square1):
                            elem.Widget.config(relief='sunken')
                        else:
                            elem.Widget.config(relief='raised')

                with self.lock:
                    self.drawnTimestamp = timeStamp
            except:
                print('Error while update')
                self.semaphore.release()

        print('UI thread stoped')

    ## Stops UI thread
    def stopUI(self):
        with self.lock:
            self.stopThread=True
        self.semaphore.release()

    ## Transfers UI coordinates to chess notation
    def fromGuiToChess(self,coord,flipped) :
        if flipped:
            return coord[0]*8+7-coord[1]
        else :
            return (7-coord[0])*8 + coord[1]

    ## Transfers chess notation to UI coordinates
    def fromChessToGui(self, square,flipped) :
        coord=[int((chess.H8-square)/8),square%8]
        if flipped:
            return [7-coord[0],7-coord[1]]
        else :
            return coord
        

    ## Transfer board to UI view
    def chessBoardToUI(self,chessBoard,flipped) :
        uiBoard=self.empty_board
        for i in range(chess.A1, chess.H8+1) :
            uiCoord=self.fromChessToGui(i,flipped)
            uiBoard[uiCoord[0]][uiCoord[1]]=[chessBoard.piece_type_at(i),chessBoard.color_at(i)]
        return uiBoard

    ## Renders specifc square for initial board tab
    def renderSquare(self, image, key, location):
        if (location[0] + location[1]) % 2:
            color = '#B58863'
        else:
            color = '#F0D9B5'
        return sg.RButton('', image_filename=image, size=(40, 40), button_color=('white', color), pad=(0, 0), key=key)


    ## creates initial board Tab
    def createBoardTab(self,chessBoard) :
        initial_board =self.chessBoardToUI(chessBoard,False)
    
        # the main board display layout
        board_layout = [[sg.T('      ')] + [sg.T('{}'.format(a), pad=((4,27),0), font='Any 13',key='_upper_letters_'+str(ord(a)-ord('a'))) for a in 'abcdefgh']]
        # loop though board and create buttons with images
        for i in range(8):
            row = [sg.T(str(8-i)+'  ', font='Any 13',key='left_number'+str(i))]
            for j in range(8):
                piece_image = self.images[tuple(initial_board[i][j])]
                row.append(self.renderSquare(piece_image, key=(i,j), location=(i,j)))
            row.append(sg.T(str(8-i)+'  ', font='Any 13',key='right_number'+str(i)))
            board_layout.append(row)
        # add the labels across bottom of board
        board_layout.append([sg.T('      ')] + [sg.T('{}'.format(a), pad=((4,27),0), font='Any 13',key='_lower_letters_'+str(ord(a)-ord('a'))) for a in 'abcdefgh'])
        return [[sg.Column(board_layout)]]

    def onEvent(self, window, button, value, chessBoard) :
        if button == 'Flip':
            with self.lock:
                self.flipped= not(self.flipped)
                if self.flipped :
                    lettersRange='hgfedcba'
                    numbersRange='12345678'
                else:
                    lettersRange='abcdefgh'
                    numbersRange='87654321'
            for i in range(0,8) :
                window.FindElement('_upper_letters_'+str(i)).Update(lettersRange[i])
                window.FindElement('_lower_letters_'+str(i)).Update(lettersRange[i])
                window.FindElement('left_number'+str(i)).Update(numbersRange[i]+'  ')
                window.FindElement('right_number'+str(i)).Update(numbersRange[i]+'  ')
            
        if type(button) is tuple :
            with self.lock:
                if self.chess_board_square1 == None:
                    self.chess_board_square1=self.fromGuiToChess(button,self.flipped)
                    if chessBoard.piece_at(self.chess_board_square1) == None :
                        self.chess_board_square1 = None
                else:
                    chess_board_square2=self.fromGuiToChess(button,self.flipped)
                    move=chess.Move(self.chess_board_square1,chess_board_square2)
                    self.chess_board_square1=None
                    return move
        return None

    def clearSquare(self) :
        with self.lock:
            self.chess_board_square1 = None
        
