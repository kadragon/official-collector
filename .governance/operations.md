<!-- Trace:
spec_id: SPEC-governance-doc-structure-1
task_id: TASK-001
-->
# Operations Guide

## System Architecture

### Core Components
- **Supabase Database**: PostgreSQL with pgvector extension
  - Tables: `task_card_mappings`, `reception_mappings`
  - Vector similarity search via RPC functions
- **OpenAI Embeddings**: text-embedding-3-small (1536 dimensions)
  - Cost: $0.00002 per 1K tokens
  - Rate limits: 3M tokens/min (Tier 1)
- **RPA Automation**: pywinauto-based document processing

### Environment Variables
```bash
# Required
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
OPENAI_API_KEY=sk-...

# Optional
ENVIRONMENT=production|development
VECTOR_SIMILARITY_THRESHOLD=0.3
OPENAI_DAILY_BUDGET_USD=10.0
OPENAI_MONTHLY_BUDGET_USD=300.0
QUOTA_WARNING_THRESHOLD=0.7
QUOTA_CRITICAL_THRESHOLD=0.9
QUOTA_AUTO_STOP=false
```

## Monitoring & Alerting

### Health Metrics
- **Success Rate**: Percentage of successful API calls
- **Average Response Time**: Rolling average in milliseconds
- **Error Count**: Total number of failures
- **Consecutive Failures**: Current streak of failures

### Health Status Levels
- **healthy**: Success rate > 90%, no consecutive failures
- **degraded**: Success rate 80-90%
- **unhealthy**: Success rate < 80%

### Alert Types

#### API Failure Alerts
**Trigger**: 3+ consecutive failures OR error rate > 10%
**Response**:
1. Check service health status
2. Review recent error logs
3. Verify API credentials
4. Check service status pages (OpenAI, Supabase)

#### Performance Degradation Alerts
**Trigger**: Response time > 5000ms
**Response**:
1. Check network connectivity
2. Review database query performance
3. Check OpenAI API latency
4. Consider scaling resources

#### Rate Limit Alerts
**Trigger**: OpenAI rate limit exceeded (automatic retry with exponential backoff)
**Response**:
1. Review usage patterns
2. Consider request batching
3. Check if quota upgrade needed

#### Database Error Alerts
**Trigger**: Supabase query failures OR connection timeouts
**Response**:
1. Verify Supabase project status
2. Check RLS policies
3. Review database logs in Supabase dashboard
4. Verify network connectivity

### Checking System Health
```python
from utils.monitoring_hooks import get_monitoring_hooks

monitoring = get_monitoring_hooks()

# Get health for all services
health = monitoring.get_health_status()
print(health)

# Get health for specific service
openai_health = monitoring.get_health_status("openai")
supabase_health = monitoring.get_health_status("supabase")

# Get recent alerts
alerts = monitoring.get_recent_alerts(limit=10)
```

## Audit Logging

### Audit Log Location
- `./logs/audit/audit_YYYYMMDD.jsonl`
- New file created daily
- UTF-8 encoding, JSON Lines format

### Audit Log Structure
```json
{
  "timestamp": "2025-11-13T10:30:45.123456",
  "action": "CREATE|READ|UPDATE|DELETE|SEARCH|API_CALL",
  "resource": "reception_document|task_card|embedding|supabase|openai|configuration",
  "resource_id": "document_title_or_identifier",
  "user": "system",
  "status": "success|failure|error",
  "details": {"key": "value"},
  "error_message": "optional error message",
  "duration_ms": 123.45
}
```

### Critical Operations Logged
1. **Data Modifications**: Reception/task card upserts, data deletions (especially `clear_all_data`)
2. **API Calls**: OpenAI embedding generation, Supabase vector searches, database queries
3. **Search Operations**: Vector similarity searches, result counts, quality metrics

