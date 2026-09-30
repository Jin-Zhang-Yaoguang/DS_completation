-- 当前候选快照，来源 gold_candidates/registry.json；旧 SQL 已归档。
WITH current_candidates(model_id, submission_id, public_score, role) AS (
  VALUES ('A_H3',56099337,2408.7,'PRIMARY'),
         ('CLAUDE_RB7925',56044732,2043.0,'SECONDARY')
)
SELECT * FROM current_candidates WHERE public_score > 2000 ORDER BY public_score DESC;
