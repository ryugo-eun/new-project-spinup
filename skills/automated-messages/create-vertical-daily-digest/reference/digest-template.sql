-- Sparta Daily Digest DM (tasking): the parameterized template.
--
-- ONLY the cfg block below changes per vertical. Everything under it is identical on every
-- campaign and must be copied verbatim. Nine placeholders, all inside cfg:
--
--   {{CAMPAIGN_ID}}   camp_...   the vertical's RL Studio campaign
--   {{PROJECT_ID}}    proj_...   the vertical's Mercor Teams project
--   {{VERTICAL}}      display name, e.g. Atria
--   {{DOMAIN_LABEL}}  what the writers actually do, e.g. Admin Healthcare
--   {{PAST_DUE_DAYS}} days in a stage before a task is Past Due. 3 everywhere so far
--   {{MAX_LINES}}     tasks listed per section before "and N more". 12 everywhere so far
--   {{EXP_ITER}}      iteration expectation. 2 on the older verticals
--   {{EXP_PASS_PCT}}  pass-rate expectation. 50 on the older verticals
--   {{POD_CHANNEL}}   e.g. #atria-pod-a. Drop the closing clause if the vertical has none
--   {{ACCOUNT_ID}}    acct_... SAME on all Sparta campaigns, see the skill
--
-- Handler: send_slack_message_as_bot
-- Body:    {"mode":"dm","jobId":"${JOBID}","message":"${MESSAGE_BODY}"}
-- Trigger: cron, "0 6 * * *" (Pacific)

WITH cfg AS (
  SELECT '{{CAMPAIGN_ID}}' AS campaign_id, '{{PROJECT_ID}}' AS project_id,
         '{{VERTICAL}}' AS vertical_name, '{{DOMAIN_LABEL}}' AS domain_label,
         {{PAST_DUE_DAYS}} AS past_due_days, {{MAX_LINES}} AS max_lines,
         {{EXP_ITER}} AS exp_iterations, {{EXP_PASS_PCT}} AS exp_pass_pct,
         '{{POD_CHANNEL}}' AS pod_channel,
         '{{ACCOUNT_ID}}' AS account_id),

-- Recipients: one active job per contractor, reviewers and leads excluded by title.
jobs AS (SELECT j.CONTRACTORID, j.JOBID FROM AURORA_MERCOR_PRODUCTION.JOBS j, cfg
  WHERE j.PROJECTID=cfg.project_id AND j.STATUS='active' AND COALESCE(j._FIVETRAN_DELETED,FALSE)=FALSE
    AND j.TITLE NOT ILIKE '%Project Manager%' AND j.TITLE NOT ILIKE '%Team Lead%' AND j.TITLE <> 'EPM'
  QUALIFY ROW_NUMBER() OVER (PARTITION BY j.CONTRACTORID ORDER BY j.CREATEDAT DESC, j.UPDATEDAT DESC, j.JOBID DESC)=1),

-- Live, non-archived worlds only. ARCHIVED_AT IS NULL is load bearing.
wg AS (SELECT w.WORLD_ID FROM RAW_ANNOTATION_PLATFORM_DATA.RL_STUDIO_PUBLIC.WORLDS w, cfg
  WHERE w.CAMPAIGN_ID=cfg.campaign_id AND w.IS_LATEST=TRUE AND COALESCE(w._FIVETRAN_DELETED,FALSE)=FALSE AND w.ARCHIVED_AT IS NULL),

-- Real tasking worlds only. The name filters drop the WB golden world, the test world,
-- templates, retired worlds and hand copies. Check the vertical's world names against these.
real_tasks AS (SELECT t.TASK_ID,t.TASK_NAME,t.TASK_STATUS,t.AUTHOR,t.WORLD_ID,t.TRANSITIONED_AT,t.VERSION
  FROM PROJECT_ANALYTICS.RLS.TASKS_BASE t, cfg
  WHERE t.CAMPAIGN_ID=cfg.campaign_id AND t.ARCHIVED_AT IS NULL
    AND t.WORLD_NAME NOT ILIKE '%golden%' AND t.WORLD_NAME NOT ILIKE '%test%'
    AND t.WORLD_NAME NOT ILIKE 'Template -%' AND t.WORLD_NAME NOT ILIKE '[OLD]%' AND t.WORLD_NAME NOT ILIKE '% - Copy'),

