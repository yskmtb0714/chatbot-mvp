import json
import os
# === データ定義 ===
# FAQデータベース
faq_database = {
    "送料はいくらですか？": "全国一律500円（税込）となっております。",
    "営業時間は？": "当店の営業時間は、平日午前9時から午後6時までです。",
    "支払い方法は何がありますか？": "クレジットカード、銀行振込、代金引換がご利用いただけます。"
}
# ダミー商品データベース
# --- product_databaseをJSONファイルから読み込む ---
product_database = [] # デフォルトは空リストにする
# このファイルの場所を基準に products.json へのパスを作成
PRODUCT_DATA_PATH = os.path.join(os.path.dirname(__file__), 'products.json') 

try:
    # ファイルが存在するか確認
    if os.path.exists(PRODUCT_DATA_PATH):
        # ファイルを開いてJSONデータを読み込む (文字コードはutf-8を指定)
        with open(PRODUCT_DATA_PATH, 'r', encoding='utf-8') as f:
            product_database = json.load(f)
        print(f"正常に商品データを読み込みました: {PRODUCT_DATA_PATH}")
    else:
        # ファイルが存在しない場合の警告
        print(f"警告: 商品データファイルが見つかりません: {PRODUCT_DATA_PATH}。空の商品リストを使用します。")
except json.JSONDecodeError:
    # JSONの形式が正しくない場合のエラー
    print(f"エラー: {PRODUCT_DATA_PATH} のJSON形式が正しくありません。ファイル内容を確認してください。")
    product_database = [] # エラー時は空にする
except Exception as e:
    # その他の予期せぬエラー
    print(f"商品データの読み込み中に予期せぬエラーが発生しました: {e}")
    product_database = [] # エラー時は空にする
# --- JSON読み込み処理ここまで ---

# order_database = [...] # 注文データはまだPythonリストのまま
# === データ定義ここまで ===
# backend/app.py の product_database の定義の後あたりに追加

# ダミーの注文データ
order_database = [
    {
        "order_id": "ORD123", 
        "customer_name": "テストユーザーA", # 任意項目
        "status": "発送済み", 
        "shipped_date": "2025-04-10" # 任意項目
    },
    {
        "order_id": "ORD456", 
        "customer_name": "テストユーザーB", 
        "status": "処理中", 
        "estimated_delivery": "2025-04-16" # 任意項目
    },
     {
        "order_id": "XYZ789", # 違う形式のIDも入れてみる
        "customer_name": "テストユーザーC", 
        "status": "配達完了", 
        "delivered_date": "2025-04-12" # 任意項目
    }
    # ここに他の注文情報を追加できます
]
# === Databases ===
faq_database = {
    "送料はいくらですか？": "全国一律500円（税込）となっております。",
    "営業時間は？": "当店の営業時間は、平日午前9時から午後6時までです。",
    "支払い方法は何がありますか？": "クレジットカード、銀行振込、代金引換がご利用いただけます。"
    # 必要に応じてFAQを追加
}

product_database = [
    {
        "id": "prod001",
        "name": "すごいTシャツ",
        "keywords": ["tシャツ", "t-shirt", "すごいtシャツ"],
        "price": 3000,
        "description": "着心地抜群！最新技術で作られたすごいTシャツです。色は白と黒があります。"
    },
    {
        "id": "prod002",
        "name": "便利なマグカップ",
        "keywords": ["マグカップ", "カップ", "便利なマグカップ"],
        "price": 1500,
        "description": "取っ手が持ちやすく、たっぷり容量の便利なマグカップ。コーヒータイムに最適です。"
    },
    {
        "id": "prod003",
        "name": "多機能ボールペン",
        "keywords": ["ボールペン", "ペン", "多機能ボールペン", "多機能ペン"],
        "price": 800,
        "description": "黒・赤ボールペンとシャープペンシルが一本になった多機能ペン。ビジネスシーンで活躍します。"
    }
    # ここに他の商品情報を追加できます
]

