#!/usr/bin/env python3
"""한국어 검토도면·설명서·1:1 장착 템플릿. 원본 공급원 도면은 수정하지 않는다."""
from pathlib import Path
import json,math
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3,A4,landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image
from reportlab.lib.styles import ParagraphStyle
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
from font_paths import korean_font
from geometry import ROOT,P,holes,center
pdfmetrics.registerFont(TTFont('KR',korean_font()));pdfmetrics.registerFont(TTFont('KRB',korean_font(True)))
INK=colors.HexColor('#223440');MUTED=colors.HexColor('#536572');LINE=colors.HexColor('#b9c3cb');WARN=colors.HexColor('#8b4d26')

def text(c,x,y,s,size=11,bold=False,col=INK):
    c.setFillColor(col);c.setFont('KRB' if bold else 'KR',size);c.drawString(x,y,str(s).replace('−','-'))

def para(c,s,x,y,w,size=11,col=INK):
    st=ParagraphStyle('p',fontName='KR',fontSize=size,leading=size*1.5,textColor=col,wordWrap='CJK');p=Paragraph(s.replace('−','-'),st);_,h=p.wrap(w,900);p.drawOn(c,x,y-h);return y-h

def tab(c,rows,x,y,widths,size=10.5):
    st=ParagraphStyle('t',fontName='KR',fontSize=size,leading=size*1.35,wordWrap='CJK');data=[[Paragraph(str(v),st) for v in row] for row in rows]
    t=Table(data,colWidths=widths,hAlign='LEFT');t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8edf0')),('GRID',(0,0),(-1,-1),.45,LINE),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]));_,h=t.wrap(sum(widths),900);t.drawOn(c,x,y-h);return y-h

def header(c,title,page,total,w,h):
    c.setStrokeColor(INK);c.setLineWidth(.7);c.rect(12*mm,12*mm,w-24*mm,h-24*mm)
    text(c,18*mm,h-25*mm,title,18,True)
    text(c,18*mm,h-33*mm,'SCMB / Rev G · 0.7.0 / 2026-10-01 / mm / 장착·구조·앱별 최종 승인 전',10)
    c.line(12*mm,h-38*mm,w-12*mm,h-38*mm)
    text(c,18*mm,18*mm,'검토용 · 도면의 미실측 대리값을 제조 확정값으로 사용하지 말 것',9,col=WARN)
    c.setFont('KR',9);c.drawRightString(w-18*mm,18*mm,f'{page} / {total}')

def svg(c,path,x,y,w,h):
    d=svg2rlg(str(path));scale=min(w/d.width,h/d.height);d.scale(scale,scale);renderPDF.draw(d,c,x+(w-d.width*scale)/2,y+(h-d.height*scale)/2)

def raster(c,path,x,y,w,h):c.drawImage(str(path),x,y,width=w,height=h,preserveAspectRatio=True,anchor='c',mask='auto')

def dim(c,x1,y1,x2,y2,label):
    c.setStrokeColor(MUTED);c.setLineWidth(.55);c.line(x1,y1,x2,y2)
    if abs(y2-y1)<.01:
        for x in [x1,x2]:c.line(x,y1-4,x,y1+4)
        c.setFont('KR',10);c.drawCentredString((x1+x2)/2,y1+5,label)
    else:
        for y in [y1,y2]:c.line(x1-4,y,x1+4,y)
        text(c,x1+6,(y1+y2)/2,label,10)

