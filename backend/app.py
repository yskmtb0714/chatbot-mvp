# backend/app.py - Final version with RAG, Function Calling, and English localization (code/prompts/messages)
import os
import traceback
import re
import json # Good practice import
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai

# Import protos safely for Function Calling types/history
try:
    from google.generativeai import protos
    print("Imported protos from google.generativeai")
except ImportError:
    try:
        # Fallback import path for protos
        from google.ai import generativelanguage_v1beta as protos
        print("Imported protos successfully from google.ai.generativelanguage_v1beta")
    except ImportError:
        print("!!! Critical Error: Failed to import 'protos'. Function Calling history/response might fail.")
        protos = None # Define as None if unavailable

# Attempt to import necessary classes for potential schema object construction or type checking
# Define fallbacks to None if imports fail, so NameErrors are avoided later
try:
    from google.generativeai.types import FunctionDeclaration, Tool, Schema, Type
    print("Imported FC classes (FunctionDeclaration, Tool, Schema, Type) from google.generativeai.types")
except ImportError:
     try:
         from google.generativeai import FunctionDeclaration, Tool, Schema, Type
         print("Imported FC classes (FunctionDeclaration, Tool, Schema, Type) from google.generativeai")
     except ImportError:
         print("!!! Warning: Failed to import FunctionDeclaration, Tool, Schema, or Type. Object construction skipped.")
         # Define as None to prevent NameErrors if code relying on these classes remains
         FunctionDeclaration, Tool, Schema, Type = None, None, None, None

# Attempt to import ToolConfig/FunctionCallingConfig safely (for potential future use)
try:
    from google.generativeai.types import ToolConfig, FunctionCallingConfig
    print("Imported ToolConfig/FunctionCallingConfig from google.generativeai.types")
except ImportError:
     try:
         from google.generativeai import ToolConfig, FunctionCallingConfig
         print("Imported ToolConfig/FunctionCallingConfig from google.generativeai")
     except ImportError:
         print("Info: Could not import ToolConfig/FunctionCallingConfig. Tool Config functionality disabled.")
         ToolConfig = None
         FunctionCallingConfig = None

from flask_cors import CORS
# Import helper functions from data_store safely
try:
    from data_store import get_faq_answer, find_product, get_order_info, retrieve_product_info
    print("Successfully imported functions from data_store.")
except ImportError as e:
     print(f"!!! Error importing from data_store: {e}")
     print("!!! Please ensure data_store.py exists in the backend folder and defines necessary functions.")
     # Define dummy functions to allow app to potentially start for debugging other parts
     def get_faq_answer(q): return None
     def find_product(q): return None
     def get_order_info(q): return None
     def retrieve_product_info(q): return None

load_dotenv() # Load environment variables from .env file

# --- Gemini API Initialization ---
gemini_api_key = os.getenv('GEMINI_API_KEY')
gemini_model = None
if gemini_api_key:
    try:
        genai.configure(api_key=gemini_api_key)
        gemini_model = genai.GenerativeModel('gemini-1.5-flash-latest') # Specify model
        print("Gemini API Key configured and Model initialized.")
    except Exception as e:
        print(f"Error during Gemini setup: {e}")
        gemini_api_key = None
        gemini_model = None
else:
    print("Warning: Gemini API Key not found in .env file.")
# --- End Gemini API Initialization ---


# --- Function Calling Schema Definition (Dictionary Version - Using STRING Types) ---
available_tools = None # Initialize
try:
    # Define schema using simple dictionary and string types
    get_order_info_func_declaration = {
        "name": "get_order_info",
        # English description for the function
        "description": "Retrieves the current status (e.g., shipped, processing) and details for a specific order based on the provided order ID.",
        "parameters": {
            "type": "OBJECT", # Use string "OBJECT"
            "properties": {
                "order_id": {
                    "type": "STRING", # Use string "STRING"
                    # English description for the parameter
                    "description": "The unique identifier or number of the order to check the status for (e.g., 'ORD123', 'XYZ789')"
                }
            },
            "required": ["order_id"]
        }
    }
    # Assign the schema dictionary to the list of available tools
    available_tools = [get_order_info_func_declaration]
    print("Function calling schema defined using DICTIONARY.")
