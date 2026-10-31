"""Independent, causal factor research engine; reads AlphaGen JSON artifacts.

No upstream AlphaGen code or pretrained weights are bundled.
"""
from __future__ import annotations
import ast
import io
import re
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd

VERSION = '1.0.0'
STOCKS = {
    'CN': [('600519','贵州茅台',1680,'消费'),('000625','长安汽车',14,'汽车'),('300750','宁德时代',235,'新能源'),('600036','招商银行',36,'金融'),('601318','中国平安',48,'金融'),('000333','美的集团',65,'家电'),('002594','比亚迪',260,'汽车'),('600900','长江电力',27,'公用事业'),('601012','隆基绿能',20,'新能源'),('002415','海康威视',30,'科技'),('688981','中芯国际',55,'半导体'),('600030','中信证券',24,'金融')],
    'HK': [('00700','腾讯控股',400,'互联网'),('09988','阿里巴巴',90,'互联网'),('03690','美团',130,'互联网'),('01810','小米集团',22,'科技'),('00941','中国移动',72,'通信'),('00939','建设银行',6,'金融'),('02318','中国平安',40,'金融'),('01211','比亚迪股份',230,'汽车'),('09618','京东集团',120,'互联网'),('00388','香港交易所',290,'金融')]
}
BUILTIN = {
    'exprs': ['Sub(Div($close,Ref($close,20d)),1.0)', 'Sub(Div($close,Mean($close,60d)),1.0)', 'Sub(1.0,Div($close,Ref($close,5d)))', 'Div(Std($close,20d),Mean($close,20d))', 'Div($volume,Mean($volume,20d))', 'Div(Sub($close,$open),Sub($high,$low))'],
    'names': ['20日动量','60日趋势偏离','5日反转','相对波动率','量能变化','日内强弱'],
}
FIELDS = ['open','high','low','close','volume']
OPS = {'Abs':1,'Sign':1,'Log':1,'Add':2,'Sub':2,'Mul':2,'Div':2,'Pow':2,'Greater':2,'Less':2,'Ref':2,'Delta':2,'Mean':2,'Sum':2,'Std':2,'Var':2,'Max':2,'Min':2,'Med':2,'Mad':2,'Corr':3,'Cov':3}

def demo_data(market):
    rng = np.random.default_rng(42 if market == 'CN' else 77)
    dates = pd.bdate_range(end='2026-10-23', periods=620)
    common = rng.normal(.00015,.008,len(dates))
    rows = []
    for i,(symbol,name,base,sector) in enumerate(STOCKS[market]):
        noise = rng.normal(0,.013+(i%3)*.003,len(dates))
        ret = .00012 + common*(.65+i*.035)+noise
        close = base*np.exp(np.cumsum(ret))
        op = np.r_[close[0],close[:-1]]*np.exp(rng.normal(0,.003,len(dates)))
        high = np.maximum(op,close)*(1+rng.uniform(.001,.017,len(dates)))
        low = np.minimum(op,close)*(1-rng.uniform(.001,.017,len(dates)))
        volume = rng.lognormal(16, .4, len(dates))
        for j,d in enumerate(dates):
            rows.append([d.strftime('%Y-%m-%d'),symbol,name,market,sector,op[j],high[j],low[j],close[j],volume[j]])
    return pd.DataFrame(rows, columns=['date','symbol','name','market','sector']+FIELDS)

