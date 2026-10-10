import React from 'react';

export const LoadingSkeleton: React.FC<{ rows?: number }> = ({ rows = 4 }) => {
  return (
    <div style={{ padding: '1rem' }}>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          style={{
            height: '40px',
            backgroundColor: '#E2E8F0',
            borderRadius: '6px',
            marginBottom: '0.75rem',
            animation: 'pulse 1.5s infinite ease-in-out',
          }}
        />
      ))}
      <style>{`
        @keyframes pulse {
          0% { opacity: 0.6; }
          50% { opacity: 1; }
          100% { opacity: 0.6; }
        }
      `}</style>
    </div>
  );
};
