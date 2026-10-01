#!/usr/bin/env python3
"""ㄷ자 좌우 모터 지지대. mm. CAD를 다시 만들 때는 미실측 DEMO 입력부터 확인할 것.
L/R을 같은 부품 복사로 만들지 않으며, 출력축 중심은 항상 (0,0,0)이다.
"""
from pathlib import Path
import json, math, sys
import cadquery as cq
from cadquery import Vector
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
P=json.loads((ROOT/'parameters.json').read_text(encoding='utf-8'))
u0,v0=P['fit']['can_axis_offset_uv_DEMO']
a0=(180.-math.degrees(math.atan2(v0,u0))+180.)%360.-180.
P['motor']['clocking_deg']={'L':a0,'R':a0+180.}
NAMES={'L':'SCMB-G01-L','R':'SCMB-G01-R'}

def exact_envelope(a):
    """표시 메시의 허용오차를 제외한 정밀 형상 외접치수."""
    b=Bnd_Box();BRepBndLib.AddOptimal_s(a.wrapped,b,False,False)
    v=b.Get()
    return list(v),[v[i+3]-v[i] for i in range(3)]

def ensure_print_volume(a,p=P):
    """미래 파라미터 변경으로 200 mm 제한을 다시 넘기지 못하도록 중단."""
    _,dims=exact_envelope(a)
    limits=p['manufacturing']['printer_build_volume_mm']
    if any(d>lim+1e-6 for d,lim in zip(dims,limits)):
        raise ValueError(f'출력 크기 초과: {dims} mm / 최대 {limits} mm. 축척으로 해결하지 마세요.')
    return a

def box(x0,x1,y0,y1,z0,z1):
    return cq.Solid.makeBox(x1-x0,y1-y0,z1-z0,Vector(x0,y0,z0))

def cyl_y(r,y0,y1,x=0.,z=0.):
    return cq.Solid.makeCylinder(r,y1-y0,Vector(x,y0,z),Vector(0,1,0))

def cyl_z(r,z0,z1,x=0.,y=0.):
    return cq.Solid.makeCylinder(r,z1-z0,Vector(x,y,z0),Vector(0,0,1))

def round_xy(w,d,r,cx,cy,z0,z1):
    w0=cq.Workplane('XY').center(cx,cy).rect(w,d).extrude(z1-z0).translate((0,0,z0))
    return w0.edges('|Z').fillet(r).val()

def round_xz(w,h,r,cx,cz,y0,y1):
    # XZ 평면의 법선은 -Y이다.
    w0=cq.Workplane('XZ',origin=(cx,y1,cz)).rect(w,h).extrude(y1-y0)
    return w0.edges('|Y').fillet(r).val()

def prism_yz(poly,x0,x1):
    v=[Vector(x0,y,z) for y,z in poly]
    return cq.Solid.extrudeLinear(cq.Wire.makePolygon(v+[v[0]]),[],Vector(x1-x0,0,0))

def holes(side,p=P):
    a=math.radians(p['motor']['clocking_deg'][side]);c,s=math.cos(a),math.sin(a)
    return [(round(c*u-s*v,9),round(s*u+c*v,9)) for u,v in p['motor']['holes_source_uv']]

def center(side,p=P):
    a=math.radians(p['motor']['clocking_deg'][side]);c,s=math.cos(a),math.sin(a)
    u,v=p['fit']['can_axis_offset_uv_DEMO']
    return c*u-s*v,s*u+c*v

