export interface Case {
  id: string;
  name: string;
  description: string;
  target_person_id: string | null;
  created_at: string;
  document_count: number;
  analysis_status: string;
  analysis_phase: string;
  analysis_error: string;
  progress: string;
  model_used: string;
  active_run_id: string | null;
}
export interface Person {
  id: string;
  canonical_name: string;
  role: string;
  aliases: string[];
  pending_aliases: string[];
}
export interface Doc {
  id: string;
  filename: string;
  total_pages: number;
  processing_status: string;
  document_type: string;
  source_person_id: string | null;
  statement_time: string | null;
  warnings: string[];
  parser_type: string;
}
export interface Source {
  document_id: string;
  filename: string;
  page_number: number;
  quote: string;
  bbox: number[] | null;
  locator_metadata: { width: number; height: number };
  statement_time: string | null;
}
export interface Fact {
  id: string;
  subject_person_id: string | null;
  source_person_id: string | null;
  predicate: string;
  object_text: string;
  location: string;
  time_text: string;
  amount: number | null;
  polarity: string;
  quote: string;
  source_type: string;
  confidence: number;
  source: Source;
  document_id: string;
  page_number: number;
}
export interface Relation {
  id: string;
  relation_type: string;
  issue_key: string;
  explanation: string;
  confidence: number;
  fact_a: Fact;
  fact_b: Fact;
  review: { review_status: string; note: string } | null;
}
export interface System {
  llm_ready: boolean;
  configured_model: string;
  active_model: string | null;
  ocr: string;
  parser: string;
  database: string;
  external_ai_api: string;
}
