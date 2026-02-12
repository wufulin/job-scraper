import asyncpg
import asyncio
import os

DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres.liltwsrgnlkuucnivuic:gxSG2RxxFTwmGiPe@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres')

async def test():
    conn = await asyncpg.connect(DB_URL)
    
    # Test 1: keyword_configs has enabled column
    cols = await conn.fetch("SELECT column_name FROM information_schema.columns WHERE table_name='keyword_configs'")
    col_names = [c['column_name'] for c in cols]
    assert 'enabled' in col_names, f"enabled column missing: {col_names}"
    print("[OK] keyword_configs.enabled exists")
    
    # Test 2: ConfigService methods work
    import sys
    sys.path.insert(0, '.')
    from app.services.config_service import ConfigService
    
    svc = ConfigService(pool=conn, cache_ttl_seconds=0)
    
    sites = await svc.get_site_configs()
    assert len(sites) > 0, "No sites returned"
    assert all('site_key' in s for s in sites), f"site_key missing from site configs: {sites[0].keys()}"
    assert all('extra_config' in s for s in sites), f"extra_config missing from site configs: {sites[0].keys()}"
    print(f"[OK] get_site_configs() works: {len(sites)} sites, has site_key and extra_config")
    
    keywords = await svc.get_keyword_configs()
    assert len(keywords) > 0, "No keywords returned"
    print(f"[OK] get_keyword_configs() works: {len(keywords)} keywords")
    
    rules = await svc.get_match_rules()
    assert len(rules) > 0, "No rules returned"
    print(f"[OK] get_match_rules() works: {len(rules)} rules")
    
    # Test 3: get_site_config_by_id also has site_key
    if sites:
        site_id = sites[0]['id']
        single_site = await svc.get_site_config_by_id(site_id)
        assert single_site is not None, f"Site {site_id} not found"
        assert 'site_key' in single_site, f"site_key missing from single site: {single_site.keys()}"
        assert 'extra_config' in single_site, f"extra_config missing from single site: {single_site.keys()}"
        print(f"[OK] get_site_config_by_id() works: has site_key and extra_config")
    
    await conn.close()
    print("\n[SUCCESS] All ConfigService methods working correctly!")

asyncio.run(test())
