# 괴산고 석식 도우미

## 개요

`괴산고 석식 도우미`는 괴산고등학교 학생들을 위한 석식 QR 인증 및 식단 제공 웹 애플리케이션입니다. 학생은 본인의 정보와 고유코드를 통해 회원가입을 하고, 로그인 후 당일 석식 메뉴를 확인할 수 있으며, QR 인증을 통해 실제 석식 수령을 기록할 수 있습니다. 관리자(admin)는 사용자 관리, 고유코드 관리, QR 스캔, 당일 석식 현황 등을 제어할 수 있습니다.

## 주요 기능

* **학생용**

  * 회원가입: 학년, 반, 번호, 이름, 고유코드 입력 및 검증
  * 로그인/로그아웃
  * 당일(또는 가장 가까운 날) 중식/석식 메뉴 확인
  * QR 코드 생성 후 카메라를 이용한 석식 인증

* **관리자용**

  * 사용자 목록 조회/수정/삭제
  * 고유코드(회원코드) 엑셀/CSV 업로드, 조회, 수정, 삭제
  * QR 인증 스캔 페이지(실시간 카메라 스캔)
  * 당일 석식 수령 현황 조회 테이블

## 요구사항

* Python 3.8 이상
* SQLite (기본 내장)
* 카메라를 지원하는 웹 브라우저

## 설치 및 실행

1. 저장소를 클론합니다.

   ```bash
   git clone <repository_url>
   cd <repository_folder>
   ```

2. 가상 환경 생성 및 활성화

   ```bash
   python -m venv venv
   source venv/bin/activate    # macOS/Linux
   venv\Scripts\activate     # Windows
   ```

3. 의존성 설치

   ```bash
   pip install -r requirements.txt
   ```

4. 환경 변수 설정

   * `app.secret_key`를 `.env` 혹은 환경 변수로 지정하는 것을 권장합니다.
   * 관리자 계정은 기본 `admin`/`adminpassword`로 설정되어 있습니다. (배포 전 변경 요망)

5. 애플리케이션 실행

   ```bash
   python app.py
   ```

   * 기본적으로 `http://127.0.0.1:5000` 에서 동작합니다.

## 디렉토리 구조

```
├── app.py                # 메인 애플리케이션
├── requirements.txt      # 의존성 목록
├── README.md             # 프로젝트 설명서
└── templates/            # HTML 템플릿
    ├── index.html
    ├── login.html
    ├── register.html
    ├── admin.html
    ├── admin_login.html
    ├── upload_codes.html
    ├── view_codes.html
    ├── edit_code.html
    ├── meal_scan.html
    ├── meal_records.html
    └── qr.html
```

## 관리자 기능 사용

* **사용자 관리**: `/admin` → 사용자 목록
* **고유코드 관리**: `/admin/codes` → 엑셀/CSV 업로드 및 조회
* **QR 인증 스캔**: `/admin/meal_scan` → 실시간 카메라 스캔
* **당일 석식 현황**: `/admin/meal_records` → 수령 현황 테이블

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.
