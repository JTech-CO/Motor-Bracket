#!/usr/bin/env python3
"""200 mm 출력 공간과 회전 배치한 실제 CAD 본체의 렌더링. 슬라이서 화면 아님."""
from geometry import ROOT,P,NAMES,box
import cadquery as cq
import vtk
from render_preview import actor,decorate

def main():
    q=cq.importers.importStep(str(ROOT/'cad/step/SCMB-G01-L.step')).val()
    q=q.rotate((0,0,0),(0,1,0),90).translate((90,37,98))
    ren=vtk.vtkRenderer();ren.SetBackground(1,1,1)
    ren.AddActor(actor(q,(.34,.44,.53)))
    ren.AddActor(actor(box(0,200,0,200,-2,0),(.83,.86,.88)))
    wire=vtk.vtkCubeSource();wire.SetBounds(0,200,0,200,0,200)
    mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(wire.GetOutputPort())
    a=vtk.vtkActor();a.SetMapper(mapper);a.GetProperty().SetRepresentationToWireframe();a.GetProperty().SetColor(.17,.46,.49);a.GetProperty().SetLineWidth(2.5);a.GetProperty().SetOpacity(.7);ren.AddActor(a)
    win=vtk.vtkRenderWindow();win.SetOffScreenRendering(True);win.SetSize(1500,1120);win.SetMultiSamples(4);win.AddRenderer(ren)
    cam=ren.GetActiveCamera();cam.ParallelProjectionOn();cam.SetPosition(425,-310,345);cam.SetFocalPoint(100,100,90);cam.SetViewUp(0,0,1);cam.SetParallelScale(183);ren.ResetCameraClippingRange();win.Render()
    image=vtk.vtkWindowToImageFilter();image.SetInput(win);image.ReadFrontBufferOff();image.Update()
    path=ROOT/'preview/Print-envelope-200mm.png';writer=vtk.vtkPNGWriter();writer.SetInputConnection(image.GetOutputPort());writer.SetFileName(str(path));writer.Write();win.Finalize()
    decorate(path,'200 × 200 × 200mm 공간 / 좌측 본체 출력 배치','배치 크기 180 × 162 × 196mm / 축척 100% / 본체 분할 없음','CAD 공간 검토 / 실제 서포트·슬라이싱·출력은 미검증')
if __name__=='__main__':main()
