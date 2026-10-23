#!/usr/bin/env python3
"""Read-only, aggregate-only local Codex audit. Never emits transcript text or IDs.

Counts are activity-window counts (since inclusive, until exclusive). Duplicate stable
turn/call events and exact timestamped event copies are suppressed across rollouts.
Repeated arguments and output error markers are diagnostic candidates, not judgments.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3


def epoch(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('timestamps require an explicit timezone')
    return parsed.timestamp()


def connection(path):
    return sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).digest()


USAGE_FIELDS = frozenset(('input_tokens', 'cached_input_tokens', 'cache_write_input_tokens',
                          'output_tokens', 'reasoning_output_tokens', 'total_tokens'))


def clean_usage(value):
    return {k: v for k, v in value.items() if k in USAGE_FIELDS
            and isinstance(v, int) and not isinstance(v, bool) and v >= 0}


def usage_delta(previous, current):
    """Cumulative counters reset after compaction/model switches; never subtract resets."""
    previous, current = clean_usage(previous), clean_usage(current)
    return {k: v - previous.get(k, 0) if v >= previous.get(k, 0) else v
            for k, v in current.items() if isinstance(v, int) and not isinstance(v, bool)}


def audit(home, since, until, excluded=()):
    capture_started = datetime.now(timezone.utc).isoformat()
    counts = Counter()
    tools = Counter()
    nested_tools = Counter()
    event_types = Counter()
    models = Counter()
    routes = Counter()
    seen = set()
    usage_seen = set()
    repeats = set()
    token_previous = {}
    tokens = Counter()
    paths = set((home / 'sessions').glob('**/*.jsonl'))
    paths.update((home / 'archived_sessions').glob('**/*.jsonl'))
    coverage = {}
    owners = {}
    excluded = set(excluded)
    state = home / 'state_5.sqlite'
    if state.exists():
        with connection(state) as db:
            rows = db.execute('select id,rollout_path,agent_role,model,created_at,updated_at from threads').fetchall()
            edges = db.execute('select parent_thread_id,child_thread_id from thread_spawn_edges').fetchall()
            while True:
                new = {c for p,c in edges if p in excluded} - excluded
                if not new: break
                excluded.update(new)
            for thread,path,role,model,created,updated in rows:
                paths.add(Path(path))
                if updated >= since and created < until and thread not in excluded:
                    counts['state_window_active_threads'] += 1
                    if role: routes[role if re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',role) else 'other'] += 1
                    if model: models[model if re.fullmatch(r'[a-zA-Z0-9_.-]{1,80}',model) else 'other'] += 1
            coverage['state_thread_timestamp_range'] = db.execute('select min(created_at),max(updated_at) from threads').fetchone()
    history = home / 'thread_history_1.sqlite'
    durations = []
    statuses = Counter()
    if history.exists():
        with connection(history) as db:
            coverage['history_turn_start_range_epoch'] = db.execute('select min(started_at),max(started_at) from thread_turns').fetchone()
            for thread,turn,status,start,duration in db.execute('select thread_id,turn_id,status,started_at,duration_ms from thread_turns'):
                owners.setdefault(turn,set()).add(thread)
                if start is not None and since <= start < until and thread not in excluded:
                    statuses[status] += 1
                    if duration is not None: durations.append(duration)
    logs = home / 'logs_2.sqlite'
    if logs.exists():
        with connection(logs) as db:
            coverage['diagnostic_retention_epoch'] = db.execute('select min(ts),max(ts) from logs').fetchone()
            coverage['diagnostic_window_rows_by_level'] = dict(db.execute('select level,count(*) from logs where ts>=? and ts<? group by level',(since,until)))
    low = None
    high = None
    for path in sorted(paths):
        if not path.is_file(): counts['missing_rollout_paths'] += 1; continue
        counts['existing_rollout_paths'] += 1
        owner = None
        turn = None
        last_poll = {}
        with path.open('rb') as stream:
            for line in stream:
                counts['bytes_scanned'] += len(line)
                try: record=json.loads(line)
                except (ValueError,UnicodeError): counts['invalid_json_lines'] += 1; continue
                if not isinstance(record,dict) or not isinstance(record.get('payload'),dict): counts['malformed_records'] += 1; continue
                payload=record['payload']; kind=record.get('type')
                if kind == 'session_meta': owner=payload.get('id'); turn=None
                if kind == 'turn_context': turn=payload.get('turn_id',turn)
                if kind == 'event_msg' and payload.get('type') == 'task_started': turn=payload.get('turn_id',turn)
                try: timestamp=epoch(record['timestamp'])
                except (ValueError,KeyError,TypeError): counts['invalid_timestamps'] += 1; continue
                low=timestamp if low is None else min(low,timestamp); high=timestamp if high is None else max(high,timestamp)
                if not since <= timestamp < until: continue
                if owner in excluded or owners.get(turn,set()) & excluded: counts['excluded_audit_records'] += 1; continue
                counts['window_records_before_dedup'] += 1
                stable=payload.get('call_id') or payload.get('id')
                key=digest([kind,payload.get('type'),stable,turn] if stable else [record.get('timestamp'),kind,payload])
                if kind == 'event_msg' and payload.get('type') == 'token_count':
                    info=payload.get('info'); current=info.get('total_token_usage') if isinstance(info,dict) else None
                    if isinstance(current,dict) and owner and turn and owners.get(turn)=={owner} and key not in usage_seen:
                        usage_seen.add(key)
                        # Last cumulative snapshot per owner is compared in file order.
                        previous=token_previous.get(owner,{})
                        if previous: tokens.update(usage_delta(previous,current)); counts['usage_delta_samples'] += 1
                        else: counts['usage_baselines_omitted'] += 1
                        token_previous[owner]=clean_usage(current)
                if key in seen: counts['duplicate_records_suppressed'] += 1; continue
                seen.add(key); counts['unique_window_records'] += 1
                if turn and owners.get(turn):
                    counts['owner_records' if owner in owners[turn] else 'inherited_records'] += 1
                else: counts['ownership_unresolved_records'] += 1
                if kind == 'compacted': counts['compaction_records'] += 1
                if kind == 'event_msg':
                    subtype=payload.get('type','unknown')
                    if re.fullmatch(r'[a-z_]{1,80}',subtype): event_types[subtype] += 1
                if kind != 'response_item': continue
                if payload.get('type') in ('function_call','custom_tool_call'):
                    name=payload.get('name','unknown')
                    if not re.fullmatch(r'[a-zA-Z0-9_.:-]{1,160}',name): name='other'
                    tools[name] += 1
                    args=payload.get('arguments',payload.get('input',''))
                    repeat=digest([turn,name,args])
                    if turn and repeat in repeats: counts['identical_call_candidates_within_turn'] += 1
                    repeats.add(repeat)
                    if re.search(r'(?:^|[._:])(wait|wait_agent|wait_threads|write_stdin|sleep)$',name):
                        counts['poll_or_wait_calls'] += 1
                        if turn in last_poll and timestamp-last_poll[turn]<10: counts['poll_or_wait_gap_under_10s'] += 1
                        last_poll[turn]=timestamp
                    if isinstance(args,str) and name in ('functions.exec', 'exec'):
                        nested_tools.update(re.findall(r'\btools\.([A-Za-z0-9_]+)\s*\(', args))
                    if isinstance(args,str) and re.search(r'(?:cat|sed|read_text|readFile|open).*?gpt-engineer/(?:SKILL\.md)',args,re.S): counts['skill_read_call_candidates'] += 1
                if payload.get('type') in ('function_call_output','custom_tool_call_output'):
                    output=payload.get('output','')
                    text=output if isinstance(output,str) else json.dumps(output)
                    if re.search(r'(?i)(?:output truncated|tokens truncated|truncated\.\.\.)',text): counts['truncated_output_markers'] += 1
                    if re.search(r'(?i)(?:isError["\s:]+true|Process exited with code [1-9]|exit_code["\s:]+[1-9]|Traceback \(most recent call last\))',text): counts['error_output_candidates'] += 1
    coverage['capture_started_utc'] = capture_started
    coverage['capture_completed_utc'] = datetime.now(timezone.utc).isoformat()
    durations.sort()
    return {'schema_version':1,'window':{'since_epoch':since,'until_exclusive_epoch':until},'coverage':dict(coverage,rollout_event_epoch_range=[low,high],excluded_thread_count=len(excluded)), 'counts':dict(counts),'tool_calls':dict(tools.most_common()),'nested_tool_call_text_candidates':dict(nested_tools.most_common()),'event_types':dict(event_types),'state_models':dict(models),'state_roles':dict(routes),'projected_turns':{'statuses':dict(statuses),'duration_samples':len(durations),'duration_ms_p50':durations[len(durations)//2] if durations else None,'duration_ms_p90':durations[min(len(durations)-1,int(len(durations)*.9))] if durations else None},'runtime_usage':{'token_deltas':dict(tokens),'billing':None,'limitations':'Owner-attested cumulative counter deltas only; initial baselines omitted; resets counted as fresh usage. Incomplete retained ownership and missing baselines make this a partial measure, never billing.'},'limitations':['All activity, not exclusively GPT Engineer. Catalog presence does not establish skill loading.','Read, error, truncation, and repetition markers are candidates; nested tools.* references are static text candidates, including possible quoted examples, not confirmed executions.','Copied stable events are deduplicated globally; owner classification uses projected turn ownership when available.','State active threads use update time; rollout metrics use event time; history metrics use turn start time.','Live rotating stores are read-only but not an immutable cross-store snapshot.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex-home',type=Path,default=Path.home()/'.codex')
    parser.add_argument('--since',required=True)
    parser.add_argument('--until',required=True)
    parser.add_argument('--exclude-thread',action='append',default=[])
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        since,until=epoch(args.since),epoch(args.until)
    except ValueError as error:
        parser.error(str(error))
    if since>=until: parser.error('--since must precede --until')
    result=json.dumps(audit(args.codex_home,since,until,args.exclude_thread),indent=2,sort_keys=True)+'\n'
    if args.output: args.output.write_text(result)
    else: print(result,end='')

if __name__=='__main__': main()
