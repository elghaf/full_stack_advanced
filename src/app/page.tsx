import {FileUpload} from "@/components/documents/FileUpload";
import DocumentPreview from "@/components/documents/DocumentPreview";
import ChatInterface from "@/components/chat_features/ChatInterface";

export default function Home() {
  return (
    <div className="flex-1 flex overflow-hidden bg-white">
      <div className="w-2/5 border-r border-gray-200 flex flex-col relative">
        <FileUpload />
        <DocumentPreview />
      </div>
      <ChatInterface />
    </div>
  );
}

const RecentDocuments = () => (
  <div className="flex-1 overflow-y-auto p-6">
    <div className="border-t border-gray-200 p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-900">Source Preview</h3>
        <button className="text-xs text-gray-500 hover:text-custom">View all</button>
      </div>
      <div className="mt-3 flex space-x-2 overflow-x-auto pb-2">
        {[1, 2, 3].map((page) => (
          <div key={page} className="flex-none w-32">
            <div className="aspect-[3/4] bg-gray-100 rounded-lg overflow-hidden">
              <img
                src="https://ai-public.creatie.ai/gen_page/pdf_preview.png"
                alt="Document preview"
                className="w-full h-full object-cover"
              />
            </div>
            <p className="mt-1 text-xs text-gray-500 truncate">Page {page}</p>
          </div>
        ))}
      </div>
    </div>
    <h3 className="text-lg font-medium text-gray-900">Recent Documents</h3>
    <div className="mt-6 space-y-4">
      {[
        { name: "Project_Report_2024.pdf", type: "pdf", size: "2.4 MB", time: "2 hours ago" },
        { name: "Meeting_Minutes.docx", type: "word", size: "1.1 MB", time: "yesterday" },
      ].map((doc) => (
        <div key={doc.name} className="bg-gray-50 p-4 rounded-lg hover:bg-gray-100 transition-colors">
          <div className="flex items-center">
            <i className={`fas fa-file-${doc.type} text-${doc.type === "pdf" ? "red" : "blue"}-500 text-xl`}></i>
            <div className="ml-3 flex-1">
              <p className="text-sm font-medium text-gray-900">{doc.name}</p>
              <p className="text-xs text-gray-500">{doc.size} · Uploaded {doc.time}</p>
            </div>
            <button className="text-gray-400 hover:text-gray-500">
              <i className="fas fa-ellipsis-v"></i>
            </button>
          </div>
        </div>
      ))}
    </div>
  </div>
);