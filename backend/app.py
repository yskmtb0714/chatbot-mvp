# backend/app.py - Final version with RAG Product Info + Function Calling Order Status
import os
import traceback
import re
import json # Just in case, though primarily used in data_store
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai
# protos は Function Calling のスキーマや履歴で型を指定するために重要
try:
    from google.generativeai import protos
except ImportError:
    print("Warning: Could not import protos from google.generativeai. Trying google.ai.generativelanguage instead for protos.")
    try:
        # 古いバージョンや環境によっては、こちらからインポートする必要がある場合がある
        from google.ai import generativelanguage_v1beta as protos # Alias as protos
        print("Imported protos successfully from google.ai.generativelanguage_v1beta")
    except ImportError:
        print("!!! Critical Error: Failed to import 'protos' for Function Calling types.")
        print("!!! Please ensure google-generativeai library is up-to-date and correctly installed.")
        protos = None # Define as None to potentially avoid NameErrors later if possible

from flask_cors import CORS
# data_store から必要な関数をインポート (data_store.py が存在し、関数が定義されている前提)
try:
    from data_store import get_faq_answer, find_product, get_order_info, retrieve_product_info
except ImportError as e:
     print(f"!!! Error importing from data_store: {e}")
     print("!!! Please ensure data_store.py exists in the backend folder and defines necessary functions.")
     # Define dummy functions to allow app to potentially start for debugging other parts
     def get_faq_answer(q): return None
     def find_product(q): return None
     def get_order_info(q): return None
     def retrieve_product_info(q): return None

load_dotenv() # .envファイルから環境変数を読み込む

# --- Gemini API Initialization ---
gemini_api_key = os.getenv('GEMINI_API_KEY')
gemini_model = None
if gemini_api_key:
    try:
        genai.configure(api_key=gemini_api_key)
        gemini_model = genai.GenerativeModel('gemini-1.5-flash-latest')
        print("Gemini API Key configured and Model initialized.")
    except Exception as e:
        print(f"Error during Gemini setup: {e}")
        gemini_api_key = None
        gemini_model = None
else:
    print("Warning: Gemini API Key not found in .env file.")
# --- End Gemini API Initialization ---


# --- Function Calling Schema Definition ---
available_tools = None # Initialize
if protos: # protosが正常にインポートできた場合のみスキーマを定義
    try:
        get_order_info_func_declaration = {
            "name": "get_order_info",
            "description": "指定された注文IDに基づいて、特定の注文の現在の状況（発送済み、処理中など）と詳細情報を取得します。",
            "parameters": {
                "type": protos.Type.OBJECT, # Enum を使う
                "properties": {
                    "order_id": {
                        "type": protos.Type.STRING, # Enum を使う
                        "description": "状況を確認したい注文の一意の識別子または番号 (例: 'ORD123', 'XYZ789')"
                    }
                },
                "required": ["order_id"]
            }
        }
        available_tools = [get_order_info_func_declaration]
        print("Function calling schema defined successfully.")
    except AttributeError as e_proto:
        print(f"!!! Error defining function schema: Could not find expected Type enums in protos object ({e_proto}). Function calling might fail.")
    except Exception as e_schema:
         print(f"!!! Error defining function schema: {e_schema}")
else:
    print("Warning: `protos` module not available, function calling schema cannot be defined.")
# --- End Function Calling Schema Definition ---


# --- Flask App Setup ---
app = Flask(__name__)
CORS(app) # CORSを有効化
# --- End Flask App Setup ---


# === Helper Functions defined within app.py ===

