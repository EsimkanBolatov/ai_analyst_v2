export type Role = {
  id: number;
  name: string;
  description?: string | null;
};

export type User = {
  id: number;
  email: string;
  created_at: string;
  role: Role;
};

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
};

export type AdminSummary = {
  users: number;
  transactions: number;
  moderation_items: number;
};

export type Budget = {
  id: number;
  month: string;
  monthly_limit: number;
  current_balance: number;
  spent_amount: number;
};

export type Transaction = {
  id: number;
  occurred_at: string;
  amount: number;
  category?: string | null;
  description?: string | null;
  source_filename?: string | null;
  created_at: string;
};

export type AssistantMessage = {
  id: number;
  role: "user" | "assistant" | string;
  content: string;
  created_at: string;
};

export type AssistantOverview = {
  budget: Budget | null;
  current_month_spent: number;
  recent_transactions: Transaction[];
  messages: AssistantMessage[];
};

export type AssistantChatResponse = {
  assistant_message: AssistantMessage;
  captured_transaction: Transaction | null;
  budget: Budget | null;
  current_month_spent: number;
  recent_transactions: Transaction[];
};

export type TransactionImportResponse = {
  stored_filename: string | null;
  imported_count: number;
  skipped_count: number;
  warnings: string[];
  detected_columns: Record<string, string | null>;
  budget: Budget | null;
  current_month_spent: number;
  recent_transactions: Transaction[];
};

export type FraudDataType = "phone" | "url" | "email" | "text";
export type ModerationStatus = "pending" | "approved" | "rejected";
export type ModerationFilterStatus = "all" | "pending" | "approved" | "rejected";

export type FraudQueueUser = {
  id: number;
  email: string;
};

export type BlacklistEntry = {
  id: number;
  data_type: string;
  value: string;
  category?: string | null;
  source_report_id?: number | null;
  approved_by_user_id?: number | null;
  created_at: string;
};

export type ModerationItem = {
  id: number;
  data_type: FraudDataType | string;
  value: string;
  user_comment?: string | null;
  ai_category?: string | null;
  ai_confidence?: number | null;
  ai_summary?: string | null;
  status: ModerationStatus | string;
  moderator_comment?: string | null;
  resolved_by_user_id?: number | null;
  resolved_at?: string | null;
  created_at: string;
  updated_at: string;
  reporter: FraudQueueUser;
  resolver?: FraudQueueUser | null;
  blacklist_entry?: BlacklistEntry | null;
};

export type FraudReportResponse = {
  item: ModerationItem;
  already_blacklisted: boolean;
};

export type ModerationQueueResponse = {
  items: ModerationItem[];
  total_count: number;
  pending_count: number;
  approved_count: number;
  rejected_count: number;
  blacklist_count: number;
};

export type ModerationResolveResponse = {
  item: ModerationItem;
  blacklist_entry?: BlacklistEntry | null;
};
