import { FileX } from 'lucide-react';

export function BinaryFile() {
  return (
    <div className="flex flex-col items-center justify-center h-full p-8 bg-gray-900/50">
      <div className="w-16 h-16 rounded-full bg-gray-800/70 flex items-center justify-center mb-6 shadow-lg border border-gray-700/50">
        {/* Using FileTerminal icon from lucide-react */}
        <FileX className="h-8 w-8 text-gray-400" />
      </div>
      <h3 className="text-xl font-semibold mb-3 text-gray-200">
        Cannot Display File
      </h3>
      <p className="text-sm text-gray-400 text-center max-w-md">
        The content of this file cannot be displayed as text. It might be a
        binary file or use an unsupported encoding.
      </p>
    </div>
  );
}
