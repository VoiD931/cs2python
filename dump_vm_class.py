import json

with open('client_dll.json', 'r') as f:
    data = json.load(f)

classes = data['client.dll']['classes']
if 'C_BaseViewModel' in classes:
    print(json.dumps(classes['C_BaseViewModel']['fields'], indent=2))
else:
    print("C_BaseViewModel not found")

if 'C_CSGOViewModel' in classes:
    print(json.dumps(classes['C_CSGOViewModel']['fields'], indent=2))
else:
    print("C_CSGOViewModel not found")
