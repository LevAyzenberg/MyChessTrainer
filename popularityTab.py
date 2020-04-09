import PySimpleGUI as sg
import threading
import fenCache
import copy
import webbrowser

class FenCacheThreadInfo :
    def __init__(self,chessBoard,configFile):
        self.configFile=configFile
        self.lock = threading.Lock()
        self.stopThread = False
        self.chessBoard =copy.deepcopy(chessBoard)
        self.fensQueue=[copy.deepcopy(chessBoard.fen())]
        self.queueSemaphore = threading.Semaphore(value=1)
        self.window = None
        
    # sets board
    # func is function to run under lock 
    def setBoard(self,chessBoard,underLockFunc):
        with self.lock:
            self.chessBoard =copy.deepcopy(chessBoard)
            tempChessBoard=copy.deepcopy(self.chessBoard)
            try:
                tempChessBoard.pop()
            except:
                pass
                #print('No previous move, probably initial position')
            # add both previous and current positions
            self.fensQueue.append(copy.deepcopy(tempChessBoard.fen()))
            self.fensQueue.append(copy.deepcopy(chessBoard.fen()))
            underLockFunc()
        self.queueSemaphore.release()
        self.queueSemaphore.release()

    def setWindow(self,window,chessBoard,func):
        with self.lock:
            if self.window != None:
                return
            self.window=window
        self.setBoard(chessBoard,func)

    def getWindow(self):
        with self.lock:
            return self.window

    # Compares fen to currentPosition if equal runs underLockSuccessFunc
    def checkCurrentPositionFen(self,fen,underLockSuccessFunc) :
        with self.lock:
            if fen == self.chessBoard.fen():
                underLockSuccessFunc()

    # Compares fen to position before last move, if equal runs underLockSuccessFunc 
    def checkPreviousMoveFen(self,fen,underLockSuccessFunc) :
        with self.lock:
            try:
                tempChessBoard=copy.deepcopy(self.chessBoard)
                move=tempChessBoard.pop()
            except:
                #print('No previous move, probably initial position')
                return
            if fen == tempChessBoard.fen() :
                underLockSuccessFunc(tempChessBoard.san(move),fen)
                

    # returns next fen from the queue
    def getNextFenFromQueue(self) :
        self.queueSemaphore.acquire()
        with self.lock:
            if self.stopThread :
                return None
            return self.fensQueue.pop(0)

    def stop(self) :
        with self.lock :
            self.stopThread=True
        self.queueSemaphore.release()


    def isStopped(self) :
        with self.lock:
            return self.stopThread

    def getConfigFile(self) :
        return self.configFile

# returns table sorted by popularity
def sortedPopularityTable(popularityDict) :
    data=[]
    for move in popularityDict.keys() :
        try :
            games=int(popularityDict[move]['Games'])
        except:
            games=0
        try :
            depth=int(popularityDict[move]['Depth'])
        except:
            depth=0
        try :
            evaluation=float(popularityDict[move]['Eval'])
        except:
            evaluation=''
      
        data.append([move,games,depth,evaluation])

    data.sort(key=lambda d : d[1] ,reverse=True)

    i=0
    for d in data :
        d.insert(0,i+1)
        i=i+1
    return data

# react on current position cache ready
def currentPositionCacheReady(window) :
    try :
        if window != None :
            window.FindElement('_popularity_').Update(disabled = False)
            window.FindElement('_show_games_').Update(disabled = False)
        else:
            print('fenCacheThread: Still no window')
    except :
        print('fenCacheThread: unable to update buttons!!!')

# react on last move cache ready
def lastMoveCacheReady(window,move,fen) :
    cacheElement=fenCache.getCache(fen);
    popularityTable = sortedPopularityTable(cacheElement['popularity'])
    index=10000
    for p in popularityTable :
        if p[1].strip()== move.strip() :
            index=p[0]
            break
    try :
        if window != None :
            window.FindElement("_current_popularity_").Update(str(index))
        else:
            print('fenCacheThread: Still no window')
            
    except:
        print('fenCacheThread: unable to update popularity!!!')

## Thread fills fen cache in backgoround
def fenCacheThread(fenCacheThreadInfo) :
    
    fenCache.initFenCache(fenCacheThreadInfo.getConfigFile())
    while not(fenCacheThreadInfo.isStopped()):
        fen=fenCacheThreadInfo.getNextFenFromQueue()
        if fen != None :
            window=fenCacheThreadInfo.getWindow()
 
            # Run from context of main thread
            #runInMainThread(lambda : fenCache.fillFenCache(fen))
            fenCache.fillFenCache(fen)
 
            # react on current position
            currentPositionLambda= lambda : currentPositionCacheReady(window)
            fenCacheThreadInfo.checkCurrentPositionFen(fen,currentPositionLambda)

 
            # react on previous posution
            lastMoveLambda=lambda move,fen: lastMoveCacheReady(window,move,fen)
            fenCacheThreadInfo.checkPreviousMoveFen(fen,lastMoveLambda)

    print('fenCacheThread: EXIT\n')        
 
    
