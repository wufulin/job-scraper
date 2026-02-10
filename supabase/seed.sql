-- seed.sql
-- Seed data extracted from config/sites.yaml and config/keywords.yaml.
-- All INSERTs use ON CONFLICT DO NOTHING for idempotent re-runs.

-- =============================================================================
-- site_configs (from config/sites.yaml)
-- =============================================================================
INSERT INTO site_configs (site_key, name, url, adapter, enabled, skip_location_match, rate_limit_seconds, max_pages, extra_config)
VALUES
    ('remoteok', 'RemoteOK', 'https://remoteok.com/api', 'api', true, true, 2, NULL,
     '{"headers": {"User-Agent": "Mozilla/5.0"}}'::jsonb),
    ('eleduck', '电鸭', 'https://svc.eleduck.com/api/v1/posts', 'api', true, false, 2, 5,
     '{"headers": {"User-Agent": "Mozilla/5.0"}, "params": {"category": 5}}'::jsonb),
    ('weworkremotely', 'WeWorkRemotely', 'https://weworkremotely.com/remote-jobs.rss', 'rss', true, true, 2, NULL,
     '{"headers": {"User-Agent": "Mozilla/5.0"}}'::jsonb),
    ('workgo', 'WorkGo', 'https://workgo.ai', 'api', false, true, 2, 5,
     '{"headers": {"User-Agent": "Mozilla/5.0"}, "api_url": "https://api.workgo.ai/auth/jobs/all", "clerk_base": "https://clerk.workgo.ai", "page_size": 20}'::jsonb),
    ('v2ex', 'V2EX', 'https://www.v2ex.com/go/remote', 'hybrid', true, false, 6, 3,
     '{"headers": {"User-Agent": "Mozilla/5.0"}, "api_base": "https://www.v2ex.com/api/topics/show.json"}'::jsonb),
    ('arcdev', 'Arc.dev', 'https://arc.dev/remote-jobs', 'browser', true, true, 2, NULL,
     '{"headers": {"User-Agent": "Mozilla/5.0"}}'::jsonb),
    ('yuancheng', '远程.work', 'https://yuancheng.work/jobs/', 'html', false, false, 2, NULL,
     '{"headers": {"User-Agent": "Mozilla/5.0"}}'::jsonb)
ON CONFLICT (site_key) DO NOTHING;

-- =============================================================================
-- keyword_configs (from config/keywords.yaml — location group)
-- =============================================================================
INSERT INTO keyword_configs (group_name, keyword) VALUES
    ('location', 'remote'),
    ('location', '远程'),
    ('location', '远程工作'),
    ('location', '远程办公'),
    ('location', '在家办公'),
    ('location', 'work from home'),
    ('location', 'wfh'),
    ('location', 'fully remote'),
    ('location', 'location independent')
ON CONFLICT (group_name, keyword) DO NOTHING;

-- keyword_configs (from config/keywords.yaml — technology group)
INSERT INTO keyword_configs (group_name, keyword) VALUES
    ('technology', 'AI'),
    ('technology', 'artificial intelligence'),
    ('technology', 'AI agent'),
    ('technology', 'AI 应用'),
    ('technology', 'AI应用开发'),
    ('technology', 'LLM'),
    ('technology', '大模型'),
    ('technology', '大语言模型'),
    ('technology', '机器学习'),
    ('technology', 'machine learning'),
    ('technology', 'deep learning'),
    ('technology', '深度学习'),
    ('technology', 'NLP'),
    ('technology', '自然语言处理'),
    ('technology', 'GPT'),
    ('technology', 'Claude'),
    ('technology', 'RAG'),
    ('technology', 'langchain'),
    ('technology', 'prompt engineer')
ON CONFLICT (group_name, keyword) DO NOTHING;

-- =============================================================================
-- match_rules (from config/keywords.yaml)
-- =============================================================================
INSERT INTO match_rules (rule_name, expression, skip_location_for)
VALUES
    ('default', 'location AND technology', ARRAY['remoteok', 'weworkremotely'])
ON CONFLICT (rule_name) DO NOTHING;
