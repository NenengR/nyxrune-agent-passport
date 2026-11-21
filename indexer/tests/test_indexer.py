import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from passport.indexer import BASE, EVENTS, Rpc, aggregate, atomic_write, collect, validate_config

# Synthetic values exist only inside tests, never as a deploy config or chain evidence.
TEST_CONTRACT = '0x' + 'a' * 40
ACTOR_A = '0x' + '1' * 40
ACTOR_B = '0x' + '2' * 40
BLOCK_HASH = '0x' + 'f' * 64


def config():
    return {'contract_address': TEST_CONTRACT, 'chain_id': 56, 'deployment_block': 100,
            'confirmations': 2, 'block_chunk_size': 1, 'event_schema_verified': True,
            'events': {name: {'topic0': '0x' + str(i + 1) * 64,
                              **({'wallet': {'source': 'topics', 'index': 1}} if name != 'PollCreated' else {})}
                       for i, name in enumerate(EVENTS)}}


def log(name='CheckIn', block=100, index=0, actor=ACTOR_A):
    return {'address': TEST_CONTRACT, 'topics': [config()['events'][name]['topic0'], '0x' + '0' * 24 + actor[2:]],
            'data': '0x', 'blockNumber': hex(block), 'blockHash': BLOCK_HASH,
            'transactionIndex': '0x0', 'logIndex': hex(index), 'removed': False}


class FakeRpc:
    def __init__(self, logs=None):
        self.logs = logs if logs is not None else [log(), log('BadgeMinted', index=1), log('Voted', block=101, actor=ACTOR_B), log('PollCreated', block=101, index=1)]
        self.calls = []
        self.anchor_calls = 0
        self.reorg = False

    def call(self, method, params):
        self.calls.append((method, params))
        if method == 'eth_chainId': return '0x38'
        if method == 'eth_blockNumber': return hex(103)
        if method == 'eth_getCode': return '0x6000'
        if method == 'eth_getBlockByNumber':
            self.anchor_calls += int(int(params[0], 16) == 101)
            return {'timestamp': hex(1794960000 if int(params[0], 16) == 100 else 1795046400),
                    'hash': 'changed' if self.reorg and self.anchor_calls > 2 else BLOCK_HASH}
        if method == 'eth_getLogs':
            return [item for item in self.logs if int(params[0]['fromBlock'], 16) <= int(item['blockNumber'], 16) <= int(params[0]['toBlock'], 16)]
        raise AssertionError(method)


