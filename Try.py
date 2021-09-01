from binance.client import Client
import config
from binance.enums import *
import math

client = Client(config.API_KEY, config.API_SECRET)

# get fees for all symbols
fees = client.get_trade_fee()
#print("fees: ",fees)
pair = "CLVUSDT"
#First get ETH price
eth_price = client.get_symbol_ticker(symbol=pair)
print("coin price: ",eth_price)

# Calculate how much ETH $200 can buy


details = {}
info=client.get_symbol_info(pair)
print(info)
for filt in info['filters']:
    if filt['filterType'] == 'MARKET_LOT_SIZE':
        details['MARKET_LOT_SIZE'] = filt
    if filt['filterType'] == 'LOT_SIZE':
        details['LOT_SIZE'] = filt

print(details['LOT_SIZE']['stepSize'])
lot_step_size = float(details['LOT_SIZE']['stepSize'])
precision = int(round(-math.log(lot_step_size, 10), 0))

buy_quantity = round(11 / float(eth_price['price']),precision)
print("buy_quantity: ",buy_quantity)

# Create test order
order = client.create_order(
        symbol=pair,
        side=Client.SIDE_SELL,
        type=Client.ORDER_TYPE_MARKET,
        quantity=10.2,
        newOrderRespType=Client.ORDER_RESP_TYPE_FULL,
    )
print(order)
balance = client.get_asset_balance(asset='USDT')
print(balance)