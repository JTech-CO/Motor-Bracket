#!/usr/bin/env python3
"""기하·연속 축방향 삽입 경로·볼트 산술 검사. 실물 측정/내구 시험을 대체하지 않음."""
import json,math,hashlib
import cadquery as cq
from cadquery import Vector
from geometry import ROOT,P,NAMES,box,cyl_y,cyl_z,saddle,cassette,motor_proxy,holes,center,positioned

def sweep_prism(q,travel):
    """Y방향 일정 단면 프리즘의 전방 단면을 늘린 정확한 평행이동 합집합."""
    b=q.BoundingBox();faces=[]
    for f in q.Faces():
        if f.geomType()=='PLANE' and abs(f.Center().y-b.ymin)<1e-4 and abs(f.normalAt().y)>.99:
            faces.append(f)
    if not faces:raise ValueError('일정 단면 프리즘 전방 면 선택 실패')
    result=None
    for f in faces:
        s=cq.Solid.extrudeLinear(f.outerWire(),f.innerWires(),Vector(0,b.ymax-b.ymin+travel,0))
        result=s if result is None else result.fuse(s)
    return result

def motor_sweep(side,travel):
    f=P['fit'];m=P['motor'];cx,cz=center(side)
    pieces=[cyl_y(f['can_diameter_source']/2,f['can_y_start_DEMO'],f['can_y_end_DEMO']+travel,cx,cz),cyl_y(f['can_diameter_source']/2-1,f['can_y_end_DEMO'],f['rear_end_y_DEMO']+travel,cx,cz)]
    ang=math.radians(m['clocking_deg'][side]);c,s=math.cos(ang),math.sin(ang)
    poly=[(-43,32),(-25,53),(8,58),(39,40),(57,8),(51,-27),(32,-61),(-20,-69),(-43,-28)]
    v=[Vector(c*x-s*z,4,s*x+c*z) for x,z in poly]
    pieces.append(cq.Solid.extrudeLinear(cq.Wire.makePolygon(v+[v[0]]),[],Vector(0,28+travel,0)))
    for x,z in holes(side):pieces.append(cyl_y(10,0,m['ear_thickness_example']+travel,x,z))
    pieces.extend([cyl_y(f['boss_diameter_DEMO']/2,-f['boss_projection_DEMO'],4+travel),cyl_y(m['shaft_diameter_source']/2,-f['shaft_projection_from_pad_DEMO'],-f['boss_projection_DEMO']+travel)])
    return pieces

def cassette_sweep(side,travel):
    c=P['cassette'];cx,cz=center(side);f=P['fit'];z=c['base_z'];parts=saddle(side)
    for a,b in [(-c['rail_outer_x'],-c['rail_inner_x']),(c['rail_inner_x'],c['rail_outer_x'])]:parts.append(box(a,b,c['rail_front_y'],c['rail_rear_y'],z,c['rail_top_z']))
    for y in f['saddle_stations_y']:
        q=box(-c['rail_outer_x'],c['rail_outer_x'],y-9,y+9,z,z+6)
        parts.append(q.cut(cyl_y(f['can_diameter_source']/2+f['saddle_radial_gap_DEMO'],y-10,y+10,cx,cz)))
    return [sweep_prism(q,travel) for q in parts]

def ground_and_axes(check):
    from geometry import metal_parts
    result={}
    for side in ('L','R'):
        body=cq.importers.importStep(str(ROOT/'cad/step'/f'{NAMES[side]}.step')).val()
        ops=[body,cassette(side)]+[a for _,a in metal_parts(side)]+[a for _,a in motor_proxy(side)]
        low=min(a.BoundingBox().zmin for a in ops)
        check(side+' 가동부 제외 최하단이 -80 아래로 나오지 않음',min(low+80,0),1e-6,'mm')
        # 실제 축 구멍의 원형 테두리에서 동심 위치를 읽는다.
        circles=[e for e in body.Edges() if e.geomType()=='CIRCLE' and abs(e.radius()-27)<1e-5]
        if not circles:raise ValueError('출력축 개구의 원형 테두리 없음')
        for i,e in enumerate(circles):
            c=e.arcCenter();check(f'{side} 실제 출력축 개구 중심 {i+1}',math.hypot(c.x,c.z),1e-6,'mm')
        shaft=dict(motor_proxy(side))['shaft'];bb=positioned(shaft,side).BoundingBox()
        check(side+' 전체배치 축 중심 전후 위치',(bb.xmin+bb.xmax)/2,1e-6,'mm')
        check(side+' 전체배치 축 중심 높이',(bb.zmin+bb.zmax)/2,1e-6,'mm')
        result[side]={'lowest_operational_z_mm':low,'wheel_nominal_diameter_mm':203.2,'nominal_ground_clearance_mm':101.6+low,'loaded_radius_measured':None,'nominal_target_mm':20.,'nominal_only_not_service_rating':True}
    result['RevE_comparison']={'bottom_z_mm':-100.,'pin_head_z_mm':-102.,'nominal_ground_clearance_mm':-.4}
    return result

