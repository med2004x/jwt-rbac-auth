# System Design

The design separates durable authorization data from high-churn token state. User records and persisted audit history live in PostgreSQL because they need transactional consistency and a clear schema history. Refresh token identifiers live in Redis because rotation and revocation are latency-sensitive and short-lived.

Refresh rotation is driven by a `jti` claim in the refresh token. When a refresh request arrives, the service verifies the JWT, checks Redis for the active identifier, revokes that identifier, and stores a newly minted replacement. This prevents refresh token reuse without introducing a heavyweight session table into every authorization check.

Administrative role mutation is a distinct code path protected by the admin role. The role update is persisted immediately, and a background task publishes an audit event so external consumers could subscribe to privileged changes without slowing down the response path.

