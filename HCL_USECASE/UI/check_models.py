import requests
import json

try:
    r = requests.get('http://localhost:11434/api/tags', timeout=10)
    data = r.json()
    models = data.get('models', [])
    print('Installed models:')
    if models:
        for m in models:
            print('  ' + m['name'])
    else:
        print('  None')
except Exception as e:
    print('Error:', e)