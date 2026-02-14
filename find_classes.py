import json

with open('client_dll.json', 'r') as f:
    data = json.load(f)

classes = data['client.dll']['classes']

print("Classes with 'ViewModel' in name:")
for cls in classes:
    if 'ViewModel' in cls:
        print(cls)

print("\nCam related:")
for cls in classes:
    if 'Camera' in cls:
        print(cls)