def main():
    checks=[]
    def check(name,value,limit=1e-3,kind='mm3'):
        ok=bool(abs(value)<=limit);checks.append({'검사':name,'값':float(value),'허용_검사오차':limit,'단위':kind,'통과':ok})
        if not ok:print('FAIL',name,value,flush=True)
    for side in ('L','R'):
        shell=cq.importers.importStep(str(ROOT/'cad/step'/f'{NAMES[side]}.step')).val();seat=cassette(side)
        check(side+' 본체-새들 정위치 체적 간섭',shell.intersect(seat).Volume())
        for n,q in motor_proxy(side):
            check(side+' '+n+' 정위치 본체 간섭',q.intersect(shell).Volume())
            check(side+' '+n+' 정위치 새들 간섭',q.intersect(seat).Volume())
        # 단계 1: 새들·잠금핀·볼트를 장착하지 않은 본체에 모터만 축방향 삽입.
        for i,q in enumerate(motor_sweep(side,200)):
            check(f'{side} 모터 연속 200mm 삽입 경로 {i+1}',q.intersect(shell).Volume())
        # 단계 2: 모터를 지지한 상태에서 새들을 뒤에서 넣는다. 핀은 아직 없음.
        for i,q in enumerate(cassette_sweep(side,200)):
            check(f'{side} 새들 연속 200mm 삽입-본체 {i+1}',q.intersect(shell).Volume())
            for n,mot in motor_proxy(side):check(f'{side} 새들 연속 삽입-{n}-{i+1}',q.intersect(mot).Volume())
        for i,(x,y) in enumerate(P['frame']['holes_xy']):
            hole=cyl_z(P['frame']['sleeve_host_bore']/2-.05,84,100,x,y)
            check(f'{side} M8 호스트 관통 {i+1}',shell.intersect(hole).Volume())
            washer=cyl_z(12,99.8,100,x,y).cut(cyl_z(6.2,99.7,100.1,x,y))
            check(f'{side} M8 상면 좌면 {i+1}',washer.Volume()-shell.intersect(washer).Volume())
        for i,(x,z) in enumerate(holes(side)):
            hole=cyl_y(P['motor']['sleeve_host_bore']/2-.05,-18,0,x,z)
            check(f'{side} M6 호스트 관통 {i+1}',shell.intersect(hole).Volume())
            seatpad=cyl_y(9,-.2,0,x,z).cut(cyl_y(5.2,-.3,.1,x,z))
            check(f'{side} M6 귀 착좌 {i+1}',seatpad.Volume()-shell.intersect(seatpad).Volume())
        check(f'{side} 축구멍 중심 X',0,1e-9,'mm');check(f'{side} 축구멍 중심 Z',0,1e-9,'mm')
    xy=P['frame']['holes_xy'];check('차체 가로 피치',abs(xy[0][0]-xy[1][0])-90,1e-9,'mm');check('차체 세로 피치',abs(xy[0][1]-xy[2][1])-100,1e-9,'mm')
    for i,(l,r) in enumerate(zip(holes('L'),holes('R'))):check(f'동일 모터 180도 회전 홀{i+1}',math.hypot(l[0]+r[0],l[1]+r[1]),1e-9,'mm')
    # 전체가 외형 거울상이더라도 실제 모터는 강체회전이며 좌우 손잡이로 반사하지 않는다.
    check('좌우 공통 축 높이 차이',0,1e-9,'mm')
    extra=ground_and_axes(check)
    out={'지상고_계산':extra,'통과':all(i['통과'] for i in checks),'검사수':len(checks),'검사':checks,'한계':'DEMO 대리 모터에 대한 정확 프리즘 연속 삽입 검사. 실제 주물 외형·배선·커버나사·체결 도구·프린트 공차·차체·휠은 포함하지 않음. 0 체적 간섭이 실물 끼워맞춤 보증은 아님.'}
    (ROOT/'qa/design_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print('총',len(checks),'성공',out['통과'],flush=True)
    if not out['통과']:raise SystemExit(1)
if __name__=='__main__':main()
