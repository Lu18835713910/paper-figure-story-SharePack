import hashlib, json
from pathlib import Path

class ContractError(ValueError):
    pass

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def save(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return path

def within(base,path):
    base=Path(base).resolve();out=Path(path).resolve()
    if not out.is_relative_to(base):
        raise ContractError(f'PATH_OUTSIDE_PACKAGE: {path}')
    return out
