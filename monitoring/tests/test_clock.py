import unittest
from unittest.mock import patch

from anfa_observability.clock import prometheus_measure


class Response:
    def __init__(self,payload):self.payload=payload
    def __enter__(self):return self
    def __exit__(self,*_):pass
    def read(self):return self.payload


class ClockTests(unittest.TestCase):
    @patch("anfa_observability.clock.urllib.request.urlopen")
    def test_accepts_prometheus_scalar(self,open_mock):
        open_mock.return_value=Response(b'{"data":{"resultType":"scalar","result":[1,"1000.0"]}}')
        result=prometheus_measure("http://example",attempts=1)
        self.assertEqual(result["best"]["remote_epoch_ns"],1_000_000_000_000)


if __name__=="__main__":unittest.main()
