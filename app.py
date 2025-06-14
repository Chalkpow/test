from flask import Flask, render_template, request, redirect, url_for, session
import qrcode
import datetime
from io import BytesIO
import base64

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 세션 사용을 위한 키

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # 사용자 정보 세션에 저장
        session['user'] = {
            'grade': f"{int(request.form['grade']):02d}",
            'class': f"{int(request.form['class']):02d}",
            'number': f"{int(request.form['number']):02d}"
        }
        return redirect(url_for('main'))
    return render_template('index.html')

@app.route('/main')
def main():
    return render_template('main.html')

@app.route('/generate_qr')
def generate_qr():
    user = session.get('user')
    if not user:
        return redirect(url_for('index'))

    today = datetime.datetime.now().strftime("%Y%m%d")
    qr_data = today + user['grade'] + user['class'] + user['number']

    img = qrcode.make(qr_data)
    buf = BytesIO()
    img.save(buf)
    img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    return render_template('qr.html', qr_data=qr_data, img_data=img_b64)

if __name__ == '__main__':
    app.run(debug=True)