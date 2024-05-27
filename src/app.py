# Import Libraries
import dash
from dash import html, callback, Input, Output
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import random
from gnews import GNews
from dash import dcc
import pandas as pd
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup
import datetime
from datetime import time, timedelta
import yfinance as yf
import time
from dotenv import load_dotenv
import os


#Load env file and connect api's
load_dotenv()

# Load Luno Client
# lunoClient = Client(api_key_id=os.getenv('LUNO_API_KEY_ID'),
#             api_key_secret=os.getenv('LUNO_API_KEY_SECRET'))

# valrClient = Client(api_key='38a8353ed7f8c72e058b645c43b739bb092e7846822f88d411dcf96cb6de4169',
#            api_secret='3b6017e2817c4804c66369e8770670c825615a6f0a04211327a6d674bc137142')

s=requests.session()

#Define variables

offshoreBid100 = 18.45
offshoreBid200 = 18.55
offshoreBid300 = 18.65
offshoreBid400 = 18.75
offshoreBid500 = 18.85

offshoreOffer100 = 18.55
offshoreOffer200 = 18.65
offshoreOffer300 = 18.75
offshoreOffer400 = 18.85
offshoreOffer500 = 18.95

# Plotly graph themes
theme='simple_white'

#Plotly image path
image_path = 'assets/lunoLogo.png'

#Candles dataframe variables
timeLag=3
currencyPairs=['USDTZAR', 'XBTZAR']

#Yahoo finance tickers
tickerStrings=['ZAR=X']

#Market Data Functions
def candles(currencyPairs, timeLag):

    from luno_python.client import Client

    # Load Luno Client
    lunoClient = Client(api_key_id=os.getenv('LUNO_API_KEY_ID'),
            api_key_secret=os.getenv('LUNO_API_KEY_SECRET'))

    my_datetime = datetime.datetime.now() - timedelta(hours=timeLag, minutes=0)
    unix=int(time.mktime(my_datetime .timetuple()) * 1000)

    candlePairs = []

    for currencyPair in currencyPairs:

        tradesPair = lunoClient.get_candles(pair=currencyPair, since=unix, duration=60)
        candlesPair = pd.DataFrame(tradesPair['candles'])
        candlesPair['timestamp']=candlesPair.apply(lambda x: datetime.datetime.fromtimestamp((x['timestamp']/1000)), axis=1)
        candlesPair.rename(columns={'timestamp':'time'}, inplace=True)
        candlesPair['time'] = candlesPair.apply(lambda x: datetime.datetime.time(x['time']), axis=1)
        candlesPair.index = candlesPair['time']
        candlesPair = candlesPair.drop(['time'], axis=1, errors='ignore')
        candlesPair = candlesPair[['close']]
        candlesPair['close'] = candlesPair.apply(lambda x: float(x['close']), axis=1)
        candlesPair.columns = [currencyPair]
        candlePairs.append(candlesPair)

    allCandles = pd.concat([candlePairs[0],candlePairs[1]], axis=1)

    return allCandles

def currencyUSD(tickerStrings):
    data = yf.download(tickerStrings, period="1d", interval='1m')
    data=data.ffill()
    data=data.dropna()
    data.index = data.index.tz_localize(None)
    data.index = data.index + timedelta(hours=2, minutes=0)
    dt = data.index
    zar = data['Close'].values

    allCurrencies=pd.DataFrame(data={'time': dt, 'ZARUSD':zar})
    allCurrencies['time'] = allCurrencies.apply(lambda x: datetime.datetime.time(x['time']), axis=1)
    allCurrencies.index = allCurrencies['time']
    allCurrencies = allCurrencies.drop(['time'], axis=1, errors='ignore')

    return allCurrencies

def premiumCalcs(allCandles, allCurrencies):
    dfAll = pd.concat([allCandles, allCurrencies], axis=1)
    dfAll=dfAll.dropna()
    dfAll['USDT Premium'] = (((dfAll['USDTZAR']) / dfAll['ZARUSD']) - 1)
    
    return dfAll

# VALR Live Prices
def getValrUSDTOrders():
    from valr_python import Client

    valrClient = Client(api_key='VALR_API_KEY_ID',
           api_secret='VALR_API_KEY_SECRET')
    
    order_book=valrClient.get_order_book_public('USDTZAR')

    return order_book


def getUsdtValrPrices(order_book, vol=0):
    #Bids
    bids = pd.DataFrame(order_book['Bids'])
    bids = bids[['quantity', 'price']]
    bids['price'] = bids.apply(lambda x : float(x['price']), axis=1)
    bids['quantity'] = bids.apply(lambda x : float(x['quantity']), axis=1)
    bids['vwap'] = bids['price'] * bids['quantity']
    bids['rollingQuantity'] = bids['quantity'].cumsum()
    bids['rollingVWAP'] = bids['vwap'].cumsum()
    bids['avgPrice'] = bids['rollingVWAP'] / bids['rollingQuantity']

    try:
        valrUsdtBid = bids[bids['rollingQuantity'] >= vol]['avgPrice'].iloc[0]
    except:
        valrUsdtBid = 0

    #Asks
    asks = pd.DataFrame(order_book['Asks'])
    asks = asks[['quantity', 'price']]
    asks['price'] = asks.apply(lambda x : float(x['price']), axis=1)
    asks['quantity'] = asks.apply(lambda x : float(x['quantity']), axis=1)
    asks['vwap'] = asks['price'] * asks['quantity']
    asks['rollingQuantity'] = asks['quantity'].cumsum()
    asks['rollingVWAP'] = asks['vwap'].cumsum()
    asks['avgPrice'] = asks['rollingVWAP'] / asks['rollingQuantity']

    try:
        valrUsdtOffer = asks[asks['rollingQuantity'] >= vol]['avgPrice'].iloc[0]
    except:
        valrUsdtOffer = 0

    return valrUsdtBid, valrUsdtOffer



def getValrBTCOrders():
    from valr_python import Client

    valrClient = Client(api_key='VALR_API_KEY_ID',
           api_secret='VALR_API_KEY_SECRET')
    
    order_book=valrClient.get_order_book_public('BTCZAR')

    return order_book

def getBtcValrPrices(order_book, vol=0):
    #Bids
    bids = pd.DataFrame(order_book['Bids'])
    bids = bids[['quantity', 'price']]
    bids['price'] = bids.apply(lambda x : float(x['price']), axis=1)
    bids['quantity'] = bids.apply(lambda x : float(x['quantity']), axis=1)
    bids['vwap'] = bids['price'] * bids['quantity']
    bids['rollingQuantity'] = bids['quantity'].cumsum()
    bids['rollingVWAP'] = bids['vwap'].cumsum()
    bids['avgPrice'] = bids['rollingVWAP'] / bids['rollingQuantity']

    try:
        valrBtcBid = bids[bids['rollingQuantity'] >= vol]['avgPrice'].iloc[0]
    except:
        valrBtcBid = 0

    #Asks
    asks = pd.DataFrame(order_book['Asks'])
    asks = asks[['quantity', 'price']]
    asks['price'] = asks.apply(lambda x : float(x['price']), axis=1)
    asks['quantity'] = asks.apply(lambda x : float(x['quantity']), axis=1)
    asks['vwap'] = asks['price'] * asks['quantity']
    asks['rollingQuantity'] = asks['quantity'].cumsum()
    asks['rollingVWAP'] = asks['vwap'].cumsum()
    asks['avgPrice'] = asks['rollingVWAP'] / asks['rollingQuantity']

    try:
        valrBtcOffer = asks[asks['rollingQuantity'] >= vol]['avgPrice'].iloc[0]
    except:
        valrBtcOffer = 0

    return valrBtcBid, valrBtcOffer



# Luno Live Prices
def getLunoUSDTOrders():
    from luno_python.client import Client

    # Load Luno Client
    lunoClient = Client(api_key_id=os.getenv('LUNO_API_KEY_ID'),
            api_key_secret=os.getenv('LUNO_API_KEY_SECRET'))
    
    # USDTZAR
    order_book = lunoClient.get_order_book_full('USDTZAR')

    return order_book

Initial_order_book = getLunoUSDTOrders()

def getUsdtLunoPrices(order_book, vol=0):
    # Asks
    asks = pd.DataFrame(order_book['asks'])
    asks['price'] = asks.apply(lambda x : float(x['price']), axis=1)
    asks['volume'] = asks.apply(lambda x : float(x['volume']), axis=1)
    asks['vwap'] = asks['price'] * asks['volume']
    asks['rollingVolume'] = asks['volume'].cumsum()
    asks['rollingVWAP'] = asks['vwap'].cumsum()
    asks['avgPrice'] = asks['rollingVWAP'] / asks['rollingVolume']
    
    try:
        lunoUsdtOffer = asks[asks['rollingVolume'] >= vol]['avgPrice'].iloc[0]
    except:
        lunoUsdtOffer = 0

    # Bids
    bids = pd.DataFrame(order_book['bids'])
    bids['price'] = bids.apply(lambda x : float(x['price']), axis=1)
    bids['volume'] = bids.apply(lambda x : float(x['volume']), axis=1)
    bids['vwap'] = bids['price'] * bids['volume']
    bids['rollingVolume'] = bids['volume'].cumsum()
    bids['rollingVWAP'] = bids['vwap'].cumsum()
    bids['avgPrice'] = bids['rollingVWAP'] / bids['rollingVolume']

    try:
        lunoUsdtBid = bids[bids['rollingVolume'] >= vol]['avgPrice'].iloc[0]
    except:
        lunoUsdtBid = 0

    return lunoUsdtBid, lunoUsdtOffer

initial_bid, initial_ask = getUsdtLunoPrices(Initial_order_book, 10000)

# Luno Live Prices
def getLunoBTCOrders():
    from luno_python.client import Client

    # Load Luno Client
    lunoClient = Client(api_key_id=os.getenv('LUNO_API_KEY_ID'),
            api_key_secret=os.getenv('LUNO_API_KEY_SECRET'))
    # BTCZAR
    order_book = lunoClient.get_order_book_full('XBTZAR')

    return order_book


