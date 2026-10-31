import json
import sys
from pathlib import Path
from unittest.mock import patch
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import market_data

class Response:
    def __init__(self,body):self.body=body
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,*args):return json.dumps(self.body).encode()

class MarketDataTests(unittest.TestCase):
    def fake(self,request,timeout):
        from urllib.parse import urlparse,parse_qs
        symbol=parse_qs(urlparse(request.full_url).query)['param'][0].split(',')[0]
        dates=__import__('pandas').bdate_range('2024-01-01',periods=200)
        bars=[[d.strftime('%Y-%m-%d'),'10','10.1','10.5','9.8','150000'] for d in dates]
        return Response({'data':{symbol:{'day':bars}}})

    @patch('market_data.time.sleep')
    def test_fallback_provenance_is_preserved(self,_):
        with patch('market_data.urlopen',side_effect=self.fake):
            frame=market_data.fetch_daily('HK',['00700','09988','03690'])
        self.assertEqual(len(frame),600)
        self.assertEqual(frame.attrs['source_details']['day_fallback_symbols'],['00700','09988','03690'])

    def test_limits_and_unsupported_codes(self):
        for market,symbols in [('CN',['000625']),('HK',['700','09988','03690']),('CN',['600519','600519','000625'])]:
            with self.subTest(symbols=symbols),self.assertRaises(ValueError):market_data.fetch_daily(market,symbols)

    def test_network_failure_is_explicit(self):
        with patch('market_data.urlopen',side_effect=TimeoutError('network timeout')):
            with self.assertRaisesRegex(ValueError,'未替换原有数据'):market_data.fetch_daily('CN',['600519','000625','300750'])

    @patch('market_data.time.sleep')
    def test_same_day_included_only_after_17(self,_):
        from datetime import datetime
        from urllib.parse import urlparse, parse_qs
        import pandas as pd
        def response(request,timeout):
            symbol=parse_qs(urlparse(request.full_url).query)['param'][0].split(',')[0]
            dates=pd.bdate_range(end='2024-10-08',periods=200)
            bars=[[d.strftime('%Y-%m-%d'),'10','10.1','10.5','9.8','150000'] for d in dates]
            return Response({'data':{symbol:{'qfqday':bars}}})
        for hour,expected in [(16,'2024-10-07'),(17,'2024-10-08')]:
            with self.subTest(hour=hour),patch('market_data.datetime') as clock,patch('market_data.urlopen',side_effect=response):
                clock.now.return_value=datetime(2024,10,8,hour)
                frame=market_data.fetch_daily('CN',['600519','000625','300750'])
                self.assertEqual(frame.date.max(),expected)

if __name__=='__main__':unittest.main()
