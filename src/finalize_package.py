#!/usr/bin/env python3
"""검증 완료 파일만 SHA256 목록과 저장소 ZIP으로 패키징."""
from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).resolve().parents[1]

def main():
    result=json.loads((ROOT/'qa/package_validation.json').read_text(encoding='utf-8'))
    if not result.get('완료') or not result.get('출력공간_통과'):
        raise RuntimeError('검증을 먼저 실행하세요.')
    # 사용자 실행 결과·파이썬 캐시는 배포 결과에서 제외함.
    files=[p for p in ROOT.rglob('*') if p.is_file() and not any(x in p.parts for x in ['__pycache__','.git','native_generated']) and p.name not in ['MANIFEST.sha256','LOCAL_FILE_CHECK.json'] and p.suffix not in ['.pyc','.FCStd1']]
    files=sorted(files)
    manifest=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(ROOT).as_posix()+'\n' for p in files)
    (ROOT/'MANIFEST.sha256').write_text(manifest,encoding='utf-8')
    target=ROOT.parent/(ROOT.name+'.zip')
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files+[ROOT/'MANIFEST.sha256']:
            z.write(p,(Path(ROOT.name)/p.relative_to(ROOT)).as_posix())
    with zipfile.ZipFile(target) as z:
        if z.testzip() is not None:raise RuntimeError('ZIP CRC 실패')
    print(json.dumps({'zip':str(target),'bytes':target.stat().st_size,'files':len(files)+1,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