class IndexerTests(unittest.TestCase):
    def test_fixture_dedup_daily_and_unique(self):
        events = json.loads((BASE / 'fixtures/events.json').read_text())
        stats = aggregate(events, 'local-fixture')
        self.assertEqual(stats['totals'], {'unique_active_agent_addresses': 2, 'check_ins': 2, 'badges': 1, 'votes': 2, 'polls': 1})
        self.assertEqual([row['day'] for row in stats['daily']], ['2026-11-18', '2026-11-19'])
        self.assertEqual([row['check_ins'] for row in stats['daily']], [1, 1])
        self.assertEqual(stats['daily'][0]['unique_active_agent_addresses'], 2)
        self.assertEqual(stats['daily'][1]['unique_active_agent_addresses'], 2)
        self.assertTrue(stats['is_fixture'])
        self.assertNotIn(ACTOR_A, json.dumps(stats))
        self.assertEqual(stats['contract_address'], '0xd3a3e3a726881d2eed7e6e49331af16a7de52392')

    def test_case_insensitive_wallet(self):
        events = [{'id': 'a', 'event': 'CheckIn', 'wallet': TEST_CONTRACT.upper().replace('0X', '0x'), 'timestamp': 0},
                  {'id': 'b', 'event': 'Voted', 'wallet': TEST_CONTRACT, 'timestamp': 1}]
        self.assertEqual(aggregate(events, 'local-fixture')['totals']['unique_active_agent_addresses'], 1)

    def test_empty(self):
        stats = aggregate([], 'local-fixture')
        self.assertEqual(stats['daily'], [])
        self.assertTrue(all(value == 0 for value in stats['totals'].values()))

    def test_conflicting_duplicates_fail(self):
        a = {'id': 'a', 'event': 'CheckIn', 'wallet': ACTOR_A, 'timestamp': 0}
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            aggregate([a, dict(a, timestamp=1)], 'local-fixture')

    def test_bad_events_fail(self):
        for event in [{'id': 'a', 'event': 'Transfer', 'timestamp': 0},
                      {'id': 'a', 'event': 'CheckIn', 'wallet': 'bad', 'timestamp': 0},
                      {'id': 'a', 'event': 'PollCreated', 'timestamp': -1}]:
            with self.subTest(event=event), self.assertRaises(ValueError):
                aggregate([event], 'local-fixture')

    def test_placeholder_blocks_before_network_and_preserves_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'stats.json'
            output.write_text('old valid snapshot')
            cfg_path = Path(tmp) / 'indexer.json'
            cfg = json.loads((BASE / 'config/indexer.example.json').read_text())
            cfg['contract_address'] = 'CONTRACT_ADDRESS_TBD'
            cfg_path.write_text(json.dumps(cfg))
            process = subprocess.run([sys.executable, '-m', 'passport.indexer', '--rpc', '--config',
                                      str(cfg_path), '--output', str(output)],
                                     capture_output=True, text=True, cwd=BASE,
                                     env={**os.environ, 'RPC_URL': 'http://127.0.0.1:1'})
            self.assertEqual(process.returncode, 1)
            self.assertEqual(process.stderr.strip(), "ERROR: contract_address is CONTRACT_ADDRESS_TBD or invalid; wait for HAMID's verified address")
            self.assertEqual(output.read_text(), 'old valid snapshot')

    def test_abi_and_numeric_guards(self):
        for field, value in [('event_schema_verified', False), ('deployment_block', None), ('confirmations', 0), ('block_chunk_size', 0), ('chain_id', True)]:
            cfg = config()
            cfg[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): validate_config(cfg)
        cfg = config()
        cfg['events']['CheckIn']['wallet'] = None
        with self.assertRaises(ValueError): validate_config(cfg)

    def test_rpc_chunks_confirmations_all_events(self):
        rpc = FakeRpc()
        events, scan = collect(rpc, config())
        stats = aggregate(events, 'rpc', TEST_CONTRACT, scan)
        self.assertEqual(set(event['event'] for event in events), set(EVENTS))
        self.assertEqual(stats['totals']['unique_active_agent_addresses'], 2)
        self.assertEqual(scan['to_block'], 101)
        requests = [params[0] for method, params in rpc.calls if method == 'eth_getLogs']
        self.assertEqual([(r['fromBlock'], r['toBlock']) for r in requests], [('0x64', '0x64'), ('0x65', '0x65')])
        self.assertTrue(all(r['address'] == TEST_CONTRACT for r in requests))
        self.assertTrue(all(len(r['topics'][0]) == 4 for r in requests))

    def test_nonindexed_wallet(self):
        entry = log('Voted')
        entry['topics'] = entry['topics'][:1]
        entry['data'] = '0x' + '0' * 64 + '0' * 24 + ACTOR_B[2:]
        cfg = config()
        cfg['events']['Voted']['wallet'] = {'source': 'data', 'index': 1}
        events, _ = collect(FakeRpc([entry]), cfg)
        self.assertEqual(events[0]['wallet'], ACTOR_B)

    def test_corrupted_logs_rejected(self):
        for change in [{'address': ACTOR_B}, {'removed': True}, {'blockHash': 'wrong'}, {'topics': ['0x' + '9' * 64]}, {'topics': [config()['events']['CheckIn']['topic0']]}]:
            entry = log()
            entry.update(change)
            with self.subTest(change=change), self.assertRaises(ValueError): collect(FakeRpc([entry]), config())

    def test_reorg_rejected(self):
        rpc = FakeRpc()
        rpc.reorg = True
        with self.assertRaisesRegex(ValueError, 'Confirmed head changed'): collect(rpc, config())

    def test_wrong_chain_and_missing_code(self):
        for method, value, message in [('eth_chainId', '0x61', 'chain ID'), ('eth_getCode', '0x', 'No contract bytecode')]:
            rpc = FakeRpc()
            original = rpc.call
            rpc.call = lambda m, p: value if m == method else original(m, p)
            with self.subTest(method=method), self.assertRaisesRegex(ValueError, message): collect(rpc, config())

    def test_atomic_write_failure_preserves_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'stats.json'
            atomic_write(output, {'ok': True})
            with patch('passport.indexer.os.replace', side_effect=OSError('simulated write failure')):
                with self.assertRaises(OSError): atomic_write(output, {'ok': False})
            self.assertEqual(json.loads(output.read_text()), {'ok': True})
            self.assertEqual(len(list(Path(tmp).iterdir())), 1)

    def test_rpc_serialization_without_socket(self):
        fake = FakeRpc()
        requests = []
        def offline_urlopen(request, timeout):
            payload = json.loads(request.data)
            requests.append(payload)
            result = fake.call(payload['method'], payload['params'])
            self.assertEqual(timeout, 30)
            return io.BytesIO(json.dumps({'jsonrpc': '2.0', 'id': payload['id'], 'result': result}).encode())
        with patch('passport.indexer.urlopen', side_effect=offline_urlopen):
            rpc = Rpc('http://127.0.0.1:1')
            events, scan = collect(rpc, config())
        self.assertEqual(len(events), 4)
        self.assertEqual(scan['to_block'], 101)
        self.assertTrue(all(req['method'] in Rpc.ALLOWED for req in requests))
        self.assertEqual([req['id'] for req in requests], list(range(1, len(requests) + 1)))
        with self.assertRaisesRegex(ValueError, 'not read-only'):
            rpc.call('eth_sendTransaction', [])

    def test_rpc_errors(self):
        for payload in [{'id': 1, 'error': {'code': -1}}, {'id': 99, 'result': []}]:
            with patch('passport.indexer.urlopen', return_value=io.BytesIO(json.dumps(payload).encode())):
                with self.assertRaisesRegex(ValueError, 'invalid response'):
                    Rpc('http://127.0.0.1:1').call('eth_chainId', [])

    def test_readonly_rpc_http_transport(self):
        fake = FakeRpc()
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                result = fake.call(request['method'], request['params'])
                payload = json.dumps({'jsonrpc': '2.0', 'id': request['id'], 'result': result}).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(payload)
            def log_message(self, *args): pass
        try:
            server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        except PermissionError as exc:
            self.skipTest(f'Local socket unavailable: {exc}')
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            rpc = Rpc(f'http://127.0.0.1:{server.server_port}')
            events, _ = collect(rpc, config())
            self.assertEqual(len(events), 4)
            with self.assertRaisesRegex(ValueError, 'not read-only'): rpc.call('eth_sendTransaction', [])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
