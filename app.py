import json, os
import gradio as gr
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request, Header, BackgroundTasks, HTTPException
import google.generativeai as genai
import requests
from PIL import Image
from io import BytesIO
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from linebot.v3.messaging import MessagingApi  # 取代 LineBotApi
from linebot.v3.webhook import WebhookHandler  # ✅ 新版 WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot import LineBotApi

# 載入 .env 變數
load_dotenv()


# 設定 Google Gemini AI API 金鑰
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
# 設定 Gemini 文字生成參數
generation_config = genai.types.GenerationConfig(
    max_output_tokens=2048, temperature=0.2, top_p=0.5, top_k=16
    )
model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config=generation_config,
    system_instruction=(
    "你是一個專業的醫療輔助機器人，只能回答與醫療相關的問題。"
    "請根據你的知識，提供準確、簡潔、符合醫療建議的回答。"
    "如果問題超出你的專業範圍，請回答「抱歉，我無法回答這個問題，請諮詢專業醫生。」"
    )
)

# 設定 Line Bot API 金鑰
line_bot_api = LineBotApi(os.getenv("CHANNEL_ACCESS_TOKEN"))
line_handler = WebhookHandler(os.getenv("CHANNEL_SECRET"))

# 設定是否與使用者交談
working_status = os.getenv("DEFALUT_TALKING", default="true").lower() == "true"


# 建立 FastAPI 應用程式
app = FastAPI()

# 設定 CORS，允許跨域請求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 根路徑請求
@app.get("/")
def root():
    return {"title": "Line Bot"}

# Line Webhook 路由
@app.post("/webhook")
async def webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_line_signature=Header(None),
):
    body = await request.body()
    try:
        background_tasks.add_task(
            line_handler.handle, body.decode("utf-8"), x_line_signature
        )
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    return "ok"

# 🔹 2️⃣ 修改 Line Bot 的訊息處理邏輯
@line_handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global working_status

    if event.type != "message" or event.message.type != "text":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入文字問題。"))
        return

    # 建立要發送的訊息
    message = """您好！
我將推薦符合您症狀的藥用植物🌿
請選擇以下最符合您症狀的種類(A~E):
A: 呼吸系統與感冒問題
B: 消化與代謝問題
C: 皮膚與過敏問題
D: 循環與泌尿系統問題
E: 身心與內分泌問題
X: 以上沒有符合我的症狀種類"""

    # 使用 Line Bot API 回覆訊息
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message))
    

 

if __name__ == "__main__":
    uvicorn.run(host="0.0.0.0", port=8000, reload=True)