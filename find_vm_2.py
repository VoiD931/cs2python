import json

with open('client_dll.json', 'r') as f:
    data = json.load(f)

classes = data['client.dll']['classes']

def find_field(classname, fieldname):
    if classname not in classes:
        return None
    cls = classes[classname]
    if fieldname in cls['fields']:
        return cls['fields'][fieldname]
    if cls['parent']:
        return find_field(cls['parent'], fieldname)
    return None

# Try Base Player Pawn
print(f"m_pViewModelServices in C_BasePlayerPawn: {find_field('C_BasePlayerPawn', 'm_pViewModelServices')}")
print(f"m_hViewModel in CCSPlayer_ViewModelServices: {find_field('CCSPlayer_ViewModelServices', 'm_hViewModel')}")
print(f"m_hViewModel in CPlayer_ViewModelServices: {find_field('CPlayer_ViewModelServices', 'm_hViewModel')}")

# List all fields in CCSPlayer_ViewModelServices
if 'CCSPlayer_ViewModelServices' in classes:
    print("CCSPlayer_ViewModelServices fields:", classes['CCSPlayer_ViewModelServices']['fields'])