# RAG version of product info handler
def get_product_info_handler(query):
    print(f"--- Intent: Product Info Query Received (RAG attempt): '{query}' ---")
    retrieved_context = retrieve_product_info(query) # Calls data_store function

    if retrieved_context:
        print("Context retrieved, proceeding to generate response with Gemini.")
        if not gemini_model: return "AIモデルの準備ができていません。"
        try:
            prompt_for_ai = f"""以下の関連情報だけを基にして、顧客の質問に答えてください。情報は箇条書きではなく、自然な会話になるように要約・編集してください。情報がない場合は「関連情報からは分かりません」と正直に答えてください。あなたはフレンドリーな店員です。

# 関連情報
{retrieved_context}

# 顧客の質問
{query}

# 店員としての応答:"""
            print(f"--- RAG Prompt for Gemini ---\n{prompt_for_ai}\n---------------------------")

            print("Calling Gemini model for RAG response...")
            response_ai = gemini_model.generate_content(prompt_for_ai)
            print("Gemini model responded for RAG.")

            response_text = "(AI応答の解析エラー)"
            try: # Robust text extraction
                if response_ai.candidates and response_ai.candidates[0].content.parts:
                    response_text = "".join(part.text for part in response_ai.candidates[0].content.parts if hasattr(part,'text'))
                elif hasattr(response_ai, 'text'):
                     response_text = response_ai.text
                # Check for blocked prompt/response
                elif response_ai.prompt_feedback.block_reason:
                     print(f"Warning: RAG response blocked. Reason: {response_ai.prompt_feedback.block_reason}")
                     response_text = "(応答がブロックされました)"
                else:
                     print(f"Warning: Unexpected RAG response structure. Full response: {response_ai}")
                     response_text = "(予期しないAI応答形式)"
                print(f"Extracted AI response (RAG): {response_text}")
            except Exception as e_text:
                print(f"Error extracting text from RAG response: {e_text}")
                print(f"Full Gemini response object on text extraction error: {response_ai}")
                response_text = "AI応答の取得/解析に失敗しました。"

            return response_text

        except Exception as e:
            print(f"!!! Error during RAG generation: {e}")
            traceback.print_exc()
            return "関連情報はありましたが、AI応答の生成中にエラーが発生しました。しばらくしてからもう一度お試しください。"
    else:
        print("No relevant product context found for RAG.")
        return "申し訳ありません、関連する商品情報が見つかりませんでした。もう少し具体的に質問していただけますか？"

# Intent detection function (using data_store functions)
def detect_intent(query):
    # This function now relies on helper functions from data_store and regex
    query_lower = query.lower()
    try:
        # 1. FAQ Check
        if get_faq_answer(query): # Use helper function
             return "faq"

        # 2. Product Check
        if find_product(query): # Use helper function
            return "product_info"

        # 3. Order Keyword or ID Pattern Check
        if "注文" in query_lower or "オーダー" in query_lower or "発送" in query_lower or "いつ届きますか" in query_lower or "届かない" in query_lower or "配送" in query_lower:
            return "order_status"
        # Check for patterns like "ID: XXX", "Order XYZ", or standalone IDs
        if re.search(r"\b(?:注文(?:番号)?|オーダー|ID)[\s:]+([A-Z0-9-]{3,})\b", query, re.IGNORECASE):
             return "order_status"
        if re.search(r"\b(ORD[0-9-]+|[A-Z]{3}[0-9]{3,}|[0-9]{5,})\b", query, re.IGNORECASE):
             return "order_status"

        # 4. Default to General Chat
        else:
            return "general_chat"
    except Exception as e:
         print(f"!!! Error during intent detection: {e}")
         traceback.print_exc()
         return "general_chat" # Default to general chat on error
# === End Helper Functions ===