order_database = [
    {
        "order_id": "ORD123",
        "customer_name": "テストユーザーA",
        "status": "発送済み",
        "shipped_date": "2025-04-10"
    },
    {
        "order_id": "ORD456",
        "customer_name": "テストユーザーB",
        "status": "処理中",
        "estimated_delivery": "2025-04-16"
    },
     {
        "order_id": "XYZ789",
        "customer_name": "テストユーザーC",
        "status": "配達完了",
        "delivered_date": "2025-04-12"
    }
    # ここに他の注文情報を追加できます
]
# === End Databases ===


# === Data Access Functions ===

def get_faq_answer(query):
    """FAQデータベースを完全一致で検索し、回答を返す"""
    return faq_database.get(query) # キーが見つかれば値を、なければNoneを返す

def find_product(query):
    """ユーザーの質問から商品名またはキーワードに一致する商品を検索する"""
    query_lower = query.lower()
    for product in product_database:
        # 商品名チェック
        if product['name'].lower() in query_lower:
             return product # 商品辞書全体を返す
        # キーワードチェック
        for keyword in product.get("keywords", []):
            if keyword in query_lower:
                return product # 商品辞書全体を返す
    return None # 見つからなければNoneを返す

def get_order_info(order_id):
     """注文IDで注文情報を検索する (大文字小文字区別なし)"""
     if not order_id: # order_idがNoneや空文字列の場合はNoneを返す
          return None
     order_id_upper = order_id.upper() # 比較用に大文字に統一
     for order in order_database:
         # order_idキーが存在し、かつ値が一致するかチェック
         if order.get("order_id") and order.get("order_id").upper() == order_id_upper:
             return order # 注文辞書全体を返す
     return None # 見つからなければNoneを返す

def retrieve_product_info(query):
    """
    質問文に商品名やキーワードが含まれる商品を product_database から探し、
    関連情報（上位いくつか）を整形した文字列で返す。見つからなければ None を返す。
    """
    print(f"--- Retrieving product info for query: '{query}' ---")
    query_lower = query.lower()
    relevant_info = []

    # データベース内の全商品をチェック
    for product in product_database:
        match_score = 0 # 簡単な関連度スコア
        product_name_lower = product['name'].lower()

        # 商品名が部分一致でも含まれていたらスコアを加算
        if product_name_lower in query_lower:
             match_score += 2 # 名前一致は重要度高め
             print(f"-> Name match: '{product['name']}'")

        # キーワードが含まれていたらスコアを加算
        product_keywords = product.get("keywords", [])
        for keyword in product_keywords:
            if keyword in query_lower:
                match_score += 1
                print(f"-> Keyword match: '{keyword}' in '{product['name']}'")
                break # 1商品につき1キーワードマッチで十分とする

        # スコアが0より大きい（何らかの一致があった）場合、リストに追加
        if match_score > 0:
            # AIに渡す情報（例：商品名、価格、説明）を整形
            info_str = f"商品名: {product['name']}\n価格: {product['price']}円\n説明: {product['description']}"
            relevant_info.append({"score": match_score, "info": info_str})

    # マッチする情報が何もなければ None を返す
    if not relevant_info:
        print("--- No relevant product info found. ---")
        return None

    # スコアの高い順に並び替え（任意だが推奨）
    relevant_info.sort(key=lambda x: x['score'], reverse=True)

    # スコア上位 N 件（例: 2件）の情報を結合して最終的なコンテキスト文字列を作成
    # ※件数を増やすとプロンプトが長くなる
    context_str = "関連する可能性のある商品情報:\n\n" 
    context_str += "\n\n---\n\n".join([item['info'] for item in relevant_info[:2]]) # 上位2件を結合

    print(f"--- Retrieved Product Context (Top {len(relevant_info[:2])}) ---\n{context_str}\n-----------------------------")
    return context_str # 整形された文字列（検索結果）を返す