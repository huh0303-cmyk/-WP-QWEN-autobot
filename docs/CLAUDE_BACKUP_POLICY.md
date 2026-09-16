# Claude backup policy

Claude is the first server-side failover provider for WordPress/general text generation when the OpenAI API is unavailable because of quota, rate limiting, timeout, overload, authentication failure, or retriable upstream errors.

This policy does not claim that a VPS can detect ChatGPT product-session token limits. Continuity is guaranteed at the API/work-queue layer instead.

Failover must preserve the same job/request identity and must never create a second public publication merely because the first provider response was uncertain.
