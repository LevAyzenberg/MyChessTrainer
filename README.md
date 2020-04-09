# MyChessTrainer
Small project to train chess variants. Usually when you are preparing some chess variant for the game for example 
Sicilian dragon by black, you start from initial position 1.e4 c5 2.Nf3 d6 3. d4 cd 4. Nxd4 Nf6 5. Nc3 g6 ... and then
try to find best moves by black, and use engine and database for white's moves. So you don't want to see the whole 
computer engine's lines and popular games on every move (like for example chessbase provides you) but initiate these 
views only when it is needed, also you want to understand how computer score is changed as result of your 
last move as well as your last move popularity among games played by masters.

Games data (popular lines and top games) is retrieved from https://chess-db.com/. You must register where and update 
config.cfg with username and password. 
The following packages are used: <br/>
    1.PySimpleGUI (https://pysimplegui.readthedocs.io/en/latest/) package for UI development<br>
    2.Python-chess (https://python-chess.readthedocs.io/en/latest/index.html) package for chess manipulations<br>
    3.Used chess pieces and code from PySimpleGUI chess sample in https://github.com/PySimpleGUI/PySimpleGUI/tree/master/Chess

    
      