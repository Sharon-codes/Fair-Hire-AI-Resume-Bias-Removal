import React, { useState, useRef } from 'react';

export default function App() {
  const [report, setReport] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const fileInputRef = useRef(null);

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) {
      setMessage('Please select a DOCX file.');
      return;
    }
    if (file.type !== 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') {
      setMessage('Please upload a valid .docx file.');
      return;
    }
    setLoading(true);
    setMessage('Uploading and processing resume with LLaMA 3.1 backend...');
    setReport('');
    try {
      const reader = new FileReader();
      reader.onload = async (e) => {
        const arrayBuffer = e.target.result;
        const base64Content = btoa(new Uint8Array(arrayBuffer).reduce((data, byte) => data + String.fromCharCode(byte), ''));
        const payload = {
          fileContent: base64Content,
          fileName: file.name
        };
        const response = await fetch(`${BACKEND_URL}/process_resume`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const result = await response.json();
        if (response.ok) {
          setReport(result.report);
          setMessage('Report generated successfully by LLaMA 3.1!');
        } else {
          console.error('Backend error:', result.error);
          setMessage(`Error: ${result.error || 'Failed to process resume.'}`);
          setReport('');
        }
      };
      reader.readAsArrayBuffer(file);
    } catch (error) {
      console.error('Network or unexpected error:', error);
      setMessage(`Network error or unexpected issue: ${error.message}. Please ensure backend is running.`);
      setReport('');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setReport('');
    setLoading(false);
    setMessage('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-gradient-to-br from-gray-100 to-gray-200 font-sans">
      {/* Main Container */}
      <div className="w-full max-w-md p-6 sm:p-8">
        <div className="bg-white shadow-lg rounded-lg p-6 sm:p-8 border border-gray-200">
          {/* Header */}
          <div className="text-center mb-6">
            <h1 className="text-3xl font-bold text-gray-900">FairHire AI</h1>
            <p className="text-md text-gray-600">Resume Screener</p>
          </div>
          {/* Instructions */}
          <p className="text-gray-700 mb-4 text-center">
            Upload a <span className="font-semibold text-blue-600">.docx</span> resume for a bias-free assessment.
          </p>
          <p className="text-sm text-gray-500 mb-6 text-center">
            Powered by <span className="font-semibold text-blue-600">LLaMA 3.1</span> for advanced bias removal and extraction.
          </p>
          {/* Upload Section */}
          <div className="mb-6 flex flex-col items-center">
            <label htmlFor="file-upload" className="cursor-pointer w-full max-w-xs">
              <div className="flex items-center justify-center px-4 py-3 border-2 border-dashed border-gray-300 rounded-lg bg-gray-50 hover:bg-gray-100 transition-colors">
                <svg className="w-6 h-6 text-gray-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
                <span className="text-gray-700 font-medium">Choose File</span>
              </div>
              <input
                id="file-upload"
                type="file"
                ref={fileInputRef}
                onChange={handleFileUpload}
                accept=".docx"
                className="hidden"
              />
            </label>
            <p className="text-sm text-gray-500 mt-2">No file chosen</p>
          </div>
          {/* Status Message */}
          {loading && (
            <div className="flex items-center justify-center mb-4 text-blue-600">
              <svg className="animate-spin h-5 w-5 mr-2 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span className="text-sm">{message}</span>
            </div>
          )}
          {message && !loading && (
            <div className={`text-center mb-4 text-sm ${report ? 'text-green-600' : 'text-red-600'}`}>
              {message}
            </div>
          )}
          {/* Report Section */}
          {report && (
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 mb-4">
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Candidate Report for HR</h2>
              <pre className="text-gray-700 text-sm whitespace-pre-wrap bg-white p-3 rounded shadow-inner overflow-x-auto">
                {report}
              </pre>
              <button
                onClick={handleReset}
                className="mt-4 w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition-colors"
              >
                Reset
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}