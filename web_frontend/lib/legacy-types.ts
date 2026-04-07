export type LegacyModelType = "IsolationForest" | "LocalOutlierFactor" | "OneClassSVM";

export type LegacyUploadResponse = {
  status: string;
  filename?: string;
  message?: string;
};

export type LegacyProfileResponse = {
  status: string;
  report_filename: string;
};

export type LegacyDistributionStats = {
  min_val?: number | null;
  p25?: number | null;
  median?: number | null;
  p75?: number | null;
  max_val?: number | null;
  mean_val?: number | null;
  count?: number | null;
};

export type LegacyAnomaly = {
  row_index: number;
  reason: string;
  data?: Record<string, unknown>;
  plot_data?: {
    transaction_amount_kzt?: number | null;
    transaction_hour?: number | null;
    mcc_category?: string | null;
  } | null;
};

export type LegacyAiAnalysis = {
  main_findings: string;
  anomalies: LegacyAnomaly[];
  recommendations: string;
  feature_engineering_ideas: string[];
  amount_distribution_stats?: LegacyDistributionStats | null;
};

export type LegacyChatMessage = {
  role: "user" | "assistant" | string;
  content: string;
};

export type LegacyModelListResponse = {
  models: string[];
};

export type LegacyModelConfig = {
  model_type: string;
  algorithm_class?: string;
  numerical_features: string[];
  categorical_features: string[];
  date_features: string[];
  categorical_values?: Record<string, string[]>;
  generated_date_features?: string[];
  generated_eng_features?: string[];
  feature_engineering_config?: Record<string, unknown>;
};

export type LegacyTrainPayload = {
  filename: string;
  model_name: string;
  model_type: LegacyModelType;
  numerical_features: string[];
  categorical_features: string[];
  date_features: string[];
  enable_feature_engineering: boolean;
  card_id_column?: string | null;
  timestamp_column?: string | null;
  amount_column?: string | null;
};

export type LegacyScoreFileResponse = {
  scores: number[];
};

export type LegacyPredictionResponse = {
  model_type: string;
  anomaly_score?: number;
  is_anomaly_predicted?: boolean;
  prediction?: unknown;
  probabilities?: Record<string, number>;
};

export type LegacyFraudDataType = "phone" | "email" | "url" | "text";

export type LegacyFraudCheckResponse = {
  input_value: string;
  risk_level: string;
  explanation: string;
  risk_score: number;
};
