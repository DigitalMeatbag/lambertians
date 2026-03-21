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
call_by_tool = collections.Counter(e['payload'].get('tool_name') for e in tool_calls)
fail_by_tool = collections.Counter(e['payload'].get('tool_name') for e in tool_failures)
fail_by_reason = collections.Counter(e['payload'].get('error_type') for e in tool_failures)
fetches = [e for e in tool_calls if e['payload'].get('tool_name') == 'http.fetch']
mem_queries = [e for e in tool_calls if e['payload'].get('tool_name') == 'memory.query']
rejections = [e for e in tool_failures if e['payload'].get('error_type') == 'mcp_rejection']
rejected_paths = collections.Counter(e['payload'].get('path') or e['payload'].get('url') for e in rejections)

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
    p = fe['payload']
    print(f"  url={p.get('url')} status={p.get('status_code')} bytes={p.get('bytes_received')} truncated={p.get('truncated')}")
print()
print(f'memory.query calls ({len(mem_queries)}):')
for m in mem_queries:
    print(f"  {m['payload']}")
print()
print('Top 20 rejected paths:')
for path, count in rejected_paths.most_common(20):
    print(f'  {count:3d}  {path}')
