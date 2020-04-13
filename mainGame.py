import PySimpleGUI as sg
import chess
import listboxPopup
import winsound
#import cProfile

from engineTab import EngineTab
from popularityTab import PopularityTab
from notationTab import NotationTab
from chessBoardUI import ChessBoardUI


CONFIG_FILE ='config.cfg'

promotion_options=['Queen','Rook','Bishop','Knight']
promotion_map = { 'Queen' : chess.QUEEN, 'Rook' : chess.ROOK, 'Bishop' : chess.BISHOP, 'Knight' : chess.KNIGHT }

## Checks move legality and makes it
def makeMove(chessBoard, window, move, engineTab, popularityTab,notationTab) :
    if move in chessBoard.legal_moves :
        # make move
        notationTab.makeMove(move,window)
        chessBoard= notationTab.getBoard()

        # update others
        window.FindElement("_popularity_table_").Update(values=[[]])
        window.FindElement("_analisys_table_").Update(values=[[]])
        window.FindElement("_games_table_").Update(values=[[]])
        window.FindElement('_make_popularity_move_').Update(disabled=True)
        window.FindElement('_goto_game_').Update(disabled=True)
        engineTab.setBoard(chessBoard,window)
        popularityTab.setBoard(chessBoard,window)

    else :
        winsound.MessageBeep()
    return chessBoard

## Checks whether candidate move is pawn promotion, if yes, asks what piece should be promoted
def detectPromotion(move,chessBoard) :
    if chessBoard.piece_type_at(move.from_square) == chess.PAWN :
        promotion=False
        if (chessBoard.color_at(move.from_square) == chess.WHITE and move.to_square > chess.H7 and move.from_square > chess.H6) :
            promotion=True
        if(chessBoard.color_at(move.from_square) == chess.BLACK and move.to_square < chess.A2 and move.from_square < chess.A3) :
            promotion=True
        if promotion :            
            promotion_piece=listboxPopup.showListBoxPopup(promotion_options,'Promotion')
            move.promotion=promotion_map[promotion_piece]
    return move

def playGame():
    menu_def = [['&File', ['&New', '&Open','&Save','Save &As','E&xit' ]],['&Board',['&Flip']]]
    sg.ChangeLookAndFeel('BrownBlue')
    # create initial board setup

    notationTab = NotationTab(CONFIG_FILE)
    chess_board= notationTab.getBoard()

    engineTab=EngineTab(chess_board,CONFIG_FILE)
    popularityTab=PopularityTab(chess_board,CONFIG_FILE)
    chessBoardUI=ChessBoardUI(CONFIG_FILE)

    rightPane = [[notationTab.getNotationTab()],[engineTab.getTabGroup(),popularityTab.getPopularityTab()]]

                      


    # the main window layout
    layout = [[sg.Menu(menu_def, tearoff=False)],
              [sg.Column([[sg.TabGroup([[sg.Tab('Board',chessBoardUI.createBoardTab(chess_board))]])],
                          [popularityTab.getGamesTab()]]),sg.Column(rightPane)]]
              

    window = sg.Window('Chess', default_button_element_size=(12,1), auto_size_buttons=False, icon='kingb.ico',return_keyboard_events=True,resizable=True).Layout(layout)
    window.Finalize()

    popularityTab.onWindowFinalize(window,chess_board)
    notationTab.onWindowFinalize(window)
    # ---===--- Loop taking in user input --- #
    i = 0

    while True:
        button, value = window.Read()
        #prof=cProfile.Profile()
        #prof.enable()
        #window.FindElement('_error_message_').Update(value='')

        if button == 'Exit':
            window.Close()
            break

        if button == None :
            break

        # Menu and buttons evaluation


        if button == 'New':
            notationTab.newGame(window)
            chess_board=notationTab.getBoard()
            engineTab.setBoard(chess_board,window)
            popularityTab.setBoard(chess_board,window)
            chessBoardUI.clearSquare()

        if button == 'Open':
            notationTab.openGame(window)
            chess_board=notationTab.getBoard()
            engineTab.setBoard(chess_board,window)
            popularityTab.setBoard(chess_board,window)
            chessBoardUI.clearSquare()

        if button == 'Save':
            notationTab.saveGame()

        if button == 'Save As':
            notationTab.saveGameAs()
            
         # check events in engine tab class
        move=engineTab.onEvent(window, button, value, chess_board)
        if move != None:
            chess_board=makeMove(chess_board,window,move,engineTab,popularityTab,notationTab)
            chessBoardUI.clearSquare()

        # check events in popularity tab class
        move= popularityTab.onEvent(window, button, value, chess_board)
        if move != None:
            chess_board=makeMove(chess_board,window,move,engineTab,popularityTab,notationTab)
            chessBoardUI.clearSquare()

        # check events in notation tab class
        if notationTab.onEvent(window, button, value) :
            chess_board = notationTab.getBoard()
            engineTab.setBoard(chess_board,window)
            popularityTab.setBoard(chess_board,window)
            chessBoardUI.clearSquare()
       
        # Move
        move=chessBoardUI.onEvent(window, button, value, chess_board)
        if move != None:
            move=detectPromotion(move,chess_board)
            chess_board=makeMove(chess_board,window,move,engineTab,popularityTab,notationTab)
                    
    
        # redraw board and notation
        chessBoardUI.redrawBoard(window, chess_board)
        #prof.disable()
        #prof.dump_stats("readLoop_profile")
    engineTab.close()
    popularityTab.close()
    chessBoardUI.stopUI()
    notationTab.stop()

    print("EXIT\n")
   
playGame()
