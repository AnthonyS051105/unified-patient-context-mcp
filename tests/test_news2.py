import pytest
from engine.news2 import calculate_news2
from engine.mews import calculate_mews


class TestNEWS2:
    def test_low_risk_healthy_patient(self):
        result = calculate_news2(rr=16, spo2=97, sbp=120, hr=75, temp=37.0, consciousness="A")
        assert result.total_score == 0
        assert result.risk_level == "low"
        assert result.algorithm == "NEWS2"

    def test_high_risk_deteriorating_patient(self):
        result = calculate_news2(rr=26, spo2=90, sbp=88, hr=115, temp=38.5, consciousness="V")
        assert result.risk_level == "high"
        assert result.total_score >= 7

    def test_medium_risk(self):
        result = calculate_news2(rr=22, spo2=95, sbp=105, hr=95, temp=38.2, consciousness="A")
        assert result.risk_level in ("low-medium", "medium")

    def test_respiratory_rate_extreme_low(self):
        result = calculate_news2(rr=6, spo2=97, sbp=120, hr=75, temp=37.0, consciousness="A")
        assert result.parameter_scores["respiratory_rate"] == 3

    def test_respiratory_rate_normal(self):
        result = calculate_news2(rr=16, spo2=97, sbp=120, hr=75, temp=37.0, consciousness="A")
        assert result.parameter_scores["respiratory_rate"] == 0

    def test_spo2_critical(self):
        result = calculate_news2(rr=16, spo2=89, sbp=120, hr=75, temp=37.0, consciousness="A")
        assert result.parameter_scores["spo2"] == 3

    def test_sbp_hypotension(self):
        result = calculate_news2(rr=16, spo2=97, sbp=85, hr=75, temp=37.0, consciousness="A")
        assert result.parameter_scores["systolic_bp"] == 3

    def test_supplemental_o2_adds_2_points(self):
        without = calculate_news2(rr=16, spo2=97, sbp=120, hr=75, temp=37.0, consciousness="A")
        with_o2 = calculate_news2(rr=16, spo2=97, sbp=120, hr=75, temp=37.0, consciousness="A", on_supplemental_o2=True)
        assert with_o2.total_score == without.total_score + 2

    def test_missing_parameters_tracked(self):
        result = calculate_news2(rr=16, hr=75)  # missing spo2, sbp, temp, consciousness
        assert "spo2" in result.missing_parameters
        assert "systolic_bp" in result.missing_parameters

    def test_altered_consciousness_scores_3(self):
        result = calculate_news2(consciousness="V")
        assert result.parameter_scores["consciousness"] == 3

    def test_temperature_hypothermia(self):
        result = calculate_news2(temp=34.5)
        assert result.parameter_scores["temperature"] == 3

    def test_temperature_high_fever(self):
        result = calculate_news2(temp=39.5)
        assert result.parameter_scores["temperature"] == 2


class TestMEWS:
    def test_normal_patient(self):
        result = calculate_mews(rr=16, hr=80, sbp=120, consciousness="A", temp=37.0)
        assert result.total_score <= 2
        assert result.algorithm == "MEWS"

    def test_high_risk(self):
        result = calculate_mews(rr=30, hr=130, sbp=65, consciousness="U", temp=34.0)
        assert result.risk_level == "high"

    def test_avpu_scoring(self):
        r_a = calculate_mews(consciousness="A")
        r_v = calculate_mews(consciousness="V")
        r_u = calculate_mews(consciousness="U")
        assert r_a.parameter_scores["consciousness"] == 0
        assert r_v.parameter_scores["consciousness"] == 1
        assert r_u.parameter_scores["consciousness"] == 3
