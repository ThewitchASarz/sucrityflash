export interface HealthStatus {
  status: string;
  app: string;
  version: string;
  environment: string;
}

export interface Project {
  id: string;
  name: string;
  customer_id: string;
  description?: string;
  status: string;
  created_at: string;
}

export interface Scope {
  id: string;
  project_id: string;
  scope_json: {
    scope_type?: string;
    targets?: Array<{ type: string; value: string; criticality: string }>;
    excluded_targets?: Array<{ type: string; value: string; criticality: string }>;
    attack_vectors_allowed?: string[];
    attack_vectors_prohibited?: string[];
    approved_tools?: string[];
  };
  locked_at?: string;
  status: string;
  created_at: string;
}

export interface Run {
  id: string;
  plan_id: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface RunStats {
  action_specs_count: number;
  pending_approvals_count: number;
  approved_count: number;
  executed_count: number;
  evidence_count: number;
  last_activity_at?: string;
}

export interface TimelineEvent {
  timestamp: string;
  agent_type: string;
  action: string;
  details?: any;
  event_type: string;
  actor?: string;
}

export interface Evidence {
  id: string;
  evidence_type: string;
  validation_status: string;
  generated_by: string;
  evidence_metadata?: {
    tool_used?: string;
    returncode?: number;
  };
  artifact_uri: string;
  artifact_hash: string;
  created_at: string;
  generated_at: string;
}

export interface PendingApproval {
  action_id: string;
  tool: string;
  target: string;
  arguments: string[];
  justification: string;
  proposed_by: string;
  risk_score: string;
  approval_tier: string;
}