def common_shell(p=P,windows=True):
    s=p['shell'];w=s['width'];yf=-s['face_thickness'];yr=s['depth_inboard'];zt=s['outer_top_z'];zb=s['outer_bottom_z'];zi=zt-s['top_thickness'];bi=zb+s['bottom_thickness']
    # 외곽은 좌우 공통, 뚜껑이 아닌 하나의 연결된 C 단면 솔리드이다.
    a=box(-w/2,w/2,yf,0,zb,zt).fuse(box(-w/2,w/2,0,yr,zi,zt),box(-w/2,w/2,0,yr,zb,bi)).clean()
    roots=[]
    for e in a.Edges():
        c=e.Center()
        if e.geomType()=='LINE' and abs(c.y)<1e-6 and (abs(c.z-zi)<1e-6 or abs(c.z-bi)<1e-6) and e.Length()>w-1:
            roots.append(e)
    if len(roots)!=2: raise ValueError('상하 루트 모서리 선택 오류')
    a=a.fillet(s['root_radius'],roots).clean()
    # 외곽 길이방향 네 코너를 둥글게 하여 적층 모서리와 손 접촉부를 정리한다.
    edges=[]
    for e in a.Edges():
        c=e.Center()
        if e.geomType()=='LINE' and abs(abs(c.x)-w/2)<1e-6 and (abs(c.z-zt)<1e-6 or abs(c.z-zb)<1e-6): edges.append(e)
    if edges:a=a.fillet(s['edge_radius'],edges).clean()
    # 창을 가진 상하 사선 거싯. 삽입 통로와 모터 캔에서 떨어진 양쪽 가장자리에 배치.
    rd=s['rib_depth'];rt=s['rib_thickness']
    for x0 in (-w/2,w/2-rt):
        for sign in (-1,1):
            zroot=zi if sign==1 else bi
            rib=prism_yz([(0,0),(rd,zroot),(0,zroot)],x0,x0+rt)
            inner=prism_yz([(12,sign*26),(90,zroot-sign*16),(12,zroot-sign*16)],x0-1,x0+rt+1)
            parallel=[e for e in inner.Edges() if e.geomType()=='LINE' and abs(e.Center().x-(x0+rt/2))<1e-5]
            inner=inner.fillet(s['rib_window_radius'],parallel)
            if windows:rib=rib.cut(inner)
            a=a.fuse(rib)
    # ㄷ자 개구가 벌어지는 것을 억제하는 양쪽 연속 세로 기둥. 모터 삽입 공간은 가운데에 유지.
    for x0,x1 in [(-w/2,-w/2+s['edge_column_width']),(w/2-s['edge_column_width'],w/2)]:
        a=a.fuse(box(x0,x1,0,s['edge_column_depth'],bi,zi))
    a=a.clean()
    a=a.cut(cyl_y(s['bore_diameter']/2,yf-1,1))
    if windows:
        for x,z in s['face_window_centers']:
            void=round_xz(s['face_window_width'],s['face_window_height'],s['face_window_radius'],x,z,yf-1,1)
            for hand in ('L','R'):
                for hx,hz in holes(hand,p):void=void.cut(cyl_y(s['seat_outer_diameter']/2,yf-2,2,hx,hz))
            a=a.cut(void)
        cx,cy=s['roof_window_center'];void=round_xy(s['roof_window_width'],s['roof_window_depth'],8,cx,cy,zi-1,zt+1)
        for x,y in p['frame']['holes_xy']:void=void.cut(cyl_z(20,zi-2,zt+2,x,y))
        a=a.cut(void)
        cx,cy=s['floor_window_center'];void=round_xy(s['floor_window_width'],s['floor_window_depth'],8,cx,cy,zb-1,bi+1)
        for y in p['fit']['saddle_stations_y']:
            hw=p['fit']['saddle_axial_width']/2+1
            void=void.cut(box(-w,w,y-hw,y+hw,zb-2,bi+2))
        a=a.cut(void)
    # 플라스틱에는 압축제한 슬리브의 외경 홀, 볼트 구멍은 금속 슬리브 내부이다.
    for x,y in p['frame']['holes_xy']:
        a=a.cut(cyl_z(p['frame']['sleeve_host_bore']/2,zi-1,zt+1,x,y))
        a=a.cut(cyl_z(p['frame']['counterbore_diameter']/2,zi-1,zt-p['frame']['grip_at_bolt'],x,y))
    # 탈착 새들 측면 레일: 아래 면에 놓이며 상부 턱은 이탈만 제한한다.
    for sign in (-1,1):
        ro=p['cassette']['rail_outer_x'];lo,hi=(ro+.4,ro+6) if sign==1 else (-ro-6,-ro-.4)
        guide=box(lo,hi,30,142,bi-1,bi+11)
        lo,hi=(ro-1.5,ro+6) if sign==1 else (-ro-6,-ro+1.5)
        guide=guide.fuse(box(lo,hi,30,142,bi+7.5,bi+11))
        a=a.fuse(guide)
    # 전방 스톱. 삽입 때는 후방(+Y)만 열려 있다.
    for x in (-p['cassette']['rail_outer_x']+6,p['cassette']['rail_outer_x']-6):a=a.fuse(box(x-6,x+6,30,32.6,bi-1,bi+6.8))
    for x,y in p['cassette']['pin_centers_xy']:
        a=a.cut(cyl_z(p['cassette']['pin_bore']/2,zb-1,bi+1,x,y))
        a=a.cut(cyl_z(p['cassette']['pin_head_diameter_example']/2+.3,zb-1,zb+p['cassette']['pin_head_recess_depth'],x,y))
    return a.clean()

