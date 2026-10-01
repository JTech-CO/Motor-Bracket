#!/usr/bin/env python3
"""Rev G의 실제 검사 결과에서 한국어 안내문과 재생성 목록을 작성."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]

def main():
    q=json.loads((ROOT/'qa/print_envelope.json').read_text())
    g=json.loads((ROOT/'qa/design_checks.json').read_text())
    mass=sum(r['mass_kg_density1_06'] for r in q['printable_parts'])
    body=q['printable_parts'][0]['mass_kg_density1_06'];seat=q['printable_parts'][1]['mass_kg_density1_06']
    clearance=min(r['can_to_shell_min_distance_mm'] for r in q['motor_clearance_proxy'])
    readme=f'''# 스마트카트 모터 브래킷 · Rev G / 0.7.0

학교 프린터의 **200 × 200 × 200 mm** 상한에 맞춘 폭 축소 개정. 본체는 **196 × 162 × 180 mm**, 좌우 각각 별도의 단일 솔리드이며 분할 접합 없이 한 개씩 출력함.

![200mm 출력 공간](preview/Print-envelope-200mm.png)

## 우선 사용할 파일

- 출력: `print/bed_ready/SCMB-G01-L-BED.stl`, `SCMB-G01-R-BED.stl` — 각각 1개. 배치 크기 **180 × 162 × 196 mm**.
- 받침: 같은 폴더의 `SCMB-G03-L-BED.stl`, `SCMB-G03-R-BED.stl` — 각각 1개. **176 × 105 × 41.430 mm**.
- SolidWorks: `cad/step/SCMB-G01-L.step` / `SCMB-G01-R.step`. 받침은 G03, 금속 참고부 포함 조립은 G10.
- FreeCAD: `cad/freecad/`의 같은 이름 FCStd. 빈 화면이면 루트 `OPEN_IN_FREECAD.FCMacro`로 BREP를 직접 가져와 네이티브 재저장.
- 도면: [설계도면](drawings/설계도면.pdf), [수정설명서](docs/수정설명서.pdf), 1:1 모터/차체 템플릿.

## Rev F 대비 변경

| 항목 | Rev F | Rev G |
|---|---:|---:|
| 본체 크기 | 212 × 162 × 180 | **196 × 162 × 180 mm** |
| 외곽 좌우 끝 | ±106 | ±98 mm |
| 상·하판 경량화 창 폭 | 170 | 154 mm |
| 전면 창의 좌우 중심 | ±78 | ±70 mm |
| 받침 레일 바깥/안쪽 좌표 | ±96 / ±84 | ±88 / ±76 mm |
| 핀 중심 X | ±90 | ±82 mm |
| 전방 모서리 기둥 깊이 | 30 | 28 mm |

단순 전체 축소를 하지 않음. 상판 M8×40 4개, 측면 M6×30 4개, 차체 중심간격90×100, 출력축 위치, 모터 각도L -45° / R135°, 8인치 기준 명목 지상고21.6 mm를 유지함. 상판16 / 측판18 / 하판12 / 거싯8 mm와 루트R10도 유지함.

## 출력 공간

회전 배치 STL의 본체 영역은 X10~190 / Y19~181 / Z0~196 mm. 200 mm 배드 중심에 한 부품씩 배치함. 5 mm 외곽 브림을 가정한 공간은 **190 × 172 mm**, 높이는196 mm임. 이는 기하학적 영역 계산이며 실제 서포트·퍼지라인·스커트·래프트·툴패스 검증이 아님. 외부 서포트가 이를 넘을 수 있으므로 학교 슬라이서 프로필에서 확인함. 래프트/두꺼운 받침을 추가하면 Z=200 mm 제한을 다시 확인함.

**100% 크기(mm) / 사용자가 요청한 100% 채움 설정.** STL에는 채움률이 저장되지 않음. 축소하여 맞춤 기능은 사용하지 않음. 기본 방향 STL도 최대196 mm라 200 mm 큐브 안에 들어가지만, 배드 회전본은 X/Y에 브림 여유를 더 확보한 배치임. 층간하중과 서포트는 실제 재료·출력 방향으로 재검토해야 함.

## 질량과 기하 검사

기존 밀도1.06 g/cm³ 입력을 유지한 CAD 계산: 본체 **{body:.3f} kg/개**, 받침 **{seat:.3f} kg/개**, 플라스틱 좌우 합계 **{mass:.3f} kg**. 금속부·모터·서포트·브림은 제외함. Rev F 약2.800 kg 대비 약0.189 kg 감소함.

대리 모터 캔과 본체의 최소 기하 간격 **{clearance:.3f} mm**. 조립 및 연속200 mm 삽입 경로 검사 **{g['검사수']}개**, 출력공간·고정치수·실제홀축 검사 **{q['check_count']}개** 통과. 모든 출력용 본체/받침의 STEP·STL 최대 치수를 검사함. 결과는 `qa/`에 있음.

**DEMO 형상 무간섭이 실물 맞춤이나 하중 안전을 보장하지 않음.** 모터 자료5쪽의 D01 외경·E02 편심·L04 보스·M01 귀 두께 등은 실측 대기 상태임. 외곽 폭을 줄여 주변 여유가 작아졌으므로 실측 대조가 특히 중요함. 21.6 mm 지상고는 타이어 눌림·구조 변형·바닥 요철을 차감하기 전의 명목값임.

## CAD 및 구조 검증의 한계

FCStd는 외부에서 직렬화한 `Part::Feature` 정밀 솔리드. 완전 구속 스케치·피처 이력은 아님. 형상 입력 치수의 재생성 원본은 `parameters.json`과 `src/geometry.py`임. `.SLDPRT`/`.SLDASM`/Simulation 프로젝트를 생성하지 않음. STEP는 정밀 솔리드 가져오기/직접 편집의 시작 형상임.

FreeCAD·SolidWorks 앱의 실제 화면/열기 검사는 미실시. 기존 BREP 직접 가져오기 매크로와 AP214 대안을 유지함. 매크로 역시 문법 검사만 실시함. **Rev G 구조 FEA·실물 출력·하중시험 미실시.** 단면/레일 위치 변경으로 기존 개정의 응력·변위·안전율을 전용하지 않음.

## 재생성

```bash
python -m pip install -r requirements.txt
python src/export_package.py
python src/check_design.py
python src/check_print_envelope.py
python src/render_preview.py
python src/render_print_bed.py
python src/write_docs.py
python src/make_drawings.py
python src/verify_package.py
python src/finalize_package.py
```

문서 생성에는 로컬 한국어 TTF가 필요함. Windows 맑은 고딕/리눅스 나눔고딕 또는 `FONT_KR`·`FONT_KR_BOLD` 환경변수를 사용함. 폰트 파일은 배포하지 않음. 치수를 바꾸면 구형 생성파일을 혼용하지 않고 전체 재생성함. 내보내기는200 mm 초과 시 중단함.

참조PDF2개·PNG1개는 `reference/`에 원본 유지. 자료에서 확정되지 않은 길이를 추측해 실측값으로 바꾸지 않음. 기준 저장소 커밋: `4792da580a78f302c24412488b0d653e7083863d` (Rev F). 원격 GitHub는 이 패키지로 수정하지 않았음.
'''
    (ROOT/'README.md').write_text(readme,encoding='utf-8')
    (ROOT/'README-KR.md').write_text(readme,encoding='utf-8')
    (ROOT/'CHANGELOG.md').write_text('''# 개정 이력

## 0.7.0 / Rev G / 2026-10-01

200 mm 학교 프린터 제한 반영. 본체 폭212→196 mm; 모든 출력 대상 부품 최대치수200 mm 이하 검사. 전체 형상 비율 축소 없이 기능 치수 유지. 상·하판 창, 전면 창 위치, 레일과 핀을 안쪽8 mm 이동하고 전방 기둥 깊이를28 mm로 조정함. 측면 회전 출력 STL 별도 제공(180×162×196 mm), 5 mm 브림의 가상영역190×172 mm. 구조 FEA 미실시.

## 0.6.0 / Rev F

8인치 저상형(바닥Z=-80), 수평 편심 배치, AP203/AP214·BREP와 FreeCAD 직접가져오기 경로. 외곽212×162×180 mm였음.
''',encoding='utf-8')
    (ROOT/'MIGRATION_KR.md').write_text('''# Rev F → Rev G 교체 안내

원격 저장소의 .git 디렉터리와 사용자 변경을 보존하고 별도 브랜치 또는 백업에서 교체함. 자동 삭제·git push는 이 패키지에서 실행하지 않음.

이 패키지는 전체 생성본임. 이전 `cad/`, `compatibility/`, `drawings/`, `print/`, `preview/`, `qa/`의 Rev F 출력 파일은 새 파일과 함께 발주/출력 목록에 남기지 않음. Git의 변경 목록에서 `SCMB-F*`가 제거되고 `SCMB-G*`로 바뀌는지 검토함. `parameters.json`, `src/`, 루트 매크로/안내/검사파일과 data/도 함께 교체함.

각 본체 폭196 mm, 각 받침 폭176 mm. 체결용 M8·M6의 수와 길이 및 차체 피치는 같지만 레일과 핀 위치가8 mm 이동했으므로 **Rev F 받침과 Rev G 본체를 혼합하지 않음**. 좌우 표기도 유지함. 모터·바퀴가 포함된 검토 조립 STEP는 출력 대상이 아님.

배포 후 `python CHECK_FILES.py`로 로컬 파일 손상 여부를 점검함. 이는 실제 CAD 앱 화면 검사와 별개임.
''',encoding='utf-8')
    (ROOT/'docs/출력안내_한국어.md').write_text('''# 200 mm 프린터 출력 안내

`print/bed_ready`의 L/R 본체 및 L/R 받침을 각각1개씩, 한 번에 한 부품으로 출력함. 본체 BED STL은 측면을 아래로 회전 배치하여180×162×196 mm임. 바닥 좌표는Z=0이며 mm/축척100%를 사용함. 원본 방향 STL은196×162×180 mm임.

명목200 mm 큐브 안에 들어가는 형상 검사를 완료했으나 기종·노즐·재료 설정이 미제공이라 실제 슬라이싱은 미실시임. 5 mm 브림을 더한 본체 외접영역190×172 mm는 계산 예시이며 실제 접착력 보장이나 권장 브림 폭 확정이 아님. 서포트, 스커트, 퍼지, 클립, 래프트의 최종 툴패스를 포함해200 mm를 넘는지 확인함. 최종Z높이도200 mm 이하여야 함.

100% 채움은 슬라이서에서 지정함. 출력품의 물성은 적층방향과 실제 공정에 달려 있으므로 100% 채움만으로 강도 승인이 되지 않음. 학교장비가 선택한재료에 필요한 노즐·챔버·건조 조건을 제공하는지 확인함. 끼워맞춤·홀·레일은 작은 시험편 또는 해당 단면 선행 출력으로 보정 후 본체를 출력함.

M8용 금속 압축제한슬리브와 M6용 금속 압축제한슬리브, 잠금핀은 플라스틱으로 대체 출력하지 않음. reference나 모터대리형상은 제작대상이 아님. 모터 맞춤은 실측해야하며 체결 토크와 실물 운행 하중은 아직 승인하지 않음.

외부 참고: Prusa의 Skirt and Brim 문서는 브림이 첫 레이어 접착면적을 늘리며 폭을 별도로 설정하는 기능임을 설명함. 특정 학교 장비에 대한 프로필은 아님. https://help.prusa3d.com/article/skirt-and-brim_133969
''',encoding='utf-8')
    src=json.loads((ROOT/'data/sources.json').read_text())
    src=[x for x in src if x.get('항목') not in ['Rev G 기준 저장소','출력 브림 안내']]
    src.insert(0,{'항목':'Rev G 기준 저장소','url':'https://github.com/JTech-CO/Motor-Bracket/tree/4792da580a78f302c24412488b0d653e7083863d','용도':'실시간 확인한 Rev F parameters.json 및 geometry.py. 로컬 geometry.py Git blob SHA d632b452b0e612f38da3f5e505f1f6ef6a1b4ba2 일치.'})
    src.append({'항목':'출력 브림 안내','url':'https://help.prusa3d.com/article/skirt-and-brim_133969','용도':'브림 폭은 별도 지정하는 첫 레이어 접착 면적. 5 mm는 이번 공간검사 예시로 설계자가 선택한 값.'})
    (ROOT/'data/sources.json').write_text(json.dumps(src,ensure_ascii=False,indent=2)+'\n')
    print('한국어 문서 작성 완료')
if __name__=='__main__':main()
