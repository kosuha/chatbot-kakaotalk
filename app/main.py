from fastapi import FastAPI, Request
from pydantic import BaseModel
from openai import OpenAI
from datetime import datetime
from app.utils import count_tokens, time_to_korean
from pytz import timezone
import os
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re
app = FastAPI()

openai_model = "gpt-4o"
perplexity_model = "llama-3.1-sonar-small-128k-online"
chat_data = {}

# Request Body 모델 정의
class RequestChatMessage(BaseModel):
    room: str
    channelId: str
    content: str
    isDebugRoom: bool
    isGroupChat: bool
    sender: str
    senderHash: str
    isMention: bool
    packageName: str
    logId: str

class RequestCommandMessage(BaseModel):
    room: str
    channelId: str
    content: str
    isDebugRoom: bool
    isGroupChat: bool
    sender: str
    senderHash: str
    isMention: bool
    packageName: str
    command: str
    args: list
    logId: str

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/onMessage")
async def on_message(request_message: RequestChatMessage):
    print("on_message", request_message.content)
    try:
        response_message = {}
        is_reply = False

        # 메시지 수신 처리
        # chat_data에 채팅방 아이디가 없으면 채팅방 아이디를 추가
        if request_message.channelId not in chat_data:
            chat_data[request_message.channelId] = []
        # chat_data에 채팅방 아이디가 있으면 채팅방 아이디에 메시지를 추가
        message = {
            "room": request_message.room,
            "channel_id": request_message.channelId,
            "content": request_message.content,
            "is_debug_room": request_message.isDebugRoom,
            "is_group_chat": request_message.isGroupChat,
            "sender": request_message.sender,
            "sender_hash": request_message.senderHash,
            "is_mention": request_message.isMention,
            "package_name": request_message.packageName,
            "log_id": request_message.logId,
            "is_bot": False,
            "created_at": datetime.now(timezone('Asia/Seoul'))
        }
        chat_data[request_message.channelId].append(message)

        if (message.get('is_group_chat') and message.get('is_mention') and "[나를 멘션]" in message.get('content')) or (not message.get('is_group_chat')):
            print("request_message",request_message.content)
            is_reply = True

            response_dict = openai_generate_response(request_message.channelId)
            print("response_dict", response_dict)
            response_message = {
                "room": request_message.room,
                "channel_id": request_message.channelId,
                "content": response_dict.get('reply'),
                "is_debug_room": request_message.isDebugRoom,
                "is_group_chat": request_message.isGroupChat,
                "sender": "bot",
                "sender_hash": "bot",
                "is_mention": False,
                "package_name": request_message.packageName,
                "log_id": request_message.logId,
                "is_bot": True,
                "created_at": datetime.now(timezone('Asia/Seoul'))
            }

            if response_dict.get('type') == "answer":
                print("답변생성", response_dict)
                response_message['content'] = response_dict.get('reply')
            elif response_dict.get('type') == "search":
                # 검색요청
                print("검색요청", response_dict.get('instruction'))
                perplexity_response = perplexity_generate_response(response_dict.get('instruction'))
                
                if perplexity_response.get('status') == "success":
                    reply_content = ""
                    reply_content += f"{perplexity_response.get('content').replace('**', '')}\n\n"
                    reply_content += f"### 출처\n\n"

                    for index, citation in enumerate(perplexity_response.get('citations')):
                        url_metadata = get_url_metadata(citation)
                        if url_metadata:
                            reply_content += f"[{index+1}] {citation}\n"
                            reply_content += f"{url_metadata.get('title')}\n"
                            reply_content += f"{url_metadata.get('description')}\n\n"
                        else:
                            reply_content += f"[{index+1}] {citation}\n"
                            reply_content += f"페이지에 접근하지 못했습니다.\n\n"
                
                    if response_dict.get('instruction_key'):
                        keyword = response_dict.get('instruction_key').replace(" ", "+")
                        reply_content += f"### 검색 키워드\n\n"
                        reply_content += f"네이버: https://search.naver.com/search.naver?query={keyword}\n"
                        reply_content += f"구글: https://www.google.com/search?q={keyword}\n"
                        reply_content += f"다음: https://search.daum.net/search?w=tot&q={keyword}\n"
                        reply_content += "\n"

                    print("검색결과", reply_content)
                    response_message['content'] = reply_content
                else:
                    response_message['content'] = "검색에 실패했습니다."
        
            chat_data[request_message.channelId].append(response_message)

        # 메모리 관리를 위해 배열 길이가 50을 넘으면 오래된 메시지를 삭제
        if len(chat_data[request_message.channelId]) > 50:
            chat_data[request_message.channelId] = chat_data[request_message.channelId][-50:]

        return {"status": "success", "message": response_message, "is_reply": is_reply}

    except Exception as e:
        return {"status": "error", "message": str(e)}

