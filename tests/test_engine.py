import copy
import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import engine

class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df=engine.demo_data('CN')
        cls.base=engine.analyze(cls.df)

    def test_future_prices_cannot_change_fitted_weights(self):
        df=self.df.copy(); future=df.date>self.base['trainEnd']
        df.loc[future,['open','high','low','close']]*=1.5
        other=engine.analyze(df)
        np.testing.assert_allclose([f['weight'] for f in self.base['factors']],[f['weight'] for f in other['factors']],rtol=1e-10,atol=1e-12)

    def test_cost_increase_reduces_net_return(self):
        dear=engine.analyze(self.df,cost_bps=100)
        self.assertLess(dear['backtest']['return'],self.base['backtest']['return'])
        np.testing.assert_allclose([t['gross'] for t in dear['backtest']['trades']],[t['gross'] for t in self.base['backtest']['trades']])

    def test_trading_is_lagged_and_nonoverlapping(self):
        trades=self.base['backtest']['trades']
        for i,t in enumerate(trades):
            self.assertLess(t['signal'],t['entry']);self.assertLess(t['entry'],t['exit'])
            if i:self.assertGreaterEqual(t['entry'],trades[i-1]['exit'])

    def test_expression_parser_rejects_code_and_future_refs(self):
        for e in ['__import__("os").system("whoami")','Ref($close,-5)','Ref($close,0d)','CSRank($close)','[$close][0]','Add($close,True)']:
            with self.subTest(e=e),self.assertRaises(ValueError):engine.Formula(e)

    def test_ref_lag_and_safe_formula(self):
        f={'close':self.df.pivot(index='date',columns='symbol',values='close')}
        np.testing.assert_allclose(engine.Formula('Div($close,Ref($close,5d))').run(f).to_numpy()[5:],(f['close']/f['close'].shift(5)).to_numpy()[5:])

    def test_pool_weights_preserved_and_cutoff_enforced(self):
        pool={'exprs':engine.BUILTIN['exprs'][:2],'weights':[.4,-.8],'market':'CN','trained_until':'2025-01-01'}
        out=engine.analyze(self.df,pool=pool)
        self.assertTrue(out['poolImported']);self.assertEqual([f['weight'] for f in out['factors']],[.4,-.8])
        for key,value in [('trained_until','2026-10-01'),('market','HK'),('weights',[0,0])]:
            bad=copy.deepcopy(pool);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):engine.analyze(self.df,pool=bad)

    def test_csv_roundtrip_and_rejections(self):
        text=self.df.to_csv(index=False);df=engine.validate_csv(text,'CN')
        self.assertEqual(df.symbol.nunique(),12);self.assertIn('000625',df.symbol.unique())
        for bad in [self.df.iloc[:20],self.df.assign(volume=0),self.df.assign(high=0),self.df.assign(date='2099-01-01')]:
            with self.assertRaises(ValueError):engine.validate_csv(bad.to_csv(index=False),'CN')
        import pandas as pd
        with self.assertRaises(ValueError):engine.validate_csv(pd.concat([self.df,self.df.iloc[:1]]).to_csv(index=False),'CN')

    def test_hk_and_horizons_have_finite_output(self):
        import json
        for h in [1,5,10,20]:
            out=engine.analyze(engine.demo_data('HK'),'HK',h)
            self.assertEqual(out['currency'],'HKD');self.assertEqual(len(out['instruments']),10)
            self.assertTrue(out['backtest']['trades']);json.dumps(engine.clean_json(out),allow_nan=False)

if __name__=='__main__':unittest.main()
