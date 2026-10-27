import asyncio, aiohttp, os, time
from datetime import datetime
TELEGRAM_BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN","")
TELEGRAM_CHAT_ID=os.getenv("TELEGRAM_CHAT_ID","")
TELEGRAM_THREAD_ID=os.getenv("TELEGRAM_THREAD_ID","1998")
BINANCE_API="https://fapi.binance.com"
FUNDING_SHORT=0.05
FUNDING_LONG=-0.03
last_sent={}
async def get_tickers(s):
    async with s.get(f"{BINANCE_API}/fapi/v1/ticker/24hr") as r: return await r.json()
async def get_funding(s):
    async with s.get(f"{BINANCE_API}/fapi/v1/premiumIndex") as r:
        d=await r.json(); return {x['symbol']: float(x['lastFundingRate'])*100 for x in d}
async def send_tg(s, text):
    url=f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload={"chat_id": TELEGRAM_CHAT_ID, "text": text}
    if TELEGRAM_THREAD_ID: payload["message_thread_id"]=int(TELEGRAM_THREAD_ID)
    try:
        async with s.post(url, json=payload) as r: print(await r.json())
    except Exception as e: print(e)
async def scan():
    async with aiohttp.ClientSession() as session:
        try:
            tickers=await get_tickers(session); fundings=await get_funding(session)
        except: return
        for t in tickers:
            sym=t['symbol']
            if not sym.endswith('USDT'): continue
            try:
                vol=float(t['quoteVolume']); change=float(t['priceChangePercent']); funding=fundings.get(sym,0)
                if vol<10000000: continue
                side=None
                if funding>=FUNDING_SHORT and change>=12: side="SHORT"
                elif funding<=FUNDING_LONG and change<=-8: side="LONG"
                else: continue
                now=time.time()
                if sym in last_sent and now-last_sent[sym]<1800: continue
                msg=f"{'🔴' if side=='SHORT' else '🟢'} {sym} {side} READY - Funding {funding:.4f}% | Change {change:.2f}% | Price {t['lastPrice']}"
                print(msg); await send_tg(session, msg); last_sent[sym]=time.time()
            except: continue
async def main():
    while True:
        await scan(); await asyncio.sleep(30)
asyncio.run(main())
