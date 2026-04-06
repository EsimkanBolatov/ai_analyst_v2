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
