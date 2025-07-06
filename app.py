from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy # SQLAlchemy 임포트
import qrcode
import datetime
from io import BytesIO
import base64

app = Flask(__name__)
app.secret_key = 'your_secret_key' # 세션 키
# SQLite 데이터베이스 설정
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db' # 'site.db'라는 SQLite 파일을 사용
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# User 모델 정의 (변경 없음)
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

@app.route('/')
def main():
    user_session_id = session.get('user_id') # 세션에서 user_id를 가져옴
    user = None
    if user_session_id:
        user = User.query.get(user_session_id) # user_id로 데이터베이스에서 사용자 정보 조회
    return render_template('main.html', user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        userid = request.form['userid']
        password = request.form['password']
        user = User.query.filter_by(userid=userid).first() # 아이디로 사용자 조회

        if user and user.password == password:
            session['user_id'] = user.id # 세션에 user.id 저장
            return redirect(url_for('main'))
        else:
            flash('아이디 또는 비밀번호가 올바르지 않습니다.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None) # 세션에서 user_id 제거
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

        # 이미 존재하는 아이디인지 확인
        if User.query.filter_by(userid=userid).first():
            flash('이미 존재하는 아이디입니다.')
            return redirect(url_for('register'))

        # 새로운 사용자 객체 생성
        new_user = User(userid=userid, password=password, name=name,
                        grade=grade, class_=class_, number=number)
        db.session.add(new_user)
        db.session.commit() # 데이터베이스에 저장

        flash('회원가입이 완료되었습니다. 로그인해주세요.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/generate_qr')
def generate_qr():
    user_session_id = session.get('user_id')
    if not user_session_id:
        flash('로그인한 뒤 이용할 수 있습니다!')
        return redirect(url_for('login'))

    user = User.query.get(user_session_id) # 데이터베이스에서 현재 사용자 정보 가져오기
    if not user:
        flash('사용자 정보를 찾을 수 없습니다. 다시 로그인해주세요.')
        return redirect(url_for('login'))

    today = datetime.datetime.now().strftime("%Y%m%d")
    qr_data = today + user.grade + user.class_ + user.number # user 객체의 속성 사용

    img = qrcode.make(qr_data)
    buf = BytesIO()
    img.save(buf)
    img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    return render_template('qr.html', qr_data=qr_data, img_data=img_b64)

if __name__ == '__main__':
    app.run(debug=True)