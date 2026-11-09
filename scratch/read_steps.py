import json

with open(r'C:\Users\Indian Railway\.gemini\antigravity\brain\e1c72f05-a097-45cf-9a3f-9cf48417738e\.system_generated\logs\transcript_full.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        idx = data.get('step_index')
        if idx in range(1974, 1982):
            c = str(data.get('content') or data.get('thinking'))
            print(f"Step {idx} [{data.get('type')}]: {c[:180]}")