## Class provide popularity UI   
class PopularityTab :
    def __init__(self,chessBoard,configFile) :
        self.popularityTab = sg.TabGroup([[sg.Tab('Popularity',[[sg.Text('Last move popularity: '),sg.Text('           ',key='_current_popularity_',justification='left')],
                                          [sg.RButton('Show Popular moves', disabled=True, key='_popularity_', size=[20,None]), sg.RButton('Make Move', key='_make_popularity_move_',disabled=True)],
                                          [sg.Table([['','','','','']],headings=['#','Move','#Games','Depth', 'Eval'], key='_popularity_table_', justification='center',auto_size_columns=False,col_widths=[3,8,9,5,4],num_rows=10)]])]])

        self.gamesTab = sg.TabGroup([[sg.Tab('Games',[[sg.Text('')],
                                     [sg.RButton('Show Games', key= '_show_games_',disabled=True),sg.RButton('Go to Game',disabled=True,key="_goto_game_")],
                                     [sg.Table([['','','','','','']],
                                               headings=['Year','White Name','ELO\nWhite','Black Name','ELO\nBlack','Result'],
                                               key='_games_table_',
                                               justification='center',
                                               auto_size_columns=False,
                                               col_widths=[4,10,4,10,4,5],num_rows=5)]])]])
        self.threadInfo = FenCacheThreadInfo(chessBoard,configFile)
        self.threadObject = threading.Thread(target=fenCacheThread, args=[self.threadInfo])
        self.threadObject.start()
       
    def getPopularityTab(self) :
        return self.popularityTab

    
    def getGamesTab(self) :
        return self.gamesTab

    def disableButtons(self,window) :
        try:
            window.FindElement('_popularity_').Update(disabled=True)
            window.FindElement('_make_popularity_move_').Update(disabled=True)
            window.FindElement('_popularity_table_').Update(values=[[]])
            window.FindElement('_show_games_').Update(disabled=True)
            window.FindElement('_games_table_').Update(values=[[]])
            window.FindElement('_goto_game_').Update(disabled=True)
            window.FindElement('_current_popularity_').Update(value='')
        except:
            print('Unable to update buttons!!!')
 
    # On new board disable buttons.
    def setBoard(self,chessBoard,window) :
        disableButtonsLambda = lambda : self.disableButtons(window)
        self.threadInfo.setBoard(chessBoard,disableButtonsLambda)

    # On show games button
    def onShowGames(self,window,chessBoard) :
        cacheElement=fenCache.getCache(chessBoard.fen())
        if cacheElement != None:
            window.FindElement('_games_table_').Update(cacheElement['games'][0])
            if len(cacheElement['games'][0]) > 0 :
                window.FindElement('_goto_game_').Update(disabled=False)
            else :
                window.FindElement('_goto_game_').Update(disabled=True)
        else :
            print('onShowGames: Cache for fen=', chessBoard.fen(), ' is not present')

    # On goto game button
    def onGotoGame(self,window, window_values,chessBoard) :
        cacheElement=fenCache.getCache(chessBoard.fen())
        if cacheElement != None:
            if len(window_values['_games_table_']) > 0:
                index = window_values['_games_table_'][0]
                href=cacheElement['games'][1][index]
                webbrowser.open(href)
            #else : 
            #    window.FindElement('_error_message_').Update(value='Choose game')
        else :
            print('onGotoGame: Cache for fen=', chessBoard.fen(), ' is not present')

    # on show popularity button
    def onPopularity(self,window,chessBoard) :
        cacheElement=fenCache.getCache(chessBoard.fen())
        if cacheElement != None:
            popularityTable=sortedPopularityTable(cacheElement['popularity'])
            window.FindElement('_popularity_table_').Update(popularityTable)
            if len(popularityTable) > 0:
                window.FindElement('_make_popularity_move_').Update(disabled=False)
            else :
                window.FindElement('_make_popularity_move_').Update(disabled=True)
        else :
            print('onPopularity: Cache for fen=', chessBoard.fen(), ' is not present')

    # make move from popularity table
    def makePopularMove(self,window, window_values,chessBoard) :
        if len(window_values['_popularity_table_']) > 0:
            index = window_values['_popularity_table_'][0]
            return chessBoard.parse_san(window.FindElement('_popularity_table_').Get()[index][1])
        #else : 
        #    window.FindElement('_error_message_').Update(value='Choose Move')
        return None

    # updates window after finalize
    def onWindowFinalize(self,window,chessBoard):
       window.FindElement('_games_table_').bind('<Double-Button-1>','double_click_')
       window.FindElement('_popularity_table_').bind('<Double-Button-1>','double_click_')
       
       self.threadInfo.setWindow(window,chessBoard,lambda : self.disableButtons(window))
        
    # on window event
    def onEvent(self,window, button, value, chessBoard) :
        move=None

        if button == '_show_games_' :
            self.onShowGames(window,chessBoard)
            
        if (button == '_goto_game_') or (button == '_games_table_double_click_') :
            self.onGotoGame(window, value,chessBoard)

        if button == '_popularity_':
            self.onPopularity(window,chessBoard)
            
        if (button == '_make_popularity_move_') or (button == '_popularity_table_double_click_'):
            move=self.makePopularMove(window, value,chessBoard)
        return move

    # on close window exit thread
    def close(self) :
        self.threadInfo.stop()


    
