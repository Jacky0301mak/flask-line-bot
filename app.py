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
detailed_input = input("請詳細描述您的症狀: ")
try:
    ai_response = model.generate_content(detailed_input)
    response_text = ai_response.text if ai_response.text else "抱歉，我無法理解你的問題，請換個方式問問看～"
    print('\n'+response_text)
  except:
    response_text = "Gemini 執行出錯，請稍後再試！"
    print(response_text)
  return  # **停止函數執行**

   Symptom_classification = {
    '呼吸系統與感冒相關': ['感冒', '頭痛', '咳嗽', '痰多', '喉嚨痛', '喉嚨發炎', '氣喘', '肺熱', '無'],
    '消化與代謝問題': ['消化不良', '腸胃不適', '胃痛', '腹瀉', '便秘', '高血糖', '口渴', '口乾舌燥', '食慾不振', '無'],
    '皮膚與過敏相關': ['皮膚紅腫', '瘡癤感染', '皮膚炎', '皮膚搔癢', '過敏反應', '燙傷', '蚊蟲叮咬', '水腫', '無'],
    '循環與泌尿系統': ['高血壓', '貧血', '血尿', '尿道感染', '腎臟問題', '心悸', '止血', '無'],
    '身心與內分泌問題': ['免疫力低下', '月經不調', '失眠', '焦慮', '眼睛疲勞', '肝火旺盛', '疲勞', '痛風', '無']
}
Symptom_questions = {
    '感冒': {
        'A': '頭痛、鼻塞、畏寒、四肢乏力，對冷空氣敏感，體溫正常或僅微微升高.',
        'B': '咽喉腫痛、聲音嘶啞、體溫超過 38°C、口乾舌燥、咽部灼熱，可能有輕微口腔潰瘍.',
        'C': '頻繁咳嗽、咳痰不暢，痰液粘稠難以排出，夜間或清晨加重，可能伴隨氣喘或胸悶.',
        'D': '近期多次感冒，症狀緩解後容易復發，對環境變化(季節交替、氣溫變化)敏感.',
        'E': '皮膚紅腫、過敏、蕁麻疹，或感冒期間出現輕微皮疹及發癢症狀.'
           },
    '喉嚨痛': {
        'A': '喉嚨乾燥、灼熱，異物感明顯，喝水無法緩解.',
        'B': '咽喉紅腫疼痛，吞嚥困難，甚至影響進食與說話.',
        'C': '伴隨咳嗽，痰少或無痰，咳嗽時喉嚨不適加重.'
           },
    '消化不良': {
        'A': '飯後胃脹氣、噯氣，腹部悶脹不適，進食過快時加重.',
        'B': '腸胃蠕動緩慢，排便困難，食物消化速度明顯變慢.',
        'C': '腸胃蠕動緩慢，排便困難，食物胃痛，飯後不適加重，進食油膩或辛辣食物時更嚴重.',
        'D': '胃寒，容易腹瀉，進食生冷食物後症狀加劇.',
        'E': '進食後胃悶脹，飽腹感持續時間較長，消化時間延長.',
        'F': '胃酸分泌過多，容易泛酸，胸口有灼熱感，易反胃.',
        'G': '腹瀉頻繁，並伴隨食慾下降，進食後易腸鳴或不適.',
        'H': '肝火旺盛，口乾舌燥，口腔易有異味，食慾降低.',
        'I': '長時間便秘，排便困難，糞便乾燥，宿便堆積.',
        'J': '進食生冷食物後，容易引發腸胃疼痛或消化不適.',
        'K': '進食後頻繁打嗝，甚至影響說話與呼吸節奏.'
           },
    '口氣不清新': {
        'A': '口腔乾燥，舌苔厚膩，嘴巴有異味，早晨起床時尤為明顯.',
        'B': '飲食不當或消化不良後，口氣變重，伴隨胃部不適或脹氣感.'
           },
    '皮膚紅腫': {
        'A': '皮膚因過敏或接觸刺激物後出現紅腫，可能伴隨搔癢、輕微脫皮或紅疹.',
        'B': '皮膚紅腫且局部發炎，可能伴隨膿皰或傷口感染，按壓時有疼痛感.'
           },
    '燙傷': {
        'A': '皮膚發紅，局部腫脹，輕微刺痛，但沒有水泡.',
        'B': '燙傷處出現水泡，伴隨腫脹與疼痛，可能有滲液.',
        'C': '燙傷後皮膚灼熱感強烈，紅腫範圍擴大，受熱部位明顯發炎.',
        'D': '燙傷後傷口癒合緩慢，可能出現輕微潰爛或感染風險.'
           },
    '咳嗽': {
        'A': '乾咳無痰，喉嚨發癢，夜間或清晨時咳嗽加重.',
        'B': '咳嗽帶黃痰，痰多不易排出，胸悶，呼吸時有黏稠感.',
        'C': '咳嗽伴隨氣喘或過敏反應，每當接觸冷空氣或粉塵時加重.',
        'D': '受寒後咳嗽，鼻涕清稀，怕冷，通常伴隨輕微發熱.',
        'E': '喉嚨有異物感，總覺得卡痰但咳不出來，導致頻繁清喉嚨.',
        'F': '早晨起床時咳嗽嚴重，常有痰堵住喉嚨，需反覆咳出.',
        'G': '夜間咳嗽頻繁，影響睡眠，特別是躺下時症狀加重.'
           },
    '發燒': {
        'A': '低燒(37.5°C～38.5°C)，身體微熱但無明顯寒顫，伴隨口乾舌燥.',
        'B': '高燒(超過 38.5°C)，全身發熱，伴隨頭痛、口渴、精神疲憊.',
        'C': '反覆發燒，體溫波動較大，白天較低、夜間升高，可能合併其他炎症.',
        'D': '發燒同時伴隨喉嚨紅腫、皮膚發熱感，甚至出現輕微紅疹.'
           },
    '皮膚炎': {
        'A': '皮膚紅腫、發熱，可能有滲液或輕微潰爛，伴隨刺痛感.',
        'B': '皮膚乾燥、脫屑，長期搔癢，抓破後可能出現紅腫或結痂.'
           },
    '腹瀉': {
        'A': '腹部絞痛，排便次數增加，糞便呈水狀或半流質，可能伴隨噯氣或腸鳴.',
        'B': '飲食後腸胃蠕動過快，出現腹瀉，且容易因生冷食物或油膩食物誘發.'
           },
    '高血壓': {
        'A': '血壓升高時伴隨頭暈、頭痛、視力模糊，易感到疲勞.',
        'B': '高血壓合併焦慮、失眠，夜間睡眠品質差，容易驚醒.',
        'C': '血壓偏高，四肢容易水腫，手腳冰冷，疲勞感增加.',
        'D': '血壓升高時伴隨口乾舌燥、煩躁易怒，甚至有口苦現象.',
        'E': '長期高血壓影響腸胃，伴隨消化不良或排便異常.',
        'F': '高血壓患者同時皮膚容易發紅、發炎或長期乾燥.',
        'G': '伴隨便秘，排便困難，糞便乾硬，腸胃蠕動較慢.'
           },
    '水腫': {
        'A': '下肢水腫，雙腳容易腫脹，站立過久或久坐後加重.',
        'B': '水腫主要發生在眼瞼或臉部，早晨起床時較為明顯.',
        'C': '腹部脹氣，感覺腸胃滯留水分，容易消化不良或便秘.',
           },
    '失眠': {
        'A': '難以入睡，躺很久都無法進入睡眠，夜間思緒活躍.',
        'B': '半夜容易驚醒，醒後難以再次入睡，睡眠品質差.',
        'C': '白天精神不濟，容易疲倦嗜睡，但晚上精神異常興奮.'
           },
    '焦慮': {
        'A': '長期緊張不安，容易因小事感到壓力，影響專注力與情緒穩定.',
        'B': '焦慮伴隨心悸、胸悶，偶爾有呼吸急促的情況，甚至感到恐慌.',
        'C': '焦慮影響睡眠，容易失眠、多夢，醒來後仍感疲勞'
           },
    '腸胃不適': {
        'A': '胃部隱隱作痛，進食後加重，容易感到噁心或反胃.',
        'B': '消化不良，進食後腹脹、腸胃悶滯，飽腹感持續較長時間.',
        'C': '胃腸功能虛弱，容易腹瀉或腹部發涼，對冷食較敏感.',
        'D': '腸胃蠕動異常，進食後易感到腸鳴，排便頻繁或不規律.'
           },
    '免疫力低下': {
        'A': '容易感冒或感染，身體恢復速度慢，經常覺得疲倦乏力.',
        'B': '季節變化時容易過敏，皮膚或呼吸道特別敏感，經常出現過敏反應.'
           },
    '氣喘': {
        'A': '天氣變冷時氣喘加重，吸入冷空氣後容易發作，伴隨鼻塞或流鼻水.',
        'B': '運動後容易喘，稍微劇烈活動就感到呼吸急促，恢復時間較長.',
        'C': '咳嗽帶痰且伴隨氣喘，尤其是痰多時氣喘症狀會加劇.',
        'D': '氣喘發作時胸悶，吸氣困難，深呼吸時感覺肺部不順暢.'
           },
    '肺熱': {
        'A': '乾咳少痰或無痰，喉嚨乾燥，口渴，可能伴隨輕微發熱.',
        'B': '咳痰呈黃稠狀，胸悶，可能伴隨喉嚨紅腫或咽痛.'
           },
    '口乾舌燥': {
        'A': '口乾明顯，舌苔偏黃厚膩，可能伴隨口苦、煩躁易怒.',
        'B': '口乾但口中無異味，舌苔較薄，常覺得口渴且想喝涼水.',
        'C': '口乾舌燥，且容易便秘，皮膚偏乾燥，容易感到疲勞.'
           },
    '胃痛': {
        'A': '胃部隱隱作痛，飯前或空腹時加重，進食後可稍微緩解.',
        'B': '胃痛伴隨消化不良，進食後脹氣、胃悶，甚至噯氣或反酸.',
        'C': '胃痛時感到腸胃蠕動異常，偶爾伴隨腹瀉或排便不規律'
           },
    '便秘': {
        'A': '排便困難，糞便乾硬，排便次數減少，伴隨口乾舌燥.',
        'B': '長期便祕，容易脹氣或腹部脹滿，排便不規律.',
        'C': '排便時感到腸道蠕動不足，經常需要很用力才排得出來.'
           },
    '肝火旺盛': {
        'A': '口乾舌燥，口苦，容易煩躁易怒，睡眠品質差.',
        'B': '眼睛紅腫或乾澀，頭部容易發熱，時常感到疲勞.'
           }
}
Symptom_answers = {
    '感冒_A': '紫蘇',
    '感冒_B': '薄荷',
    '感冒_C': '咸豐草',
    '感冒_D': '羅勒',
    '感冒_E': '蚌蘭',
    '喉嚨痛_A': '含羞草',
    '喉嚨痛_B': '紫蘇',
    '喉嚨痛_C': '薄荷',
    '消化不良_A': '薄荷',
    '消化不良_B': '紅鳳菜',
    '消化不良_C': '羅勒',
    '消化不良_D': '車前草',
    '消化不良_E': '咸豐草',
    '消化不良_F': '左手香',
    '消化不良_G': '酢漿草',
    '消化不良_H': '仙草',
    '消化不良_I': '苦瓜',
    '消化不良_J': '含羞草',
    '口氣不清新_A': '薄荷',
    '口氣不清新_B': '羅勒',
    '皮膚紅腫_A': '落地生根',
    '皮膚紅腫_B': '山芙蓉',
    '燙傷_A': '蚌蘭',
    '燙傷_B': '山芙蓉',
    '燙傷_C': '落地生根',
    '燙傷_D': '左手香',
    '咳嗽_A': '台灣百合',
    '咳嗽_B': '腎蕨',
    '咳嗽_C': '車前草',
    '咳嗽_D': '咸豐草',
    '咳嗽_E': '羅勒',
    '咳嗽_F': '山芙蓉',
    '咳嗽_G': '美人蕉',
    '發燒_A': '咸豐草',
    '發燒_B': '仙草',
    '發燒_C': '蚌蘭',
    '發燒_D': '朱蕉',
    '皮膚炎_A': '朱蕉',
    '皮膚炎_B': '左手香',
    '腹瀉_A': '美人蕉',
    '腹瀉_B': '酢漿草',
    '高血壓_A': '台灣百合',
    '高血壓_B': '仙草',
    '高血壓_C': '美人蕉',
    '高血壓_D': '枸杞',
    '高血壓_E': '山藥',
    '高血壓_F': '紅鳳菜',
    '高血壓_G': '苦瓜',
    '水腫_A': '美人蕉',
    '水腫_B': '車前草',
    '水腫_C': '落地生根',
    '失眠_A': '含羞草',
    '失眠_B': '台灣百合',
    '失眠_C': '枸杞',
    '焦慮_A': '含羞草',
    '焦慮_B': '紫蘇',
    '焦慮_C': '羅勒',
    '腸胃不適_A': '朱蕉',
    '腸胃不適_B': '落地生根',
    '腸胃不適_C': '山藥',
    '腸胃不適_D': '含羞草',
    '免疫力低下_A': '枸杞',
    '免疫力低下_B': '山藥',
    '氣喘_A': '紫蘇',
    '氣喘_B': '左手香',
    '氣喘_C': '咸豐草',
    '氣喘_D': '腎蕨',
    '肺熱_A': '台灣百合',
    '肺熱_B': '腎蕨',
    '口乾舌燥_A': '酢漿草',
    '口乾舌燥_B': '仙草',
    '口乾舌燥_C': '紅鳳菜',
    '胃痛_A': '山藥',
    '胃痛_B': '羅勒',
    '胃痛_C': '酢漿草',
    '便秘_A': '仙草',
    '便秘_B': '紅鳳菜',
    '便秘_C': '苦瓜',
    '肝火旺盛_A': '酢漿草',
    '肝火旺盛_B': '枸杞'
}

