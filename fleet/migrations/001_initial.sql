-- =============================================================================
-- R58 Fleet Management Database Schema
-- Initial migration: Core tables for device management
-- =============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- Organizations (Multi-tenant)
-- =============================================================================
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    settings JSONB DEFAULT '{}'::jsonb,
    
    -- Subscription/limits
    max_devices INTEGER DEFAULT 10,
    plan TEXT DEFAULT 'free' CHECK (plan IN ('free', 'pro', 'enterprise'))
);

-- Create default organization
INSERT INTO organizations (id, name, slug) 
VALUES ('00000000-0000-0000-0000-000000000001', 'Default', 'default');

-- =============================================================================
-- Users
-- =============================================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'viewer' CHECK (role IN ('admin', 'operator', 'viewer')),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    last_login TIMESTAMPTZ,
    
    -- Account status
    is_active BOOLEAN DEFAULT true,
    email_verified BOOLEAN DEFAULT false,
    
    -- Profile
    avatar_url TEXT,
    preferences JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_users_org ON users(org_id);
CREATE INDEX idx_users_email ON users(email);

-- =============================================================================
-- Devices
-- =============================================================================
CREATE TABLE devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id TEXT UNIQUE NOT NULL,  -- Human-readable ID, e.g., "r58-prod-001"
    name TEXT NOT NULL,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Authentication
    token_hash TEXT NOT NULL,  -- SHA256 of device token
    token_created_at TIMESTAMPTZ DEFAULT now(),
    
    -- Status
    status TEXT DEFAULT 'offline' CHECK (status IN ('online', 'offline', 'updating', 'error', 'maintenance')),
    last_heartbeat TIMESTAMPTZ,
    last_error TEXT,
    error_count INTEGER DEFAULT 0,
    
    -- Version info
    current_version TEXT,
    target_version TEXT,  -- Pending update target
    update_channel TEXT DEFAULT 'stable' CHECK (update_channel IN ('stable', 'beta', 'dev')),
    last_update_at TIMESTAMPTZ,
    
    -- Hardware info
    platform TEXT,
    arch TEXT DEFAULT 'arm64',
    serial_number TEXT,
    mac_address TEXT,
    
    -- Capabilities snapshot (from device /capabilities endpoint)
    capabilities JSONB DEFAULT '{}'::jsonb,
    
    -- Location/metadata
    location TEXT,
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}'::jsonb,
    notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    registered_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_devices_org ON devices(org_id);
CREATE INDEX idx_devices_status ON devices(status);
CREATE INDEX idx_devices_device_id ON devices(device_id);
CREATE INDEX idx_devices_tags ON devices USING GIN(tags);

-- =============================================================================
-- Heartbeats (Time-series data, partitioned by month)
-- =============================================================================
CREATE TABLE heartbeats (
    id BIGSERIAL,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    received_at TIMESTAMPTZ DEFAULT now(),
    
    -- Metrics snapshot
    cpu_percent REAL,
    mem_percent REAL,
    disk_free_gb REAL,
    disk_total_gb REAL,
    temperature_c REAL,
    uptime_seconds BIGINT,
    load_avg REAL[],  -- 1, 5, 15 minute load averages
    
    -- Application status
    recording_active BOOLEAN DEFAULT false,
    mixer_active BOOLEAN DEFAULT false,
    active_inputs TEXT[],
    degradation_level INTEGER DEFAULT 0,
    
    -- Network
    ip_address INET,
    network_rx_bytes BIGINT,
    network_tx_bytes BIGINT,
    
    -- Errors
    error_count INTEGER DEFAULT 0,
    last_errors JSONB DEFAULT '[]'::jsonb,
    
    PRIMARY KEY (id, received_at)
) PARTITION BY RANGE (received_at);

-- Create partitions for the next 12 months
DO $$
DECLARE
    start_date DATE := date_trunc('month', CURRENT_DATE);
    end_date DATE;
    partition_name TEXT;
BEGIN
    FOR i IN 0..11 LOOP
        end_date := start_date + INTERVAL '1 month';
        partition_name := 'heartbeats_' || to_char(start_date, 'YYYY_MM');
        
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I PARTITION OF heartbeats FOR VALUES FROM (%L) TO (%L)',
            partition_name,
            start_date,
            end_date
        );
        
        start_date := end_date;
    END LOOP;
