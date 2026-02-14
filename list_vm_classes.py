import json

with open('client_dll.json', 'r') as f:
    data = json.load(f)

classes = data['client.dll']['classes']

print("Classes containing 'ViewModel':")
for k in classes.keys():
    if 'ViewModel' in k:
        print(k)

if 'C_BaseEntity' in classes:
    print("\nC_BaseEntity fields (first 20):")
    fields = classes['C_BaseEntity']['fields']
    i = 0
    for k, v in fields.items():
        print(f"{k}: {v}")
        i += 1
        if i > 20: break