single_choice = {
    '頭痛': '薄荷',
    '瘡癤感染': '山芙蓉',
    '喉嚨發炎': '山芙蓉',
    '月經不調': '朱蕉',
    '血尿': '朱蕉',
    '痛風': '美人蕉',
    '皮膚瘙癢': '蚌蘭',
    '過敏反應': '蚌蘭',
    '眼睛疲勞': '枸杞',
    '痰多': '腎蕨',
    '心悸': '台灣百合',
    '止血': '落地生根',
    '貧血': '紅鳳菜',
    '蚊蟲叮咬': '左手香',
    '高血糖': '苦瓜',
    '口渴': '苦瓜',
    '疲勞': '山藥',
    '尿道感染': '車前草',
    '腎臟問題': '車前草',
}

response = {
    '薄荷':[
        '營養成分',
        '1. 薄荷醇（Menthol）：主要活性成分，具清涼感，能舒緩不適。',
        '2. 揮發油：如薄荷酮、薄荷酯等，具抗菌、抗病毒作用。',
        '3. 多酚類化合物：如黃酮類與迷迭香酸，具有抗氧化與抗發炎作用。',
        '4. 維生素與礦物質：含維生素A、C、鈣、鎂、鉀，有助於維持免疫力與電解質平衡。',
        '5. 膳食纖維：促進腸道蠕動，幫助消化與腸道健康。',

        '健康功效',
        '1. 舒緩腸胃不適：可放鬆腸道平滑肌，減少胃脹氣、腸絞痛與消化不良。',
	      '2. 緩解呼吸道症狀：薄荷醇能舒緩喉嚨不適，幫助清除痰液，減少鼻塞。'
	      '3. 提升專注力與舒緩壓力：薄荷香氣能刺激神經系統，提高專注力並減少疲勞。',
	      '4. 抗菌與抗發炎：揮發油與多酚成分能幫助對抗細菌與病毒感染。',
	      '5. 幫助降溫與解熱：適合發燒或燥熱時飲用，能幫助身體降溫。',
	      '6. 減少口氣異味：薄荷的清涼感與抗菌作用能有效改善口臭。',

        '烹調方式',
	      '1. 薄荷茶：用新鮮或乾燥薄荷葉沖泡，可單獨飲用或搭配蜂蜜、檸檬增添風味。',
	      '2. 薄荷水：將新鮮薄荷葉泡入冷水中，可加入檸檬片、黃瓜片，製成清爽飲品。',
	      '3. 薄荷調味：剁碎後加入沙拉、湯品、醬料或拌炒料理中，增加清新口感。',
	      '4. 薄荷甜點：可用於製作薄荷巧克力、冰淇淋、蛋糕等甜品。',
	      '5. 薄荷入菜：常見於中東與東南亞料理，如薄荷羊肉、越南春捲等。',
	      '6. 薄荷油：可滴入溫水或搭配精油擴香，有助於放鬆身心與緩解鼻塞。',

        '建議食用量',
	      '• 一般健康成人：每日 5~10克新鮮薄荷葉（約12小撮）或 **12克乾燥薄荷葉**，適量食用可促進消化與舒緩壓力。',
	      '• 腸胃敏感者：建議每日 5克內，避免刺激腸胃造成不適。',
	      '• 孕婦與哺乳婦女：適量食用（每日 5克內），避免影響荷爾蒙與乳汁分泌。',
	      '• 高血壓或低血壓者：少量食用（每日 5克內），避免影響血壓調節。',
	      '• 兒童：建議適量減少至 2~5克，以免過量影響腸胃或神經系統。',

        '⚠注意事項⚠',
	      '• 胃食道逆流患者不宜過量食用，以免刺激胃酸分泌，加重不適。',
	      '• 薄荷精油不建議直接內服，可能引起腸胃不適或神經系統刺激。',
	      '• 過量食用可能導致低血壓或影響鐵質吸收，應適量控制攝取量。'],
    '山芙蓉':[
        '營養成分',
        '1. 花青素：具有強大的抗氧化能力，能保護細胞免受自由基的損害。',
        '2. 類黃酮：具有抗炎、抗病毒和抗癌的潛在作用。',
        '3. 多醣體：可能具有免疫調節作用，有助於增強免疫系統。',
        '4. 纖維：有助於促進腸道蠕動，改善消化功能。',
        '5. 維生素和礦物質：含有少量維生素C、鈣和鉀等。',

        '健康功效',
        '1. 抗氧化：花青素能清除自由基，延緩衰老，保護心血管健康。',
        '2. 抗發炎：類黃酮有助於減輕炎症反應，緩解關節疼痛等症狀。',
        '3. 免疫調節：多醣體可能增強免疫細胞活性，提高抵抗力。',
        '4. 促進消化：纖維有助於改善便秘，維持腸道健康。',
        '5. 美容養顏：花青素有助於改善皮膚彈性，減少皺紋。',
        '6. 潛在的抗癌作用：部分研究顯示類黃酮可能具有抑制癌細胞生長的作用，但仍需更多研究證實。',

        '烹調方式',
        '1. 芙蓉花茶：將新鮮或乾燥的山芙蓉花瓣沖泡成茶，可單獨飲用或搭配蜂蜜、檸檬。',
        '2. 芙蓉花粥：將新鮮芙蓉花瓣加入粥中，增加風味和營養。',
        '3. 芙蓉花沙拉：將新鮮芙蓉花瓣加入沙拉中，增添色彩和口感。',
        '4. 芙蓉花蜜餞：將芙蓉花瓣醃製成蜜餞，作為零食或甜點。',
        '5. 芙蓉花酒：將芙蓉花浸泡在酒中，製成花酒。',
        '6. 芙蓉花面膜：將芙蓉花瓣搗碎後敷在臉上，有助於保濕和美白。',

        '建議食用量',
        '• 一般健康成人：每日 3~5朵新鮮芙蓉花或 **3~5克乾燥芙蓉花**，適量食用可促進健康。',
        '• 腸胃敏感者：建議少量食用，避免引起不適。',
        '• 孕婦與哺乳婦女：建議諮詢醫生後再食用。',
        '• 特殊疾病患者：建議諮詢醫生後再食用。',
        '• 兒童：建議適量減少。',

        '⚠注意事項⚠',
        '• 部分人可能對芙蓉花過敏，食用前應先確認是否過敏。',
        '• 芙蓉花性涼，體質虛寒者不宜過量食用。',
        '• 芙蓉花可能影響藥物吸收，正在服用藥物者應諮詢醫生後再食用。',
        '• 請勿採食路邊或不明來源的芙蓉花，以免受到污染。'],
    '朱蕉':[
        '營養成分',
        '1. 多酚類化合物：如黃酮類和酚酸，具有抗氧化和抗炎作用。',
        '2. 皂苷：可能具有免疫調節和抗癌的潛在作用。',
        '3. 碳水化合物：提供能量。',
        '4. 纖維：有助於促進腸道蠕動，改善消化功能。',
        '5. 維生素和礦物質：含有少量維生素C、鈣和鉀等。',

        '健康功效',
        '1. 抗氧化：多酚類化合物能清除自由基，延緩衰老，保護細胞健康。',
        '2. 抗發炎：多酚類化合物有助於減輕炎症反應。',
        '3. 免疫調節：皂苷可能增強免疫細胞活性，提高抵抗力。',
        '4. 促進消化：纖維有助於改善便秘，維持腸道健康。',
        '5. 潛在的抗癌作用：部分研究顯示皂苷可能具有抑制癌細胞生長的作用，但仍需更多研究證實。',
        '6. 觀賞價值：鮮豔的葉片具有觀賞價值，可舒緩心情。',

        '烹調方式',
        '1. 藥膳：在某些地區，朱蕉的根、莖和葉被用於藥膳，但需在專業人士指導下使用。',
        '2. 觀賞：主要作為觀賞植物，不建議直接食用。',
        '3. 染色：葉片可用於天然染色。',
        '4. 民間療法：在某些文化中，朱蕉被用於治療跌打損傷等，但缺乏科學證據。',
        '5. 泡茶 (不建議)：雖然有人會將朱蕉葉曬乾後泡茶，但由於缺乏安全性研究，不建議自行嘗試。',

        '建議食用量',
        '• 一般情況下，不建議食用朱蕉。若要用於藥膳，必須在專業人士指導下進行。',
        '• 觀賞用途為主，請勿自行食用。',

        '⚠注意事項⚠',
        '• 朱蕉含有皂苷等成分，可能具有毒性，不宜生食。',
        '• 孕婦、哺乳婦女和兒童應避免食用。',
        '• 若接觸朱蕉汁液後出現皮膚過敏等不適，應立即清洗並就醫。',
        '• 請勿自行採摘和食用朱蕉，以免發生中毒。',
        '• 由於缺乏安全性研究，不建議將朱蕉用於食品或茶飲。'],
        '美人蕉':[
        '營養成分',
        '1. 澱粉：主要成分，提供能量。',
        '2. 纖維：有助於促進腸道蠕動，改善消化功能。',
        '3. 多酚類化合物：如黃酮類和酚酸，具有抗氧化和抗炎作用（含量較低）。',
        '4. 維生素和礦物質：含有少量維生素C、鈣和鉀等。',

        '健康功效',
        '1. 提供能量：澱粉是主要能量來源。',
        '2. 促進消化：纖維有助於改善便秘，維持腸道健康。',
        '3. 觀賞價值：鮮豔的花朵具有觀賞價值，可舒緩心情。',
        '4. 傳統用途：在某些地區，美人蕉的根莖被用於傳統醫學，但需謹慎使用。',

        '烹調方式',
        '1. 根莖食用：美人蕉的根莖可以煮熟後食用，類似馬鈴薯，但口感較差。',
        '2. 澱粉提取：根莖可以提取澱粉，用於製作食品。',
        '3. 觀賞：主要作為觀賞植物，花朵和葉片具有裝飾作用。',
        '4. 傳統醫學：在某些地區，美人蕉被用於傳統醫學，但需在專業人士指導下使用。',
        '5. 花朵食用 (不建議)：雖然有些文化會食用美人蕉的花朵，但由於可能含有微量毒素，不建議自行嘗試。',

        '建議食用量',
        '• 若要食用美人蕉的根莖，應少量食用，並確保完全煮熟。',
        '• 觀賞用途為主，請勿過量食用。',

        '⚠注意事項⚠',
        '• 美人蕉可能含有微量毒素，不宜生食。',
        '• 孕婦、哺乳婦女和兒童應謹慎食用。',
        '• 若食用後出現不適，應立即停止食用並就醫。',
        '• 請勿自行採摘和食用路邊的美人蕉，以免受到污染。',
        '• 由於缺乏安全性研究，不建議將美人蕉的花朵用於食品或茶飲。',
        '• 某些品種的美人蕉可能具有較高的毒性，應避免食用。'],
    '蚌蘭':[
        '營養成分',
        '1. 皂苷：可能具有抗炎、抗菌和抗腫瘤的潛在作用。',
        '2. 黃酮類化合物：具有抗氧化和抗炎作用。',
        '3. 多醣體：可能具有免疫調節作用。',
        '4. 纖維：有助於促進腸道蠕動，改善消化功能。',
        '5. 維生素和礦物質：含有少量維生素C、鈣和鉀等。',

        '健康功效',
        '1. 抗炎：皂苷和黃酮類化合物可能減輕炎症反應。',
        '2. 抗菌：皂苷可能抑制細菌生長。',
        '3. 免疫調節：多醣體可能增強免疫細胞活性，提高抵抗力。',
        '4. 促進消化：纖維有助於改善便秘，維持腸道健康。',
        '5. 傳統用途：在某些地區，蚌蘭被用於傳統醫學，但需謹慎使用。',
        '6. 觀賞價值：葉片具有觀賞價值，可舒緩心情。',

        '烹調方式',
        '1. 藥用：在某些地區，蚌蘭的葉片被用於藥用，但需在專業人士指導下使用。',
        '2. 觀賞：主要作為觀賞植物，不建議直接食用。',
        '3. 外用：搗碎的葉片可用於外敷，治療跌打損傷等，但缺乏科學證據。',
        '4. 泡茶 (不建議)：雖然有人會將蚌蘭葉曬乾後泡茶，但由於缺乏安全性研究，不建議自行嘗試。',

        '建議食用量',
        '• 一般情況下，不建議食用蚌蘭。若要用於藥用，必須在專業人士指導下進行。',
        '• 觀賞用途為主，請勿自行食用。',

        '⚠注意事項⚠',
        '• 蚌蘭含有皂苷等成分，可能具有毒性，不宜生食。',
        '• 孕婦、哺乳婦女和兒童應避免食用。',
        '• 若接觸蚌蘭汁液後出現皮膚過敏等不適，應立即清洗並就醫。',
        '• 請勿自行採摘和食用蚌蘭，以免發生中毒。',
        '• 由於缺乏安全性研究，不建議將蚌蘭用於食品或茶飲。',
        '• 過量食用可能導致腹瀉等不適。'],
    '含羞草':[
        '營養成分',
        '1. 含羞草鹼 (Mimosine)：一種非蛋白質胺基酸，具有潛在的毒性。',
        '2. 黃酮類化合物：具有抗氧化和抗炎作用（含量較低）。',
        '3. 單寧酸：具有收斂作用。',
        '4. 纖維：有助於促進腸道蠕動，改善消化功能（含量較低）。',
        '5. 維生素和礦物質：含有少量維生素C、鈣和鉀等。',

        '健康功效',
        '1. 傳統用途：在某些地區，含羞草被用於傳統醫學，具有鎮靜、止痛等作用，但需謹慎使用。',
        '2. 觀賞價值：葉片對觸摸的敏感反應具有觀賞價值，可舒緩心情。',
        '3. 潛在的藥理活性：研究顯示含羞草可能具有抗氧化、抗炎、抗菌等活性，但仍需更多研究證實。',

        '烹調方式',
        '1. 藥用：在某些地區，含羞草的根、莖和葉被用於藥用，但需在專業人士指導下使用。',
        '2. 觀賞：主要作為觀賞植物，不建議直接食用。',
        '3. 傳統醫學：在某些文化中，含羞草被用於治療失眠、疼痛等，但缺乏科學證據。',
        '4. 食用 (不建議)：雖然有些文化會食用含羞草的嫩葉，但由於含有含羞草鹼，不建議自行嘗試。',

        '建議食用量',
        '• 一般情況下，不建議食用含羞草。若要用於藥用，必須在專業人士指導下進行。',
        '• 觀賞用途為主，請勿自行食用。',

        '⚠注意事項⚠',
        '• 含羞草含有含羞草鹼 (Mimosine)，具有毒性，不宜生食。',
        '• 過量食用可能導致脫髮、食慾不振、神經系統損傷等。',
        '• 孕婦、哺乳婦女和兒童應避免食用。',
        '• 若接觸含羞草汁液後出現皮膚過敏等不適，應立即清洗並就醫。',
        '• 請勿自行採摘和食用含羞草，以免發生中毒。',
        '• 由於缺乏安全性研究，不建議將含羞草用於食品或茶飲。',
        '• 長期接觸含羞草可能導致皮膚敏感。'],
    '枸杞':[
        '營養成分',
        '1. 多醣體：具有免疫調節、抗氧化和抗腫瘤的潛在作用。',
        '2. 類胡蘿蔔素：如β-胡蘿蔔素、玉米黃素，具有抗氧化作用，有益於眼睛健康。',
        '3. 維生素：含有維生素C、維生素B群等。',
        '4. 礦物質：含有鐵、鉀、鋅等。',
        '5. 胺基酸：含有多種必需胺基酸。',
        '6. 甜菜鹼：可能具有保護肝臟的作用。',

        '健康功效',
        '1. 增強免疫力：多醣體能增強免疫細胞活性，提高抵抗力。',
        '2. 保護眼睛：類胡蘿蔔素有助於預防黃斑部病變、白內障等眼部疾病。',
        '3. 抗氧化：多醣體和類胡蘿蔔素能清除自由基，延緩衰老。',
        '4. 保護肝臟：甜菜鹼可能具有保護肝臟的作用。',
        '5. 改善睡眠：部分研究顯示枸杞可能改善睡眠品質。',
        '6. 降低血糖：部分研究顯示枸杞可能降低血糖。',

        '烹調方式',
        '1. 枸杞茶：將枸杞直接沖泡熱水飲用，可單獨飲用或搭配紅棗、菊花等。',
        '2. 枸杞粥：將枸杞加入粥中，增加風味和營養。',
        '3. 枸杞湯：將枸杞加入湯品中，如雞湯、排骨湯等。',
        '4. 枸杞藥膳：枸杞常被用於藥膳，如枸杞燉雞、枸杞羊肉等。',
        '5. 枸杞零食：直接食用乾燥的枸杞，作為零食。',
        '6. 枸杞酒：將枸杞浸泡在酒中，製成枸杞酒。',

        '建議食用量',
        '• 一般健康成人：每日 15~30克乾燥枸杞，適量食用可促進健康。',
        '• 糖尿病患者：應注意食用量，避免血糖波動過大。',
        '• 服用抗凝血藥物者：應諮詢醫生後再食用。',
        '• 腸胃敏感者：建議少量食用，避免引起不適。',

        '⚠注意事項⚠',
        '• 部分人可能對枸杞過敏，食用前應先確認是否過敏。',
        '• 枸杞性溫，體質燥熱者不宜過量食用。',
        '• 枸杞可能影響藥物吸收，正在服用藥物者應諮詢醫生後再食用。',
        '• 請勿食用變質或發霉的枸杞。',
        '• 購買枸杞時應選擇品質良好的產品，避免購買到染色或劣質枸杞。'],
    '腎蕨':[
        '營養成分',
        '1. 澱粉：主要成分，提供能量（含量較高於其他營養素）。',
        '2. 纖維：有助於促進腸道蠕動，改善消化功能（含量較低）。',
        '3. 多酚類化合物：具有抗氧化和抗炎作用（含量極低）。',
        '4. 礦物質：含有少量鉀、鈣、鎂等。',
        '5. 維生素：含有少量維生素C。',

        '健康功效',
        '1. 提供能量：澱粉是主要能量來源（但食用價值不高）。',
        '2. 觀賞價值：葉片具有觀賞價值，可舒緩心情。',
        '3. 空氣淨化：腎蕨具有一定的空氣淨化能力。',
        '4. 傳統用途：在某些地區，腎蕨被用於傳統醫學，但需謹慎使用，且現代研究支持有限。',

        '烹調方式',
        '1. 根莖食用：腎蕨的根莖可以煮熟後食用，但口感較差，且營養價值不高。',
        '2. 觀賞：主要作為觀賞植物，不建議食用。',
        '3. 傳統醫學：在某些地區，腎蕨被用於傳統醫學，但需在專業人士指導下使用，且風險較高。',
        '4. 食用 (不建議)：由於口感不佳、營養價值不高，且可能含有少量對人體有害的物質，不建議食用。',

        '建議食用量',
        '• 一般情況下，不建議食用腎蕨。若要食用，應少量食用，並確保完全煮熟。',
        '• 觀賞用途為主，請勿自行食用。',

        '⚠注意事項⚠',
        '• 腎蕨可能含有少量對人體有害的物質，不宜生食。',
        '• 孕婦、哺乳婦女和兒童應避免食用。',
        '• 若食用後出現不適，應立即停止食用並就醫。',
        '• 請勿自行採摘和食用路邊的腎蕨，以免受到污染。',
        '• 由於缺乏安全性研究，不建議將腎蕨用於食品或茶飲。',
        '• 腎蕨的食用價值遠低於其他常見蔬菜，不建議作為主要食物來源。'],
    '台灣百合':[
        '營養成分',
        '1. 澱粉：主要成分，提供能量。',
        '2. 纖維：有助於促進腸道蠕動，改善消化功能。',
        '3. 多醣體：可能具有免疫調節作用。',
        '4. 蛋白質：提供胺基酸。',
        '5. 維生素和礦物質：含有少量維生素C、鈣和鉀等。',

        '健康功效',
        '1. 提供能量：澱粉是主要能量來源。',
        '2. 促進消化：纖維有助於改善便秘，維持腸道健康。',
        '3. 觀賞價值：花朵具有觀賞價值，可舒緩心情。',
        '4. 傳統用途：在某些地區，台灣百合的鱗莖被用於傳統醫學，但需謹慎使用。',

        '烹調方式',
        '1. 鱗莖食用：台灣百合的鱗莖可以煮熟後食用，口感類似馬鈴薯，但帶有百合特有的香氣。',
        '2. 煮湯：將鱗莖加入湯品中，增加風味和營養。',
        '3. 炒菜：將鱗莖切片後與其他蔬菜一起炒食。',
        '4. 甜點：將鱗莖用於製作甜點，如百合蓮子湯。',
        '5. 觀賞：主要作為觀賞植物，花朵具有裝飾作用。',

        '建議食用量',
        '• 一般健康成人：每日 50~100克煮熟的台灣百合鱗莖，適量食用可促進健康。',
        '• 腸胃敏感者：建議少量食用，避免引起不適。',
        '• 特殊疾病患者：建議諮詢醫生後再食用。',

        '⚠注意事項⚠',
        '• 部分人可能對百合過敏，食用前應先確認是否過敏。',
        '• 台灣百合的野生族群數量較少，應避免過度採摘，選擇人工栽培的品種。',
        '• 台灣百合的鱗莖可能含有微量生物鹼，不宜生食，應完全煮熟後再食用。',
        '• 請勿食用路邊或不明來源的台灣百合，以免受到污染。',
        '• 孕婦、哺乳婦女和兒童應謹慎食用。'],
    '落地生根':[
        '營養成分',
        '1. 有機酸：如蘋果酸、檸檬酸等，具有一定的酸味。',
        '2. 黃酮類化合物：具有抗氧化和抗炎作用（含量較低）。',
        '3. 礦物質：含有少量鉀、鈣、鎂等。',
        '4. 維生素：含有少量維生素C。',
        '5. 強心配醣體 (Bufadienolides)：具有毒性，影響心臟功能。',

        '健康功效',
        '1. 觀賞價值：葉片邊緣長出小植株的特性具有觀賞價值，可舒緩心情。',
        '2. 傳統用途：在某些地區，落地生根被用於傳統醫學，但需謹慎使用，且現代研究支持有限。',

        '烹調方式',
        '1. 藥用：在某些地區，落地生根的葉片被用於藥用，但需在專業人士指導下使用，且風險極高。',
        '2. 觀賞：主要作為觀賞植物，不建議食用。',
        '3. 外用：搗碎的葉片可用於外敷，治療跌打損傷等，但缺乏科學證據，且可能引起皮膚刺激。',
        '4. 食用 (嚴禁)：由於含有強心配醣體，具有毒性，嚴禁食用。',

        '建議食用量',
        '• 嚴禁食用落地生根。',
        '• 觀賞用途為主，請勿自行食用。',

        '⚠注意事項⚠',
        '• 落地生根含有強心配醣體 (Bufadienolides)，具有毒性，食用後可能引起心律不整、噁心、嘔吐等症狀，嚴重者可能危及生命。',
        '• 孕婦、哺乳婦女和兒童絕對禁止食用。',
        '• 若接觸落地生根汁液後出現皮膚過敏等不適，應立即清洗並就醫。',
        '• 請勿自行採摘和食用落地生根，以免發生中毒。',
        '• 由於具有毒性，不建議將落地生根用於食品、茶飲或藥用。',
        '• 應妥善管理落地生根，避免兒童或寵物誤食。'],
    '酢漿草':[
        '營養成分',
        '1. 草酸：含量較高，影響鈣質吸收。',
        '2. 維生素C：具有抗氧化作用。',
        '3. 礦物質：含有少量鉀、鎂等。',
        '4. 黃酮類化合物：具有抗氧化和抗炎作用（含量較低）。',

        '健康功效',
        '1. 觀賞價值：葉片和花朵具有觀賞價值，可舒緩心情。',
        '2. 傳統用途：在某些地區，酢漿草被用於傳統醫學，但需謹慎使用，且現代研究支持有限。',
        '3. 清涼解渴：葉片具有酸味，可少量食用以解渴。',

        '烹調方式',
        '1. 沙拉：將少量酢漿草葉片加入沙拉中，增添風味。',
        '2. 湯品：將少量酢漿草葉片加入湯品中，增加酸味。',
        '3. 藥用：在某些地區，酢漿草被用於藥用，但需在專業人士指導下使用，且風險較高。',
        '4. 食用 (少量)：可少量食用葉片，但應注意草酸含量。',

        '建議食用量',
        '• 一般健康成人：每日少量食用（幾片葉子），不宜過量。',
        '• 腎臟疾病患者、孕婦、哺乳婦女和兒童應避免食用。',

        '⚠注意事項⚠',
        '• 酢漿草含有草酸，過量食用會影響鈣質吸收，可能導致腎結石等問題。',
        '• 腎臟疾病患者、孕婦、哺乳婦女和兒童應避免食用。',
        '• 若食用後出現不適，應立即停止食用並就醫。',
        '• 請勿自行採摘和食用路邊的酢漿草，以免受到污染。',
        '• 由於草酸含量較高，不建議長期或大量食用酢漿草。',
        '• 酢漿草的酸味可能刺激腸胃，腸胃敏感者應謹慎食用。'],
    '咸豐草':[
        '營養成分',
        '1. 黃酮類化合物：如槲皮素、木犀草素等，具有抗氧化和抗炎作用。',
        '2. 多醣體：可能具有免疫調節作用。',
        '3. 揮發油：含有多種成分，具有抗菌、抗病毒等作用。',
        '4. 綠原酸：具有抗氧化作用。',
        '5. 礦物質：含有少量鉀、鈣、鎂等。',

        '健康功效',
        '1. 抗氧化：黃酮類化合物和綠原酸能清除自由基，延緩衰老。',
        '2. 抗炎：黃酮類化合物可能減輕炎症反應。',
        '3. 抗菌：揮發油可能抑制細菌生長。',
        '4. 免疫調節：多醣體可能增強免疫細胞活性，提高抵抗力。',
        '5. 傳統用途：在某些地區，咸豐草被用於傳統醫學，具有清熱解毒、利尿消腫等作用，但需謹慎使用。',

        '烹調方式',
        '1. 青草茶：將咸豐草曬乾後煮成青草茶，具有清涼解渴的作用。',
        '2. 藥用：在某些地區，咸豐草被用於藥用，但需在專業人士指導下使用。',
        '3. 煮湯：將少量咸豐草加入湯品中，增加風味。',
        '4. 涼拌：將嫩葉洗淨後涼拌食用。',
        '5. 食用 (少量)：可少量食用嫩葉，但應注意來源和安全性。',

        '建議食用量',
        '• 一般健康成人：每日少量食用（幾片嫩葉或少量青草茶），不宜過量。',
        '• 孕婦、哺乳婦女和兒童應謹慎食用。',
        '• 特殊疾病患者：建議諮詢醫生後再食用。',

        '⚠注意事項⚠',
        '• 部分人可能對咸豐草過敏，食用前應先確認是否過敏。',
        '• 請勿自行採摘和食用路邊的咸豐草，以免受到污染。',
        '• 由於缺乏安全性研究，不建議長期或大量食用咸豐草。',
        '• 咸豐草可能影響藥物吸收，正在服用藥物者應諮詢醫生後再食用。',
        '• 咸豐草的藥性較強，不宜長期飲用。'],
    '紅鳳菜':[
        '營養成分',
        '1. 花青素：具有強大的抗氧化能力，能保護細胞免受自由基的損害，賦予葉片紅色。',
        '2. 鐵質：有助於紅血球生成，預防貧血。',
        '3. 鈣質：有助於骨骼和牙齒的健康。',
        '4. 維生素A：有助於維持視力、皮膚和黏膜的健康。',
        '5. 膳食纖維：促進腸道蠕動，幫助消化與腸道健康。',
        '6. 鉀：有助於維持體內電解質平衡，調節血壓。',

        '健康功效',
        '1. 抗氧化：花青素能清除自由基，延緩衰老，保護心血管健康。',
        '2. 補血：鐵質有助於紅血球生成，改善貧血症狀。',
        '3. 強健骨骼：鈣質有助於骨骼和牙齒的健康。',
        '4. 保護視力：維生素A有助於維持視力健康。',
        '5. 促進消化：膳食纖維有助於改善便秘，維持腸道健康。',
        '6. 穩定血壓：鉀有助於維持體內電解質平衡，調節血壓。',

        '烹調方式',
        '1. 清炒：將紅鳳菜洗淨後清炒，可加入蒜末、薑絲等調味。',
        '2. 麻油炒：將紅鳳菜與麻油、薑絲一起炒，具有補血暖身的作用。',
        '3. 煮湯：將紅鳳菜加入湯品中，如雞湯、排骨湯等。',
        '4. 涼拌：將紅鳳菜燙熟後涼拌，可加入蒜末、醬油、醋等調味。',
        '5. 火鍋：將紅鳳菜作為火鍋食材。',

        '建議食用量',
        '• 一般健康成人：每日 100~200克紅鳳菜，適量食用可促進健康。',
        '• 貧血者：可適量增加食用量。',
        '• 腎臟疾病患者：應注意鉀的攝取量，諮詢醫生後再食用。',
        '• 孕婦：可適量食用，補充鐵質。',

        '⚠注意事項⚠',
        '• 紅鳳菜性涼，體質虛寒者不宜過量食用。',
        '• 紅鳳菜含有草酸，可能影響鈣質吸收，建議食用前先用熱水燙過。',
        '• 腎臟疾病患者應注意鉀的攝取量，諮詢醫生後再食用。',
        '• 紅鳳菜容易氧化變黑，建議烹調時加入少量醋，有助於保持色澤。',
        '• 請勿食用腐爛或變質的紅鳳菜。'],
    '左手香':[
        '營養成分',
        '1. 揮發油：含有多種成分，如百里香酚、香芹酚等，具有抗菌、抗炎、鎮靜等作用。',
        '2. 黃酮類化合物：具有抗氧化和抗炎作用。',
        '3. 酚酸類化合物：具有抗氧化作用。',
        '4. 礦物質：含有少量鉀、鈣、鎂等。',

        '健康功效',
        '1. 抗菌：揮發油可能抑制細菌生長。',
        '2. 抗炎：揮發油和黃酮類化合物可能減輕炎症反應。',
        '3. 鎮靜：揮發油可能具有鎮靜安神的作用。',
        '4. 傳統用途：在某些地區，左手香被用於傳統醫學，具有消炎止痛、止癢等作用，但需謹慎使用。',
        '5. 觀賞價值：葉片具有特殊的香氣，可舒緩心情。',

        '烹調方式',
        '1. 泡茶：將左手香葉片曬乾後泡茶，具有清涼解渴的作用。',
        '2. 藥用：在某些地區，左手香被用於藥用，但需在專業人士指導下使用。',
        '3. 外用：將左手香葉片搗碎後外敷，可緩解蚊蟲叮咬、皮膚炎等症狀。',
        '4. 沐浴：將左手香加入洗澡水中，具有舒緩皮膚的作用。',
        '5. 食用 (不建議)：雖然有些人會將左手香葉片用於烹調，但由於缺乏安全性研究，不建議自行嘗試。',

        '建議食用量',
        '• 一般情況下，不建議食用左手香。若要用於藥用，必須在專業人士指導下進行。',
        '• 外用為主，請勿自行食用。',

        '⚠注意事項⚠',
        '• 左手香含有揮發油等成分，可能具有刺激性，不宜生食。',
        '• 孕婦、哺乳婦女和兒童應謹慎使用。',
        '• 若接觸左手香汁液後出現皮膚過敏等不適，應立即清洗並就醫。',
        '• 請勿自行採摘和食用路邊的左手香，以免受到污染。',
        '• 由於缺乏安全性研究，不建議將左手香用於食品或茶飲。',
        '• 過量使用可能導致皮膚刺激或其他不適。'],
    '苦瓜':[
        '營養成分',
        '1. 苦瓜素 (Momordicin)：主要活性成分，賦予苦瓜獨特的苦味，具有降血糖、抗氧化等作用。',
        '2. 維生素C：具有抗氧化作用，有助於增強免疫力。',
        '3. 膳食纖維：促進腸道蠕動，幫助消化與腸道健康。',
        '4. 鉀：有助於維持體內電解質平衡，調節血壓。',
        '5. 維生素B群：有助於維持神經系統的健康。',
        '6. 葫蘆素 (Cucurbitacins)：具有抗腫瘤的潛在作用。',

        '健康功效',
        '1. 降血糖：苦瓜素能促進胰島素分泌，降低血糖，適合糖尿病患者食用。',
        '2. 抗氧化：維生素C和苦瓜素能清除自由基，延緩衰老。',
        '3. 促進消化：膳食纖維有助於改善便秘，維持腸道健康。',
        '4. 穩定血壓：鉀有助於維持體內電解質平衡，調節血壓。',
        '5. 增強免疫力：維生素C有助於增強免疫細胞活性，提高抵抗力。',
        '6. 潛在的抗癌作用：葫蘆素可能具有抑制癌細胞生長的作用，但仍需更多研究證實。',

        '烹調方式',
        '1. 涼拌：將苦瓜切片後涼拌，可加入蒜末、醬油、醋等調味。',
        '2. 清炒：將苦瓜切片後清炒，可加入豆豉、小魚乾等調味。',
        '3. 苦瓜排骨湯：將苦瓜與排骨一起燉煮，具有清熱解毒的作用。',
        '4. 苦瓜封：將苦瓜挖空後填入絞肉，蒸煮或滷製。',
        '5. 苦瓜汁：將苦瓜榨汁飲用，可加入蜂蜜或檸檬汁調味。',
        '6. 鹹蛋苦瓜：將苦瓜與鹹蛋一起炒，具有獨特的風味。',

        '建議食用量',
        '• 一般健康成人：每日 50~100克苦瓜，適量食用可促進健康。',
        '• 糖尿病患者：可適量增加食用量，但應注意血糖變化。',
        '• 孕婦：應適量食用，避免過量。',
        '• 腸胃虛弱者：應少量食用，避免引起不適。',

        '⚠注意事項⚠',
        '• 苦瓜性寒，體質虛寒者不宜過量食用。',
        '• 苦瓜具有降血糖作用，低血糖者應謹慎食用。',
        '• 孕婦應適量食用，避免過量，以免引起子宮收縮。',
        '• 苦瓜的苦味較重，可先用鹽水浸泡或焯水，以減少苦味。',
        '• 請勿食用腐爛或變質的苦瓜。'],
    '山藥':[
        '營養成分',
        '1. 澱粉：主要成分，提供能量。',
        '2. 黏液蛋白：具有保護胃黏膜的作用。',
        '3. 膳食纖維：促進腸道蠕動，幫助消化與腸道健康。',
        '4. 薯蕷皂苷 (Diosgenin)：具有抗氧化、抗炎等作用。',
        '5. 維生素B群：有助於維持神經系統的健康。',
        '6. 礦物質：含有鉀、鎂、鈣等。',
        '7. 胺基酸：含有多種必需胺基酸。',

        '健康功效',
        '1. 提供能量：澱粉是主要能量來源。',
        '2. 保護胃黏膜：黏液蛋白有助於修復和保護胃黏膜，適合胃潰瘍患者食用。',
        '3. 促進消化：膳食纖維有助於改善便秘，維持腸道健康。',
        '4. 抗氧化：薯蕷皂苷能清除自由基，延緩衰老。',
        '5. 穩定血糖：部分研究顯示山藥可能具有穩定血糖的作用。',
        '6. 增強免疫力：山藥含有多種營養成分，有助於增強免疫力。',

        '烹調方式',
        '1. 清炒：將山藥切片後清炒，可加入木耳、紅蘿蔔等。',
        '2. 煮湯：將山藥加入湯品中，如排骨湯、雞湯等。',
        '3. 蒸煮：將山藥蒸熟後直接食用，可保留較多的營養成分。',
        '4. 磨泥：將山藥磨成泥，可加入牛奶、蜂蜜等調味。',
        '5. 甜點：將山藥用於製作甜點，如山藥糕、山藥粥等。',
        '6. 火鍋：將山藥作為火鍋食材。',

        '建議食用量',
        '• 一般健康成人：每日 100~200克山藥，適量食用可促進健康。',
        '• 糖尿病患者：可適量食用，但應注意澱粉攝取量。',
        '• 腸胃虛弱者：可適量食用，但應選擇容易消化的烹調方式。',

        '⚠注意事項⚠',
        '• 山藥含有較多的澱粉，糖尿病患者應注意食用量。',
        '• 山藥的黏液可能引起皮膚過敏，處理時可戴上手套。',
        '• 山藥不宜與鹼性食物同食，以免破壞營養成分。',
        '• 請勿食用腐爛或變質的山藥。',
        '• 部分人可能對山藥過敏，食用前應先確認是否過敏。'],
    '仙草':[
        '營養成分',
        '1. 多醣體：具有免疫調節、抗氧化和抗腫瘤的潛在作用。',
        '2. 黃酮類化合物：具有抗氧化和抗炎作用。',
        '3. 酚酸類化合物：具有抗氧化作用。',
        '4. 膳食纖維：促進腸道蠕動，幫助消化與腸道健康。',
        '5. 礦物質：含有少量鉀、鈣、鎂等。',

        '健康功效',
        '1. 清熱解毒：仙草具有清熱解毒的作用，適合夏季食用。',
        '2. 降血壓：部分研究顯示仙草可能具有降血壓的作用。',
        '3. 降血糖：部分研究顯示仙草可能具有降血糖的作用。',
        '4. 抗氧化：多醣體、黃酮類化合物和酚酸類化合物能清除自由基，延緩衰老。',
        '5. 促進消化：膳食纖維有助於改善便秘，維持腸道健康。',

        '烹調方式',
        '1. 仙草茶：將仙草乾熬煮成仙草茶，具有清涼解渴的作用。',
        '2. 仙草凍：將仙草茶加入太白粉或吉利丁等凝固劑，製成仙草凍。',
        '3. 燒仙草：將仙草凍加熱後加入配料，如花生、芋圓、粉圓等。',
        '4. 仙草雞湯：將仙草與雞肉一起燉煮，具有滋補養生的作用。',
        '5. 仙草冰：將仙草凍刨成冰，加入配料。',

        '建議食用量',
        '• 一般健康成人：每日 100~200克仙草凍或仙草茶，適量食用可促進健康。',
        '• 體質虛寒者：不宜過量食用。',
        '• 糖尿病患者：應注意糖分攝取量，選擇無糖或低糖的仙草產品。',

        '⚠注意事項⚠',
        '• 仙草性寒，體質虛寒者不宜過量食用。',
        '• 仙草製品通常含有較多的糖分，糖尿病患者應注意攝取量。',
        '• 市售仙草產品可能添加人工色素、香精等，應選擇品質良好的產品。',
        '• 請勿食用腐爛或變質的仙草。',
        '• 孕婦應適量食用，避免過量。'],
    '車前草':[
        '營養成分',
        '1. 多醣體：具有免疫調節作用。',
        '2. 黏液質：具有潤滑和保護作用。',
        '3. 黃酮類化合物：具有抗氧化和抗炎作用。',
        '4. 酚酸類化合物：具有抗氧化作用。',
        '5. 礦物質：含有鉀、鈣、鎂等。',
        '6. 維生素：含有維生素A、維生素C等。',
        '7. 膳食纖維：促進腸道蠕動，幫助消化與腸道健康。',

        '健康功效',
        '1. 利尿：車前草具有利尿作用，有助於排除體內多餘水分。',
        '2. 止咳化痰：車前草可能具有止咳化痰的作用。',
        '3. 抗炎：黃酮類化合物可能減輕炎症反應。',
        '4. 促進消化：膳食纖維有助於改善便秘，維持腸道健康。',
        '5. 傳統用途：在某些地區，車前草被用於傳統醫學，具有清熱解毒、明目等作用，但需謹慎使用。',

        '烹調方式',
        '1. 青草茶：將車前草曬乾後煮成青草茶，具有清涼解渴的作用。',
        '2. 藥用：在某些地區，車前草被用於藥用，但需在專業人士指導下使用。',
        '3. 煮粥：將車前草加入粥中，增加風味。',
        '4. 涼拌：將嫩葉洗淨後涼拌食用。',
        '5. 食用 (少量)：可少量食用嫩葉，但應注意來源和安全性。',

        '建議食用量',
        '• 一般健康成人：每日少量食用（幾片嫩葉或少量青草茶），不宜過量。',
        '• 孕婦、哺乳婦女和兒童應謹慎食用。',
        '• 特殊疾病患者：建議諮詢醫生後再食用。',

        '⚠注意事項⚠',
        '• 部分人可能對車前草過敏，食用前應先確認是否過敏。',
        '• 請勿自行採摘和食用路邊的車前草，以免受到污染。',
        '• 由於缺乏安全性研究，不建議長期或大量食用車前草。',
        '• 車前草可能影響藥物吸收，正在服用藥物者應諮詢醫生後再食用。',
        '• 車前草具有利尿作用，應注意補充水分。',
        '• 腎功能不佳者應謹慎食用。'],
    '紫蘇':[
        '營養成分',
        '1. 揮發油：含有紫蘇醛、紫蘇酮、檸檬烯等，具有抗菌、抗炎、鎮靜等作用。',
        '2. α-亞麻酸：一種Omega-3脂肪酸，有益於心血管健康。',
        '3. 黃酮類化合物：具有抗氧化和抗炎作用。',
        '4. 酚酸類化合物：具有抗氧化作用。',
        '5. 維生素：含有維生素A、維生素C、維生素E等。',
        '6. 礦物質：含有鈣、鐵、鉀等。',
        '7. 膳食纖維：促進腸道蠕動，幫助消化與腸道健康。',

        '健康功效',
        '1. 抗炎：揮發油和黃酮類化合物可能減輕炎症反應。',
        '2. 抗菌：揮發油可能抑制細菌生長。',
        '3. 改善過敏：紫蘇可能具有改善過敏體質的作用。',
        '4. 保護心血管：α-亞麻酸有助於降低膽固醇，預防心血管疾病。',
        '5. 促進消化：膳食纖維有助於改善便秘，維持腸道健康。',
        '6. 鎮靜安神：紫蘇可能具有鎮靜安神的作用。',

        '烹調方式',
        '1. 紫蘇茶：將紫蘇葉沖泡熱水飲用，具有暖身、解表的作用。',
        '2. 紫蘇梅：將紫蘇葉與梅子一起醃製，製成紫蘇梅。',
        '3. 紫蘇炒蛤蜊：將紫蘇葉與蛤蜊一起炒，增加風味。',
        '4. 紫蘇壽司：將紫蘇葉用於製作壽司。',
        '5. 紫蘇天婦羅：將紫蘇葉裹粉後油炸，製成天婦羅。',
        '6. 紫蘇醬：將紫蘇葉製成醬料，搭配肉類或蔬菜食用。',

        '建議食用量',
        '• 一般健康成人：每日 5~10克新鮮紫蘇葉或 1~2克乾燥紫蘇葉，適量食用可促進健康。',
        '• 孕婦：應適量食用，避免過量。',
        '• 服用抗凝血藥物者：應諮詢醫生後再食用。',

        '⚠注意事項⚠',
        '• 部分人可能對紫蘇過敏，食用前應先確認是否過敏。',
        '• 紫蘇具有活血作用，孕婦應適量食用，避免過量，以免引起出血。',
        '• 服用抗凝血藥物者應諮詢醫生後再食用，以免影響藥效。',
        '• 紫蘇不宜與螃蟹同食，以免引起不適。',
        '• 請勿食用腐爛或變質的紫蘇。'],
    '羅勒':[
        '營養成分',
        '1. 揮發油：含有多種成分，如丁香酚、羅勒烯、樟腦等，具有抗菌、抗炎、抗氧化等作用。',
        '2. 維生素K：有助於血液凝固和骨骼健康。',
        '3. 維生素A：有助於維持視力、皮膚和黏膜的健康。',
        '4. 維生素C：具有抗氧化作用，有助於增強免疫力。',
        '5. 礦物質：含有鈣、鐵、鉀等。',
        '6. 黃酮類化合物：具有抗氧化和抗炎作用。',

        '健康功效',
        '1. 抗炎：揮發油和黃酮類化合物可能減輕炎症反應。',
        '2. 抗菌：揮發油可能抑制細菌生長。',
        '3. 抗氧化：揮發油和黃酮類化合物能清除自由基，延緩衰老。',
        '4. 促進消化：羅勒可能具有促進消化的作用。',
        '5. 舒緩壓力：羅勒的香氣可能具有舒緩壓力的作用。',

        '烹調方式',
        '1. 青醬：將羅勒葉、松子、蒜頭、起司、橄欖油等製成青醬，搭配義大利麵或麵包食用。',
        '2. 披薩：將羅勒葉撒在披薩上，增加風味。',
        '3. 義大利麵：將羅勒葉加入義大利麵中，增加風味。',
        '4. 沙拉：將羅勒葉加入沙拉中，增添風味。',
        '5. 湯品：將羅勒葉加入湯品中，增加風味。',
        '6. 羅勒茶：將羅勒葉沖泡熱水飲用，具有舒緩壓力的作用。',

        '建議食用量',
        '• 一般健康成人：每日 5~10克新鮮羅勒葉或 1~2克乾燥羅勒葉，適量食用可促進健康。',
        '• 孕婦：應適量食用，避免過量。',
        '• 服用抗凝血藥物者：應諮詢醫生後再食用。',

        '⚠注意事項⚠',
        '• 部分人可能對羅勒過敏，食用前應先確認是否過敏。',
        '• 羅勒含有較高的維生素K，服用抗凝血藥物者應諮詢醫生後再食用，以免影響藥效。',
        '• 羅勒不宜與高草酸食物同食，以免影響鈣質吸收。',
        '• 請勿食用腐爛或變質的羅勒。',
        '• 孕婦應適量食用，避免過量，以免引起子宮收縮。']
}