def validate_csv(text, market):
    """Parse and reject malformed OHLCV before replacing any saved dataset.

    Symbols are strings so leading zeroes survive CSV import. Dates remain
    canonical ISO strings after validation, allowing lexical time ordering.
    """
    try:
        df = pd.read_csv(io.StringIO(text.lstrip('\ufeff')), dtype={'symbol':str})
    except Exception as e:
        raise ValueError('CSV 读取失败，请使用 UTF-8 编码和英文列名。') from e
    required = {'date','symbol',*FIELDS}
    if not required.issubset(df.columns):
        raise ValueError('缺少列：'+', '.join(sorted(required-set(df.columns))))
    if len(df)>100000 or len(df)<540:
        raise ValueError('每次导入 540～100000 行，至少 3 只股票、每只至少 180 根日线。')
    if 'market' in df and not df.market.eq(market).all():
        raise ValueError('market 列必须全部与当前市场一致，A 股与港股请分别导入。')
    pattern = r'\d{6}' if market == 'CN' else r'\d{5}'
    if not df.symbol.str.fullmatch(pattern).all():
        raise ValueError('A 股代码为 6 位、港股代码为 5 位；保留前导零，不带交易所后缀。')
    df['date'] = pd.to_datetime(df.date, format='%Y-%m-%d', errors='coerce')
    today = pd.Timestamp(datetime.now(timezone(timedelta(hours=8))).date())
    if df.date.isna().any() or (df.date>today).any():
        raise ValueError('日期无效或晚于北京时间今天。')
    if df.duplicated(['date','symbol']).any():
        raise ValueError('存在重复的股票 / 日期记录，请去重后再导入。')
    for col in FIELDS:
        df[col] = pd.to_numeric(df[col],errors='coerce')
    if not np.isfinite(df[FIELDS].to_numpy()).all():
        raise ValueError('OHLCV 存在缺失值或非有限数字。')
    if (df[FIELDS[:4]]<=0).any().any() or (df.volume<=0).any():
        raise ValueError('价格和成交量必须为正数；停牌日请剔除。')
    if ((df.high < df[['open','close','low']].max(axis=1)) | (df.low > df[['open','close','high']].min(axis=1))).any():
        raise ValueError('最高价 / 最低价与开盘价、收盘价不一致。')
    counts = df.groupby('symbol').size()
    if len(counts)<3 or len(counts)>100 or counts.min()<180:
        raise ValueError('需要 3～100 只股票，每只至少 180 根日线。')
    for col in ['name','sector']:
        if col not in df: df[col] = df.symbol if col=='name' else '未分类'
        df[col] = df[col].fillna('未分类').astype(str).str.slice(0,40)
        if df.groupby('symbol')[col].nunique().max()>1:
            raise ValueError(f'同一股票的 {col} 必须一致。')
    df['market'] = market
    df['date'] = df.date.dt.strftime('%Y-%m-%d')
    return df.sort_values(['date','symbol']).reset_index(drop=True)

class Formula:
    """Interpret a bounded AlphaGen-style subset without executing Python code.

    Expressions can only access the explicitly allowed OHLCV fields and
    operators. Positive Ref/Delta lags prevent formulas from reading future
    rows. This standalone implementation is not a bit-exact Qlib evaluator.
    """
    def __init__(self, expression):
        if not isinstance(expression,str) or len(expression)>2000: raise ValueError('因子公式过长或类型错误。')
        s = re.sub(r'\$(\w+)',r'F_\1',expression)
        s = re.sub(r'\b(\d+)d\b',r'\1',s)
        try: self.tree=ast.parse(s,mode='eval').body
        except SyntaxError as e: raise ValueError('因子公式语法无效。') from e
        if len(list(ast.walk(self.tree)))>180: raise ValueError('因子公式过于复杂。')
        self.check(self.tree)

    def check(self,node):
        if isinstance(node,ast.Constant) and type(node.value) in (int,float) and np.isfinite(node.value) and abs(node.value)<=1e8: return
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
            if not isinstance(node.operand,ast.Constant): raise ValueError('一元符号仅用于数值常量。')
            self.check(node.operand); return
        if isinstance(node,ast.Name) and node.id in ['F_'+x for x in FIELDS]: return
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in OPS and not node.keywords:
            name=node.func.id
            if len(node.args)!=OPS[name]: raise ValueError(f'{name} 参数数量错误。')
            if name in {'Ref','Delta','Mean','Sum','Std','Var','Max','Min','Med','Mad','Corr','Cov'}:
                lag=node.args[-1]
                if not isinstance(lag,ast.Constant) or type(lag.value)!=int or not 1<=lag.value<=120:
                    raise ValueError('窗口 / 滞后仅支持 1～120 的正整数，禁止前视引用。')
            for x in node.args: self.check(x)
            return
        raise ValueError('不支持的公式。可用字段：$open/$high/$low/$close/$volume；算子：'+', '.join(OPS))

    def run(self, fields):
        template=fields['close']
        def ev(n):
            if isinstance(n,ast.Constant): return n.value
            if isinstance(n,ast.UnaryOp): return (-1 if isinstance(n.op,ast.USub) else 1)*ev(n.operand)
            if isinstance(n,ast.Name): return fields[n.id[2:]]
            name=n.func.id; a=[ev(x) for x in n.args]; x=a[0]
            if name=='Abs': return abs(x)
            if name=='Sign': return np.sign(x)
            if name=='Log': return np.log(x)
            if name=='Add': return x+a[1]
            if name=='Sub': return x-a[1]
            if name=='Mul': return x*a[1]
            if name=='Div': return x/a[1]
            if name=='Pow': return x**a[1]
            if name=='Greater': return np.maximum(x,a[1])
            if name=='Less': return np.minimum(x,a[1])
            if np.isscalar(x): x=pd.DataFrame(x,index=template.index,columns=template.columns)
            lag=a[-1]
            if name=='Ref': return x.shift(lag)
            if name=='Delta': return x-x.shift(lag)
            if name in ['Corr','Cov']:
                y=a[1]
                if np.isscalar(y): y=pd.DataFrame(y,index=template.index,columns=template.columns)
                return getattr(x.rolling(lag),'corr' if name=='Corr' else 'cov')(y)
            roll=x.rolling(lag)
            if name=='Mad': return roll.apply(lambda v: abs(v-v.mean()).mean(),raw=True)
            return getattr(roll,{'Mean':'mean','Sum':'sum','Std':'std','Var':'var','Max':'max','Min':'min','Med':'median'}[name])()
        with np.errstate(all='ignore'): result=ev(self.tree)
        if np.isscalar(result): raise ValueError('因子必须含行情字段。')
        return result.replace([np.inf,-np.inf],np.nan)

