#!/usr/bin/env python3
"""배포 CAD의 형상·파일 구조 회귀 검사. CAD 앱 화면/실물 강도 검증은 아님."""
from pathlib import Path
import ast, hashlib, io, json, re, zipfile, xml.etree.ElementTree as ET
import cadquery as cq
import trimesh
import fitz
import OCP

ROOT = Path(__file__).resolve().parents[1]

def require(condition, message):
    if not condition:
        raise AssertionError(message)

def main():
    manifest = json.loads((ROOT/'data/import_manifest.json').read_text(encoding='utf-8'))
    results = {'구조_형상검사': [], 'STL': [], 'PDF': [], '소스문법': [], '원본': [],
               'FreeCAD_실제앱열기': '미실시', 'SolidWorks_실제앱열기': '미실시',
               '매크로_실제앱실행': '미실시 / 문법 검사만 실시', 'RevG_구조해석': '미실시',
               '실행환경': {'CadQuery': cq.__version__, 'OCP': OCP.__version__}}
    for row in manifest:
        name = row['name']; expected = row['expected_solids']; volume = row['expected_volume_mm3']
        for rel in [row['step'], f'compatibility/AP214/{name}.step']:
            p = ROOT/rel; data = p.read_bytes()
            require(data.startswith(b'ISO-10303-21;'), rel+': STEP 헤더 오류')
            require(max(data) < 128 and b'.MILLI.,.METRE.' in data, rel+': ASCII/mm 검사 오류')
            shape = cq.importers.importStep(str(p)).val()
            error = abs(shape.Volume()-volume)/volume
            require(shape.isValid() and len(shape.Solids()) == expected and error < 1e-6, rel+': 형상 불일치')
            require(len(re.findall(rb'\bPRODUCT\(', data)) == 1, rel+': 제품 계층이 평탄하지 않음')
            results['구조_형상검사'].append({'file': rel, 'solids': len(shape.Solids()), 'volume_mm3': shape.Volume(), 'relative_error': error, 'pass': True})
        rel = f'cad/freecad/{name}.FCStd'
        with zipfile.ZipFile(ROOT/rel) as z:
            require(z.testzip() is None, rel+': ZIP CRC 오류')
            doc = ET.fromstring(z.read('Document.xml')); gui = ET.fromstring(z.read('GuiDocument.xml'))
            count = len(doc.find('Objects')); views = gui.find('ViewProviderData')
            require(count == len(views) == len(doc.find('ObjectData')), rel+': 객체 수 불일치')
            total = 0.; solids = 0
            for o in doc.find('ObjectData'):
                shape_file = o.find("Properties/Property[@name='Shape']/Part").get('file')
                data = z.read(shape_file)
                require(b'CASCADE Topology V1' in data[:100], rel+': BREP V1 오류')
                q = cq.Shape.importBrep(io.BytesIO(data))
                require(q.isValid() and q.Volume() > 0, rel+': 저장 형상 오류')
                total += q.Volume(); solids += len(q.Solids())
            require(solids == expected and abs(total-volume)/volume < 1e-6, rel+': 내장 솔리드 불일치')
            require(all(v.find("Properties/Property[@name='Visibility']/Bool").get('value')=='true' for v in views), rel+': 숨김 객체 존재')
            require(gui.find('Camera') is not None, rel+': 카메라 누락')
            results['구조_형상검사'].append({'file':rel, 'solids':solids, 'objects':count, 'volume_mm3':total, 'container_pass':True, 'app_tested':False})
        raw = (ROOT/row['brep']).read_bytes()
        require(b'CASCADE Topology V1' in raw[:100], row['brep']+': BREP 버전 불일치')
        q = cq.Shape.importBrep(io.BytesIO(raw))
        require(q.isValid() and len(q.Solids()) == expected, row['brep']+': BREP 오류')
        print(name+' 검사 완료', flush=True)
    by_name = {r['name']: r for r in manifest}
    for p in sorted((ROOT/'print').glob('*.stl')):
        mesh = trimesh.load_mesh(p, process=True)
        expected = by_name[p.stem]['expected_volume_mm3']
        error = abs(abs(mesh.volume)-expected)/expected
        require(mesh.is_watertight and mesh.is_winding_consistent and error < .003, p.name+': STL 수밀성/체적 검사 오류')
        results['STL'].append({'file':str(p.relative_to(ROOT)), 'watertight':bool(mesh.is_watertight), 'triangles':len(mesh.faces), 'relative_volume_error':error})
    pdfs = {'drawings/설계도면.pdf':4, 'docs/수정설명서.pdf':4, 'drawings/Motor-LR-1to1-A4.pdf':2, 'drawings/Frame-90x100-1to1-A4.pdf':1}
    for rel,pages in pdfs.items():
        with fitz.open(ROOT/rel) as doc:
            require(len(doc)==pages and all(len(p.get_text().strip())>100 for p in doc), rel+': 페이지/본문 누락')
            results['PDF'].append({'file':rel, 'pages':len(doc), 'text_present':True})
    for p in sorted((ROOT/'src').glob('*.py')) + sorted(ROOT.glob('*.py')) + sorted(ROOT.glob('*.FCMacro')):
        ast.parse(p.read_text(encoding='utf-8'),filename=p.name)
        results['소스문법'].append(str(p.relative_to(ROOT)))
    for row in json.loads((ROOT/'qa/reference_hashes.json').read_text(encoding='utf-8')):
        actual = hashlib.sha256((ROOT/'reference'/row['file']).read_bytes()).hexdigest()
        require(actual==row['sha256'], row['file']+': 참조 원본 해시 불일치')
        results['원본'].append({'file':row['file'], 'sha256':actual, 'matches_recorded_original':True})
    design = json.loads((ROOT/'qa/design_checks.json').read_text(encoding='utf-8'))
    require(design['통과'], '기하 검사 선행 실패')
    envelope = json.loads((ROOT/'qa/print_envelope.json').read_text(encoding='utf-8'))
    require(envelope['all_pass'], '200 mm 출력 공간 검사 실패')
    results['출력공간_검사수'] = envelope['check_count']
    for row in envelope['bed_ready_parts']:
        mesh = trimesh.load_mesh(ROOT/row['file'], process=True)
        require(mesh.is_watertight and mesh.is_winding_consistent, row['file']+': 배치 STL 비수밀')
        require(max(mesh.extents) <= 200.00001 and mesh.bounds.min() >= -0.00001 and mesh.bounds.max() <= 200.00001, row['file']+': 배치 경계 초과')
        expected = by_name[row['part']]['expected_volume_mm3']
        error = abs(abs(mesh.volume)-expected)/expected
        require(error < .003, row['file']+': 배치 후 체적 불일치')
        results['STL'].append({'file':row['file'], 'watertight':True, 'triangles':len(mesh.faces), 'relative_volume_error':error, 'bed_bounds_mm':mesh.bounds.tolist()})
    results['출력공간_통과'] = True
    results['기하검사_통과'] = True
    results['완료'] = True
    (ROOT/'qa/package_validation.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('CAD 26 STEP / 13 FCStd + BREP, STL, PDF, 원본·소스 검사 완료. 앱 열기는 미검증.',flush=True)

if __name__ == '__main__':
    main()
