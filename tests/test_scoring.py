from ai_outbound_engine.leads import Lead
from ai_outbound_engine.scoring import score_lead


def test_strong_fit_is_tier_a_with_breakdown(vp_sales, config):
    result = score_lead(vp_sales, config.icp)
    assert result.tier == "A"
    assert result.score == 75
    parts = {name: (points, hit) for name, points, hit in result.breakdown}
    assert parts["title"] == (25, "sales")
    assert parts["seniority"] == (20, "vp")
    assert parts["industry"][0] == 30
    assert "seniority +20 (vp)" in result.explain()


def test_negative_keyword_penalizes_and_clamps_at_zero(config):
    intern = Lead(first_name="Marco", title="Marketing Intern", company="Pixelpear", domain="p.example")
    result = score_lead(intern, config.icp)
    assert result.score == 0
    assert result.tier == "C"
    assert ("negative", -40, "intern") in result.breakdown


def test_keywords_match_whole_words_only(config):
    # "mvp" must not trigger the "vp" seniority keyword.
    lead = Lead(first_name="X", title="MVP Builder", company="Y", domain="y.example")
    assert score_lead(lead, config.icp).breakdown == []
    assert score_lead(lead, config.icp).explain() == "no ICP signals matched"


def test_industry_points_are_capped(config):
    lead = Lead(first_name="X", title="Analyst", company="Y", domain="y.example",
                industry="B2B SaaS software platform API analytics fintech")
    industry = [p for name, p, _ in score_lead(lead, config.icp).breakdown if name == "industry"]
    assert industry == [config.icp.industry_max]


def test_homepage_text_contributes_industry_signal(config):
    lead = Lead(first_name="X", title="Head of Growth", company="Y", domain="y.example")
    without = score_lead(lead, config.icp).score
    with_page = score_lead(lead, config.icp, page_text="The analytics platform for B2B teams").score
    assert with_page == without + 30
