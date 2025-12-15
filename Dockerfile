# Dockerfile
FROM python:3.9-slim

# 작업 폴더 설정
WORKDIR /app

# 라이브러리 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스코드 복사
COPY . .

# 인스턴스 폴더 생성 (DB용)
RUN mkdir -p instance

# 포트 설정 (Cloud Run 기본값 8080)
ENV PORT=8080

# 실행 명령어 (Gunicorn 사용)
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app