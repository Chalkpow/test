from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import qrcode
import datetime
from io import BytesIO
import base64
from functools import wraps  # wraps 임포트
import calendar

import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 세션 키 (실제 배포 시에는 더 강력한 키 사용)

# SQLite 데이터베이스 설정 (로컬 개발용)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 관리자 계정 설정 (실제 서비스에서는 환경 변수 등으로 관리하는 것이 좋습니다.)
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'adminpassword'

# User 모델 정의
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    grade = db.Column(db.String(2), nullable=False)
    class_ = db.Column(db.String(2), nullable=False)
    number = db.Column(db.String(2), nullable=False)

    def __repr__(self):
        return f'<User {self.userid}>'

# 데이터베이스 생성 (처음 한 번만 실행)
with app.app_context():
    db.create_all()

# 관리자 로그인 확인 데코레이터
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session or not session['admin_logged_in']:
            flash('관리자 권한이 필요합니다.')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# 급식 메뉴 파싱 함수
def fetch_month_menu(year: int, month: int) -> dict:
    """
    주어진 연·월의 괴산고 급식 식단표를 가져와
    {일: {'lunch': 중식메뉴, 'dinner': 석식메뉴}, ...} 형태로 반환.
    """
    ymd = f"{year}{month:02d}01"
    url = f"https://school.cbe.go.kr/goesan-h/M01050701/list?ymd={ymd}"
    resp = requests.get(url)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, 'html.parser')
    table = soup.find('table')

    menu = {}
    for td in table.find_all('td'):
        text = td.get_text(separator=' ', strip=True)
        m = re.search(r"(\d+)\s*중식(.*?)석식(.*)", text, re.S)
        if not m:
            continue
        day, lunch, dinner = m.groups()
        menu[int(day)] = {
            'lunch': lunch.strip(),
            'dinner': dinner.strip()
        }
    return menu

@app.route('/')
def main():
    # (1) 로그인된 사용자 조회
    user = None
    uid = session.get('user_id')
    if uid:
        user = User.query.get(uid)

    # (2) 오늘 날짜·이번 달 메뉴 로딩
    now = datetime.datetime.now()
    year, month, today = now.year, now.month, now.day
    try:
        menu = fetch_month_menu(year, month)
    except:
        menu = {}
        flash('식단 정보를 가져오는 중 오류가 발생했습니다.')

    # (3) 오늘 메뉴가 없으면 -> 앞으로 (혹은 뒤로) 가장 가까운 날 찾기
    if today in menu:
        sel_day = today
    else:
        # 앞으로 우선 탐색
        future = [d for d in sorted(menu) if d > today]
        if future:
            sel_day = future[0]
        else:
            # 뒤로
            past = [d for d in sorted(menu) if d < today]
            sel_day = past[-1] if past else None

    sel_menu = menu.get(sel_day)

    return render_template(
        'index.html',
        user=user,
        year=year,
        month=month,
        sel_day=sel_day,
        sel_menu=sel_menu,
    )

@app.template_filter('split_menu')
def split_menu(menu_str: str) -> list:
    """
    1) \([^)]*\) 패턴으로 괄호 안 알러지 정보 제거
    2) 남은 문자열을 공백 기준으로 split
    3) 빈 문자열 제거 후 리스트 반환
    """
    # (1) 알러지 코드 제거
    cleaned = re.sub(r'\([^)]*\)', '', menu_str)
    # (2) 공백 기준으로 분리하고, 빈 항목 drop
    parts = [p.strip() for p in cleaned.split() if p.strip()]
    return parts

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        userid = request.form['userid']
        password = request.form['password']
        user = User.query.filter_by(userid=userid).first()

        if user and user.password == password:
            session['user_id'] = user.id
            return redirect(url_for('main'))
        else:
            flash('아이디 또는 비밀번호가 올바르지 않습니다.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('main'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        userid = request.form['userid']
        password = request.form['password']
        name = request.form['name']
        grade = f"{int(request.form['grade']):02d}"
        class_ = f"{int(request.form['class']):02d}"
        number = f"{int(request.form['number']):02d}"

        if User.query.filter_by(userid=userid).first():
            flash('이미 존재하는 아이디입니다.')
            return redirect(url_for('register'))

        new_user = User(userid=userid, password=password, name=name,
                        grade=grade, class_=class_, number=number)
        db.session.add(new_user)
        db.session.commit()

        flash('회원가입이 완료되었습니다. 로그인해주세요.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/generate_qr')
def generate_qr():
    user_session_id = session.get('user_id')
    if not user_session_id:
        flash('로그인한 뒤 이용할 수 있습니다!')
        return redirect(url_for('login'))

    user = User.query.get(user_session_id)
    if not user:
        flash('사용자 정보를 찾을 수 없습니다. 다시 로그인해주세요.')
        return redirect(url_for('login'))

    today = datetime.datetime.now().strftime("%Y%m%d")
    qr_data = today + user.grade + user.class_ + user.number

    img = qrcode.make(qr_data)
    buf = BytesIO()
    img.save(buf)
    img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    return render_template('qr.html', qr_data=qr_data, img_data=img_b64)

# --- 관리자 기능 추가 ---
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            flash('관리자 로그인 성공!')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('잘못된 관리자 아이디 또는 비밀번호입니다.')
    return render_template('admin_login.html')

@app.route('/admin_logout')
@admin_required
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('관리자 로그아웃 되었습니다.')
    return redirect(url_for('admin_login'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    users = User.query.all()  # 모든 사용자 정보 조회
    return render_template('admin.html', users=users)

@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        user.userid = request.form['userid']
        user.name = request.form['name']
        user.grade = f"{int(request.form['grade']):02d}"
        user.class_ = f"{int(request.form['class']):02d}"
        user.number = f"{int(request.form['number']):02d}"
        if request.form['password']:
            user.password = request.form['password']

        db.session.commit()
        flash(f'{user.name} 님의 정보가 성공적으로 업데이트되었습니다.')
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_user.html', user=user)

@app.route('/admin/delete_user/<int:user_id>')
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f'{user.name} 님의 계정이 삭제되었습니다.')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)