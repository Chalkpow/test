from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['POST'])
def signup():
    # 회원가입 정보 처리
    grade = request.form['grade']
    class_ = request.form['class']
    number = request.form['number']
    phone = request.form['phone']
    userid = request.form['userid']
    password = request.form['password']

    # 여기에 DB 저장 or 처리 로직 추가 가능
    print(f'회원가입 정보: {grade}-{class_}-{number}, {phone}, {userid}')

    # 회원가입 후 메인 화면으로 리다이렉트
    return redirect(url_for('main'))

@app.route('/main')
def main():
    return render_template('main.html')

if __name__ == '__main__':
    app.run(debug=True)