def engineering():
    w,h=landscape(A3);c=canvas.Canvas(str(ROOT/'drawings/설계도면.pdf'),pagesize=(w,h))
    c.setTitle('Rev G / 196 mm 컴팩트 본체와 200 mm 출력 공간')
    header(c,'01 / 좌우 단일 본체 · 200mm 프린터 대응',1,4,w,h)
    svg(c,ROOT/'drawings/L-Iso.svg',16*mm,102*mm,182*mm,141*mm)
    svg(c,ROOT/'drawings/R-Iso.svg',211*mm,102*mm,182*mm,141*mm)
    text(c,20*mm,246*mm,'좌측 / SCMB-G01-L + SCMB-G03-L',13,True)
    text(c,218*mm,246*mm,'우측 / SCMB-G01-R + SCMB-G03-R',13,True)
    rows=[['항목','Rev G','유지 조건'],['본체 외곽','196 × 162 × 180mm','212mm에서 폭만16mm 감소 / 분할 없음'],['상판 / 측판 / 하판 / 거싯','16 / 18 / 12 / 8mm','볼트 자리 유효 두께12 / 9mm 유지'],['출력축·지상고','O=(0,0,0) / 중앙 개구 Ø54','상면Z=100, 최하단Z=-80 / 8인치 명목지상고21.6mm'],['모터 배치','L -45° / R 135°','원본 공급원 좌표와 대리 편심 기반 / 실물 실측 대기']]
    tab(c,rows,18*mm,101*mm,[64*mm,118*mm,202*mm],10.5)
    c.showPage();header(c,'02 / 실제 출력 배치와 부품별 크기',2,4,w,h)
    raster(c,ROOT/'preview/Print-envelope-200mm.png',18*mm,48*mm,218*mm,201*mm)
    tab(c,[['항목','공간 (mm)'],['학교 프린터 상한','200 × 200 × 200'],['본체 원래 방향','196 × 162 × 180'],['본체 회전 출력 배치','180 × 162 × 196'],['5mm 브림 외접영역 예시','190 × 172 / 높이196'],['받침 별도 출력','176 × 105 × 41.430'],['출력 위치 / 축척','XY 배드 중앙 / Z=0 / 100%']],246*mm,239*mm,[55*mm,100*mm],10.5)
    para(c,'본체 BED STL의 좌표: X10~190 / Y19~181 / Z0~196mm. 한 번에 한 개씩 출력. 5mm 브림은 영역 계산 예시이며 실제 접착 조건은 학교 장비·재료 프로필로 결정한다.',246*mm,143*mm,154*mm,10.5)
    para(c,'서포트·스커트·퍼지라인·래프트를 포함한 최종 툴패스는 미검증이다. 출력물 형상이200mm 이내라는 사실과 실제 슬라이싱 완료는 다르다. 전체 축소로 공간을 맞추면 M8/M6 홀과 모터 맞춤이 바뀌므로 금지한다.',246*mm,104*mm,154*mm,10.5)
    para(c,'측면으로 눕힌 배치는 체적 적합성을 위한 방향이다. 층간강도·서포트는 별도로 검토한다. 출력품 내부100% 채움은 슬라이서에서 설정한다.',246*mm,61*mm,154*mm,10.5)
    c.showPage();header(c,'03 / 모터 홀과 차체 체결 규격 유지',3,4,w,h)
    for hand,cx in [('L',78*mm),('R',220*mm)]:
        cy=175*mm;scale=1.22*mm;c.setStrokeColor(INK);c.setLineWidth(.8);c.circle(cx,cy,27*scale)
        c.setDash(5,3);c.line(cx-70*scale,cy,cx+70*scale,cy);c.line(cx,cy-68*scale,cx,cy+68*scale);c.setDash()
        text(c,cx-60*mm,249*mm,hand+' / 출력축 정면 · 중심 O',12,True)
        for i,(x,z) in enumerate(holes(hand),1):
            a,b=cx+x*scale,cy+z*scale;c.circle(a,b,5.1*scale);c.line(a-3,b,a+3,b);c.line(a,b-3,a,b+3);text(c,a+7,b+2,'H'+str(i),9)
        text(c,cx-30*mm,94*mm,'4 × Ø10.2 슬리브 수용홀',10)
    rows=[['홀','좌측 X, Z(mm)','우측 X, Z(mm)']]+[[f'H{i}',f'{a[0]:+.3f}, {a[1]:+.3f}',f'{b[0]:+.3f}, {b[1]:+.3f}'] for i,(a,b) in enumerate(zip(holes('L'),holes('R')),1)]
    tab(c,rows,287*mm,235*mm,[18*mm,48*mm,48*mm],10)
    para(c,'Ø10.2는 금속 슬리브 외경 수용홀이다. 내부 Ø6.6에 M6×30 사용. 본체 폭 변경 전후 홀 중심은 동일하다. 모터의 실제 귀 두께·나사 접근은 여전히 실측 확인 대상이다.',287*mm,156*mm,111*mm,10.5)
    tab(c,[['체결','본체 수용홀 / 금속부','규격'],['차체 상판','4 × Ø12.2 / 슬리브 ID Ø9.0','M8×40 4개 / 중심 간격90×100mm'],['모터 측판','4 × Ø10.2 / 슬리브 ID Ø6.6','M6×30 4개 / 유효 두께9mm'],['잠금핀','2 × Ø4.2 / 머리 포켓 Ø7.6 × 2.2','X=±82, Y=132 / D4 무나사핀2개/측']],18*mm,82*mm,[55*mm,149*mm,180*mm],10.5)
    c.showPage();header(c,'04 / 상면·측면 및 국소 폭 변경',4,4,w,h)
    svg(c,ROOT/'drawings/L-Top.svg',18*mm,107*mm,182*mm,131*mm)
    svg(c,ROOT/'drawings/L-Side.svg',211*mm,107*mm,183*mm,131*mm)
    text(c,20*mm,246*mm,'상면 / 폭196mm · M8 피치90×100mm',12,True)
    text(c,214*mm,246*mm,'측면 / 깊이162mm · 높이180mm',12,True)
    rows=[['부위','Rev F → Rev G / 단위mm'],['경량화 창','상·하판 폭170→154 / 전면 창 중심X ±78→±70 / 전면 창38×32 유지'],['레일·잠금핀','레일 외측±96→±88, 내측±84→±76 / 핀 중심±90→±82'],['전방 기둥','두께12 유지 / 깊이30→28 / 대리 모터 앞끝Y=30과의 공간 확보'],['모터캔-본체 최소 간격','대리형상 기준 약1.699 / 실제 외경·편심·돌출·케이블에 대한 맞춤 보증 아님'],['기준·한계','상판Z=100, 바닥Z=-80 유지 / 새 구조FEA·실물출력·하중시험은 미실시']]
    tab(c,rows,18*mm,100*mm,[59*mm,325*mm],10.5)
    c.save()

