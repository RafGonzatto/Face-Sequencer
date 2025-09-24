import yaml, jsonschema
from app import app
with open('openapi.yaml','r',encoding='utf-8') as f:
    spec=yaml.safe_load(f)
client=app.test_client()
app.config['app_state']['export_tasks']['demo-task']={'status':'running','progress':10,'filename':'out.mp4','path':'uploads/out.mp4','error':None,'message':'Working'}
resp=client.get('/api/export/status/demo-task')
print('Response JSON:', resp.get_json())
export_status_schema=spec['components']['schemas']['ExportStatusResponse']

def expand(s):
    if '$ref' in s:
        return expand(spec['components']['schemas'][s['$ref'].split('/')[-1]])
    if 'allOf' in s:
        merged={'type':'object','properties':{},'required':[]}
        for part in s['allOf']:
            ex=expand(part)
            if ex.get('type')=='object':
                merged['properties'].update(ex.get('properties',{}))
                merged['required']+=ex.get('required',[])
        return merged
    return s
std=expand({'$ref':'#/components/schemas/StandardResponse'})
jsonschema.validate(instance=resp.get_json(), schema=std)
print('Validation OK')
