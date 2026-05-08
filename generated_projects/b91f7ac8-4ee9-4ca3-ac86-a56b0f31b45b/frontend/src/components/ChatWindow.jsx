import { useState } from "react";
import MessageBubble from "./MessageBubble";
import { sendChatMessage } from "../services/chatbotApi";

export default function ChatWindow({ messages, onMessage }) {
  const [message, setMessage] = useState("");
  const [customerId, setCustomerId] = useState("CUST1001");
  const [otp, setOtp] = useState("");
  const [isSending, setIsSending] = useState(false);

  async function handleSend(event) {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed) return;
    onMessage({ role: "user", content: trimmed });
    setMessage("");
    setIsSending(true);
    try {
      const response = await sendChatMessage({ message: trimmed, customer_id: customerId, otp });
      onMessage({ role: "bot", content: response.reply });
    } catch (error) {
      onMessage({ role: "bot", content: error.message || "Unable to reach banking assistant." });
    } finally {
      setIsSending(false);
    }
  }

  return (
    <section className="chat-card">
      <div className="chat-toolbar">
        <input value={customerId} onChange={(event) => setCustomerId(event.target.value)} placeholder="Customer ID" />
        <input value={otp} onChange={(event) => setOtp(event.target.value)} placeholder="OTP" />
      </div>
      <div className="message-list">
        {messages.map((item, index) => <MessageBubble key={`${item.role}-${index}`} message={item} />)}
      </div>
      <form className="chat-form" onSubmit={handleSend}>
        <input value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Ask a banking question..." />
        <button type="submit" disabled={isSending}>{isSending ? "Sending..." : "Send"}</button>
      </form>
    </section>
  );
}
