import requests
import json
import numpy as np
from pandas.plotting import autocorrelation_plot
import requests
from ftplib import FTP
import pandas as pd
import time
key = 'ZI07CTOUOBYYVES2'

def getTimeSeries(symbol, interval, outputsize = 'full'):
    ''' Returns a JSON with two fields, Meta Data and Time Series (<interval>). Meta Data contains fields Symbol, Last Refreshed, Interval, Output Size, and Time Zone. '''
    
    return json.loads(requests.get('https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=%s&interval=%s&apikey=key&outputsize=%s'%(symbol,interval,outputsize)).text)
    
interval = '1min'
#js = getTimeSeries('XIV', interval)

def getNYSE():
    ''' Returns a list of all ticker symbols currently traded on the NYSE. Data taken from http://www.nasdaq.com/screening/companies-by-industry.aspx?exchange=NYSE '''
    csv = pd.read_csv('NYSE.csv')
    return csv['Symbol'].tolist()

def getDaily(symbol, outputsize='full'):
    return json.loads(requests.get('https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=%s&apikey=%s&outputsize=%s'%(symbol, key, outputsize)).text)


def JSONtoDF(js, continuous = False, interval = 'daily'):
    if interval == 'intraday':
        cols = ['open', 'high', 'low', 'close', 'volume']
        js = js['Time Series (1min)']
    if interval == 'daily':
        cols = ['open', 'high', 'low', 'close', 'adjusted close', 'volume', 'dividend amount', 'split coefficient']
        js = js['Time Series (Daily)']
    df = pd.DataFrame(index = [], columns = cols)
    for x in js:
        temp = pd.DataFrame(index = [x], columns = cols)
        i = 1
        for col in cols:
            temp.loc[x, col] = float(js[x]['%i. %s'%(i,col)])
            i += 1
        df = df.append(temp)
    df = df.set_index(df.index.to_datetime())
    if continuous == True:
        minutes = np.arange(0, len(df), 1)
        df = df.iloc[::-1].set_index(minutes)
    return df

def checkTrue(symbol, threshold, period):
    js = getDaily(symbol)
    df = JSONtoDF(js, interval ='daily')
    df = df['adjusted close']
    maxClose = df.max()
    minClose = df.min()
    maxChange = (maxClose - minClose)/minClose
    if maxChange < threshold:
        return False        # before doing the more intensive calculation, do a simple check to rule out bad companies - unlikely that this will return false though
    # now form sliding windows of 252 trading days (1 year)
    for i in range(0, len(df)-period):
        subdf = df.iloc[i:i+period]
        initialValue = subdf.iloc[i]
        maxValue = subdf.max()
        percentChange = (maxValue - initialValue)/initialValue
        if percentChange > threshold:
            return True
    return False

def getTrues(threshold = .25, period = 252):
    NYSE = getNYSE()
    trues = []
    with open('trues.txt', 'w') as outfile:
        outfile.write('List of NYSE stocks that have surpassed %i%% returns in a %i day period'%(int(threshold*100),period) )
    i = 0
    startTime = time.time()
    for symbol in NYSE:
        try:
            isTrue = checkTrue(symbol, threshold, period)
            # sometimes the alphavantage server is busy (or something) and we get a nonsense result, so let's give it two tries before giving up
        except:
            try:
                isTrue = checkTrue(symbol, threshold, period)
            except:
                print('Failed to evaluate data for %s'%symbol)
                with open('fails.txt', 'a') as outfile:
                    outfile.write(symbol)
        if isTrue:
            trues.append(symbol)
            with open('trues.txt', 'a') as outfile:
                outfile.write('\n%s'%symbol)  
        i += 1
        now = time.time()
        remainingIterations = len(NYSE)-i
        timePerIteration = (now-startTime)/i
        estimatedTimeRemaining = remainingIterations*timePerIteration/3600            # estimated time remaining in hours
        print('%f%% done. Estimated time remaining: %f hours.'%(i/len(NYSE)*100, estimatedTimeRemaining))
    return trues

            
            