### Reviewing Audit Logs
```bash
# View today's audit logs
cat logs/audit/audit_$(date +%Y%m%d).jsonl

# Filter by action type
grep '"action":"DELETE"' logs/audit/audit_*.jsonl

# Filter by status
grep '"status":"failure"' logs/audit/audit_*.jsonl

# Pretty print specific entry
cat logs/audit/audit_*.jsonl | jq 'select(.resource_id=="specific_document")'

# Count operations by type
cat logs/audit/audit_*.jsonl | jq -r .action | sort | uniq -c
```

### Compliance & Retention
- **Retention Period**: 90 days (recommended)
- **Backup**: Archive monthly to secure storage
- **Access Control**: Restrict to authorized personnel only

## API Quota Management

### Budget Configuration
Default budgets (override via environment variables):
- **Daily Budget**: $10.00 USD
- **Monthly Budget**: $300.00 USD

### Quota Status Levels
- **OK**: < 70% of budget used
- **WARNING**: 70-90% of budget used
- **CRITICAL**: 90-100% of budget used
- **EXCEEDED**: > 100% of budget used

### Checking Quota Usage
```python
from utils.quota_manager import get_quota_manager

quota = get_quota_manager()

# Get usage summary
summary = quota.get_usage_summary()
print(f"Daily: ${summary['daily']['cost_usd']:.4f} / ${summary['daily']['budget_usd']:.2f}")
print(f"Monthly: ${summary['monthly']['cost_usd']:.4f} / ${summary['monthly']['budget_usd']:.2f}")
print(f"Status: {summary['daily']['status']}")

# Check if request can be made
can_proceed, reason = quota.can_make_request(estimated_tokens=1000)
if not can_proceed:
    print(f"Request blocked: {reason}")
```

### Quota Alerts
Alerts are logged when quota status changes:
- **WARNING**: 70% threshold crossed
- **CRITICAL**: 90% threshold crossed
- **EXCEEDED**: 100% threshold crossed

### Managing Quota Overruns
1. **Temporary Increase**
   ```bash
   export OPENAI_DAILY_BUDGET_USD=20.0
   export OPENAI_MONTHLY_BUDGET_USD=600.0
   ```

2. **Auto-Stop on Exceed**
   ```bash
   export QUOTA_AUTO_STOP=true
   ```
   ⚠️ **Warning**: This will block all API calls when quota exceeded

3. **Reset Metrics** (development only)
   ```python
   from utils.quota_manager import get_quota_manager
   quota = get_quota_manager()
   quota.reset_metrics()  # Resets daily and monthly
   ```

## Common Operations

### Starting the System
```bash
# Standard mode (automatic)
uv run ./src/main.py

# Interactive mode (manual selections)
uv run ./src/main.py --interactive

# Deletion interface
uv run ./src/main.py --delete
```

### Checking Connection Status
```python
from services.supabase_service import SupabaseService
from services.openai_embedding_service import OpenAIEmbeddingService

embedding_service = OpenAIEmbeddingService()
supabase = SupabaseService(embedding_service)
status = supabase.get_connection_status()
print(status)

# Check document counts
card_count = supabase.get_document_count("task_card")
reception_count = supabase.get_document_count("reception")
print(f"Cards: {card_count}, Receptions: {reception_count}")
```

### Monitoring Performance
```python
from utils.performance_logger import get_performance_tracker

tracker = get_performance_tracker()
stats = tracker.get_all_stats()

for operation, metrics in stats.items():
    print(f"{operation}:")
    print(f"  Count: {metrics['count']}")
    print(f"  Avg: {metrics['avg']:.3f}s")
    print(f"  Min/Max: {metrics['min']:.3f}s / {metrics['max']:.3f}s")
```

## Troubleshooting

### High OpenAI API Latency
**Symptoms**: Response times > 5 seconds, performance degradation alerts
**Diagnosis**:
1. Check OpenAI status: https://status.openai.com
2. Review monitoring metrics
3. Check network connectivity
**Resolution**: Wait for service recovery, consider request batching, check rate limits

