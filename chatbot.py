# chatbot.py
import streamlit as st
import streamlit.components.v1 as components


def render_chatbot():
    # Use a large iframe that injects into window.parent (the real Streamlit page)
    components.html("""
    <!DOCTYPE html>
    <html>
    <body>
    <script>
      // Inject into the PARENT window (actual Streamlit page), not the iframe
      const doc = window.parent.document;

      // Avoid duplicate injection on Streamlit reruns
      if (doc.getElementById('deepfake-chat-btn')) {
        console.log('Chatbot already injected.');
      } else {

        // --- Styles ---
        const style = doc.createElement('style');
        style.innerHTML = `
          #deepfake-chat-btn {
            position: fixed; bottom: 28px; right: 28px;
            width: 56px; height: 56px; border-radius: 50%;
            background: #6c63ff; color: white; font-size: 24px;
            border: none; cursor: pointer;
            box-shadow: 0 4px 16px rgba(108,99,255,0.5);
            z-index: 99999; transition: transform 0.2s;
          }
          #deepfake-chat-btn:hover { transform: scale(1.1); }

          #deepfake-chat-popup {
            display: none; position: fixed;
            bottom: 96px; right: 28px;
            width: 320px; height: 430px;
            background: white; border-radius: 16px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.18);
            z-index: 99999; flex-direction: column; overflow: hidden;
            font-family: sans-serif;
          }
          #deepfake-chat-header {
            background: #6c63ff; color: white;
            padding: 14px 16px; font-weight: bold; font-size: 15px;
            display: flex; justify-content: space-between; align-items: center;
          }
          #deepfake-chat-close {
            background: none; border: none; color: white;
            font-size: 18px; cursor: pointer; line-height: 1;
          }
          #deepfake-chat-messages {
            flex: 1; overflow-y: auto; padding: 12px; font-size: 14px;
          }
          #deepfake-chat-thinking {
            padding: 4px 14px; font-size: 12px;
            color: #999; display: none;
          }
          .dchat-msg { margin: 8px 0; }
          .dchat-msg.user { text-align: right; }
          .dchat-msg.user span {
            background: #6c63ff; color: white; padding: 7px 13px;
            border-radius: 16px 16px 0 16px;
            display: inline-block; max-width: 80%;
          }
          .dchat-msg.bot span {
            background: #f0f0f0; color: #222; padding: 7px 13px;
            border-radius: 16px 16px 16px 0;
            display: inline-block; max-width: 80%;
          }
          #deepfake-chat-input-row {
            display: flex; border-top: 1px solid #eee; padding: 8px; gap: 6px;
          }
          #deepfake-chat-input {
            flex: 1; border: 1px solid #ddd; border-radius: 20px;
            padding: 7px 13px; font-size: 14px; outline: none;
          }
          #deepfake-chat-input:focus { border-color: #6c63ff; }
          #deepfake-chat-send {
            background: #6c63ff; color: white; border: none;
            border-radius: 50%; width: 36px; height: 36px;
            cursor: pointer; font-size: 16px; flex-shrink: 0;
          }
        `;
        doc.head.appendChild(style);

        // --- Button ---
        const btn = doc.createElement('button');
        btn.id = 'deepfake-chat-btn';
        btn.innerHTML = '💬';
        doc.body.appendChild(btn);

        // --- Popup ---
        const popup = doc.createElement('div');
        popup.id = 'deepfake-chat-popup';
        popup.innerHTML = `
          <div id="deepfake-chat-header">
            💬 Deepfake Assistant
            <button id="deepfake-chat-close">✕</button>
          </div>
          <div id="deepfake-chat-messages"></div>
          <div id="deepfake-chat-thinking">Assistant is thinking...</div>
          <div id="deepfake-chat-input-row">
            <input id="deepfake-chat-input" type="text" placeholder="Ask about deepfakes..." />
            <button id="deepfake-chat-send">➤</button>
          </div>
        `;
        doc.body.appendChild(popup);

        // --- Logic ---
        const msgsDiv = doc.getElementById('deepfake-chat-messages');

        btn.addEventListener('click', () => {
          popup.style.display = popup.style.display === 'flex' ? 'none' : 'flex';
          msgsDiv.scrollTop = msgsDiv.scrollHeight;
        });

        doc.getElementById('deepfake-chat-close').addEventListener('click', () => {
          popup.style.display = 'none';
        });

        const input = doc.getElementById('deepfake-chat-input');
        input.addEventListener('keydown', e => { if (e.key === 'Enter') sendMessage(); });
        doc.getElementById('deepfake-chat-send').addEventListener('click', sendMessage);

        function appendMessage(role, text) {
          const div = doc.createElement('div');
          div.className = 'dchat-msg ' + (role === 'user' ? 'user' : 'bot');
          div.innerHTML = '<span>' + text.replace(/</g, '&lt;') + '</span>';
          msgsDiv.appendChild(div);
          msgsDiv.scrollTop = msgsDiv.scrollHeight;
        }

        async function sendMessage() {
          const text = input.value.trim();
          if (!text) return;
          appendMessage('user', text);
          input.value = '';
          input.disabled = true;
          doc.getElementById('deepfake-chat-thinking').style.display = 'block';

          try {
            const res = await fetch('http://localhost:8000/chat', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ message: text })
            });
            const data = await res.json();
            appendMessage('bot', data.reply);
          } catch (e) {
            appendMessage('bot', '⚠️ Cannot reach assistant. Is chat_server.py running?');
          } finally {
            doc.getElementById('deepfake-chat-thinking').style.display = 'none';
            input.disabled = false;
            input.focus();
          }
        }
      }
    </script>
    </body>
    </html>
    """, height=0)