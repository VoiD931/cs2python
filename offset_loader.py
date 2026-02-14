import json
import os

def load_json(filename):
    if not os.path.exists(filename):
        return {}
    with open(filename, 'r') as f:
        return json.load(f)

class OffsetLoader:
    def __init__(self):
        self.offsets = load_json("offsets.json")
        self.client_dll = load_json("client_dll.json")
        
    def get_client_offset(self, name):
        return self.offsets.get("client.dll", {}).get(name, 0)

    def get_netvar(self, class_name, field_name):
        # Recursive search in client_dll.json
        classes = self.client_dll.get("client.dll", {}).get("classes", {})
        
        current_class = class_name
        while current_class:
            cls_data = classes.get(current_class)
            if not cls_data:
                break
                
            fields = cls_data.get("fields", {})
            if field_name in fields:
                return fields[field_name]
                
            current_class = cls_data.get("parent")
            
        return 0

_loader = None

def get_loader():
    global _loader
    if _loader is None:
        _loader = OffsetLoader()
    return _loader
