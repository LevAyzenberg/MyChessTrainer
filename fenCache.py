from html.parser import HTMLParser
import unicodedata
import re
import requests

import time
import lxml.html as lh
import threading
import configparser

htmlSession=requests.Session()
config = configparser.RawConfigParser()


#This file creates map from fen sting to various parameters: games, popularity,
#first lines of analisys, etc...

fenCacheLock=threading.Lock()
fenCache={}

class MyGamesParser(HTMLParser):
    def __init__(self, baseURL,gamesString) :
        HTMLParser.__init__(self)
        self.baseURL=baseURL
        self.gamesString=gamesString
        self.found_h2=False
        self.found_games = False
        self.tr_started =False
        self.games_output=[[]]
        self.current_output=[]
        self.hrefs=[]
        
    def handle_starttag(self, tag, attrs):
        if tag=='h2':
            self.found_h2=True
        if self.found_games:
            if tag == 'tr' :
                self.tr_started=True
        if self.tr_started :
            for attr in attrs:
                if attr[0]=='href':
                    self.hrefs.append(self.baseURL+attr[1])
        
    def handle_endtag(self, tag):
        if tag=='table' :
            self.found_games=False
        if tag == 'tr' :
            self.games_output.append(self.current_output)
            self.current_output=[]
            self.tr_started=False

    def handle_data(self, data):
        if self.found_h2:
            if data==self.gamesString:
               self.found_games=True
        if self.tr_started:
           self.current_output.append(unicodedata.normalize("NFKD", data))
           
def parseGamesOutput(parserGamesOutput) :
    table_lines=[]
    for line in parserGamesOutput :
        if len(line) != 0 :
            year=re.split(r'[:]',line[0].strip())[0]

            # get result
            splitted_line_space=re.split(r'\s',line[1].strip())
            result = splitted_line_space[len(splitted_line_space)-1]

            # put it back
            restored_line = ''
            for i in range(0,len(splitted_line_space)-1) :
                restored_line+= splitted_line_space[i]
            splitted_line=re.split(r'[-]',restored_line.strip())
            splitted_part1 = re.split(r'[\(\)]',splitted_line[0].strip())
            white_name = splitted_part1[0]
            white_rating = ''
            if len(splitted_part1) > 1 :
                white_rating = splitted_part1[1]
            if white_rating == '' :
                white_rating='0'
            splitted_part2 = re.split(r'[\(\)]',splitted_line[1].strip())
            black_name = splitted_part2[0]
            black_rating=''
            if len(splitted_part2) > 1 :
                black_rating = splitted_part2[1]
            if black_rating == '' :
                black_rating='0'
            table_line=[year,white_name,white_rating, black_name, black_rating,result]
            table_lines.append(table_line)
    return table_lines

def getGames(requestData) :
    try:
        parser = MyGamesParser(config.get('chess-db','baseURL'),config.get('chess-db','gamesString'))
        parser.feed(requestData)
        return (parseGamesOutput(parser.games_output),parser.hrefs)

    except:
        print('Error!!! Something wrong happen in getGames, saving to request_error.html error file')
        f=open('request_error.html','w+')
        f.write(str(requestData.encode("utf-8")))
        f.close()
        return popularityDict


def getPopularity(requestData) : 
    popularityDict={}

    try :
        #Store the contents of the website under doc
        doc = lh.fromstring(requestData)
        #Parse data that are stored between <th>..</th> of HTML
        th_elements = doc.xpath('//th')
        tr_elements = doc.xpath('//tr')
    
        for i in range(1,len(tr_elements)) :
            if len(tr_elements[i]) > 0 :
                move_dict={}
                j=0
                for t in tr_elements[i].iterchildren():
                    key=unicodedata.normalize("NFKD", th_elements[j].text_content()).strip()
                    data=unicodedata.normalize("NFKD", t.text_content()).strip()
                    if key == data :
                        break
                    move_dict[key]=data
                    j=j+1
                
                if j== len(tr_elements[i]) :
                     popularityDict[move_dict['Move']]=move_dict

        return popularityDict                

    except:
        print('Error!!! Something wrong happen in getPopularity, saving to request_error.html error file')
        f=open('request_error.html','w+')
        f.write(str(requestData.encode("utf-8")))
        f.close()
        return popularityDict


def initFenCacheInternally() :
    user=config.get('chess-db','user')
    password=config.get('chess-db','password')
    loginUrl=config.get('chess-db','loginUrl')+'?username='+user+'&password='+password
    login_response=htmlSession.post(loginUrl)
    
def initFenCache(configFile) :
    config.read(configFile)
    initFenCacheInternally()

def fillFenCache(fen) :
    with fenCacheLock :
        if fen in fenCache.keys() :
#            print('fen=',fen, ' already in cache')
            return
        
    for retry in range(0,config.getint('chess-db','retriesNumber')) : 
        try:
            a1=time.time()
            r_games=htmlSession.get(url=config.get('chess-db','dbURL'),params={'fen':fen,'etype':1, 'avelo':'-1', 'interactive' : 'true'})
            a2=time.time()
            r_popularity=htmlSession.get(url=config.get('chess-db','dbURL'),params={'fen':fen,'etype':1, 'avelo':'-1', 'rows' : config.get('chess-db','popularityRows')})
#            print('Get popularity time: ', time.time()-a2, ', Get games time: ', a2-a1, 'fen=',fen)
            cacheElement={'games' : getGames(r_games.text), 'popularity' : getPopularity(r_popularity.text)}
            with fenCacheLock:
                fenCache[fen]=cacheElement
            return
        except:
            print('Failed!, reconnect and retry,',retry)
            initFenCacheInternally()

def getCache(fen) :
    with fenCacheLock :
        if fen in fenCache.keys() :
            return fenCache[fen]
        else :
            return None

def getPgn(gameUrl) :
    for retry in range(0, config.getint('chess-db', 'retriesNumber')):
        try:
            a1 = time.time()
            rgame = htmlSession.get(url=gameUrl)
            a2 = time.time()
            doc = lh.fromstring(rgame.text)
            input_elements = doc.xpath('//input[@name=\'pgn\']')
            if len(input_elements) == 0 :
                print('PGN not found!!!')
                return None
            return input_elements[0].attrib['value']
        except:
            print('Failed!, reconnect and retry,', retry)
            initFenCacheInternally()
    return None

#initFenCache('config.cfg')
#fillFenCache('rnbqkbnr/pppppppp/8/8/8/P7/1PPPPPPP/RNBQKBNR b KQkq - 0 1')


