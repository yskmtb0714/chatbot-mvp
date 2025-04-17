# backend/app.py - Final combined version
import os
import traceback
import re
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai
from flask_cors import CORS
# data_store から必要な関数をインポート
from data_store import get_faq_answer, find_product, get_order_info, retrieve_product_info

load_dotenv() # .envファイルから環境変数を読み込む

# --- Gemini API Initialization ---
gemini_api_key = os.getenv('GEMINI_API_KEY')
gemini_model = None
if gemini_api_key:
    try:
        genai.configure(api_key=gemini_api_key)
        # 使用するモデルを指定
        gemini_model = genai.GenerativeModel('gemini-1.5-flash-latest')
        print("Gemini API Key configured and Model initialized.")
    except Exception as e:
        print(f"Error during Gemini setup: {e}")
        gemini_api_key = None
        gemini_model = None
else:
    print("Warning: Gemini API Key not found in .env file.")
# --- End Gemini API Initialization ---


# --- Flask App Setup ---
app = Flask(__name__)
CORS(app) # CORSを有効化
# --- End Flask App Setup ---


# === Helper Functions ===
# (ルート定義よりも前に記述)

# RAG version of product info handler
def get_product_info_handler(query):
    print(f"--- Intent: Product Info Query Received (RAG attempt): '{query}' ---")

    # --- 1. data_store から関連情報を検索 (Retrieve) ---
    retrieved_context = retrieve_product_info(query) # Calls data_store function

    # --- 2. 検索結果に基づいて応答を生成 (Generate) ---
    if retrieved_context: # 関連情報が見つかった場合 (None でない場合)
        print("Context retrieved, proceeding to generate response with Gemini.")
        try:
            # --- RAG 用のプロンプトを作成 ---
            prompt_for_ai = f"""以下の関連情報だけを基にして、顧客の質問に答えてください。情報は箇条書きではなく、自然な会話になるように要約・編集してください。情報がない場合は「関連情報からは分かりません」と正直に答えてください。あなたはフレンドリーな店員です。

# 関連情報
{retrieved_context}

# 顧客の質問
{query}

# 店員としての応答:"""
            print(f"--- RAG Prompt for Gemini ---\n{prompt_for_ai}\n---------------------------")

            if not gemini_model: # モデルチェック
                 print("Error: gemini_model object is not initialized.")
                 return "AIモデルの準備ができていないため、商品説明を生成できません。管理者にお問い合わせください。"

            print("Calling Gemini model for RAG response...")
            # Gemini API を呼び出し
            response_ai = gemini_model.generate_content(prompt_for_ai)
            print("Gemini model responded for RAG.")

            # --- 応答テキストを抽出 ---
            response_text = "AI応答の取得/解析に失敗しました。"
            try:
                # (応答テキスト抽出ロジック)
                if hasattr(response_ai, 'text'): response_text = response_ai.text
                elif hasattr(response_ai, 'parts') and response_ai.parts: response_text = "".join(part.text for part in response_ai.parts)
                elif hasattr(response_ai, 'candidates') and not response_ai.candidates:
                    print(f"Warning: Gemini RAG response empty/blocked. Full response: {response_ai}")
                    response_text = "(AI応答がブロックされたか、内容がありませんでした)"
                else:
                    print(f"Warning: Unexpected RAG response structure. Full response: {response_ai}")
                    response_text = "(予期しないAI応答形式)"
                print(f"Extracted AI response (RAG): {response_text}")
            except Exception as e_text:
                print(f"Error extracting text from RAG response: {e_text}")
                print(f"Full Gemini response object on text extraction error: {response_ai}")

            return response_text # AIが生成したテキストを返す

        except Exception as e:
            # Gemini API 呼び出し中のエラー
            print(f"!!! Error during RAG generation: {e}")
            traceback.print_exc()
            return "関連情報はありましたが、AI応答の生成中にエラーが発生しました。しばらくしてからもう一度お試しください。"

    else: # 関連情報が見つからなかった場合
        print("No relevant product context found for RAG.")
        # 関連情報がない場合は固定メッセージを返す
        response_message = "申し訳ありません、関連する商品情報が見つかりませんでした。もう少し具体的に質問していただけますか？"
        return response_message

# Order status handler (using data_store function)
def check_order_status_handler(query):
    print(f"--- Intent: Order Status Query Received: '{query}' ---")
    order_id = None
    # 改良された注文番号抽出ロジック
    match = re.search(r"(?:注文(?:番号)?|オーダー|ID)[\s:]+([A-Z0-9-]{3,})\b", query, re.IGNORECASE)
    if match:
        order_id = match.group(1).upper()
    else:
        match_simple = re.search(r"\b(ORD[0-9-]+|[A-Z]{3}[0-9]{3,}|[0-9]{5,})\b", query, re.IGNORECASE)
        if match_simple:
             order_id = match_simple.group(1).upper()
    print(f"Extracted Order ID (Attempt): {order_id}")

    found_order = get_order_info(order_id) # data_store の関数を呼び出し

    if found_order:
        print(f"Found matching order: {found_order}")
        status = found_order.get("status", "不明")
        response_message = f"ご注文（{order_id}）の状況は「{status}」です。"
        if status == "発送済み" and found_order.get("shipped_date"): response_message += f" ({found_order['shipped_date']}発送)"
        elif status == "処理中" and found_order.get("estimated_delivery"): response_message += f" (お届け予定: {found_order['estimated_delivery']})"
        elif status == "配達完了" and found_order.get("delivered_date"): response_message += f" ({found_order['delivered_date']}配達完了)"
    elif order_id:
        print(f"Order ID {order_id} not found in database.")
        response_message = f"申し訳ありません、注文番号「{order_id}」に該当する注文が見つかりませんでした。番号をお確かめの上、再度お尋ねください。"
    else:
        print("Order ID could not be extracted from the query.")
        response_message = "ご注文状況をお調べします。注文番号（例: ORD123, XYZ789）を教えていただけますか？"
    return response_message

