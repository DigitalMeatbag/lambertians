import json, collections

events = []
with open('/app/runtime/event_stream/events.jsonl') as f:
    for line in f:
        line = line.strip()
        if line:
            events.append(json.loads(line))

total = len(events)
by_type = collections.Counter(e['event_type'] for e in events)
tool_calls = [e for e in events if e['event_type'] == 'TOOL_CALL']
tool_failures = [e for e in events if e['event_type'] == 'TOOL_FAILURE']

call_by_tool = collections.Counter(e.get('tool_name') for e in tool_calls)
fail_by_tool = collections.Counter(e.get('tool_name') for e in tool_failures)
fail_by_reason = collections.Counter(e.get('error_type') for e in tool_failures)

fetches = [e for e in tool_calls if e.get('tool_name') == 'http.fetch']
mem_queries = [e for e in tool_calls if e.get('tool_name') == 'memory.query']
mem_stores = [e for e in tool_calls if e.get('tool_name') == 'memory.store']
fs_writes = [e for e in tool_calls if e.get('tool_name') == 'fs.write']

rejections = [e for e in tool_failures if e.get('error_type') == 'mcp_rejection']
rejected_paths = collections.Counter(e.get('path') or e.get('url') for e in rejections)
death = [e for e in events if e['event_type'] == 'DEATH']

print('=== L32 POSTMORTEM ===')
print(f'Total events: {total}')
print(f'Event types: {dict(by_type)}')
print()
print(f'TOOL_CALL by tool: {dict(call_by_tool)}')
print(f'TOOL_FAILURE by tool: {dict(fail_by_tool)}')
print(f'TOOL_FAILURE by reason: {dict(fail_by_reason)}')
print()
print(f'http.fetch calls ({len(fetches)}):')
for fe in fetches:
    print(f"  t{fe.get('turn_number')} url={fe.get('url')} status={fe.get('status_code')} bytes={fe.get('bytes_received')} truncated={fe.get('truncated')}")
print()
print(f'memory.query calls ({len(mem_queries)}):')
for m in mem_queries:
    print(f"  t{m.get('turn_number')} query={m.get('query_text')}")
print()
print(f'memory.store calls ({len(mem_stores)}):')
for m in mem_stores:
    print(f"  t{m.get('turn_number')} {json.dumps({k:v for k,v in m.items() if k not in ['event_id','instance_id','source_service','timestamp']})}")
print()
print(f'fs.write calls ({len(fs_writes)}):')
for w in fs_writes:
    print(f"  t{w.get('turn_number')} path={w.get('path')}")
print()
print('Top 25 rejected paths:')
for path, count in rejected_paths.most_common(25):
    print(f'  {count:3d}  {path}')
print()
print('DEATH event:')
for d in death:
    print(json.dumps(d, indent=2))
