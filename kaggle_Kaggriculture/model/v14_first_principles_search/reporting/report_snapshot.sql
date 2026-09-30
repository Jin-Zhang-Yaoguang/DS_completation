-- Portable-report provenance query.
--
-- The material evidence transformation is implemented in v14_evidence.py and
-- writes report_snapshot.json.  This DuckDB query is the report's actual,
-- reviewable projection over that immutable-at-build-time snapshot; it does
-- not run validation, inspect held-out test outcomes, or contact Kaggle.
SELECT *
FROM read_json_auto(
  'kaggle_Kaggriculture/model/v14_first_principles_search/reporting/report_snapshot.json',
  format = 'auto'
);
