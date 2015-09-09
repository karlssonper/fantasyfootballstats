from bs4 import BeautifulSoup
from urllib2 import urlopen
import pandas as pd
import math, csv

urlPoints = "http://www.fantasypros.com/nfl/reports/leaders/$POS.php?year=2014&week={0}"
urlTargets = "http://www.fantasypros.com/nfl/reports/targets/{0}.php"
urlRank = "http://www.fantasypros.com/nfl/rankings/ppr-cheatsheets.php"

def computeStats(x):
    x.sort()
    N = sum([1 for xx in x if xx]) # :/
    tot = sum(x)
    avg = tot / N if N > 0 else 0
    med = x[N/2] if N > 0 else 0
    stddev = math.sqrt(sum([(p-avg)*(p-avg) for p in x])/(N-1 if N > 1 else 1))
    return tot, avg, med, stddev

class Player(object):
    def __init__(self, name):
        self.name = name
        self.p = [0.0] * 17
        self.totalP = self.avgP = self.medianP = self.stddevP = 0.0
        self.t = [0.0] * 17
        self.totalT = self.avgT = self.medianT = self.stddevT = 0.0
        self.rank = self.avgPRank = self.avgTRank = -1
 
    def compute(self):
        self.totalP,self.avgP,self.medianP,self.stddevP = computeStats(self.p)
        self.totalT,self.avgT,self.medianT,self.stddevT = computeStats(self.t)

def createPlayers(url):
    players = {}
    for i in xrange(1,18):
        soup = BeautifulSoup(urlopen(url.format(str(i))).read(), "lxml")
        for x in soup.find(class_='mobile-table').find_all("tr"):
            td = x.find_all("td")
            if td and len(td) == 6:
                name = td[1].string
                pts = eval(td[3].string)
                if name not in players:
                    players[name] = Player(name)
                players[name].p[i-1] = pts
    return players

def readTargets(url, players):
    soup = BeautifulSoup(urlopen(url).read(), "lxml")
    for x in soup.find(class_='mobile-table').find_all("tr"):
        td = x.find_all("td")
        if td and len(td) == 21:
            name = td[0].string
            if name in players:
                for i in xrange(1,18):
                    if td[1+i].string != "bye":
                        players[name].t[i-1] = eval(td[1+i].string)

def readDraftRank(qbs, rbs, wrs, tes):
    soup = BeautifulSoup(urlopen(urlRank).read(), "lxml")
    for x in soup.find(class_='mobile-table').find_all("tr"):
        td = x.find_all("td")
        if td and len(td) == 9:
            name = td[1].find("a").string
            pos = td[2].string
            if pos.startswith("QB") and name in qbs:
                qbs[name].rank = int(pos[2:])
            elif pos.startswith("WR") and name in wrs:
                wrs[name].rank = int(pos[2:])
            elif pos.startswith("TE") and name in tes:
                tes[name].rank = int(pos[2:])
            elif pos.startswith("RB") and name in rbs:
                rbs[name].rank = int(pos[2:])

def computePlayers(players):
    for p in players:
        players[p].compute()
    players_sorted = sorted([players[name] for name in players], 
                            key=lambda p: p.avgP)
    for i,p in enumerate(reversed(players_sorted)):
        p.avgPRank = i+1
    players_sorted = sorted([players[name] for name in players], 
                            key=lambda p: p.avgT)
    for i,p in enumerate(reversed(players_sorted)):
        p.avgTRank = i+1

def printStats(players):
    players_sorted = sorted([players[name] for name in players], 
                            key=lambda p: p.totalP)
    d = {}
    for player in reversed(players_sorted[len(players_sorted)-25:]):
        d[player.name] = [player.totalP, player.avgP, player.medianP, 
                          player.stddevP, player.totalT, 
                          player.avgT, player.stddevT]
    pd.set_eng_float_format(accuracy=1, use_eng_prefix=True)
    idx = ["T", "A", "M","V","TT", "AT", "VT"]
    print pd.DataFrame(d, index = idx).transpose().sort("T", ascending=False)
    
def writeToFile(players, f):
    w = csv.writer(open(f, 'w'))
    data = []
    players_sorted = sorted([players[name] for name in players], 
                            key=lambda p: p.rank)
    for p in players_sorted:
        d = [p.stddevP, p.totalP, p.medianP]
        d2= [ p.stddevT,p.totalT]
        if p.rank != -1:
            data.append([p.rank,p.name, "%.1f - %i" % (p.avgP, p.avgPRank)] \
                            + ["%.1f" % x for x in d] + \
                            ["%.1f - %i" %  (p.avgT,p.avgTRank)] + \
                             ["%.1f" % x for x in d2])
    w.writerows(data)

qbs,wrs,rbs,tes = [createPlayers(urlPoints.replace("$POS", p))\
                       for p in ["qb", "ppr-wr", "ppr-rb", "ppr-te"]]
readDraftRank(qbs, rbs, wrs, tes)
for s,p in zip(["wr", "rb", "te"],[wrs, rbs, tes]):
    readTargets(urlTargets.format(s),p)
for p in [qbs,wrs,rbs,tes]:
    computePlayers(p)
    printStats(p)
for s,p in zip(["qb.csv", "wr.csv", "rb.csv", "te.csv"],[qbs,wrs,rbs,tes]):
    writeToFile(p,s)
