import PySimpleGUI as sg
import chess
import chess.pgn
import os
import keyboardKeys
import configparser
import threading
import io
#import cProfile

SHOW_MOVES_FROM_CURRENT=8
class NotationChangedException(Exception) :
    def __init(self) :
        Exception.__init__(self)

class NotationTab :
    def __init__(self,configFile) :
        config = configparser.RawConfigParser()
        config.read(configFile)
        iconsPath=config.get('notation','iconsPath')
        forward = os.path.join(iconsPath, config.get('notation','forward_icon'))
        backward = os.path.join(iconsPath, config.get('notation','backward_icon'))
        remove_variation = os.path.join(iconsPath, config.get('notation','delete_icon'))
        undo = os.path.join(iconsPath, config.get('notation','undo_icon'))
        redo = os.path.join(iconsPath, config.get('notation','redo_icon'))
        

        self.notationTab = sg.TabGroup(
            [[sg.Tab('Notation',
                     [[sg.Multiline([],
                                    do_not_clear=True,
                                    autoscroll=True,
                                    size=(93,16),
                                    background_color='white',
                                    key='_notation_',
                                    disabled=True)],
                      [sg.Button(image_filename=backward,
                                 key='_notation_backward_',
                                 image_subsample=3,
                                 tooltip='Backward'),
                       sg.Button(image_filename=forward,
                                 key ='_notation_forward_',
                                 image_subsample=3,
                                 tooltip='Forward'),
                       sg.Button(image_filename=remove_variation ,
                                 key='_remove_variation_',
                                 image_subsample=3,
                                 tooltip='Remove variation'),
                       sg.Button(image_filename=undo ,
                                 key='_undo_',
                                 image_subsample=3,
                                 tooltip='Undo'),
                       sg.Button(image_filename=redo ,
                                 key='_redo_',
                                 image_subsample=3,
                                 tooltip='Redo')]]
                     )]])

        # Every time we change game or current node timestamp increases
        # in addition all the accesses to below members must be under lock
        self.lock = threading.Lock()
        self.showNotationSemaphore=threading.Semaphore(value=0)
        self.timeStamp=0
        self.game=chess.pgn.Game()
        self.current_node=self.game
        self.undoList=[]
        self.redoList=[]
        self.textIndeciesToVariation={}
        self.filename=None
        self.otherGamesInPgn = []
        # .san call is very expensive for chess library, so caching "san" values
        self.nodeToSanCache = {}
        self.threadObject = None
        self.stopThread=False



    ########################################### node to San cache operations ###########################################
    def getSan(self,node,board):
        if node in self.nodeToSanCache:
            return self.nodeToSanCache[node]
        san=board.san(node.move)
        with self.lock:
            self.nodeToSanCache[node]=san
        return san

    def removeVariationFromSanCache(self,node):
        with self.lock:
            if node in self.nodeToSanCache:
                del self.nodeToSanCache[node]
        for variation in node.variations :
            self.removeVariationFromSanCache(variation)


    ########################################### yndo/redo  operations ##################################################
    ## copies game from copyNode to node
    def copyGame(self,node,current_node,timestamp,copyNode,sanCache) :
        with self.lock:
            # Check timestamp and throw exception if it changes
            if timestamp != self.timeStamp:
                raise NotationChangedException

        returnValue=None
        # mark current move
        if node==current_node:
            returnValue = copyNode
        # copy san cache
        with self.lock:
            if node in self.nodeToSanCache :
                sanCache[node]=self.nodeToSanCache[node]

        # recursion
        for variation in node.variations :
            copy_variation=copyNode.add_variation(variation.move)
            r=self.copyGame(variation,current_node,timestamp,copy_variation,sanCache)
            if r != None :
                returnValue=r
        return returnValue

    ## inserts current state to undo
    def insertCurrentToUndo(self) :
        copyGame=chess.pgn.Game()
        sanCache={}
        try:
            with self.lock:
                game=self.game
                current_node=self.current_node
                timestamp=self.timeStamp
            copyNode=self.copyGame(game,current_node,timestamp,copyGame,sanCache)
            with self.lock:
                self.undoList.append([copyGame,copyNode,sanCache])
                self.redoList=[]
        except NotationChangedException:
            print('Timestamp changed during copyGame')
            pass

    ## performs undo operation
    def performUndo(self):
        with self.lock:
            if len(self.undoList) > 0:
                self.timeStamp=self.timeStamp+1
                undoData = self.undoList.pop(-1)
                self.redoList.append([self.game, self.current_node,self.nodeToSanCache])
                self.game = undoData[0]
                self.current_node = undoData[1]
                self.nodeToSanCache=undoData[2]
                return True
            else :
                return False

    ## performs redo operation
    def performRedo(self):
        with self.lock:
            if len(self.redoList) > 0:
                self.timeStamp=self.timeStamp+1
                redoData = self.redoList.pop(-1)
                self.undoList.append([self.game, self.current_node,self.nodeToSanCache])
                self.game = redoData[0]
                self.current_node = redoData[1]
                self.nodeToSanCache=redoData[2]
                return True
            else :
                return False


    ######################################### notation multiline operations ############################################
    ## shows output previously gathered by addMovesToOutput
    def showOutput(self,output,txt):
        # clear content
        txt.delete('1.0', 'end')
        index=[1,1]
        prevmark=''
        out_sting=''
        for a in output:
            # set mark for current
            if a == 'current_node':
                txt.mark_set('Current move','insert')
                txt.mark_gravity('Current move','left')
                continue

            # Show text
            if prevmark == a[1] :
                out_sting+=a[0]
                prevmark=a[1]
            else:
                if out_sting !='' :
                    txt.insert('end',out_sting,prevmark)
                out_sting=a[0]
                prevmark=a[1]

            # update indexes table
            if a[2] != None and not('\n' in a[0]) :
                for i in range(len(a[0])) :
                     with self.lock:
                        self.textIndeciesToVariation[str(index[0]) + '.' + str(index[1])] = a[2]
                     index[1]+=1
            else :
                for c in a[0] :
                    if c=='\n':
                        index[0]+=1
                        index[1]=1
                    else:
                        index[1]+=1

        if out_sting !='' :
            txt.insert('end',out_sting,prevmark)



    ## adds comment to output
    def addCommentToOutput(self,output,node):
        if node.comment != '' :
            output.append(['('+node.comment.replace('\n',' ')+')','comment',None])

    ## shows one move in multiline element
    def addOneMoveToOutput(self, output, node, move_text, config):
        output.append([move_text, config, node])

    ## finishes variation if needed (adds [...] in the end of variation)
    def finishVariationIfNeeded(self,output, node,current_node):
        # in case it is last move in variation - it is not needed
        if len(node.variations) == 0 :
            return False

        #Try to find current.node in previous moves of node
        tmpNode = node
        distance= 0

        while tmpNode != None and tmpNode != current_node:
            tmpNode = tmpNode.parent
            distance += 1

        # If found  - finish or not according to distance
        finish_variation = (tmpNode != None) and (distance > SHOW_MOVES_FROM_CURRENT)

        # Try to find node in previous moves of current_node if we did not find in opposite direction
        if tmpNode == None :
            tmpNode = current_node
            while tmpNode != None and tmpNode != node:
                tmpNode = tmpNode.parent
            # not found it is side variation - finish it
            finish_variation = (tmpNode == None)

        # Finally finish if needed
        if finish_variation :
            self.addOneMoveToOutput(output,
                             node,
                             '[...]',
                             'following_moves_mainline' if node.is_mainline() else 'following_moves_variation')

            # here if it is single variation go to the end and find last comment
            tmpNode = node
            while len(tmpNode.variations) != 0:
                if len(tmpNode.variations) > 1:
                    return True
                tmpNode = tmpNode.variations[0]
            self.addCommentToOutput(output, tmpNode)
            return True

        return False

    ## adds moves started from current node in multiline elemenet
    def addMovesToOutput(self,timestamp,node,current_node,output,half_move,tabs_space,board) :
        config_dict = {0 : 'variation', 1 : 'mainline', 2 : 'current_move_variation', 3 : 'current_move_mainline'}

        with self.lock:
            if self.timeStamp !=timestamp:
                raise NotationChangedException

        # Mark place of current node
        if node != current_node:
            if self.finishVariationIfNeeded(output,node,current_node) :
                return
        else:
            output.append('current_node')


        self.addCommentToOutput(output,node)

        if node.move != None :
            board.push(node.move)

        # First
        for variation in node.variations :
            # check what config we should use 
            config_id=0
            if variation.is_mainline() :
                config_id+=1
            if variation == current_node:
                config_id+=2
            
            # in case where are more than one variation new line and move tab space
            new_tabs_space=tabs_space
            if not variation.is_main_variation() :
                new_tabs_space+=1
                string='\n'
                for i in range(0,new_tabs_space) :
                    string=string+'   '
                output.append([string,'variation',None])
                if half_move%2 == 1:
                    output.append([str(int(half_move/2)+1)+'...',config_dict[config_id],variation])

            self.addOneMoveToOutput(output,
                             variation,
                             (str(int(half_move/2)+1)+'. ' if half_move%2 == 0 else '')+self.getSan(variation,board) + ' ',
                             config_dict[config_id])
            self.addMovesToOutput(timestamp,variation,current_node,output,half_move+1,new_tabs_space,board)

        if node.move != None :
            board.pop()

    ## updates multiline notation with current state
    def updateNotation(self, window):
        self.showNotationSemaphore.release()

    def updateNotationInternal(self,window) :
        with self.lock:
            self.textIndeciesToVariation.clear()
            game=self.game
            current_node=self.current_node
            timeStamp=self.timeStamp
        try:
            element = window.FindElement('_notation_')
            output=[]
            self.addMovesToOutput(timeStamp, game, current_node, output, 0, 0, game.board())

            element.Update(disabled=False)
            self.showOutput(output, element.Widget)
            element.Update(disabled=True)
            element.Widget.see(element.Widget.index('Current move'))

        except NotationChangedException:
            pass

    ## thread updates notation
    def notationThread(self,window) :
        while True:
            self.showNotationSemaphore.acquire()
            with self.lock:
                if self.stopThread:
                    print('Notation thread exit\n')
                    return
            while True :
                try:
                    self.updateNotationInternal(window)
                    #cProfile.runctx('self.updateNotationInternal(window)',{},{'self':self,'window':window},'updataNotation_profile')
                    break
                except:
                    pass

    ############################################ Game operations #######################################################
    ## Clears game
    def newGame(self,window) :
        self.insertCurrentToUndo()
        with self.lock:
            self.timeStamp=self.timeStamp+1
            self.game=chess.pgn.Game()
            self.current_node=self.game
            self.nodeToSanCache.clear()
            self.filename=None

        self.updateNotation(window)

    ## saves game to filenames save in class
    def saveGameInternal(self,filename) :
        try :
            with self.lock:
                game=self.game
                otherGames=self.otherGamesInPgn

            with open(filename, 'w') as f:
                print(game, file=f, end='\n\n')
                # Save others
                for othergame in otherGames:
                    print(othergame, file=f, end='\n\n')
        except :
            print('Unable to save file')
            sg.PopupError('Unable to save file')

    ## save
    def saveGame(self) :
        with self.lock:
            filename=self.filename
        if filename == None :
            self.saveGameAs()
        else :
            self.saveGameInternal(filename)

    ## save as
    def saveGameAs(self) :
        filename=sg.PopupGetFile('Save Game', title='Save Game', no_window=True, default_extension="pgn", save_as=True,file_types=(('PGN Files', '*.pgn'),))
        if filename != '' :
            with self.lock:
                self.filename = filename
            self.saveGameInternal(filename)
        else :
            print('Save was cancelled')

    ## opens game
    def openGame(self,window) :
        self.insertCurrentToUndo()
        filename=sg.PopupGetFile('Open Game', title='Open Game', no_window=True, default_extension="pgn",file_types=(('PGN Files', '*.pgn'),))
        if filename != '' :
            try :
                pgn=open(filename)

                #sometimes it reads empty game and in this case we must continue to the next
                game=None
                while True:
                    tmp_game=chess.pgn.read_game(pgn)
                    if tmp_game != None :
                        game=tmp_game
                        if len(game.variations) > 0 :
                            break
                    else :
                        break

                if game== None:
                    print('Pgn file is empty')
                    sg.PopupError('Pgn file is empty')
                    return

                filename=filename
                otherGamesInPgn=[]
                while True:
                    next_game=chess.pgn.read_game(pgn)
                    if next_game == None :
                        break
                    else :
                        otherGamesInPgn.append(next_game)
                with self.lock:
                    self.timeStamp=self.timeStamp+1
                    self.filename=filename
                    self.game=game
                    self.otherGamesInPgn=otherGamesInPgn
                    self.current_node = self.game
                    self.nodeToSanCache.clear()
            except :
                print('Unable to open file')
                sg.PopupError('Unable to open file')
                return
            self.updateNotation(window)
            window.FindElement('_notation_').set_focus()
        else :
            print('Open was cancelled')
            

    ############################################## UI operations #######################################################
    def stop(self):
        with self.lock:
            self.stopThread=True
        self.showNotationSemaphore.release()

    ## returns current board for other UI components
    def getBoard(self) :
        with self.lock:
            return self.current_node.board()

    ## inserts new branch into current node of current game
    def insertBranch(self,node,new_node, comment):
        if len(new_node.variations) == 0 :
            node.comment=comment
        for variation in new_node.variations :
            if node.has_variation(variation.move) :
                self.insertBranch(node.variation(variation.move),variation,comment)
            else :
                self.insertBranch(node.add_variation(variation.move),variation,comment)

    ## copies given pgn to notation
    def copyToNotation(self,pgn_text,window):
        new_game=chess.pgn.read_game(io.StringIO(pgn_text))
        headers=new_game.headers
        print(headers)
        comment=headers['Date'] + ': '+\
                headers['White']+'('+headers['WhiteElo']+') - '+\
                headers['Black']+'('+headers['BlackElo']+')'+\
                ', ' + headers['Result']
        with self.lock:
            game=self.game
        self.insertBranch(game,new_game,comment)
        self.updateNotation(window)

    ## makes given move
    def makeMove(self, move, window):
        self.insertCurrentToUndo()
        with self.lock:
            self.timeStamp=self.timeStamp+1
            if self.current_node.has_variation(move):
                self.current_node = self.current_node.variation(move)
            else:
                self.current_node = self.current_node.add_variation(move)
        self.updateNotation(window)

    ## Returns notation tab for initial layout
    def getNotationTab(self) :
        return self.notationTab


    ## On finilize window (before something started)
    def onWindowFinalize(self,window) :
        element=window.FindElement('_notation_')
        element.bind('<Button-1>','click_')
        txt = element.Widget
        txt.tag_config('mainline', font='-weight bold -size 10')
        txt.tag_config('variation', font='-slant italic -size 10')
        txt.tag_config('current_move_mainline', font='-weight bold -size 10', background='gray')
        txt.tag_config('current_move_variation', font='-slant italic -size 10', background='gray')
        txt.tag_config('following_moves_mainline', font='-weight bold -size 10', foreground='green')
        txt.tag_config('following_moves_variation', font='-slant italic -size 10', foreground='green')
        txt.tag_config('comment', font='-slant italic -size 8', foreground='blue')
        txt.tag_config('sel', background = 'white', foreground='black')
        self.threadObject = threading.Thread(target=self.notationThread, args=[window])
        self.threadObject.start()



    ## On backward button
    def onBackward(self, window):
        with self.lock:
            if self.current_node.parent != None:
                self.timeStamp=self.timeStamp+1
                self.current_node = self.current_node.parent
                returnValue=True
            else:
                returnValue=False
        if returnValue:
            self.updateNotation(window)
        return returnValue

    ## On forward button
    def onForward(self,window):
        with self.lock:
            if len(self.current_node.variations) > 0:
                self.timeStamp=self.timeStamp+1
                self.current_node = self.current_node.variations[0]
                returnValue=True
            else:
                returnValue = False
        if returnValue:
            self.updateNotation(window)
        return returnValue

    ## On remove variation button
    def onRemoveVariation(self,window):
        with self.lock:
            current_node=self.current_node

        if current_node.parent != None:
            self.insertCurrentToUndo()

            with self.lock:
                if self.current_node == current_node:
                    self.timeStamp=self.timeStamp+1
                    variation_to_remove = self.current_node
                    self.current_node = self.current_node.parent
                    returnValue=True
                else:
                    returnValue=False
            # remove from cache
            if returnValue:
                self.current_node.remove_variation(variation_to_remove.move)
                self.updateNotation(window)
            return returnValue

        return False

    ## On notation click
    def onNotationClick(self,window):
        widget = window.FindElement('_notation_').Widget
        abs_postionX = widget.winfo_pointerx() - widget.winfo_rootx()
        abs_postionY = widget.winfo_pointery() - widget.winfo_rooty()
        index = widget.index('@%d,%d' % (abs_postionX, abs_postionY))
        with self.lock:
            if index in self.textIndeciesToVariation.keys():
                self.timeStamp=self.timeStamp+1
                self.current_node = self.textIndeciesToVariation[index]
                returnValue=True
            else:
                returnValue=False

        if returnValue:
            self.updateNotation(window)
        return returnValue

    ## Main event reaction function
    def onEvent(self,window, button, value) :
        if button == '_notation_backward_' or button == keyboardKeys.Left:
            return self.onBackward(window)

        if button == '_notation_forward_' or button == keyboardKeys.Right:
            return self.onForward(window)

        if button == '_remove_variation_':
            return self.onRemoveVariation(window)

        if button == '_undo_':
            if self.performUndo() :
                self.updateNotation(window)
                return True

        if button == '_redo_':
            if self.performRedo() :
                self.updateNotation(window)
                return True

        if button == '_notation_click_' :
            return self.onNotationClick(window)

        return False
            