def openai_generate_response(channel_id):
    openai_client = OpenAI()

    print("openai_generate_response", channel_id)
    system_message = """당신은 AI 챗봇, 까톡봇이다. 당신은 곧 user에게 당신이 속한 채팅방의 대화내역을 입력받을 것이다.
당신의 역할은 채팅방 참여자들의 대화를 이해하고 대화의 맥락상 마지막 메시지에 대한 적절한 대응으로 바로 답변할지 검색을 할지 판단하여 출력 생성 형식에 맞는 결과를 반환하는 것이다. 아래 지시사항을 철저히 따르라.

# 출력 생성 형식
- 출력 생성 형식은 딕셔너리 형태로 key는 "type", "reply", "instruction", "instruction_key"이다.
    예시1: {"type": "search", "reply": "강남역 맛집을 찾아드릴게요.", "instruction": "강남역 맛집을 찾아줘", "instruction_key": "강남역 맛집"}
    예시2: {"type": "answer", "reply": "안녕하세요"}
    예시3: {"type": "search", "reply": "오늘 날씨입니다.", "instruction": "오늘 날씨 알려줘", "instruction_key": "오늘 날씨"}
    예시4: {"type": "answer", "reply": "반가워요!"}
- 출력은 파싱할 수 있도록 반드시 딕셔너리만 출력한다.
- 출력을 그대로 딕셔너리로 파싱했을때 오류가 발생하지 않도록 출력 생성 형식을 철저히 따른다.
- "type"의 value는 출력의 종류를 나타내는 문자열로 검색은 "search", 답변은 "answer"이다.
- "reply"의 value는 채팅방에 보낼 메시지를 저장하는 문자열이다.
- "instruction"의 value는 검색을 담당하는 AI에게 전달할 명령어 문자열이다. "type"이 "search"인 경우에만 존재한다.
- "instruction_key"의 value는 검색을 담당하는 AI에게 전달할 명령어의 키워드 문자열이다. 이것은 검색포탈 링크를 사용자에게 제공하기 위한 것이다. "type"이 "search"인 경우에만 존재한다.

# 마지막 메시지에 대응하는 규칙
- 우선 대화의 맥락을 파악하고 마지막 메시지의 의미를 분석한다.
- 마지막 메시지의 의미를 분석하여 검색이 필요한지 판단한다.
- 마지막 메시지의 요청이 실행 불가능하다면 반드시 거절하는 답변을 해야한다.
- 미래에 대한 행동을 요청받으면 당신이 수행할 수 없는 요청이므로 친절하게 거절한다.
- 마지막 메시지에 대화의 맥락에 따라 답변이 가능하다면 검색이 필요하지 않다고 판단하여 바로 답변을 생성한다.
- 검색이 필요한 경우는 "찾아주세요", "추천해주세요", "알려줘"와 같은 의미의 메시지가 포함됐을 가능성이 높다.
- 검색이 필요하다고 판단되는 경우, "type"의 value는 "search"이고 "reply"의 value는 마지막 메시지에 대한 내용을 찾아보겠다는 의미의 답변이고 "instruction"의 value는 검색을 위한 명령어이다. "instruction_key"의 value는 검색포탈 링크를 사용자에게 제공하기 위한 검색 키워드이다.
- 검색이 필요하지 않다고 판단되는 경우, "type"의 value는 "answer"이고 "reply"의 value는 마지막 메시지에 대한 답변이다.
- 메시지는 사람과 같이 친근한 말투로 존댓말을 사용한다.

# 채팅 규칙
- 주어진 채팅기록의 형식은 "{{sender}}({{created_at}}): {{content}}"이다.
- 채팅기록의 형식은 채팅 참여자를 구분하고 시간을 표시하기 위한 것이다.
- sender는 채팅 참여자의 이름이다.
- created_at은 채팅 참여자의 메시지 생성 시간으로 한국시간을 사용한다.
- content는 채팅 참여자가 보낸 메시지 내용이다.
- 당신이 메시지를 생성할때는 content만 생성한다.
    """

    chat_history = ""
    
    # 각 참여자의 메시지를 개별적으로 추가 (hash 포함)
    print("chat_data[channel_id]", chat_data[channel_id])
    for chat in chat_data[channel_id]:
        print("chat", chat.get('content'))
        if chat['is_bot']:
            chat_history += f"[까톡봇({time_to_korean(chat['created_at'])}): {chat['content']}]\n"
        else:
            chat_history += f"[{chat['sender']}({time_to_korean(chat['created_at'])}): {chat['content']}]\n"
    
    messages = [
        {
            "role": "system", 
            "content": system_message
        },
        {
            "role": "user",
            "content": chat_history
        }
    ]

    print("openai_generate_response 0", messages)

    # 토큰 수 확인 및 제한
    while count_tokens(messages) > 100000:
        if len(messages) > 2:  # system 메시지 보존
            messages.pop(1)

    print("openai_generate_response 1", messages)
    
    # OpenAI API 호출
    response = openai_client.chat.completions.create(
        model=openai_model,
        messages=messages,
        temperature=0.7,
        max_tokens=1000
    )

    print("openai_generate_response 2", response)

    # 생성된 텍스트 파싱
    response_text = response.choices[0].message.content.strip()
    print("\n\nopenai_generate_response response_text", response_text)
    try:
        parsed_response = json.loads(response_text)
        print("\n\nopenai_generate_response parsed_response", parsed_response)
        return parsed_response

    except json.JSONDecodeError:
        print("ERROR: json.JSONDecodeError", response_text, "\n", messages)
        return {"type": "answer", "reply": response_text}
    except Exception as e:
        print("ERROR: Exception", e)
    
    return {"type": "answer", "reply": "검색에 실패했습니다."}

