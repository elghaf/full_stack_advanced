'use client'

import { useState } from 'react';
import { useDocuments } from '@/context/DocumentContext';
import { ChatMessage } from '@/types/file';
import { 
  FiSend, 
  FiPaperclip, 
  FiSearch, 
  FiList, 
  FiFileText,
  FiZap,
  FiMessageSquare,
  FiUser
} from 'react-icons/fi';

interface Source {
  document_id: string;
  page: number;
  text: string;
}

const ChatInterface = () => {
  const { activeDocument } = useDocuments();
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      content: "Hello! I'm here to help you analyze your documents. You can upload files and ask me questions about their content.",
      sender: 'ai',
      timestamp: new Date(),
    },
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      content: inputMessage,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: inputMessage,
          document_id: activeDocument?.id,
          chat_history: messages.map(msg => ({
            sender: msg.sender,
            content: msg.content
          }))
        }),
      });

      const data = await response.json();
      
      const botMessage: ChatMessage = {
        id: data.id,
        content: data.content,
        sender: 'ai',
        timestamp: new Date(),
        sources: data.sources
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-3/5 flex flex-col">
      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="space-y-6">
          {messages.map((message) => (
            <div key={message.id} className={`flex items-start ${message.sender === 'user' ? 'justify-end' : ''}`}>
              {message.sender === 'ai' && (
                <div className="flex-shrink-0">
                  <FiMessageSquare className="h-10 w-10 text-gray-500" />
                </div>
              )}
              <div className={`${message.sender === 'user' ? 'mr-3' : 'ml-3'} ${
                message.sender === 'user' ? 'bg-custom text-white' : 'bg-gray-100'
              } rounded-lg px-4 py-3 max-w-3xl`}>
                <p className="text-sm">{message.content}</p>
                {message.sources && (
                  <div className="mt-2 space-y-2">
                    {message.sources.map((source, index) => (
                      <div 
                        key={index}
                        className="p-2 bg-gray-50 rounded border border-gray-200 text-xs"
                      >
                        <div className="font-medium text-gray-700">Source {index + 1}:</div>
                        <div className="text-gray-600">{source.text}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              {message.sender === 'user' && (
                <div className="flex-shrink-0">
                  <FiUser className="h-10 w-10 text-gray-500" />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
      <div className="border-t border-gray-200 px-6 py-4">
        <form onSubmit={handleSubmit} className="flex space-x-3">
          <div className="flex-1">
            <div className="relative rounded-lg shadow-sm">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                className="block w-full rounded-lg border-gray-300 pl-3 pr-10 py-3 focus:outline-none focus:ring-1 focus:ring-custom focus:border-custom sm:text-sm"
                placeholder="Ask a question about your documents..."
              />
              <div className="absolute inset-y-0 right-0 flex items-center pr-3">
                <button type="button" className="text-gray-400 hover:text-gray-500">
                  <FiPaperclip className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
          <button
            type="submit"
            disabled={isLoading || !inputMessage.trim()}
            className="!rounded-button inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-custom hover:bg-custom/90 disabled:opacity-50"
          >
            <FiSend className="w-4 h-4 mr-2" />
            {isLoading ? 'Sending...' : 'Send'}
          </button>
        </form>
        <div className="mt-3 flex space-x-4">
          <button className="text-sm text-gray-500 hover:text-custom flex items-center gap-1">
            <FiZap className="w-4 h-4" />
            Summarize document
          </button>
          <button className="text-sm text-gray-500 hover:text-custom flex items-center gap-1">
            <FiList className="w-4 h-4" />
            Extract key points
          </button>
          <button className="text-sm text-gray-500 hover:text-custom flex items-center gap-1">
            <FiSearch className="w-4 h-4" />
            Find specific information
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