except Exception as e_dict_schema:
    print(f"!!! Error defining dictionary schema: {e_dict_schema}")
    available_tools = None

if available_tools is None:
     print("Warning: `available_tools` (dictionary schema) could not be defined. Function Calling will be skipped.")
# --- End Function Calling Schema Definition ---


# --- Flask App Setup ---
app = Flask(__name__)
CORS(app) # Enable CORS
# --- End Flask App Setup ---


# === Helper Functions ===
# (Defined AFTER app setup, BEFORE routes using them)

# RAG version of product info handler (English prompt & messages)
def get_product_info_handler(query):
    print(f"--- Intent: Product Info Query Received (RAG attempt): '{query}' ---")
    retrieved_context = retrieve_product_info(query) # Calls data_store function

    if retrieved_context:
        print("Context retrieved, proceeding to generate response with Gemini.")
        if not gemini_model:
             return "The AI model is not ready, so product descriptions cannot be generated. Please contact the administrator."
        try:
            # RAG Prompt using English instructions
            prompt_for_ai = f"""Based *only* on the relevant information below, please answer the customer's question **in English**. Summarize and edit the information into a natural conversational response, not bullet points. If the information is not present, state honestly that you cannot answer from the provided information. You are a friendly shop assistant.

# Relevant Information
{retrieved_context}

# Customer Question
{query}

# Assistant Response (in English):""" # Respond in English instruction
            print(f"--- RAG Prompt for Gemini ---\n{prompt_for_ai}\n---------------------------")

            print("Calling Gemini model for RAG response...")
            response_ai = gemini_model.generate_content(prompt_for_ai)
            print("Gemini model responded for RAG.")

            response_text = "(Error parsing AI response)" # English default
            try: # Robust text extraction
                if response_ai.candidates and response_ai.candidates[0].content.parts:
                    response_text = "".join(part.text for part in response_ai.candidates[0].content.parts if hasattr(part,'text'))
                elif hasattr(response_ai, 'text'):
                     response_text = response_ai.text
                elif response_ai.prompt_feedback.block_reason:
                     print(f"Warning: RAG response blocked. Reason: {response_ai.prompt_feedback.block_reason}")
                     response_text = "(The response was blocked due to safety settings.)" # English
                else:
                     print(f"Warning: Unexpected RAG response structure. Full response: {response_ai}")
                     response_text = "(Unexpected AI response format.)" # English
                print(f"Extracted AI response (RAG): {response_text}")
            except Exception as e_text:
                print(f"Error extracting text from RAG response: {e_text}")
                print(f"Full Gemini response object on text extraction error: {response_ai}")
                response_text = "Failed to get/parse AI product description." # English

            return response_text

        except Exception as e:
            print(f"!!! Error during RAG generation: {e}")
            traceback.print_exc()
            # English message
            return "Relevant information was found, but an error occurred during AI response generation. Please try again later."
    else:
        print("No relevant product context found for RAG.")
        # English message
        return "Sorry, no relevant product information was found. Could you please ask more specifically?"

