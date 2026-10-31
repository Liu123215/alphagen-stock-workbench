"""Run: python app.py [--port 8765] [--no-browser]. Local loopback server."""
import argparse
import json
import logging
import os
from pathlib import Path
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
import engine
import market_data

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; DATA.mkdir(exist_ok=True)
LOCK=threading.RLock()
CACHE={}

def load(market):
    path=DATA/(market+'.csv')
    if path.exists():
        meta=DATA/(market+'_source.json')
        info=json.loads(meta.read_text(encoding='utf-8')) if meta.exists() else {'source':'csv'}
        frame=engine.validate_csv(path.read_text(encoding='utf-8-sig'),market)
        frame.attrs['source_details']=info.get('details',{})
        return frame,info.get('source','csv')
    return engine.demo_data(market),'demo'

def pool_for(market):
    p=DATA/(market+'_pool.json')
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None

def atomic(path,text):
    tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(text,encoding='utf-8'); os.replace(tmp,path)

def result(body):
    market=body.get('market','CN')
    if market not in ('CN','HK'): raise ValueError('市场必须是 CN 或 HK。')
    horizon=body.get('horizon',5); topk=body.get('topk',3); cost=body.get('cost',15)
    if type(horizon)!=int or type(topk)!=int or type(cost) not in (int,float): raise ValueError('参数类型错误。')
    key=(market,horizon,topk,cost)
    with LOCK:
        if key not in CACHE:
            df,source=load(market)
            CACHE[key]=engine.clean_json(engine.analyze(df,market,horizon,topk,cost,pool_for(market),source))
        return CACHE[key]

class Handler(BaseHTTPRequestHandler):
    def respond(self,status,data,kind='application/json; charset=utf-8'):
        payload=json.dumps(data,ensure_ascii=False,allow_nan=False).encode() if kind.startswith('application/json') else data
        self.send_response(status)
        self.send_header('Content-Type',kind); self.send_header('Content-Length',str(len(payload)))
        self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Cache-Control','no-store')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers(); self.wfile.write(payload)

    def local(self):
        allowed={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
        return self.headers.get('Host') in allowed

    def do_GET(self):
        if not self.local(): return self.respond(403,{'error':'只接受本机访问。'})
        path=urlparse(self.path).path
        if path=='/api/health': return self.respond(200,{'ok':True,'version':engine.VERSION})
        files={'/':('index.html','text/html; charset=utf-8'),'/style.css':('style.css','text/css; charset=utf-8'),'/app.js':('app.js','application/javascript; charset=utf-8')}
        if path not in files: return self.respond(404,{'error':'资源不存在。'})
        name,kind=files[path]; self.respond(200,(ROOT/'static'/name).read_bytes(),kind)

    def do_POST(self):
        if not self.local(): return self.respond(403,{'error':'只接受本机访问。'})
        origin=self.headers.get('Origin')
        if origin and origin not in [f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}']:
            return self.respond(403,{'error':'拒绝跨站请求。'})
        if self.headers.get('Content-Type','').split(';')[0]!='application/json': return self.respond(415,{'error':'需要 JSON 请求。'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<1 or length>12_000_000: return self.respond(413,{'error':'请求应小于 12MB。'})
            body=json.loads(self.rfile.read(length))
            if not isinstance(body,dict): raise ValueError('请求必须是 JSON 对象。')
            path=urlparse(self.path).path; market=body.get('market','CN')
            if market not in ('CN','HK'): raise ValueError('市场参数错误。')
            if path=='/api/analyze': return self.respond(200,result(body))
            if path=='/api/sync':
                frame=market_data.fetch_daily(market,body.get('symbols'))
                with LOCK:
                    engine.analyze(frame,market,pool=pool_for(market),source='tencent')
                    atomic(DATA/(market+'.csv'),frame.to_csv(index=False))
                    atomic(DATA/(market+'_source.json'),json.dumps({'source':'tencent','details':frame.attrs.get('source_details',{})}))
                    CACHE.clear()
                return self.respond(200,{'ok':True,'rows':len(frame)})
            with LOCK:
                if path=='/api/data':
                    text=body.get('csv')
                    if not isinstance(text,str): raise ValueError('CSV 内容必须是文本。')
                    frame=engine.validate_csv(text,market)
                    # Analyze before commit, preserving existing dataset on all failures.
                    engine.analyze(frame,market,pool=pool_for(market),source='csv')
                    atomic(DATA/(market+'.csv'),frame.to_csv(index=False))
                    atomic(DATA/(market+'_source.json'),json.dumps({'source':'csv'})); CACHE.clear()
                elif path=='/api/pool':
                    df,source=load(market)
                    checked=engine.analyze(df,market,pool=body.get('pool'),source=source)
                    if not checked['pool']: raise ValueError('未提供因子池。')
                    atomic(DATA/(market+'_pool.json'),json.dumps(checked['pool'],ensure_ascii=False)); CACHE.clear()
                elif path=='/api/reset':
                    for p in [DATA/(market+'.csv'),DATA/(market+'_pool.json'),DATA/(market+'_source.json')]: p.unlink(missing_ok=True)
                    CACHE.clear()
                elif path=='/api/reset-pool':
                    (DATA/(market+'_pool.json')).unlink(missing_ok=True); CACHE.clear()
                else: return self.respond(404,{'error':'接口不存在。'})
            self.respond(200,{'ok':True})
        except (ValueError,TypeError,KeyError,OverflowError) as e:
            self.respond(400,{'error':str(e)[:1200]})
        except Exception:
            logging.exception('Request failed')
            self.respond(500,{'error':'计算失败，详情请查看启动窗口日志；原有数据保留。'})

def main():
    parser=argparse.ArgumentParser(description='AlphaGen A/H Research Workbench')
    parser.add_argument('--port',type=int,default=8765); parser.add_argument('--no-browser',action='store_true')
    args=parser.parse_args(); server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    url=f'http://127.0.0.1:{args.port}'; print('AlphaGen Workbench '+url,flush=True)
    if not args.no_browser: threading.Timer(.8,lambda:webbrowser.open(url)).start()
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=='__main__': main()
