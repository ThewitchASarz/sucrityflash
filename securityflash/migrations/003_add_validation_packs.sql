-- Migration: Add validation_packs table for Phase 2/3
-- NO AUTONOMOUS EXPLOITATION - human-executed validation only

CREATE TABLE IF NOT EXISTS validation_packs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    finding_id UUID REFERENCES findings(id) ON DELETE SET NULL,
    action_spec_id UUID REFERENCES action_specs(id) ON DELETE SET NULL,

    -- Pack metadata
    title VARCHAR NOT NULL,
    category VARCHAR NOT NULL,
    risk_level VARCHAR NOT NULL,

    -- Instructions (human-readable, engagement-safe)
    instructions_md TEXT NOT NULL,
    command_templates JSONB,  -- Parameterized templates, not executable code
    required_evidence_types JSONB DEFAULT '[]'::jsonb,
    evidence_checklist_md TEXT,

    -- Safety constraints
    target_must_match_scope BOOLEAN DEFAULT true NOT NULL,
    rate_limit_seconds JSONB,
    safety_notes TEXT,

    -- Lifecycle
    status VARCHAR NOT NULL DEFAULT 'PENDING_APPROVAL',

    -- Ownership
    created_by VARCHAR NOT NULL,
    approved_by VARCHAR,
    assigned_to VARCHAR,
    completed_by VARCHAR,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    approved_at TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

    -- Evidence attachments
    evidence_ids JSONB DEFAULT '[]'::jsonb,

    -- Execution notes
    execution_notes TEXT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_validation_packs_run_id ON validation_packs(run_id);
CREATE INDEX IF NOT EXISTS idx_validation_packs_finding_id ON validation_packs(finding_id);
CREATE INDEX IF NOT EXISTS idx_validation_packs_status ON validation_packs(status);
CREATE INDEX IF NOT EXISTS idx_validation_packs_created_at ON validation_packs(created_at);

-- Add validation_packs relationship to findings if not exists
-- (Already defined in model, no schema change needed)

COMMENT ON TABLE validation_packs IS 'High-risk validation procedures for human execution only. Worker MUST refuse.';
COMMENT ON COLUMN validation_packs.instructions_md IS 'Step-by-step human instructions (engagement-safe, no exploit code)';
COMMENT ON COLUMN validation_packs.command_templates IS 'Parameterized command templates for reference only';
COMMENT ON COLUMN validation_packs.target_must_match_scope IS 'CRITICAL: Enforces scope validation before execution';