# Intent detection function (using data_store functions & added English keywords)
def detect_intent(query):
    query_lower = query.lower()
    try:
        # 1. FAQ Check
        if get_faq_answer(query): # Still uses Japanese keys from data_store for now
             return "faq"

        # 2. Product Check
        if find_product(query): # Uses Japanese names/keywords from data_store/products.json for now
            return "product_info"

        # 3. Order Keyword or ID Pattern Check (Added English keywords)
        order_keywords = ["注文", "オーダー", "発送", "いつ届きますか", "届かない", "配送", "order", "shipment", "delivery", "status", "track"]
        if any(keyword in query_lower for keyword in order_keywords):
            return "order_status"
        # Check for patterns like "ID: XXX", "Order XYZ" using regex (includes English keywords)
        if re.search(r"\b(?:注文(?:番号)?|オーダー|ID|order\s?(?:number|no|id)?)[\s:]+([A-Z0-9-]{3,})\b", query, re.IGNORECASE):
             return "order_status"
        # Check for standalone ID patterns
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
    response = None # Initialize response variable
    try:
        data = request.get_json()
        print(f"Received data: {data}")
        if not data or 'query' not in data:
            return jsonify({"error": "Request body must contain 'query'."}), 400 # English

        user_query = data['query'].strip()
        print(f"User query: '{user_query}'")

        intent = detect_intent(user_query)
        print(f"Detected intent: {intent}")

        # Default error message (English)
        response_text = "Sorry, I could not respond properly due to an internal error."

        # --- Intent Routing ---
        if intent == "faq":
            response_text = get_faq_answer(user_query) # Assumes returns Japanese from data
            print("--- Handling as FAQ ---")
            if response_text is not None:
                response = jsonify({"response": response_text})
            else:
                print("FAQ intent detected but no specific answer found. Falling back.")
                intent = "general_chat" # Fallback designation
                print(f"Falling back to intent: {intent}")
                # Let it fall through

        # Check product_info AFTER potential fallback from faq
        if intent == "product_info":
            response_text = get_product_info_handler(user_query) # Handler returns English messages
            print("--- Handling as Product Info (RAG) ---")
            response = jsonify({"response": response_text})

        elif intent == "order_status":
            # --- Function Calling Logic for Order Status ---
            print("--- Handling as Order Status (Attempting Function Calling) ---")
            if not gemini_model:
                response = jsonify({"error": "AI model is not available."}), 500 # English
            elif not available_tools: # Check if dictionary schema was defined
                 response = jsonify({"error": "Function calling configuration is not available."}), 500 # English
            else:
                try:
                    # tool_config remains None (forcing AUTO mode)
                    tool_config_value = None
                    print(f"Calling Gemini with function declaration for query: '{user_query}' (Mode: Default/AUTO)")
                    fc_response = gemini_model.generate_content(
                        user_query,
                        tools=available_tools,
                        tool_config=tool_config_value
                    )
                    print("Gemini responded (initial function call check).")

                    # Check if Gemini requested a function call
                    function_call = None
                    if fc_response.candidates and fc_response.candidates[0].content.parts:
                         part = fc_response.candidates[0].content.parts[0]
                         if hasattr(part, 'function_call') and part.function_call.name == "get_order_info":
                             function_call = part.function_call

                    if function_call:
                        # Function call requested
                        args = function_call.args
                        order_id_from_ai = args.get('order_id')
                        print(f"Gemini requested call: {function_call.name}({args})")
                        print(f"Extracted order_id by AI: {order_id_from_ai}")

                        # Execute local function
                        function_result_data = get_order_info(order_id_from_ai)
                        print(f"Local func result: {function_result_data}")

                        # Prepare function response content (English frame)
                        if function_result_data:
                            status = function_result_data.get('status', 'Unknown')
                            # Construct English response frame, status might still be JP from data
                            function_response_content = f"The status for Order ID '{order_id_from_ai}' is '{status}'."
                            if status == "発送済み" and function_result_data.get('shipped_date'): function_response_content += f" (Shipped on {function_result_data.get('shipped_date')})"
                            elif status == "処理中" and function_result_data.get('estimated_delivery'): function_response_content += f" (Estimated delivery: {function_result_data.get('estimated_delivery')})"
                            elif status == "配達完了" and function_result_data.get('delivered_date'): function_response_content += f" (Delivered on {function_result_data.get('delivered_date')})"
                        else:
                             function_response_content = f"Order ID '{order_id_from_ai}' was not found." # English

                        # Send function response BACK to Gemini WITH HISTORY
                        print("Calling Gemini again with history including function response...")
                        if not protos: raise ImportError("Protos module is required for history construction.")

                        function_response_part = protos.Part(
                            function_response=protos.FunctionResponse(
                                name='get_order_info',
                                response={'result': function_response_content}
                            )
                        )
                        history = [
                            protos.Content(role="user", parts=[protos.Part(text=user_query)]),
                            fc_response.candidates[0].content, # Model's previous turn
                            protos.Content(role="tool", parts=[function_response_part]) # Tool result turn
                        ]
                        # Add final instruction for English response
                        history.append(
                            protos.Content(role="user", parts=[protos.Part(text="Now, using the function result provided, please answer the original user query in English.")])
                        )
                        response_final = gemini_model.generate_content(history) # Pass the history list
                        print("Gemini responded (after function call).")

                        # Extract final text response
                        response_text = "(Error parsing final AI response)" # English default
                        try: # Robust extraction
                            if response_final.candidates and response_final.candidates[0].content.parts: response_text = "".join(part.text for part in response_final.candidates[0].content.parts if hasattr(part,'text'))
                            elif hasattr(response_final, 'text'): response_text = response_final.text
                            elif response_final.prompt_feedback.block_reason: print(f"Warning: Final response blocked..."); response_text = "(The final response was blocked.)" # English
                            else: print(f"Warning: Unexpected final response structure...")
                        except Exception as e_final_text: print(f"Error extracting final text: {e_final_text}")

                    else:
                        # Function call NOT requested
                        print("Gemini did not request function call. Using its text response.")
                        response_text = "(Error parsing initial AI response)" # English default
                        try: # Extract from initial response
                            if fc_response.candidates and fc_response.candidates[0].content.parts: response_text = "".join(part.text for part in fc_response.candidates[0].content.parts if hasattr(part,'text'))
                            elif hasattr(fc_response, 'text'): response_text = fc_response.text
                            elif fc_response.prompt_feedback.block_reason: print(f"Warning: Initial response blocked..."); response_text = "(The initial response was blocked.)" # English
                            else: print(f"Warning: Unexpected initial response structure...")
                        except Exception as e_initial_text: print(f"Error extracting initial text: {e_initial_text}")

                    print(f"Final response text for order status intent: {response_text}")
                    response = jsonify({"response": response_text}) # Set response here

                except Exception as e:
                    print(f"!!! Error during Function Calling process for order status: {e}")
                    traceback.print_exc()
                    # English error
                    response = jsonify({"error": f"An error occurred while checking order status: {str(e)}"}), 500
        # --- End of Function Calling order_status block ---

        # Check if intent fell through from FAQ or was originally general_chat
        if intent == "general_chat":
            print("--- Handling as General Chat (Calling Gemini) ---")
            if not gemini_api_key or not gemini_model:
                response = jsonify({"error": "AI model is not available."}), 500 # English
            else:
                try:
                    # Prepend English instruction
                    prompt_with_instruction = f"Please respond in English.\n\nUser query: {user_query}"
                    print(f"Calling Gemini model with instruction: {prompt_with_instruction}")
                    gc_response = gemini_model.generate_content(prompt_with_instruction)
                    print("Gemini model responded.")

                    response_text = "(Error parsing general AI response)" # English default
                    try: # Extract text
                       if hasattr(gc_response, 'text'): response_text = gc_response.text
                       elif gc_response.candidates and gc_response.candidates[0].content.parts: response_text = "".join(part.text for part in gc_response.candidates[0].content.parts if hasattr(part,'text'))
                       elif gc_response.prompt_feedback.block_reason: print(f"Warning: General response blocked..."); response_text = "(General response was blocked)" # English
                       else: print(f"Warning: Unexpected general response structure...")
                    except Exception as e_text: print(f"Error extracting general text: {e_text}")

                    print(f"Returning JSON response from Gemini: {response_text}")
                    response = jsonify({"response": response_text})
                except Exception as e:
                    print(f"!!! Gemini API call error: {e}")
                    traceback.print_exc()
                    # English error
                    response = jsonify({"error": f"An internal error occurred during AI response generation: {str(e)}"}), 500

        # --- Final Response Check ---
        # If 'response' object was not set by any handler above (e.g., only FAQ fallback happened), return error
        if response is None:
             print(f"Error: No response object generated for intent '{intent}'. Returning default error.")
             # English error
             response = jsonify({"error": "Internal server error: Could not generate response."}), 500

        return response # Return the determined response object

    except Exception as e_outer:
         # Catch-all for unexpected errors in the main chat logic
         print(f"!!! Unexpected error in chat function: {e_outer}")
         traceback.print_exc()
         # English error
         return jsonify({"error": "An unexpected internal error occurred."}), 500
# --- End Routes ---


# --- Server Start ---
if __name__ == '__main__':
    print(">>> Starting Flask server via app.run()...")
    app.run(debug=True, host='0.0.0.0', port=5000)
# --- End Server Start ---