# --- Main Chat Route ---
@app.route('/chat', methods=['POST'])
def chat():
    print("--- /chat endpoint called ---")
    response = None # Initialize response variable to ensure something is returned
    try:
        data = request.get_json()
        print(f"Received data: {data}")
        if not data or 'query' not in data:
            print("Error: 'query' not found in request data.")
            return jsonify({"error": "リクエストボディに 'query' が含まれていません。"}), 400

        user_query = data['query'].strip()
        print(f"User query: '{user_query}'")

        intent = detect_intent(user_query)
        print(f"Detected intent: {intent}")

        response_text = "すみません、エラーによりうまく応答できませんでした。" # Default error message

        # --- Intent Routing ---
        if intent == "faq":
            response_text = get_faq_answer(user_query)
            print("--- Handling as FAQ ---")
            if response_text is not None:
                response = jsonify({"response": response_text})
            else:
                print("Error: FAQ intent detected but get_faq_answer returned None. Falling back.")
                intent = "general_chat" # Fallback designation
                print(f"Falling back to intent: {intent}")
                # Let it fall through to the general_chat block

        # Use 'if' here to catch potential fallback from FAQ
        if intent == "product_info":
            response_text = get_product_info_handler(user_query)
            print("--- Handling as Product Info (RAG) ---")
            response = jsonify({"response": response_text})

        elif intent == "order_status":
            # --- Function Calling Logic for Order Status ---
            print("--- Handling as Order Status (Attempting Function Calling) ---")
            if not gemini_model:
                response = jsonify({"error": "AIモデルが利用できない状態です。"}), 500
            elif not available_tools: # Check if tools are defined (depends on protos import)
                 response = jsonify({"error": "Function calling schema is not available. Check imports/definitions."}), 500
            else:
                try:
                    # 1. Initial call to Gemini with tools
                    print(f"Calling Gemini with function declaration for query: '{user_query}'")
                    fc_response = gemini_model.generate_content(
                        user_query,
                        tools=available_tools
                    )
                    print("Gemini responded (initial function call check).")

                    # 2. Check if Gemini requested a function call
                    function_call = None
                    if fc_response.candidates and fc_response.candidates[0].content.parts:
                         part = fc_response.candidates[0].content.parts[0]
                         # Check for function_call attribute AND correct name
                         if hasattr(part, 'function_call') and part.function_call.name == "get_order_info":
                             function_call = part.function_call

                    if function_call:
                        # 3a. Function call requested
                        args = function_call.args
                        order_id_from_ai = args.get('order_id')
                        print(f"Gemini requested call: {function_call.name}({args})")
                        print(f"Extracted order_id by AI: {order_id_from_ai}")

                        # 4. Execute local function
                        function_result_data = get_order_info(order_id_from_ai)
                        print(f"Local function (get_order_info) execution result: {function_result_data}")

                        # 5. Prepare function response content
                        function_response_content = ""
                        if function_result_data:
                            status = function_result_data.get('status', '不明')
                            function_response_content = f"注文ID「{order_id_from_ai}」の状況は「{status}」です。"
                            # Add optional details based on status
                            if status == "発送済み" and function_result_data.get('shipped_date'): function_response_content += f" ({function_result_data.get('shipped_date')}発送)"
                            elif status == "処理中" and function_result_data.get('estimated_delivery'): function_response_content += f" (お届け予定: {function_result_data.get('estimated_delivery')})"
                            elif status == "配達完了" and function_result_data.get('delivered_date'): function_response_content += f" ({function_result_data.get('delivered_date')}配達完了)"
                        else:
                             function_response_content = f"注文ID「{order_id_from_ai}」は見つかりませんでした。"

                        # 6. Send function response BACK to Gemini WITH HISTORY
                        print("Calling Gemini again with history including function response...")
                        # Ensure protos was imported correctly
                        if not protos:
                             raise ImportError("Cannot construct FunctionResponse part because protos module is not available.")
                             
                        function_response_part = protos.Part(
                            function_response=protos.FunctionResponse(
                                name='get_order_info',
                                response={'result': function_response_content}
                            )
                        )
                        # Construct history list
                        history = [
                            protos.Content(role="user", parts=[protos.Part(text=user_query)]),
                            fc_response.candidates[0].content, # Model's previous turn (the function call request)
                            protos.Content(role="tool", parts=[function_response_part]) # Function result turn
                        ]
                        response_final = gemini_model.generate_content(history) # Pass the history list
                        print("Gemini responded (after function call).")

                        # 7. Extract final text response
                        response_text = "(AI最終応答解析エラー)"
                        try:
                            if response_final.candidates and response_final.candidates[0].content.parts:
                                response_text = "".join(part.text for part in response_final.candidates[0].content.parts if hasattr(part,'text'))
                            elif hasattr(response_final, 'text'):
                                 response_text = response_final.text
                            elif response_final.prompt_feedback.block_reason:
                                 print(f"Warning: Final response blocked. Reason: {response_final.prompt_feedback.block_reason}")
                                 response_text = "(最終応答がブロックされました)"
                            else: print(f"Warning: Unexpected final response structure...")
                        except Exception as e_final_text: print(f"Error extracting final text: {e_final_text}")

                    else:
                        # 3b. Function call NOT requested
                        print("Gemini did not request function call. Using its text response.")
                        response_text = "(AI初期応答解析エラー)"
                        try: # Extract from initial response
                            if fc_response.candidates and fc_response.candidates[0].content.parts:
                                response_text = "".join(part.text for part in fc_response.candidates[0].content.parts if hasattr(part,'text'))
                            elif hasattr(fc_response, 'text'):
                                 response_text = fc_response.text
                            elif fc_response.prompt_feedback.block_reason:
                                 print(f"Warning: Initial response blocked. Reason: {fc_response.prompt_feedback.block_reason}")
                                 response_text = "(初期応答がブロックされました)"
                            else: print(f"Warning: Unexpected initial response structure...")
                        except Exception as e_initial_text: print(f"Error extracting initial text: {e_initial_text}")

                    # Set the final response object for order status
                    response = jsonify({"response": response_text})
                    print(f"Final response text for order status intent: {response_text}")

                except Exception as e:
                    print(f"!!! Error during Function Calling process for order status: {e}")
                    traceback.print_exc()
                    response = jsonify({"error": f"注文状況の確認中にエラーが発生しました: {str(e)}"}), 500
        # --- End of Function Calling order_status block ---

        # Check if intent fell through from FAQ or was originally general_chat
        if intent == "general_chat":
            print("--- Handling as General Chat (Calling Gemini) ---")
            if not gemini_api_key or not gemini_model:
                response = jsonify({"error": "AIモデルが利用できない状態です。"}), 500
            else:
                try:
                    print("Calling Gemini model...")
                    gc_response = gemini_model.generate_content(user_query) # Use different var name
                    print("Gemini model responded.")
                    response_text = "(AI一般応答解析エラー)"
                    try: # Extract text
                        if hasattr(gc_response, 'text'): response_text = gc_response.text
                        elif gc_response.candidates and gc_response.candidates[0].content.parts: response_text = "".join(part.text for part in gc_response.candidates[0].content.parts if hasattr(part,'text'))
                        elif gc_response.prompt_feedback.block_reason:
                             print(f"Warning: General response blocked. Reason: {gc_response.prompt_feedback.block_reason}")
                             response_text = "(一般応答がブロックされました)"
                        else: print(f"Warning: Unexpected general response structure...")
                    except Exception as e_text: print(f"Error extracting general text: {e_text}")

                    print(f"Returning JSON response from Gemini: {response_text}")
                    response = jsonify({"response": response_text})

                except Exception as e:
                    print(f"!!! Gemini API call error: {e}")
                    traceback.print_exc()
                    response = jsonify({"error": f"AI応答の生成中に内部エラーが発生しました: {str(e)}"}), 500

        # --- Final Response Check ---
        # Ensure response is set before returning
        if response is None:
             # This should only happen if intent was not faq, product_info, order_status, or general_chat
             print(f"Error: No response generated for intent: {intent}. Returning default error.")
             response = jsonify({"error": "内部サーバーエラー：応答を生成できませんでした。"}), 500

        return response # Return the determined response

    except Exception as e_outer:
         # Catch-all for unexpected errors in the main chat logic
         print(f"!!! Unexpected error in chat function: {e_outer}")
         traceback.print_exc()
         return jsonify({"error": "予期せぬ内部エラーが発生しました。"}), 500
# --- End Routes ---


# --- Server Start ---
if __name__ == '__main__':
    print(">>> Starting Flask server via app.run()...")
    app.run(debug=True, host='0.0.0.0', port=5000)
# --- End Server Start ---