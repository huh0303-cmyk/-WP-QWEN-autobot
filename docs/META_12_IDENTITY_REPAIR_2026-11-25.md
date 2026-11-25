# Meta twelve-destination identity and reservation repair

The owner authorized completing six Instagram and six Threads accounts, including
credential registration, controlled real posts, and eventual automatic publication.
Japanese, Korean and Seoul Jisoo Threads tokens were saved in META-SOCIAL on November 25.
Credential values are never recorded here.

- Prefer the exact current account token name in preflight, single test, scheduled
  twelve-destination publisher and Threads-only publisher.
- When the exact name is absent, retain the existing English PICK1, Korean SEOUL_TOPIK,
  and Seoul Jisoo legacy token fallbacks. Every use still requires authenticated
  `/me` to match the current expected handle. A legacy name is not proof of identity.
- A separate USER_ID setting is optional. A supplied ID must match; otherwise derive
  the numeric ID from the verified authenticated response before any publication.
- Single-test reservations include the actual `test_attempted_at_kst` field and
  reserved/uncertain statuses. A network failure must never cause an automatic duplicate.
- Identity preflight remains read-only. Scheduling gates remain unchanged until
  all twelve destination identities, write access and test public URLs are verified.

Validation: unit and integration tests cover all twelve identities without configured
IDs, wrong handles/IDs, invalid API identity fields, and reservation retry blocking.
Live verification and any remaining missing authorizations belong in the activity ledger.

The owner's requested card-news/carousel presentation is recorded separately in the
activity ledger. This credential repair does not claim that media authoring is implemented.
