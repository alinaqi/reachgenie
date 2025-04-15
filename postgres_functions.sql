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
RETURNS TABLE (
    id uuid,
    created_at timestamptz,
    company_id uuid,
    campaign_id uuid,
    campaign_run_id uuid,
    lead_id uuid,
    call_script text,
    status text,
    priority integer,
    processed_at timestamptz,
    error_message text,
    retry_count integer,
    call_log_id uuid,
    work_time_start time,
    work_time_end time
) AS $$
BEGIN
    RETURN QUERY
    SELECT *
    FROM call_queue
    WHERE company_id = p_company_id
    AND status = 'pending'
    AND work_time_start IS NOT NULL
    AND work_time_end IS NOT NULL
    AND (
        (
            work_time_start <= work_time_end
            AND CURRENT_TIME >= work_time_start
            AND CURRENT_TIME <= work_time_end
        )
        OR
        (
            work_time_start > work_time_end
            AND (
                CURRENT_TIME >= work_time_start
                OR CURRENT_TIME <= work_time_end
            )
        )
    )
    ORDER BY priority DESC, created_at ASC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;
