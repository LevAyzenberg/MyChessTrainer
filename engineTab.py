import PySimpleGUI as sg
import chess
import chess.engine
import threading
import copy
import configparser

## Class for comunicating with engine thread
class EngineThreadInfo :
    def __init__(self,chessBoard,configFile):
        self.lock = threading.Lock()
        self.stopThread = False
        self.newBoard = False
        self.showLines = False
        self.board = copy.deepcopy(chessBoard)
        self.configFile=configFile
        
    def setBoard(self,chessBoard):
        with self.lock:
            self.board = copy.deepcopy(chessBoard)
            self.newBoard = True
            self.showLines = False

    def checkNewBoard(self) :
        with self.lock:
            return self.newBoard

    def setShowLines(self,value) :
        with self.lock:
            self.showLines=value
         
    def getShowLines(self) :
        with self.lock:
            return self.showLines
        
    def getBoard(self) :
        with self.lock:
            self.newBoard=False
            return copy.deepcopy(self.board)

    def stop(self) :
        with self.lock:
            self.stopThread = True

    def checkStop(self) :
        with self.lock:
            return self.stopThread

    def getConfigFile(self) :
        return self.configFile

                

# Calculates score from stockfish output
def calcScore(score) :
    out_score=(float(score.relative.score())/100.0)
    if score.turn == chess.BLACK :
        out_score=-out_score
    return '%.2f' % out_score

## Thread running engine score
def engineInfoThread(engineThreadInfo, window) :
    config = configparser.RawConfigParser()
    config.read(engineThreadInfo.getConfigFile())
    enginePath=config.get('engine','enginePath')
    print('engineInfoThread: path to engine=',enginePath)
    engine=chess.engine.SimpleEngine.popen_uci(enginePath)

    # Change elements state
  
    while True :
        chessBoard=engineThreadInfo.getBoard()

        if engineThreadInfo.checkStop() :
            print('engineInfoThread: exit')
            break

        current_multipv_seldepth=0
        multipv_dict={}
        
        with engine.analysis(chessBoard, multipv=10,options={'Contempt':0}) as analysis:
            for info in analysis:

                # In case of new board exit current analisys.
                if engineThreadInfo.checkNewBoard() :
                    try :
                        window.FindElement('_analisys_table_').Update(values=[])
                        window.FindElement('_make_lines_move_').Update(disabled=True)
                    except:
                        print('engineInfoThread: FALED TO CLEAR ANALISYS TABLE!!!')
                    break

                if engineThreadInfo.checkStop() :
                    print('engineInfoThread: STOP')
                    break

                # Show lines
                if engineThreadInfo.getShowLines() :
                    if info.get('multipv') != None :
                        #if depth growed clear dict
                        if info.get('seldepth') > current_multipv_seldepth:
                            multipv_dict={}
                            current_multipv_seldepth=info.get('seldepth')
                            keys_sum=0

                        # update dict
                        key=info.get('multipv')
                        value=[chessBoard.san(info.get('pv')[0]),calcScore(info.get('score'))]
                        if (key not in multipv_dict.keys()) or (multipv_dict[key] !=value) :
                            multipv_dict[key]= value

                            # convert dict to list
                            multipv_table=[]
                            for key in  multipv_dict.keys():
                                multipv_table.append([key, multipv_dict[key][0],multipv_dict[key][1]])
                            #sort & show
                            multipv_table.sort(key=(lambda d : d[0]))

                            # don't update for low lines, avoid blinking
                            keys_sum+=11-key
                            if keys_sum > 20:
                                keys_sum=0
                                try:
                                    window.FindElement('_analisys_table_').Update(values=multipv_table)
                                except:
                                    print('engineInfoThread: FALED TO UPDATE ANALISYS TABLE!!!')

                # update score and depth
                if info.get('multipv') == 1:
                    score=calcScore(info.get("score", 0))
                    try:
                        window.FindElement('_current_computer_depth_').Update(value=str(info.get("depth", 0)))
                        window.FindElement('_current_computer_score_').Update(value=score)
                    except:
                        print('engineInfoThread: FALED TO UPDATE SCORE!!!')


    engine.quit()
    print('engineInfoThread: EXIT\n')
 


#Class cares on engine UI and functionality
class EngineTab :
    def __init__(self, chessBoard,configFile) :
        self.tabGroup=sg.TabGroup([[sg.Tab('Engine',[[sg.RButton('Start', key='_start_analisys_',size=(7,1)),sg.Text('Depth:'),sg.Text('     ',key='_current_computer_depth_'),sg.Text('Score:'),sg.Text('       ',key='_current_computer_score_',justification='left')],
                                   [sg.RButton('Lines', key='_show_lines_',disabled=True,size=(7,1)),sg.RButton('Move', key='_make_lines_move_',disabled=True,size=(7,1))],
                                   [sg.Table([['  ','       ','']],headings=[' # ','Line','Eval'],auto_size_columns=False,col_widths=[5,13,9],justification='center', key='_analisys_table_',num_rows=10)]])]])
        self.threadInfo=None
        self.thread=None
        self.configFile=configFile

    def getTabGroup(self):
        return self.tabGroup


    def changeUiToStartMode(self,window) : 
        window.FindElement('_start_analisys_').Update('Stop')
        window.FindElement('_show_lines_').Update(disabled=False)
        window.FindElement('_make_lines_move_').Update(disabled=True)
        window.FindElement('_analisys_table_').Update(values=[])
        window.FindElement('_analisys_table_').bind('<Double-Button-1>','double_click_')


    def changeUiToStopMode(self,window) :
        window.FindElement('_start_analisys_').Update('Start')
        window.FindElement('_show_lines_').Update(disabled=True)
        window.FindElement('_make_lines_move_').Update(disabled=True)
        window.FindElement('_analisys_table_').Update(values=[])

    def onEvent(self,window, button, value, chessBoard) :
        if button == '_start_analisys_':
            if window.FindElement('_start_analisys_').GetText() == 'Start' :
                self.changeUiToStartMode(window)
                self.threadInfo=EngineThreadInfo(chessBoard,self.configFile)
                self.threadObject = threading.Thread(target=engineInfoThread, args=(self.threadInfo,window))
                self.threadObject.start()
            else :
                self.threadInfo.stop()
                self.changeUiToStopMode(window)
                self.threadObject = None
                self.threadInfo=None
        if button == '_show_lines_':
            if self.threadInfo != None:
                self.threadInfo.setShowLines(True)
            window.FindElement('_make_lines_move_').Update(disabled=False)

        if (button == '_make_lines_move_') or (button == '_analisys_table_double_click_'):
            if len(value['_analisys_table_']) > 0:
                index = value['_analisys_table_'][0]
                move=chessBoard.parse_san(window.FindElement('_analisys_table_').Get()[index][1])
                return move
        return None

    def close(self) :
        if self.threadInfo != None:
            self.threadInfo.stop()
        
            
    def setBoard(self,chessBoard,window) :
        if self.threadInfo != None :
            self.threadInfo.setBoard(chessBoard)
    
            
