import asyncio, aiohttp, os, time
from datetime import datetime
from aiohttp import web

TELEGRAM_BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN","")
TELEGRAM_CHAT_ID=os.getenv("TELEGRAM_CHAT_ID","")
TELEGRAM_THREAD_ID=os.getenv("TELEGRAM_THREAD_ID","1998")
BINANCE_API="https://fapi.binance.com"
FUNDING_SHORT=0.05
FUNDING_LONG=-0.03
last_sent={}
is_running = True

async def get_tickers(s):
    async with s.get(f"{BINANCE_API}/fapi/v1/ticker/24hr") as r: return await r.json()
    
async def get_funding(s):
    async with s.get(f"{BINANCE_API}/fapi/v1/premiumIndex") as r:
        d=await r.json(); return {x['symbol']: float(x['lastFundingRate'])*100 for x in d}
        
async def send_tg(s, text):
    if not TELEGRAM_BOT_TOKEN: 
        print(f"[DRY] {text}")
        return
    url=f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload={"chat_id": TELEGRAM_CHAT_ID, "text": text}
    if TELEGRAM_THREAD_ID and TELEGRAM_THREAD_ID!="0":
        try: payload["message_thread_id"]=int(TELEGRAM_THREAD_ID)
        except: pass
    try:
        async with s.post(url, json=payload) as r: 
            data=await r.json()
            print(f"TG {'OK' if data.get('ok') else 'FAIL'}: {text[:60]}")
    except Exception as e: print(f"TG error {e}")

async def scan():
    async with aiohttp.ClientSession() as session:
        try:
            tickers=await get_tickers(session); fundings=await get_funding(session)
        except Exception as e:
            print(f"Binance error {e}"); return
        count=0
        for t in tickers:
            sym=t['symbol']
            if not sym.endswith('USDT'): continue
            try:
                vol=float(t['quoteVolume']); change=float(t['priceChangePercent']); funding=fundings.get(sym,0)
                if vol<8000000: continue
                side=None
                if funding>=FUNDING_SHORT and change>=12: side="SHORT"
                elif funding<=FUNDING_LONG and change<=-8: side="LONG"
                else: continue
                now=time.time()
                if sym in last_sent and now-last_sent[sym]<1800: continue
                msg=f"{'🔴' if side=='SHORT' else '🟢'} {sym} {side} READY - Funding {funding:.4f}% | Change {change:.2f}% | Price {t['lastPrice']}"
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
                await send_tg(session, msg)
                last_sent[sym]=time.time()
                count+=1
                await asyncio.sleep(1)
            except: continue
        print(f"Scan done, found {count} new signals")

async def main_loop():
    print("=== SHORT HUNTER BOT - FREE SERVER ===")
    while is_running:
        try: await scan()
        except Exception as e: print(f"Loop error {e}")
        await asyncio.sleep(30)

# Веб-сервер щоб Render не вбивав
async def handle(request):
    return web.Response(text=f"BOT RUNNING - Last scan {datetime.now()} - Cooldowns: {len(last_sent)}")

async def start_web_and_bot():
    app = web.Application()
    app.router.add_get('/', handle)
    app.router.add_get('/health', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", "10000"))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Web server started on port {port}")
    await main_loop()

if __name__ == "__main__":
    asyncio.run(start_web_and_bot())
