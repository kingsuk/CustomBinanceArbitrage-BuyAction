from collections import defaultdict
from operator import itemgetter
from time import time
import config, csv
import datetime
import sys
import math

from binance.client import Client
from binance.exceptions import BinanceAPIException

import json

WRITE_DATA_LIST = []
WRITE_DATA = {}
amount_in_usdt = 20
total_depth = 3
FEE = 0.001       # Binance VIP0 level spot-trade transaction fee for "Taker" (limit order)
ITERATIONS = 5000   # iterations to run
#PRIMARY = ['ETH', 'USDT', 'BTC', 'BNB', 'ADA', 'SOL', 'LINK', 'LTC', 'UNI', 'XTZ','SHIB','DOGE','SXP','SCRT']
PRIMARY = ['USDT', 'BTC','DOGE']


def main():
    start_time = time()
    csvfile = open('arbitrage.csv', 'w', newline='', encoding='UTF8')
    result_writer = csv.writer(csvfile, delimiter=',')

    client = Client(config.API_KEY, config.API_SECRET)
    balance = client.get_asset_balance(asset='USDT')
    print(balance)
    WRITE_DATA["intial_balance"] = balance

    n = 0
    while True:
        n += 1
        print('Interation Count: %d' % n, end='\r')
        prices = get_prices(client)
        #print(prices)
        triangles = list(find_triangles(prices))
        #print(triangles)
        if triangles:
            for triangle in sorted(triangles, key=itemgetter('profit'), reverse=True):
                describe_triangle(prices, triangle, result_writer,client)
                print(n)
            print('________')

def get_prices(client):
    prices = client.get_orderbook_tickers()
    #print(prices)
    prepared = defaultdict(dict)
    for ticker in prices:
        pair = ticker['symbol']
        ask = float(ticker['askPrice'])
        bid = float(ticker['bidPrice'])
        if ask == 0.0:
            continue
        for primary in PRIMARY:
            if pair.endswith(primary):
                secondary = pair[:-len(primary)]
                prepared[primary][secondary] = 1 / ask
                prepared[secondary][primary] = bid

                
            
    #print(prepared)
    return prepared


def find_triangles(prices):
    triangles = []
    starting_coin = 'USDT'
    for triangle in recurse_triangle(prices, starting_coin, starting_coin):
        coins = set(triangle['coins'])
        if not any(prev_triangle == coins for prev_triangle in triangles):
            yield triangle
            triangles.append(coins)
    # starting_coin = 'DOGE'
    # for triangle in recurse_triangle(prices, starting_coin, starting_coin):
    #     coins = set(triangle['coins'])
    #     if not any(prev_triangle == coins for prev_triangle in triangles):
    #         yield triangle
    #         triangles.append(coins)

    # starting_coin = 'BTC'
    # for triangle in recurse_triangle(prices, starting_coin, starting_coin):
    #     coins = set(triangle['coins'])
    #     if not any(prev_triangle == coins for prev_triangle in triangles):
    #         yield triangle
    #         triangles.append(coins)


def recurse_triangle(prices, current_coin, starting_coin, depth_left=total_depth, amount=1.0):
    if depth_left > 0:
        pairs = prices[current_coin]
        for coin, price in pairs.items():
            new_price = (amount * price) * (1.0 - FEE)
            for triangle in recurse_triangle(prices, coin, starting_coin, depth_left - 1, new_price):
                triangle['coins'] = triangle['coins'] + [current_coin]
                #print(triangle)
                yield triangle
                #print(triangle)
    elif current_coin == starting_coin and amount > 1.0:
        yield {
            'coins': [current_coin],
            'profit': amount
        }
    
def check_pair_exists(coin1,coin2,client):
    try:
        symbol_exists = client.get_symbol_ticker(symbol=coin1+coin2)
        return symbol_exists
    except BinanceAPIException as e:
        print("pair doesn't exists: ",coin1+coin2)
        symbol_exists = client.get_symbol_ticker(symbol=coin2+coin1)
        return symbol_exists

def determine_quantity(amount_to_use,pair_list,client):
    global previousBuyQuantity

    for pair in pair_list:
        info=client.get_symbol_info(pair['symbol'])
        #print(info)
        
        for filt in info['filters']:
            if filt['filterType'] == 'MARKET_LOT_SIZE':
                pair['MARKET_LOT_SIZE'] = float(filt['maxQty'])
            if filt['filterType'] == 'LOT_SIZE':
                pair['stepSize'] = filt['stepSize']
            if filt['filterType'] == 'MIN_NOTIONAL':
                pair['MIN_NOTIONAL'] = float(filt['minNotional'])
        lot_step_size = float(pair['stepSize'])
        precision = int(round(-math.log(lot_step_size, 10), 0))
        pair['precision'] = precision
        pair['buy_quantity'] = round(amount_to_use / float(pair['price']),precision)
        pair['MARKET_LOT_SIZE'] = round(pair['MARKET_LOT_SIZE'],precision)
        previousBuyQuantity = pair['buy_quantity']

        if pair['buy_quantity'] > pair['MARKET_LOT_SIZE']:
            # if iteration_count == MAX_ITERATION_COUNT_FILTER:
            #     print("Max recursive iteration count reached")
            #     iteration_count = 0
            #     pair['buy_quantity'] = pair['MARKET_LOT_SIZE'] - 1
            if previousBuyQuantity == pair['buy_quantity']:
                print("Max recursive iteration count reached")
                iteration_count = 0
                pair['buy_quantity'] = pair['MARKET_LOT_SIZE'] - 1
            else:
                print("changing for max lot size: ",pair)
                pair['buy_quantity'] = pair['MARKET_LOT_SIZE']
                new_amout = round(pair['buy_quantity']*float(pair['price']),precision)
                print("new_amount: ",new_amout)
                determine_quantity(new_amout,pair_list,client)
        
    return pair_list

