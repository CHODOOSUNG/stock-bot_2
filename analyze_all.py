import pandas as pd
import requests
import io
import time
import os

# 1. 텔레그램 알림 발송 함수 (환경변수 사용)
def send_telegram_message(message):
    token = os.environ.get('TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {'chat_id': chat_id, 'text': message}
    try:
        response = requests.get(url, params=params)
        return response.status_code == 200
    except Exception as e:
        print(f"알림 전송 실패: {e}")
        return False

# 2. 분석할 종목 리스트 (필요 시 더 추가하세요)
def get_target_stocks():
    # KOSPI 200 + KOSDAQ 150 주요 종목 예시
    return [
        ('005930', '삼성전자'), ('000660', 'SK하이닉스'), ('035420', 'NAVER'),
        ('005380', '현대차'), ('068270', '셀트리온'), ('035720', '카카오'),
        ('000270', '기아'), ('006400', '삼성SDI'), ('051910', 'LG화학'),
        ('010130', '고려아연'), ('066570', 'LG전자'), ('034020', '두산에너빌리티')
    ]

# 3. 데이터 수집 함수
def get_stock_data(code):
    url = f"https://finance.naver.com/item/frgn.naver?code={code}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers)
        tables = pd.read_html(io.StringIO(res.text))
        for table in tables:
            if '외국인' in str(table.columns):
                table.columns = ['날짜', '종가', '전일비', '등락률', '거래량', '기관', '외국인', '보유주수', '보유율']
                table = table.iloc[1:].copy()
                for col in ['거래량', '기관', '외국인']:
                    table[col] = pd.to_numeric(table[col], errors='coerce')
                return table
    except: return None
    return None

# 4. 수급 및 거래량 급증 판단 로직
def check_surge(df):
    if df is None: return False
    # 최근 5일 합계 / 20일 평균 수급
    recent_5d = df[['기관', '외국인']].head(5).sum().sum()
    avg_20d = df[['기관', '외국인']].head(20).mean().sum()
    # 당일 거래량 / 20일 평균 거래량
    today_vol = df['거래량'].iloc[0]
    avg_20d_vol = df['거래량'].head(20).mean()
    
    if avg_20d == 0 or avg_20d_vol == 0: return False
    
    # 조건: 수급 3배 이상 AND 거래량 3배 이상
    return (recent_5d > (avg_20d * 3)) and (today_vol > (avg_20d_vol * 3))

# 5. 메인 실행부
if __name__ == "__main__":
    target_stocks = get_target_stocks()
    found_list = []
    
    for code, name in target_stocks:
        df = get_stock_data(code)
        if check_surge(df):
            found_list.append(name)
        time.sleep(0.5) # 서버 부하 방지 (중요)
        
    if found_list:
        msg = "🚨 [수급+거래량 급증 종목]\n" + "\n".join([f"- {s}" for s in found_list])
        send_telegram_message(msg)
    else:
        # 조건 만족 종목이 없을 때도 알림을 원하면 주석 해제하세요
        # send_telegram_message("오늘 포착된 급증 종목이 없습니다.")
        print("조건 만족 종목 없음.")