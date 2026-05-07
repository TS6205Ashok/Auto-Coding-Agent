import { useState } from "react";
import ChatWindow from "../components/ChatWindow";

const initialMessages = [
  {
    role: "bot",
    content: "Welcome to The Proposed System Is. Ask about balance, transactions, card blocking, loan EMI, complaints, branches, or ATMs."
  }
];

export default function ChatbotPage() {
  const [messages, setMessages] = useState(initialMessages);

  function addMessage(message) {
    setMessages((current) => [...current, message]);
  }

  return (
    <main className="banking-page">
      <section className="banking-hero">
        <p className="eyebrow">Banking Chatbot / IVR</p>
        <h1>The Proposed System Is</h1>
        <p>Demo customer: CUST1001. OTP: 123456.</p>
      </section>
      <ChatWindow messages={messages} onMessage={addMessage} />
    </main>
  );
}
