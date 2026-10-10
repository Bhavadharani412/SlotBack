import React from 'react';
import { Inbox, AlertCircle } from 'lucide-react';

interface EmptyStateProps {
  title: string;
  description: string;
  action?: React.ReactNode;
  isError?: boolean;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  action,
  isError = false,
}) => {
  return (
    <div
      style={{
        padding: '3rem 1.5rem',
        textAlign: 'center',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          backgroundColor: isError ? 'var(--danger-bg)' : 'var(--primary-light)',
          color: isError ? 'var(--danger)' : 'var(--primary)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: '1rem',
        }}
      >
        {isError ? <AlertCircle size={28} /> : <Inbox size={28} />}
      </div>
      <h3 style={{ marginBottom: '0.25rem' }}>{title}</h3>
      <p style={{ maxWidth: '400px', marginBottom: action ? '1.25rem' : '0' }}>{description}</p>
      {action && <div>{action}</div>}
    </div>
  );
};
