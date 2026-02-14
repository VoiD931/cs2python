import json

with open('client_dll.json', 'r') as f:
    data = json.load(f)

classes = data['client.dll']['classes']
if 'CCSPlayerController' in classes:
    print(json.dumps(classes['CCSPlayerController']['fields'], indent=2))
else:
    print("CCSPlayerController not found")
