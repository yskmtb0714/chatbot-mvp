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

  // ユーザーのメッセージを履歴に追加
  chatHistory.value.push({ sender: 'user', text: userMessage });
  console.log('送信するメッセージ:', userMessage);
  const messageToSend = message.value; // APIに送るメッセージを一時保存
  message.value = ''; // 送信したら入力欄をクリア
  isLoading.value = true; // ローディング状態にする

  try {
    // バックエンドAPI (http://localhost:5000/chat) を呼び出す
    const response = await axios.post('http://localhost:5000/chat', {
      query: messageToSend // { "query": "ユーザーが入力した内容" } を送信
    });
    console.log('バックエンドからの応答:', response.data);

    // AIの応答を履歴に追加
    if (response.data && response.data.response) {
      chatHistory.value.push({ sender: 'ai', text: response.data.response });
    } else {
      // バックエンドから期待した形式の応答が返ってこなかった場合
      chatHistory.value.push({ sender: 'ai', text: 'AIから予期しない応答がありました。' });
    }

  } catch (error) {
    // API呼び出し中にエラーが発生した場合
    console.error('API呼び出しエラー:', error);
    let errorMessage = 'エラーが発生しました。';
     if (error.response) {
       // バックエンドからエラー応答が返ってきた場合
       errorMessage = `エラー (ステータス: ${error.response.status})`;
     } else if (error.request) {
       // バックエンドから応答が全くなかった場合
       errorMessage = 'サーバーから応答がありません。バックエンドは起動していますか？';
     }
    // エラーメッセージを履歴に追加
    chatHistory.value.push({ sender: 'ai', text: errorMessage });
  } finally {
    // 成功・失敗に関わらずローディング状態を解除
    isLoading.value = false;
  }
};
</script>

<template>
  <div id="app-container">
    <h1>チャットボット MVP</h1>

    <div class="chat-history" ref="chatHistoryRef">
      <div v-if="chatHistory.length === 0" class="no-messages">
        メッセージを入力して会話を開始してください。
      </div>
      <div v-for="(msg, index) in chatHistory" :key="index"
           :class="['message-wrapper', msg.sender === 'user' ? 'user-wrapper' : 'ai-wrapper']">
        <div :class="['message', msg.sender === 'user' ? 'user-message' : 'ai-message']">
          <span class="text">{{ msg.text }}</span>
        </div>
      </div>
      <div v-if="isLoading" class="message-wrapper ai-wrapper">
          <div class="message ai-message loading-message">
              <span class="text">考え中...</span>
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
/* App.vue スタイル全体 - 微調整版 */
#app-container {
  max-width: 650px; /* 最大幅を少し広げる */
  margin: 25px auto; /* 上下マージン調整 */
  padding: 25px; /* 内側パディング */
  border: 1px solid #e0e0e0; /* 枠線の色 */
  border-radius: 10px; /* 角の丸み */
  font-family: "Segoe UI", Meiryo, system-ui, sans-serif; /* フォント (メイリオ追加) */
  display: flex;
  flex-direction: column;
  height: 88vh; /* 高さを少し調整 */
  box-shadow: 0 5px 15px rgba(0,0,0,0.12); /* 影を調整 */
  background-color: #ffffff; /* 背景色 */
}

h1 {
  text-align: center;
  color: #343a40; /* 見出しの色 */
  margin-bottom: 20px; /* 下マージン調整 */
  flex-shrink: 0;
  font-weight: 600;
  font-size: 1.4em; /* 文字サイズ調整 */
}