-- TASKS_BASE is version-per-row. rn=1 is the task's CURRENT state.
latest AS (SELECT r.*, ROW_NUMBER() OVER (PARTITION BY r.TASK_ID ORDER BY r.VERSION DESC) rn FROM real_tasks r),

-- What the writer is actually asked to look at. Excluded: terminal states, unclaimed work,
-- and the whole audit chain (audit is not a writer stage; a failed audit hands the task to a
-- "Needs ... Fixes" stage, and those ARE listed, so nothing is lost).
active AS (SELECT l.AUTHOR,l.TASK_ID,l.TASK_NAME,l.TASK_STATUS,
    DATEDIFF('day',CONVERT_TIMEZONE('America/Los_Angeles',l.TRANSITIONED_AT)::date,CONVERT_TIMEZONE('America/Los_Angeles',CURRENT_TIMESTAMP())::date) AS days_in_stage
  FROM latest l JOIN wg ON wg.WORLD_ID=l.WORLD_ID
  WHERE l.rn=1 AND l.AUTHOR IS NOT NULL AND l.TASK_STATUS IS NOT NULL
    AND l.TASK_STATUS NOT IN ('Discarded','Delivered','Ready for Delivery','Available for Claim','Unclaimed','Pending','Claimed for Writing')
    AND l.TASK_STATUS NOT ILIKE 'In Audit'
    AND l.TASK_STATUS NOT ILIKE 'Audit%'),

-- The annotator deep link needs BOTH query params. The bare path 404s.
lines AS (SELECT a.AUTHOR,a.days_in_stage,
    CASE WHEN a.days_in_stage > cfg.past_due_days THEN 'past' ELSE 'ontime' END AS bucket,
    '- <https://studio.mercor.com/annotator/tasks/'||a.TASK_ID||'/?accountId='||cfg.account_id||'&campaignId='||cfg.campaign_id||'|'||REGEXP_REPLACE(a.TASK_NAME,'[<>|]','')||'> - '||a.TASK_STATUS||' - '||
      CASE WHEN a.days_in_stage<=0 THEN 'entered today' WHEN a.days_in_stage=1 THEN '1 day in stage' ELSE a.days_in_stage||' days in stage' END||
      CASE WHEN a.TASK_STATUS ILIKE 'Running %' OR a.TASK_STATUS ILIKE '%Pipeline Running%'
           THEN ' - waiting on the pipeline, nothing for you to do' ELSE '' END AS line
  FROM active a, cfg),
ranked_lines AS (SELECT l.*, cfg.max_lines,
    ROW_NUMBER() OVER (PARTITION BY l.AUTHOR,l.bucket ORDER BY l.days_in_stage DESC,l.line) rk,
    COUNT(*) OVER (PARTITION BY l.AUTHOR,l.bucket) bucket_n FROM lines l, cfg),

-- NULLIF around LISTAGG: an all-NULL group returns empty string, not NULL, which printed a
-- bare "Past Due" heading with nothing under it.
blocks AS (SELECT AUTHOR,
    COALESCE(MAX(CASE WHEN bucket='ontime' THEN bucket_n END),0) ontime_n,
    COALESCE(MAX(CASE WHEN bucket='past' THEN bucket_n END),0) past_n,
    NULLIF(LISTAGG(CASE WHEN bucket='ontime' AND rk<=max_lines THEN line END,'<NL>') WITHIN GROUP (ORDER BY days_in_stage DESC,line),'') on_time_block,
    NULLIF(LISTAGG(CASE WHEN bucket='past' AND rk<=max_lines THEN line END,'<NL>') WITHIN GROUP (ORDER BY days_in_stage DESC,line),'') past_due_block,
    MAX(max_lines) max_lines FROM ranked_lines GROUP BY AUTHOR),