def getBtcLunoPrices(order_book, vol=0):
    #Asks
    asks = pd.DataFrame(order_book['asks'])
    asks['price'] = asks.apply(lambda x : float(x['price']), axis=1)
    asks['volume'] = asks.apply(lambda x : float(x['volume']), axis=1)
    asks['vwap'] = asks['price'] * asks['volume']
    asks['rollingVolume'] = asks['volume'].cumsum()
    asks['rollingVWAP'] = asks['vwap'].cumsum()
    asks['avgPrice'] = asks['rollingVWAP'] / asks['rollingVolume']
    try:
        lunoBtcOffer = asks[asks['rollingVolume'] >= vol]['avgPrice'].iloc[0]
    except:
        lunoBtcOffer = 0

    # Bids
    bids = pd.DataFrame(order_book['bids'])
    bids['price'] = bids.apply(lambda x : float(x['price']), axis=1)
    bids['volume'] = bids.apply(lambda x : float(x['volume']), axis=1)
    bids['vwap'] = bids['price'] * bids['volume']
    bids['rollingVolume'] = bids['volume'].cumsum()
    bids['rollingVWAP'] = bids['vwap'].cumsum()
    bids['avgPrice'] = bids['rollingVWAP'] / bids['rollingVolume']
    try:
        lunoBtcBid = bids[bids['rollingVolume'] >= vol]['avgPrice'].iloc[0]
    except:
        lunoBtcBid = 0

    return lunoBtcBid, lunoBtcOffer

# FX Live Prices
def getLiveInvesting():

    # Investing.com Live Prices
    try:
        url='https://www.investing.com/currencies/live-currency-cross-rates'
        response=s.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        asking= float(soup.find('div', {'class': 'pid-17-ask innerContainer'}).text)
        bidding= float(soup.find('div', {'class': 'pid-17-bid innerContainer'}).text)
    except:
        bidding=1.0000
        asking=1.0000


    #OctaFx Live Prices
    # try:
    #     url='https://www.octafx.com/markets/quotes/mt4/?symbol=USD'
    #     response=s.get(url)
    #     soup = BeautifulSoup(response.text, "html.parser")
    #     ask= soup.find_all('td',{"class": "js-ask-val live-quotes__colored"})
    #     asking = float(ask[60].text)
    #     bid = soup.find_all('td',{"class": "js-bid-val live-quotes__colored"})
    #     bidding=float(bid[60].text)
    # except:
    #     bidding=1.0000
    #     asking=1.0000

    return bidding, asking

def getNews(news='Crypto'):
    google_news = GNews(period='1h', max_results=10)
    crypto_news = google_news.get_news(news)
    df=pd.DataFrame(crypto_news)
    #return crypto_news
    article = df['description'].values
    href = df['url'].values
    return article, href


###Forward Points
fwdT1 = 0.0058
fwdT2 = 0.0042

###Forward Points Graph (Figure)
figFwdPoints = go.Figure(data=[go.Table(
    header=dict(values=['<b>Settlement<b>', '<b>T1<b>', '<b>T2<b>'],
                fill_color='#4678A8',
                align='center',
                line_color='lightgrey',
                font=dict(color='white', size=12)),
    cells=dict(values=[['Carry'], '{:.4f}'.format(fwdT1), '{:.4f}'.format(fwdT2)],
            fill_color='rgb(242,242,242)',
            align='center',
            line_color='lightgrey',
            font=dict(color='black', size=11)))
])

figFwdPoints.update_layout(margin=dict(l=0, r=0, b=0,t=0), width=385, height=50)

###Dash Styling

###Dash Components
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP])

mytitle = dcc.Markdown(id='my-title', children='Luno Trading Dashboard')
usdtZar = dcc.Graph(id='usdtZar', figure={})
btcZar = dcc.Graph(id='btcZar', figure={})
zarUsd = dcc.Graph(id='zarUsd', figure={})
premiumPair = dcc.Graph(id='premiumPair', figure={})
brokerTrades = dcc.Graph(id='brokerTrades', figure={})
b2c2Trades = dcc.Graph(id='b2c2Trades', figure={})
forwardPoints = dcc.Graph(id='forwardPoints', figure=figFwdPoints)
bidInput = dbc.Input(id="bidInput", type="number", min=0.0001, max=50.0000, step=0.0001, value='{:.4f}'.format(initial_bid), placeholder="Buy At", className='text-center', style={'width':'7vw', 'height': '2.2vh', 'margin-bottom':'5px'})
offerInput = dbc.Input(id="offerInput", type="number", min=0.0001, max=50.0000, step=0.00001, value='{:.4f}'.format(initial_ask), placeholder="Sell At", className='text-center', style={'width':'7vw', 'height': '2.2vh', 'margin-bottom':'5px'})
usdtVolInput = dbc.Input(id="usdtVolInput", type="number", min=1, max=100000, step=1, value=10000, placeholder="USDT VOL", className='text-center', style={'width':'7vw', 'height': '2.2vh', 'margin-bottom':'5px'})
btcVolInput = dbc.Input(id="btcVolInput", type="number", min=0.01, max=50.00, step=0.01, value=1, placeholder="BTC VOL", className='text-center', style={'width':'7vw', 'height': '2.2vh', 'margin-bottom':'5px'})
brokerVolume1 = dbc.Input(id="brokerVol1", type="number", min=1, max=100000, step=1, value=10000, placeholder="Vol1", className='text-center', style={'width':'7vw', 'height': '2.2vh','margin-bottom':'5px'})
brokerVolume2 = dbc.Input(id="brokerVol2", type="number", min=1, max=100000, step=1, value=20000, placeholder="Vol2", className='text-center', style={'width':'7vw', 'height': '2.2vh', 'margin-bottom':'5px'})
keyInput = dbc.Input(id="keyInput", type="text", valid=True, placeholder="Keyword", value='Crypto', debounce=False, className='text-center', style={'width':'7vw', 'height': '2.2vh', 'margin-bottom':'5px'})

brokerProvider = [
    dbc.CardHeader("Provider",style={"color": "WhiteSmoke","background-color": "DarkSalmon", "font-size": "15px"}, id='brokerProviderHeader',className="text-center"),
    dbc.CardBody(
        [
            html.A("BROKER", href='https://www.luno.com/trade/markets/USDTZAR', target='_blank', style={"color": "MidnightBlue","font-size": "12px", 'margin-left':'26px'}),
            html.P("10.0k", id='usdtLunoUnits', style={"color": "MidnightBlue", "font-size": "9px", "margin-left":"5px","margin-bottom":"2px"}, className="card-text text-center"),
        ], style={"color": "white" ,"background-color": "Lavender"}, id='brokerProviderBody'
    ),
]

brokerProviderBTC = [
    dbc.CardHeader("Provider",style={"color": "WhiteSmoke","background-color": "DarkSalmon", "font-size": "15px"}, id='brokerProviderBTCHeader', className="text-center"),
    dbc.CardBody(
        [
            html.A("BROKER", href='https://www.luno.com/trade/markets/BTCZAR', target='_blank', style={"color": "MidnightBlue","font-size": "12px", 'margin-left':'26px'}),
            html.P("1 btc", id='btcLunoUnits', style={"color": "MidnightBlue", "font-size": "9px", "margin-left":"5px","margin-bottom":"2px"}, className="card-text text-center"),
        ], style={"color": "white" ,"background-color": "Lavender"}, id='brokerProviderBTCBody',
    ),
]


valrProvider = [
    dbc.CardBody(
        [
            html.A("VALR", href='https://www.valr.com/exchange/USDT/ZAR', target='_blank', style={"color": "MidnightBlue", "font-size": "12px",'margin-left':'36px'}),
            html.P("10.0k", id='usdtValrUnits',style={"color": "MidnightBlue", "font-size": "9px", "margin-left":"5px","margin-bottom":"2.5px"}, className="card-text text-center"),
        ], style={"color": "white" , "background-color": "PeachPuff"}, id='valrProviderBody'
    ),
]

valrProviderBTC = [
    dbc.CardBody(
        [
            html.A("VALR", href='https://www.valr.com/exchange/BTC/ZAR', target='_blank', style={"color": "MidnightBlue", "font-size": "12px",'margin-left':'36px'}),
            html.P("1 btc",id='btcValrUnits', style={"color": "MidnightBlue", "font-size": "9px", "margin-left":"5px","margin-bottom":"2.5px"}, className="card-text text-center"),
        ], style={"color": "white" , "background-color": "PeachPuff"}, id='valrProviderBTCBody',
    ),
]


forexProvider = [
    dbc.CardHeader("Provider",style={"color": "WhiteSmoke","background-color": "DarkSeaGreen", "font-size":'15px'}, id='forexProviderHeader', className="text-center"),
    dbc.CardBody(
        [
            html.A("investing", href='https://www.investing.com/currencies/live-currency-cross-rates', target='_blank', style={"color": "MidnightBlue", "font-size": "12px","margin-bottom":"0px", "margin-top":"0px", 'margin-left':'25px'}),
            html.A("OCTAFX",href='https://www.octafx.com/markets/quotes/mt4/?symbol=USD', target='_blank', style={"color": "MidnightBlue","font-size": "9px","margin-bottom":"0px", "margin-top":"0px", 'margin-left':'30px'}),
        ], style={"color": "white" ,"background-color": "lavenderblush"}, id='forexProviderBody',
    ),
]

 
countryProvider = [
    dbc.CardHeader("Provider",style={"color": "WhiteSmoke","background-color": "DarkSeaGreen", "font-size":'15px'}, id='countryProviderHeader', className="text-center"),
    dbc.CardBody(
        [
            html.H1("COUNTRY", style={"color": "MidnightBlue", "font-size": "12px"}, className="card-title text-center"),
            html.P("Premium",style={"color": "MidnightBlue","font-size": "9px", "margin-left":"4px","margin-bottom":"0px", 'margin-top':'21px'}, className="card-text text-center"),
        ], style={"color": "white" ,"background-color": "lavenderblush"}, id='countryProviderBody'
    ),
]

# countryProviderBTC = [
#     dbc.CardBody(
#         [
#             html.H1("COUNTRY", style={"color": "MidnightBlue", "font-size": "12px"}, className="card-title text-center"),
#             html.P("Premium",style={"color": "MidnightBlue","font-size": "9px", "margin-left":"4px","margin-bottom":"3px", 'margin-top':'0px'}, className="card-text text-center"),
#         ], style={"color": "white" ,"background-color": "PaleGoldenRod"}
#     ),
# ]

premiumProvider = [
    dbc.CardHeader("Calculation",style={"color": "WhiteSmoke","background-color": "PaleVioletRed", "font-size": "15px"}, id='premiumProviderHeader', className="text-center"),
    dbc.CardBody(
        [
            html.H1("Country", style={"color": "MidnightBlue","font-size": "12px",'margin-top':'0px', 'margin-bottom':'10px'}, className="card-title text-center"),
            html.P("Premium",style={"color": "MidnightBlue", "font-size": "9px", "margin-left":"0px",'margin-top':'8px', 'margin-bottom':'2.5px'}, className="card-text text-center"),
        ], style={"color": "white" ,"background-color": "LightGoldenRodYellow"}, id='premiumProviderBody',
    ),
]


