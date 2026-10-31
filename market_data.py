"""On-demand Tencent daily bars, no credentials. Requests are sequential and bounded.

Provider is a public website endpoint, without availability guarantees. Never
substitutes synthetic data. Only fully completed dates are retained.
"""
import json
import re
import time
from datetime import datetime, timedelta, timezone
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import pandas as pd
from engine import STOCKS, validate_csv

def fetch_daily(market, symbols):
    """Fetch one complete market batch; raise on any failed constituent.

    The returned frame records fallback symbols and retrieval time in attrs.
    Persistence is handled by app.py after validation and a trial analysis.
    """
    if market not in STOCKS: raise ValueError('市场参数错误。')
    if not isinstance(symbols,list) or not 3<=len(symbols)<=12: raise ValueError('每次同步 3～12 只股票。')
    pattern=r'\d{6}' if market=='CN' else r'\d{5}'
    if any(not isinstance(s,str) or not re.fullmatch(pattern,s) for s in symbols) or len(set(symbols))!=len(symbols):
        raise ValueError('代码格式错误或存在重复。A 股 6 位、港股 5 位。')
    now=datetime.now(timezone(timedelta(hours=8)))
    today=now.strftime('%Y-%m-%d')
    meta={s:(n,sec) for s,n,_,sec in STOCKS[market]}; rows=[]; fallback=[]
    for i,symbol in enumerate(symbols):
        if market=='HK': remote='hk'+symbol
        elif symbol.startswith(('6','9')): remote='sh'+symbol
        elif symbol.startswith(('0','2','3')): remote='sz'+symbol
        else: raise ValueError('在线源目前仅适配沪深 A 股及港股；北交所请使用 CSV。')
        endpoint='hkfqkline' if market=='HK' else 'fqkline'
        url='https://web.ifzq.gtimg.cn/appstock/app/'+endpoint+'/get?'+urlencode({'param':remote+',day,,,640,qfq'})
        try:
            req=Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':'https://gu.qq.com/'})
            with urlopen(req,timeout=18) as response:
                payload=response.read(3_000_001)
            if len(payload)>3_000_000: raise ValueError('远端响应超过限制。')
            obj=json.loads(payload); info=obj['data'][remote]
            bars=info.get('qfqday')
            if not bars:
                # Some replies contain only `day`; keep the provider's values
                # but record the affected symbols because adjustment is unverified.
                bars=info.get('day')
                if bars: fallback.append(symbol)
            if not bars: raise ValueError('日线为空。')
            name,sector=meta.get(symbol,(symbol,'未分类'))
            for b in bars:
                # Only consume a same-day bar after 17:00 China time. The feed
                # controls whether a bar exists on holidays / shortened sessions.
                if b[0]>today or (b[0]==today and now.hour<17): continue
                op,cl,hi,lo,vol=map(float,b[1:6])
                if vol<=0: continue
                rows.append([b[0],symbol,name,market,sector,op,hi,lo,cl,vol])
        except (URLError,TimeoutError,OSError,ValueError,KeyError,TypeError,IndexError) as e:
            raise ValueError(f'{symbol} 在线行情获取失败：{str(e)[:180]}。未替换原有数据，可稍后重试或导入 CSV。') from e
        if i<len(symbols)-1:time.sleep(.2)
    frame=pd.DataFrame(rows,columns=['date','symbol','name','market','sector','open','high','low','close','volume'])
    # Volume stays in provider-native units; same ticker uses a consistent unit.
    checked=validate_csv(frame.to_csv(index=False),market)
    checked.attrs['source_details']={'provider':'Tencent public daily endpoint','requested_adjustment':'qfq','day_fallback_symbols':fallback,'fetched_at':now.isoformat(timespec='seconds'),'note':'北京时间17:00后才采用当天日线；源站 day 字段复权状态未核验，成交量为源站单位。'}
    return checked
