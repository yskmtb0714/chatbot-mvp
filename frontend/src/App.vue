<script setup>
import { ref, watch, nextTick } from 'vue' // watch と nextTick をインポート
import axios from 'axios'

const message = ref(''); // ユーザーの入力メッセージ
const chatHistory = ref([]); // 会話履歴を保持する配列
const isLoading = ref(false); // ローディング状態フラグ
const chatHistoryRef = ref(null); // チャット履歴表示エリアのDOM要素への参照用

// 新しいメッセージが追加された時に、表示エリアの最下部にスクロールする関数
const scrollToBottom = () => {
  // nextTick を使うことで、DOMの更新が完了した後にスクロール処理を実行
  nextTick(() => {
    const container = chatHistoryRef.value;
    if (container) {
      // scrollTop を scrollHeight に設定することで一番下にスクロール
      container.scrollTop = container.scrollHeight;
    }
  });
};

// chatHistory 配列の内容が変更（メッセージが追加）されるたびに scrollToBottom を実行
watch(chatHistory, () => {
  scrollToBottom();
}, { deep: true }); // 配列内部の変更も検知するために deep オプションを true に設定

// メッセージ送信処理を行う非同期関数
const sendMessage = async () => {
  const userMessage = message.value.trim(); // 入力の前後の空白を削除
  // メッセージが空か、既にリクエスト送信中の場合は何もしない
  if (userMessage === '' || isLoading.value) return;

  // ユーザーのメッセージを履歴に追加 (type: 'message' を明示)
  chatHistory.value.push({ sender: 'user', text: userMessage, type: 'message' });
  console.log('送信するメッセージ:', userMessage);
  const messageToSend = message.value; // APIに送るメッセージを一時保存
  message.value = ''; // 送信したら入力欄をクリア
  isLoading.value = true; // ★ ローディング開始状態にする

  try {
    // バックエンドAPI (http://localhost:5000/chat) を呼び出す
    const response = await axios.post('http://localhost:5000/chat', {
      query: messageToSend // { "query": "ユーザーが入力した内容" } を送信
    });
    console.log('バックエンドからの応答:', response.data);

    // AIの応答を履歴に追加 (type: 'message' を明示)
    if (response.data && response.data.response) {
      chatHistory.value.push({ sender: 'ai', text: response.data.response, type: 'message' });
    } else {
      // バックエンドから期待した形式の応答が返ってこなかった場合もエラー扱い
      chatHistory.value.push({ sender: 'ai', text: 'AIから予期しない応答がありました。', type: 'error' });
    }

  } catch (error) {
    // API呼び出し中にエラーが発生した場合
    console.error('API呼び出しエラー:', error);
    let errorMessage = 'エラーが発生しました。';
     if (error.response) {
       // バックエンドからエラー応答(例: 500)が返ってきた場合
       errorMessage = `エラー (ステータス: ${error.response.status})`;
       // もしバックエンドがエラー詳細を返すなら、それを表示することも可能
       // if (error.response.data && error.response.data.error) {
       //   errorMessage += `: ${error.response.data.error}`;
       // }
     } else if (error.request) {
       // バックエンドから応答が全くなかった場合 (net::ERR_FAILEDなど)
       errorMessage = 'サーバーから応答がありません。バックエンドは起動していますか？';
     }
    // エラーメッセージを type: 'error' 付きで履歴に追加
    chatHistory.value.push({ sender: 'ai', text: errorMessage, type: 'error' });
  } finally {
    // 成功・失敗に関わらずローディング状態を解除
    isLoading.value = false; // ★ ローディング終了状態にする
  }
};
</script>

<template>
  <div id="app-container">
    <h1>チャットボット MVP</h1>

    <div class="chat-history" ref="chatHistoryRef">
      <div v-if="chatHistory.length === 0 && !isLoading" class="no-messages">
        メッセージを入力して会話を開始してください。
      </div>
      <div v-for="(msg, index) in chatHistory" :key="index"
           :class="['message-wrapper', msg.sender === 'user' ? 'user-wrapper' : 'ai-wrapper']">
         <div :class="['message',
                       msg.sender === 'user' ? 'user-message' : 'ai-message',
                       msg.type === 'error' ? 'error-message' : '']">
          <span class="text">{{ msg.text }}</span>
        </div>
      </div>
      <div v-if="isLoading" class="message-wrapper ai-wrapper loading-indicator">
          <div class="message ai-message loading-message">
              <div class="spinner"></div>
              <span class="text loading-text">AIが考え中...</span>
          </div>
      </div>
    </div>

    <div class="input-area">
      <input
        type="text"
        v-model="message"
        placeholder="メッセージを入力してください..."
        @keyup.enter="sendMessage"
        :disabled="isLoading"
      />
      <button @click="sendMessage" :disabled="isLoading">
        {{ isLoading ? '送信中...' : '送信' }}
      </button>
    </div>

  </div>
</template>