brokerBid = [
    dbc.CardHeader("Bid",style={"color": "WhiteSmoke","background-color": "DarkSalmon", "font-size": "15px"}, id='brokerBidHeader' ,className="text-center"),
    dbc.CardBody(
        [
            html.H1(id='luno-usdtBid', style={"color": "green", "font-size": "12px", 'margin-top':'0px', 'margin-bottom':'1px'}, className="card-title text-center"),
            html.I(id='luno-usdtBidIcon', style={"color": "green", "font-size": "9px", "margin-left":"35px", 'margin-top':'0px', 'margin-bottom':'0px'}, className="bi bi-caret-up-fill card-text"),

        ], style={"color": "white" ,"background-color": "Lavender"}, id='brokerBidBody'
    ),
]

brokerBidBTC = [
    dbc.CardHeader("Bid",style={"color": "WhiteSmoke","background-color": "DarkSalmon", "font-size": "15px"}, id='brokerBidBTCHeader', className="text-center"),
    dbc.CardBody(
        [
            html.H1(id='luno-btcBid', style={"color": "green", "font-size": "12px", 'margin-top':'0px', 'margin-bottom':'1px'}, className="card-title text-center"),
            html.I(id='luno-btcBidIcon', style={"color": "green", "font-size": "9px", "margin-left":"35px", 'margin-top':'0px', 'margin-bottom':'0px'}, className="bi bi-caret-up-fill card-text"),

        ], style={"color": "white" ,"background-color": "Lavender"}, id='brokerBidBTCBody',
    ),
]


valrBid = [
    dbc.CardBody(
        [
            html.H1(id='valr-usdtBid', style={"color": "green", "font-size": "12px", 'margin-top':'0px', 'margin-bottom':'2px'}, className="card-title text-center"),
            html.I(id='valr-usdtBidIcon', style={"color": "green", "font-size": "9px", "margin-left":"35px", 'margin-top':'0px', 'margin-bottom':'0px'}, className="bi bi-caret-up-fill"),
        ], style={"color": "white" , "background-color": "PeachPuff"}, id='valrBidBody'
    ),
]

valrBidBTC = [
    dbc.CardBody(
        [
            html.H1(id='valr-btcBid', style={"color": "green", "font-size": "12px", 'margin-top':'0px', 'margin-bottom':'2px'}, className="card-title text-center"),
            html.I(id='valr-btcBidIcon', style={"color": "green", "font-size": "9px", "margin-left":"35px", 'margin-top':'0px', 'margin-bottom':'0px'}, className="bi bi-caret-up-fill"),
        ], style={"color": "white" , "background-color": "PeachPuff"}, id='valrBidBTCBody',
    ),
]


forexBid = [
    dbc.CardHeader("Bid",style={"color": "WhiteSmoke","background-color": "DarkSeaGreen", "font-size":'15px'}, id='forexBidHeader', className="text-center"),
    dbc.CardBody(
        [
            html.H1(id='investing-zarBid', style={"color": "green", "font-size": "12px", 'margin-top':'10px', 'margin-bottom':'0px'}, className="card-title text-center"),
            html.I(id='investing-zarBidIcon', style={"color": "green", "font-size": "9px", "margin-left":"25px", 'margin-top':'0px', 'margin-bottom':'0px'}, className="bi bi-caret-up-fill"),
        ], style={"color": "white" ,"background-color": "lavenderblush"}, id='forexBidBody',
    ),
]


countryBid = [
    dbc.CardHeader("Bid",style={"color": "WhiteSmoke","background-color": "DarkSeaGreen", "font-size":'15px'}, id='countryBidHeader', className="text-center"),
    dbc.CardBody(
        [
            html.H1(id='mktImpliedBid',style={"color": "green", "font-size": "12px", 'margin-top':'21px', 'margin-bottom':'0px'}, className="card-title text-center"),
            html.I(id='mktImpliedBidIcon', style={"color": "green", "font-size": "9px", "margin-left":"35px", 'margin-top':'0px', 'margin-bottom':'0px'}, className="bi bi-caret-up-fill"),
        ], style={"color": "white" ,"background-color": "lavenderblush"}, id='countryBidBody'
    ),
]


# countryBidBTC = [
#     dbc.CardBody(
#         [
#             html.H1(style={"color": "green", "font-size": "12px", 'margin-top':'0px', 'margin-bottom':'0px'}, className="card-title text-center"),
#             html.I(style={"color": "green", "font-size": "9px", "margin-left":"35px", 'margin-top':'0px', 'margin-bottom':'0px'}, className="bi bi-caret-up-fill"),
#         ], style={"color": "white" ,"background-color": "PaleGoldenRod"}
#     ),
# ]

premiumBid = [
    dbc.CardHeader("Bid",style={"color": "WhiteSmoke","background-color": "PaleVioletRed", "font-size":'15px'}, id='premiumBidHeader', className="text-center"),
    dbc.CardBody(
        [
            html.H1(id='mktComputedBid', style={"color": "green", "font-size": "12px",'margin-top':'0px', 'margin-bottom':'0px'}, className="card-title text-center"),
            html.I(id='mktComputedBidIcon', style={"color": "green", "font-size": "9px", "margin-left":"35px",'margin-top':'0px', 'margin-bottom':'0px'}, className="bi bi-graph-up-arrow"),

        ], style={"color": "white" ,"background-color": "LightGoldenRodYellow"}, id='premiumBidBody',
    ),
]


brokerOffer = [
    dbc.CardHeader("Ask", style={"color": "WhiteSmoke" ,"background-color": "DarkSalmon", "font-size": "15px"}, id='brokerOfferHeader', className="text-center"),
    dbc.CardBody(
        [
            html.H1(id='luno-usdtOffer', style={"color": "darkred", "font-size": "12px", 'margin-top':'0px', 'margin-bottom':'1px'}, className="card-title text-center"),
            html.I(id='luno-usdtOfferIcon', style={"color": "darkred", "font-size": "9px", "margin-left":"25px", 'margin-top':'0px', 'margin-bottom':'0px'}, className="bi bi-caret-down-fill")
        ], style={"color": "white" ,"background-color": "Lavender"}, id='brokerOfferBody'
    ),
]

brokerOfferBTC = [
    dbc.CardHeader("Ask", style={"color": "WhiteSmoke" ,"background-color": "DarkSalmon", "font-size": "15px"}, id='brokerOfferBTCHeader',className="text-center"),
    dbc.CardBody(
        [
            html.H1(id='luno-btcOffer', style={"color": "darkred", "font-size": "12px", 'margin-top':'0px', 'margin-bottom':'1px'}, className="card-title text-center"),
            html.I(id='luno-btcOfferIcon', style={"color": "darkred", "font-size": "9px", "margin-left":"25px", 'margin-top':'0px', 'margin-bottom':'0px'}, className="bi bi-caret-down-fill")
        ], style={"color": "white" ,"background-color": "Lavender"}, id='brokerOfferBTCBody',
    ),
]


valrOffer = [
    dbc.CardBody(
        [
            html.H1(id='valr-usdtOffer', style={"color": "darkred", "font-size": "12px", 'margin-top':'0px', 'margin-bottom':'2px'}, className="card-title text-center"),
            html.I(id='valr-usdtOfferIcon', style={"color": "darkred", "font-size": "9px", "margin-left":"25px", 'margin-top':'0px', 'margin-bottom':'0px'}, className="bi bi-caret-down-fill")
        ], style={"color": "white" , "background-color": "PeachPuff"}, id='valrOfferBody'
    ),
]

valrOfferBTC = [
    dbc.CardBody(
        [
            html.H1(id='valr-btcOffer', style={"color": "darkred", "font-size": "12px", 'margin-top':'0px', 'margin-bottom':'2px'}, className="card-title text-center"),
            html.I(id='valr-btcOfferIcon', style={"color": "darkred", "font-size": "9px", "margin-left":"25px", 'margin-top':'0px', 'margin-bottom':'0px'}, className="bi bi-caret-down-fill")
        ], style={"color": "white" , "background-color": "PeachPuff"}, id='valrOfferBTCBody',
    ),
]

forexOffer = [
    dbc.CardHeader("Ask", style={"color": "WhiteSmoke","background-color": "DarkSeaGreen", "font-size":'15px'}, id='forexOfferHeader', className="text-center"),
    dbc.CardBody(
        [
            html.H1(id='investing-zarOffer', style={"color": "darkred", "font-size": "12px", 'margin-top':'10px', 'margin-bottom':'0px'}, className="card-title text-center"),
            html.I(id='investing-zarOfferIcon', style={"color": "darkred", "margin-left":"25px", "font-size": "9px", 'margin-top':'0px', 'margin-bottom':'0px'}, className="bi bi-caret-down-fill")
        ], style={"color": "white" ,"background-color": "lavenderblush"}, id='forexOfferBody',
    ),
]


countryOffer = [
    dbc.CardHeader("Ask", style={"color": "WhiteSmoke","background-color": "DarkSeaGreen", "font-size":'15px'}, id='countryOfferHeader', className="text-center"),
    dbc.CardBody(
        [
            html.H1(id='mktImpliedOffer',style={"color": "darkred", "font-size": "12px", 'margin-top':'1px', 'margin-bottom':'0px'}, className="card-title text-center"),
            html.I(id='mktImpliedOfferIcon', style={"color": "darkred", "margin-left":"25px","font-size": "9px", 'margin-top':'0px', 'margin-bottom':'0px'}, className="bi bi-caret-down-fill")
        ], style={"color": "white" ,"background-color": "lavenderblush"}, id='countryOfferBody'
    ),
]

# countryOfferBTC = [
#     dbc.CardBody(
#         [
#             html.H1(style={"color": "darkred", "font-size": "12px", 'margin-top':'0px', 'margin-bottom':'0px'}, className="card-title text-center"),
#             html.I(style={"color": "darkred", "margin-left":"25px","font-size": "9px", 'margin-top':'0px', 'margin-bottom':'0px'}, className="bi bi-caret-down-fill")
#         ], style={"color": "white" ,"background-color": "PaleGoldenRod"}
#     ),
# ]

premiumOffer = [
    dbc.CardHeader("Ask", style={"color": "WhiteSmoke","background-color": "PaleVioletRed", "font-size":'15px'},id='premiumOfferHeader', className="text-center"),
    dbc.CardBody(
        [
            html.H1(id='mktComputedOffer', style={"color": "darkred", "font-size": "12px", 'margin-top':'0px', 'margin-bottom':'0px'}, className="card-title text-center"),
            html.I(id='mktComputedOfferIcon', style={"color": "darkred", "font-size": "9px", "margin-left":"25px", 'margin-top':'0px', 'margin-bottom':'0px'}, className="bi bi-graph-down-arrow")
        ], style={"color": "white" ,"background-color": "LightGoldenRodYellow"}, id='premiumOfferBody',
    ),
]


myInterval = dcc.Interval(
    id='interval-component',
    interval=60*1000, # in milliseconds
    n_intervals=0
)

