# 출입 통제 시스템 백엔드 (Access Control Server)

클라우드 플랫폼 **Render**에 배포되어 현재 운영 중인 FastAPI 기반의 백엔드 서버입니다. Qt 클라이언트 등에서 발생하는 출입, 등록, QR 이벤트 데이터를 수신하여 클라우드 데이터베이스와 스토리지에 안전하게 저장합니다.

## 공개 서버 주소 (Public Server URL)

  * **`https://accesscontrolserver.onrender.com`**

-----

## API 사용법

공개 서버 주소를 사용하여 API 엔드포인트를 호출할 수 있습니다. 예를 들어, `curl`을 사용하여 서버 상태를 확인할 수 있습니다.

```bash
curl https://accesscontrolserver.onrender.com/healthz
```

Qt 클라이언트 및 다른 프로그램에서도 위 기본 주소를 사용하면 됩니다.

-----

## 주요 기능

  * **이벤트 처리**: 3가지 종류의 이벤트를 처리하는 API 엔드포인트 제공
      * `POST /access-events`: 출입 이벤트 (이미지 1장 + 메타데이터)
      * `POST /registrations`: 등록 이벤트 (이미지 N장 + 메타데이터)
      * `POST /qr-events`: QR 이벤트 (JSON 전용)
  * **클라우드 연동**: 모든 데이터를 영구적으로 보관하기 위해 클라우드 서비스를 사용합니다.
      * **데이터베이스**: Neon (PostgreSQL)
      * **파일 스토리지**: Cloudflare R2 (S3 호환)

-----

## 기술 스택

  * **Backend**: Python, FastAPI
  * **Database**: PostgreSQL, SQLAlchemy
  * **Storage**: Cloudflare R2, boto3
  * **Server**: Uvicorn
  * **Deployment**: Render

-----

## API 엔드포인트 목록

  * `GET /healthz`: 서버의 상태를 확인합니다.
  * `POST /qr-events`: QR 이벤트 데이터를 기록합니다.
  * `POST /access-events`: 출입 이벤트 데이터와 이미지를 기록합니다.
  * `POST /registrations`: 등록 이벤트 데이터와 이미지들을 기록합니다.

-----

## (참고) 로컬 개발 환경 설정

> ⚠️ **참고:** 아래 내용은 이 서버의 코드를 직접 수정하거나 개발할 개발자를 위한 안내입니다. 단순히 서버를 사용만 하는 경우에는 알 필요가 없습니다.

#### 1\. 소스 코드 복제

```bash
git clone <당신의_GitHub_저장소_URL>
cd <프로젝트_폴더명>
```

#### 2\. 파이썬 가상 환경 생성 및 활성화

```bash
# 가상 환경 생성
python -m venv .venv

# 가상 환경 활성화 (Windows)
.venv\Scripts\activate

# 가상 환경 활성화 (macOS/Linux)
source .venv/bin/activate
```

#### 3\. 필요 패키지 설치

```bash
pip install -r requirements.txt
```

#### 4\. 환경 변수 설정

프로젝트 루트 폴더에 `.env` 파일을 생성하고, 아래 형식에 맞게 Neon DB 및 Cloudflare R2 접속 정보를 입력합니다.

**`.env` 파일 예시:**

```
# Neon DB Settings
DATABASE_URL="postgresql://user:password@host/dbname"

# Cloudflare R2 Settings
R2_BUCKET_NAME="your-bucket-name"
R2_ENDPOINT_URL="https://<ACCOUNT_ID>.r2.cloudflarestorage.com"
R2_ACCESS_KEY_ID="your-access-key-id"
R2_SECRET_ACCESS_KEY="your-secret-access-key"
```

#### 5\. 로컬 서버 실행

```bash
uvicorn main:app --reload
```

로컬 서버는 `http://127.0.0.1:8000` 주소에서 실행됩니다.
