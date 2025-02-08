'use client'

import { useState } from 'react';
import { useDocuments } from '@/context/DocumentContext';
import { 
  FiSend, 
  FiPaperclip, 
  FiSearch,
  FiList, 
  FiFileText,
  FiZap,
  FiMessageSquare,
  FiUser,
  FiCpu
} from 'react-icons/fi';

interface Source {
  document_id: string;
  page: number;
  text: string;
}

interface ChatMessage {
  id: string;
  content: string;
  sender: 'user' | 'ai';
  timestamp: Date;
  sources?: Source[];
}

const ChatInterface = () => {
  const { activeDocument, documents } = useDocuments();
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
      console.group('🌐 Chat API Interaction');
      
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
      
      // Log API Response
      console.group('📥 API Response Details');
      console.table({
        status: response.status,
        messageId: data.id,
        timestamp: new Date().toLocaleString(),
        contentLength: data.content.length
      });

      // Log Sources
      if (data.sources && data.sources.length > 0) {
        console.group('📚 Source Documents');
        data.sources.forEach((source, index) => {
          console.log(`Source ${index + 1}:`, {
            documentId: source.document_id,
            fileName: source.file_name,
            page: source.page,
            relevanceScore: source.relevance_score,
            text: source.text.substring(0, 100) + (source.text.length > 100 ? '...' : '')
          });
        });
        console.groupEnd();
      }

      // Log AI Response
      console.group('🤖 AI Response');
      console.log({
        content: data.content,
        sourceCount: data.sources?.length || 0,
        timestamp: new Date().toLocaleString()
      });
      console.groupEnd();
      
      const botMessage: ChatMessage = {
        id: data.id,
        content: data.content,
        sender: 'ai',
        timestamp: new Date(),
        sources: data.sources
      };

      setMessages(prev => [...prev, botMessage]);
      console.groupEnd(); // API Response Details
      console.groupEnd(); // Chat API Interaction
      
    } catch (error) {
      console.group('❌ Error Details');
      console.error({
        type: error.name,
        message: error.message,
        timestamp: new Date().toLocaleString()
      });
      console.groupEnd();
    } finally {
      setIsLoading(false);
    }
  };


  return (
    <div className="w-3/5 flex flex-col">
      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="space-y-6">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {message.sender === 'ai' && (
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center mr-3">
                  <FiCpu className="w-5 h-5 text-blue-600" />
                </div>
              )}
              <div
                className={`max-w-[80%] rounded-lg p-3 ${
                  message.sender === 'user'
                    ? 'bg-custom text-white'
                    : 'bg-gray-100 text-gray-900'
                }`}
              >
                <p>{message.content}</p>
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
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center ml-3">
                  <FiUser className="w-5 h-5 text-gray-600" />
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