def saddle(side,p=P,windows=True):
    s=p['shell'];f=p['fit'];cx,cz=center(side,p);b=s['outer_bottom_z']+s['bottom_thickness'];h=f['saddle_top_relative_to_can_center']+cz
    out=[]
    for y in f['saddle_stations_y']:
        y0=y-f['saddle_axial_width']/2;y1=y+f['saddle_axial_width']/2
        q=box(cx-f['saddle_x_half_width'],cx+f['saddle_x_half_width'],y0,y1,b,h)
        q=q.cut(cyl_y(f['can_diameter_source']/2+f['saddle_radial_gap_DEMO'],y0-1,y1+1,cx,cz))
        # 높이가 큰 반전측 받침은 속을 채우는 대신 아치형 관통창을 남긴다.
        if windows and cz>0:
            q=q.cut(round_xz(52,38,6,cx,-58,y0-1,y1+1))
        out.append(q)
    return out

def cassette(side,p=P,windows=True):
    """본체와 별도로 출력되는 새들 카세트. 2개 무나사 잠금핀으로 후방 이탈 방지."""
    c=p['cassette'];cx,cz=center(side,p);f=p['fit'];z=c['base_z'];parts=saddle(side,p,windows)
    for x0,x1 in [(-c['rail_outer_x'],-c['rail_inner_x']),(c['rail_inner_x'],c['rail_outer_x'])]:
        parts.append(box(x0,x1,c['rail_front_y'],c['rail_rear_y'],z,c['rail_top_z']))
    for y in f['saddle_stations_y']:
        b=box(-c['rail_outer_x'],c['rail_outer_x'],y-9,y+9,z,z+6)
        b=b.cut(cyl_y(f['can_diameter_source']/2+f['saddle_radial_gap_DEMO'],y-10,y+10,cx,cz))
        parts.append(b)
    a=parts[0]
    for q in parts[1:]:a=a.fuse(q)
    for x,y in c['pin_centers_xy']:a=a.cut(cyl_z(c['pin_bore']/2,z-1,z+9,x,y))
    a=a.clean()
    if not a.isValid() or len(a.Solids())!=1:raise ValueError(side+' 카세트 연결 오류')
    return ensure_print_volume(a,p)

def bonded_analysis(side,p=P):
    """실제 접촉 대신 완전 결합한 비교해석용 단일체. 출력/가공용 부품 아님."""
    a=make_bracket(side,p).fuse(cassette(side,p)).clean()
    if not a.isValid() or len(a.Solids())!=1:raise ValueError('결합 해석체 연결 오류')
    return a

def liner(side,p=P):
    """명목 0.4 mm 하부 맞춤 라이너. 실제 재료·두께·접촉 구역 승인 전."""
    cx,cz=center(side,p);f=p['fit'];r=f['can_diameter_source']/2;gap=f['saddle_radial_gap_DEMO'];out=[]
    for y in f['saddle_stations_y']:
        q=cyl_y(r+gap,y-9,y+9,cx,cz).cut(cyl_y(r,y-10,y+10,cx,cz))
        q=q.intersect(box(cx-43,cx+43,y-9,y+9,cz-r-gap,cz-28)).clean()
        out.append(q)
    return out

def make_bracket(side,p=P,windows=True,with_saddle=False):
    s=p['shell'];m=p['motor'];h=holes(side,p)
    a=common_shell(p,windows)
    # 돌출 커버를 위한 안쪽 얕은 포켓. 모터 귀 접촉 패드는 삭제하지 않는다.
    pocket=cyl_y(s['face_recess_diameter']/2,-s['face_recess_depth'],1)
    for x,z in h:pocket=pocket.cut(cyl_y(s['seat_outer_diameter']/2,-s['face_recess_depth']-1,2,x,z))
    a=a.cut(pocket)
    if with_saddle:a=a.fuse(cassette(side,p,windows))
    for x,z in h:
        a=a.cut(cyl_y(m['sleeve_host_bore']/2,-s['face_thickness']-1,1,x,z))
        # 30 mm M6를 유지: 두꺼운 면판의 볼트부만 9 mm 유효 물림 두께로 만든다.
        a=a.cut(cyl_y(m['counterbore_diameter']/2,-s['face_thickness']-1,-m['grip_at_bolt'],x,z))
    a=a.clean()
    # 중요 좌면을 피하고 중심 구멍 바깥/안쪽 입구만 R1 처리.
    ee=[]
    for e in a.Edges():
        if e.geomType()=='CIRCLE':
            try:
                if abs(e.radius()-s['bore_diameter']/2)<1e-4:ee.append(e)
            except ValueError:pass
    if ee:a=a.fillet(1.,ee).clean()
    if not a.isValid() or len(a.Solids())!=1: raise ValueError(side+' 브래킷이 유효한 단일 솔리드가 아님')
    return ensure_print_volume(a,p)

