import json

with open('client_dll.json', 'r') as f:
    data = json.load(f)

classes = data['client.dll']['classes']
if 'CPlayer_WeaponServices' in classes:
    print(json.dumps(classes['CPlayer_WeaponServices']['fields'], indent=2))
else:
    print("CPlayer_WeaponServices not found")