def reports():
    q=json.loads((ROOT/'qa/print_envelope.json').read_text());g=json.loads((ROOT/'qa/design_checks.json').read_text())
    mass=sum(r['mass_kg_density1_06'] for r in q['printable_parts'])
    st=ParagraphStyle('body',fontName='KR',fontSize=10.5,leading=16,wordWrap='CJK',textColor=INK,spaceAfter=8)
    h1=ParagraphStyle('h1',parent=st,fontName='KRB',fontSize=18,leading=25,spaceAfter=14)
    h2=ParagraphStyle('h2',parent=st,fontName='KRB',fontSize=12.5,leading=18,spaceBefore=10,spaceAfter=7)
    story=[]
    def p(s):story.append(Paragraph(s,st))
    def title(s):story.append(Paragraph(s,h1))
    def heading(s):story.append(Paragraph(s,h2))
    def table(rows,widths):
        t=Table([[Paragraph(str(v),st)for v in row] for row in rows],colWidths=widths)
        t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.4,LINE),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8edf0')),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),4)]));story.append(t);story.append(Spacer(1,11))
    title('Rev G / 200mm 프린터 대응 수정')
    p('스마트카트 모터 브래킷 · 0.7.0 · 2026-10-01<br/>좌우 단일 본체196×162×180mm / 기능 치수 유지 / 제작 검토본')
    heading('1. 전체 비율이 아닌 외곽 폭만 줄임')
    p('학교 프린터 상한200×200×200mm를 기준으로 외곽 폭212mm를196mm로 조정했다. 각 본체를 별도 파트로 분할하지 않는다. 전체 모델을196/212 비율로 축소하지 않고 측면 구조와 경량화 창·받침 레일을 국소적으로 이동했다.')
    table([['항목','Rev F','Rev G'],['본체 외곽(mm)','212×162×180','196×162×180'],['레일 전체 폭(mm)','192','176'],['핀 중심X(mm)','±90','±82'],['상·하판 창 폭(mm)','170','154'],['전방 기둥 깊이(mm)','30','28']],[58*mm,54*mm,56*mm])
    p('상판16 / 측판18 / 하판12 / 거싯8mm와 루트R10을 유지했다. 앞쪽 기둥 두께12mm도 유지하고 깊이를2mm 줄여 대리 모터의 Y=30 앞끝과의 공간을 확보했다. 이번 국소 변경이 강도 유지의 검증을 의미하지는 않는다.')
    p(f'기존 밀도1.06g/cm³를 그대로 사용한 CAD 플라스틱 질량은 좌우 합계 {mass:.3f}kg이다. Rev F 약2.800kg 대비 약0.189kg 감소했다. 모터·금속부·서포트·브림·출력 오차를 제외한다.')
    p('기준 저장소: JTech-CO/Motor-Bracket, 커밋4792da580a78f302c24412488b0d653e7083863d의 Rev F. geometry.py의 Git blob SHA를 대조한 후 소스를 수정했다. 원격 저장소 수정이나 발주는 하지 않았다.')
    story.append(PageBreak());title('2. 출력 배치와 슬라이서 설정')
    table([['출력 파일','배치 크기(mm)','수량'],['SCMB-G01-L-BED.stl','180×162×196','1'],['SCMB-G01-R-BED.stl','180×162×196','1'],['SCMB-G03-L-BED.stl','176×105×41.430','1'],['SCMB-G03-R-BED.stl','176×105×41.430','1']],[87*mm,61*mm,20*mm])
    p('print/bed_ready의 본체 파일은 측면을 바닥으로 +Y축90° 회전하고 XY 중앙·Z0으로 옮긴 STL이다. 축척은100%이며 스케일 변경이 아니다. 원래 방향 STL도196×162×180mm로200mm 큐브 안에 들어간다.')
    p('본체 배치 좌표는 X10~190 / Y19~181 / Z0~196mm이다. 5mm 브림을 가정하면 외접영역은190×172mm이고 높이는196mm로 유지된다. 이는 브림의 기하 공간 계산이며 학교 장비의 실제 G-code는 생성하지 않았다.')
    heading('실제 출력 전에 확인')
    p('한 작업에 본체 한 개씩 배치하고 mm·축척100%·내부채움100%를 사용한다. STL에는 채움률이 저장되지 않는다. 받침은 별도 작업이다. 모터·바퀴·금속부가 들어간 검토조립 STEP는 출력대상이 아니다.')
    p('슬라이서에서 서포트·브림·스커트·퍼지·래프트를 포함한 최종 툴패스가200mm 공간 안인지 확인한다. 학교 기종·클립 위치·제한구역·노즐·재료 프로필이 없어 실제 슬라이싱은 미검증이다. 래프트나 높이 보정을 추가하면 남은Z여유4mm를 초과하지 않는지 확인한다.')
    p('측면 출력 방향은 공간 적합성을 위한 배치다. 층간강도와 서포트 접촉을 검토한 출력조건을 사용한다. 5mm 브림을 접착력 확정값으로 취급하지 않는다. 장비가 재료의 건조·노즐·챔버 조건을 충족하는지도 확인한다.')
    p('브림 참고: Prusa 공식 “Skirt and Brim”은 첫 레이어의 접착면적을 늘리며 폭을 따로 지정하는 기능으로 설명한다. 이 설명은 학교 프린터 전용 설정을 제공하는 것은 아니다. 주소는data/sources.json에 있다.')
    story.append(PageBreak());title('3. 바퀴·체결 및 CAD 파일')
    table([['유지 항목','Rev G 값'],['차체 체결','M8×40mm 4개 / 중심 간격90×100mm'],['모터 체결','M6×30mm 4개 / 원본 공급원 패턴의 회전 좌표 유지'],['출력축 중심','좌우 동일 높이Z0 / 중앙 여유홀Ø54와 동심'],['하판 최하단 / 상판면','Z=-80 / Z=+100mm'],['8인치 명목 지상고','203.2/2 - 80 = 21.6mm'],['모터 상대 각도','L -45° / R135° / 차이180°']],[63*mm,105*mm])
    p('Ø54 개구는 축을 지지하는 베어링홀이 아니다. 바퀴허브·모터베어링 하중과 축물림은 별도 확인해야 한다. 21.6mm는 무하중 명목값으로 타이어 눌림과 구조 변형이 차감되기 전이다.')
    p('브래킷 M8/M6 자리는 각각 Ø12.2/Ø10.2 슬리브 수용홀이다. 금속 슬리브 ID는Ø9.0/Ø6.6이다. 볼트 유효 두께12/9mm를 유지했으나 모터 귀와 잠금너트·와셔 실측이 없으므로 M6×30의 길이 적합성과 체결토크는 확정 전이다.')
    heading('FreeCAD와 SolidWorks')
    p('cad/step은 각각 유효한 단일 솔리드 AP203을 제공한다. 대안 AP214는compatibility/AP214에 있다. SolidWorks는STEP를 가져와 직접 편집하거나 새 피처/해석을 추가하는 시작형상으로 사용한다. 고유SLDPRT/SLDASM/Simulation 프로젝트는 제공하지 않는다.')
    p('cad/freecad의 FCStd는 외부 직렬화한 Part::Feature 솔리드 문서이며 원시 스케치 이력이 아니다. 빈 화면이면 OPEN_IN_FREECAD.FCMacro로BREP를 직접 읽어 표시·네이티브 저장·재열기를 수행한다. 실제 앱 버전/결과는native_generated/app_report.json에 기록된다. 여기서는 앱/매크로 실행은 하지 않았다.')
    p('parameters.json·src/geometry.py가 재생성 원본이다. 전용 출력 한계 검사로200mm 초과 시 내보내기를 중단한다. 기존Rev F 본체/받침과 새Rev G를 혼용하지 않는다.')
    story.append(PageBreak());title('4. 검증 결과와 제작 승인 조건')
    table([['검사 항목','실행 결과'],['기하·연속200mm 삽입 경로',f"{g['검사수']}개 통과 / 명시된 대리형상 기준"],['출력공간·실제 홀축·회전배치',f"{q['check_count']}개 통과 / STEP·STL200mm 이내"],['STEP / FCStd','AP203·AP214 재읽기 / FCStd ZIP·XML·내장BREP 검사'],['학교 장비 슬라이싱·출력','미실시 / 실제 프로필·툴패스 미제공'],['CAD 앱 직접 실행','FreeCAD·SolidWorks 및 매크로 실행 미실시'],['새 형상 구조해석·하중시험','미실시 / 기존 개정의 응력·안전율 전용 금지']],[71*mm,97*mm])
    p('모터 캔 대리형상과 본체의 최소 거리는 약1.699mm다. 실제 모터 크기·도장·편심·배선이 다르면 달라진다. 0체적 간섭 및 양의 공차 여유는 실물 끼워맞춤 승인이 아니다.')
    p('첨부 모터자료의 5쪽은 D01 몸통 외경, E02 편심, L04 보스, M01 귀 두께와 접촉평면 등을 실측란으로 남긴다. 공급원Ø102·Ø17과4개 장착홀 좌표는 실측 공차 승인값이 아니다. 본 개정에서 외부 모터치수를 임의로 확정하지 않았다.')
    p('지지대 두께는 유지했지만 폭·레일·보강기둥 위치를 바꾸었으므로 구조 검증은 새 형상으로 수행한다. 실제 접촉, 적층이방성, 볼트 예압, 금속 슬리브, 크리프와 온도를 고려한다. 사람 탑승이나 고속 운행에 대한 승인을 포함하지 않는다.')
    p('참조PDF2개 및PNG1개는 reference/에 원본 그대로 보존했다. 다운로드 무결성은CHECK_FILES.py로 점검한다. 수치 결과는qa/와data/print_parts.csv에서 볼 수 있다. 한국어 README에 전체 재생성 순서가 있다.')
    def foot(c,d):
        c.setStrokeColor(LINE);c.line(20*mm,18*mm,190*mm,18*mm);text(c,20*mm,12*mm,'SCMB Rev G / 200mm 공간 검토본 / 실물·구조 승인 전',8,col=MUTED);c.setFont('KR',8);c.drawRightString(190*mm,12*mm,str(d.page))
    doc=SimpleDocTemplate(str(ROOT/'docs/수정설명서.pdf'),pagesize=A4,rightMargin=20*mm,leftMargin=20*mm,topMargin=19*mm,bottomMargin=23*mm)
    doc.build(story,onFirstPage=foot,onLaterPages=foot)

