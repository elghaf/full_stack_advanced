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
import { format } from 'date-fns';

interface Source {
  document_id: string;
  file_name: string;
  page: number;
  text: string;
  relevance_score: number;
  url?: string;
}

interface ChatMessage {
  id: string;
  content: string;
  sender: 'user' | 'ai';
  timestamp: string;
  sources?: Source[];
}

const SourceDisplay = ({ sources }: { sources: Source[] }) => (
  <div className="mt-4 space-y-3">
    <div className="text-sm font-medium text-gray-500">Sources:</div>
    <div className="space-y-2">
      {sources.map((source, index) => (
        <div key={index} className="bg-gray-50 rounded-lg p-3 border border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-medium text-gray-400">Source {index + 1}</span>
              <span className="text-xs bg-blue-100 text-blue-600 px-2 py-0.5 rounded-full">
                Page {source.page}
              </span>
              <span className="text-xs bg-green-100 text-green-600 px-2 py-0.5 rounded-full">
                Score: {source.relevance_score ? (source.relevance_score * 100).toFixed(0) : 'N/A'}%
              </span>
            </div>
            <div className="text-xs text-gray-400 truncate max-w-[200px]">
              {source.file_name || 'Unnamed Document'}
            </div>
          </div>
          <div className="text-sm text-gray-600 line-clamp-3">
            {source.text?.replace(/\n+\s*/g, ' ').trim()}
          </div>
          {source.url && (
            <div className="mt-1 text-xs text-blue-500">
              <a href={source.url} target="_blank" rel="noopener noreferrer" className="underline">
                More information
              </a>
            </div>
          )}
        </div>
      ))}
    </div>
  </div>
);

const formatResponse = (response: string) => {
  const [servicesPart, sourcesPart] = response.split('Sources:');
  
  const services = servicesPart.trim().split('\n\n').map(service => {
    const [title, ...descriptionLines] = service.split('\n');
    const description = descriptionLines.join(' ').trim();
    return {
      title: title.replace(/\*\*/g, '').trim(),
      description: description
    };
  }).filter(service => service.title);

  const sources = sourcesPart ? sourcesPart.trim().split('\n').filter(line => line.startsWith('1.')) : [];

  return { services, sources };
};

const ChatInterface = () => {
  const { activeDocument, documents } = useDocuments();
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      content: "Hello! I'm here to help you analyze your documents. You can upload files and ask me questions about their content.",
      sender: 'ai',
      timestamp: new Date().toISOString(),
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
      timestamp: new Date().toISOString(),
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

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response:', errorText);
        throw new Error('Failed to get response from backend');
      }

      const data = await response.json();
      const { services, sources } = formatResponse(data.content);
      
      const botMessage: ChatMessage = {
        id: data.id,
        content: services.map(service => `**${service.title}**: ${service.description}`).join('\n\n'),
        sender: 'ai',
        timestamp: new Date().toISOString(),
        sources: data.sources // Assuming sources is already in the correct format
      };

      setMessages(prev => [...prev, botMessage]);
      console.groupEnd(); // API Response Details
      
    } catch (error) {
      console.group('❌ Error Details');
      if (error instanceof Error) {
        console.error({
          type: error.name,
          message: error.message,
          timestamp: new Date().toLocaleString()
        });
      } else {
        console.error({
          type: 'Unknown Error',
          message: typeof error === 'string' ? error : 'An unexpected error occurred',
          timestamp: new Date().toLocaleString()
        });
      }
      console.groupEnd();
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-3/5 flex flex-col">
      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="space-y-6">
          {messages.map((message, index) => (
            <div key={index} className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] ${message.sender === 'user' ? 'bg-custom text-white' : 'bg-gray-100'} rounded-lg p-4`}>
                <div className="text-sm">{message.content}</div>
                {message.sender === 'ai' && message.sources && (
                  <SourceDisplay sources={message.sources} />
                )}
                {message.sender === 'ai' && message.timestamp && (
                  <div className="mt-2 text-xs text-gray-400">
                    {format(new Date(message.timestamp), 'MMM d, yyyy HH:mm:ss')}
                  </div>
                )}
              </div>
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
