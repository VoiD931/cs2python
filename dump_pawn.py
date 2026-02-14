import json

with open('client_dll.json', 'r') as f:
    data = json.load(f)

classes = data['client.dll']['classes']
if 'C_BasePlayerPawn' in classes:
    print(json.dumps(classes['C_BasePlayerPawn']['fields'], indent=2))
else:
    print("C_BasePlayerPawn not found")
