import pandas as pd
import requests
import io
import time
import os

# 1. 텔레그램 알림 발송 함수
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

# 2. 데이터 수집 함수 (등락률/현재가 포함)
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
                # 숫자 변환
                for col in ['종가', '거래량', '기관', '외국인']:
                    table[col] = pd.to_numeric(table[col], errors='coerce')
                return table
    except: return None
    return None

# 3. 매수 신호 판단 (수급 + 거래량 + 이동평균선 돌파)
def get_buy_signal(df):
    if df is None: return None
    
    # 지표 계산
    recent_5d = df[['기관', '외국인']].head(5).sum().sum()
    avg_20d = df[['기관', '외국인']].head(20).mean().sum()
    today_vol = df['거래량'].iloc[0]
    avg_20d_vol = df['거래량'].head(20).mean()
    
    # 20일 이동평균선 확인
    close_price = df['종가'].iloc[0]
    ma20 = df['종가'].head(20).mean()
    
    # 조건 설정
    is_surge = (recent_5d > (avg_20d * 3)) and (today_vol > (avg_20d_vol * 3))
    is_uptrend = close_price > ma20
    
    if is_surge and is_uptrend:
        return {
            'price': close_price,
            'rate': df['등락률'].iloc[0],
            'score': round((recent_5d/avg_20d) + (today_vol/avg_20d_vol), 1)
        }
    return None

# 4. 메인 실행부
if __name__ == "__main__":
    target_stocks = [('005930', '삼성전자'), ('000660', 'SK하이닉스'), ('035420', 'NAVER'), 
                     ('005380', '현대차'), ('068270', '셀트리온'), ('035720', '카카오')]
    
    found_list = []
    for code, name in target_stocks:
        df = get_stock_data(code)
        signal = get_buy_signal(df)
        if signal:
            found_list.append(f"🚀 {name}\n- 현재가: {signal['price']:,}원\n- 등락률: {signal['rate']}\n- 매수강도: {signal['score']}점")
        time.sleep(0.5)
        
    if found_list:
        msg = "🚨 [구체적 매수 신호 포착]\n\n" + "\n\n".join(found_list)
        send_telegram_message(msg)
