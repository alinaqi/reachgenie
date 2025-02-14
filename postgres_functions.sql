CREATE FUNCTION count_unique_leads_by_campaign(campaign_ids UUID[])
RETURNS INT AS $$
  SELECT COUNT(DISTINCT lead_id)
  FROM (
      SELECT lead_id FROM email_logs WHERE campaign_id = ANY(campaign_ids)
      UNION
      SELECT lead_id FROM calls WHERE campaign_id = ANY(campaign_ids)
  ) AS combined_leads;
$$ LANGUAGE sql STABLE;
