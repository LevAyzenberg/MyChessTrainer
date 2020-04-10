# MyChessTrainer
Small project to train chess variants.<br> 
Usually when you are preparing some chess variant for the game for example 
Sicilian dragon by black, you start from initial position 1.e4 c5 2.Nf3 d6 3. d4 cd 4. Nxd4 Nf6 5. Nc3 g6 ... and then
try to find best moves by black using engine and database for white's moves. So you don't want to see the whole 
computer engine's lines and popular games on every move (like for example chessbase provides you) but initiate these 
views only when it is needed. As well, you want to understand how computer score is changed as result of your 
last move as well as your last move popularity among games played by masters.
Games data (popular lines and top games) is retrieved from https://chess-db.com/. You must register where and update 
config.cfg with username and password. <br> 

<br>**Before running**:<br>
Update config.cfg with following parameters:<br> 
1. _chess-db.user, chess-db.password_ - chess-db username and password <br>
2. _engine.enginePath_ - path to engine <br>
3. _iconsPath.iconsPath, chessBoard.piecesPath_ - paths to icons and pieces folders <br>
  
<br>**Features**:<br>
1. File -> Open/Save/Save as. Reads and Writes pgn files. Only first game of pgn is showed, but open/save will preserve other games.<br>
2. Board -> Flip, flips board <br>
3. Notation - shows moves, current move is shown by gray background <br>
    &nbsp;&nbsp;&nbsp;&nbsp;a. Moves from variations which are not contain current move are hidden and you see\[...\] instead.<br> 
    &nbsp;&nbsp;&nbsp;&nbsp;b. Moves in current variation, but very far from current move are hidden and you see\[...\] instead. <br>
    &nbsp;&nbsp;&nbsp;&nbsp;c. Click on specific move goes to that move's position. <br>
    &nbsp;&nbsp;&nbsp;&nbsp;d. ">" button or keyboard right arrow goes to next move <br>
    &nbsp;&nbsp;&nbsp;&nbsp;e. "<" button or keyboard left arrow goes to previous move <br>
    &nbsp;&nbsp;&nbsp;&nbsp;f. "X" button removes current move and all the following moves <br>
    &nbsp;&nbsp;&nbsp;&nbsp;g. Undo and Redo are supported <br>
4. Popularity Tab. Last move popularity calculated according to chess-db master games table (https://chess-db.com/public/explorer.jsp?interactive=true&avelo=2700&etype=1&flipped=false)
Move with more games played is more popular. To show popular moves you must press "Show Popular Moves" button. Then you can pick the move and press "Make Mov". It takes around 5 seconds to retrieve popularity info from chess-db. 
If information is still not retrieved appropriate buttons are disabled.<br> 
5. Engine Tab, start/stop button starts or stops an engine. "Show Lines" shows first move of each lines. Double click or 
Move button make chosen move. <br>
6. Games Tab. "Show Games" - shows top games played in this position. Double click on game or  "Go to Game" button shows chosen game in the browser.<br>

<br>**Project files**<br>
_chessBordUI.py_ - responsible for chess board UI <br>
_engineTab.py_ - responsible for engine UI and communication<br>
_fenCache.py_ - responsible for retrieving data from chess-db and caching it <br>
_keyboardKeys.py_ - keyboard keys defines <br>
_listboxPopup.py_ - popup window with listbox to choose several options <br>
_mainGame.py_ - main module <br>
_notationTab.py_ - responsible for notation tab UI <br>
_popularityTab.py_ - responsible for games and popularity tabs <br>  

 

<br>**Packages used**<br> 
The following packages are used for development: <br/>
    1.PySimpleGUI (https://pysimplegui.readthedocs.io/en/latest/) package for UI development<br>
    2.Python-chess (https://python-chess.readthedocs.io/en/latest/index.html) package for chess manipulations<br>
    3.Used chess pieces and code from PySimpleGUI chess sample in https://github.com/PySimpleGUI/PySimpleGUI/tree/master/Chess

    
      
