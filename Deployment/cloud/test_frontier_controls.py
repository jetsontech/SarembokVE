from __future__ import annotations
import os
import unittest

from Deployment.cloud.production_guard_v2 import ProductionGuard, scrub, Identity, METHOD_REQUIREMENTS
from Deployment.cloud.orchestration_contract import ExecutionGraph, GraphNode, validate_graph, ready_nodes

class DummyWS:
    def __init__(self, origin='https://sarembok.com', peer=('127.0.0.1', 1234)):
        self.request_headers={'Origin':origin,'Host':'sarembok.com'}
        self.remote_address=peer

class FrontierControlTests(unittest.TestCase):
    def test_secret_scrubbing(self):
        payload={'apiKey':'sk-secret-value-123456789','nested':{'authorization':'Bearer abc','text':'sk-or-abcdefghijklmno'}}
        out=scrub(payload)
        self.assertEqual(out['apiKey'],'[REDACTED]')
        self.assertEqual(out['nested']['authorization'],'[REDACTED]')
        self.assertIn('[REDACTED]',out['nested']['text'])

    def test_unknown_method_fails_closed(self):
        guard=ProductionGuard()
        with self.assertRaises(PermissionError):
            guard.require('DefinitelyNotARealMethod',{},Identity('USER','u'))

    def test_user_cannot_execute_admin_method(self):
        guard=ProductionGuard()
        with self.assertRaises(PermissionError):
            guard.require('AdminExecuteDirective',{},Identity('USER','u'))

    def test_origin_allowlist(self):
        guard=ProductionGuard()
        self.assertTrue(guard.origin_allowed(DummyWS()))
        self.assertFalse(guard.origin_allowed(DummyWS('https://evil.example')))

    def test_rate_limit(self):
        old=os.environ.get('SAREMBOK_RATE_LIMIT_PER_IP')
        oldw=os.environ.get('SAREMBOK_RATE_LIMIT_WINDOW_SECONDS')
        os.environ['SAREMBOK_RATE_LIMIT_PER_IP']='1'; os.environ['SAREMBOK_RATE_LIMIT_WINDOW_SECONDS']='60'
        try:
            guard=ProductionGuard(); ws=DummyWS()
            guard.allow_ip(ws)
            with self.assertRaises(PermissionError): guard.allow_ip(ws)
        finally:
            if old is None: os.environ.pop('SAREMBOK_RATE_LIMIT_PER_IP',None)
            else: os.environ['SAREMBOK_RATE_LIMIT_PER_IP']=old
            if oldw is None: os.environ.pop('SAREMBOK_RATE_LIMIT_WINDOW_SECONDS',None)
            else: os.environ['SAREMBOK_RATE_LIMIT_WINDOW_SECONDS']=oldw

    def test_graph_cycle_rejected(self):
        graph=ExecutionGraph('g',(GraphNode('a','x',('b',)),GraphNode('b','y',('a',))))
        self.assertIn('dependency_cycle',validate_graph(graph))

    def test_graph_ready_nodes(self):
        graph=ExecutionGraph('g',(
            GraphNode('a','x',state='SUCCEEDED'),
            GraphNode('b','y',('a',),state='PENDING'),
            GraphNode('c','z',('b',),state='PENDING'),
        ))
        self.assertEqual(ready_nodes(graph),['b'])

if __name__ == '__main__':
    unittest.main()