-- Studio identity to Mercor identity. Studio email prefix = USERMETADATA.EXTERNALID.
-- MERCORUSERS_NEW has no EXTERNALID column, do not try to route through it.
em AS (SELECT ru.USER_ID AS author, NULLIF(TRIM(REPLACE(REPLACE(ru.FIRST_NAME,'[EXP]',''),'[Exp]','')),'') first_name, SPLIT_PART(LOWER(ru.EMAIL),'@',1) extid
  FROM RAW_ANNOTATION_PLATFORM_DATA.RL_STUDIO_PUBLIC.USERS ru WHERE COALESCE(ru._FIVETRAN_DELETED,FALSE)=FALSE AND ru.EMAIL IS NOT NULL),
um AS (SELECT em.author, em.first_name, m.USERID FROM em JOIN AURORA_MERCOR_PRODUCTION.USERMETADATA m ON LOWER(m.EXTERNALID)=em.extid),
recip AS (SELECT um.author, um.first_name, j.JOBID, j.CONTRACTORID FROM um JOIN jobs j ON j.CONTRACTORID=um.USERID
  QUALIFY ROW_NUMBER() OVER (PARTITION BY um.author ORDER BY j.JOBID)=1),

-- Prefers the Studio task-writing timer, falls back to all clocked hours. On every vertical
-- except Vigil that column is 0.000000, so in practice this is ALL hours on the project.
hrs AS (SELECT um.author, SUM(a.TASK_PRODUCTION_DURATION_HOURS_STUDIO) tw_hours, SUM(a.DURATION_HOURS) all_hours
  FROM um JOIN PROJECT_ANALYTICS.CENTRALIZED.AHT_BASE a ON a.USERID=um.USERID CROSS JOIN cfg WHERE a.PROJECTID=cfg.project_id GROUP BY um.author),

-- CURRENT state, not history. A task that falls back to a Needs stage leaves this count.
finished AS (SELECT AUTHOR AS author, COUNT(DISTINCT TASK_ID) fin FROM latest
  WHERE rn=1 AND (TASK_STATUS IN ('Ready for Delivery','Delivered') OR TASK_STATUS ILIKE 'In Audit' OR TASK_STATUS ILIKE 'Audit%')
  GROUP BY AUTHOR),

-- Stage ranks match NAME PATTERNS, never exact status lists: cloned campaigns rename stages.
ranked AS (SELECT TASK_ID,AUTHOR,VERSION,
  CASE WHEN TASK_STATUS IS NULL THEN NULL WHEN TASK_STATUS='Discarded' THEN NULL
    WHEN TASK_STATUS IN ('Ready for Delivery','Delivered','In QC','Needs QC Revision') OR TASK_STATUS ILIKE 'Audit%' OR TASK_STATUS ILIKE 'In Audit' THEN 5
    WHEN TASK_STATUS ILIKE '%Final Review%' THEN 4
    WHEN TASK_STATUS ILIKE '%Preference Label%' THEN 3
    WHEN TASK_STATUS ILIKE '%First Human Review%' THEN 2 ELSE 1 END AS rnk FROM real_tasks),
seq AS (SELECT TASK_ID,AUTHOR,rnk,LAG(rnk) OVER (PARTITION BY TASK_ID ORDER BY VERSION) prev FROM ranked WHERE rnk IS NOT NULL),
pertask AS (SELECT AUTHOR,TASK_ID,
  SUM(CASE WHEN prev IN (2,4) AND rnk<prev THEN 1 ELSE 0 END) sb,
  SUM(CASE WHEN rnk IN (2,4) AND prev<rnk THEN 1 ELSE 0 END) sub,
  SUM(CASE WHEN prev IN (2,4) AND rnk>prev THEN 1 ELSE 0 END) pss,
  MAX(CASE WHEN rnk>=2 THEN 1 ELSE 0 END) reached FROM seq GROUP BY AUTHOR,TASK_ID),
metrics AS (SELECT AUTHOR AS author, SUM(sb) sb, SUM(reached) reached, SUM(sub) sub, SUM(pss) pss FROM pertask GROUP BY AUTHOR)

