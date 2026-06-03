from src.http.v1.request.onboarding import UpdateCompanyOnboardingRequest


def test_update_company_onboarding_request_accepts_primary_color() -> None:
    request = UpdateCompanyOnboardingRequest(primary_color="#3B5BDB")

    assert request.primary_color == "#3B5BDB"