.chat-history {
  flex-grow: 1;
  overflow-y: auto; /* スクロール */
  border: none; /* 履歴エリアの枠線削除 */
  border-radius: 8px;
  padding: 15px; /* パディング調整 */
  margin-bottom: 20px; /* 下マージン調整 */
  background-color: #f8f9fa; /* 履歴エリアの背景色 */
}
/* スクロールバーの見た目調整（Chrome, Edge, Safariなど） */
.chat-history::-webkit-scrollbar {
  width: 8px;
}
.chat-history::-webkit-scrollbar-thumb {
  background-color: #ced4da; /* スクロールバーの色 */
  border-radius: 4px;
}
.chat-history::-webkit-scrollbar-track {
  background-color: #f1f1f1; /* スクロールバーの背景 */
}

.no-messages {
    text-align: center;
    color: #aaa;
    padding: 40px 20px; /* パディング調整 */
    font-style: italic;
}

.message-wrapper {
  margin-bottom: 15px; /* メッセージ間のスペース */
  display: flex;
}

.user-wrapper {
  justify-content: flex-end; /* ユーザーメッセージを右寄せ */
}

.ai-wrapper {
  justify-content: flex-start; /* AIメッセージを左寄せ */
}

.message {
  padding: 10px 16px; /* メッセージ内のパディング */
  border-radius: 18px; /* 角の丸み */
  display: inline-block;
  max-width: 78%; /* メッセージの最大幅 */
  word-wrap: break-word;
  line-height: 1.5; /* 行間 */
  box-shadow: 0 2px 3px rgba(0,0,0,0.08); /* 影 */
  position: relative;
}

.user-message {
  background-color: #0d6efd; /* ユーザーメッセージの背景色 (青系) */
  color: white;
  border-bottom-right-radius: 6px; /* 右下に少し角 */
}

.ai-message {
  background-color: #e9ecef; /* AIメッセージの背景色 (グレー系) */
  color: #212529;
  border-bottom-left-radius: 6px; /* 左下に少し角 */
}

.loading-message .text { 
    font-style: italic; /* 斜体にする */
    color: #6c757d;     /* テキスト色をグレーに */
    background-color: #f8f9fa !important; /* 背景を履歴エリアに近づける (ai-messageより優先) */
    /* 点滅アニメーションなどを追加するとより分かりやすいですが、まずはここまで */
    padding: 10px 16px; /* 通常メッセージと合わせる */
    border-radius: 18px;
    display: inline-block;
    box-shadow: none; /* 影を消す */
}
/* ローディングメッセージのラッパーにもスタイルを適用（任意） */
.loading-message {
    /* background: none !important; */ /* 背景を透過させる場合など */
    box-shadow: none !important; /* 影を消す */
}

.text {
  white-space: pre-wrap; /* テキストの改行を反映 */
}

.input-area {
  display: flex;
  align-items: center;
  margin-top: auto; /* 下部に固定 */
  flex-shrink: 0;
  padding-top: 15px;
  border-top: 1px solid #eee;
}

.input-area input[type="text"] {
  flex-grow: 1;
  margin-right: 10px;
  padding: 11px 16px; /* 入力欄のパディング */
  border: 1px solid #ced4da; /* 枠線の色 */
  border-radius: 20px; /* 角の丸み */
  font-size: 1rem;
}
/* 入力欄がフォーカスされた時のスタイル */
.input-area input[type="text"]:focus {
  outline: none;
  border-color: #86b7fe; /* フォーカス時の色 */
  box-shadow: 0 0 0 0.2rem rgba(13, 110, 253, 0.25); /* フォーカス時の影 */
}

.input-area button {
  padding: 11px 20px; /* ボタンのパディング */
  border: none;
  background-color: #0d6efd; /* ボタンの色 */
  color: white;
  border-radius: 20px; /* 角の丸み */
  cursor: pointer;
  font-size: 1rem;
  font-weight: 500;
  transition: background-color 0.2s ease; /* ホバー時の色変化を滑らかに */
  flex-shrink: 0;
}

.input-area button:disabled {
  background-color: #adb5bd; /* 無効時の色 */
  cursor: not-allowed;
}

.input-area button:hover:not(:disabled) {
  background-color: #0b5ed7; /* ホバー時の色 */
}
</style>