myIntervalReal = dcc.Interval(
    id='interval-component-real',
    interval=1*1000, # in milliseconds
    n_intervals=0
)

myIntervalNews = dcc.Interval(
    id='interval-component-news',
    interval=900*1000, # in milliseconds
    n_intervals=0
)


newsFeed = [
    dbc.CardHeader("Headlines", className="text-left", style={"font-size": "15px"}, id='newsFeedHeader'),
    dbc.CardBody(
        [
            html.A(id="newsfeed1", target="_blank", className="card-text text-left", style={"font-size": "12px"}),
            html.Br(),
            html.A(id="newsfeed2", target="_blank", className="card-text text-left", style={"font-size": "12px"}),
            #html.Br(),
            #html.A(id="newsfeed3", target="_blank", className="card-text text-left", style={"font-size": "12px"}),
        ], id='newsFeedBody',
    )
]


###Dash Layout
#app.layout = dbc.Container([

app.layout = html.Div([
    dbc.Row([
        dbc.Col(html.Img(src=image_path,style={'height':'50%', 'width':'12.5%', "margin-left": 560, 'margin-bottom':'0px','margin-top':'12px'}), width=3),
        dbc.Col([html.H1('LUNO Trading Dashboard', style={'fontSize': 45, "margin-left": 165, 'margin-bottom':'50px','margin-top':'15px'})], width=9)
    ]),

    dbc.Row([
        dbc.Col([html.H6('Daily Graphs'), usdtZar, btcZar], style={'margin-right':'50px'}, width=({"size":1, "order": 1})),
        dbc.Col([html.Br()], width=({"size":1, "order": 1}), style={'width': '16vw', 'height': '0vh'}),


        
        dbc.Col([html.H6('BTC/ZAR'), dbc.Card(brokerProviderBTC, id='brokerProviderBTCCard'), dbc.Card(valrProviderBTC, id='valrProviderBTCCard'), html.Br(), 
                 html.H6('USD/ZAR'), dbc.Card(forexProvider, id='forexProviderCard'), html.Br(), 
                 html.H6('Broker Trades'), brokerTrades, html.Br(), 
                 html.H6('B2C2 Trades'), b2c2Trades, html.Br(),
                 html.H6('Forward Points'), forwardPoints], width=({"size":1, "order": 2}), style={'width': '7vw', 'height': '0vh'}),
                 

        dbc.Popover(target="brokerProviderBTCCard", trigger="hover", id="brokerProviderBTCHover", className="d-none"),
        dbc.Popover(target="valrProviderBTCCard", trigger="hover", id="valrProviderBTCHover", className="d-none"),
        dbc.Popover(target="forexProviderCard", trigger="hover", id="forexProviderHover", className="d-none"),

        dbc.Col([html.H6('Volume', style={'text-align': 'center'}), dbc.Card(brokerBidBTC, id='brokerBidBTCCard'),
                 dbc.Card(valrBidBTC, id='valrBidBTCCard'),
                 html.Br(), html.H6('USD/ZAR', style={'opacity':'0'}), dbc.Card(forexBid, id='forexBidCard'),
                 html.Br(),brokerVolume1],
                 width=({"size":1, "order": 3}),style={'width': '7vw', 'height': '0vh'}),

        dbc.Popover(target="brokerBidBTCCard", trigger="hover", id="brokerBidBTCHover", className="d-none"),
        dbc.Popover(target="valrBidBTCCard", trigger="hover", id="valrBidBTCHover", className="d-none"),
        dbc.Popover(target="forexBidCard", trigger="hover", id="forexBidHover", className="d-none"),


        dbc.Col([btcVolInput, dbc.Card(brokerOfferBTC, id='brokerOfferBTCCard'), dbc.Card(valrOfferBTC, id='valrOfferBTCCard'),
                 html.Br(), html.H6('USD/ZAR', style={'opacity':'0'}), dbc.Card(forexOffer, id='forexOfferCard'),
                 html.Br(),brokerVolume2],
                 width=({"size":1, "order": 4}), style={'width': '7vw', 'height': '0vh',}),
        dbc.Col([html.Br()], width=({"size":1, "order": 5}), style={'width': '3vw', 'height': '0vh'}),


        dbc.Popover(target="brokerOfferBTCCard", trigger="hover", id="brokerOfferBTCHover", className="d-none"),
        dbc.Popover(target="valrOfferBTCCard", trigger="hover", id="valrOfferBTCHover", className="d-none"),
        dbc.Popover(target="forexOfferCard", trigger="hover", id="forexOfferHover", className="d-none"),


        dbc.Col([html.H6('USDT/ZAR'), dbc.Card(brokerProvider, id='brokerProviderCard'), dbc.Card(valrProvider, id='valrProviderCard'), 
                 html.Br(), html.H6('Mkt Implied'), dbc.Card(countryProvider, id='countryProviderCard'),
                 html.Br(), html.H6('Computed'), dbc.Card(premiumProvider, id='premiumProviderCard'),
                 html.Br(), html.H6('News Feed'), dbc.Card(newsFeed, id='newsFeedCard', color="light", outline=True, style={'width': '21vw', 'height': '18.5vh'})],
                 width=({"size":1, "order": 5}), style={'width': '7vw', 'height': '0vh'}),


        dbc.Popover(target="brokerProviderCard", trigger="hover", id="brokerProviderHover", className="d-none"),
        dbc.Popover(target="valrProviderCard", trigger="hover", id="valrProviderHover", className="d-none"),
        dbc.Popover(target="countryProviderCard", trigger="hover", id="countryProviderHover", className="d-none"),
        dbc.Popover(target="premiumProviderCard", trigger="hover", id="premiumProviderHover", className="d-none"),
        dbc.Popover(target="newsFeedCard", trigger="hover", id="newsFeedHover", className="d-none"),

        dbc.Col([html.H6('Volume', style={'text-align': 'center'}), dbc.Card(brokerBid, id='brokerBidCard'), 
                 dbc.Card(valrBid, id='valrBidCard'),
                 html.Br(), html.H6('Implied', style={'opacity':'0'}), dbc.Card(countryBid, id='countryBidCard'),
                 html.Br(), bidInput, dbc.Card(premiumBid, id='premiumBidCard'),
                 html.Br(), html.H6('Search', style={'text-align': 'center'})], width=({"size":1, "order": 5}),
                 style={'width': '7vw', 'height': '0vh'}),


        dbc.Popover(target="brokerBidCard", trigger="hover", id="brokerBidHover", className="d-none"),
        dbc.Popover(target="valrBidCard", trigger="hover", id="valrBidHover", className="d-none"),
        dbc.Popover(target="countryBidCard", trigger="hover", id="countryBidHover", className="d-none"),
        dbc.Popover(target="premiumBidCard", trigger="hover", id="premiumBidHover", className="d-none"),


        dbc.Col([usdtVolInput, dbc.Card(brokerOffer, id='brokerOfferCard'), dbc.Card(valrOffer, id='valrOfferCard'),
                 html.Br(), html.H6('Implied', style={'opacity':'0'}), dbc.Card(countryOffer, id='countryOfferCard'),
                 html.Br(), offerInput, dbc.Card(premiumOffer, id='premiumOfferCard'),
                 html.Br(),keyInput],width=({"size":1, "order": 5}), style={'width': '7vw', 'height': '0vh'}),
        ], style={'margin-left':'212px'}, className='g-0'),



        dbc.Popover(target="brokerOfferCard", trigger="hover", id="brokerOfferHover", className="d-none"),
        dbc.Popover(target="valrOfferCard", trigger="hover", id="valrOfferHover", className="d-none"),
        dbc.Popover(target="countryOfferCard", trigger="hover", id="countryOfferHover", className="d-none"),
        dbc.Popover(target="premiumOfferCard", trigger="hover", id="premiumOfferHover", className="d-none"),

    dbc.Row([
        dbc.Col([zarUsd], width=4),
    ], style={'margin-left':'200px'}),

    dbc.Row([
        dbc.Col([premiumPair], width=4),
    ], style={'margin-left':'200px'}),

    dbc.Row([
        dbc.Col([myInterval], width=9)
    ]),

    dbc.Row([
        dbc.Col([myIntervalReal], width=9)
    ]),
        dbc.Row([
        dbc.Col([myIntervalNews], width=9)
    ]),
    dcc.Store(id='newsDF'),
    dcc.Store(id='usdtValrDf'),
    dcc.Store(id='btcValrDf'),
    dcc.Store(id='usdtLunoDf'),
    dcc.Store(id='btcLunoDf'),

    dcc.Store(id='btcVolAmount'),
    dcc.Store(id='usdtVolAmount'),

    dcc.Store(id='btcBidBrokerPrev', data=1),
    dcc.Store(id='btcBidBrokerCurrent', data=1),

    dcc.Store(id='btcOfferBrokerPrev', data=1),
    dcc.Store(id='btcOfferBrokerCurrent', data=1),

    dcc.Store(id='btcBidValrPrev', data=1),
    dcc.Store(id='btcBidValrCurrent', data=1),
    
    dcc.Store(id='btcOfferValrPrev', data=1),
    dcc.Store(id='btcOfferValrCurrent', data=1),


    dcc.Store(id='usdtBidBrokerPrev', data=1),
    dcc.Store(id='usdtBidBrokerCurrent', data=1),

    dcc.Store(id='usdtOfferBrokerPrev', data=1),
    dcc.Store(id='usdtOfferBrokerCurrent', data=1),

    dcc.Store(id='usdtBidValrPrev', data=1),
    dcc.Store(id='usdtBidValrCurrent', data=1),
    
    dcc.Store(id='usdtOfferValrPrev', data=1),
    dcc.Store(id='usdtOfferValrCurrent', data=1),

    dcc.Store(id='fxBidPrev', data=1),
    dcc.Store(id='fxBidCurrent', data=1),
    
    dcc.Store(id='fxOfferPrev', data=1),
    dcc.Store(id='fxOfferCurrent', data=1),

    dcc.Store(id='impliedBidPrev', data=1),
    dcc.Store(id='impliedBidCurrent', data=1),
    
    dcc.Store(id='impliedOfferPrev', data=1),
    dcc.Store(id='impliedOfferCurrent', data=1),

    dcc.Store(id='computedBidPrev', data=1),
    dcc.Store(id='computedBidCurrent', data=1),
    
    dcc.Store(id='computedOfferPrev', data=1),
    dcc.Store(id='computedOfferCurrent', data=1),

])


###Dash Callbacks


#Get NewsDataframe
@callback(Output('newsDF', 'data'), Input('interval-component-news', 'n_intervals'), Input('keyInput', 'value'))
def UpdateNewsDf(n, key):
    articles, url = getNews(key)
    return articles, url

