export interface User {
  id: string;
  name: string;
  email: string;
  active: boolean;
  role_id: number;
  role: string;
  permissions: string[];
}
export interface Document {
  id: string;
  name: string;
  size: number;
  status: string;
  pages: number;
  error: string | null;
  created_at: string;
}
export interface Citation {
  document_id: string;
  document_name: string;
  page: number;
  excerpt: string;
}
export interface Message {
  id: string;
  role: string;
  content: string;
  created_at: string;
  sources: Citation[];
}
export interface Conversation {
  id: string;
  title: string;
  document_ids: string[];
  created_at: string;
  last_activity_at: string;
  expires_at: string;
  messages?: Message[];
}
export interface Limits {
  max_upload_mb: number;
  max_documents: number;
  daily_questions: number;
  chat_retention_hours?: number;
}
export interface Role {
  id: number;
  name: string;
  permissions: string[];
}
export interface Audit {
  id: number;
  actor_id: string | null;
  action: string;
  target_id: string | null;
  created_at: string;
}
export interface Stats {
  users: number;
  documents: number;
  active_conversations: number;
  questions_today: number;
  processing: {
    id: string;
    status: string;
    pages: number;
    error: string | null;
  }[];
}
