"""폰트 파일을 배포하지 않고 로컬 한국어 글꼴을 찾는다."""
import os
from pathlib import Path

def korean_font(bold=False):
    env=os.environ.get('FONT_KR_BOLD' if bold else 'FONT_KR')
    names=([env] if env else [])+([
        '/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf',
        'C:/Windows/Fonts/malgunbd.ttf'] if bold else [
        '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
        'C:/Windows/Fonts/malgun.ttf'])
    for name in names:
        if Path(name).is_file():return name
    raise FileNotFoundError('한국어 TTF 글꼴이 없습니다. FONT_KR/FONT_KR_BOLD 환경변수로 로컬 글꼴 경로를 지정하세요.')
