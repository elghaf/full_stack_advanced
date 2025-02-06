'use client'

import { useState } from 'react';
import { useDocuments } from '@/context/DocumentContext';
import { 
  FiSend, 
  FiMessageSquare,
  FiUser,
  FiZap,
  FiList,
  FiSearch,
  FiExternalLink
} from 'react-icons/fi';
import { analyzeDocument, getDocumentContent, type DocumentAnalysis } from '@/services/documentService';

interface Source {
  document_id: string;
  page: number;
  start_line?: number;
  end_line?: number;
  preview?: string;
  relevance_score: number;
}

interface ChatMessage {
  id: string;
  content: string;
  sender: 'user' | 'ai';
  timestamp: Date;
  sources?: Source[];
}

const ChatInterface = () => {
  const { uploadedFiles, activeDocument } = useDocuments();
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      content: "Hello! I'm here to help you analyze your documents. You can ask me questions about their content and I'll provide answers with relevant sources.",
      sender: 'ai',
      timestamp: new Date(),
    },
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedSource, setSelectedSource] = useState<Source | null>(null);
  const [documentAnalyses, setDocumentAnalyses] = useState<Record<string, DocumentAnalysis>>({});

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
        id: crypto.randomUUID(),
        content: data.content,
        sender: 'ai',
        timestamp: new Date(),
        sources: data.sources?.map((source: any) => ({
          ...source,
          confidence_score: Math.round(source.confidence_score * 100) / 100
        }))
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage: ChatMessage = {
        id: crypto.randomUUID(),
        content: "I apologize, but I encountered an error processing your request. Please try again.",
        sender: 'ai',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const analyzeAllDocuments = async () => {
    setIsLoading(true);
    try {
      const analyses = await Promise.all(
        uploadedFiles.map(async (doc) => {
          const analysis = await analyzeDocument(doc.id);
          return [doc.id, analysis] as const;
        })
      );
      
      setDocumentAnalyses(Object.fromEntries(analyses));
      
      const summaryMessage: ChatMessage = {
        id: crypto.randomUUID(),
        content: "Here's a summary of your documents:",
        sender: 'ai',
        timestamp: new Date(),
        sources: uploadedFiles.map(doc => ({
          document_id: doc.id,
          page: 1,
          text: documentAnalyses[doc.id]?.summary || '',
          snippet_text: `${doc.name}: ${documentAnalyses[doc.id]?.summary.substring(0, 100)}...`,
          confidence_score: 1
        }))
      };
      
      setMessages(prev => [...prev, summaryMessage]);
    } catch (error) {
      console.error('Error analyzing documents:', error);
      const errorMessage: ChatMessage = {
        id: crypto.randomUUID(),
        content: "I apologize, but I encountered an error analyzing your documents. Please try again.",
        sender: 'ai',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickAction = async (action: 'summarize' | 'keyPoints' | 'search') => {
    try {
      setIsLoading(true);
      let message = '';
      
      switch (action) {
        case 'summarize':
          message = 'Please provide a comprehensive summary of all the documents';
          break;
        case 'keyPoints':
          message = 'What are the key points from all the documents?';
          break;
        case 'search':
          // Handle search separately if needed
          break;
      }

      if (message) {
        const response = await fetch('/api/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message,
            chat_history: messages
          }),
        });

        if (!response.ok) {
          throw new Error('Failed to get response');
        }

        const data = await response.json();
        
        setMessages(prev => [...prev, {
          id: data.id,
          content: data.content,
          sender: 'ai',
          timestamp: new Date(data.timestamp),
          sources: data.sources
        }]);
      }
    } catch (error) {
      console.error('Error:', error);
      // Handle error appropriately
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-full">
      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        {/* Messages */}
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
                  <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  {message.sources && message.sources.length > 0 && (
                    <div className="mt-3 space-y-2">
                      <p className="text-xs font-medium text-gray-500">Sources:</p>
                      {message.sources.map((source, index) => (
                        <button
                          key={index}
                          onClick={() => setSelectedSource(source)}
                          className="block w-full text-left p-2 bg-white rounded border border-gray-200 text-xs hover:bg-gray-50 transition-colors"
                        >
                          <div className="flex justify-between items-center">
                            <span className="font-medium text-gray-700">Page {source.page}</span>
                            <span className="text-gray-500">
                              Score: {source.confidence_score}
                              <FiExternalLink className="inline ml-1" />
                            </span>
                          </div>
                          <p className="mt-1 text-gray-600 line-clamp-2">{source.snippet_text}</p>
                        </button>
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
            {isLoading && (
              <div className="flex items-center space-x-2 text-gray-500">
                <FiMessageSquare className="h-5 w-5 animate-pulse" />
                <span>Thinking...</span>
              </div>
            )}
          </div>
        </div>

        {/* Input area */}
        <div className="border-t border-gray-200 px-6 py-4">
          <form onSubmit={handleSubmit} className="flex flex-col space-y-3">
            <div className="flex space-x-3">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                className="flex-1 rounded-lg border border-gray-300 px-4 py-2 focus:outline-none focus:ring-2 focus:ring-custom focus:border-transparent"
                placeholder="Ask a question about your documents..."
                disabled={isLoading}
              />
              <button
                type="submit"
                disabled={isLoading || !inputMessage.trim()}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-lg text-white bg-custom hover:bg-custom/90 disabled:opacity-50"
              >
                <FiSend className="w-4 h-4 mr-2" />
                {isLoading ? 'Sending...' : 'Send'}
              </button>
            </div>
            <div className="flex space-x-4">
              <button 
                type="button" 
                onClick={() => handleQuickAction('summarize')}
                className="text-sm text-gray-500 hover:text-custom flex items-center gap-1"
              >
                <FiZap className="w-4 h-4" />
                Summarize
              </button>
              <button 
                type="button"
                onClick={() => handleQuickAction('keyPoints')} 
                className="text-sm text-gray-500 hover:text-custom flex items-center gap-1"
              >
                <FiList className="w-4 h-4" />
                Key Points
              </button>
              <button 
                type="button"
                onClick={() => handleQuickAction('search')}
                className="text-sm text-gray-500 hover:text-custom flex items-center gap-1"
              >
                <FiSearch className="w-4 h-4" />
                Search
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Source preview sidebar */}
      {selectedSource && (
        <div className="w-1/3 border-l border-gray-200 p-4 overflow-y-auto">
          <div className="sticky top-0 bg-white pb-4">
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-medium">Source Preview</h3>
              <button
                onClick={() => setSelectedSource(null)}
                className="text-gray-500 hover:text-gray-700"
              >
                ×
              </button>
            </div>
            <div className="text-sm text-gray-500 mb-4">
              <p>Page {selectedSource.page}</p>
              <p>Confidence Score: {selectedSource.confidence_score}</p>
            </div>
          </div>
          {selectedSource.preview ? (
            <img
              src={selectedSource.preview}
              alt={`Page ${selectedSource.page}`}
              className="w-full rounded-lg shadow-lg"
            />
          ) : (
            <div className="bg-gray-100 rounded-lg p-4">
              <p className="text-gray-600 text-sm">{selectedSource.text}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ChatInterface;
