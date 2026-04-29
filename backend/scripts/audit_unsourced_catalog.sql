-- F03 SC-001 — Audit : aucune entité catalogue exposée sans source verified.
-- Doit retourner 0 ligne pour passer l'audit.
--
-- Couvre les tables catalogue F01 portant `source_id` :
--   indicateur, critere, document_requis, facteur_emission.
-- (referentiel, formule, seuil n'ont pas de source_id en F01 — couverts en F09.)

WITH unsourced AS (
  SELECT 'indicateur' AS entity, i.id AS entity_id
  FROM indicateur i
  LEFT JOIN source s ON s.id = i.source_id
  WHERE s.id IS NULL OR s.verification_status <> 'verified'

  UNION ALL

  SELECT 'critere' AS entity, c.id AS entity_id
  FROM critere c
  LEFT JOIN source s ON s.id = c.source_id
  WHERE s.id IS NULL OR s.verification_status <> 'verified'

  UNION ALL

  SELECT 'document_requis' AS entity, d.id AS entity_id
  FROM document_requis d
  LEFT JOIN source s ON s.id = d.source_id
  WHERE s.id IS NULL OR s.verification_status <> 'verified'

  UNION ALL

  SELECT 'facteur_emission' AS entity, f.id AS entity_id
  FROM facteur_emission f
  LEFT JOIN source s ON s.id = f.source_id
  WHERE s.id IS NULL OR s.verification_status <> 'verified'
)
SELECT entity, count(*) AS unsourced_count
FROM unsourced
GROUP BY entity
ORDER BY entity;
