import json
d = json.load(open('full_out.json'))
print(f"Total Cases: {len(d)}")
print()
for c in d[:5]:
    print(json.dumps(c, indent=2))
    print()
