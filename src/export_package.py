#!/usr/bin/env python3
"""단일부품/평탄 다중솔리드 STEP(AP203/AP214), 구버전 ASCII BREP, FCStd 호환 문서.
FreeCAD 앱을 대체하는 검증기가 아니다. 앱 내 재저장은 OPEN_IN_FREECAD.FCMacro가 담당한다.
"""
from pathlib import Path
import io,json,zipfile,uuid,math,xml.etree.ElementTree as ET
import cadquery as cq
from OCP.BRepTools import BRepTools
from OCP.TopTools import TopTools_FormatVersion
from OCP.STEPControl import STEPControl_Writer,STEPControl_AsIs
from OCP.Interface import Interface_Static
from OCP.IFSelect import IFSelect_RetDone
from scipy.spatial.transform import Rotation
import numpy as np
from geometry import *

def brep_v1(shape):
    b=io.BytesIO();BRepTools.Write_s(shape.wrapped,b,False,False,TopTools_FormatVersion.TopTools_FormatVersion_VERSION_1)
    return b.getvalue()

def export_step(shape,path,schema='AP203'):
    # STEPControl 초기화 후 매번 스키마/단위를 지정한다. 계층 조립 변환은 사용하지 않는다.
    writer=STEPControl_Writer()
    Interface_Static.SetCVal_s('write.step.schema',schema)
    Interface_Static.SetCVal_s('write.step.unit','MM')
    Interface_Static.SetIVal_s('write.step.assembly',0)
    assert writer.Transfer(shape.wrapped,STEPControl_AsIs)==IFSelect_RetDone
    assert writer.Write(str(path))==IFSelect_RetDone
    raw=path.read_bytes();assert raw.startswith(b'ISO-10303-21;') and b'MANIFOLD_SOLID_BREP' in raw and max(raw)<128
    recovered=cq.importers.importStep(str(path)).val()
    assert recovered.isValid() and len(recovered.Solids())==len(shape.Solids())
    error=abs(recovered.Volume()-shape.Volume())/shape.Volume()
    assert error<1e-6
    return {'file':str(path.relative_to(ROOT)),'schema':schema,'solids':len(recovered.Solids()),'volume_mm3':recovered.Volume(),'relative_volume_error':error,'product_count':raw.count(b'= PRODUCT('),'external_refs':raw.count(b'EXTERNALLY_DEFINED'),'ascii_only':True}

def prop(parent,n,ty,tag,**vals):
    q=ET.SubElement(parent,'Property',name=n,type=ty);ET.SubElement(q,tag,**{k:str(v) for k,v in vals.items()})

def pack_fcstd(path,items):
    """외부 직렬화 호환 문서. FreeCAD 네이티브 앱 저장/재열기 검증은 하지 않았다."""
    comp=cq.Compound.makeCompound([a for _,_,a,_ in items]);b=comp.BoundingBox()
    target=np.array([(b.xmin+b.xmax)/2,(b.ymin+b.ymax)/2,(b.zmin+b.zmax)/2]);di=np.array([1.,-1.5,.85]);di/=np.linalg.norm(di)
    r=np.cross([0,0,1],di);r/=np.linalg.norm(r);up=np.cross(di,r)
    rv=Rotation.from_matrix(np.column_stack([r,up,di])).as_rotvec();angle=float(np.linalg.norm(rv));axis=rv/angle
    height=max(b.xlen,b.ylen,b.zlen)*1.8;dist=height*4;pos=target+di*dist
    cam='OrthographicCamera {\n viewportMapping ADJUST_CAMERA\n position '+' '.join(f'{x:.12g}' for x in pos)+'\n orientation '+' '.join(f'{x:.12g}' for x in [*axis,angle])+f'\n nearDistance 0.1\n farDistance {dist*3:.12g}\n aspectRatio 1\n focalDistance {dist:.12g}\n height {height:.12g}\n}}\n'
    d=ET.Element('Document',SchemaVersion='4',ProgramVersion='0.21R0',FileVersion='1')
    pr=ET.SubElement(d,'Properties',Count='5')
    for k,v in {'Label':path.stem,'Comment':'외부 직렬화 호환 FCStd / 네이티브 앱 저장 아님. 빈 화면이면 루트 OPEN_IN_FREECAD.FCMacro로 BREP를 직접 읽고 네이티브 재저장.','CreatedBy':'SCMB 외부 CAD 내보내기','Id':str(uuid.uuid4()),'Company':'JTech-CO'}.items():prop(pr,k,'App::PropertyString','String',value=v)
    ob=ET.SubElement(d,'Objects',Count=str(len(items)));od=ET.SubElement(d,'ObjectData',Count=str(len(items)))
    gui=ET.Element('Document',SchemaVersion='1');view=ET.SubElement(gui,'ViewProviderData',Count=str(len(items)))
    files={}
    for i,(name,label,shape,col) in enumerate(items,1):
        ET.SubElement(ob,'Object',type='Part::Feature',name=name,id=str(i))
        item=ET.SubElement(od,'Object',name=name);pr=ET.SubElement(item,'Properties',Count='3')
        prop(pr,'Label','App::PropertyString','String',value=label)
        prop(pr,'Placement','App::PropertyPlacement','PropertyPlacement',Px=0,Py=0,Pz=0,Q0=0,Q1=0,Q2=0,Q3=1)
        prop(pr,'Shape','Part::PropertyPartShape','Part',file=name+'.brp')
        v=ET.SubElement(view,'ViewProvider',name=name,expanded='0');vp=ET.SubElement(v,'Properties',Count='3')
        c=[int(a*255) for a in col];prop(vp,'ShapeColor','App::PropertyColor','PropertyColor',value=c[0]<<24|c[1]<<16|c[2]<<8)
        prop(vp,'Visibility','App::PropertyBool','Bool',value='true')
        prop(vp,'LineWidth','App::PropertyFloat','Float',value=1.0)
        files[name+'.brp']=brep_v1(shape)
    ET.SubElement(gui,'Camera',settings=cam)
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for name,xml in [('Document.xml',d),('GuiDocument.xml',gui)]:
            ET.indent(xml);z.writestr(name,ET.tostring(xml,encoding='utf-8',xml_declaration=True))
        for n,bts in files.items():z.writestr(n,bts)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for _,bts in files.items():
            s=cq.Shape.importBrep(io.BytesIO(bts));assert s.isValid() and len(s.Solids())>=1
    return {'file':str(path.relative_to(ROOT)),'objects':len(items),'solids':len(comp.Solids()),'brep_version':1,'xml_zip_and_brep_checked':True,'native_app_saved':False,'native_app_open_test':False}