@callback(Output('usdtValrDf', 'data'), Input('interval-component-real', 'n_intervals'))
def valrUsdtUpdate(n):
    df = getValrUSDTOrders()
    return df

@callback(Output('btcValrDf', 'data'), Input('interval-component-real', 'n_intervals'))
def valrBtcUpdate(n):
    df = getValrBTCOrders()
    return df

@callback(Output('usdtLunoDf', 'data'), Input('interval-component-real', 'n_intervals'))
def lunoUsdtUpdate(n):
    df = getLunoUSDTOrders()
    return df

@callback(Output('btcLunoDf', 'data'), Input('interval-component-real', 'n_intervals'))
def lunoBtcUpdate(n):
    df = getLunoBTCOrders()
    return df


#Update broker btc bid
@callback(Output('luno-btcBidIcon', 'children'), Output('luno-btcBidIcon', 'style'), Output('luno-btcBidIcon', 'className'),
          Output('luno-btcBid', 'style'), Output('btcBidBrokerPrev', 'data'), 
          Input('btcBidBrokerPrev', 'data'), Input('btcBidBrokerCurrent', 'data'))
def UpdatesbtcBrokerMoveBid(prev, curr):

    if (curr <= 1):
        curr = prev

    move = ((float(curr) - float(prev)) / float(prev))

    if(move > 0):
        style2={"color": "green", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "green", "font-size": "12px", 'margin-top':'0px', 'margin-bottom':'1px'}
        cName="bi bi-caret-up-fill"
    elif(move < 0):
        style2={"color": "darkred", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "darkred", "font-size": "12px", 'margin-top':'0px', 'margin-bottom':'1px'}
        cName="bi bi-caret-down-fill"
    else:
        style2={"color": "green", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "green", "font-size": "12px", 'margin-top':'0px', 'margin-bottom':'1px'}
        cName=""

    return '{:.2%}'.format(move), style2, cName, style1, curr

#Update valr btc bid
@callback(Output('valr-btcBidIcon', 'children'), Output('valr-btcBidIcon', 'style'), Output('valr-btcBidIcon', 'className'),
          Output('valr-btcBid', 'style'), Output('btcBidValrPrev', 'data'), 
          Input('btcBidValrPrev', 'data'), Input('btcBidValrCurrent', 'data'))
def UpdatesbtcValrMoveBid(prev, curr):

    if (curr <= 1):
        curr = prev

    move = ((float(curr) - float(prev)) / float(prev))

    if(move > 0):
        style2={"color": "green", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "green", "font-size": "12px", 'margin-top':'1px', 'margin-bottom':'1px'}
        cName="bi bi-caret-up-fill"
    elif(move < 0):
        style2={"color": "darkred", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "darkred", "font-size": "12px", 'margin-top':'1px', 'margin-bottom':'1px'}
        cName="bi bi-caret-down-fill"
    else:
        style2={"color": "green", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "green", "font-size": "12px", 'margin-top':'1px', 'margin-bottom':'1px'}
        cName=""

    return '{:.2%}'.format(move), style2, cName, style1, curr

#Update broker btc offer
@callback(Output('luno-btcOfferIcon', 'children'), Output('luno-btcOfferIcon', 'style'), Output('luno-btcOfferIcon', 'className'),
          Output('luno-btcOffer', 'style'), Output('btcOfferBrokerPrev', 'data'), 
          Input('btcOfferBrokerPrev', 'data'), Input('btcOfferBrokerCurrent', 'data'))
def UpdatesbtcBrokerMoveOffer(prev, curr):

    if (curr <= 1):
        curr = prev

    move = ((float(curr) - float(prev)) / float(prev))

    if(move > 0):
        style2={"color": "green", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "green", "font-size": "12px", 'margin-top':'0px', 'margin-bottom':'0.5px'}
        cName="bi bi-caret-up-fill"
    elif(move < 0):
        style2={"color": "darkred", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "darkred", "font-size": "12px", 'margin-top':'0px', 'margin-bottom':'0.5px'}
        cName="bi bi-caret-down-fill"
    else:
        style2={"color": "green", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "green", "font-size": "12px", 'margin-top':'0px', 'margin-bottom':'0.5px'}
        cName=""

    return '{:.2%}'.format(move), style2, cName, style1, curr

#Update valr btc offer
@callback(Output('valr-btcOfferIcon', 'children'), Output('valr-btcOfferIcon', 'style'), Output('valr-btcOfferIcon', 'className'),
          Output('valr-btcOffer', 'style'), Output('btcOfferValrPrev', 'data'), 
          Input('btcOfferValrPrev', 'data'), Input('btcOfferValrCurrent', 'data'))
def UpdatesbtcValrMoveOffer(prev, curr):

    if (curr <= 1):
        curr = prev

    move = ((float(curr) - float(prev)) / float(prev))

    if(move > 0):
        style2={"color": "green", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "green", "font-size": "12px", 'margin-top':'1px', 'margin-bottom':'0.5px'}
        cName="bi bi-caret-up-fill"
    elif(move < 0):
        style2={"color": "darkred", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "darkred", "font-size": "12px", 'margin-top':'1px', 'margin-bottom':'0.5px'}
        cName="bi bi-caret-down-fill"
    else:
        style2={"color": "green", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "green", "font-size": "12px", 'margin-top':'1px', 'margin-bottom':'0.5px'}
        cName=""

    return '{:.2%}'.format(move), style2, cName, style1, curr


#Update broker usdt bid
@callback(Output('luno-usdtBidIcon', 'children'), Output('luno-usdtBidIcon', 'style'), Output('luno-usdtBidIcon', 'className'),
          Output('luno-usdtBid', 'style'), Output('usdtBidBrokerPrev', 'data'), 
          Input('usdtBidBrokerPrev', 'data'), Input('usdtBidBrokerCurrent', 'data'))
def UpdatesUsdtBrokerMoveBid(prev, curr):

    if (curr <= 1):
        curr = prev

    move = ((float(curr) - float(prev)) / float(prev))

    if(move > 0):
        style2={"color": "green", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "green", "font-size": "12px", 'margin-top':'0px', 'margin-bottom':'1px'}
        cName="bi bi-caret-up-fill"
    elif(move < 0):
        style2={"color": "darkred", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "darkred", "font-size": "12px", 'margin-top':'0px', 'margin-bottom':'1px'}
        cName="bi bi-caret-down-fill"
    else:
        style2={"color": "green", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "green", "font-size": "12px", 'margin-top':'0px', 'margin-bottom':'1px'}
        cName=""

    return '{:.4%}'.format(move), style2, cName, style1, curr

#Update valr usdt bid
@callback(Output('valr-usdtBidIcon', 'children'), Output('valr-usdtBidIcon', 'style'), Output('valr-usdtBidIcon', 'className'),
          Output('valr-usdtBid', 'style'), Output('usdtBidValrPrev', 'data'), 
          Input('usdtBidValrPrev', 'data'), Input('usdtBidValrCurrent', 'data'))
def UpdatesUsdtValrMoveBid(prev, curr):

    if (curr <= 1):
        curr = prev

    move = ((float(curr) - float(prev)) / float(prev))

    if(move > 0):
        style2={"color": "green", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "green", "font-size": "12px", 'margin-top':'1px', 'margin-bottom':'1px'}
        cName="bi bi-caret-up-fill"
    elif(move < 0):
        style2={"color": "darkred", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "darkred", "font-size": "12px", 'margin-top':'1px', 'margin-bottom':'1px'}
        cName="bi bi-caret-down-fill"
    else:
        style2={"color": "green", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "green", "font-size": "12px", 'margin-top':'1px', 'margin-bottom':'1px'}
        cName=""

    return '{:.4%}'.format(move), style2, cName, style1, curr

#Update broker usdt offer
@callback(Output('luno-usdtOfferIcon', 'children'), Output('luno-usdtOfferIcon', 'style'), Output('luno-usdtOfferIcon', 'className'),
          Output('luno-usdtOffer', 'style'), Output('usdtOfferBrokerPrev', 'data'), 
          Input('usdtOfferBrokerPrev', 'data'), Input('usdtOfferBrokerCurrent', 'data'))
def UpdatesUsdtBrokerMoveOffer(prev, curr):

    if (curr <= 1):
        curr = prev

    move = ((float(curr) - float(prev)) / float(prev))

    if(move > 0):
        style2={"color": "green", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'px'}
        style1={"color": "green", "font-size": "12px", 'margin-top':'0px', 'margin-bottom':'0.5px'}
        cName="bi bi-caret-up-fill"
    elif(move < 0):
        style2={"color": "darkred", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "darkred", "font-size": "12px", 'margin-top':'0px', 'margin-bottom':'0.5px'}
        cName="bi bi-caret-down-fill"
    else:
        style2={"color": "green", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "green", "font-size": "12px", 'margin-top':'0px', 'margin-bottom':'0.5px'}
        cName=""

    return '{:.4%}'.format(move), style2, cName, style1, curr

#Update valr usdt offer
@callback(Output('valr-usdtOfferIcon', 'children'), Output('valr-usdtOfferIcon', 'style'), Output('valr-usdtOfferIcon', 'className'),
          Output('valr-usdtOffer', 'style'), Output('usdtOfferValrPrev', 'data'), 
          Input('usdtOfferValrPrev', 'data'), Input('usdtOfferValrCurrent', 'data'))
def UpdatesUsdtValrMoveOffer(prev, curr):

    if (curr <= 1):
        curr = prev

    move = ((float(curr) - float(prev)) / float(prev))

    if(move > 0):
        style2={"color": "green", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "green", "font-size": "12px", 'margin-top':'1px', 'margin-bottom':'0.5px'}
        cName="bi bi-caret-up-fill"
    elif(move < 0):
        style2={"color": "darkred", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "darkred", "font-size": "12px", 'margin-top':'1px', 'margin-bottom':'0.5px'}
        cName="bi bi-caret-down-fill"
    else:
        style2={"color": "green", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "green", "font-size": "12px", 'margin-top':'1px', 'margin-bottom':'0.5px'}
        cName=""

    return '{:.4%}'.format(move), style2, cName, style1, curr

#Update Forex bid
@callback(Output('investing-zarBidIcon', 'children'), Output('investing-zarBidIcon', 'style'), Output('investing-zarBidIcon', 'className'),
          Output('investing-zarBid', 'style'), Output('fxBidPrev', 'data'), 
          Input('fxBidPrev', 'data'), Input('fxBidCurrent', 'data'))
