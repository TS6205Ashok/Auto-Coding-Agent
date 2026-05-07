export default function MessageBubble({ message }) {
  const isUser = message.role === "user";
  return (
    <article className={`message-bubble ${isUser ? "user" : "bot"}`}>
      <span>{isUser ? "You" : "Banking Bot"}</span>
      <p>{message.content}</p>
    </article>
  );
}