### Supabase Connection Failures
**Symptoms**: "Connection refused" errors, database timeout errors, consecutive failure alerts
**Diagnosis**:
1. Verify Supabase project status
2. Check credentials (`SUPABASE_URL`, `SUPABASE_KEY`)
3. Test connectivity: `curl $SUPABASE_URL/rest/v1/`
**Resolution**:
1. Verify environment variables
2. Check Supabase dashboard for issues
3. Verify RLS policies not blocking queries
4. Check network/firewall rules

### Vector Search Returning No Results
**Symptoms**: Empty recommendation lists, search queries returning 0 results
**Diagnosis**:
1. Check similarity threshold: `VECTOR_SIMILARITY_THRESHOLD`
2. Verify embeddings exist
3. Check if documents uploaded
**Resolution**:
1. Lower similarity threshold (default: 0.3) → `export VECTOR_SIMILARITY_THRESHOLD=0.2`
2. Verify document count: `supabase.get_document_count("task_card")`
3. Run migration scripts if needed

### Quota Exceeded Errors
**Symptoms**: "Quota check failed" errors, API calls blocked, EXCEEDED status in logs
**Diagnosis**:
1. Check quota usage summary
2. Review audit logs for high-volume operations
3. Identify unexpected usage patterns
**Resolution**:
1. Increase budget limits
2. Optimize batch sizes
3. Enable auto-stop to prevent overruns
4. Review usage patterns for inefficiencies

### Audit Logs Not Created
**Symptoms**: No files in `./logs/audit/`, missing audit entries
**Diagnosis**:
1. Check directory permissions
2. Verify disk space
3. Check if audit logger initialized
**Resolution**:
```bash
mkdir -p ./logs/audit
chmod 755 ./logs/audit
# Verify initialization in main.py - should call init_audit_logger() at startup
```

## Emergency Procedures

### Emergency Shutdown
If system is causing issues (cost overruns, data corruption):
```bash
# 1. Stop the process
kill -SIGTERM <pid>

# 2. Disable auto-start if configured
systemctl stop official-collector  # if using systemd

# 3. Set quota to zero to block API calls
export OPENAI_DAILY_BUDGET_USD=0.0
export QUOTA_AUTO_STOP=true
```

### Data Corruption Recovery
⚠️ **Never use in production**
```python
# Development/Testing only
from services.supabase_service import SupabaseService
from services.openai_embedding_service import OpenAIEmbeddingService

embedding_service = OpenAIEmbeddingService()
supabase = SupabaseService(embedding_service)

# This will be blocked in production
result = supabase.clear_all_data()  # Returns False if ENVIRONMENT=production
```

**Production Recovery**:
1. Access Supabase dashboard
2. Use SQL editor for targeted fixes
3. Restore from backup if available

### Emergency Contacts
- **Supabase Support**: https://supabase.com/support
- **OpenAI Support**: https://help.openai.com
- **Project Maintainer**: [Add contact info]

## Deployment Checklist
- [ ] All environment variables configured
- [ ] Supabase RLS policies verified
- [ ] OpenAI API key with sufficient quota
- [ ] Budget limits configured appropriately
- [ ] Audit logging directory created
- [ ] Monitoring thresholds tuned
- [ ] Emergency procedures documented
- [ ] Backup strategy in place
- [ ] Access controls configured
- [ ] All tests passing

## Configuration Reference

### Performance Thresholds
```python
# In monitoring_hooks initialization
performance_threshold_ms = 5000.0      # Alert if response > 5s
error_rate_threshold = 0.1             # Alert if error rate > 10%
consecutive_failure_threshold = 3      # Alert after 3 failures
```

### Timeout Configuration
See `src/config.py` for complete timeout settings:
- `ELEMENT_WAIT`: 3.0s
- `WINDOW_WAIT`: 3.0s
- `RECEPTION_CONFIRMATION`: 5.0s
- `CIRCULATION_COMPLETION`: 8.0s

### Pricing Configuration
```python
# OpenAI Embedding Pricing
TEXT_EMBEDDING_3_SMALL_PRICE = 0.00002  # per 1K tokens
CHARS_PER_TOKEN = 4                     # estimation
```