def buy_function_test(pair,client):
    print("Current Executing operation: ",pair)
   
    order = client.create_order(
        symbol=pair['symbol'],
        side=pair['type'],
        type=Client.ORDER_TYPE_MARKET,
        quantity = format(pair['buy_quantity'],'f'),
        newOrderRespType=Client.ORDER_RESP_TYPE_FULL,
    )
    print(order)
    






def describe_triangle(prices, triangle, result_writer,client):
    coins = triangle['coins']
    #print(prices)
    #print(triangle)
    price_percentage = (triangle['profit'] - 1.0) * 100
    describe = f"{datetime.datetime.now()} {'->'.join(coins):26} {round(price_percentage, 4):-7}% profit"
    print(describe)
    #result_writer.writerow([datetime.datetime.now(), '->'.join(coins), round(price_percentage, 4)])

    buy_pair_list = []
    

    for i in range(len(coins) - 1):
        metadata = {}
        first = coins[i]
        second = coins[i + 1]
        if(second=="USDT"):
            buy_pair = check_pair_exists(second,first,client)
            metadata['type'] = Client.SIDE_SELL
        else:
            buy_pair = second+first
            buy_pair = check_pair_exists(second,first,client)
            print(buy_pair)
            metadata['type'] = Client.SIDE_BUY
        metadata['symbol'] = buy_pair['symbol']
        metadata['price'] = buy_pair['price']

        buy_pair_list.append(metadata)

    buy_pair_list = determine_quantity(amount_in_usdt,buy_pair_list,client)

    print("Final dataset: ",buy_pair_list)
    WRITE_DATA["Final Trade Set"] = buy_pair_list

    try:
        for index,pair in enumerate(buy_pair_list):
            buy_function_test(pair,client)
    except BinanceAPIException as e:
        print(e)
        WRITE_DATA["Exception"] = "Error in "+index+" Transaction: "+e
        sys.exit()
    finally:
        WRITE_DATA["Describe"] = describe
        balance = client.get_asset_balance(asset='USDT')
        print(balance)
        WRITE_DATA["current_balance"] = balance
        with open('log.json', 'w') as convert_file:
            WRITE_DATA_LIST.append(WRITE_DATA)
            convert_file.write(json.dumps(WRITE_DATA_LIST))

    sys.exit()
            
        

    # for i in range(len(coins) - 1):
    #     print("Count: ",i)
    #     first = coins[i]
    #     second = coins[i + 1]
    #     print(f"     {second:4} / {first:4}: {prices[first][second]:-17.8f}")
    #     if(second=="USDT"):
    #         buy_pair = first+second
    #     else:
    #         buy_pair = second+first
        
    #     buy_pair = check_pair_exists(second,first,client)

    #     print("Buy PAIR ",buy_pair)
    #     try:
    #         buy_function(buy_pair,client)
    #     except BinanceAPIException as e:
    #         print(e.message)
    #         if(e=="Filter failure: LOT_SIZE"):
    #             print("LotFail")
    #         elif(e.message=="Invalid symbol."):
    #             print("InvalidSymbol")
                
    #         elif(e=="Account has insufficient balance for requested action."):
    #             print("InsufficentBalance")
    #         elif(e.message=="Filter failure: MARKET_LOT_SIZE"):
    #             print("marketLotSize divide by 10")
    #         #sys.exit()


    # balance = client.get_asset_balance(asset='USDT')
    # print(balance)

    # print('')
    # #sys.exit()


# def buy_function(buy_pair,client):  

#     print("---------------------")
#     print("buy pair: ",buy_pair)
#     #h = input()
#     buy_price = client.get_symbol_ticker(symbol=buy_pair)
#     print("buy price: ",buy_price)


#     info=client.get_symbol_info(buy_pair)
#     details = {}
#     for filt in info['filters']:
#         if filt['filterType'] == 'MARKET_LOT_SIZE':
#             details['MARKET_LOT_SIZE'] = filt
#         if filt['filterType'] == 'LOT_SIZE':
#             details['LOT_SIZE'] = filt
#     lot_step_size = float(details['LOT_SIZE']['stepSize'])
#     precision = int(round(-math.log(lot_step_size, 10), 0))


#     buy_quantity = round(amount_in_usdt / float(buy_price['price']),precision)

#     print("buy quantity: ",buy_quantity)

#     order = client.create_test_order(
#         symbol=buy_pair,
#         side=Client.SIDE_BUY,
#         type=Client.ORDER_TYPE_MARKET,
#         quantity=buy_quantity,
#         newOrderRespType=Client.ORDER_RESP_TYPE_FULL,
#     )
#     print(order)

main()