def validate_pool(pool, market, train_end):
    if not isinstance(pool,dict): raise ValueError('因子池必须为 JSON 对象。')
    exprs=pool.get('exprs'); weights=pool.get('weights')
    if not isinstance(exprs,list) or not 1<=len(exprs)<=20: raise ValueError('因子池需要 1～20 个 exprs。')
    if not isinstance(weights,list) or len(weights)!=len(exprs): raise ValueError('weights 与 exprs 长度必须一致。')
    if any(type(w) not in (int,float) or not np.isfinite(w) or abs(w)>1e6 for w in weights) or sum(abs(w) for w in weights)==0:
        raise ValueError('因子权重必须是有效数字，且不能全部为零。')
    if pool.get('market')!=market: raise ValueError('因子池 market 必须为当前市场 CN 或 HK。')
    try: trained = datetime.strptime(pool['trained_until'],'%Y-%m-%d').date()
    except (ValueError,KeyError,TypeError) as e: raise ValueError('需提供因子挖掘数据截止日 trained_until，避免测试集泄漏。') from e
    if trained>datetime.strptime(train_end,'%Y-%m-%d').date():
        raise ValueError(f'因子挖掘截止日不能晚于本数据训练截止日 {train_end}。')
    for expr in exprs: Formula(expr)
    return {k:pool[k] for k in ['exprs','weights','market','trained_until']}

def zscore(frame):
    # A row is one date, columns are stocks: normalize cross-sectionally, not
    # across time. A constant cross-section maps to zero rather than infinity.
    mean=frame.mean(axis=1); std=frame.std(axis=1,ddof=0)
    return frame.sub(mean,axis=0).div(std.where(std>1e-12,1),axis=0).clip(-8,8)

def safe_corr(x,y):
    ok=np.isfinite(x)&np.isfinite(y)
    if ok.sum()<3 or np.std(x[ok])<1e-12 or np.std(y[ok])<1e-12: return None
    return float(np.corrcoef(x[ok],y[ok])[0,1])