<style scoped>
/* スタイル定義 - 前回調整したもの + ローディング/エラー用スタイル */
#app-container {
  max-width: 650px; 
  margin: 25px auto; 
  padding: 25px;
  border: 1px solid #e0e0e0; 
  border-radius: 10px; 
  font-family: "Segoe UI", Meiryo, system-ui, sans-serif; 
  display: flex; 
  flex-direction: column; 
  height: 88vh; 
  box-shadow: 0 5px 15px rgba(0,0,0,0.12); 
  background-color: #ffffff; 
}

h1 {
  text-align: center;
  color: #343a40; 
  margin-bottom: 20px; 
  flex-shrink: 0; 
  font-weight: 600;
  font-size: 1.4em; 
}

.chat-history {
  flex-grow: 1; 
  overflow-y: auto; 
  border: none; 
  border-radius: 8px; 
  padding: 15px; 
  margin-bottom: 20px; 
  background-color: #f8f9fa; 
}
.chat-history::-webkit-scrollbar { width: 8px; }
.chat-history::-webkit-scrollbar-thumb { background-color: #ced4da; border-radius: 4px; }
.chat-history::-webkit-scrollbar-track { background-color: #f1f1f1; }

.no-messages {
    text-align: center;
    color: #aaa; 
    padding: 40px 20px; 
    font-style: italic;
}

.message-wrapper {
  margin-bottom: 15px; 
  display: flex;
}

.user-wrapper {
  justify-content: flex-end; 
}

.ai-wrapper {
  justify-content: flex-start; 
}

.message {
  padding: 10px 16px; 
  border-radius: 18px; 
  display: inline-block; 
  max-width: 78%; 
  word-wrap: break-word; 
  line-height: 1.5; 
  box-shadow: 0 1px 2px rgba(0,0,0,0.1); 
  position: relative; 
}

.user-message {
  background-color: #0d6efd; 
  color: white;
  border-bottom-right-radius: 6px; 
}

.ai-message {
  background-color: #e9ecef; 
  color: #212529; 
  border-bottom-left-radius: 6px; 
}

/* --- ★ ローディング表示用スタイル ★ --- */

.loading-message { /* 「考え中」の吹き出し自体のスタイル */
  background-color: transparent !important; /* 背景を透過 */
  border: none !important; /* 枠線も消す */
  box-shadow: none !important; /* 影も消す */
  padding-top: 5px; 
  padding-bottom: 5px;
  display: flex; /* スピナーとテキストを横並び */
  align-items: center; /* 縦方向中央揃え */
}
.loading-text { 
    font-style: italic;
    color: #6c757d; 
    margin-left: 8px; /* スピナーとの間隔 */
}
.spinner {
    border: 3px solid #f0f0f0; /* スピナーの背景色 */
    border-top: 3px solid #6c757d; /* スピナーの色 */
    border-radius: 50%;
    width: 16px; /* スピナーのサイズ */
    height: 16px;
    animation: spin 1s linear infinite; /* 回転アニメーション */
    display: inline-block;
}
@keyframes spin { /* 回転アニメーションの定義 */
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
/* --- ★ ローディング表示用スタイルここまで ★ --- */

/* --- ★ エラーメッセージ用スタイル ★ --- */
.error-message { /* .message にこのクラスが付与される */
  background-color: #f8d7da !important; /* 薄い赤背景 (!importantで他の背景色指定を上書き) */
  color: #721c24 !important;           /* 濃い赤テキスト */
  border: 1px solid #f5c6cb;         /* 赤系の枠線 */
}
/* aiメッセージとして表示されるエラーの場合の調整 */
.ai-wrapper .error-message {
   border-bottom-left-radius: 6px; /* 他のAIメッセージと角の丸みを合わせる */
}
/* --- ★ エラーメッセージ用スタイルここまで ★ --- */

.text { 
  white-space: pre-wrap; 
}

.input-area {
  display: flex;
  align-items: center; 
  margin-top: auto; 
  flex-shrink: 0; 
  padding-top: 15px; 
  border-top: 1px solid #eee;
}

.input-area input[type="text"] {
  flex-grow: 1;
  margin-right: 10px;
  padding: 11px 16px; 
  border: 1px solid #ced4da; 
  border-radius: 20px; 
  font-size: 1rem; 
}
.input-area input[type="text"]:focus { 
  outline: none;
  border-color: #86b7fe; 
  box-shadow: 0 0 0 0.2rem rgba(13, 110, 253, 0.25); 
}

.input-area button {
  padding: 11px 20px; 
  border: none;
  background-color: #0d6efd; 
  color: white;
  border-radius: 20px; 
  cursor: pointer;
  font-size: 1rem;
  font-weight: 500; 
  transition: background-color 0.2s ease; 
  flex-shrink: 0; 
}

.input-area button:disabled {
  background-color: #adb5bd; 
  cursor: not-allowed;
}

.input-area button:hover:not(:disabled) {
  background-color: #0b5ed7; 
}
</style>