def perplexity_generate_response(instruction):
    perplexity_client = OpenAI(
        api_key=os.getenv("PERPLEXITY_API_KEY"),
        base_url="https://api.perplexity.ai"
    )
    print("perplexity_generate_response", instruction)
    system_message = "당신은 검색을 담당하는 AI이다. 주어진 명령을 분석한 후, 최적의 검색 결과를 반환하라. 답변은 사람과 같이 친근한 말투로 존댓말을 사용한다."
    messages = [
        {
            "role": "system", 
            "content": system_message
        },
        {
            "role": "user",
            "content": instruction
        }
    ]
    response = perplexity_client.chat.completions.create(
        model=perplexity_model,
        messages=messages,
        temperature=0.7
    )
    print("perplexity_generate_response response", response)
    return {
        "status": "success",
        "citations": response.citations, # 참고 문헌, 문자열 배열
        "content": response.choices[0].message.content.strip() # 생성된 답변, 문자열
    }

def get_url_metadata(url):
    try:
        # User-Agent 헤더 추가
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # URL이 유효한지 확인
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            return None

        # GET 요청 보내기
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()  # HTTP 에러 체크
        
        # 인코딩 설정
        response.encoding = response.apparent_encoding
        
        # HTML 파싱
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 타이틀 찾기
        title_tag = soup.find('title')
        title = title_tag.string if title_tag else None

        # 페이지 설명
        description_tag = soup.find('meta', attrs={'name': 'description'})
        description = description_tag.get('content') if description_tag else None
        # 설명이 너무 길면 자르기
        if description and len(description) > 50:
            description = description[:50] + "..."

        # 타이틀 정제 (불필요한 공백 제거)
        if title:
            title = re.sub(r'\s+', ' ', title).strip()
            
        return {
            "title": title,
            "description": description
        }

    except Exception as e:
        print(f"Error fetching title: {str(e)}")
        return None