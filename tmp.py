import requests
from bs4 import BeautifulSoup
import re

def fetch_month_menu(year: int, month: int) -> dict:
    """
    주어진 연(year)·월(month)의 괴산고 급식 식단표를 가져와
    {일: {'lunch': 중식메뉴, 'dinner': 석식메뉴}, ...} 형태로 반환.
    """
    # 페이지가 월 단위로 렌더링 되므로, day는 01로 고정해도 OK
    ymd = f"{year}{month:02d}01"
    url = f"https://school.cbe.go.kr/goesan-h/M01050701/list?ymd={ymd}"
    
    resp = requests.get(url)
    resp.raise_for_status()
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    # 페이지 내 식단표가 유일한 table 요소로 들어있습니다
    table = soup.find('table')
    
    menu = {}
    # <td>마다 “1 중식 ... 석식 ...” 형태의 텍스트가 있으므로 모두 순회
    for td in table.find_all('td'):
        text = td.get_text(separator=' ', strip=True)
        # “번호 중식(…)석식(…)” 패턴에 매칭
        m = re.search(r'(\d+)\s*중식(.*?)석식(.*)', text, re.S)
        if not m:
            continue
        day, lunch, dinner = m.groups()
        menu[int(day)] = {
            'lunch': lunch.strip(),
            'dinner': dinner.strip()
        }
    return menu

if __name__ == "__main__":
    # 예: 2025년 7월 전체 메뉴 가져오기
    july_menu = fetch_month_menu(2025, 7)
    for day in sorted(july_menu):
        print(f"{day}일 ▶ 중식: {july_menu[day]['lunch']}")
        print(f"       석식: {july_menu[day]['dinner']}\n")
