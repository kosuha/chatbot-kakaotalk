# 변수 정의
APP_NAME = chatbot-kakaotalk
PORT = 4242

# .env 파일에서 환경변수 로드 (없으면 무시)
-include .env

# 기본 명령어
.PHONY: build run stop clean help

# 도움말
help:
	@echo "사용 가능한 명령어:"
	@echo "make build    - Docker 이미지 빌드"
	@echo "make run      - Docker 컨테이너 실행"
	@echo "make stop     - Docker 컨테이너 중지"
	@echo "make clean    - Docker 컨테이너와 이미지 삭제"
	@echo "make logs     - 컨테이너 로그 확인"
	@echo "make re       - 컨테이너 재시작"

# Docker 이미지 빌드
build:
	docker build -t $(APP_NAME) .

# Docker 컨테이너 실행
run:
	@if [ -z "$(OPENAI_API_KEY)" ]; then \
		echo "Error: OPENAI_API_KEY is not set"; \
		exit 1; \
	fi
	@if [ -z "$(PERPLEXITY_API_KEY)" ]; then \
		echo "Error: PERPLEXITY_API_KEY is not set"; \
		exit 1; \
	fi
	docker run -d \
		--name $(APP_NAME) \
		-p $(PORT):$(PORT) \
		-e OPENAI_API_KEY=$(OPENAI_API_KEY) \
		-e PERPLEXITY_API_KEY=$(PERPLEXITY_API_KEY) \
		$(APP_NAME)

# Docker 컨테이너 중지
stop:
	docker stop $(APP_NAME) || true
	docker rm $(APP_NAME) || true

# Docker 컨테이너와 이미지 삭제
clean: stop
	docker rmi $(APP_NAME) || true

# 로그 확인
logs:
	docker logs -f $(APP_NAME)

# 컨테이너 재시작
re: stop clean build run

# 개발 환경 설정
dev-setup:
	pip install -r requirements.txt

# 로컬에서 실행
dev-run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port $(PORT) 