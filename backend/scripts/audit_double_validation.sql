-- F03 SC-007 — Audit hebdomadaire : aucune source verified sans double validation.
-- Doit retourner 0 ligne (toute source verified a verified_by != captured_by).

SELECT id, title, publisher, captured_by, verified_by, verified_at
FROM source
WHERE verification_status = 'verified'
  AND (
    verified_by IS NULL
    OR verified_by = captured_by
    OR verified_at IS NULL
    OR embedding IS NULL
  )
ORDER BY verified_at DESC NULLS LAST;