# Intent detection function (using data_store functions)
def detect_intent(query):
    query_lower = query.lower()

    # 1. FAQチェック
    if get_faq_answer(query):
         return "faq"

    # 2. 商品チェック
    if find_product(query):
        return "product_info"

    # 3. 注文キーワード or IDパターンチェック
    if "注文" in query_lower or "オーダー" in query_lower or "発送" in query_lower or "いつ届きますか" in query_lower or "届かない" in query_lower or "配送" in query_lower:
        return "order_status"
    if re.search(r"\b(?:注文(?:番号)?|オーダー|ID)[\s:]+([A-Z0-9-]{3,})\b", query, re.IGNORECASE):
         return "order_status"
    if re.search(r"\b(ORD[0-9-]+|[A-Z]{3}[0-9]{3,}|[0-9]{5,})\b", query, re.IGNORECASE):
         return "order_status"

    # 4. 上記以外は一般会話
    else:
        return "general_chat"
# === End Helper Functions ===


# --- Routes ---
@app.route('/')
def hello():
    return "チャットボットバックエンド動作中。/chat へPOSTで質問してください。"

@app.route('/chat', methods=['POST'])
def chat():
    print("--- /chat endpoint called ---")
    data = request.get_json()
    print(f"Received data: {data}")
    if not data or 'query' not in data:
        print("Error: 'query' not found in request data.")
        return jsonify({"error": "リクエストボディに 'query' が含まれていません。"}), 400

    user_query = data['query'].strip()
    print(f"User query: '{user_query}'")

    # 意図解釈
    intent = detect_intent(user_query)
    print(f"Detected intent: {intent}")

    response_text = "すみません、うまく応答できませんでした。"

    # 意図に基づいて処理を振り分け
    if intent == "faq":
        response_text = get_faq_answer(user_query)
        print("--- Handling as FAQ ---")
        if response_text:
            return jsonify({"response": response_text})
        else:
            print("Error: FAQ intent detected but get_faq_answer returned None.")
            intent = "general_chat" # フォールバック
            print(f"Falling back to intent: {intent}")
            # この下の general_chat 処理に進むように return しない

    # FAQでなかった、またはFAQで見つからずフォールバックした場合
    if intent == "product_info": # elif ではなく if にしてフォールバックを受け入れる
        response_text = get_product_info_handler(user_query)
        print("--- Handling as Product Info (RAG) ---") # RAGであることを明記
        return jsonify({"response": response_text})

    elif intent == "order_status":
        response_text = check_order_status_handler(user_query)
        print("--- Handling as Order Status ---")
        return jsonify({"response": response_text})

    elif intent == "general_chat": # 元々の general_chat または FAQからのフォールバック
        print("--- Handling as General Chat (Calling Gemini) ---")
        if not gemini_api_key or not gemini_model:
            print("Error: API key or model not configured properly for general chat.")
            return jsonify({"error": "AIモデルが利用できない状態です。"}), 500

        try:
            print("Calling Gemini model...")
            response = gemini_model.generate_content(user_query)
            print("Gemini model responded.")
            print(f"Gemini response object type: {type(response)}")

            response_text = "AIからの応答テキストの取得に失敗しました。"
            try:
                if hasattr(response, 'text'): response_text = response.text
                elif hasattr(response, 'parts') and response.parts: response_text = "".join(part.text for part in response.parts)
                elif hasattr(response, 'candidates') and not response.candidates:
                     print(f"Warning: Gemini response empty/blocked. Full response: {response}")
                     response_text = "(応答がブロックされたか、内容がありませんでした)"
                else:
                     print(f"Warning: Unexpected response structure. Full response: {response}")
                     response_text = "(予期しないAI応答形式)"
                print(f"Extracted response text: {response_text}")
            except Exception as e_text:
                print(f"Error extracting text from response: {e_text}")
                print(f"Full Gemini response object on text extraction error: {response}")

            print("Returning JSON response from Gemini...")
            return jsonify({"response": response_text})

        except Exception as e:
            print(f"!!! Gemini API call error: {e}")
            traceback.print_exc()
            return jsonify({"error": f"AI応答の生成中に内部エラーが発生しました: {str(e)}"}), 500

    else: # 基本的にここには到達しないはず
        print(f"Error: Unhandled intent detected: {intent}")
        return jsonify({"error": "不明なリクエストタイプです。"}), 400
# --- End Routes ---


# --- Server Start ---
if __name__ == '__main__':
    print(">>> Starting Flask server via app.run()...")
    app.run(debug=True, host='0.0.0.0', port=5000)
# --- End Server Start ---