import json
from pathlib import Path
import tempfile
import sqlite3
import subprocess
import sys
import unittest
from audit_traces import audit, epoch, usage_delta

class AuditTests(unittest.TestCase):
    def test_explicit_timezone_and_window(self):
        with self.assertRaises(ValueError): epoch('2026-10-01T00:00:00')
        process=subprocess.run([sys.executable,str(Path(__file__).with_name('audit_traces.py')),'--since','2026-10-02T00:00:00Z','--until','2026-10-01T00:00:00Z'],capture_output=True,text=True)
        self.assertEqual(process.returncode,2)
        self.assertIn('--since must precede --until',process.stderr)

    def test_wrong_typed_rollout_fields_do_not_abort(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            folder = home / 'sessions'
            folder.mkdir()
            events = []
            for timestamp in (None, 123, [], {}):
                events.append({'timestamp': timestamp, 'type': 'event_msg',
                               'payload': {'type': 'valid_type'}})
            for subtype in (None, 123, [], {}):
                events.append({'timestamp': '2026-10-01T00:00:00Z', 'type': 'event_msg',
                               'payload': {'type': subtype}})
            for index, name in enumerate((None, 123, [], {'private-label': 'private-value'})):
                events.append({'timestamp': '2026-10-01T00:00:01Z', 'type': 'response_item',
                               'payload': {'type': 'function_call', 'call_id': str(index),
                                           'name': name, 'arguments': 'private-arguments'}})
            events.append({'timestamp': '2026-10-01T00:00:02Z', 'type': 'event_msg',
                           'payload': {'type': 'valid_type'}})
            (folder / 'malformed.jsonl').write_text(''.join(json.dumps(e) + '\n' for e in events))
            result = audit(home, 1790812800, 1790899200)
            self.assertEqual(result['counts']['invalid_timestamps'], 4)
            self.assertEqual(result['counts']['malformed_records'], 4)
            self.assertEqual(result['event_types'], {'valid_type': 1})
            self.assertEqual(result['tool_calls'], {'other': 4})
            self.assertNotIn('private-', json.dumps(result))

    def test_usage_rejects_unknown_and_invalid_fields(self):
        self.assertEqual(usage_delta({'input_tokens':'bad'}, {'input_tokens':7,'output_tokens':-1,'total_tokens':True,'private-token-label':123}), {'input_tokens':7})

    def test_counters_reset(self):
        self.assertEqual(usage_delta({'input_tokens':100},{'input_tokens':7,'output_tokens':2}),{'input_tokens':7,'output_tokens':2})

    def test_copies_window_privacy(self):
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory); folder=home/'sessions'; folder.mkdir()
            events=[{'timestamp':'2026-10-01T00:00:00Z','type':'turn_context','payload':{'turn_id':'private-turn'}}, {'timestamp':'2026-10-01T00:00:01Z','type':'response_item','payload':{'type':'function_call','call_id':'secret-call','name':'exec_command','arguments':'secret-token private-cwd'}}, {'timestamp':'2026-10-01T00:00:02Z','type':'response_item','payload':{'type':'function_call','call_id':'second-call','name':'exec_command','arguments':'secret-token private-cwd'}}, {'timestamp':'2025-01-01T00:00:00Z','type':'event_msg','payload':{'type':'outside'}}]
            for filename in ['a','b']: (folder/(filename+'.jsonl')).write_text(''.join(json.dumps(e)+'\n' for e in events))
            result=audit(home,1790812800,1790899200)
            self.assertEqual(result['tool_calls'],{'exec_command':2})
            self.assertEqual(result['counts']['duplicate_records_suppressed'],3)
            self.assertEqual(result['counts']['identical_call_candidates_within_turn'],1)
            rendered=json.dumps(result)
            for secret in ['secret-token','private-cwd','private-turn','secret-call']: self.assertNotIn(secret,rendered)
            self.assertNotIn('outside',result['event_types'])

    def test_owner_usage_and_malformed(self):
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory); folder=home/'sessions'; folder.mkdir()
            with sqlite3.connect(home/'thread_history_1.sqlite') as db:
                db.execute('create table thread_turns(thread_id,turn_id,status,started_at,duration_ms)')
                db.execute("insert into thread_turns values('owner','turn','completed',1790812800,1200)")
            events=[{'type':'session_meta','payload':{'id':'owner'}}, {'type':'turn_context','payload':{'turn_id':'turn'}}]
            for value in [100,130,5]:
                events.append({'type':'event_msg','payload':{'type':'token_count','info':{'total_token_usage':{'input_tokens':value}}}})
            for index,event in enumerate(events): event['timestamp']='2026-10-01T00:00:0%dZ'%index
            copied=json.loads(json.dumps(events)); copied[0]['payload']['id']='inherited-owner'
            (folder/'a.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in copied))
            (folder/'b.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events)+'invalid\n[]\n')
            result=audit(home,1790812800,1790899200)
            self.assertEqual(result['runtime_usage']['token_deltas'],{'input_tokens':35})
            self.assertEqual(result['projected_turns']['duration_ms_p50'],1200)
            self.assertEqual(result['counts']['invalid_json_lines'],1)
            self.assertEqual(result['counts']['malformed_records'],1)

if __name__=='__main__': unittest.main()
