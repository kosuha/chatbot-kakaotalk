import tiktoken
from pytz import timezone

def count_tokens(messages, model="gpt-3.5-turbo"):
    """메시지 리스트의 총 토큰 수를 계산합니다."""
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = 0
    for message in messages:
        # 각 메시지마다 기본 토큰 (role, content 필드) 추가
        num_tokens += 4
        # 메시지 내용의 토큰 수 계산
        for key, value in message.items():
            num_tokens += len(encoding.encode(str(value)))
    # 포맷 관련 토큰 추가
    num_tokens += 2
    return num_tokens

def time_to_korean(time):
    return time.astimezone(timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')