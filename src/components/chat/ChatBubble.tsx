// src/components/ChatBubble.tsx
interface ChatBubbleProps {
    message: string;
    isUser: boolean;
  }
  
  const ChatBubble: React.FC<ChatBubbleProps> = ({ message, isUser }) => {
    const className = isUser ? "user-bubble" : "bot-bubble";
    return (
      <div className={`chat-bubble ${className}`}>
        <p>{message}</p>
      </div>
    );
  };
  
  export default ChatBubble;