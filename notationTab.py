import PySimpleGUI as sg
import chess
import chess.pgn
import os
import listboxPopup
import keyboardKeys
import configparser

SHOW_MOVES_FROM_CURRENT=8

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
        self.game=chess.pgn.Game()
        self.current_node=self.game
        self.undoList=[]
        self.redoList=[]
        self.textIndeciesToVariation={}
        self.filename=None
        self.otherGamesInPgn = []
        # .san call is very expensive for chess library, so caching "san" values
        self.nodeToSanCache = {}


    ########################################### node to San cache operations ###########################################
    def getSan(self,node):
        if node in self.nodeToSanCache:
            return self.nodeToSanCache[node]
        san=node.san()
        self.nodeToSanCache[node]=san
        return san

    def removeVariationFromSanCache(self,node):
        if node in self.nodeToSanCache:
            del self.nodeToSanCache[node]
        for variation in node.variations :
            self.removeVariationFromSanCache(variation)


    ########################################### yndo/redo  operations ##################################################
    ## copies game from copyNode to node
    def copyGame(self,node,copyNode,sanCache) :
        returnValue=None
        # mark current move
        if node==self.current_node:
            returnValue = copyNode
        # copy san cache
        if node in self.nodeToSanCache :
            sanCache[node]=self.nodeToSanCache[node]

        # recursion
        for variation in node.variations :
            copy_variation=copyNode.add_variation(variation.move)
            r=self.copyGame(variation,copy_variation,sanCache)
            if r != None :
                returnValue=r
        return returnValue

    ## inserts current state to undo
    def insertCurrentToUndo(self) :
        copyGame=chess.pgn.Game()
        sanCache={}
        copyNode=self.copyGame(self.game,copyGame,sanCache)
        self.undoList.append([copyGame,copyNode,sanCache])
        self.redoList=[]

    ## performs undo operation
    def performUndo(self):
        if len(self.undoList) > 0:
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
        if len(self.redoList) > 0:
            redoData = self.redoList.pop(-1)
            self.undoList.append([self.game, self.current_node,self.nodeToSanCache])
            self.game = redoData[0]
            self.current_node = redoData[1]
            self.nodeToSanCache=redoData[2]
            return True
        else :
            return False


    ######################################### notation multiline operations ############################################
    ## shows comment in multiline element
    def showComment(self,txt,node):
        if node.comment != '' :
            txt.insert('end','('+node.comment.replace('\n',' ')+')','comment')

    ## shows one move in multiline element
    def showOneMove(self, txt, node, move_text, config):
        start_index = txt.index('insert').split('.')
        txt.insert('end', move_text, config)
        end_index = txt.index('insert').split('.')
        if start_index[0] == end_index[0]:
            for i in range(int(start_index[1]), int(end_index[1])):
                self.textIndeciesToVariation[start_index[0] + '.' + str(i)] = node
        else:
            print('indexes are not on same line!!!', start_index, ',', end_index)

    ## finishes variation if needed (shows [...] in the end of variation)
    def finishVariationIfNeeded(self,txt, node):
        # in case it is last move in variation - it is not needed
        if len(node.variations) == 0 :
            return False

        #Try to find current.node in previous moves of node
        tmpNode = node
        distance= 0
        while tmpNode != None and tmpNode != self.current_node:
            tmpNode = tmpNode.parent
            distance += 1

        # If found  - finish or not according to distance
        finish_variation = (tmpNode != None) and (distance > SHOW_MOVES_FROM_CURRENT)

        # Try to find node in previous moves of current_node if we did not find in opposite direction
        if tmpNode == None :
            tmpNode = self.current_node
            while tmpNode != None and tmpNode != node:
                tmpNode = tmpNode.parent
            # not found it is side variation - finish it
            finish_variation = (tmpNode == None)

        # Finally finish if needed
        if finish_variation :
            self.showOneMove(txt,
                             node,
                             '[...]',
                             'following_moves_mainline' if node.is_mainline() else 'following_moves_variation')

            # here if it is single variation go to the end and find last comment
            tmpNode = node
            while len(tmpNode.variations) != 0:
                if len(tmpNode.variations) > 1:
                    return True
                tmpNode = tmpNode.variations[0]
            self.showComment(txt, tmpNode)
            return True

        return False

    ## shows moves started from current node in multiline elemenet
    def showMoves(self,element,node,half_move,tabs_space) :
        txt = element.Widget
        config_dict = {0 : 'variation', 1 : 'mainline', 2 : 'current_move_variation', 3 : 'current_move_mainline'}

        # Mark place of current node
        if node == self.current_node:
            txt.mark_set('Current move','insert')
            txt.mark_gravity('Current move','left')
        else :
            if self.finishVariationIfNeeded(txt,node) :
                return
        self.showComment(txt,node)

        # First
        for variation in node.variations :
            # check what config we should use 
            config_id=0
            if variation.is_mainline() :
                config_id+=1
            if variation == self.current_node:
                config_id+=2
            
            # in case where are more than one variation new line and move tab space
            new_tabs_space=tabs_space
            if not variation.is_main_variation() :
                new_tabs_space+=1
                txt.insert('end','\n')
                for i in range(0,new_tabs_space) :
                    txt.insert('end','   ')
                if half_move%2 == 1:
                    txt.insert('end',str(int(half_move/2)+1)+'...',config_dict[config_id])

            self.showOneMove(txt,
                             variation,
                             (str(int(half_move/2)+1)+'. ' if half_move%2 == 0 else '')+self.getSan(variation) + ' ',
                             config_dict[config_id])

            self.showMoves(element,variation,half_move+1,new_tabs_space)

    ## updates multiline notation with current state
    def updateNotation(self,window) :
        element=window.FindElement('_notation_')
        self.textIndeciesToVariation.clear()
        element.Update(value='',disabled=False)
        self.showMoves(element,self.game,0,0)
        element.Update(disabled=True)
        element.Widget.mark_set('sel.first', 1.0)
        element.Widget.mark_set('sel.last', 1.0)
        element.Widget.see(element.Widget.index('Current move'))



    ############################################ Game operations #######################################################
    ## Clears game
    def newGame(self,window) :
        self.insertCurrentToUndo()
        self.game=chess.pgn.Game()
        self.current_node=self.game
        self.nodeToSanCache.clear()
        self.filename=None
        self.updateNotation(window)

    ## saves game to filenames save in class
    def saveGameInternal(self) :
        try :
            with open(self.filename, 'w') as f:
                print(self.game, file=f, end='\n\n')
                # Save others
                for game in self.otherGamesInPgn:
                    print(game, file=f, end='\n\n')
        except :
            print('Unable to save file')
            sg.PopupError('Unable to save file')

    ## save
    def saveGame(self) :
        if self.filename == None :
            self.saveGameAs()
        else :
            self.saveGameInternal()

    ## save as
    def saveGameAs(self) :
        filename=sg.PopupGetFile('Save Game', title='Save Game', no_window=True, default_extension="pgn", save_as=True,file_types=(('PGN Files', '*.pgn'),))
        if filename != '' :
            self.filename = filename
            self.saveGameInternal()
        else :
            print('Save was cancelled')

    ## opens game
    def openGame(self,window) :
        self.insertCurrentToUndo()
        filename=sg.PopupGetFile('Open Game', title='Open Game', no_window=True, default_extension="pgn",file_types=(('PGN Files', '*.pgn'),))
        if filename != '' :
            try :
                pgn=open(filename)
                self.game=chess.pgn.read_game(pgn)
                self.filename=filename
                while True:
                    next_game=chess.pgn.read_game(pgn)
                    if next_game == None :
                        break
                    else :
                        self.otherGamesInPgn.append(next_game)
            except :
                print('Unable to open file')
                sg.PopupError('Unable to open file')
                return
            self.current_node=self.game
            self.nodeToSanCache.clear()
            self.updateNotation(window)
            window.FindElement('_notation_').set_focus()
        else :
            print('Open was cancelled')
            

    ############################################## UI operations #######################################################
    ## returns current board for other UI components
    def getBoard(self) :
        return self.current_node.board()

    ## makes given move
    def makeMove(self, move, window):
        self.insertCurrentToUndo()
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
        txt.tag_config('mainline', font='-weight bold -size 10')
        txt.tag_config('current_move_mainline', font='-weight bold -size 10', background='gray')
        txt.tag_config('current_move_variation', font='-slant italic -size 10', background='gray')
        txt.tag_config('following_moves_mainline', font='-weight bold -size 10', foreground='green')
        txt.tag_config('following_moves_variation', font='-slant italic -size 10', foreground='green')
        txt.tag_config('comment', font='-slant italic -size 8', foreground='blue')
        txt.tag_config('sel', background = 'white', foreground='black')

    ## On backward button
    def onBackward(self, window):
        if self.current_node.parent != None:
            self.current_node = self.current_node.parent
            self.updateNotation(window)
            return True
        return False

    ## On forward button
    def onForward(self,window):
        if len(self.current_node.variations) > 0:
            if len(self.current_node.variations) == 1:
                self.current_node = self.current_node.variations[0]
            else:
                variation_choices = {}
                for variation in self.current_node.variations:
                    variation_choices[variation.san()] = variation
                variation_list = list(variation_choices.keys())
                move = listboxPopup.showListBoxPopup(variation_list, 'Choose Variation')
                self.current_node = variation_choices[move]
            self.updateNotation(window)
            return True
        return False

    ## On remove variation button
    def onRemoveVariation(self,window):
        if self.current_node.parent != None:
            self.insertCurrentToUndo()
            variation_to_remove = self.current_node
            self.current_node = self.current_node.parent
            # remove from cache
            self.current_node.remove_variation(variation_to_remove.move)
            self.updateNotation(window)
            return True
        return False

    ## On notation click
    def onNotationClick(self,window):
        widget = window.FindElement('_notation_').Widget
        abs_postionX = widget.winfo_pointerx() - widget.winfo_rootx()
        abs_postionY = widget.winfo_pointery() - widget.winfo_rooty()
        index = widget.index('@%d,%d' % (abs_postionX, abs_postionY))
        if index in self.textIndeciesToVariation.keys():
            self.current_node = self.textIndeciesToVariation[index]
            self.updateNotation(window)
            return True
        return False

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
            
