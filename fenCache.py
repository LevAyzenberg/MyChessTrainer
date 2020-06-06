from html.parser import HTMLParser
import unicodedata
import re
from typing import List, Tuple, Dict, Union, Optional

import requests

import time
import lxml.html as lh
import threading
import configparser
import json
import berserk

# This file creates map from fen sting to various parameters: games, popularity,
# first lines of analisys, etc...

fenCacheLock = threading.Lock()
fenCache = {}


#################################################### Abstract class for info getters ###################################
class InfoGetter:
    def getCacheElement(self, fen: str) -> Dict[str, Union[Tuple[List[List[str]], List[str]],
                                                           Dict[str, Dict[str, str]]]]:
        return {}

    def getPgn(self, gameUrl: str) -> Optional[str]:
        return None


infoGetter = InfoGetter()


#################################################### Chess db implementation ###########################################

## Helper class to parse chess-db html
class MyChessDBGamesParser(HTMLParser):
    def __init__(self, baseURL, gamesString):
        HTMLParser.__init__(self)
        self.baseURL = baseURL
        self.gamesString = gamesString
        self.found_h2 = False
        self.found_games = False
        self.tr_started = False
        self.games_output = [[]]
        self.current_output = []
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == 'h2':
            self.found_h2 = True
        if self.found_games:
            if tag == 'tr':
                self.tr_started = True
        if self.tr_started:
            for attr in attrs:
                if attr[0] == 'href':
                    self.hrefs.append(self.baseURL + attr[1])

    def handle_endtag(self, tag):
        if tag == 'table':
            self.found_games = False
        if tag == 'tr':
            self.games_output.append(self.current_output)
            self.current_output = []
            self.tr_started = False

    def handle_data(self, data):
        if self.found_h2:
            if data == self.gamesString:
                self.found_games = True
        if self.tr_started:
            self.current_output.append(unicodedata.normalize("NFKD", data))


## class to work with chess-db
class ChessDBInfoGetter(InfoGetter):
    def initInternally(self):
        # login to html session
        self.htmlSession = requests.Session()
        user = self.config.get('chess-db', 'user')
        password = self.config.get('chess-db', 'password')
        loginUrl = self.config.get('chess-db', 'loginUrl') + '?username=' + user + '&password=' + password
        self.htmlSession.post(loginUrl)

    def __init__(self, configFile: str):
        self.htmlSession = None
        self.config = configparser.RawConfigParser()
        self.config.read(configFile)
        self.initInternally()

    ## parses output for games
    @staticmethod
    def parseGamesOutput(parserGamesOutput: List[List[str]]) -> List[List[str]]:
        table_lines = []
        for line in parserGamesOutput:
            if len(line) != 0:
                year = re.split(r'[:]', line[0].strip())[0]

                # get result
                splitted_line_space = re.split(r'\s', line[1].strip())
                result = splitted_line_space[len(splitted_line_space) - 1]

                # put it back
                restored_line = ''
                for i in range(0, len(splitted_line_space) - 1):
                    restored_line += splitted_line_space[i]
                splitted_line = re.split(r'[-]', restored_line.strip())
                splitted_part1 = re.split(r'[()]', splitted_line[0].strip())
                white_name = splitted_part1[0]
                white_rating = ''
                if len(splitted_part1) > 1:
                    white_rating = splitted_part1[1]
                if white_rating == '':
                    white_rating = '0'
                splitted_part2 = re.split(r'[()]', splitted_line[1].strip())
                black_name = splitted_part2[0]
                black_rating = ''
                if len(splitted_part2) > 1:
                    black_rating = splitted_part2[1]
                if black_rating == '':
                    black_rating = '0'
                table_line = [year, white_name, white_rating, black_name, black_rating, result]
                table_lines.append(table_line)
        return table_lines

    ## Internal function - returns games from given requestData
    def getGames(self, requestData: str) -> Tuple[List[List[str]], List[str]]:
        try:
            parser = MyChessDBGamesParser(self.config.get('chess-db', 'baseURL'),
                                          self.config.get('chess-db', 'gamesString'))
            parser.feed(requestData)
            return self.parseGamesOutput(parser.games_output), parser.hrefs

        except:
            print('Error!!! Something wrong happen in getGames, saving to request_error.html error file')
            f = open('request_error.html', 'w+')
            f.write(str(requestData.encode("utf-8")))
            f.close()
            return [], []

    ## Internal function returns popularity
    @staticmethod
    def getPopularity(requestData: str) -> Dict[str, Dict[str, str]]:
        popularityDict = {}

        try:
            # Store the contents of the website under doc
            doc = lh.fromstring(requestData)
            # Parse data that are stored between <th>..</th> of HTML
            th_elements = doc.xpath('//th')
            tr_elements = doc.xpath('//tr')

            for i in range(1, len(tr_elements)):
                if len(tr_elements[i]) > 0:
                    move_dict = {}
                    j = 0
                    for t in tr_elements[i].iterchildren():
                        key = unicodedata.normalize("NFKD", th_elements[j].text_content()).strip()
                        data = unicodedata.normalize("NFKD", t.text_content()).strip()
                        if key == data:
                            break
                        move_dict[key] = data
                        j = j + 1

                    if j == len(tr_elements[i]):
                        popularityDict[move_dict['Move']] = move_dict

            return popularityDict

        except:
            print('Error!!! Something wrong happen in getPopularity, saving to request_error.html error file')
            f = open('request_error.html', 'w+')
            f.write(str(requestData.encode("utf-8")))
            f.close()
            return popularityDict

    ## returns fen cache element, according to given fen
    def getCacheElement(self, fen: str) -> Dict[str, Union[Tuple[List[List[str]], List[str]],
                                                           Dict[str, Dict[str, str]]]]:
        print(fen)
        for retry in range(0, self.config.getint('chess-db', 'retriesNumber')):
            try:
                r_games = self.htmlSession.get(url=self.config.get('chess-db', 'dbURL'),
                                               params={'fen': fen, 'etype': 1, 'avelo': '-1', 'interactive': 'true'})
                r_popularity = self.htmlSession.get(url=self.config.get('chess-db', 'dbURL'),
                                                    params={'fen': fen, 'etype': 1, 'avelo': '-1',
                                                            'rows': self.config.get('chess-db', 'popularityRows')})
                return {'games': self.getGames(r_games.text), 'popularity': self.getPopularity(r_popularity.text)}
            except:
                print('Failed!, reconnect and retry,', retry)
                self.initInternally()
        return {}

    ## returns pgn for given games url
    def getPgn(self, gameUrl: str) -> Optional[str]:
        for retry in range(0, self.config.getint('chess-db', 'retriesNumber')):
            try:
                rgame = self.htmlSession.get(url=gameUrl)
                doc = lh.fromstring(rgame.text)
                input_elements = doc.xpath('//input[@name=\'pgn\']')
                if len(input_elements) == 0:
                    print('PGN not found!!!')
                    return None
                return input_elements[0].attrib['value']
            except:
                print('Failed!, reconnect and retry,', retry)
                self.initInternally()
        return None


