import json

transcript_path = r"C:\Users\Indian Railway\.gemini\antigravity\brain\e1c72f05-a097-45cf-9a3f-9cf48417738e\.system_generated\logs\transcript_full.jsonl"
out_path = r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard\scratch\raw_user_upload.txt"

with open(transcript_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(reversed(lines)):
    if 'AZ1054' in line:
        data = json.loads(line)
        print("Found line at reversed idx:", idx, "type:", data.get('type'), "source:", data.get('source'))
        content = data.get('content', '')
        if 'AZ1054' in content:
            with open(out_path, 'w', encoding='utf-8') as out:
                out.write(content)
            print("Wrote content to", out_path, "length:", len(content))
            break
