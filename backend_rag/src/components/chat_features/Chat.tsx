'use client';

import { useState } from 'react';
import { sendMessage } from '@/services/chatService';
import { useDocuments } from '@/context/DocumentContext';
import { FiSend } from 'react-icons/fi';

interface Message {
  id: string;
  text: string;
  isUser: boolean;
  sources?: {
    document_id: string;
    page: number;
    text: string;
  }[];
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { activeDocument } = useDocuments();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: input,
      isUser: true
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await sendMessage(
        input, 
        activeDocument?.id // Optional: scope to active document
      );

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: response.answer,
        isUser: false,
        sources: response.sources
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      // Add error message to chat
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: 'Sorry, there was an error processing your message.',
        isUser: false
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.isUser ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg p-3 ${
                message.isUser
                  ? 'bg-custom text-white'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              <p>{message.text}</p>
              {message.sources && message.sources.length > 0 && (
                <div className="mt-2 text-sm">
                  <p className="font-medium">Sources:</p>
                  {message.sources.map((source, index) => (
                    <div key={index} className="mt-1 text-xs">
                      <p>Page {source.page}</p>
                      <p className="italic">{source.text}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg p-3">
              <p>Thinking...</p>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t">
        <div className="flex space-x-4">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about your documents..."
            className="flex-1 border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-custom"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading}
            className="bg-custom text-white px-4 py-2 rounded-lg hover:bg-custom/90 disabled:opacity-50"
          >
            <FiSend />
          </button>
        </div>
      </form>
    </div>
  );
} 