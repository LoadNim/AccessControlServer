# 출입 통제 시스템 백엔드 (Access Control Server)

Qt 클라이언트 등에서 발생하는 출입, 등록, QR 이벤트 데이터를 수신하여 클라우드 데이터베이스와 스토리지에 안전하게 저장하는 FastAPI 기반의 백엔드 서버입니다.

## 주요 기능

  * **이벤트 처리**: 3가지 종류의 이벤트를 처리하는 API 엔드포인트 제공
      * `POST /access-events`: 출입 이벤트 (이미지 1장 + 메타데이터)
      * `POST /registrations`: 등록 이벤트 (이미지 N장 + 메타데이터)
      * `POST /qr-events`: QR 이벤트 (JSON 전용)
  * **클라우드 연동**: 모든 데이터를 영구적으로 보관하기 위해 클라우드 서비스를 사용합니다.
      * **데이터베이스**: Neon (PostgreSQL)
      * **파일 스토리지**: Cloudflare R2 (S3 호환)

## 기술 스택

  * **Backend**: Python, FastAPI
  * **Database**: PostgreSQL, SQLAlchemy
  * **Storage**: Cloudflare R2, boto3
  * **Server**: Uvicorn

## 로컬 개발 환경 설정

#### 1\. 소스 코드 복제

```bash
git clone <당신의_GitHub_저장소_URL>
cd <프로젝트_폴더명>
```

#### 2\. 파이썬 가상 환경 생성 및 활성화

프로젝트별로 독립된 개발 환경을 사용하기 위해 가상 환경을 생성합니다.

```bash
# 가상 환경 생성
python -m venv .venv

# 가상 환경 활성화 (Windows)
.venv\Scripts\activate

# 가상 환경 활성화 (macOS/Linux)
source .venv/bin/activate
```

#### 3\. 필요 패키지 설치

`requirements.txt` 파일을 사용하여 프로젝트에 필요한 모든 라이브러리를 설치합니다.

```bash
pip install -r requirements.txt
```

#### 4\. 환경 변수 설정

프로젝트 루트 폴더에 `.env` 파일을 생성하고, 아래 형식에 맞게 당신의 Neon DB 및 Cloudflare R2 접속 정보를 입력하세요. 이 파일은 민감한 정보를 담고 있으므로 Git 저장소에 포함되어서는 안 됩니다.

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

## 서버 실행

모든 설정이 완료되었다면, 아래 명령어를 통해 로컬 테스트 서버를 실행할 수 있습니다.

```bash
uvicorn main:app --reload
```

서버는 `http://127.0.0.1:8000` 주소에서 실행됩니다.

## API 엔드포인트

  * `GET /healthz`: 서버의 상태를 확인합니다.
  * `POST /qr-events`: QR 이벤트 데이터를 기록합니다.
  * `POST /access-events`: 출입 이벤트 데이터와 이미지를 기록합니다.
  * `POST /registrations`: 등록 이벤트 데이터와 이미지들을 기록합니다.