#################################################### Lichess implementation ############################################

class LichessInfoGetter(InfoGetter):
    def __init__(self, configFile: str):
        self.htmlSession = None
        self.config = configparser.RawConfigParser()
        self.config.read(configFile)
        self.htmlSession = requests.Session()

    ## returns cache element according to fen
    def getCacheElement(self, fen: str) -> Dict[str, Union[Tuple[List[List[str]], List[str]], Dict[str, Dict[str, str]]]]:
        try:
            fenUrl = self.config.get('lichess', 'fenUrl') + fen
            response = self.htmlSession.get(url=fenUrl)
            response_dict = json.loads(response.text)

            # build games element
            games = response_dict['topGames']
            games_table = []
            hrefs = []
            for game in games:
                hrefs.append(self.config.get('lichess', 'gameUrl') + game['id'])
                if game['winner'] == 'draw':
                    result = '1/2-1/2'
                else:
                    if game['winner'] == 'white':
                        result = '1-0'
                    else:
                        result = '0-1'

                table_line = [game['year'],
                              game['white']['name'],
                              game['white']['rating'],
                              game['black']['name'],
                              game['black']['rating'],
                              result]
                games_table.append(table_line)

            # build popularity element
            popularity_dict = {}
            for move in response_dict['moves']:
                move_dict = {'Move': move['san'], 'Eval': '', 'Games': move['white'] + move['draws'] + move['black']}
                popularity_dict[move_dict['Move']] = move_dict
            return {'games': (games_table, hrefs), 'popularity': popularity_dict}
        except:
            print('Failed to retrive data from lichess')
            return {}

    ## returns pgn of given game
    def getPgn(self, gameUrl: str) -> Optional[str]:
        try:
            with open(self.config.get('lichess', 'tokenFile')) as file:
                token = file.read()
            session = berserk.TokenSession(token)
            lichessClient = berserk.Client(session)
            gameId=gameUrl[len(self.config.get('lichess', 'gameUrl')):]
            return lichessClient.games.export(gameId, as_pgn=True)
        except  berserk.exceptions.BerserkError as error:
            print(error)
        except:
            print('Unable to load lichess pgn')
            return None

#################################################### Common implementation #############################################

def initFenCache(configFile):
    global infoGetter
    # infoGetter=ChessDBInfoGetter(configFile)
    infoGetter = LichessInfoGetter(configFile)


## builds cache element and saves it
def fillFenCache(fen):
    with fenCacheLock:
        if fen in fenCache.keys():
            return

    cacheElement = infoGetter.getCacheElement(fen)
    if len(cacheElement) == 0:
        return
    with fenCacheLock:
        fenCache[fen] = cacheElement
        return


## returns cache element
def getCache(fen):
    with fenCacheLock:
        if fen in fenCache.keys():
            return fenCache[fen]
        else:
            return None


def getPgn(gameUrl):
    return infoGetter.getPgn(gameUrl)

# initFenCache('config.cfg')
# fillFenCache('rnbqkbnr/pppppppp/8/8/8/P7/1PPPPPPP/RNBQKBNR b KQkq - 0 1')