image_url = {
    '薄荷': 'https://upload.wikimedia.org/wikipedia/commons/thumb/b/b0/Mint-leaves-2007.jpg/800px-Mint-leaves-2007.jpg',
    '山芙蓉': 'https://shoplineimg.com/5848f39d617069d6a59b0500/5d75b753b051d1001709bbf9/3860x.jpg?',
    '朱蕉': 'https://www.picturethisai.com/wiki-image/1080/154495260783804421.jpeg',
    '美人蕉': 'https://lh6.googleusercontent.com/proxy/3sKLm0TQ1fCGshFbjGfsndvUlEamdbYZ2gYT65gTj_TC9KFmhH5ugdLUN0L3bpFZB5Umk8HsE1DXSwtC9OTTgP6w500cdr8870_ZmqCU_Q',
    '蚌蘭': 'https://www.picturethisai.com/wiki-image/1080/153723206052610076.jpeg',
    '含羞草': 'https://shoplineimg.com/62cb90c69730d2004d2343f2/6704cdb009a23b000dc67808/750x.jpg?',
    '枸杞': 'https://upload.wikimedia.org/wikipedia/commons/a/a7/Lycium_chinense%28siamak_sabet%29_%282%29.jpg',
    '腎蕨': 'https://www.future.url.tw/images/plant/465/5eedd0aa0a4b3.JPG',
    '台灣百合': 'https://lh4.googleusercontent.com/proxy/z7VXahNItLMq0PlosDgGnXB4TIQ0xbBpd7Hnpv5os7Ev1kkboSmC3AjzMnjQ_SPA8D6BNXzhzbdVhWtVxToJS59qfB3DRsogj94nCSW2Zf5KDeXLHrb7Cx2tzpkq6y_sY0bkciQJr-tAn-uLFffKiB_LYgFhyMQ9TRWV0cpdL8xNdThZ',
    '落地生根': 'https://www.picturethisai.com/wiki-image/1080/154095334904037403.jpeg',
    '酢漿草': 'https://upload.wikimedia.org/wikipedia/commons/3/35/Oxalis_corymbosa_2.jpg',
    '咸豐草': 'https://www.newsmarket.com.tw/files/2021/12/%E5%92%B8%E8%B1%90%E8%8D%89%EF%BC%88%E5%9C%96%E7%89%87%E4%BE%86%E6%BA%90%EF%BC%8FShipher-Wu%EF%BC%8Cflickr%EF%BC%89.jpg',
    '紅鳳菜': 'https://top1cdn.top1health.com/cdn/am/37758/99714.jpg',
    '左手香': 'https://lupusa.net/wp-content/uploads/2023/05/IMG_5936-1024x683.jpeg',
    '苦瓜': 'https://as.chdev.tw/web/article/7/e/4/7f7a4c5d-ed77-44ee-84e0-b8ee26d492721669609669.jpg',
    '山藥': 'https://global-blog.cpcdn.com/tw/2021/10/AdobeStock_226788907-min--1-.jpeg',
    '仙草': 'https://images.agriharvest.tw/wp-content/uploads/2023/03/1-24-1024x591.jpg',
    '車前草': 'https://inaturalist-open-data.s3.amazonaws.com/photos/340473562/large.jpg',
    '紫蘇': 'https://www.newsmarket.com.tw/files/2022/06/%E7%B4%AB%E8%98%87%EF%BC%88%E6%94%9D%E5%BD%B1%EF%BC%8F%E6%9E%97%E6%80%A1%E5%9D%87%EF%BC%89-1.jpg',
    '羅勒': 'https://imgs.gvm.com.tw/upload/gallery/health/66364_01.jpg'
}
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
    def main():
    print("您好！我將為您推薦符合您症狀的藥用植物🌿")
    print("""
請選擇以下最符合您症狀的種類(A~E):
A: 呼吸系統與感冒問題
B: 消化與代謝問題
C: 皮膚與過敏問題
D: 循環與泌尿系統問題
E: 身心與內分泌問題
X: 以上沒有符合我的症狀種類
""")

    # 讓使用者選擇症狀分類
    Symptom_input = input("請輸入(A/B/C/D/E/X): ").upper()
    while Symptom_input not in valid_choices:
        print("輸入錯誤，請重新輸入 A, B, C, D, E 或 X")
        Symptom_input = input("請輸入您的選擇 (A/B/C/D/E/X): ").upper()

    if Symptom_input == 'X':
        print("請詳細描述您的症狀: ")
        detailed_input = input()
        try:
            ai_response = model.generate_content(detailed_input)
            print(ai_response.text if ai_response.text else "抱歉，我無法理解你的問題，請換個方式問問看～")
        except Exception as e:
            print(f"Gemini 執行出錯: {str(e)}")
        return

    # 根據使用者選擇的症狀分類進行處理
    category = valid_choices[Symptom_input]
    symptoms_check = ['沒有'] + Symptom_classification[category]
    symptoms = ", ".join(Symptom_classification[category])
    print(f"\n以下有符合您的症狀描述嗎? {symptoms}")

    type_input = input("請輸入符合您的症狀: ")
    while type_input not in symptoms_check:
        print("輸入錯誤，請重新輸入")
        type_input = input("請輸入上述符合您的症狀: ")

    if type_input in ['沒有', '無']:
        print("感謝您的使用，再見！")
        return

    # 根據具體症狀進行更詳細的選擇
    print("\n請選擇以下符合您的症狀描述:")
    des = []
    for key, description in Symptom_questions.get(type_input, {}).items():
        print(f"{key}: {description}")
        des.append(key)

    final_input = input(f"以上哪種症狀描述較符合您({', '.join(des)})? ").upper()
    while final_input not in des:
        print("輸入錯誤，請重新輸入")
        final_input = input(f"以上哪種症狀描述較符合您({', '.join(des)})? ").upper()

    result = f"{type_input}_{final_input}"
    print("\n" + Symptom_answers[result])

if __name__ == "__main__":
    main()

 

if __name__ == "__main__":
    uvicorn.run(host="0.0.0.0",port=int(os.getenv("PORT", 8000)), reload=True)
