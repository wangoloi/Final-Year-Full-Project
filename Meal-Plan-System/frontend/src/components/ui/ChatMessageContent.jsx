function stripMarkdown(text) {
  return String(text)
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/\*(.*?)\*/g, '$1')
    .replace(/__(.*?)__/g, '$1')
    .replace(/_(.*?)_/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .trim();
}

/**
 * Renders assistant/user text without exposing raw markdown markers.
 */
export default function ChatMessageContent({ content, variant = 'assistant' }) {
  const text = typeof content === 'string' ? stripMarkdown(content) : '';
  const blocks = text.split(/\n\s*\n/).filter(Boolean);

  return (
    <div
      className={
        variant === 'user'
          ? 'chat-md chat-md--user'
          : 'chat-md chat-md--assistant'
      }
    >
      {blocks.map((block, index) => {
        const lines = block.split('\n').filter(Boolean);
        const isBulletList = lines.every((line) => /^[-*]\s+/.test(line.trim()));

        if (isBulletList) {
          return (
            <ul key={index} className="chat-md-ul list-disc pl-5">
              {lines.map((line, lineIndex) => (
                <li key={lineIndex} className="chat-md-li mb-1 pl-0.5">
                  {line.replace(/^[-*]\s+/, '')}
                </li>
              ))}
            </ul>
          );
        }

        return (
          <p key={index} className="chat-md-p">
            {lines.map((line, lineIndex) => (
              <span key={lineIndex}>
                {line}
                {lineIndex < lines.length - 1 ? <br /> : null}
              </span>
            ))}
          </p>
        );
      })}
    </div>
  );
}