def UpdatesForexMoveBid(prev, curr):

    if (curr <= 1):
        curr = prev

    move = ((float(curr) - float(prev)) / float(prev))

    if(move > 0):
        style2={"color": "green", "font-size": "9px", "margin-left":"25px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "green", "font-size": "12px", 'margin-top':'8.5px', 'margin-bottom':'1px'}
        cName="bi bi-caret-up-fill"
    elif(move < 0):
        style2={"color": "darkred", "font-size": "9px", "margin-left":"25px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "darkred", "font-size": "12px", 'margin-top':'8.5px', 'margin-bottom':'1px'}
        cName="bi bi-caret-down-fill"
    else:
        style2={"color": "green", "font-size": "9px", "margin-left":"25px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "green", "font-size": "12px", 'margin-top':'8.5px', 'margin-bottom':'1px'}
        cName=""

    return '{:.4%}'.format(move), style2, cName, style1, curr


#Update Forex offer
@callback(Output('investing-zarOfferIcon', 'children'), Output('investing-zarOfferIcon', 'style'), Output('investing-zarOfferIcon', 'className'),
          Output('investing-zarOffer', 'style'), Output('fxOfferPrev', 'data'), 
          Input('fxOfferPrev', 'data'), Input('fxOfferCurrent', 'data'))
def UpdatesForexMoveOffer(prev, curr):
    if (curr <= 1):
        curr = prev

    move = ((float(curr) - float(prev)) / float(prev))

    if(move > 0):
        style2={"color": "green", "font-size": "9px", "margin-left":"25px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "green", "font-size": "12px", 'margin-top':'9px', 'margin-bottom':'1px'}
        cName="bi bi-caret-up-fill"
    elif(move < 0):
        style2={"color": "darkred", "font-size": "9px", "margin-left":"25px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "darkred", "font-size": "12px", 'margin-top':'9px', 'margin-bottom':'1px'}
        cName="bi bi-caret-down-fill"
    else:
        style2={"color": "green", "font-size": "9px", "margin-left":"25px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "green", "font-size": "12px", 'margin-top':'9px', 'margin-bottom':'1px'}
        cName=""

    return '{:.4%}'.format(move), style2, cName, style1, curr



#Update Mkt Implied bid
@callback(Output('mktImpliedBidIcon', 'children'), Output('mktImpliedBidIcon', 'style'), Output('mktImpliedBidIcon', 'className'),
          Output('mktImpliedBid', 'style'), Output('impliedBidPrev', 'data'), 
          Input('impliedBidPrev', 'data'), Input('impliedBidCurrent', 'data'))
def UpdatesMktImpliedMoveBid(prev, curr):

    # if (curr <= 1):
    #     curr = prev

    move = (float(curr) - float(prev))

    if(move > 0):
        style2={"color": "green", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "green", "font-size": "12px", 'margin-top':'10px', 'margin-bottom':'0px'}
        cName="bi bi-graph-up-arrow"
    elif(move < 0):
        style2={"color": "darkred", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "darkred", "font-size": "12px", 'margin-top':'10px', 'margin-bottom':'0px'}
        cName="bi bi-graph-down-arrow"
    else:
        style2={"color": "green", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "green", "font-size": "12px", 'margin-top':'10px', 'margin-bottom':'0px'}
        cName=""

    return '{:.2%}'.format(move), style2, cName, style1, curr

#Update Mkt Implied offer
@callback(Output('mktImpliedOfferIcon', 'children'), Output('mktImpliedOfferIcon', 'style'), Output('mktImpliedOfferIcon', 'className'),
          Output('mktImpliedOffer', 'style'), Output('impliedOfferPrev', 'data'), 
          Input('impliedOfferPrev', 'data'), Input('impliedOfferCurrent', 'data'))
def UpdatesMktImpliedMoveOffer(prev, curr):

    # if (curr <= 1):
    #     curr = prev

    move = (float(curr) - float(prev))

    if(move > 0):
        style2={"color": "green", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "green", "font-size": "12px", 'margin-top':'10px', 'margin-bottom':'0px'}
        cName="bi bi-graph-up-arrow"
    elif(move < 0):
        style2={"color": "darkred", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "darkred", "font-size": "12px", 'margin-top':'10px', 'margin-bottom':'0px'}
        cName="bi bi-graph-down-arrow"
    else:
        style2={"color": "green", "font-size": "9px", "margin-left":"30px", 'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "green", "font-size": "12px", 'margin-top':'10px', 'margin-bottom':'0px'}
        cName=""

    return '{:.2%}'.format(move), style2, cName, style1, curr


#Update Computed bid premium
@callback(Output('mktComputedBidIcon', 'children'), Output('mktComputedBidIcon', 'style'), Output('mktComputedBidIcon', 'className'),
          Output('mktComputedBid', 'style'), Output('computedBidPrev', 'data'), 
          Input('computedBidPrev', 'data'), Input('computedBidCurrent', 'data'))
def UpdatesComputedMoveBid(prev, curr):
    
    # if (curr <= 1):
    #     curr = prev

    move = (float(curr) - float(prev))

    if(move > 0):
        style2={"color": "green", "font-size": "9px", "margin-left":"30px",'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "green", "font-size": "12px",'margin-top':'0px', 'margin-bottom':'0.6px'}
        cName="bi bi-graph-up-arrow"
    elif(move < 0):
        style2={"color": "darkred", "font-size": "9px", "margin-left":"30px",'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "darkred", "font-size": "12px",'margin-top':'0px', 'margin-bottom':'0.6px'}
        cName="bi bi-graph-down-arrow"
    else:
        style2={"color": "green", "font-size": "9px", "margin-left":"30px",'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "green", "font-size": "12px",'margin-top':'0px', 'margin-bottom':'0.6px'}
        cName=""

    return '{:.2%}'.format(move), style2, cName, style1, curr



#Update Computed offer premium
@callback(Output('mktComputedOfferIcon', 'children'), Output('mktComputedOfferIcon', 'style'), Output('mktComputedOfferIcon', 'className'),
          Output('mktComputedOffer', 'style'), Output('computedOfferPrev', 'data'), 
          Input('computedOfferPrev', 'data'), Input('computedOfferCurrent', 'data'))
def UpdatesComputedMoveOffer(prev, curr):
    # if (curr <= 1):
    #     curr = prev
    move = (float(curr) - float(prev))

    if(move > 0):
        style2={"color": "green", "font-size": "9px", "margin-left":"30px",'margin-top':'px', 'margin-bottom':'0px'}
        style1={"color": "green", "font-size": "12px",'margin-top':'1px', 'margin-bottom':'0px'}
        cName="bi bi-graph-up-arrow"
    elif(move < 0):
        style2={"color": "darkred", "font-size": "9px", "margin-left":"30px",'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "darkred", "font-size": "12px",'margin-top':'1px', 'margin-bottom':'0px'}
        cName="bi bi-graph-down-arrow"
    else:
        style2={"color": "green", "font-size": "9px", "margin-left":"30px",'margin-top':'0px', 'margin-bottom':'0px'}
        style1={"color": "green", "font-size": "12px",'margin-top':'1px', 'margin-bottom':'0px'}
        cName=""

    return '{:.2%}'.format(move), style2, cName, style1, curr


#Update btc Volume
@callback(Output('btcVolAmount', 'data'), Output('btcLunoUnits', 'children'),
          Output('btcValrUnits', 'children'), Input('btcVolInput', 'value'))
def updateBtcVol(vol):
    units = str(vol)+' btc'
    return vol, units, units

@callback(Output('usdtVolAmount', 'data'), Output('usdtLunoUnits', 'children'),
          Output('usdtValrUnits', 'children'), Input('usdtVolInput', 'value'))
def updateUsdtVol(vol):
    volume= round(vol/1000,1)
    units = str(volume)+'k'
    return vol, units, units


# #Get NewsDataframe
# @callback(Output('newsDF', 'data'), Input('interval-component-news', 'n_intervals'), Input('keyInput', 'value'))
# def UpdateNewsDf(n, key):
#     articles, url = getNews(key)
#     return articles, url

@callback(Output('newsfeed1', 'children'), Output('newsfeed2', 'children'),
          Output('newsfeed1', 'href'), Output('newsfeed2', 'href'),
          Input('newsDF', 'data'), Input('interval-component', 'n_intervals'))

def updateHeadlines(data,n):

    article=data[0]
    href=data[1]

    headline1 = random.choice(article)
    url1 = href[article.index(headline1)]
    article.remove(headline1)
    href.remove(url1)

    headline2 = random.choice(article)
    url2 = href[article.index(headline2)]
    article.remove(headline2)
    href.remove(url2)

    return headline1, headline2, url1, url2


# Valr Live Pricing
@callback(Output('valr-usdtBid', 'children'), Output('valr-usdtOffer', 'children'), 
          Output('valr-btcBid', 'children'), Output('valr-btcOffer', 'children'), 
          Output('usdtBidValrCurrent', 'data'), Output('usdtOfferValrCurrent', 'data'),
          Output('btcBidValrCurrent', 'data'), Output('btcOfferValrCurrent', 'data'),  
          Input('btcValrDf', 'data'), Input('usdtValrDf', 'data'), Input('btcVolAmount', 'data'), Input('usdtVolAmount', 'data'))

def update_valrPrices(df1, df2, vol1, vol2):
    usdtValrBid, usdtValrOffer = getUsdtValrPrices(df2, vol2)
    btcValrBid, btcValrOffer = getBtcValrPrices(df1, vol1)
    return '{:,.4f}'.format(usdtValrBid), '{:,.4f}'.format(usdtValrOffer),'{:,.0f}'.format(btcValrBid), '{:,.0f}'.format(btcValrOffer), float(usdtValrBid), float(usdtValrOffer), float(btcValrBid), float(btcValrOffer)

# Luno Live Pricing
@callback(Output('luno-usdtBid', 'children'), Output('luno-usdtOffer', 'children'), 
          Output('luno-btcBid', 'children'), Output('luno-btcOffer', 'children'),
          Output('usdtBidBrokerCurrent', 'data'), Output('usdtOfferBrokerCurrent', 'data'),
          Output('btcBidBrokerCurrent', 'data'), Output('btcOfferBrokerCurrent', 'data'),  
          Input('btcLunoDf', 'data'), Input('usdtLunoDf', 'data'), Input('btcVolAmount', 'data'), Input('usdtVolAmount', 'data'))

def update_lunoPrices(df1,df2, vol1, vol2):
    usdtLunoBid, usdtLunoOffer = getUsdtLunoPrices(df2, vol2)
    btcLunoBid, btcLunoOffer = getBtcLunoPrices(df1, vol1)
    return '{:,.4f}'.format(usdtLunoBid), '{:,.4f}'.format(usdtLunoOffer),'{:,.0f}'.format(btcLunoBid), '{:,.0f}'.format(btcLunoOffer), float(usdtLunoBid), float(usdtLunoOffer), float(btcLunoBid), float(btcLunoOffer)


# Forex Price
@callback(Output('investing-zarBid', 'children'), Output('investing-zarOffer', 'children'),
          Output('fxBidCurrent', 'data'), Output('fxOfferCurrent', 'data'),
          Input('interval-component-real', 'n_intervals'))
def update_ForexPrices(n):
    zarUsdBid, zarUsdAsk = getLiveInvesting()
    return '{:,.4f}'.format(zarUsdBid), '{:,.4f}'.format(zarUsdAsk), float(zarUsdBid), float(zarUsdAsk)

# Mkt Implied Premium Price
@callback(Output('mktImpliedBid', 'children'), Output('mktImpliedOffer', 'children'),
          Output('impliedBidCurrent', 'data'), Output('impliedOfferCurrent', 'data'), 
          Input('usdtBidBrokerCurrent', 'data'), Input('usdtOfferBrokerCurrent', 'data'),
          Input('fxBidCurrent', 'data'), Input('fxOfferCurrent', 'data'))
def Update_mktImplied(usdtBid, usdtOffer, fxBid, fxOffer):

    bidPremium = ((float(usdtBid)/float(fxOffer)) - 1)
    offerPremium = ((float(usdtOffer)/float(fxBid)) - 1)

    return '{:.2%}'.format(bidPremium), '{:.2%}'.format(offerPremium), float(bidPremium), float(offerPremium)


# Computed Premium Price
@callback(Output('mktComputedBid', 'children'), Output('mktComputedOffer', 'children'),
          Output('computedBidCurrent', 'data'), Output('computedOfferCurrent', 'data'), 
          Input('bidInput', 'value'), Input('offerInput', 'value'),
          Input('fxBidCurrent', 'data'), Input('fxOfferCurrent', 'data'))
def Update_computed(usdtBid, usdtOffer, fxBid, fxOffer):

    bidPremium = ((float(usdtBid)/float(fxOffer)) - 1)
    offerPremium = ((float(usdtOffer)/float(fxBid)) - 1)

    return '{:.2%}'.format(bidPremium), '{:.2%}'.format(offerPremium), float(bidPremium), float(offerPremium)


# Graph Updates
@callback(Output('usdtZar', 'figure'), Output('btcZar', 'figure'), Output('zarUsd', 'figure'), 
          Output('premiumPair', 'figure'), Output('b2c2Trades', 'figure'), Input('interval-component', 'n_intervals'))

def update_graph_live(n):

    lunoCandles = candles(currencyPairs, timeLag)
    fxUsd = currencyUSD(tickerStrings)
    df=premiumCalcs(lunoCandles, fxUsd)

    ##USDT/ZAR Pair

    figUsdtZar = go.Figure()

    figUsdtZar.add_trace(
    go.Scatter(
        x=df.index,
        y=df['USDTZAR'],
        name='USDT/ZAR',
        line_color='darkred',
        showlegend=False,
        opacity=.5
    ))


    figUsdtZar.add_trace(go.Scatter(x=[df.index[-1]],
                         y=[df['USDTZAR'].iloc[-1]],
                         text=['{:,.2f}'.format(df['USDTZAR'].iloc[-1])],
                         mode='markers+text',
                         marker=dict(color='darkblue', size=9),
                         textfont=dict(color='darkblue', size=12),
                         textposition='bottom left',
                         showlegend=False))

    figUsdtZar.update_layout(
        template=theme,
        width=420,
        height=190,
        xaxis=dict(autorange=True,
                title_text='Time',
                title_font=dict(size=9),
                showticklabels=False),
        yaxis=dict(autorange=True,
                title_text='USDT/ZAR',
                title_font=dict(size=9),
                tickfont = dict(size=9)),
        margin=dict (l=50, r=50, t=50, b=50),
        title='<b>USDT/ZAR<b>',
        title_font=dict(size=15,
                    color='grey',
                    family='Arial'),
        title_x=0.5, 
        title_y=0.95,
    )
    
    ##BTC/ZAR Pair

    figBtcZar = go.Figure()

    figBtcZar.add_trace(
    go.Scatter(
        x=df.index,
        y=df['XBTZAR'],
        name='BTC/ZAR',
        line_color='darkblue',
        showlegend=False,
        opacity=.5
    ))

    figBtcZar.add_trace(go.Scatter(x=[df.index[-1]],
                         y=[df['XBTZAR'].iloc[-1]],
                         text=['{:,.0f}'.format(df['XBTZAR'].iloc[-1])],
                         mode='markers+text',
                         marker=dict(color='darkred', size=9),
                         textfont=dict(color='darkred', size=12),
                         textposition='bottom left',
                         showlegend=False))


    figBtcZar.update_layout(
        template=theme,
        width=420,
        height=190,
        xaxis=dict(autorange=True,
                title_text='Time',
                showticklabels=False,
                title_font=dict(size=9)
                ),
        yaxis=dict(autorange=True,
                title_text='BTC/ZAR',
                tickfont=dict(size=9),
                title_font=dict(size=9)),
        margin=dict (l=50, r=50, t=50, b=50),
        title='<b>BTC/ZAR<b>',
        title_font=dict(size=15,
                    color='grey',
                    family='Arial'),
        title_x=0.5,  
        title_y=0.95, 
    )

    ##ZAR/USD Pair

    figZarUsd = go.Figure()

    figZarUsd.add_trace(
    go.Scatter(
        x=df.index,
        y=df['ZARUSD'],
        name='ZAR/USD',
        line_color='darkgreen',
        showlegend=False,
        opacity=.5
    ))

    figZarUsd.add_trace(go.Scatter(x=[df.index[-1]],
                         y=[df['ZARUSD'].iloc[-1]],
                         text=['{:.2f}'.format(df['ZARUSD'].iloc[-1])],
                         mode='markers+text',
                         marker=dict(color='darkred', size=9),
                         textfont=dict(color='darkred', size=12),
                         textposition='bottom left',
                         showlegend=False))


    figZarUsd.update_layout(
        template=theme,
        width=420,
        height=190,
        xaxis=dict(autorange=True,
                title_text='Time',
                showticklabels=False,
                title_font=dict(size=9)
                ),
        yaxis=dict(autorange=True,
                title_text='ZAR/USD',
                title_font=dict(size=9),
                tickfont=dict(size=9)),
        margin=dict (l=50, r=50, t=50, b=50),
        title='<b>ZAR/USD<b>',
        title_font=dict(size=15,
                    color='grey',
                    family='Arial'),
        title_x=0.5,  
        title_y=0.95,
    )



    ##Country Premium

    figPremium = go.Figure()

    figPremium.add_trace(
    go.Scatter(
        x=df.index,
        y=df['USDT Premium'],
        name='Country Premium',
        showlegend=False,
        line_color='darkorange',
        opacity=.5
    ))


    figPremium.add_trace(go.Scatter(x=[df.index[-1]],
                         y=[df['USDT Premium'].iloc[-1]],
                         text=['{:.2%}'.format(df['USDT Premium'].iloc[-1])],
                         mode='markers+text',
                         marker=dict(color='purple', size=9),
                         textfont=dict(color='purple', size=12),
                         textposition='bottom left',
                         showlegend=False))


    figPremium.update_layout(
        template=theme,
        width=420,
        height=190,
        xaxis=dict(autorange=True,
                title_text='Time',
                showticklabels=False,
                title_font=dict(size=9)
                ),
        yaxis=dict(autorange=True,
                title_text='Country Premium',
                tickformat=',.2%',
                title_font=dict(size=9),
                tickfont=dict(size=9)),
        margin=dict (l=50, r=50, t=50, b=50),
        title='<b>Country Premium<b>',
        title_font=dict(size=15,
                    color='grey',
                    family='Arial'),
        title_x=0.5, 
        title_y=0.95,  
    )

    ##B2C2 Trades

    head = ['<b>Volume<b>', '<b>Bid<b>', '<b>Offer<b>']
    labels = ['100k', '200k', '300k', '400k', '500k']

    offshore100bid= ['{:,}'.format(offshoreBid100)]
    offshore200bid= ['{:,}'.format(offshoreBid200)]
    offshore300bid= ['{:,}'.format(offshoreBid300)]
    offshore400bid= ['{:,}'.format(offshoreBid400)]
    offshore500bid= ['{:,}'.format(offshoreBid500)]

    offshore100offer  = ['{:,}'.format(offshoreOffer100)]
    offshore200offer  = ['{:,}'.format(offshoreOffer200)]
    offshore300offer  = ['{:,}'.format(offshoreOffer300)]
    offshore400offer  = ['{:,}'.format(offshoreOffer400)]
    offshore500offer  = ['{:,}'.format(offshoreOffer500)]

    bidpoints = [offshore100bid, offshore200bid,offshore300bid,offshore400bid,offshore500bid]
    offerpoints = [offshore100offer, offshore200offer, offshore300offer, offshore400offer, offshore500offer]

    figB2C2Trades = go.Figure(data=[go.Table(
        header=dict(values=head,
                    fill_color='#4678A8',
                    align='center',
                    line_color='lightgrey',
                    font=dict(color='white', size=12)),
        cells=dict(values=[labels, bidpoints, offerpoints],
                fill_color='rgb(242,242,242)',
                align='center',
                line_color='lightgrey',
                font=dict(color='black', size=11)))
    ])

    figB2C2Trades.update_layout(margin=dict(l=0, r=0, b=0,t=0), width=385, height=130)

    return figUsdtZar, figBtcZar, figZarUsd, figPremium, figB2C2Trades



##Broker Trades
@callback(Output('brokerTrades', 'figure'), Input('brokerVol1', 'value'),
          Input('brokerVol2', 'value'), Input('usdtLunoDf', 'data'))
def UpdateBrokerTable(vol1, vol2, df):

    #patched_fig = Patch()

    volume1= round(vol1/1000,1)
    units1 = str(volume1)+'k'

    volume2= round(vol2/1000,1)
    units2 = str(volume2)+'k'

    usdtLunoBidVol1, usdtLunoOfferVol1 = getUsdtLunoPrices(df, vol1)
    usdtLunoBidVol2, usdtLunoOfferVol2 = getUsdtLunoPrices(df, vol2)

    labels = [units1, units2]

    lunoBidVol1 = '{:,.4f}'.format(usdtLunoBidVol1)
    lunoBidVol2 = '{:,.4f}'.format(usdtLunoBidVol2)

    lunoOfferVol1= '{:,.4f}'.format(usdtLunoOfferVol1)
    lunoOfferVol2  = '{:,.4f}'.format(usdtLunoOfferVol2)

    bidpoints = [lunoBidVol1, lunoBidVol2]
    offerpoints = [lunoOfferVol1, lunoOfferVol2]

    figBrokerTrades = go.Figure(data=[go.Table(
        header=dict(values=['<b>Volume<b>', '<b>Bid<b>', '<b>Offer<b>'],
                    fill_color='#4678A8',
                    align='center',
                    line_color='lightgrey',
                    font=dict(color='white', size=12)),
        cells=dict(values=[labels, bidpoints, offerpoints],
                fill_color='rgb(242,242,242)',
                align='center',
                line_color='lightgrey',
                font=dict(color='black', size=11)))
    ])

    figBrokerTrades.update_layout(margin=dict(l=0, r=0, b=0,t=0), width=385, height=70)

    return figBrokerTrades



@callback(Output('brokerProviderBTCHeader', 'style'), Output('brokerProviderBTCBody', 'style'), Input('brokerProviderBTCHover', 'is_open'))
def changeBrokerProviderStyle(is_open):
    if is_open:
        return {"color": "WhiteSmoke","background-color": "Purple", "font-size": "15px"}, {"color": "white" ,"background-color": "Thistle"}
    else:
        return {"color": "WhiteSmoke","background-color": "DarkSalmon", "font-size": "15px"}, {"color": "white" ,"background-color": "Lavender"}


@callback(Output('brokerBidBTCHeader', 'style'), Output('brokerBidBTCBody', 'style'), Input('brokerBidBTCHover', 'is_open'))
def changeBrokerBidStyle(is_open):
    if is_open:
        return {"color": "WhiteSmoke","background-color": "Purple", "font-size": "15px"}, {"color": "white" ,"background-color": "Thistle"}
    else:
        return {"color": "WhiteSmoke","background-color": "DarkSalmon", "font-size": "15px"}, {"color": "white" ,"background-color": "Lavender"}


@callback(Output('brokerOfferBTCHeader', 'style'), Output('brokerOfferBTCBody', 'style'), Input('brokerOfferBTCHover', 'is_open'))
def changeBrokerOfferStyle(is_open):
    if is_open:
        return {"color": "WhiteSmoke","background-color": "Purple", "font-size": "15px"}, {"color": "white" ,"background-color": "Thistle"}
    else:
        return {"color": "WhiteSmoke","background-color": "DarkSalmon", "font-size": "15px"}, {"color": "white" ,"background-color": "Lavender"}


@callback(Output('valrProviderBTCBody', 'style'), Input('valrProviderBTCHover', 'is_open'))
def changeValrProviderStyle(is_open):
    if is_open:
        return {"color": "white" , "background-color": "Thistle"}
    else:
        return {"color": "white" , "background-color": "PeachPuff"}
    

@callback(Output('valrBidBTCBody', 'style'), Input('valrBidBTCHover', 'is_open'))
def changeValrBidStyle(is_open):
    if is_open:
        return {"color": "white" , "background-color": "Thistle"}
    else:
        return {"color": "white" , "background-color": "PeachPuff"}

@callback(Output('valrOfferBTCBody', 'style'), Input('valrOfferBTCHover', 'is_open'))
def changeValrOfferStyle(is_open):
    if is_open:
        return {"color": "white" , "background-color": "Thistle"}
    else:
        return {"color": "white" , "background-color": "PeachPuff"}
    


#####################################################################
#####################################################################


@callback(Output('brokerProviderHeader', 'style'), Output('brokerProviderBody', 'style'), Input('brokerProviderHover', 'is_open'))
def changeBrokerProviderStyle1(is_open):
    if is_open:
        return {"color": "WhiteSmoke","background-color": "Purple", "font-size": "15px"}, {"color": "white" ,"background-color": "Thistle"}
    else:
        return {"color": "WhiteSmoke","background-color": "DarkSalmon", "font-size": "15px"}, {"color": "white" ,"background-color": "Lavender"}


@callback(Output('brokerBidHeader', 'style'), Output('brokerBidBody', 'style'), Input('brokerBidHover', 'is_open'))
def changeBrokerBidStyle1(is_open):
    if is_open:
        return {"color": "WhiteSmoke","background-color": "Purple", "font-size": "15px"}, {"color": "white" ,"background-color": "Thistle"}
    else:
        return {"color": "WhiteSmoke","background-color": "DarkSalmon", "font-size": "15px"}, {"color": "white" ,"background-color": "Lavender"}


@callback(Output('brokerOfferHeader', 'style'), Output('brokerOfferBody', 'style'), Input('brokerOfferHover', 'is_open'))
def changeBrokerOfferStyle1(is_open):
    if is_open:
        return {"color": "WhiteSmoke","background-color": "Purple", "font-size": "15px"}, {"color": "white" ,"background-color": "Thistle"}
    else:
        return {"color": "WhiteSmoke","background-color": "DarkSalmon", "font-size": "15px"}, {"color": "white" ,"background-color": "Lavender"}


@callback(Output('valrProviderBody', 'style'), Input('valrProviderHover', 'is_open'))
def changeValrProviderStyle1(is_open):
    if is_open:
        return {"color": "white" , "background-color": "Thistle"}
    else:
        return {"color": "white" , "background-color": "PeachPuff"}
    

@callback(Output('valrBidBody', 'style'), Input('valrBidHover', 'is_open'))
def changeValrBidStyle1(is_open):
    if is_open:
        return {"color": "white" , "background-color": "Thistle"}
    else:
        return {"color": "white" , "background-color": "PeachPuff"}

@callback(Output('valrOfferBody', 'style'), Input('valrOfferHover', 'is_open'))
def changeValrOfferStyle1(is_open):
    if is_open:
        return {"color": "white" , "background-color": "Thistle"}
    else:
        return {"color": "white" , "background-color": "PeachPuff"}



######################################################################
######################################################################

@callback(Output('forexProviderHeader', 'style'), Output('forexProviderBody', 'style'), Input('forexProviderHover', 'is_open'))
def changeForexProviderStyle(is_open):
    if is_open:
        return {"color": "WhiteSmoke","background-color": "Purple", "font-size":'15px'}, {"color": "white" ,"background-color": "Thistle"}
    else:
        return {"color": "WhiteSmoke","background-color": "DarkSeaGreen", "font-size":'15px'}, {"color": "white" ,"background-color": "lavenderblush"}


@callback(Output('forexBidHeader', 'style'), Output('forexBidBody', 'style'), Input('forexBidHover', 'is_open'))
def changeForexBidStyle(is_open):
    if is_open:
        return {"color": "WhiteSmoke","background-color": "Purple", "font-size":'15px'}, {"color": "white" ,"background-color": "Thistle"}
    else:
        return {"color": "WhiteSmoke","background-color": "DarkSeaGreen", "font-size":'15px'}, {"color": "white" ,"background-color": "lavenderblush"}
    

@callback(Output('forexOfferHeader', 'style'), Output('forexOfferBody', 'style'), Input('forexOfferHover', 'is_open'))
def changeForexOfferStyle(is_open):
    if is_open:
        return {"color": "WhiteSmoke","background-color": "Purple", "font-size":'15px'}, {"color": "white" ,"background-color": "Thistle"}
    else:
        return {"color": "WhiteSmoke","background-color": "DarkSeaGreen", "font-size":'15px'}, {"color": "white" ,"background-color": "lavenderblush"}

######################################################################
######################################################################

@callback(Output('countryProviderHeader', 'style'), Output('countryProviderBody', 'style'), Input('countryProviderHover', 'is_open'))
def changeCountryProviderStyle(is_open):
    if is_open:
        return {"color": "WhiteSmoke","background-color": "Purple", "font-size":'15px'}, {"color": "white" ,"background-color": "Thistle"}
    else:
        return {"color": "WhiteSmoke","background-color": "DarkSeaGreen", "font-size":'15px'}, {"color": "white" ,"background-color": "lavenderblush"}


@callback(Output('countryBidHeader', 'style'), Output('countryBidBody', 'style'), Input('countryBidHover', 'is_open'))
def changeCountryBidStyle(is_open):
    if is_open:
        return {"color": "WhiteSmoke","background-color": "Purple", "font-size":'15px'}, {"color": "white" ,"background-color": "Thistle"}
    else:
        return {"color": "WhiteSmoke","background-color": "DarkSeaGreen", "font-size":'15px'}, {"color": "white" ,"background-color": "lavenderblush"}
    

@callback(Output('countryOfferHeader', 'style'), Output('countryOfferBody', 'style'), Input('countryOfferHover', 'is_open'))
def changeCountryOfferStyle(is_open):
    if is_open:
        return {"color": "WhiteSmoke","background-color": "Purple", "font-size":'15px'}, {"color": "white" ,"background-color": "Thistle"}
    else:
        return {"color": "WhiteSmoke","background-color": "DarkSeaGreen", "font-size":'15px'}, {"color": "white" ,"background-color": "lavenderblush"}



######################################################################
######################################################################


@callback(Output('premiumProviderHeader', 'style'), Output('premiumProviderBody', 'style'), Input('premiumProviderHover', 'is_open'))
def changeCountryProviderStyle(is_open):
    if is_open:
        return {"color": "WhiteSmoke","background-color": "Purple", "font-size":'15px'}, {"color": "white" ,"background-color": "Thistle"}
    else:
        return {"color": "WhiteSmoke","background-color": "PaleVioletRed", "font-size":'15px'}, {"color": "white" ,"background-color": "LightGoldenRodYellow"}


@callback(Output('premiumBidHeader', 'style'), Output('premiumBidBody', 'style'), Input('premiumBidHover', 'is_open'))
def changeCountryBidStyle(is_open):
    if is_open:
        return {"color": "WhiteSmoke","background-color": "Purple", "font-size":'15px'}, {"color": "white" ,"background-color": "Thistle"}
    else:
        return {"color": "WhiteSmoke","background-color": "PaleVioletRed", "font-size":'15px'}, {"color": "white" ,"background-color": "LightGoldenRodYellow"}
    

@callback(Output('premiumOfferHeader', 'style'), Output('premiumOfferBody', 'style'), Input('premiumOfferHover', 'is_open'))
def changeCountryOfferStyle(is_open):
    if is_open:
        return {"color": "WhiteSmoke","background-color": "Purple", "font-size":'15px'}, {"color": "white" ,"background-color": "Thistle"}
    else:
        return {"color": "WhiteSmoke","background-color": "PaleVioletRed", "font-size":'15px'}, {"color": "white" ,"background-color": "LightGoldenRodYellow"}


######################################################################
######################################################################

@callback(Output('newsFeedHeader', 'style'), Output('newsFeedBody', 'style'), Input('newsFeedHover', 'is_open'))
def changenewsFeedStyle(is_open):
    if is_open:
        return {"color": "Black","background-color": "Thistle", "font-size":'15px'}, {"color": "white" ,"background-color": "Purple"}
    else:
        return {"font-size":'15px'}, {}


######################################################################
######################################################################


#Run app
if __name__=='__main__':
    app.run_server(debug=True)