END $$;

CREATE INDEX idx_heartbeats_device_time ON heartbeats(device_id, received_at DESC);

-- =============================================================================
-- Commands (Remote commands queue)
-- =============================================================================
CREATE TABLE commands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    
    -- Command details
    type TEXT NOT NULL CHECK (type IN ('update', 'reboot', 'config', 'bundle', 'restart_service', 'custom')),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Status tracking
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'acked', 'running', 'completed', 'failed', 'cancelled', 'expired')),
    priority INTEGER DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),  -- 1 = highest
    
    -- Timing
    created_at TIMESTAMPTZ DEFAULT now(),
    sent_at TIMESTAMPTZ,
    acked_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    
    -- Result
    result JSONB,
    error TEXT,
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    
    -- Retry configuration
    retry_delay_seconds INTEGER DEFAULT 60,
    
    -- Audit
    created_by UUID REFERENCES users(id),
    cancelled_by UUID REFERENCES users(id),
    notes TEXT
);

CREATE INDEX idx_commands_device_status ON commands(device_id, status);
CREATE INDEX idx_commands_pending ON commands(status, priority) WHERE status = 'pending';
CREATE INDEX idx_commands_device_created ON commands(device_id, created_at DESC);

-- =============================================================================
-- Releases
-- =============================================================================
CREATE TABLE releases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version TEXT UNIQUE NOT NULL,
    channel TEXT NOT NULL DEFAULT 'stable' CHECK (channel IN ('stable', 'beta', 'dev')),
    
    -- Build info
    build_date TIMESTAMPTZ,
    git_sha TEXT,
    
    -- Artifacts
    artifact_url TEXT NOT NULL,
    signature_url TEXT,
    checksum_sha256 TEXT NOT NULL,
    size_bytes BIGINT,
    
    -- Compatibility
    min_version TEXT,
    arch TEXT DEFAULT 'arm64',
    
    -- Metadata
    changelog TEXT,
    release_notes TEXT,
    manifest JSONB,
    
    -- Status
    is_active BOOLEAN DEFAULT true,  -- Can be deployed
    is_latest BOOLEAN DEFAULT false, -- Latest in channel
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    published_at TIMESTAMPTZ,
    deprecated_at TIMESTAMPTZ,
    
    -- Audit
    created_by UUID REFERENCES users(id)
);

CREATE INDEX idx_releases_channel ON releases(channel, is_active, is_latest);
CREATE INDEX idx_releases_version ON releases(version);

-- =============================================================================
-- Support Bundles
-- =============================================================================
CREATE TABLE support_bundles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    
    -- Storage
    storage_path TEXT NOT NULL,  -- S3/local path
    storage_provider TEXT DEFAULT 'local' CHECK (storage_provider IN ('local', 's3', 'gcs')),
    size_bytes BIGINT,
    
    -- Metadata
    device_version TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ DEFAULT (now() + INTERVAL '30 days'),
    
    -- Contents
    includes_logs BOOLEAN DEFAULT true,
    includes_config BOOLEAN DEFAULT true,
    includes_recordings BOOLEAN DEFAULT false,
    includes_diagnostics BOOLEAN DEFAULT true,
    
    -- Privacy
    redacted BOOLEAN DEFAULT false,
    redaction_rules JSONB,
    
    -- Status
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'uploading', 'ready', 'expired', 'deleted')),
    download_count INTEGER DEFAULT 0,
    last_downloaded_at TIMESTAMPTZ,
    
    -- Audit
    requested_by UUID REFERENCES users(id),
    notes TEXT
);

CREATE INDEX idx_bundles_device ON support_bundles(device_id, created_at DESC);
CREATE INDEX idx_bundles_status ON support_bundles(status);

-- =============================================================================
-- Alerts
-- =============================================================================
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Alert details
    type TEXT NOT NULL,  -- disk_low, memory_high, offline, update_failed, etc.
    severity TEXT NOT NULL DEFAULT 'warning' CHECK (severity IN ('info', 'warning', 'error', 'critical')),
    title TEXT NOT NULL,
    message TEXT,
    
    -- Status
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'acknowledged', 'resolved', 'silenced')),
    
    -- Timing
    created_at TIMESTAMPTZ DEFAULT now(),
    acknowledged_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    silenced_until TIMESTAMPTZ,
    
    -- Context
    context JSONB DEFAULT '{}'::jsonb,  -- Additional data about the alert
    
    -- Audit
    acknowledged_by UUID REFERENCES users(id),
    resolved_by UUID REFERENCES users(id)
);

