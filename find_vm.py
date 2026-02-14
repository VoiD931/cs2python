import json

with open('client_dll.json', 'r') as f:
    data = json.load(f)

classes = data['client.dll']['classes']

def find_field(classname, fieldname):
    if classname not in classes:
        print(f"Class {classname} not found")
        return None
    cls = classes[classname]
    if fieldname in cls['fields']:
        return cls['fields'][fieldname]
    if cls['parent']:
        return find_field(cls['parent'], fieldname)
    return None

print(f"m_flViewmodelFOV in C_CSPlayerPawn: {find_field('C_CSPlayerPawn', 'm_flViewmodelFOV')}")
print(f"m_flViewmodelFOV in C_BasePlayerPawn: {find_field('C_BasePlayerPawn', 'm_flViewmodelFOV')}")

# Also check for m_pViewModelServices and m_hViewModel
print(f"m_pViewModelServices in C_CSPlayerPawn: {find_field('C_CSPlayerPawn', 'm_pViewModelServices')}")
print(f"m_hViewModel in CPlayer_ViewModelServices: {find_field('CPlayer_ViewModelServices', 'm_hViewModel')}")
