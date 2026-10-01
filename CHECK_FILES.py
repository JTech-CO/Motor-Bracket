#!/usr/bin/env python3
"""Python 기본 라이브러리만으로 다운로드 손상/HTML 오저장을 검사한다.
형상 커널 또는 FreeCAD/SolidWorks 화면을 검증하는 도구는 아니다.
실행: python CHECK_FILES.py
"""
from pathlib import Path
import hashlib, json, zipfile

def main():
    root = Path(__file__).resolve().parent
    errors=[]; checked=0
    sha_file=root/'MANIFEST.sha256'
    if not sha_file.exists():
        print('MANIFEST.sha256가 없습니다. 최종 ZIP을 다시 압축 해제해 주세요.')
        return 2
    for line in sha_file.read_text(encoding='utf-8').splitlines():
        digest,rel=line.split('  ',1);p=root/rel
        if not p.is_file():errors.append(rel+': 파일 없음');continue
        checked+=1
        if hashlib.sha256(p.read_bytes()).hexdigest()!=digest:errors.append(rel+': SHA256 불일치')
    for p in (root/'cad/step').glob('*.step'):
        data=p.read_bytes()
        if not data.startswith(b'ISO-10303-21;') or b'MANIFOLD_SOLID_BREP' not in data:
            errors.append(p.name+': STEP 형식 헤더/솔리드 엔터티 없음 (웹페이지를 저장했는지 확인)')
    for p in (root/'cad/freecad').glob('*.FCStd'):
        try:
            with zipfile.ZipFile(p) as z:
                if z.testzip() is not None:errors.append(p.name+': 압축 CRC 오류')
                for n in ('Document.xml','GuiDocument.xml'):
                    if n not in z.namelist():errors.append(p.name+': '+n+' 없음')
        except Exception as exc:errors.append(p.name+': '+str(exc))
    report={'checked_files':checked,'download_integrity_pass':not errors,'errors':errors,'CAD_app_display_tested':False}
    (root/'LOCAL_FILE_CHECK.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    print('파일 무결성과 CAD 앱의 표시 성공은 서로 다른 검사입니다.')
    return 1 if errors else 0

if __name__=='__main__':
    raise SystemExit(main())
