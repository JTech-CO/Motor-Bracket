#!/usr/bin/env python3
"""OCCT 솔리드를 VTK로 렌더링. FreeCAD/SolidWorks 앱 화면은 아님."""
from geometry import *
import vtk
from PIL import Image,ImageDraw,ImageFont
from font_paths import korean_font
FONT=korean_font();BOLD=korean_font(True)

def actor(s,color):
    v,f=s.tessellate(.14,.12);p=vtk.vtkPoints();c=vtk.vtkCellArray()
    for a in v:p.InsertNextPoint(a.x,a.y,a.z)
    for inds in f:
        c.InsertNextCell(3)
        for i in inds:c.InsertCellPoint(i)
    mesh=vtk.vtkPolyData();mesh.SetPoints(p);mesh.SetPolys(c)
    n=vtk.vtkPolyDataNormals();n.SetInputData(mesh);n.SetFeatureAngle(40);n.Update()
    m=vtk.vtkPolyDataMapper();m.SetInputData(n.GetOutput());a=vtk.vtkActor();a.SetMapper(m);a.GetProperty().SetColor(*color);a.GetProperty().SetAmbient(.25);a.GetProperty().SetDiffuse(.72);a.GetProperty().SetSpecular(.15);return a

def render(file,items,pos,target,scale,size=(1800,1150)):
    r=vtk.vtkRenderer();r.SetBackground(1,1,1)
    for a,c in items:r.AddActor(actor(a,c))
    w=vtk.vtkRenderWindow();w.SetOffScreenRendering(True);w.SetSize(*size);w.SetMultiSamples(4);w.AddRenderer(r)
    cam=r.GetActiveCamera();cam.ParallelProjectionOn();cam.SetPosition(*pos);cam.SetFocalPoint(*target);cam.SetViewUp(0,0,1);cam.SetParallelScale(scale);r.ResetCameraClippingRange();w.Render()
    im=vtk.vtkWindowToImageFilter();im.SetInput(w);im.ReadFrontBufferOff();im.Update();wr=vtk.vtkPNGWriter();wr.SetInputConnection(im.GetOutputPort());wr.SetFileName(str(file));wr.Write();w.Finalize()

def decorate(file,title,sub,foot):
    im=Image.open(file).convert('RGB');out=Image.new('RGB',(im.width,im.height+205),'white');out.paste(im,(0,145));d=ImageDraw.Draw(out)
    d.text((45,25),title,font=ImageFont.truetype(BOLD,36),fill='#20303c');d.text((47,83),sub,font=ImageFont.truetype(FONT,24),fill='#53616b');d.text((47,out.height-47),foot,font=ImageFont.truetype(FONT,23),fill='#895622');out.save(file)

def ground_diagram():
    im=Image.new('RGB',(1800,930),'white');d=ImageDraw.Draw(im);bf=ImageFont.truetype(BOLD,30);f=ImageFont.truetype(FONT,24)
    d.text((50,25),'8인치 명목 바퀴 / 출력축 기준 지상고 비교',font=ImageFont.truetype(BOLD,37),fill='#20303c')
    k=2.25;zc=405;r=101.6*k;ground=zc+r
    for cx,low,lab in [(445,-102,'Rev E / 핀 최하단 -102mm'),(1335,-80,'Rev G / 최하단 -80mm')]:
        d.text((cx-325,100),lab,font=bf,fill='#20303c')
        d.ellipse((cx-r,zc-r,cx+r,zc+r),outline='#7a858d',width=5)
        # 측면 C 단면. 오른쪽으로 열린 통로.
        x0=cx-182;x1=cx+182;zt=zc-100*k;zb=zc-(-low)*(-k)
        # 좌표: 화면 아래 = -Z
        zb=zc-low*k
        top=16*k;bottom=(16 if low==-102 else 12)*k
        shellbottom=zc+(100 if low==-102 else 80)*k
        d.rectangle((x0,zt,x0+18*k,shellbottom),fill='#536a7c')
        d.rectangle((x0,zt,x1,zt+top),fill='#536a7c')
        d.rectangle((x0,shellbottom-bottom,x1,shellbottom),fill='#536a7c')
        if low==-102:d.rectangle((x1-40,shellbottom,x1-25,zb),fill='#ad4b30')
        d.line((cx-280,ground,cx+280,ground),fill='#303a40',width=3)
        d.line((cx-270,zc,cx+270,zc),fill='#89959c',width=2)
        d.ellipse((cx-7,zc-7,cx+7,zc+7),fill='#253d4c')
        d.text((cx-95,zc+12),'출력축 Z=0',font=f,fill='#253d4c')
        clearance=101.6+low
        d.text((cx-250,710),f'명목 지상고: {clearance:.1f}mm',font=bf,fill='#ad4b30' if low==-102 else '#245f67')
        d.text((cx-320,765),'바퀴 반지름 101.6mm - 축 아래 최하단 거리',font=f,fill='#53616b')
    d.text((50,855),'단면 개념도 / 하중에 의한 타이어 눌림·브래킷 변형·요철 여유는 별도 차감해야 함.',font=f,fill='#895622');im.save(ROOT/'preview/Ground-clearance.png')

if __name__=='__main__':
    gray=(.31,.39,.46);seatcol=(.41,.55,.56);metal=(.64,.67,.69)
    items=[]
    for hand in ['L','R']:
        body=cq.importers.importStep(str(ROOT/'cad/step'/f'{NAMES[hand]}.step')).val();seat=cassette(hand)
        local=[(body,gray),(seat,seatcol)]
        path=ROOT/'preview'/f'{hand}-Bracket.png';render(path,local,(330,520,270),(0,65,0),145,(1100,950));decorate(path,hand+' / 200mm 프린터 대응 ㄷ자 본체','196 × 162 × 180mm / 상판16 · 측판18 · 하판12mm','가상 편심 기준 설계 / 장착·하중 승인 전')
        local += [(q,metal if n!='can' else (.35,.36,.38)) for n,q in motor_proxy(hand)]
        path=ROOT/'preview'/f'{hand}-Motor.png';render(path,local,(350,560,290),(0,65,10),150,(1100,950));decorate(path,hand+' / 수평 편심 모터 배치',f"원본 자세에서 {P['motor']['clocking_deg'][hand]:g}도 / 실물 편심 입력 필요",'모터 외곽은 대리형상이며 실측 모델이 아님')
        for q,c in local:items.append((positioned(q,hand),c))
        wheel=cyl_y(101.6,-58,-28).cut(cyl_y(8.8,-59,-27));items.append((positioned(wheel,hand),(.16,.19,.21)))
    path=ROOT/'preview/SCMB-RevG-8inch.png';render(path,items,(850,-950,560),(0,0,0),290);decorate(path,'Rev G / 196mm 컴팩트 본체 · 200mm 프린터 대응','좌우 별도 부품 / M8×40 · M6×30 각 4개 / 8인치 지상고 21.6mm 유지','VTK CAD 렌더링 / 실제 CAD 앱 화면·실물 장착 승인 아님')
    ground_diagram();print('렌더링 완료')