SELECT r.JOBID AS "JOBID", r.CONTRACTORID AS "contractorId", COALESCE(r.first_name,'there') AS "FIRSTNAME",
  r.CONTRACTORID||'_'||CURRENT_DATE()::varchar AS "daily_key",
  'Hi '||COALESCE(r.first_name,'there')||','||CHR(10)||CHR(10)||
  '*'||cfg.vertical_name||' Daily Status: '||
    CASE DAYNAME(CONVERT_TIMEZONE('America/Los_Angeles',CURRENT_TIMESTAMP()))
      WHEN 'Mon' THEN 'Monday' WHEN 'Tue' THEN 'Tuesday' WHEN 'Wed' THEN 'Wednesday' WHEN 'Thu' THEN 'Thursday'
      WHEN 'Fri' THEN 'Friday' WHEN 'Sat' THEN 'Saturday' WHEN 'Sun' THEN 'Sunday' END||', '||
    CASE MONTH(CONVERT_TIMEZONE('America/Los_Angeles',CURRENT_TIMESTAMP()))
      WHEN 1 THEN 'January' WHEN 2 THEN 'February' WHEN 3 THEN 'March' WHEN 4 THEN 'April' WHEN 5 THEN 'May' WHEN 6 THEN 'June'
      WHEN 7 THEN 'July' WHEN 8 THEN 'August' WHEN 9 THEN 'September' WHEN 10 THEN 'October' WHEN 11 THEN 'November' WHEN 12 THEN 'December' END
    ||' '||DAY(CONVERT_TIMEZONE('America/Los_Angeles',CURRENT_TIMESTAMP()))||'*'||CHR(10)||CHR(10)||
  'You have '||(b.ontime_n+b.past_n)||' active task'||CASE WHEN (b.ontime_n+b.past_n)=1 THEN '' ELSE 's' END||' ('||cfg.domain_label||').'||CHR(10)||
  CASE WHEN b.on_time_block IS NOT NULL THEN CHR(10)||'*:white_check_mark: On Time*'||CHR(10)||REPLACE(b.on_time_block,'<NL>',CHR(10))||CHR(10)||
    CASE WHEN b.ontime_n>b.max_lines THEN 'and '||(b.ontime_n-b.max_lines)||' more'||CHR(10) ELSE '' END ELSE '' END||
  CASE WHEN b.past_due_block IS NOT NULL THEN CHR(10)||'*:alarm_clock: Past Due*'||CHR(10)||REPLACE(b.past_due_block,'<NL>',CHR(10))||CHR(10)||
    CASE WHEN b.past_n>b.max_lines THEN 'and '||(b.past_n-b.max_lines)||' more'||CHR(10) ELSE '' END ELSE '' END||
  CHR(10)||'*:bar_chart: Your metrics*'||CHR(10)||
  'Total clocked time: '||CASE WHEN COALESCE(NULLIF(h.tw_hours,0),h.all_hours) > 0
        THEN TO_CHAR(ROUND(COALESCE(NULLIF(h.tw_hours,0),h.all_hours),1),'FM999990.0')||'h on this project'
        ELSE 'none logged yet' END||CHR(10)||
  'Tasks ready for delivery: '||COALESCE(f.fin,0)||CHR(10)||
  'Avg iterations per task: '||CASE WHEN COALESCE(m.reached,0)=0 THEN 'n/a' ELSE TO_CHAR(ROUND(m.sb/m.reached,1),'FM999990.0') END||' (times sent back from a human review)'||CHR(10)||
  'Pass rate: '||CASE WHEN COALESCE(m.sub,0)=0 THEN 'n/a' ELSE TO_CHAR(ROUND(m.pss/m.sub*100),'FM999990')||'%' END||' (passes / submissions to first or final human review)'||CHR(10)||CHR(10)||
  '*:dart: Expected*'||CHR(10)||
  'Time in a stage: move to the next stage within '||cfg.past_due_days||' days'||CHR(10)||
  'Avg iterations per task: '||cfg.exp_iterations||' or fewer'||CHR(10)||
  'Pass rate: above '||cfg.exp_pass_pct||'%'||CHR(10)||CHR(10)||
  'If you have any blockers please reach out to your pod lead in '||cfg.pod_channel||'!' AS "MESSAGE_BODY"
FROM recip r JOIN blocks b ON b.AUTHOR=r.author CROSS JOIN cfg
LEFT JOIN hrs h ON h.author=r.author LEFT JOIN finished f ON f.author=r.author LEFT JOIN metrics m ON m.author=r.author