CREATE INDEX idx_alerts_device ON alerts(device_id, created_at DESC);
CREATE INDEX idx_alerts_org_status ON alerts(org_id, status);
CREATE INDEX idx_alerts_active ON alerts(status) WHERE status = 'active';

-- =============================================================================
-- Audit Log
-- =============================================================================
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    org_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    device_id UUID REFERENCES devices(id) ON DELETE SET NULL,
    
    -- Action
    action TEXT NOT NULL,  -- device.register, command.create, user.login, etc.
    resource_type TEXT,    -- device, command, user, release, etc.
    resource_id TEXT,
    
    -- Details
    details JSONB DEFAULT '{}'::jsonb,
    ip_address INET,
    user_agent TEXT,
    
    -- Timing
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_audit_org_time ON audit_log(org_id, created_at DESC);
CREATE INDEX idx_audit_user ON audit_log(user_id, created_at DESC);
CREATE INDEX idx_audit_device ON audit_log(device_id, created_at DESC);
CREATE INDEX idx_audit_action ON audit_log(action, created_at DESC);

-- =============================================================================
-- API Keys (for CI/CD and automation)
-- =============================================================================
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Key details
    name TEXT NOT NULL,
    key_hash TEXT NOT NULL,  -- SHA256 of the key
    key_prefix TEXT NOT NULL,  -- First 8 chars for identification
    
    -- Permissions
    scopes TEXT[] DEFAULT '{}',  -- e.g., ['releases:write', 'devices:read']
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    last_used_at TIMESTAMPTZ,
    use_count INTEGER DEFAULT 0,
    
    -- Expiration
    expires_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    created_by UUID REFERENCES users(id)
);

CREATE INDEX idx_api_keys_org ON api_keys(org_id);
CREATE INDEX idx_api_keys_prefix ON api_keys(key_prefix);

-- =============================================================================
-- Functions and Triggers
-- =============================================================================

-- Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_organizations_updated_at
    BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_devices_updated_at
    BEFORE UPDATE ON devices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Update device status based on heartbeat
CREATE OR REPLACE FUNCTION update_device_on_heartbeat()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE devices
    SET 
        status = 'online',
        last_heartbeat = NEW.received_at,
        error_count = CASE WHEN NEW.error_count > 0 THEN NEW.error_count ELSE 0 END
    WHERE id = NEW.device_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER on_heartbeat_update_device
    AFTER INSERT ON heartbeats
    FOR EACH ROW EXECUTE FUNCTION update_device_on_heartbeat();

-- Mark devices offline after no heartbeat
CREATE OR REPLACE FUNCTION mark_devices_offline()
RETURNS void AS $$
BEGIN
    UPDATE devices
    SET status = 'offline'
    WHERE status = 'online'
      AND last_heartbeat < now() - INTERVAL '3 minutes';
END;
$$ LANGUAGE plpgsql;

-- Expire old commands
CREATE OR REPLACE FUNCTION expire_old_commands()
RETURNS void AS $$
BEGIN
    UPDATE commands
    SET status = 'expired'
    WHERE status = 'pending'
      AND expires_at IS NOT NULL
      AND expires_at < now();
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Views
-- =============================================================================

-- Device summary with latest metrics
CREATE VIEW device_summary AS
SELECT 
    d.*,
    h.cpu_percent,
    h.mem_percent,
    h.disk_free_gb,
    h.temperature_c,
    h.recording_active,
    h.mixer_active,
    h.uptime_seconds,
    o.name as org_name,
    (SELECT COUNT(*) FROM commands c WHERE c.device_id = d.id AND c.status = 'pending') as pending_commands,
    (SELECT COUNT(*) FROM alerts a WHERE a.device_id = d.id AND a.status = 'active') as active_alerts
FROM devices d
LEFT JOIN organizations o ON d.org_id = o.id
LEFT JOIN LATERAL (
    SELECT * FROM heartbeats
    WHERE device_id = d.id
    ORDER BY received_at DESC
    LIMIT 1
) h ON true;

-- =============================================================================
-- Grants (adjust as needed)
-- =============================================================================
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO fleet_api;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO fleet_api;