def templates():
    c=canvas.Canvas(str(ROOT/'drawings/Motor-LR-1to1-A4.pdf'),pagesize=A4)
    for page,hand in enumerate(['L','R'],1):
        header(c,f'{hand} / 모터 홀 중심 대조용 1:1',page,2,*A4)
        x0=105*mm;y0=164*mm;c.setStrokeColor(INK);c.circle(x0,y0,27*mm)
        c.setDash(4,3);c.line(35*mm,y0,175*mm,y0);c.line(x0,95*mm,x0,232*mm);c.setDash()
        for i,(x,z) in enumerate(holes(hand),1):
            a=x0+x*mm;b=y0+z*mm;c.circle(a,b,5.1*mm);c.setDash(2,2);c.circle(a,b,3.25*mm);c.setDash();c.line(a-4,b,a+4,b);c.line(a,b-4,a,b+4)
            text(c,a+7,b+3,f'H{i}',9)
        para(c,'실선 Ø10.2: 브래킷 슬리브 수용홀 / 점선 Ø6.5: 공급원 모터 귀 구멍. 현재 각도는 대리 편심 기준이다. 실제 모터에 맞추어 회전/접촉면을 먼저 대조한다.',22*mm,81*mm,166*mm,10)
        dim(c,50*mm,45*mm,150*mm,45*mm,'100mm 출력 교정선')
        text(c,26*mm,31*mm,'인쇄 100% · 페이지 맞춤 끄기 · 교정선을 실제 자로 확인',9,col=WARN)
        c.showPage()
    c.save()
    c=canvas.Canvas(str(ROOT/'drawings/Frame-90x100-1to1-A4.pdf'),pagesize=A4);header(c,'차체 90×100mm / 홀 중심 대조 1:1',1,1,*A4)
    x0=105*mm;y0=163*mm;c.setStrokeColor(INK)
    for x in [-45,45]:
        for y in [-50,50]:
            a=x0+x*mm;b=y0+y*mm;c.circle(a,b,6.1*mm);c.setDash(3,2);c.circle(a,b,12*mm);c.setDash();c.line(a-5,b,a+5,b);c.line(a,b-5,a,b+5)
    dim(c,x0-45*mm,y0-66*mm,x0+45*mm,y0-66*mm,'90mm');dim(c,x0+64*mm,y0-50*mm,x0+64*mm,y0+50*mm,'100mm')
    para(c,'실선 Ø12.2: 상판 슬리브 수용홀 / 점선 Ø24: 와셔 외경 예시. 실제 차체 장공의 최종 볼트 착좌점을 대조한다. 본체196×162mm 외곽은 이 홀 중심 대조도에 표시하지 않는다.',22*mm,77*mm,163*mm,10)
    dim(c,50*mm,45*mm,150*mm,45*mm,'100mm 출력 교정선');text(c,26*mm,31*mm,'인쇄 100% · 페이지 맞춤 끄기 · 교정선을 실제 자로 확인',9,col=WARN);c.save()


if __name__=='__main__':
    engineering();reports();templates();print('PDF4종 생성 완료')