def sleeve(od,id,length,axis='Y'):
    a=cyl_y(od/2,-length,0).cut(cyl_y(id/2,-length-1,1)) if axis=='Y' else cyl_z(od/2,0,length).cut(cyl_z(id/2,-1,length+1))
    return a.clean()

def motor_proxy(side,p=P):
    """실측 모델이 아닌 간섭 검토용 대리 외형. 사진을 재측정해 수치화하지 않는다."""
    f=p['fit'];m=p['motor'];cx,cz=center(side,p)
    can=cyl_y(f['can_diameter_source']/2,f['can_y_start_DEMO'],f['can_y_end_DEMO'],cx,cz)
    rear=cyl_y(f['can_diameter_source']/2-1,f['can_y_end_DEMO'],f['rear_end_y_DEMO'],cx,cz)
    a=math.radians(m['clocking_deg'][side]);co,si=math.cos(a),math.sin(a)
    def pt(x,z):return (co*x-si*z,si*x+co*z)
    poly=[(-43,32),(-25,53),(8,58),(39,40),(57,8),(51,-27),(32,-61),(-20,-69),(-43,-28)]
    verts=[Vector(x,4,z) for x,z in [pt(x,z) for x,z in poly]]
    gear=cq.Solid.extrudeLinear(cq.Wire.makePolygon(verts+[verts[0]]),[],Vector(0,28,0))
    for x,z in holes(side,p):gear=gear.fuse(cyl_y(10,0,m['ear_thickness_example'],x,z))
    for x,z in holes(side,p):gear=gear.cut(cyl_y(m['source_mount_bore_diameter']/2,-1,m['ear_thickness_example']+1,x,z))
    boss=cyl_y(f['boss_diameter_DEMO']/2,-f['boss_projection_DEMO'],4)
    shaft=cyl_y(m['shaft_diameter_source']/2,-f['shaft_projection_from_pad_DEMO'],-f['boss_projection_DEMO'])
    return [('can',can),('rear',rear),('gear',gear.clean()),('boss',boss),('shaft',shaft)]

def positioned(shape,side,p=P):
    t=p['assembly']['pad_plane_separation_DEMO']/2
    return shape.rotate((0,0,0),(0,0,1),180).translate((0,t,0)) if side=='L' else shape.translate((0,-t,0))

def retention_pin(p=P):
    c=p['cassette'];z=p['shell']['outer_bottom_z']+c['pin_head_recess_depth']
    a=cyl_z(c['pin_diameter']/2,z,z+c['pin_length_example']).fuse(cyl_z(c['pin_head_diameter_example']/2,z-c['pin_head_height_example'],z))
    bore=cq.Solid.makeCylinder(c['pin_cross_bore_example']/2,8,Vector(-4,0,z+c['pin_length_example']-3),Vector(1,0,0))
    return a.cut(bore).clean()

def metal_parts(side,p=P):
    m=p['motor'];f=p['frame'];a=[]
    for i,(x,z) in enumerate(holes(side,p)):
        a.append((f'M6_Sleeve_{i+1}',sleeve(m['sleeve_od'],m['sleeve_id'],m['sleeve_length_example']).translate((x,-.05,z))))
    for i,(x,y) in enumerate(f['holes_xy']):
        a.append((f'M8_Sleeve_{i+1}',sleeve(f['sleeve_od'],f['sleeve_id'],f['sleeve_length_example'],'Z').translate((x,y,p['shell']['outer_top_z']-f['grip_at_bolt']+.05))))
    for i,(x,y) in enumerate(p['cassette']['pin_centers_xy']):a.append((f'Retention_Pin_{i+1}',retention_pin(p).translate((x,y,0))))
    return a

def props(a):
    bb,dims=exact_envelope(a);return {'valid':a.isValid(),'solids':len(a.Solids()),'volume_mm3':a.Volume(),'bounds':[bb[0],bb[3],bb[1],bb[4],bb[2],bb[5]],'size_mm':dims,'mass_kg_at_1_06':a.Volume()*1.06e-6}