def analyze(df, market='CN', horizon=5, topk=3, cost_bps=15, pool=None, source='demo'):
    """Fit on early dates and assess the later, untouched date ranges.

    A signal at close[t] predicts open[t+h+1] / open[t+1] - 1. Arrays use
    [date, stock, factor] order. Imported pools supply ranking weights, while
    their score-to-return calibration is fitted using the training slice only.
    """
    if market not in STOCKS: raise ValueError('市场参数错误。')
    if horizon not in (1,5,10,20): raise ValueError('预测周期仅支持 1 / 5 / 10 / 20 个交易日。')
    if type(topk)!=int or not 1<=topk<=20: raise ValueError('持仓数应为 1～20。')
    if not np.isfinite(cost_bps) or not 0<=cost_bps<=200: raise ValueError('单边综合成本应在 0～200 bps。')
    fields={x:df.pivot(index='date',columns='symbol',values=x).sort_index() for x in FIELDS}
    # Require the entire universe to have OHLCV for a date; never carry a
    # suspended/missing stock's old price forward into a new trading day.
    keep=np.logical_and.reduce([v.notna().all(axis=1).to_numpy() for v in fields.values()])
    original=len(keep); fields={k:v.loc[keep] for k,v in fields.items()}
    close=fields['close']; dates=list(close.index); n=len(dates)
    if n<180: raise ValueError('对齐后不足 180 个共同交易日，请补充数据。')
    cut=int(n*.6); vcut=int(n*.8); train_end=dates[cut-1]
    if pool: pool=validate_pool(pool,market,train_end)
    exprs=pool['exprs'] if pool else BUILTIN['exprs']
    raw=[Formula(e).run(fields) for e in exprs]
    normalized=[zscore(x) for x in raw]
    x=np.stack([v.to_numpy() for v in normalized],axis=2)
    valid=np.isfinite(x).all(axis=2)
    # Signal after t close; enter at t+1 open, exit t+h+1 open.
    target=(fields['open'].shift(-horizon-1)/fields['open'].shift(-1)-1).to_numpy()
    day=np.arange(n)[:,None]*np.ones((1,len(close.columns)),dtype=int)
    # Purge labels crossing split boundaries: their exits would otherwise leak
    # validation or test prices into model fitting / validation.
    train=valid&np.isfinite(target)&(day+horizon+1<cut)
    val=valid&np.isfinite(target)&(day>=cut)&(day+horizon+1<vcut)
    test=valid&np.isfinite(target)&(day>=vcut)
    if train.sum()<100 or test.sum()<20: raise ValueError('有效因子或样本数量不足，请缩短窗口或补充数据。')
    if pool:
        weights=np.array(pool['weights'],dtype=float)
        # Artifact scores are not probabilities. Calibration is fit on training only.
        train_score=x[train]@weights
        design=np.c_[np.ones(len(train_score)),train_score]
        beta=np.linalg.lstsq(design,target[train],rcond=None)[0]
        pred=beta[0]+(x@weights)*beta[1]
        contributions=x[-1]*weights*beta[1]
        ranking=x@weights
        engine='AlphaGen 因子池 · 本地兼容评估'
    else:
        design=np.c_[np.ones(train.sum()),x[train]]
        penalty=np.eye(design.shape[1])*10; penalty[0,0]=0
        beta=np.linalg.solve(design.T@design+penalty,design.T@target[train])
        pred=beta[0]+x@beta[1:]; ranking=pred
        weights=beta[1:]; contributions=x[-1]*weights
        engine='内置因子 · Ridge 基线'
    if not valid[-1].all(): raise ValueError('最新日期存在无效因子值，请检查公式或行情。')
    rmse=float(np.sqrt(np.mean((pred[val]-target[val])**2))) if val.any() else None
    metrics={}
    for key,mask in [('validation',val),('test',test)]:
        metrics[key]={'samples':int(mask.sum()),'rmse':float(np.sqrt(np.mean((pred[mask]-target[mask])**2))) if mask.any() else None,
            'direction':float(np.mean((pred[mask]>0)==(target[mask]>0))) if mask.any() else None}
    ics=[]; factor_ics=[[] for _ in exprs]
    for i in range(vcut,n-horizon-1):
        ic=safe_corr(ranking[i],target[i])
        if ic is not None: ics.append({'date':dates[i],'ic':ic})
        for j in range(len(exprs)):
            fic=safe_corr(x[i,:,j],target[i])
            if fic is not None: factor_ics[j].append(fic)
    # Non-overlapping, fully liquidated equal-weight baskets; costs paid both
    # sides. The curve is sampled at exits, so intra-period drawdown is unknown.
    nav=bench=1.; equity=[{'date':dates[vcut],'nav':1.,'benchmark':1.}]; trades=[]
    k=min(topk,len(close.columns))
    for i in range(vcut,n-horizon-1,horizon):
        available=np.flatnonzero(valid[i]&np.isfinite(target[i]))
        if len(available)<k: continue
        chosen=available[np.argsort(ranking[i,available])[-k:]]
        gross=float(target[i,chosen].mean()); fee=cost_bps/10000
        net=(1+gross)*(1-fee)/(1+fee)-1
        bret=float(target[i,available].mean())
        nav*=1+net; bench*=1+bret
        equity.append({'date':dates[i+horizon+1],'nav':nav,'benchmark':bench})
        trades.append({'signal':dates[i],'entry':dates[i+1],'exit':dates[i+horizon+1], 'symbols':', '.join(close.columns[chosen]),'gross':gross,'net':net})
    values=np.array([r['nav'] for r in equity]); dd=values/np.maximum.accumulate(values)-1
    period_returns=np.array([t['net'] for t in trades]); ann=252/horizon
    sharpe=float(period_returns.mean()/period_returns.std(ddof=1)*np.sqrt(ann)) if len(period_returns)>1 and period_returns.std()>1e-12 else None
    instruments=[]
    meta=df.groupby('symbol').first()
    for j,symbol in enumerate(close.columns):
        series=close[symbol]; bars=[]
        ma20=series.rolling(20).mean(); ma60=series.rolling(60).mean()
        for i,d in enumerate(dates):
            bars.append({'date':d,**{col:float(fields[col].loc[d,symbol]) for col in FIELDS},'ma20':float(ma20.iloc[i]) if pd.notna(ma20.iloc[i]) else None,'ma60':float(ma60.iloc[i]) if pd.notna(ma60.iloc[i]) else None})
        instruments.append({'symbol':symbol,'name':str(meta.loc[symbol,'name']),'sector':str(meta.loc[symbol,'sector']), 'close':float(series.iloc[-1]), 'change':float(series.iloc[-1]/series.iloc[-2]-1),'prediction':float(pred[-1,j]),'score':float(ranking[-1,j]),'contributions':[float(c) for c in contributions[j]],'bars':bars})
    instruments.sort(key=lambda r:r['score'],reverse=True)
    for i,r in enumerate(instruments): r['rank']=i+1
    factors=[{'id':f'ALPHA_{j+1:03d}','name':('上游因子 '+str(j+1)) if pool else BUILTIN['names'][j], 'expr':e,'weight':float(weights[j]),'ic':float(np.mean(factor_ics[j])) if factor_ics[j] else None} for j,e in enumerate(exprs)]
    corr=np.corrcoef(x[test].T) if len(exprs)>1 else np.ones((1,1))
    return {'version':VERSION,'market':market,'source':source,'sourceDetails':df.attrs.get('source_details',{}),'asof':dates[-1],'engine':engine,'poolImported':bool(pool),'horizon':horizon,'topk':k,'costBps':cost_bps,'trainEnd':train_end,'trainLabelEnd':dates[cut-1],'validationStart':dates[cut],'testStart':dates[vcut], 'rows':len(df),'days':n,'alignmentDropped':original-n,'currency':'CNY' if market=='CN' else 'HKD','instruments':instruments,'factors':factors,'correlation':corr.tolist(),'ics':ics,'metrics':metrics,'backtest':{'equity':equity,'trades':trades,'return':nav-1,'benchmarkReturn':bench-1,'maxDrawdown':float(dd.min()),'sharpe':sharpe},'rmse':rmse,'pool':pool}

def clean_json(value):
    if isinstance(value,dict): return {k:clean_json(v) for k,v in value.items()}
    if isinstance(value,list): return [clean_json(v) for v in value]
    if isinstance(value,(float,np.floating)): return float(value) if np.isfinite(value) else None
    if isinstance(value,np.integer): return int(value)
    return value
