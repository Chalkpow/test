from flask import Flask, render_template, request, redirect, url_for, session, flash
import qrcode
import datetime
from io import BytesIO
import base64

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 세션 키

# 메모리 저장용 (예시용, 실제 서비스는 DB 사용 권장)
users = {}

@app.route('/')
def main():
    user = session.get('user')
    return render_template('main.html', user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        userid = request.form['userid']
        password = request.form['password']
        user = users.get(userid)
        if user and user['password'] == password:
            session['user'] = {
                'userid': userid,
                'grade': user['grade'],
                'class': user['class'],
                'number': user['number'],
                'name': user['name']
            }
            return redirect(url_for('main'))
        else:
            flash('아이디 또는 비밀번호가 올바르지 않습니다.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
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

        if userid in users:
            flash('이미 존재하는 아이디입니다.')
            return redirect(url_for('register'))

        users[userid] = {
            'password': password,
            'name': name,
            'grade': grade,
            'class': class_,
            'number': number,
        }
        flash('회원가입이 완료되었습니다. 로그인해주세요.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/generate_qr')
def generate_qr():
    user = session.get('user')
    if not user:
        flash('로그인한 뒤 이용할 수 있습니다!')
        return redirect(url_for('login'))

    today = datetime.datetime.now().strftime("%Y%m%d")
    qr_data = today + user['grade'] + user['class'] + user['number']

    img = qrcode.make(qr_data)
    buf = BytesIO()
    img.save(buf)
    img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    return render_template('qr.html', qr_data=qr_data, img_data=img_b64)

if __name__ == '__main__':
    app.run(debug=True)
