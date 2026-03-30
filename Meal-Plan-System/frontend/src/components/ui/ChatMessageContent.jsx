import ReactMarkdown from 'react-markdown';

/**
 * Renders assistant/user text with Markdown (**bold**, lists). Keeps plain text safe (no raw HTML).
 */
export default function ChatMessageContent({ content, variant = 'assistant' }) {
  const text = typeof content === 'string' ? content : '';
  return (
    <div
      className={
        variant === 'user'
          ? 'chat-md chat-md--user'
          : 'chat-md chat-md--assistant'
      }
    >
      <ReactMarkdown
        components={{
          p: ({ children }) => <p className="chat-md-p">{children}</p>,
          strong: ({ children }) => (
            <strong className="font-semibold text-inherit">{children}</strong>
          ),
          em: ({ children }) => <em className="italic opacity-95">{children}</em>,
          ul: ({ children }) => (
            <ul className="chat-md-ul list-disc pl-5">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="chat-md-ol list-decimal pl-5">{children}</ol>
          ),
          li: ({ children }) => (
            <li className="chat-md-li mb-1 pl-0.5">{children}</li>
          ),
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
