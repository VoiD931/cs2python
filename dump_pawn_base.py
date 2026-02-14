import json

with open('client_dll.json', 'r') as f:
    data = json.load(f)

classes = data['client.dll']['classes']
if 'C_CSPlayerPawnBase' in classes:
    print(json.dumps(classes['C_CSPlayerPawnBase']['fields'], indent=2))
else:
    print("C_CSPlayerPawnBase not found")
