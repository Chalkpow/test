from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import qrcode
import datetime
from io import BytesIO, TextIOWrapper
import base64
from functools import wraps  # wraps 임포트
import io
import csv
from sqlalchemy import text
import pandas as pd
from datetime import date

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
    unique_code = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f'<User {self.userid}>'

class UniqueCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(100), unique=True, nullable=False)
    name   = db.Column(db.String(80),  nullable=True)
    grade  = db.Column(db.String(2),   nullable=True)
    class_ = db.Column(db.String(2),   nullable=True)
    number = db.Column(db.String(2),   nullable=True)
    booking_month  = db.Column(db.Integer,     nullable=True)   # 추가
    booking_flag   = db.Column(db.String(10),  nullable=True)

    def __repr__(self):
        return f'<UniqueCode {self.code}>'
    
class DailyMeal(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    unique_code_id  = db.Column(db.Integer, db.ForeignKey('unique_code.id'), nullable=False)
    date            = db.Column(db.Date, nullable=False)
    received        = db.Column(db.Boolean, default=False, nullable=False)

    unique_code     = db.relationship('UniqueCode', backref='daily_meals')

# 데이터베이스 생성 (처음 한 번만 실행)
with app.app_context():
    db.create_all()
    # 테이블에 새 컬럼이 없으면 ALTER TABLE
    cols = [row[1] for row in db.session.execute(text("PRAGMA table_info('unique_code')")).fetchall()]
    def _add(col, sql_type):
        db.session.execute(text(f"ALTER TABLE unique_code ADD COLUMN {col} {sql_type}"))
    if 'name'   not in cols: _add('name',   'VARCHAR(80)')
    if 'grade'  not in cols: _add('grade',  'VARCHAR(2)')
    if 'class_' not in cols: _add('class_', 'VARCHAR(2)')
    if 'number' not in cols: _add('number', 'VARCHAR(2)')
    if 'booking_month' not in cols: _add('booking_month',  'INTEGER')
    if 'booking_flag'  not in cols: _add('booking_flag',   'VARCHAR(10)')
    db.session.commit()

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('관리자 권한이 필요합니다.')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/upload_codes', methods=['GET', 'POST'])
@admin_required
def upload_codes():
    if request.method == 'POST':
        f = request.files.get('file')
        if not f:
            flash('파일을 선택해주세요.')
            return redirect(request.url)

        # 메모리 버퍼
        raw = f.read()
        buf = BytesIO(raw)

        # 1) 엑셀 우선 시도
        try:
            df = pd.read_excel(buf, engine='openpyxl')
            # 필수 컬럼 검사
            must = ['회원코드','이름','학년','반','번호']
            for col in must:
                if col not in df.columns:
                    flash(f'엑셀에 "{col}" 열이 없습니다.')
                    return redirect(request.url)

            # 'n월석식신청여부' 컬럼 찾기
            booking_col = next((c for c in df.columns if re.match(r'^\d{1,2}월석식신청여부$', c)), None)
            if booking_col is None:
                flash('엑셀에 "n월석식신청여부" 형식의 열이 없습니다.')
                return redirect(request.url)
            # month 추출
            month = int(booking_col.split('월')[0])

            # DB 리셋
            db.session.query(UniqueCode).delete()
            for _, row in df.iterrows():
                code = str(row['회원코드']).strip()
                if not code: continue
                uc = UniqueCode(
                    code=code,
                    name=str(row['이름']).strip(),
                    grade=f"{int(row['학년']):02d}",
                    class_=f"{int(row['반']):02d}",
                    number=f"{int(row['번호']):02d}",
                    booking_month=month,
                    booking_flag=str(row[booking_col]).strip()
                )
                db.session.add(uc)
            db.session.commit()

            flash(f'{len(df)}개의 고유코드를 업로드했습니다.')
            return redirect(url_for('view_codes'))

        except Exception:
            # 2) 엑셀 실패하면 CSV 시도
            buf.seek(0)
            try:
                reader = csv.reader(TextIOWrapper(buf, encoding='utf-8'))
                codes = [r[0].strip() for r in reader if r and r[0].strip()]
                db.session.query(UniqueCode).delete()
                for c in set(codes):
                    db.session.add(UniqueCode(code=c))
                db.session.commit()
                flash(f'{len(codes)}개의 고유코드를 업로드했습니다.')
                return redirect(url_for('view_codes'))
            except:
                flash('파일을 읽는 중 오류가 발생했습니다.\n(지원: 엑셀[xlsx/xls] 또는 UTF-8 CSV)')
                return redirect(request.url)

    return render_template('upload_codes.html')

@app.route('/admin/meal_scan')
@admin_required
def meal_scan():
    return render_template('meal_scan.html')

@app.route('/admin/scan_qr', methods=['POST'])
@admin_required
def scan_qr():
    qr = request.form['qr_data'].strip()
    # 1) 오늘 날짜
    today = date.today()
    # 2) 오늘 기록이 한번도 초기화되지 않았다면—전일 데이터 지우고 오늘용 레코드 생성
    if not DailyMeal.query.filter_by(date=today).first():
        DailyMeal.query.delete()
        db.session.commit()
        for uc in UniqueCode.query.all():
            db.session.add(DailyMeal(unique_code_id=uc.id, date=today, received=False))
        db.session.commit()

    # 3) QR 파싱: YYYYMMDD + grade(2) + class(2) + num(2)
    dt_str, g, c, n = qr[:8], qr[8:10], qr[10:12], qr[12:14]
    # (dt_str는 오늘이므로 따로 검증 생략)
    uc = UniqueCode.query.filter_by(grade=g, class_=c, number=n).first()
    if not uc or uc.booking_flag != 'O':
        return {'status':'NOT_ELIGIBLE',
                'message':'석식 대상자가 아닙니다.'}

    # 4) DailyMeal 레코드 조회
    rec = DailyMeal.query.filter_by(date=today, unique_code_id=uc.id).first()
    if rec.received:
        msg = f"{today.month}월 {today.day}일 {uc.name} 학생 이미 석식 받았습니다"
        return {'status':'ALREADY', 'message':msg}
    # 5) 최초 스캔
    rec.received = True
    db.session.commit()
    msg = f"{today.month}월 {today.day}일 {uc.name} 학생 확인되었습니다"
    return {'status':'OK', 'message':msg}



@app.route('/admin/meal_records')
@admin_required
def meal_records():
    today = date.today()
    records = (DailyMeal.query
                 .filter_by(date=today)
                 .join(UniqueCode)
                 .order_by(UniqueCode.grade, UniqueCode.class_, UniqueCode.number)
                 .all())
    return render_template('meal_records.html',
                           records=records,
                           month=today.month, day=today.day)


@app.route('/admin/codes')
@admin_required
def view_codes():
    codes = UniqueCode.query.order_by(UniqueCode.id).all()
    month = codes[0].booking_month if codes and codes[0].booking_month else None
    booking_label = f"{month}월석식신청여부" if month else "석식신청여부"
    return render_template('view_codes.html', codes=codes, booking_label=booking_label)


@app.route('/admin/edit_code/<int:code_id>', methods=['GET', 'POST'])
@admin_required
def edit_code(code_id):
    code = UniqueCode.query.get_or_404(code_id)
    if request.method == 'POST':
        new_code = request.form['code'].strip()
        if new_code:
            code.code = new_code
            db.session.commit()
            flash('고유코드를 업데이트했습니다.')
        return redirect(url_for('view_codes'))
    return render_template('edit_code.html', code=code)

@app.route('/admin/delete_code/<int:code_id>')
@admin_required
def delete_code(code_id):
    code = UniqueCode.query.get_or_404(code_id)
    db.session.delete(code)
    db.session.commit()
    flash('고유코드를 삭제했습니다.')
    return redirect(url_for('view_codes'))

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

    if user:
        uc = UniqueCode.query.filter_by(code=user.unique_code).first()
        if uc and uc.booking_month and uc.booking_flag is not None:
            booking_month = uc.booking_month
            booking_flag  = uc.booking_flag
        else:
            booking_month = None
            booking_flag  = None
    else:
        booking_month = None
        booking_flag  = None

    return render_template(
        'index.html',
        user=user,
        year=year,
        month=month,
        sel_day=sel_day,
        sel_menu=sel_menu,
        booking_month=booking_month,
        booking_flag=booking_flag,
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
        # 1) 폼 데이터 수집
        userid      = request.form['userid'].strip()
        password    = request.form['password']
        name        = request.form['name'].strip()
        grade       = f"{int(request.form['grade']):02d}"
        class_      = f"{int(request.form['class']):02d}"
        number      = f"{int(request.form['number']):02d}"
        unique_code = request.form['unique_code'].strip()

        # 2) 아이디 중복 체크
        if User.query.filter_by(userid=userid).first():
            flash('이미 존재하는 아이디입니다.')
            return redirect(url_for('register'))

        # 3) 고유코드 + 정보 일치 체크
        #   코드만 존재하는지 먼저 보고, 그 다음 세부 정보까지 확인할 수도 있고
        #   한 번에 필터링해도 무방합니다.
        uc = UniqueCode.query.filter_by(
            code=unique_code,
            name=name,
            grade=grade,
            class_=class_,
            number=number
        ).first()

        if not uc:
            # 코드가 없거나, 코드에 매칭된 정보가 하나라도 다르다면
            flash('고유코드 또는 학년·반·번호·이름 정보가 일치하지 않습니다.')
            return redirect(url_for('register'))

        # 4) 가입 처리
        new_user = User(
            userid=userid,
            password=password,
            name=name,
            grade=grade,
            class_=class_,
            number=number,
            unique_code=unique_code
        )
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