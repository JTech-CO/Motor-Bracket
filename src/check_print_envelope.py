#!/usr/bin/env python3
"""실제 STEP/STL 치수, 출력 배치, 원본 기능 치수와 간섭 여유 검사.
한계: 슬라이서/G-code·실물 출력·강성 검사는 아니다. 단위 mm.
"""
from pathlib import Path
import json, math, hashlib, csv
import numpy as np
import cadquery as cq
import trimesh
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from geometry import ROOT,P,NAMES,motor_proxy,holes,cassette

def exact_bounds(shape):
    b=Bnd_Box()
    BRepBndLib.AddOptimal_s(shape.wrapped,b,False,False)
    return np.array(b.Get()).reshape(2,3)

def size(shape):
    b=exact_bounds(shape)
    return b[1]-b[0]

def passed(name,value,limit,unit,rows):
    value=float(value);ok=abs(value)<=limit
    rows.append({'검사':name,'값':value,'검사_허용오차':limit,'단위':unit,'통과':bool(ok)})
    if not ok:raise AssertionError(f'{name}: {value} > {limit}')

def main():
    rows=[];parts=[];bed=[];clearance=[]
    limit=np.array(P['manufacturing']['printer_build_volume_mm'])
    # 출력축 기준 치수를 보존한다. 폭 축소를 모델 전체 비율 축소로 대체하지 않는다.
    for name,value,expected in [('상판두께',P['shell']['top_thickness'],16),('측판두께',P['shell']['face_thickness'],18),('하판두께',P['shell']['bottom_thickness'],12),('상면Z',P['shell']['outer_top_z'],100),('최하단Z',P['shell']['outer_bottom_z'],-80),('바퀴외경',P['assembly']['wheel_diameter_user'],203.2),('M8길이',P['frame']['bolt_length'],40),('M6길이',P['motor']['bolt_length'],30),('M8개수',P['frame']['quantity_each'],4),('M6개수',P['motor']['quantity_each'],4)]:
        passed(name+' 유지',value-expected,1e-8,'mm 또는 개',rows)
    for side in ('L','R'):
        for number in ('01','03'):
            name=f'SCMB-G{number}-{side}';q=cq.importers.importStep(str(ROOT/'cad/step'/f'{name}.step')).val()
            bb=exact_bounds(q);dims=bb[1]-bb[0]
            passed(name+' 단일솔리드',len(q.Solids())-1,0,'개',rows)
            passed(name+' CAD 크기 상한200',np.maximum(dims-limit,0).max(),1e-5,'mm',rows)
            raw=trimesh.load_mesh(ROOT/'print'/f'{name}.stl',process=True)
            passed(name+' STL 크기 상한200',np.maximum(raw.extents-limit,0).max(),1e-5,'mm',rows)
            if not raw.is_watertight or not raw.is_winding_consistent:raise AssertionError(name+' STL 비수밀')
            passed(name+' STL/CAD 체적차',abs(abs(raw.volume)-q.Volume())/q.Volume(),.003,'비율',rows)
            rot=np.eye(4)
            if number=='01':
                # 수직판과 ㄷ자 측면을 배드에 놓는 +Y 90도 배치: XY=180×162 / Z=196.
                rot[:3,:3]=np.array([[0,0,1],[0,1,0],[-1,0,0]])
            placed=raw.copy();placed.apply_transform(rot)
            delta=np.array([100,100,0])-np.array([placed.bounds[:,0].mean(),placed.bounds[:,1].mean(),placed.bounds[0,2]])
            trans=np.eye(4);trans[:3,3]=delta;matrix=trans@rot;placed.apply_transform(trans)
            path=ROOT/'print/bed_ready'/f'{name}-BED.stl';placed.export(path)
            readback=trimesh.load_mesh(path,process=True)
            passed(name+' 배치후 각축<=200',np.maximum(readback.extents-limit,0).max(),1e-5,'mm',rows)
            passed(name+' 배드 음수좌표 없음',np.minimum(readback.bounds[0],0).min(),1e-5,'mm',rows)
            passed(name+' 실제배드 200큐브내',np.maximum(readback.bounds[1]-limit,0).max(),1e-5,'mm',rows)
            passed(name+' 배치후Z최저0',readback.bounds[0,2],1e-5,'mm',rows)
            passed(name+' 강체변환 회전행렬',np.linalg.norm(matrix[:3,:3].T@matrix[:3,:3]-np.eye(3)),1e-10,'무차원',rows)
            b=P['manufacturing']['example_brim_width_mm'];with_brim=readback.extents.copy();with_brim[:2]+=2*b
            passed(name+' 5mm브림 가정범위<=200',np.maximum(with_brim-limit,0).max(),1e-5,'mm',rows)
            parts.append({'part':name,'bounds_mm':bb.tolist(),'size_mm':dims.tolist(),'mass_kg_density1_06':q.Volume()*1.06e-6,'volume_mm3':q.Volume(),'solid_count':len(q.Solids())})
            bed.append({'part':name,'file':str(path.relative_to(ROOT)),'bed_bounds_mm':readback.bounds.tolist(),'bed_size_mm':readback.extents.tolist(),'rigid_transform_4x4':matrix.tolist(),'example_brim_mm':b,'example_envelope_with_brim_mm':with_brim.tolist(),'infill_request_percent':100,'sliced':False,'supports_validated':False})
        shell=cq.importers.importStep(str(ROOT/'cad/step'/f'{NAMES[side]}.step')).val()
        can=dict(motor_proxy(side))['can']
        min_dist=shell.distance(can)
        passed(side+' 모터캔과본체 최소1mm명목여유',max(1.-min_dist,0),1e-5,'mm',rows)
        clearance.append({'side':side,'can_to_shell_min_distance_mm':min_dist,'proxy_only':True})
        # 홀 축을 STEP의 원통면에서 읽어 원본 중심이 유지되는지 확인한다.
        axes=[]
        for f in shell.Faces():
            if f.geomType()=='CYLINDER':
                cyl=f._geomAdaptor().Cylinder();r=cyl.Radius();pos=cyl.Location();direction=cyl.Axis().Direction()
                if abs(r-5.1)<1e-5 and abs(direction.Y())>.9999:
                    axes.append(np.array([pos.X(),pos.Z()]))
        for i,h in enumerate(holes(side),1):
            passed(f'{side} 실제M6홀{i} 중심 보존',min(np.linalg.norm(x-np.array(h)) for x in axes),1e-5,'mm',rows)
        axes8=[]
        for f in shell.Faces():
            if f.geomType()=='CYLINDER':
                cy=f._geomAdaptor().Cylinder();pos=cy.Location()
                if abs(cy.Radius()-6.1)<1e-5 and abs(cy.Axis().Direction().Z())>.9999:axes8.append(np.array([pos.X(),pos.Y()]))
        for i,h in enumerate(P['frame']['holes_xy'],1):
            passed(f'{side} 실제M8홀{i} 90x100좌표 보존',min(np.linalg.norm(x-np.array(h)) for x in axes8),1e-5,'mm',rows)
    out={'revision':'G','printer_mm':limit.tolist(),'printable_parts':parts,'bed_ready_parts':bed,'motor_clearance_proxy':clearance,'check_count':len(rows),'checks':rows,'all_pass':True,'structural_analysis':False,'slicing_and_machine_test':False,'limitations':'5 mm 브림은 기하학적 외접영역 계산이며 실제 툴패스가 아님. 서포트·래프트·퍼지·프린터 제한영역은 학교 프로필로 검토.'}
    (ROOT/'qa/print_envelope.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (ROOT/'data/print_parts.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['부품','STL파일','출력배치Xmm','출력배치Ymm','출력배치Zmm','수량','축척','채움요청%','주의'])
        for p in bed:w.writerow([p['part'],p['file'],*[round(v,3) for v in p['bed_size_mm']],1,'100%',100,'한 부품씩 출력 / 서포트·프린터프로필 검토'])
    print(json.dumps({k:out[k] for k in ['check_count','printable_parts','motor_clearance_proxy']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