def main():
    meta={};record=[];fcrecord=[];specs={};gray=(.32,.4,.48);teal=(.4,.52,.54);metal=(.65,.67,.69)
    for hand in ('L','R'):
        body=make_bracket(hand);seat=cassette(hand)
        items=[('Shell',hand+' ㄷ자 본체',body,gray),('Saddle',hand+' 탈착 받침',seat,teal)]
        for number,(shape,name,label) in enumerate([(body,NAMES[hand],hand+' ㄷ자 본체'),(seat,f'SCMB-G03-{hand}',hand+' 탈착 받침')]):
            specs[name]=[(name.replace('-','_'),label,shape,gray if number==0 else teal)]
            cq.exporters.export(shape,str(ROOT/'print'/f'{name}.stl'),tolerance=.12,angularTolerance=.1)
            meta[name]=props(shape)
        for n,q in metal_parts(hand):items.append((n,n+' 금속 참고',q,metal))
        specs[f'SCMB-G10-{hand}']=items
        specs[f'SCMB-G20-{hand}-MOTOR-DEMO']=items+[(n,'모터 '+n+' / 대리형상',q,metal) for n,q in motor_proxy(hand)]
    specs['00-CAD-TEST-CUBE']=[('Cube','10mm 진단 큐브',box(0,10,0,10,0,10),gray)]
    specs['SCMB-G02-M6']=[('Sleeve','M6 금속 슬리브 / 길이 검토',sleeve(10,6.6,8.9),metal)]
    specs['SCMB-G02-M8']=[('Sleeve','M8 금속 슬리브 / 길이 검토',sleeve(12,9,11.9,'Z'),metal)]
    specs['SCMB-G05-PIN']=[('Pin','매립식 금속 잠금핀 / 공급품 확인',retention_pin(),metal)]
    items=[]
    for hand in ('L','R'):
        for n,l,q,c in specs[f'SCMB-G20-{hand}-MOTOR-DEMO']:items.append((hand+'_'+n,hand+' '+l,positioned(q,hand),c))
    specs['SCMB-G00-PAIR-DEMO']=items
    assembly=[];manifest=[]
    for name,items in specs.items():
        shape=items[0][2] if len(items)==1 else cq.Compound.makeCompound([a for _,_,a,_ in items])
        for schema,path in [('AP203',ROOT/'cad/step'/f'{name}.step'),('AP214IS',ROOT/'compatibility/AP214'/f'{name}.step')]:record.append(export_step(shape,path,schema))
        (ROOT/'cad/brep'/f'{name}.brep').write_bytes(brep_v1(shape))
        fcrecord.append(pack_fcstd(ROOT/'cad/freecad'/f'{name}.FCStd',items))
        manifest.append({'name':name,'label':items[0][1] if len(items)==1 else name+' / 검토조립','brep':f'cad/brep/{name}.brep','step':f'cad/step/{name}.step','expected_solids':len(shape.Solids()),'expected_volume_mm3':shape.Volume()})
    # 최초 열기는 부품 1개를 우선한다. 조립은 회전 링크 없는 평탄 다중솔리드.
    (ROOT/'data/import_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'qa/step_roundtrip.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'qa/fcstd_container.json').write_text(json.dumps(fcrecord,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'qa/geometry.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
    for hand in ['L','R']:
        whole=cq.Compound.makeCompound([a for _,_,a,_ in specs[f'SCMB-G10-{hand}']])
        for view,axis in [('Front',(0,-1,0)),('Side',(1,0,0)),('Top',(0,0,1)),('Iso',(1,-1,.7))]:
            cq.exporters.export(whole,str(ROOT/'drawings'/f'{hand}-{view}.svg'),opt={'projectionDir':axis,'showHidden':False,'width':900,'height':800,'strokeWidth':.5})
    print(json.dumps(meta,ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':main()
