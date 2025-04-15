CREATE FUNCTION count_unique_leads_by_campaign(campaign_ids UUID[])
RETURNS INT AS $$
  SELECT COUNT(DISTINCT lead_id)
  FROM (
      SELECT lead_id FROM email_logs WHERE campaign_id = ANY(campaign_ids)
      UNION
      SELECT lead_id FROM calls WHERE campaign_id = ANY(campaign_ids)
  ) AS combined_leads;
$$ LANGUAGE sql STABLE;

-----

CREATE OR REPLACE FUNCTION get_next_calls_to_process(
    p_company_id uuid,
    p_limit integer
)
RETURNS SETOF call_queue AS $$
BEGIN
    RETURN QUERY
    SELECT cq.*
    FROM call_queue cq
    WHERE cq.company_id = p_company_id
    AND cq.status = 'pending'
    AND cq.work_time_start IS NOT NULL
    AND cq.work_time_end IS NOT NULL
    AND (
        (
            cq.work_time_start <= cq.work_time_end
            AND CURRENT_TIME >= cq.work_time_start
            AND CURRENT_TIME <= cq.work_time_end
        )
        OR
        (
            cq.work_time_start > cq.work_time_end
            AND (
                CURRENT_TIME >= cq.work_time_start
                OR CURRENT_TIME <= cq.work_time_end
            )
        )
    )
    ORDER BY cq.priority DESC, cq.created_at ASC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;
